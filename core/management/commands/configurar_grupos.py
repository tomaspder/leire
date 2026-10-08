from django.conf import settings
from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand

GROUPS = {
    "Consulta": ("view",),
    "Edición": ("view", "add", "change", "delete"),
}


class Command(BaseCommand):
    help = "Crea o actualiza los grupos 'Consulta' (solo lectura) y 'Edición' (ABM) para las apps de datos."

    def handle(self, *args, **options):
        for name, actions in GROUPS.items():
            group, _ = Group.objects.get_or_create(name=name)
            perms = Permission.objects.filter(
                content_type__app_label__in=settings.DATA_APPS,
                codename__regex=r"^(%s)_" % "|".join(actions),
            )
            group.permissions.set(perms)
            self.stdout.write(f"Grupo '{name}': {perms.count()} permisos.")
