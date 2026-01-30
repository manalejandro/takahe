# Auto-Delete Posts Feature

This feature allows users to automatically delete their posts after a specified duration.

## Overview

The auto-delete functionality is configurable per identity and provides the following options:
- **Disabled** (default): Posts are never automatically deleted
- **1 Day**: Delete posts older than 1 day
- **1 Week**: Delete posts older than 7 days
- **1 Month**: Delete posts older than 30 days

## Implementation Details

### Database Changes

A new field `auto_delete_posts` has been added to the `Identity` model:
- Type: IntegerField with choices
- Default: 0 (Disabled)
- Choices: 0 (Disabled), 1 (1 Day), 7 (1 Week), 30 (1 Month)

### Automatic Deletion

Posts are automatically deleted through two mechanisms:

1. **Stator Integration**: The `PostStates.handle_fanned_out` method checks each local post's age against the author's auto-delete setting during its normal state transition cycle.

2. **Management Command**: A dedicated management command can be run manually or via cron job to batch-process deletions.

## Usage

### Management Command

Run the auto-delete command:

```bash
python manage.py auto_delete_posts
```

Options:
- `--dry-run`: Show what would be deleted without actually deleting anything
- `--identity username@domain`: Process only a specific identity

Examples:

```bash
# Dry run to see what would be deleted
python manage.py auto_delete_posts --dry-run

# Process only for a specific user
python manage.py auto_delete_posts --identity user@example.com

# Actually delete posts
python manage.py auto_delete_posts
```

### Scheduled Execution

To run this automatically, add a cron job:

```bash
# Run daily at 3 AM
0 3 * * * cd /path/to/takahe && /path/to/python manage.py auto_delete_posts
```

Or using a systemd timer (recommended for production):

Create `/etc/systemd/system/takahe-autodelete.service`:
```ini
[Unit]
Description=Takahe Auto-Delete Posts
After=network.target

[Service]
Type=oneshot
User=takahe
WorkingDirectory=/path/to/takahe
ExecStart=/path/to/python manage.py auto_delete_posts
```

Create `/etc/systemd/system/takahe-autodelete.timer`:
```ini
[Unit]
Description=Run Takahe auto-delete daily
Requires=takahe-autodelete.service

[Timer]
OnCalendar=daily
Persistent=true

[Install]
WantedBy=timers.target
```

Enable and start:
```bash
sudo systemctl enable takahe-autodelete.timer
sudo systemctl start takahe-autodelete.timer
```

### Configuring Auto-Delete per User

The setting can be configured in several ways:

#### 1. Django Admin

If you have Django admin enabled:
1. Go to `/admin/users/identity/`
2. Select the identity
3. Set the "Auto delete posts" field to the desired value
4. Save

#### 2. Django Shell

```python
from users.models.identity import Identity

# Find the identity
identity = Identity.objects.get(username="yourusername", domain__domain="example.com")

# Set auto-delete to 7 days (1 week)
identity.auto_delete_posts = Identity.AutoDeleteDuration.ONE_WEEK
identity.save()

# Or set to disabled
identity.auto_delete_posts = Identity.AutoDeleteDuration.DISABLED
identity.save()
```

#### 3. Database directly

```sql
-- Set to 7 days for a specific user
UPDATE users_identity 
SET auto_delete_posts = 7 
WHERE username = 'yourusername' AND domain_id = 'example.com';

-- Disable auto-delete
UPDATE users_identity 
SET auto_delete_posts = 0 
WHERE username = 'yourusername' AND domain_id = 'example.com';
```

## Migration

To apply the database changes, run:

```bash
python manage.py migrate users
```

## Notes

- Only local posts are affected by auto-delete settings
- Remote posts are handled separately by the existing REMOTE_PRUNE_HORIZON setting
- Posts are transitioned to the "deleted" state, which will properly fan out deletion notices to followers
- The published date (not created date) is used to determine post age
- Auto-delete is disabled by default for all users

## Security Considerations

- Only local identities can have auto-delete configured
- Users cannot accidentally delete posts from other users
- The feature respects the existing state machine and proper ActivityPub delete notifications

## Performance

- The stator integration checks posts during normal state transitions
- The management command uses efficient database queries with proper filtering
- Consider running the management command during off-peak hours for large instances
