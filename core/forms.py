from django import forms
from django.db.models import Q


class BootstrapFormMixin:
    """Aplica clases de Bootstrap 5 a los widgets."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            widget = field.widget
            if isinstance(widget, forms.CheckboxInput):
                css = "form-check-input"
            elif isinstance(widget, (forms.Select, forms.SelectMultiple)):
                css = "form-select"
            else:
                css = "form-control"
            widget.attrs["class"] = f"{widget.attrs.get('class', '')} {css}".strip()

    def full_clean(self):
        super().full_clean()
        for name in self.errors:
            if name in self.fields:
                attrs = self.fields[name].widget.attrs
                attrs["class"] += " is-invalid"
                attrs["aria-invalid"] = "true"


class FilterForm(BootstrapFormMixin, forms.Form):
    """Formulario de filtros GET. Las subclases definen campos y `apply()`."""

    search_fields = ()

    q = forms.CharField(
        label="Buscar",
        required=False,
        max_length=100,
        widget=forms.TextInput(attrs={"type": "search", "placeholder": "Buscar…"}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.search_fields:
            del self.fields["q"]

    def filter(self, queryset):
        if not self.is_bound:
            return queryset
        self.is_valid()
        # Los campos inválidos se ignoran; se aplican solo los valores validados.
        data = getattr(self, "cleaned_data", {})
        term = data.get("q")
        if term:
            query = Q()
            for field in self.search_fields:
                query |= Q(**{f"{field}__icontains": term})
            queryset = queryset.filter(query)
        return self.apply(queryset, data)

    def apply(self, queryset, data):
        return queryset
