from django.core.management.commands.migrate import Command as MigrateCommand

from core.safety import ensure_schema_changes_allowed


class Command(MigrateCommand):
    def handle(self, *args, **options):
        ensure_schema_changes_allowed()
        return super().handle(*args, **options)
