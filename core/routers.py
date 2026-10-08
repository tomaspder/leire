from django.conf import settings


class SafeMigrationRouter:
    """Impide crear o modificar tablas de demostración fuera del modo demo."""

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        if app_label in settings.DEMO_ONLY_APPS and settings.APP_DB_MODE != "demo":
            return False
        return None
