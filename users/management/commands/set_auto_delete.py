"""
Django management command to configure auto-delete settings for user identities.
"""
from django.core.management.base import BaseCommand, CommandError

from users.models.identity import Identity


class Command(BaseCommand):
    help = "Configure auto-delete settings for an identity"

    def add_arguments(self, parser):
        parser.add_argument(
            "handle",
            type=str,
            help="Identity handle (username@domain.com)",
        )
        parser.add_argument(
            "setting",
            type=str,
            nargs="?",
            choices=["disabled", "1day", "1week", "1month"],
            help="Auto-delete setting (disabled|1day|1week|1month)",
        )

    def handle(self, *args, **options):
        handle = options["handle"]
        setting = options.get("setting")

        # Parse the handle
        try:
            username, domain = handle.split("@")
        except ValueError:
            raise CommandError(f"Invalid handle format: {handle}. Use: username@domain.com")

        # Find the identity
        try:
            identity = Identity.objects.get(
                username=username,
                domain__domain=domain,
                local=True
            )
        except Identity.DoesNotExist:
            raise CommandError(f"Identity '{handle}' not found or is not a local identity")

        # If no setting provided, show current setting
        if setting is None:
            current = dict(Identity.AutoDeleteDuration.choices)[identity.auto_delete_posts]
            self.stdout.write(self.style.SUCCESS(f"Current auto-delete setting for {handle}: {current}"))
            self.stdout.write("\nTo change, use:")
            self.stdout.write(f"  python manage.py set_auto_delete {handle} [disabled|1day|1week|1month]")
            return

        # Map setting names to values
        setting_map = {
            "disabled": Identity.AutoDeleteDuration.DISABLED,
            "1day": Identity.AutoDeleteDuration.ONE_DAY,
            "1week": Identity.AutoDeleteDuration.ONE_WEEK,
            "1month": Identity.AutoDeleteDuration.ONE_MONTH,
        }

        # Update the setting
        old_value = dict(Identity.AutoDeleteDuration.choices)[identity.auto_delete_posts]
        identity.auto_delete_posts = setting_map[setting]
        identity.save()
        new_value = dict(Identity.AutoDeleteDuration.choices)[identity.auto_delete_posts]

        self.stdout.write(self.style.SUCCESS(f"✓ Updated auto-delete setting for {handle}"))
        self.stdout.write(f"  Changed from: {old_value}")
        self.stdout.write(f"  Changed to:   {new_value}")
        
        if identity.auto_delete_posts > 0:
            self.stdout.write(
                self.style.WARNING(
                    f"\nNote: Posts older than {new_value.lower()} will be automatically deleted"
                )
            )
            self.stdout.write("Run: python manage.py auto_delete_posts --dry-run")
            self.stdout.write("     to see what posts would be deleted")
