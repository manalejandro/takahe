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

## ⚠️ IMPORTANT: Start the Stator Worker Process

**The Stator worker process MUST be running for scheduled tasks to execute automatically.**

The Stator process handles all background tasks including:
- Scheduled tasks (auto-delete, pruning)
- Post state transitions
- Federation activities
- All asynchronous processing

### Quick Start (Development)

```bash
./start_stator.sh
```

This starts the Stator worker in the foreground. Press Ctrl+C to stop.

### Alternative: Manual Start

```bash
python manage.py runstator
```

### Production Deployment

In production, Stator should run as a separate service/container:

**Docker/Heroku:** The Procfile already defines the worker:
```
worker: python manage.py runstator
```

Make sure to run a worker dyno/container.

**Systemd Service:**
```bash
sudo systemctl start takahe-worker
sudo systemctl status takahe-worker
```

### Verify Stator is Running

```bash
ps aux | grep runstator
```

If nothing is returned, Stator is NOT running and scheduled tasks will NOT execute.


## Configuration

### For a Single User

**Option 1: Using Django Management Command (Recommended)**
```bash
# View current setting
python manage.py set_auto_delete user@example.com

# Enable auto-delete after 1 week
python manage.py set_auto_delete user@example.com 1week

# Disable auto-delete
python manage.py set_auto_delete user@example.com disabled
```

**Option 2: Using Helper Script**
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

**PREREQUISITE:** The Stator worker process must be running. See the section above for how to start it.

#### Option 1: Using Takahe's Built-in Scheduled Tasks (Recommended)

Takahe has a built-in scheduled task system that uses the Stator process. **This is now the default and recommended method.**

1. **Verify the scheduled task exists**:
```bash
python manage.py shell -c "from core.models.scheduled_task import ScheduledTask; task = ScheduledTask.objects.filter(name='auto_delete_posts').first(); print(f'Task: {task.name if task else \"NOT FOUND\"}'); print(f'Enabled: {task.enabled if task else \"N/A\"}'); print(f'Next run: {task.next_run if task else \"N/A\"}')"
```

2. **If the task doesn't exist, create it**:
```bash
python manage.py setup_scheduled_tasks
```

3. **Ensure Stator is running** (it handles the scheduled tasks):
   - Run `./start_stator.sh` in development
   - In production, ensure the worker process/dyno/container is running
   - Verify: `ps aux | grep runstator`

4. **The task will run automatically** at the scheduled time (default: 3:00 AM daily)

5. **To manually enable/disable or adjust the schedule**:
```bash
python manage.py shell
```
```python
from core.models.scheduled_task import ScheduledTask
import datetime

task = ScheduledTask.objects.get(name='auto_delete_posts')

# Change run time (e.g., 2:30 AM)
task.run_time = datetime.time(2, 30)
task.calculate_next_run()
task.save()

# Disable the task
task.enabled = False
task.save()

# Re-enable
task.enabled = True
task.save()
```

#### Option 2: Cron Job (Alternative)
```bash
crontab -e
```

Add:
```
# Run daily at 3 AM
0 3 * * * cd /path/to/takahe && /path/to/venv/bin/python manage.py auto_delete_posts
```

#### Option 2: Systemd Timer

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

### Posts are not being deleted automatically

**Most common cause:** The Stator worker process is not running.

1. **Check if Stator is running**:
```bash
ps aux | grep runstator
```

If you see no results, Stator is NOT running.

2. **Start Stator**:
```bash
# In development:
./start_stator.sh

# Or directly:
python manage.py runstator
```

3. **Verify the scheduled task**:
```bash
python manage.py shell -c "from core.models.scheduled_task import ScheduledTask; task = ScheduledTask.objects.get(name='auto_delete_posts'); print(f'Enabled: {task.enabled}'); print(f'State: {task.state}'); print(f'Next run: {task.next_run}'); print(f'Last run: {task.last_run}'); print(f'Run count: {task.run_count}')"
```

4. **Check for locks** (if the task seems stuck):
```bash
python manage.py shell -c "from core.models.scheduled_task import ScheduledTask; task = ScheduledTask.objects.get(name='auto_delete_posts'); task.state_locked_until = None; task.save(); print('Lock cleared')"
```

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
