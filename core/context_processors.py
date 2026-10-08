from django.conf import settings


def app_mode(request):
    return {"DEMO_MODE": settings.APP_DB_MODE == "demo"}
