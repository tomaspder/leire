"""Salvaguardas para no escribir por accidente en una base que no sea de demostración."""

import os

from django.conf import settings
from django.core.management.base import CommandError

LOCAL_HOSTS = {"", "localhost", "127.0.0.1", "::1"}


def ensure_demo_database(connection):
    """Lanza CommandError salvo que la conexión apunte a una base local de demostración."""
    if settings.APP_DB_MODE != "demo":
        raise CommandError("Operación permitida solo con APP_DB_MODE=demo.")
    db = connection.settings_dict
    name = db.get("NAME") or ""
    host = db.get("HOST") or ""
    if "demo" not in name.lower():
        raise CommandError(f"La base '{name}' no parece de demostración (su nombre debe contener 'demo').")
    if host not in LOCAL_HOSTS and not host.startswith("/"):
        raise CommandError(f"El host '{host}' no es local. Solo se admiten bases de demostración locales.")


def ensure_schema_changes_allowed():
    """Bloquea migraciones y vaciados en modo real salvo autorización explícita."""
    if settings.APP_DB_MODE == "demo":
        return
    if os.environ.get("ALLOW_REAL_DB_MIGRATIONS") != "si":
        raise CommandError(
            "Bloqueado: APP_DB_MODE=real. No se modifican tablas de la base real sin un plan aprobado. "
            "Ver docs/plan-base-real.md."
        )
