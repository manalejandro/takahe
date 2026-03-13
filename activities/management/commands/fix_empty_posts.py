"""
Management command to fix remote posts left with empty content due to the
get_or_create race-prevention stub bug.

Two categories are addressed:
1. Stubs (url=None): created by get_or_create but never populated.
   → Delete them; they'll be re-created when the pending InboxMessage retries.
2. content="" with url set: stub was fanned out before the guard in handle_new
   was added.  Re-queue a FetchPost so the content gets refreshed.
"""
from django.core.management.base import BaseCommand

from activities.models import Post, PostStates
from users.models import InboxMessage


class Command(BaseCommand):
    help = "Fix remote posts with empty content caused by stub race condition"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            default=False,
            help="Show what would be done without making changes",
        )

    def handle(self, dry_run: bool, *args, **options):
        label = "[DRY RUN] " if dry_run else ""

        # --- 1. Stubs: url=None, remote, any state --------------------------
        stubs = Post.objects.filter(local=False, url__isnull=True)
        stub_count = stubs.count()
        self.stdout.write(f"Stub posts (url=None, remote): {stub_count}")
        if stub_count:
            if not dry_run:
                stubs.delete()
            self.stdout.write(
                f"  {label}Deleted {stub_count} stub post(s) "
                "(InboxMessage will re-create them with proper content)"
            )

        # --- 2. Empty-content posts that were already fanned out ------------
        empty_fanned = Post.objects.filter(
            local=False,
            content="",
            url__isnull=False,
            state__in=[PostStates.fanned_out, PostStates.new],
        )
        empty_count = empty_fanned.count()
        self.stdout.write(
            f"Remote posts with empty content (fanned_out or new): {empty_count}"
        )
        queued = 0
        for post in empty_fanned.only("pk", "object_uri", "state"):
            if not dry_run:
                # Re-queue a FetchPost so by_ap runs again with update=True
                InboxMessage.create_internal(
                    {
                        "type": "FetchPost",
                        "object": post.object_uri,
                        "reason": "fix_empty_posts management command",
                    }
                )
                # Reset to new so handle_new runs again once content is set
                Post.objects.filter(pk=post.pk).update(state=PostStates.new)
            queued += 1
        if empty_count:
            self.stdout.write(
                f"  {label}Queued {queued} FetchPost message(s) to re-populate content"
            )

        self.stdout.write(self.style.SUCCESS("Done."))
