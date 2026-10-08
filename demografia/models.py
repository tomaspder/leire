"""Esquema de DEMOSTRACIÓN con datos ficticios. No representa la base universitaria."""

from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import F, Q


class District(models.Model):
    name = models.CharField("nombre", max_length=100, unique=True)
    code = models.CharField("código", max_length=10, unique=True)

    class Meta:
        db_table = "district"
        verbose_name = "distrito"
        verbose_name_plural = "distritos"
        ordering = ["code"]

    def __str__(self):
        return self.name


class Neighborhood(models.Model):
    district = models.ForeignKey(
        District, on_delete=models.PROTECT, related_name="neighborhoods", verbose_name="distrito"
    )
    name = models.CharField("nombre", max_length=120)
    code = models.CharField("código", max_length=10, unique=True)
    area_km2 = models.DecimalField(
        "superficie (km²)",
        max_digits=8,
        decimal_places=3,
        validators=[MinValueValidator(Decimal("0.001"), "La superficie debe ser mayor que 0.")],
    )

    class Meta:
        db_table = "neighborhood"
        verbose_name = "barrio"
        verbose_name_plural = "barrios"
        ordering = ["district__code", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["district", "name"],
                name="neighborhood_unique_name_per_district",
                violation_error_message="Ya existe un barrio con ese nombre en el distrito.",
            ),
            models.CheckConstraint(
                condition=Q(area_km2__gt=0),
                name="neighborhood_area_positive",
                violation_error_message="La superficie debe ser mayor que 0.",
            ),
        ]

    def __str__(self):
        return self.name


class PopulationSnapshot(models.Model):
    reference_date = models.DateField("fecha de referencia", unique=True)
    source_label = models.CharField(
        "fuente (sintética)", max_length=200, default="Fuente sintética de demostración"
    )

    class Meta:
        db_table = "population_snapshot"
        verbose_name = "período"
        verbose_name_plural = "períodos"
        ordering = ["reference_date"]

    def __str__(self):
        return self.reference_date.strftime("%d/%m/%Y")


class AgeGroup(models.Model):
    label = models.CharField("etiqueta", max_length=50, unique=True)
    min_age = models.PositiveSmallIntegerField("edad mínima", unique=True)
    max_age = models.PositiveSmallIntegerField(
        "edad máxima", null=True, blank=True, help_text="Dejar vacío para un grupo abierto (p. ej. 80 o más)."
    )

    class Meta:
        db_table = "age_group"
        verbose_name = "grupo de edad"
        verbose_name_plural = "grupos de edad"
        ordering = ["min_age"]
        constraints = [
            models.CheckConstraint(
                condition=Q(max_age__isnull=True) | Q(max_age__gte=F("min_age")),
                name="age_group_max_gte_min",
                violation_error_message="La edad máxima debe ser mayor o igual que la mínima.",
            ),
        ]

    def __str__(self):
        return self.label


class NeighborhoodPopulation(models.Model):
    neighborhood = models.ForeignKey(
        Neighborhood, on_delete=models.PROTECT, related_name="populations", verbose_name="barrio"
    )
    snapshot = models.ForeignKey(
        PopulationSnapshot, on_delete=models.PROTECT, related_name="populations", verbose_name="período"
    )
    total_population = models.PositiveIntegerField("población total")
    households = models.PositiveIntegerField("hogares")
    women = models.PositiveIntegerField("mujeres", null=True, blank=True)
    men = models.PositiveIntegerField("hombres", null=True, blank=True)

    class Meta:
        db_table = "neighborhood_population"
        verbose_name = "población por barrio"
        verbose_name_plural = "población por barrio"
        ordering = ["-snapshot__reference_date", "neighborhood__district__code", "neighborhood__name"]
        constraints = [
            models.UniqueConstraint(
                fields=["neighborhood", "snapshot"],
                name="neighborhood_population_unique",
                violation_error_message="Ya existe un registro de población para ese barrio y período.",
            ),
            models.CheckConstraint(
                condition=Q(households__lte=F("total_population")),
                name="neighborhood_population_households_lte_total",
                violation_error_message="La cantidad de hogares no puede superar la población total.",
            ),
            models.CheckConstraint(
                condition=Q(women__isnull=True)
                | Q(men__isnull=True)
                | Q(total_population__gte=F("women") + F("men")),
                name="neighborhood_population_sex_lte_total",
                violation_error_message="La suma de mujeres y hombres no puede superar la población total.",
            ),
        ]

    def __str__(self):
        return f"{self.neighborhood} – {self.snapshot}"

    @property
    def density(self):
        """Habitantes por km², derivado; no se almacena."""
        if not self.neighborhood.area_km2:
            return None
        return round(self.total_population / float(self.neighborhood.area_km2), 1)


class NeighborhoodAgePopulation(models.Model):
    neighborhood = models.ForeignKey(
        Neighborhood, on_delete=models.PROTECT, related_name="age_populations", verbose_name="barrio"
    )
    snapshot = models.ForeignKey(
        PopulationSnapshot, on_delete=models.PROTECT, related_name="age_populations", verbose_name="período"
    )
    age_group = models.ForeignKey(
        AgeGroup, on_delete=models.PROTECT, related_name="populations", verbose_name="grupo de edad"
    )
    population = models.PositiveIntegerField("habitantes")

    class Meta:
        db_table = "neighborhood_age_population"
        verbose_name = "población por grupo de edad"
        verbose_name_plural = "población por grupo de edad"
        ordering = ["-snapshot__reference_date", "neighborhood__name", "age_group__min_age"]
        constraints = [
            models.UniqueConstraint(
                fields=["neighborhood", "snapshot", "age_group"],
                name="neighborhood_age_population_unique",
                violation_error_message="Ya existe un registro para ese barrio, período y grupo de edad.",
            ),
        ]

    def __str__(self):
        return f"{self.neighborhood} – {self.snapshot} – {self.age_group}"
