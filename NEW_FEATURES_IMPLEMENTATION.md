# New Features Implementation Summary

## Overview

This implementation adds several missing Mastodon API v1 endpoints and a scheduled task system for automatic post deletion.

## New Features

### 1. Complete API Endpoints

#### Mutes and Blocks
- **GET /api/v1/mutes** - List muted accounts
- **GET /api/v1/blocks** - List blocked accounts
- **GET /api/v1/domain_blocks** - List blocked domains (stub for future implementation)
- **POST /api/v1/domain_blocks** - Block a domain (stub)
- **DELETE /api/v1/domain_blocks** - Unblock a domain (stub)

#### Account Management
- **GET /api/v1/endorsements** - List endorsed accounts (stub)
- **POST /api/v1/accounts/:id/note** - Add private note to account (stub)
- **GET /api/v1/accounts/:id/lists** - Get lists containing account

#### Reports
- **POST /api/v1/reports** - Create a report (fully functional)

#### Scheduled Statuses
- **GET /api/v1/scheduled_statuses** - List scheduled  statuses (stub)
- **GET /api/v1/scheduled_statuses/:id** - Get scheduled status (stub)
- **PUT /api/v1/scheduled_statuses/:id** - Update scheduled status (stub)
- **DELETE /api/v1/scheduled_statuses/:id** - Delete scheduled status (stub)

#### Markers (Timeline Position Tracking)
- **GET /api/v1/markers** - Get timeline markers (stub)
- **POST /api/v1/markers** - Save timeline markers (stub)

#### Lists (Fully Implemented)
- **GET /api/v1/lists** - Get all lists
- **POST /api/v1/lists** - Create a new list
- **GET /api/v1/lists/:id** - Get a specific list
- **PUT /api/v1/lists/:id** - Update a list
- **DELETE /api/v1/lists/:id** - Delete a list
- **GET /api/v1/lists/:id/accounts** - Get accounts in a list
- **POST /api/v1/lists/:id/accounts** - Add accounts to a list
- **DELETE /api/v1/lists/:id/accounts** - Remove accounts from a list
- **GET /api/v1/timelines/list/:id** - Get timeline for a list

### 2. Scheduled Task System

A new scheduled task system integrated with Stator for running periodic maintenance tasks:

#### Features
- **Database-driven scheduling** - Tasks are stored in the database
- **Stator integration** - Uses the existing Stator state machine for reliable execution
- **Multiple schedule types** - Hourly, daily, weekly, or custom intervals
- **Task tracking** - Monitors execution count, last run time, and errors
- **Flexible configuration** - Can be enabled/disabled per task

#### Available Tasks
- **Auto-delete posts** - Automatically delete old posts based on user settings (runs daily at 3 AM by default)
- **Prune remote posts** - Remove old remote posts (disabled by default)
- **Prune remote identities** - Clean up stale remote identities (disabled by default)

## Installation & Setup

### 1. Apply Database Migrations

```bash
python manage.py migrate users
python manage.py migrate core
```

### 2. Set Up Scheduled Tasks

```bash
python manage.py setup_scheduled_tasks
```

This will create default scheduled tasks in the database.

### 3. Ensure Stator is Running

The scheduled tasks run through Stator, so make sure you have Stator running:

```bash
python manage.py runstator
```

Or in production, ensure your Stator service/process includes the `core.ScheduledTask` model:

```bash
python manage.py runstator core.ScheduledTask
```

## Usage

### Managing Lists via API

Example using curl:

```bash
# Create a list
curl -X POST https://your-instance.com/api/v1/lists \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d "title=My Friends" \
  -d "replies_policy=followed"

# Add accounts to list
curl -X POST https://your-instance.com/api/v1/lists/1/accounts \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d "account_ids[]=123" \
  -d "account_ids[]=456"

# Get list timeline
curl https://your-instance.com/api/v1/timelines/list/1 \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Managing Scheduled Tasks

#### Via Django Admin

1. Access `/admin/core/scheduledtask/`
2. View and modify scheduled tasks
3. Enable/disable tasks
4. View execution history

#### Via Django Shell

```python
from core.models import ScheduledTask

