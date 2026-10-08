from django.contrib.auth.decorators import permission_required
from django.core.paginator import Paginator
from django.conf import settings
from django.shortcuts import render
from django.utils.cache import patch_vary_headers

from . import queries
from .filters import ConsultaFilter, PanelFilter

VIEW_PERM = "demografia.view_neighborhoodpopulation"


def _bound_with_default_period(form_class, request):
    data = request.GET.copy()
    if not data.get("periodo"):
        latest = queries.latest_snapshot()
        if latest:
            data["periodo"] = str(latest.pk)
    return form_class(data)


@permission_required(VIEW_PERM, raise_exception=True)
def consulta(request):
    form = _bound_with_default_period(ConsultaFilter, request)
    form.is_valid()
    period = form.cleaned_data.get("periodo")
    base = queries.population_queryset()
    qs = form.filter(base) if period else base.none()

    page = Paginator(qs, settings.PAGINATE_BY).get_page(request.GET.get("page"))
    context = {"filter_form": form, "page_obj": page, "period": period, "totals": queries.summary(qs)}
    template = "demografia/_consulta_results.html" if request.headers.get("HX-Request") else "demografia/consulta.html"
    response = render(request, template, context)
    patch_vary_headers(response, ["HX-Request"])
    return response


@permission_required(VIEW_PERM, raise_exception=True)
def panel(request):
    form = _bound_with_default_period(PanelFilter, request)
    form.is_valid()
    data = getattr(form, "cleaned_data", {})
    period = data.get("periodo")
    district = data.get("distrito")
    limit = data.get("limite") if "limite" in request.GET else 15

    charts = None
    totals = None
    if period:
        qs = queries.population_queryset(snapshot=period, district=district)
        totals = queries.summary(qs)
        charts = {
            "population": queries.by_neighborhood(qs, "population", limit),
            "density": queries.by_neighborhood(qs, "density", limit),
            "evolution": queries.evolution(district=district),
            "districts": queries.district_comparison(period),
            "selectedDistrict": district.pk if district else None,
            "ages": queries.age_distribution(period, district=district),
        }
    return render(
        request,
        "demografia/panel.html",
        {"filter_form": form, "period": period, "district": district, "totals": totals, "charts": charts},
    )
