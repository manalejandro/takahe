# Auto-Delete Posts Feature - Implementation Summary

## Overview
Implemented automatic deletion of posts/statuses for Takahe ActivityPub instance with user-configurable retention periods.

## Features Implemented

### 1. Database Model Changes
- **File**: `users/models/identity.py`
- Added `auto_delete_posts` field to Identity model
- Choices: Disabled (0), 1 Day (1), 1 Week (7), 1 Month (30)
- Default: Disabled

### 2. Automatic Deletion Logic
- **File**: `activities/models/post.py`
- Modified `PostStates.handle_fanned_out()` method
- Checks post age against user's auto-delete setting
- Integrates with existing Stator state machine
- Properly transitions posts to deleted state for ActivityPub federation

### 3. Management Command
- **File**: `activities/management/commands/auto_delete_posts.py`
- Command: `python manage.py auto_delete_posts`
- Options:
  - `--dry-run`: Preview deletions without executing
  - `--identity`: Process specific user only
- Provides detailed output of what was deleted

### 4. Database Migration
- **File**: `users/migrations/0023_identity_auto_delete_posts.py`
- Adds the new field to the database schema

### 5. Django Admin Integration
- **File**: `users/admin.py`
- Custom admin interface for Identity model
- Easy configuration of auto-delete settings
- Organized fieldsets for better UX

### 6. Helper Script
- **File**: `scripts/set_auto_delete.py`
- Command-line tool for setting user preferences
- Usage: `python scripts/set_auto_delete.py user@domain.com [disabled|1day|1week|1month]`
- Shows current settings when run without setting parameter

### 7. Django Management Command (Recommended)
- **File**: `users/management/commands/set_auto_delete.py`
- More reliable Django management command
- Usage: `python manage.py set_auto_delete user@domain.com [disabled|1day|1week|1month]`
- Better error handling and integration with Django

### 8. Documentation
- **File**: `AUTO_DELETE_POSTS.md` - Complete technical documentation
- **File**: `AUTO_DELETE_QUICKSTART.md` - Quick start guide for users

## Usage Examples

### Enable auto-delete for a user
```bash
# Using management command (recommended)
python manage.py set_auto_delete alice@example.com 1week

# Using helper script
python scripts/set_auto_delete.py alice@example.com 1week

# Using Django shell
python manage.py shell -c "
from users.models.identity import Identity
i = Identity.objects.get(username='alice', domain__domain='example.com')
i.auto_delete_posts = 7
i.save()
"
```

### Run auto-delete
```bash
# Dry run to preview
python manage.py auto_delete_posts --dry-run

# Actually delete
python manage.py auto_delete_posts

# For specific user only
python manage.py auto_delete_posts --identity alice@example.com
```

### Setup automation
```bash
# Cron (daily at 3 AM)
echo "0 3 * * * cd /path/to/takahe && /path/to/venv/bin/python manage.py auto_delete_posts" | crontab -

# Or use systemd timer (see documentation)
```

## Technical Details

### How It Works
1. **Stator Integration**: During normal post state transitions in the `fanned_out` state, the system checks if:
   - Post is local
   - Author has auto-delete enabled
   - Post age exceeds the configured threshold
   - If all conditions met, post transitions to `deleted` state

2. **Management Command**: Batch processes all posts that meet deletion criteria:
   - Queries for identities with auto-delete enabled
   - Calculates cutoff date based on each user's setting
   - Finds posts older than cutoff
   - Transitions them to deleted state (proper ActivityPub federation)

3. **State Machine**: Uses existing PostStates.deleted transition:
   - Creates fan-out objects for deletion notices
   - Notifies followers on other instances
   - Properly federates the deletion

### Database Schema
```sql
ALTER TABLE users_identity 
ADD COLUMN auto_delete_posts INTEGER DEFAULT 0 
CHECK (auto_delete_posts IN (0, 1, 7, 30));
```

### Performance Considerations
- Efficient database queries with proper indexing
- Uses existing published date field (indexed)
- Batch processing in management command
- Integrates with existing Stator queue system

## Security & Safety
- Only affects local posts (user's own posts)
- Cannot delete other users' posts
- Disabled by default for all users
- Proper ActivityPub Delete activities sent
- Respects existing state machine and permissions

## Files Modified/Created

### Modified
1. `/home/ale/projects/activitypub/takahe/users/models/identity.py`
2. `/home/ale/projects/activitypub/takahe/activities/models/post.py`

### Created
1. `/home/ale/projects/activitypub/takahe/activities/management/`
2. `/home/ale/projects/activitypub/takahe/activities/management/commands/`
3. `/home/ale/projects/activitypub/takahe/activities/management/commands/auto_delete_posts.py`
4. `/home/ale/projects/activitypub/takahe/users/migrations/0023_identity_auto_delete_posts.py`
5. `/home/ale/projects/activitypub/takahe/users/admin.py`
6. `/home/ale/projects/activitypub/takahe/users/management/commands/set_auto_delete.py`
7. `/home/ale/projects/activitypub/takahe/scripts/set_auto_delete.py`
8. `/home/ale/projects/activitypub/takahe/AUTO_DELETE_POSTS.md`
9. `/home/ale/projects/activitypub/takahe/AUTO_DELETE_QUICKSTART.md`
10. `/home/ale/projects/activitypub/takahe/IMPLEMENTATION_SUMMARY.md` (this file)

## Next Steps

1. **Apply the migration**:
   ```bash
   python manage.py migrate users
   ```

2. **Test the feature**:
   ```bash
   # Set auto-delete for a test user
   python scripts/set_auto_delete.py testuser@yourdomain.com 1day
   
   # Preview what would be deleted
   python manage.py auto_delete_posts --dry-run
   ```

3. **Setup automation**:
   - Choose between cron or systemd timer
   - Configure to run daily during off-peak hours

4. **Monitor**:
   - Check logs after first runs
   - Verify ActivityPub Delete activities are being sent
   - Confirm posts are being removed as expected

## Language Implementation
- ✅ Implemented in English as requested
- All user-facing messages in English
- Code comments in English
- Documentation in English
