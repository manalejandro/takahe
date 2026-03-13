"""
Management command to fix remote posts left with empty content due to the
get_or_create race-prevention stub bug.

Two categories are addressed:
1. Stubs (url=None): created by get_or_create but never populated.
   → Delete them (cascades FanOut + TimelineEvent); InboxMessage will re-create.
2. content="" with url set, no attachments: stub fanned out before the guard.
   → Queue FetchPost with force_update=True so handle_fetch_internal re-fetches
     and calls by_ap(update=True) to refresh the content from the remote server.
   → Also delete any existing stale TimelineEvent entries for these posts so users
     stop seeing the empty placeholder while the refetch is in flight.
"""
from django.db import models
from django.core.management.base import BaseCommand

from activities.models import Post, PostStates
from activities.models.timeline_event import TimelineEvent
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
        # Deleting the Post also CASCADE-deletes its FanOut and TimelineEvent rows,
        # so empty entries disappear from all local timelines immediately.
        stubs = Post.objects.filter(local=False, url__isnull=True)
        stub_count = stubs.count()
        self.stdout.write(f"Stub posts (url=None, remote): {stub_count}")
        if stub_count:
            if not dry_run:
                stubs.delete()
            self.stdout.write(
                f"  {label}Deleted {stub_count} stub post(s) "
                "(FanOut + TimelineEvent cascaded; InboxMessage will re-create with content)"
            )

        # --- 2. Empty-content posts (url set, no attachments) ---------------
        # These are likely stubs that slipped through the guard before it was
        # deployed.  We:
        #   a) Remove their stale TimelineEvent entries right away so users no
        #      longer see empty placeholders.
        #   b) Queue a FetchPost with force_update=True so the content is
        #      refreshed from the remote server; once populated, handle_new /
        #      handle_edited will re-fan-out with real content.
        empty_fanned = (
            Post.objects.filter(
                local=False,
                content="",
                url__isnull=False,
                state__in=[PostStates.fanned_out, PostStates.new],
            )
            .annotate(att_count=models.Count("attachments"))
            .filter(att_count=0)
        )
        empty_count = empty_fanned.count()
        self.stdout.write(
            f"Remote empty-content posts with no attachments (fanned_out or new): {empty_count}"
        )
        fixed = 0
        for post in empty_fanned.only("pk", "object_uri", "state"):
            if not dry_run:
                # a) Remove stale timeline entries so the empty post disappears
                TimelineEvent.objects.filter(subject_post_id=post.pk).delete()
                # b) Force a re-fetch from the remote AP server
                InboxMessage.create_internal(
                    {
                        "type": "FetchPost",
                        "object": post.object_uri,
                        "force_update": True,
                    }
                )
                # Reset to new so handle_new fans it out after content is set
                Post.objects.filter(pk=post.pk).update(
                    state=PostStates.new,
                    state_next_attempt=None,
                )
            fixed += 1
        if empty_count:
            self.stdout.write(
                f"  {label}Removed stale timeline entries and queued "
                f"{fixed} force-refetch message(s)"
            )

        self.stdout.write(self.style.SUCCESS("Done."))
