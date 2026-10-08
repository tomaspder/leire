from django.urls import path

from core.crud import entity_urls

from . import views
from .entities import ENTITIES

urlpatterns = [
    path("panel/", views.panel, name="panel"),
    path("consulta/", views.consulta, name="consulta"),
]
for _entity in ENTITIES:
    urlpatterns += entity_urls(_entity)
