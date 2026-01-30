"""
Management command to automatically delete posts based on user settings.
"""
import datetime

from django.core.management.base import BaseCommand
from django.utils import timezone

from activities.models.post import Post, PostStates
from users.models.identity import Identity


class Command(BaseCommand):
    help = "Automatically delete posts older than the configured duration for each user"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be deleted without actually deleting",
        )
        parser.add_argument(
            "--identity",
            type=str,
            help="Only process posts for a specific identity (username@domain)",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        identity_filter = options.get("identity")

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN MODE - No posts will be deleted"))

        # Get identities with auto-delete enabled
        identities = Identity.objects.filter(
            local=True,
            auto_delete_posts__gt=0,
        ).exclude(
            state__in=["deleted", "deleted_fanned_out"]
        )

        if identity_filter:
            identities = identities.filter(username=identity_filter.split("@")[0])

        total_deleted = 0
        total_identities = identities.count()

        self.stdout.write(
            self.style.SUCCESS(f"Processing {total_identities} identities with auto-delete enabled")
        )

        for identity in identities:
            # Calculate the cutoff date based on the user's setting
            days = identity.auto_delete_posts
            cutoff_date = timezone.now() - datetime.timedelta(days=days)

            # Find posts to delete
            posts_to_delete = Post.objects.filter(
                author=identity,
                local=True,
                published__lt=cutoff_date,
            ).exclude(
                state__in=[PostStates.deleted, PostStates.deleted_fanned_out]
            )

            count = posts_to_delete.count()

            if count > 0:
                setting_name = dict(Identity.AutoDeleteDuration.choices)[
                    identity.auto_delete_posts
                ]
                self.stdout.write(
                    f"  {identity.handle}: {count} posts older than {setting_name} (before {cutoff_date.date()})"
                )

                if not dry_run:
                    # Transition each post to deleted state
                    for post in posts_to_delete:
                        try:
                            post.transition_perform(PostStates.deleted)
                            total_deleted += 1
                        except Exception as e:
                            self.stderr.write(
                                self.style.ERROR(
                                    f"    Error deleting post {post.id}: {str(e)}"
                                )
                            )
                else:
                    total_deleted += count

        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f"\nWould delete {total_deleted} posts (dry run - nothing was actually deleted)"
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"\nSuccessfully deleted {total_deleted} posts"
                )
            )
