# Generated manually for ScheduledTask model
from django.db import migrations, models
import stator.models
import core.models.scheduled_task


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0002_domain_config"),
    ]

    operations = [
        migrations.CreateModel(
            name="ScheduledTask",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "state",
                    stator.models.StateField(
                        choices=[
                            ("pending", "pending"),
                            ("running", "running"),
                            ("completed", "completed"),
                            ("failed", "failed"),
                        ],
                        default="pending",
                        graph=core.models.scheduled_task.ScheduledTaskStates,
                        max_length=100,
                    ),
                ),
                ("state_changed", models.DateTimeField(auto_now_add=True)),
                ("state_next_attempt", models.DateTimeField(blank=True, null=True)),
                ("state_locked_until", models.DateTimeField(blank=True, null=True)),
                ("state_ready", models.BooleanField(default=True)),
                ("name", models.CharField(max_length=255, unique=True)),
                (
                    "task_type",
                    models.CharField(
                        choices=[
                            ("auto_delete_posts", "Auto-delete old posts"),
                            ("prune_posts", "Prune remote posts"),
                            ("prune_identities", "Prune remote identities"),
                            ("custom", "Custom task"),
                        ],
                        default="custom",
                        max_length=50,
                    ),
                ),
                ("description", models.TextField(blank=True)),
                (
                    "schedule_type",
                    models.CharField(
                        choices=[
                            ("daily", "Daily"),
                            ("weekly", "Weekly"),
                            ("hourly", "Hourly"),
                            ("custom", "Custom interval"),
                        ],
                        default="daily",
                        max_length=20,
                    ),
                ),
                (
                    "interval_seconds",
                    models.IntegerField(
                        default=86400,
                        help_text="Interval in seconds for custom schedules",
                    ),
                ),
                (
                    "run_time",
                    models.TimeField(
                        blank=True,
                        help_text="Specific time to run (for daily/weekly tasks)",
                        null=True,
                    ),
                ),
                (
                    "weekday",
                    models.IntegerField(
                        blank=True,
                        choices=[
                            (0, "Monday"),
                            (1, "Tuesday"),
                            (2, "Wednesday"),
                            (3, "Thursday"),
                            (4, "Friday"),
                            (5, "Saturday"),
                            (6, "Sunday"),
                        ],
                        help_text="Day of week (for weekly tasks)",
                        null=True,
                    ),
                ),
                ("next_run", models.DateTimeField(blank=True, null=True)),
                ("last_run", models.DateTimeField(blank=True, null=True)),
                ("run_count", models.IntegerField(default=0)),
                ("last_error", models.TextField(blank=True, null=True)),
                ("enabled", models.BooleanField(default=True)),
                ("created", models.DateTimeField(auto_now_add=True)),
                ("updated", models.DateTimeField(auto_now=True)),
            ],
            options={
                "abstract": False,
            },
        ),
    ]
