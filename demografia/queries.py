"""Consultas de agregación. Toda la lógica de cálculo vive aquí, separada de los datos de carga."""

from django.db.models import F, FloatField, Sum
from django.db.models.functions import Cast, Coalesce, NullIf

from .models import NeighborhoodAgePopulation, NeighborhoodPopulation, PopulationSnapshot


def density_expression(population="total_population", area="neighborhood__area_km2"):
    return Cast(F(population), FloatField()) / Cast(F(area), FloatField())


def annotate_density(queryset):
    return queryset.annotate(density_value=density_expression())


def latest_snapshot():
    return PopulationSnapshot.objects.order_by("-reference_date").first()


def population_queryset(snapshot=None, district=None):
    qs = NeighborhoodPopulation.objects.select_related("neighborhood__district", "snapshot")
    if snapshot is not None:
        qs = qs.filter(snapshot=snapshot)
    if district is not None:
        qs = qs.filter(neighborhood__district=district)
    return annotate_density(qs).annotate(
        household_size=Cast(F("total_population"), FloatField()) / NullIf(Cast(F("households"), FloatField()), 0.0)
    )


def summary(queryset):
    totals = queryset.aggregate(
        population=Coalesce(Sum("total_population"), 0),
        households=Coalesce(Sum("households"), 0),
        area=Sum(Cast("neighborhood__area_km2", FloatField())),
    )
    totals["neighborhoods"] = queryset.values("neighborhood").distinct().count()
    area = totals["area"] or 0
    totals["density"] = round(totals["population"] / area, 1) if area else None
    totals["household_size"] = (
        round(totals["population"] / totals["households"], 2) if totals["households"] else None
    )
    return totals


def by_neighborhood(queryset, metric, limit=None):
    """Lista ordenada de (barrio, valor) para 'population' o 'density'."""
    field = {"population": "total_population", "density": "density_value"}[metric]
    rows = queryset.order_by(f"-{field}", "neighborhood__name")
    if limit:
        rows = rows[:limit]
    return [
        {"label": r.neighborhood.name, "value": round(getattr(r, field), 1)}
        for r in rows
    ]


def evolution(district=None):
    qs = NeighborhoodPopulation.objects.all()
    if district is not None:
        qs = qs.filter(neighborhood__district=district)
    rows = (
        qs.values("snapshot__reference_date")
        .annotate(population=Sum("total_population"))
        .order_by("snapshot__reference_date")
    )
    return [
        {"label": r["snapshot__reference_date"].strftime("%d/%m/%Y"), "value": r["population"]}
        for r in rows
    ]


def district_comparison(snapshot):
    rows = (
        NeighborhoodPopulation.objects.filter(snapshot=snapshot)
        .values("neighborhood__district_id", "neighborhood__district__name", "neighborhood__district__code")
        .annotate(
            population=Sum("total_population"),
            area=Sum(Cast("neighborhood__area_km2", FloatField())),
        )
        .order_by("neighborhood__district__code")
    )
    return [
        {
            "id": r["neighborhood__district_id"],
            "label": r["neighborhood__district__name"],
            "population": r["population"],
            "density": round(r["population"] / r["area"], 1) if r["area"] else None,
        }
        for r in rows
    ]


def age_distribution(snapshot, district=None):
    qs = NeighborhoodAgePopulation.objects.filter(snapshot=snapshot)
    if district is not None:
        qs = qs.filter(neighborhood__district=district)
    rows = (
        qs.values("age_group__label", "age_group__min_age")
        .annotate(population=Sum("population"))
        .order_by("age_group__min_age")
    )
    return [{"label": r["age_group__label"], "value": r["population"]} for r in rows]
