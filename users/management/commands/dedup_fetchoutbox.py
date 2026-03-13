from django.core.management.base import BaseCommand
from django.db.models import Count, Min


class Command(BaseCommand):
    help = "Removes duplicate pending FetchOutbox InboxMessages, keeping one per identity"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be deleted without actually deleting",
        )

    def handle(self, dry_run: bool, *args, **options):
        from users.models import InboxMessage

        pending = InboxMessage.objects.filter(
            state="received",
            message__type="__internal__",
            message__object__type="FetchOutbox",
        )

        total = pending.count()
        self.stdout.write(f"Total pending FetchOutbox messages: {total}")

        # Find identities with duplicates
        dupes = (
            pending.values("message__object__identity")
            .annotate(cnt=Count("id"), keep_id=Min("id"))
            .filter(cnt__gt=1)
        )

        total_to_delete = 0
        for row in dupes:
            identity_pk = row["message__object__identity"]
            keep_id = row["keep_id"]
            cnt = row["cnt"]
            to_delete = cnt - 1
            total_to_delete += to_delete
            self.stdout.write(
                f"  identity={identity_pk}: {cnt} messages, keeping id={keep_id}, deleting {to_delete}"
            )
            if not dry_run:
                InboxMessage.objects.filter(
                    state="received",
                    message__object__type="FetchOutbox",
                    message__object__identity=str(identity_pk),
                ).exclude(id=keep_id).delete()

        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f"DRY RUN: would delete {total_to_delete} duplicate messages"
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(f"Deleted {total_to_delete} duplicate messages")
            )
