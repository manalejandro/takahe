#!/usr/bin/env python
"""
Helper script to configure auto-delete settings for user identities.

Usage:
    python set_auto_delete.py username@domain.com [disabled|1day|1week|1month]
"""
import os
import sys
import django

# Set up Django environment
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "takahe.settings")
django.setup()

from users.models.identity import Identity


def main():
    if len(sys.argv) < 2:
        print("Usage: python set_auto_delete.py username@domain.com [disabled|1day|1week|1month]")
        print("\nAvailable options:")
        print("  disabled - Disable auto-delete (default)")
        print("  1day     - Delete posts older than 1 day")
        print("  1week    - Delete posts older than 1 week")
        print("  1month   - Delete posts older than 1 month")
        sys.exit(1)

    handle = sys.argv[1]
    setting = sys.argv[2].lower() if len(sys.argv) > 2 else None

    # Parse the handle
    try:
        username, domain = handle.split("@")
    except ValueError:
        print(f"Error: Invalid handle format. Use: username@domain.com")
        sys.exit(1)

    # Find the identity
    try:
        identity = Identity.objects.get(
            username=username,
            domain__domain=domain,
            local=True
        )
    except Identity.DoesNotExist:
        print(f"Error: Identity '{handle}' not found or is not a local identity")
        sys.exit(1)

    # If no setting provided, show current setting
    if setting is None:
        current = dict(Identity.AutoDeleteDuration.choices)[identity.auto_delete_posts]
        print(f"Current auto-delete setting for {handle}: {current}")
        print("\nTo change, use:")
        print(f"  python set_auto_delete.py {handle} [disabled|1day|1week|1month]")
        return

    # Map setting names to values
    setting_map = {
        "disabled": Identity.AutoDeleteDuration.DISABLED,
        "1day": Identity.AutoDeleteDuration.ONE_DAY,
        "1week": Identity.AutoDeleteDuration.ONE_WEEK,
        "1month": Identity.AutoDeleteDuration.ONE_MONTH,
    }

    if setting not in setting_map:
        print(f"Error: Invalid setting '{setting}'")
        print("Valid options: disabled, 1day, 1week, 1month")
        sys.exit(1)

    # Update the setting
    old_value = dict(Identity.AutoDeleteDuration.choices)[identity.auto_delete_posts]
    identity.auto_delete_posts = setting_map[setting]
    identity.save()
    new_value = dict(Identity.AutoDeleteDuration.choices)[identity.auto_delete_posts]

    print(f"✓ Updated auto-delete setting for {handle}")
    print(f"  Changed from: {old_value}")
    print(f"  Changed to:   {new_value}")
    
    if identity.auto_delete_posts > 0:
        print(f"\nNote: Posts older than {new_value.lower()} will be automatically deleted")
        print("Run: python manage.py auto_delete_posts --dry-run")
        print("     to see what posts would be deleted")


if __name__ == "__main__":
    main()
