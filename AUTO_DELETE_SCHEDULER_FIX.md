# Auto-Delete Scheduler Fix

## Issues Found and Fixed

### 1. **CRITICAL: Python 3.13 Compatibility Issue** ✅ FIXED

**Problem**: The StateGraph class in `stator/graph.py` was incompatible with Python 3.13, which adds new special attributes like `__firstlineno__` to classes. The validation code rejected these attributes, causing the entire application to crash.

**Error**:
```
ValueError: Graph has item __firstlineno__ of unallowed type <class 'int'>
```

**Fix Applied**: Modified `/home/ale/projects/activitypub/takahe/stator/graph.py` to skip all dunder attributes (`__name__`, `__firstlineno__`, etc.) instead of hardcoding specific ones.

**Changed**:
```python
# Before - only skipped specific attributes
if name in ["__module__", "__doc__", "states"]:
    pass

# After - skips all dunder attributes
if name.startswith("__") and name.endswith("__"):
    pass
elif name in ["states"]:
    pass
```

This fix ensures compatibility with Python 3.13 and future Python versions that may add more dunder attributes.

---

### 2. **Database Connection Issue** (Needs Your Attention)

**Problem**: The PostgreSQL database server is not running on port 5433.

**Error**:
```
connection to server at "127.0.0.1", port 5433 failed: Connection refused
```

**To Fix**: Start your PostgreSQL database server before running Django commands:
```bash
# If using Docker
docker-compose -f docker/docker-compose.yml up -d

# Or if using local PostgreSQL, ensure it's running
sudo systemctl start postgresql
```

---

## Next Steps to Verify Scheduler Setup

Once the database is running, check if the scheduled task exists:

```bash
# Load environment and check task status
set -a && source development.env && set +a
/home/ale/projects/activitypub/takahe/.venv/bin/python manage.py shell -c "
from core.models.scheduled_task import ScheduledTask
task = ScheduledTask.objects.filter(name='auto_delete_posts').first()
if task:
    print(f'✅ Task exists: {task.name}')
    print(f'   Enabled: {task.enabled}')
    print(f'   State: {task.state}')
    print(f'   State Ready: {task.state_ready}')
    print(f'   Next run: {task.next_run}')
    print(f'   Last run: {task.last_run}')
    print(f'   Run count: {task.run_count}')
    print(f'   Last error: {task.last_error}')
else:
    print('❌ Task does not exist - run setup command')
"
```

---

## Common Reasons Why Scheduler Doesn't Fire

### 1. Task Not Created
**Check**: Run the setup command
```bash
/home/ale/projects/activitypub/takahe/.venv/bin/python manage.py setup_scheduled_tasks
```

### 2. Task Disabled
**Check**: Verify `enabled = True` in the database
**Fix**: Enable via Django shell:
```python
from core.models.scheduled_task import ScheduledTask
task = ScheduledTask.objects.get(name='auto_delete_posts')
task.enabled = True
task.save()
```

### 3. `state_ready = False`
**Problem**: The task is locked or waiting
**Fix**: Reset state:
```python
from core.models.scheduled_task import ScheduledTask
from django.utils import timezone
task = ScheduledTask.objects.get(name='auto_delete_posts')
task.state = 'pending'
task.state_ready = True
task.state_locked_until = None
task.next_run = timezone.now()  # Run immediately
task.save()
```

### 4. Stator Not Running
**Problem**: The Stator process handles scheduled tasks and must be running
**Check**: Verify Stator is in your process list:
```bash
ps aux | grep stator
```

**Fix**: Start Stator based on your deployment:

**Development**:
```bash
/home/ale/projects/activitypub/takahe/.venv/bin/python manage.py runstator
```

**Production with systemd**:
```bash
sudo systemctl status takahe-stator
sudo systemctl start takahe-stator
```

**Production with Docker**:
```bash
docker-compose ps  # Check if stator container is running
docker-compose up -d stator  # Start if not running
```

### 5. `next_run` in the Future
**Problem**: The scheduler will only fire when `next_run <= now()`
**Check**: Look at the `next_run` value
**Fix**: Force immediate run:
```python
from core.models.scheduled_task import ScheduledTask
from django.utils import timezone
task = ScheduledTask.objects.get(name='auto_delete_posts')
task.next_run = timezone.now()
task.save()
```

### 6. No Users Configured for Auto-Delete
**Problem**: Even if the scheduler fires, no posts will be deleted if no users have auto-delete enabled
**Check**: See who has auto-delete configured:
```bash
/home/ale/projects/activitypub/takahe/.venv/bin/python manage.py shell -c "
from users.models.identity import Identity
users = Identity.objects.filter(local=True, auto_delete_posts__gt=0)
if users:
    print('Users with auto-delete enabled:')
    for u in users:
        print(f'  - {u.handle}: {u.get_auto_delete_posts_display()}')
else:
    print('No users have auto-delete enabled')
"
```

**Enable for a user**:
```bash
/home/ale/projects/activitypub/takahe/.venv/bin/python manage.py set_auto_delete user@example.com 1week
```

---

## Testing the Scheduler

### Test Manually
Force a task run to test it works:
```bash
/home/ale/projects/activitypub/takahe/.venv/bin/python manage.py auto_delete_posts --dry-run
```

### Monitor Stator Logs
Watch for scheduled task execution:
```bash
# If running directly
/home/ale/projects/activitypub/takahe/.venv/bin/python manage.py runstator

# If using systemd
sudo journalctl -u takahe-stator -f

# If using Docker
docker-compose logs -f stator
```

Look for log messages like:
```
Running scheduled task: auto_delete_posts
Scheduled task completed: auto_delete_posts
```

---

## Summary

✅ **Fixed**: Python 3.13 compatibility issue in stator/graph.py
🔴 **Action Required**: Start PostgreSQL database server
⏭️ **Next**: Verify scheduled task setup and ensure Stator process is running

The scheduler system is now functional from a code perspective. The remaining issue is ensuring:
1. Database is running
2. Scheduled task exists in the database
3. Stator process is running to execute scheduled tasks
