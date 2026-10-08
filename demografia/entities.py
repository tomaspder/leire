"""Configuración de ABM por entidad (columnas, formularios y filtros)."""

from django.db.models import Count

from core.crud import Entity

from . import filters, forms, models
from .queries import annotate_density


def _round(value, digits=1):
    return round(value, digits) if value is not None else None


DISTRICT = Entity(
    slug="distritos",
    model=models.District,
    form_class=forms.DistrictForm,
    filter_form_class=filters.DistrictFilter,
    columns=[("Código", "code"), ("Nombre", "name"), ("Barrios", "num_neighborhoods")],
    annotate=lambda qs: qs.annotate(num_neighborhoods=Count("neighborhoods")),
    ordering=("code",),
)

NEIGHBORHOOD = Entity(
    slug="barrios",
    model=models.Neighborhood,
    form_class=forms.NeighborhoodForm,
    filter_form_class=filters.NeighborhoodFilter,
    columns=[
        ("Código", "code"),
        ("Nombre", "name"),
        ("Distrito", "district.name"),
        ("Superficie (km²)", "area_km2"),
    ],
    select_related=("district",),
    ordering=("district__code", "name"),
)

SNAPSHOT = Entity(
    slug="periodos",
    model=models.PopulationSnapshot,
    form_class=forms.PopulationSnapshotForm,
    filter_form_class=filters.SnapshotFilter,
    columns=[("Fecha de referencia", "reference_date"), ("Fuente (sintética)", "source_label")],
    ordering=("-reference_date",),
)

AGE_GROUP = Entity(
    slug="grupos-edad",
    model=models.AgeGroup,
    form_class=forms.AgeGroupForm,
    filter_form_class=filters.AgeGroupFilter,
    columns=[
        ("Etiqueta", "label"),
        ("Edad mínima", "min_age"),
        ("Edad máxima", lambda o: o.max_age if o.max_age is not None else "sin límite"),
    ],
    ordering=("min_age",),
)

POPULATION = Entity(
    slug="poblacion",
    model=models.NeighborhoodPopulation,
    form_class=forms.NeighborhoodPopulationForm,
    filter_form_class=filters.NeighborhoodPopulationFilter,
    columns=[
        ("Período", "snapshot"),
        ("Distrito", "neighborhood.district.name"),
        ("Barrio", "neighborhood.name"),
        ("Población", "total_population"),
        ("Hogares", "households"),
        ("Mujeres", "women"),
        ("Hombres", "men"),
        ("Densidad (hab/km²)", lambda o: _round(o.density_value)),
    ],
    select_related=("neighborhood__district", "snapshot"),
    annotate=annotate_density,
    ordering=("-snapshot__reference_date", "neighborhood__district__code", "neighborhood__name"),
)

AGE_POPULATION = Entity(
    slug="poblacion-edad",
    model=models.NeighborhoodAgePopulation,
    form_class=forms.NeighborhoodAgePopulationForm,
    filter_form_class=filters.NeighborhoodAgePopulationFilter,
    columns=[
        ("Período", "snapshot"),
        ("Distrito", "neighborhood.district.name"),
        ("Barrio", "neighborhood.name"),
        ("Grupo de edad", "age_group.label"),
        ("Habitantes", "population"),
    ],
    select_related=("neighborhood__district", "snapshot", "age_group"),
    ordering=("-snapshot__reference_date", "neighborhood__name", "age_group__min_age"),
)

ENTITIES = [DISTRICT, NEIGHBORHOOD, SNAPSHOT, AGE_GROUP, POPULATION, AGE_POPULATION]
