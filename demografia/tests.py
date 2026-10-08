from decimal import Decimal
from io import StringIO
from unittest import mock

from django.contrib.auth.models import Group, User
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db.models import Sum
from django.test import TestCase, override_settings
from django.urls import reverse

from . import queries
from .models import (
    AgeGroup,
    District,
    Neighborhood,
    NeighborhoodAgePopulation,
    NeighborhoodPopulation,
    PopulationSnapshot,
)

PASSWORD = "clave-de-prueba-larga-123"


def make_user(username, group=None):
    user = User.objects.create_user(username, password=PASSWORD)
    if group:
        user.groups.add(Group.objects.get(name=group))
    return user


class BaseDataTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("configurar_grupos", stdout=StringIO())
        cls.d1 = District.objects.create(name="Distrito Uno", code="D01")
        cls.d2 = District.objects.create(name="Distrito Dos", code="D02")
        cls.n1 = Neighborhood.objects.create(district=cls.d1, name="Barrio A", code="B001", area_km2=Decimal("2.000"))
        cls.n2 = Neighborhood.objects.create(district=cls.d1, name="Barrio B", code="B002", area_km2=Decimal("0.500"))
        cls.n3 = Neighborhood.objects.create(district=cls.d2, name="Barrio C", code="B003", area_km2=Decimal("4.000"))
        cls.s1 = PopulationSnapshot.objects.create(reference_date="2020-01-01")
        cls.s2 = PopulationSnapshot.objects.create(reference_date="2021-01-01")
        for snap, factor in ((cls.s1, 1), (cls.s2, 2)):
            NeighborhoodPopulation.objects.create(neighborhood=cls.n1, snapshot=snap, total_population=1000 * factor, households=400)
            NeighborhoodPopulation.objects.create(neighborhood=cls.n2, snapshot=snap, total_population=2000 * factor, households=800)
            NeighborhoodPopulation.objects.create(neighborhood=cls.n3, snapshot=snap, total_population=4000 * factor, households=1600)
        cls.young = AgeGroup.objects.create(label="0 a 14", min_age=0, max_age=14)
        cls.old = AgeGroup.objects.create(label="15 o más", min_age=15)
        NeighborhoodAgePopulation.objects.create(neighborhood=cls.n1, snapshot=cls.s2, age_group=cls.young, population=500)
        NeighborhoodAgePopulation.objects.create(neighborhood=cls.n1, snapshot=cls.s2, age_group=cls.old, population=1500)
        NeighborhoodAgePopulation.objects.create(neighborhood=cls.n3, snapshot=cls.s2, age_group=cls.old, population=8000)
        cls.reader = make_user("lectora", "Consulta")
        cls.editor = make_user("editora", "Edición")
        cls.nobody = make_user("sinpermisos")


class PermissionTests(BaseDataTestCase):
    def test_user_without_permissions_gets_403(self):
        self.client.force_login(self.nobody)
        for name in ["panel", "consulta", "distritos_list", "poblacion_list"]:
            self.assertEqual(self.client.get(reverse(name)).status_code, 403, name)

    def test_reader_can_view_but_not_modify(self):
        self.client.force_login(self.reader)
        self.assertEqual(self.client.get(reverse("distritos_list")).status_code, 200)
        self.assertEqual(self.client.get(reverse("panel")).status_code, 200)
        self.assertEqual(self.client.get(reverse("distritos_create")).status_code, 403)
        self.assertEqual(
            self.client.post(reverse("distritos_create"), {"name": "Nuevo", "code": "D99"}).status_code, 403
        )
        self.assertEqual(
            self.client.post(reverse("distritos_update", args=[self.d1.pk]), {"name": "Cambio", "code": "D01"}).status_code,
            403,
        )
        self.assertEqual(self.client.post(reverse("distritos_delete", args=[self.d2.pk])).status_code, 403)
        self.assertFalse(District.objects.filter(code="D99").exists())
        self.assertTrue(District.objects.filter(name="Distrito Uno").exists())

    def test_reader_does_not_see_edit_buttons(self):
        self.client.force_login(self.reader)
        response = self.client.get(reverse("distritos_list"))
        self.assertNotContains(response, "Nuevo registro")
        self.assertNotContains(response, reverse("distritos_delete", args=[self.d1.pk]))


