from django.core.management.commands.flush import Command as FlushCommand

from core.safety import ensure_schema_changes_allowed


class Command(FlushCommand):
    def handle(self, *args, **options):
        ensure_schema_changes_allowed()
        return super().handle(*args, **options)
