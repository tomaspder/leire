from django import forms

from core.forms import BootstrapFormMixin, FilterForm

from .models import AgeGroup, District, PopulationSnapshot


def district_field(label="Distrito"):
    return forms.ModelChoiceField(
        label=label, queryset=District.objects.order_by("code"), required=False, empty_label="Todos"
    )


def snapshot_field(required=False):
    return forms.ModelChoiceField(
        label="Período",
        queryset=PopulationSnapshot.objects.order_by("-reference_date"),
        required=required,
        empty_label=None if required else "Todos",
    )


class DistrictFilter(FilterForm):
    search_fields = ("name", "code")


class NeighborhoodFilter(FilterForm):
    search_fields = ("name", "code")
    distrito = district_field()

    def apply(self, qs, data):
        if data.get("distrito"):
            qs = qs.filter(district=data["distrito"])
        return qs


class SnapshotFilter(FilterForm):
    search_fields = ("source_label",)
    anio = forms.IntegerField(label="Año", required=False, min_value=1900, max_value=2100)

    def apply(self, qs, data):
        if data.get("anio"):
            qs = qs.filter(reference_date__year=data["anio"])
        return qs


class AgeGroupFilter(FilterForm):
    search_fields = ("label",)


class NeighborhoodPopulationFilter(FilterForm):
    search_fields = ("neighborhood__name", "neighborhood__code")
    distrito = district_field()
    periodo = snapshot_field()
    densidad_min = forms.FloatField(label="Densidad mín. (hab/km²)", required=False, min_value=0)
    densidad_max = forms.FloatField(label="Densidad máx. (hab/km²)", required=False, min_value=0)

    def apply(self, qs, data):
        if data.get("distrito"):
            qs = qs.filter(neighborhood__district=data["distrito"])
        if data.get("periodo"):
            qs = qs.filter(snapshot=data["periodo"])
        if data.get("densidad_min") is not None:
            qs = qs.filter(density_value__gte=data["densidad_min"])
        if data.get("densidad_max") is not None:
            qs = qs.filter(density_value__lte=data["densidad_max"])
        return qs


class NeighborhoodAgePopulationFilter(FilterForm):
    search_fields = ("neighborhood__name", "neighborhood__code")
    distrito = district_field()
    periodo = snapshot_field()
    grupo = forms.ModelChoiceField(
        label="Grupo de edad", queryset=AgeGroup.objects.all(), required=False, empty_label="Todos"
    )

    def apply(self, qs, data):
        if data.get("distrito"):
            qs = qs.filter(neighborhood__district=data["distrito"])
        if data.get("periodo"):
            qs = qs.filter(snapshot=data["periodo"])
        if data.get("grupo"):
            qs = qs.filter(age_group=data["grupo"])
        return qs


CONSULTA_ORDERS = {
    "densidad_desc": ("Densidad (mayor a menor)", ("-density_value",)),
    "densidad_asc": ("Densidad (menor a mayor)", ("density_value",)),
    "poblacion_desc": ("Población (mayor a menor)", ("-total_population",)),
    "poblacion_asc": ("Población (menor a mayor)", ("total_population",)),
    "barrio": ("Barrio (A-Z)", ("neighborhood__name",)),
    "distrito": ("Distrito", ("neighborhood__district__code", "neighborhood__name")),
}


class ConsultaFilter(NeighborhoodPopulationFilter):
    periodo = snapshot_field(required=True)
    orden = forms.ChoiceField(
        label="Ordenar por",
        required=False,
        choices=[(key, label) for key, (label, _) in CONSULTA_ORDERS.items()],
    )

    def apply(self, qs, data):
        qs = super().apply(qs, data)
        _, order = CONSULTA_ORDERS.get(data.get("orden") or "distrito")
        return qs.order_by(*order)


class PanelFilter(BootstrapFormMixin, forms.Form):
    periodo = snapshot_field(required=True)
    distrito = district_field()
    limite = forms.TypedChoiceField(
        label="Barrios mostrados",
        coerce=int,
        required=False,
        empty_value=0,
        choices=[(15, "15 principales"), (30, "30 principales"), (0, "Todos")],
    )
