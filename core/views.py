from django.shortcuts import render

from core.crud import registry


def home(request):
    entities = [e for e in registry if request.user.has_perm(e.perm("view"))]
    return render(request, "core/home.html", {"entities": entities})
