# Data migration to create default scheduled tasks
from django.db import migrations


def create_default_tasks(apps, schema_editor):
    """Create default scheduled tasks."""
    ScheduledTask = apps.get_model("core", "ScheduledTask")
    
    # Import datetime here to ensure it's available
    import datetime
    
    # Auto-delete posts task (daily at 3 AM)
    task1, _ = ScheduledTask.objects.get_or_create(
        name="auto_delete_posts",
        defaults={
            "task_type": "auto_delete_posts",
            "description": "Automatically delete old posts based on user settings",
            "schedule_type": "daily",
            "run_time": datetime.time(3, 0),
            "enabled": True,
        },
    )
    
    # Prune remote posts task (daily at 4 AM)
    task2, _ = ScheduledTask.objects.get_or_create(
        name="prune_remote_posts",
        defaults={
            "task_type": "prune_posts",
            "description": "Prune old remote posts",
            "schedule_type": "daily",
            "run_time": datetime.time(4, 0),
            "enabled": False,  # Disabled by default
        },
    )
    
    # Trigger save() to calculate next_run for both tasks
    # This is needed because calculate_next_run() is called in save()
    task1.save()
    task2.save()


def remove_default_tasks(apps, schema_editor):
    """Remove default scheduled tasks if migration is reversed."""
    ScheduledTask = apps.get_model("core", "ScheduledTask")
    ScheduledTask.objects.filter(
        name__in=["auto_delete_posts", "prune_remote_posts"]
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0004_scheduledtask"),
    ]

    operations = [
        migrations.RunPython(create_default_tasks, remove_default_tasks),
    ]
