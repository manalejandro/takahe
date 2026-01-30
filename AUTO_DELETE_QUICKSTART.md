# Auto-Delete Posts - Quick Start Guide

## Installation
1. Apply the database migration:
   ```bash
   python manage.py migrate users
   ```

2. Verify the installation:
   ```bash
   python manage.py auto_delete_posts --dry-run
   ```

## Configuration

### For a Single User

Use the helper script:
```bash
# View current setting
python scripts/set_auto_delete.py user@example.com

# Enable auto-delete after 1 week
python scripts/set_auto_delete.py user@example.com 1week

# Disable auto-delete
python scripts/set_auto_delete.py user@example.com disabled
```

### Via Django Admin

1. Access Django admin: `/admin/`
2. Navigate to Users → Identities
3. Select the identity to configure
4. Set "Auto delete posts" field
5. Save

### Via Django Shell

```bash
python manage.py shell
```

```python
from users.models.identity import Identity

# Find user
identity = Identity.objects.get(username="yourname", domain__domain="example.com")

# Set to 1 week
identity.auto_delete_posts = 7
identity.save()
```

## Running Auto-Delete

### Manual Execution
```bash
# Preview what will be deleted
python manage.py auto_delete_posts --dry-run

# Actually delete the posts
python manage.py auto_delete_posts
```

### Automated Execution

#### Option 1: Cron Job
```bash
crontab -e
```

Add:
```
# Run daily at 3 AM
0 3 * * * cd /path/to/takahe && /path/to/venv/bin/python manage.py auto_delete_posts
```

#### Option 2: Systemd Timer (Recommended)

Create `/etc/systemd/system/takahe-autodelete.service`:
```ini
[Unit]
Description=Takahe Auto-Delete Posts
After=network.target

[Service]
Type=oneshot
User=takahe
WorkingDirectory=/path/to/takahe
Environment="PATH=/path/to/takahe/.venv/bin:/usr/local/bin:/usr/bin:/bin"
ExecStart=/path/to/takahe/.venv/bin/python manage.py auto_delete_posts
```

Create `/etc/systemd/system/takahe-autodelete.timer`:
```ini
[Unit]
Description=Run Takahe auto-delete daily

[Timer]
OnCalendar=daily
Persistent=true

[Install]
WantedBy=timers.target
```

Enable:
```bash
sudo systemctl daemon-reload
sudo systemctl enable takahe-autodelete.timer
sudo systemctl start takahe-autodelete.timer

# Check status
sudo systemctl status takahe-autodelete.timer
```

## Available Settings

- **Disabled** (default): No automatic deletion
- **1 Day**: Delete posts older than 24 hours
- **1 Week**: Delete posts older than 7 days
- **1 Month**: Delete posts older than 30 days

## Notes

- Only affects local posts (posts created by local users)
- Remote posts are handled by the REMOTE_PRUNE_HORIZON setting
- Deletions are properly federated to other instances
- Posts are deleted using the standard state machine (proper ActivityPub Delete activities are sent)

## Troubleshooting

### Check if migration was applied
```bash
python manage.py showmigrations users
```

### View current settings for all users
```bash
python manage.py shell
```
```python
from users.models.identity import Identity

for identity in Identity.objects.filter(local=True, auto_delete_posts__gt=0):
    print(f"{identity.handle}: {identity.get_auto_delete_posts_display()}")
```

### Test with a specific user
```bash
python manage.py auto_delete_posts --identity username@domain.com --dry-run
```