class CrudTests(BaseDataTestCase):
    def setUp(self):
        self.client.force_login(self.editor)

    def test_create_update_delete_district(self):
        response = self.client.post(reverse("distritos_create"), {"name": "Distrito Tres", "code": "D03"})
        self.assertRedirects(response, reverse("distritos_list"))
        district = District.objects.get(code="D03")

        response = self.client.post(reverse("distritos_update", args=[district.pk]), {"name": "Distrito 3", "code": "D03"})
        self.assertRedirects(response, reverse("distritos_list"))
        district.refresh_from_db()
        self.assertEqual(district.name, "Distrito 3")

        self.assertContains(self.client.get(reverse("distritos_delete", args=[district.pk])), "¿Confirma")
        response = self.client.post(reverse("distritos_delete", args=[district.pk]))
        self.assertRedirects(response, reverse("distritos_list"))
        self.assertFalse(District.objects.filter(pk=district.pk).exists())

    def test_duplicate_code_shows_spanish_error(self):
        response = self.client.post(reverse("distritos_create"), {"name": "Otro", "code": "D01"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Ya existe")

    def test_delete_with_related_data_is_blocked(self):
        response = self.client.post(reverse("distritos_delete", args=[self.d1.pk]), follow=True)
        self.assertTrue(District.objects.filter(pk=self.d1.pk).exists())
        self.assertContains(response, "No se puede eliminar")

    def test_create_neighborhood_validates_area(self):
        data = {"district": self.d1.pk, "name": "Nuevo", "code": "B010", "area_km2": "0"}
        response = self.client.post(reverse("barrios_create"), data)
        self.assertContains(response, "La superficie debe ser mayor que 0.")
        data["area_km2"] = "1.250"
        self.assertRedirects(self.client.post(reverse("barrios_create"), data), reverse("barrios_list"))

    def test_duplicate_neighborhood_name_in_district(self):
        data = {"district": self.d1.pk, "name": "Barrio A", "code": "B011", "area_km2": "1"}
        response = self.client.post(reverse("barrios_create"), data)
        self.assertContains(response, "Ya existe un barrio con ese nombre en el distrito.")

    def test_population_households_constraint(self):
        snap = PopulationSnapshot.objects.create(reference_date="2022-01-01")
        data = {"neighborhood": self.n1.pk, "snapshot": snap.pk, "total_population": 100, "households": 200}
        response = self.client.post(reverse("poblacion_create"), data)
        self.assertContains(response, "La cantidad de hogares no puede superar la población total.")
        data["households"] = 40
        self.assertRedirects(self.client.post(reverse("poblacion_create"), data), reverse("poblacion_list"))

    def test_population_unique_per_period(self):
        data = {"neighborhood": self.n1.pk, "snapshot": self.s1.pk, "total_population": 100, "households": 10}
        response = self.client.post(reverse("poblacion_create"), data)
        self.assertContains(response, "Ya existe un registro de población para ese barrio y período.")

    def test_age_group_constraint(self):
        response = self.client.post(reverse("grupos-edad_create"), {"label": "X", "min_age": 30, "max_age": 20})
        self.assertContains(response, "La edad máxima debe ser mayor o igual que la mínima.")

    def test_all_entity_pages_render(self):
        for slug in ["distritos", "barrios", "periodos", "grupos-edad", "poblacion", "poblacion-edad"]:
            self.assertEqual(self.client.get(reverse(f"{slug}_list")).status_code, 200, slug)
            self.assertEqual(self.client.get(reverse(f"{slug}_create")).status_code, 200, slug)


class ListFilterTests(BaseDataTestCase):
    def setUp(self):
        self.client.force_login(self.reader)

    def test_search_and_district_filter(self):
        response = self.client.get(reverse("barrios_list"), {"q": "barrio a"})
        self.assertEqual(response.context["paginator"].count, 1)
        response = self.client.get(reverse("barrios_list"), {"distrito": self.d1.pk})
        self.assertEqual(response.context["paginator"].count, 2)

    def test_density_filter(self):
        # Densidades 2021: A=1000, B=8000, C=2000 hab/km²
        response = self.client.get(reverse("poblacion_list"), {"periodo": self.s2.pk, "densidad_min": 1500})
        names = sorted(obj.neighborhood.name for obj, _ in response.context["rows"])
        self.assertEqual(names, ["Barrio B", "Barrio C"])

    def test_invalid_filter_value_is_ignored(self):
        response = self.client.get(reverse("barrios_list"), {"distrito": "no-existe"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["paginator"].count, 3)

    def test_htmx_returns_partial(self):
        response = self.client.get(reverse("barrios_list"), {"q": "C"}, HTTP_HX_REQUEST="true")
        self.assertTemplateUsed(response, "crud/_results.html")
        self.assertTemplateNotUsed(response, "base.html")
        self.assertIn("HX-Request", response["Vary"])

    def test_pagination(self):
        from core import crud

        with mock.patch.object(crud.EntityListView, "paginate_by", 2):
            response = self.client.get(reverse("poblacion_list"))
        self.assertTrue(response.context["is_paginated"])
        self.assertEqual(response.context["paginator"].num_pages, 3)


class QueryTests(BaseDataTestCase):
    def test_density_is_population_over_area(self):
        row = queries.population_queryset(snapshot=self.s1).get(neighborhood=self.n2)
        self.assertAlmostEqual(row.density_value, 4000.0)
        self.assertEqual(row.density, 4000.0)

    def test_summary(self):
        totals = queries.summary(queries.population_queryset(snapshot=self.s1, district=self.d1))
        self.assertEqual(totals["population"], 3000)
        self.assertEqual(totals["neighborhoods"], 2)
        self.assertEqual(totals["density"], round(3000 / 2.5, 1))

    def test_evolution(self):
        self.assertEqual([r["value"] for r in queries.evolution()], [7000, 14000])
        self.assertEqual([r["value"] for r in queries.evolution(district=self.d2)], [4000, 8000])

    def test_district_comparison(self):
        rows = {r["label"]: r for r in queries.district_comparison(self.s1)}
        self.assertEqual(rows["Distrito Uno"]["population"], 3000)
        self.assertEqual(rows["Distrito Dos"]["density"], 1000.0)

    def test_age_distribution(self):
        rows = queries.age_distribution(self.s2)
        self.assertEqual([r["value"] for r in rows], [500, 9500])
        rows = queries.age_distribution(self.s2, district=self.d2)
        self.assertEqual([r["value"] for r in rows], [8000])


class PanelAndConsultaTests(BaseDataTestCase):
    def setUp(self):
        self.client.force_login(self.reader)

    def test_panel_defaults_to_latest_period(self):
        response = self.client.get(reverse("panel"))
        self.assertEqual(response.context["period"], self.s2)
        self.assertContains(response, 'id="chart-data"')
        self.assertContains(response, "Datos de demostración: cifras ficticias")

    def test_panel_filters_update_chart_data(self):
        response = self.client.get(reverse("panel"), {"periodo": self.s1.pk, "distrito": self.d2.pk})
        charts = response.context["charts"]
        self.assertEqual(charts["population"], [{"label": "Barrio C", "value": 4000}])
        self.assertEqual(charts["selectedDistrict"], self.d2.pk)
        self.assertEqual(response.context["totals"]["population"], 4000)

    def test_panel_limit(self):
        response = self.client.get(reverse("panel"), {"periodo": self.s2.pk, "limite": 15})
        self.assertEqual(len(response.context["charts"]["density"]), 3)
        self.assertEqual(response.context["charts"]["density"][0]["label"], "Barrio B")

    def test_consulta_filters_and_order(self):
        response = self.client.get(
            reverse("consulta"), {"periodo": self.s2.pk, "orden": "poblacion_desc", "distrito": self.d1.pk}
        )
        names = [r.neighborhood.name for r in response.context["page_obj"]]
        self.assertEqual(names, ["Barrio B", "Barrio A"])
        self.assertEqual(response.context["totals"]["population"], 6000)

    def test_consulta_rejects_arbitrary_order(self):
        response = self.client.get(reverse("consulta"), {"orden": "neighborhood__district__name; DROP"})
        self.assertEqual(response.status_code, 200)


class SeedCommandTests(TestCase):
    def test_load_is_reproducible(self):
        call_command("cargar_datos_demo", stdout=StringIO())
        self.assertEqual(District.objects.count(), 10)
        self.assertEqual(Neighborhood.objects.count(), 73)
        total_1 = NeighborhoodPopulation.objects.aggregate(t=Sum("total_population"))["t"]

        with self.assertRaisesMessage(CommandError, "--reemplazar"):
            call_command("cargar_datos_demo", stdout=StringIO())

        call_command("cargar_datos_demo", "--reemplazar", stdout=StringIO())
        total_2 = NeighborhoodPopulation.objects.aggregate(t=Sum("total_population"))["t"]
        self.assertEqual(total_1, total_2)

        # Los grupos de edad suman exactamente la población total de cada barrio y período.
        ages = NeighborhoodAgePopulation.objects.aggregate(t=Sum("population"))["t"]
        self.assertEqual(ages, total_2)

    @override_settings(APP_DB_MODE="real")
    def test_load_refused_outside_demo_mode(self):
        with self.assertRaises(CommandError):
            call_command("cargar_datos_demo", stdout=StringIO())
        self.assertFalse(District.objects.exists())
