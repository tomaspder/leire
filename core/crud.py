"""Vistas genéricas de ABM protegidas por permisos de modelo de Django."""

from dataclasses import dataclass, field
from typing import Callable

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.db.models import ProtectedError, RestrictedError
from django.shortcuts import redirect
from django.urls import path, reverse_lazy
from django.utils.cache import patch_vary_headers
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

registry = []


@dataclass
class Entity:
    slug: str
    model: type
    form_class: type
    # (encabezado, atributo con puntos o función que recibe el objeto)
    columns: list
    filter_form_class: type | None = None
    ordering: tuple = ()
    select_related: tuple = ()
    annotate: Callable | None = None
    description: str = ""
    extra: dict = field(default_factory=dict)

    @property
    def meta(self):
        return self.model._meta

    @property
    def verbose_name(self):
        return self.meta.verbose_name

    @property
    def verbose_name_plural(self):
        return self.meta.verbose_name_plural

    def perm(self, action):
        return f"{self.meta.app_label}.{action}_{self.meta.model_name}"

    def url_name(self, action):
        return f"{self.slug}_{action}"

    @property
    def url_list(self):
        return self.url_name("list")

    @property
    def url_create(self):
        return self.url_name("create")

    @property
    def url_update(self):
        return self.url_name("update")

    @property
    def url_delete(self):
        return self.url_name("delete")

    def queryset(self):
        qs = self.model._default_manager.all()
        if self.select_related:
            qs = qs.select_related(*self.select_related)
        if self.annotate:
            qs = self.annotate(qs)
        if self.ordering:
            qs = qs.order_by(*self.ordering)
        return qs


def resolve(obj, accessor):
    if callable(accessor):
        return accessor(obj)
    value = obj
    for part in accessor.split("."):
        value = getattr(value, part, None)
        if value is None:
            break
    return value


class EntityMixin(PermissionRequiredMixin):
    entity: Entity = None
    action = "view"
    raise_exception = True

    def get_permission_required(self):
        return [self.entity.perm(self.action)]

    def get_queryset(self):
        return self.entity.queryset()

    def get_success_url(self):
        return reverse_lazy(self.entity.url_list)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user
        ctx.update(
            entity=self.entity,
            can_add=user.has_perm(self.entity.perm("add")),
            can_change=user.has_perm(self.entity.perm("change")),
            can_delete=user.has_perm(self.entity.perm("delete")),
        )
        return ctx


class EntityListView(EntityMixin, ListView):
    template_name = "crud/list.html"
    paginate_by = settings.PAGINATE_BY

    def get_queryset(self):
        qs = super().get_queryset()
        form_class = self.entity.filter_form_class
        self.filter_form = form_class(self.request.GET or None) if form_class else None
        if self.filter_form is not None:
            qs = self.filter_form.filter(qs)
        return qs

    def get_template_names(self):
        if self.request.headers.get("HX-Request"):
            return ["crud/_results.html"]
        return [self.template_name]

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["filter_form"] = self.filter_form
        ctx["headers"] = [label for label, _ in self.entity.columns]
        ctx["rows"] = [
            (obj, [resolve(obj, accessor) for _, accessor in self.entity.columns])
            for obj in ctx["object_list"]
        ]
        return ctx

    def render_to_response(self, context, **kwargs):
        response = super().render_to_response(context, **kwargs)
        patch_vary_headers(response, ["HX-Request"])
        return response


class EntityCreateView(EntityMixin, SuccessMessageMixin, CreateView):
    action = "add"
    template_name = "crud/form.html"
    success_message = "Registro creado correctamente."

    def get_form_class(self):
        return self.entity.form_class


class EntityUpdateView(EntityMixin, SuccessMessageMixin, UpdateView):
    action = "change"
    template_name = "crud/form.html"
    success_message = "Cambios guardados correctamente."

    def get_form_class(self):
        return self.entity.form_class


class EntityDeleteView(EntityMixin, DeleteView):
    action = "delete"
    template_name = "crud/confirm_delete.html"

    def form_valid(self, form):
        try:
            response = super().form_valid(form)
        except (ProtectedError, RestrictedError) as exc:
            objs = getattr(exc, "protected_objects", None) or getattr(exc, "restricted_objects", [])
            related = sorted({str(obj._meta.verbose_name_plural) for obj in objs})
            messages.error(
                self.request,
                "No se puede eliminar el registro porque tiene datos relacionados ("
                + ", ".join(related)
                + "). Elimine o reasigne primero esos datos.",
            )
            return redirect(self.entity.url_list)
        messages.success(self.request, "Registro eliminado correctamente.")
        return response


def entity_urls(entity):
    if entity not in registry:
        registry.append(entity)
    kw = {"entity": entity}
    return [
        path(f"{entity.slug}/", EntityListView.as_view(**kw), name=entity.url_list),
        path(f"{entity.slug}/nuevo/", EntityCreateView.as_view(**kw), name=entity.url_create),
        path(f"{entity.slug}/<int:pk>/editar/", EntityUpdateView.as_view(**kw), name=entity.url_update),
        path(f"{entity.slug}/<int:pk>/eliminar/", EntityDeleteView.as_view(**kw), name=entity.url_delete),
    ]
