from django import forms

from core.forms import BootstrapFormMixin

from .models import (
    AgeGroup,
    District,
    Neighborhood,
    NeighborhoodAgePopulation,
    NeighborhoodPopulation,
    PopulationSnapshot,
)


def neighborhood_label(obj):
    return f"{obj.name} ({obj.district.name})"


class NeighborhoodChoiceMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        field = self.fields["neighborhood"]
        field.queryset = Neighborhood.objects.select_related("district").order_by("district__code", "name")
        field.label_from_instance = neighborhood_label


class DistrictForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = District
        fields = ["name", "code"]


class NeighborhoodForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Neighborhood
        fields = ["district", "name", "code", "area_km2"]


class PopulationSnapshotForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = PopulationSnapshot
        fields = ["reference_date", "source_label"]
        widgets = {"reference_date": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d")}


class AgeGroupForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = AgeGroup
        fields = ["label", "min_age", "max_age"]


class NeighborhoodPopulationForm(NeighborhoodChoiceMixin, BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = NeighborhoodPopulation
        fields = ["neighborhood", "snapshot", "total_population", "households", "women", "men"]


class NeighborhoodAgePopulationForm(NeighborhoodChoiceMixin, BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = NeighborhoodAgePopulation
        fields = ["neighborhood", "snapshot", "age_group", "population"]
