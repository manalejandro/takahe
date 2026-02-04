import datetime
import logging
from typing import ClassVar

from django.core.management import call_command
from django.db import models
from django.utils import timezone

from stator.models import State, StateField, StateGraph, StatorModel

logger = logging.getLogger(__name__)


class ScheduledTaskStates(StateGraph):
    """
    State graph for scheduled tasks that need to run periodically.
    """

    pending = State(try_interval=60 * 60, force_initial=True)  # Check every hour
    running = State(externally_progressed=True)
    completed = State(externally_progressed=True)
    failed = State(externally_progressed=True)

    pending.transitions_to(running)
    running.transitions_to(completed)
    running.transitions_to(failed)
    completed.transitions_to(pending)
    failed.transitions_to(pending)

    # Reset to pending after completion
    completed.times_out_to(pending, seconds=1)
    failed.times_out_to(pending, seconds=60 * 10)  # Retry failed tasks after 10 minutes

    @classmethod
    def handle_pending(cls, instance: "ScheduledTask"):
        """
        Check if the task should run based on its schedule.
        """
        now = timezone.now()

        # Check if it's time to run
        if instance.next_run and instance.next_run <= now:
            return cls.running

    @classmethod
    def handle_running(cls, instance: "ScheduledTask"):
        """
        Execute the scheduled task.
        """
        try:
            logger.info(f"Running scheduled task: {instance.name}")

            # Execute the task based on its type
            if instance.task_type == ScheduledTask.TaskType.AUTO_DELETE_POSTS:
                call_command("auto_delete_posts")
            elif instance.task_type == ScheduledTask.TaskType.PRUNE_POSTS:
                call_command("pruneposts")
            elif instance.task_type == ScheduledTask.TaskType.PRUNE_IDENTITIES:
                call_command("pruneidentities")
            else:
                logger.warning(f"Unknown task type: {instance.task_type}")

            # Update next run time
            instance.last_run = timezone.now()
            instance.calculate_next_run()
            instance.run_count += 1
            instance.save()

            logger.info(f"Scheduled task completed: {instance.name}")
            return cls.completed

        except Exception as e:
            logger.error(f"Error running scheduled task {instance.name}: {str(e)}")
            instance.last_error = str(e)
            instance.save()
            return cls.failed


class ScheduledTask(StatorModel):
    """
    Represents a scheduled task that runs periodically using the stator system.
    """

    class TaskType(models.TextChoices):
        AUTO_DELETE_POSTS = "auto_delete_posts", "Auto-delete old posts"
        PRUNE_POSTS = "prune_posts", "Prune remote posts"
        PRUNE_IDENTITIES = "prune_identities", "Prune remote identities"
        CUSTOM = "custom", "Custom task"

    class ScheduleType(models.TextChoices):
        DAILY = "daily", "Daily"
        WEEKLY = "weekly", "Weekly"
        HOURLY = "hourly", "Hourly"
        CUSTOM = "custom", "Custom interval"

    state = StateField(ScheduledTaskStates)

    # Task identification
    name = models.CharField(max_length=255, unique=True)
    task_type = models.CharField(
        max_length=50,
        choices=TaskType.choices,
        default=TaskType.CUSTOM,
    )
    description = models.TextField(blank=True)

    # Scheduling
    schedule_type = models.CharField(
        max_length=20,
        choices=ScheduleType.choices,
        default=ScheduleType.DAILY,
    )
    interval_seconds = models.IntegerField(
        default=86400,  # 24 hours
        help_text="Interval in seconds for custom schedules",
    )
    run_time = models.TimeField(
        null=True,
        blank=True,
        help_text="Specific time to run (for daily/weekly tasks)",
    )
    weekday = models.IntegerField(
        null=True,
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
    )

    # Execution tracking
    next_run = models.DateTimeField(null=True, blank=True)
    last_run = models.DateTimeField(null=True, blank=True)
    run_count = models.IntegerField(default=0)
    last_error = models.TextField(blank=True, null=True)

    # Status
    enabled = models.BooleanField(default=True)

    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        indexes: ClassVar = []

    def __str__(self):
        return f"{self.name} ({self.get_schedule_type_display()})"

    def calculate_next_run(self):
        """
        Calculate the next run time based on the schedule type.
        """
        now = timezone.now()

        if self.schedule_type == self.ScheduleType.HOURLY:
            self.next_run = now + datetime.timedelta(hours=1)

        elif self.schedule_type == self.ScheduleType.DAILY:
            # Run at specific time each day
            if self.run_time:
                next_run = now.replace(
                    hour=self.run_time.hour,
                    minute=self.run_time.minute,
                    second=0,
                    microsecond=0,
                )
                if next_run <= now:
                    next_run += datetime.timedelta(days=1)
                self.next_run = next_run
            else:
                self.next_run = now + datetime.timedelta(days=1)

        elif self.schedule_type == self.ScheduleType.WEEKLY:
            # Run at specific time on specific weekday
            days_ahead = self.weekday - now.weekday()
            if days_ahead <= 0:  # Target day already passed this week
                days_ahead += 7
            next_run = now + datetime.timedelta(days=days_ahead)
            if self.run_time:
                next_run = next_run.replace(
                    hour=self.run_time.hour,
                    minute=self.run_time.minute,
                    second=0,
                    microsecond=0,
                )
            self.next_run = next_run

        elif self.schedule_type == self.ScheduleType.CUSTOM:
            self.next_run = now + datetime.timedelta(seconds=self.interval_seconds)

    def save(self, *args, **kwargs):
        # Calculate next run if it's not set
        if not self.next_run:
            self.calculate_next_run()
        super().save(*args, **kwargs)

    @classmethod
    def ensure_default_tasks(cls):
        """
        Ensure default scheduled tasks exist in the database.
        """
        # Auto-delete posts task (daily at 3 AM)
        cls.objects.get_or_create(
            name="auto_delete_posts",
            defaults={
                "task_type": cls.TaskType.AUTO_DELETE_POSTS,
                "description": "Automatically delete old posts based on user settings",
                "schedule_type": cls.ScheduleType.DAILY,
                "run_time": datetime.time(3, 0),
                "enabled": True,
                "state_ready": True,
                "state": "pending",
            },
        )

        # Prune remote posts task (daily at 4 AM)
        cls.objects.get_or_create(
            name="prune_remote_posts",
            defaults={
                "task_type": cls.TaskType.PRUNE_POSTS,
                "description": "Prune old remote posts",
                "schedule_type": cls.ScheduleType.DAILY,
                "run_time": datetime.time(4, 0),
                "enabled": False,  # Disabled by default
                "state_ready": True,
                "state": "pending",
            },
        )
