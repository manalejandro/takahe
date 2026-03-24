import datetime
import logging
from typing import cast

from django.apps import apps
from django.core.management.base import BaseCommand
from django.db import models
from django.utils import timezone

from stator.models import StatorModel

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Prunes stale pending Stator tasks (cleans expired locks and removes stuck tasks)"

    def add_arguments(self, parser):
        parser.add_argument(
            "model_labels",
            nargs="*",
            type=str,
            help="Optional list of model labels (e.g. users.inboxmessage) to limit pruning to",
        )
        parser.add_argument(
            "--older-than",
            "-o",
            type=int,
            default=None,
            metavar="DAYS",
            help=(
                "Delete tasks that have been stuck in a non-terminal state for more "
                "than DAYS days (default: only clean locks, do not delete)"
            ),
        )
        parser.add_argument(
            "--dry-run",
            "-n",
            action="store_true",
            default=False,
            help="Show what would be done without making any changes",
        )
        parser.add_argument(
            "--exclude",
            "-x",
            type=str,
            action="append",
            metavar="MODEL_LABEL",
            help="Model labels to exclude from pruning",
        )

    def handle(
        self,
        model_labels: list[str],
        older_than: int | None,
        dry_run: bool,
        exclude: list[str] | None,
        *args,
        **options,
    ):
        logging.basicConfig(
            format="[%(asctime)s] %(levelname)8s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
            level=logging.INFO,
            force=True,
        )

        # Resolve model list
        if model_labels:
            selected_models = cast(
                list[type[StatorModel]],
                [apps.get_model(label) for label in model_labels],
            )
        else:
            selected_models = list(StatorModel.subclasses)

        excluded_models = cast(
            list[type[StatorModel]],
            [apps.get_model(label) for label in (exclude or [])],
        )
        selected_models = [m for m in selected_models if m not in excluded_models]

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN — no changes will be made\n"))

        total_locks_cleaned = 0
        total_tasks_deleted = 0

        for model in selected_models:
            label = model._meta.label_lower
            automatic_states = model.state_graph.automatic_states

            if not automatic_states:
                continue

            # --- 1. Count & clean expired locks ---
            stale_lock_qs = model.objects.filter(
                state_locked_until__lte=timezone.now(),
                state__in=automatic_states,
            )
            stale_count = stale_lock_qs.count()

            if stale_count:
                if dry_run:
                    self.stdout.write(
                        f"  {label}: would release {stale_count} expired lock(s)"
                    )
                else:
                    stale_lock_qs.update(state_locked_until=None)
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"  {label}: released {stale_count} expired lock(s)"
                        )
                    )
                total_locks_cleaned += stale_count

            # --- 2. Optionally delete tasks stuck too long ---
            if older_than is not None:
                cutoff = timezone.now() - datetime.timedelta(days=older_than)
                stuck_qs = model.objects.filter(
                    state__in=automatic_states,
                    state_changed__lte=cutoff,
                )
                stuck_count = stuck_qs.count()

                if stuck_count:
                    if dry_run:
                        self.stdout.write(
                            f"  {label}: would delete {stuck_count} task(s) stuck for >{older_than}d"
                        )
                    else:
                        deleted, _ = stuck_qs.delete()
                        self.stdout.write(
                            self.style.SUCCESS(
                                f"  {label}: deleted {deleted} task(s) stuck for >{older_than}d"
                            )
                        )
                    total_tasks_deleted += stuck_count

        # --- Summary ---
        self.stdout.write("")
        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f"DRY RUN summary: {total_locks_cleaned} lock(s) to release, "
                    f"{total_tasks_deleted} task(s) to delete"
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Done: {total_locks_cleaned} lock(s) released, "
                    f"{total_tasks_deleted} task(s) deleted"
                )
            )