# List all tasks
for task in ScheduledTask.objects.all():
    print(f"{task.name}: {task.enabled} - Next run: {task.next_run}")

# Disable a task
task = ScheduledTask.objects.get(name="auto_delete_posts")
task.enabled = False
task.save()

# Change schedule
task = ScheduledTask.objects.get(name="auto_delete_posts")
task.schedule_type = ScheduledTask.ScheduleType.WEEKLY
task.weekday = 0  # Monday
task.run_time = "04:00:00"
task.save()
```

### Auto-Delete Posts Configuration

The auto-delete functionality is already implemented (see AUTO_DELETE_POSTS.md for details). The new scheduled task system automates its execution:

1. **Configure per-user settings** - Set `auto_delete_posts` field on Identity model
2. **Let Stator handle it** - The scheduled task runs daily automatically
3. **Monitor execution** - Check the ScheduledTask record for last run time and errors

## Technical Details

### New Models

#### users.List
- Represents a user-created list of accounts
- Fields: owner, title, replies_policy
- Supports different reply visibility policies

#### users.ListMember
- Many-to-many relationship between lists and identities
- Tracks when accounts were added to lists

#### core.ScheduledTask
- Stator-based model for scheduled tasks
- States: pending, running, completed, failed
- Automatically calculates next run time based on schedule type

### Files Created

```
api/views/mutes.py              - Mutes endpoint
api/views/blocks.py             - Blocks endpoint
api/views/domain_blocks.py      - Domain blocks endpoints (stubs)
api/views/endorsements.py       - Endorsements endpoint (stub)
api/views/reports.py            - Reports endpoint
api/views/scheduled_statuses.py - Scheduled statuses endpoints (stubs)
api/views/markers.py            - Markers endpoints (stubs)
users/models/list.py            - List and ListMember models
core/models/scheduled_task.py   - ScheduledTask model
core/management/commands/setup_scheduled_tasks.py - Setup command
users/migrations/0024_add_lists.py - Lists migration
core/migrations/0004_scheduledtask.py - ScheduledTask migration
```

### Files Modified

```
api/urls.py                     - Added all new endpoint routes
api/views/lists.py              - Implemented full CRUD for lists
api/views/timelines.py          - Added list timeline endpoint
api/views/accounts.py           - Added note and lists endpoints
users/models/__init__.py        - Exported List and ListMember
core/models/__init__.py         - Exported ScheduledTask
```

## Compatibility

All endpoints follow the Mastodon API specification. Stubbed endpoints return appropriate empty responses or 404 errors for API compatibility while features are being developed.

## Performance Considerations

- **Lists** - Indexed on owner and creation time for fast queries
- **List members** - Indexed on list and identity for efficient lookups
- **Scheduled tasks** - Run during Stator's normal operation cycle
- **Auto-delete** - Processes posts in batches to avoid memory issues

## Future Enhancements

Stubbed endpoints can be fully implemented in the future:
- User-level domain blocking
- Account endorsements/pinning
- Scheduled post publishing
- Timeline position markers
- Account notes

## Troubleshooting

### Scheduled tasks not running

1. Check if Stator is running: `ps aux | grep runstator`
2. Verify task is enabled: `python manage.py setup_scheduled_tasks`
3. Check for errors: Query the ScheduledTask model for `last_error` field

### Lists not showing in timeline

1. Verify list ownership
2. Check that accounts are actually in the list
3. Ensure followed accounts are posting content

### API endpoints returning errors

1. Verify migrations are applied
2. Check authentication scopes
3. Review server logs for detailed error messages

## Support

For issues or questions:
- Check the AUTO_DELETE_POSTS.md for auto-delete details
- Review Django admin for task execution history
- Check Stator logs for task processing information
