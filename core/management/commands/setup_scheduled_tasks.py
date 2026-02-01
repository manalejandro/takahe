"""
Management command to set up default scheduled tasks.
"""
from django.core.management.base import BaseCommand

from core.models import ScheduledTask


class Command(BaseCommand):
    help = "Set up default scheduled tasks"

    def handle(self, *args, **options):
        self.stdout.write("Setting up default scheduled tasks...")

        ScheduledTask.ensure_default_tasks()

        self.stdout.write(self.style.SUCCESS("Default scheduled tasks created successfully"))

        # List all tasks
        self.stdout.write("\nConfigured scheduled tasks:")
        for task in ScheduledTask.objects.all():
            status = "enabled" if task.enabled else "disabled"
            self.stdout.write(
                f"  - {task.name}: {task.get_schedule_type_display()} "
                f"({status}) - Next run: {task.next_run}"
            )
