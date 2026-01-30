# Installation and Testing Checklist

## ✅ Pre-Installation Verification

- [x] Feature implemented in English
- [x] All Python files have valid syntax
- [x] Documentation created

## 📋 Installation Steps

### 1. Apply Database Migration
```bash
cd /home/ale/projects/activitypub/takahe
source .venv/bin/activate
python manage.py migrate users
```

**Expected output:**
```
Running migrations:
  Applying users.0023_identity_auto_delete_posts... OK
```

### 2. Verify Migration Applied
```bash
python manage.py showmigrations users
```

**Expected output should include:**
```
users
 [X] 0001_initial
 ...
 [X] 0022_follow_request
 [X] 0023_identity_auto_delete_posts
```

### 3. Test Management Command
```bash
python manage.py auto_delete_posts --dry-run
```

**Expected output:**
```
DRY RUN MODE - No posts will be deleted
Processing 0 identities with auto-delete enabled

Would delete 0 posts (dry run - nothing was actually deleted)
```

## 🧪 Feature Testing

### Test 1: Configure Auto-Delete for a User

**Option 1: Using Management Command (Recommended)**
```bash
# Replace with your actual username and domain
python manage.py set_auto_delete yourusername@yourdomain.com 1week
```

**Option 2: Using Helper Script**
```bash
# Replace with your actual username and domain
python scripts/set_auto_delete.py yourusername@yourdomain.com 1week
```

**Expected output:**
```
✓ Updated auto-delete setting for yourusername@yourdomain.com
  Changed from: Disabled
  Changed to:   1 Week

Note: Posts older than 1 week will be automatically deleted
Run: python manage.py auto_delete_posts --dry-run
     to see what posts would be deleted
```

### Test 2: View Current Setting
```bash
python manage.py set_auto_delete yourusername@yourdomain.com
# or
python scripts/set_auto_delete.py yourusername@yourdomain.com
```

**Expected output:**
```
Current auto-delete setting for yourusername@yourdomain.com: 1 Week

To change, use:
  python scripts/set_auto_delete.py yourusername@yourdomain.com [disabled|1day|1week|1month]
```

### Test 3: Run Dry-Run for Specific User
```bash
python manage.py auto_delete_posts --identity yourusername@yourdomain.com --dry-run
```

**Expected output:**
```
DRY RUN MODE - No posts will be deleted
Processing 1 identities with auto-delete enabled
  yourusername@yourdomain.com: X posts older than 1 Week (before YYYY-MM-DD)

Would delete X posts (dry run - nothing was actually deleted)
```

### Test 4: Verify via Django Shell
```bash
python manage.py shell
```

```python
from users.models.identity import Identity

# Check your user
identity = Identity.objects.get(username='yourusername', domain__domain='yourdomain.com')
print(f"Auto-delete setting: {identity.get_auto_delete_posts_display()}")
print(f"Value: {identity.auto_delete_posts} days")

# List all users with auto-delete enabled
for i in Identity.objects.filter(local=True, auto_delete_posts__gt=0):
    print(f"{i.handle}: {i.get_auto_delete_posts_display()}")
```

### Test 5: Django Admin Access
1. Access: http://your-takahe-domain/admin/
2. Log in with admin credentials
3. Navigate to: Users → Identities
4. Find a local identity and click it
5. Verify you can see and modify the "Auto delete posts" field

## 🔄 Setup Automated Execution

### Option A: Cron Job
```bash
# Edit crontab
crontab -e

# Add this line (runs daily at 3 AM)
0 3 * * * cd /home/ale/projects/activitypub/takahe && /home/ale/projects/activitypub/takahe/.venv/bin/python manage.py auto_delete_posts
```

### Option B: Systemd Timer (Recommended)

1. Create service file:
```bash
sudo nano /etc/systemd/system/takahe-autodelete.service
```

Paste:
```ini
[Unit]
Description=Takahe Auto-Delete Posts
After=network.target

[Service]
Type=oneshot
User=ale
WorkingDirectory=/home/ale/projects/activitypub/takahe
Environment="PATH=/home/ale/projects/activitypub/takahe/.venv/bin:/usr/local/bin:/usr/bin:/bin"
ExecStart=/home/ale/projects/activitypub/takahe/.venv/bin/python manage.py auto_delete_posts
StandardOutput=journal
StandardError=journal
```

2. Create timer file:
```bash
sudo nano /etc/systemd/system/takahe-autodelete.timer
```

Paste:
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

3. Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable takahe-autodelete.timer
sudo systemctl start takahe-autodelete.timer
```

4. Verify:
```bash
sudo systemctl status takahe-autodelete.timer
sudo systemctl list-timers | grep takahe
```

## 🔍 Troubleshooting

### Issue: Migration fails
```bash
# Check existing migrations
python manage.py showmigrations users

# If migration already exists or conflicts, you may need to:
# 1. Check database for existing column
python manage.py dbshell
# In db: \d users_identity (PostgreSQL) or DESC users_identity (MySQL)

# 2. Fake the migration if column already exists
python manage.py migrate users 0023_identity_auto_delete_posts --fake
```

### Issue: Command not found
```bash
# Ensure you're using the virtual environment
source /home/ale/projects/activitypub/takahe/.venv/bin/activate

# Or use full path
/home/ale/projects/activitypub/takahe/.venv/bin/python manage.py auto_delete_posts
```

### Issue: Import errors
```bash
# Verify all __init__.py files exist
ls -la activities/management/__init__.py
ls -la activities/management/commands/__init__.py

# If missing, create them:
touch activities/management/__init__.py
touch activities/management/commands/__init__.py
```

## ✅ Final Verification

After completing all steps, verify:

1. [ ] Migration applied successfully
2. [ ] Can view/modify auto-delete setting via helper script
3. [ ] Can view/modify auto-delete setting via Django admin
4. [ ] Management command runs without errors (dry-run)
5. [ ] Automated execution is configured (cron or timer)
6. [ ] Documentation is accessible

## 📚 Documentation Reference

- `AUTO_DELETE_QUICKSTART.md` - Quick start guide
- `AUTO_DELETE_POSTS.md` - Complete technical documentation  
- `IMPLEMENTATION_SUMMARY.md` - Implementation details

## 🚀 You're Ready!

The auto-delete feature is now fully implemented and ready to use. Users can:
- Configure their own auto-delete preferences
- Choose from: Disabled, 1 Day, 1 Week, or 1 Month retention
- Have posts automatically cleaned up based on their settings

The system will automatically process deletions daily (if configured), or you can run manually at any time with:
```bash
python manage.py auto_delete_posts
```
