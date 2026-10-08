from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path

from core import views as core_views

admin.site.site_header = "Administración de usuarios"
admin.site.site_title = "Administración"

urlpatterns = [
    path("", core_views.home, name="home"),
    path(
        "acceso/",
        auth_views.LoginView.as_view(redirect_authenticated_user=True),
        name="login",
    ),
    path("salir/", auth_views.LogoutView.as_view(), name="logout"),
    path("datos/", include("demografia.urls")),
    path("admin/", admin.site.urls),
]
