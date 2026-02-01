#!/bin/bash

# Setup script for new features
# Run this after pulling the new code

set -e

echo "==================================="
echo "Takahe New Features Setup"
echo "==================================="
echo ""

# Check if in virtualenv
if [ -z "$VIRTUAL_ENV" ]; then
    if [ -f ".venv/bin/activate" ]; then
        echo "Activating virtual environment..."
        source .venv/bin/activate
    else
        echo "Warning: Virtual environment not found. Make sure Python dependencies are available."
    fi
fi

echo "Step 1: Applying database migrations..."
python manage.py migrate users
python manage.py migrate core

echo ""
echo "Step 2: Setting up scheduled tasks..."
python manage.py setup_scheduled_tasks

echo ""
echo "==================================="
echo "Setup Complete!"
echo "==================================="
echo ""
echo "New features available:"
echo "  - Full Lists API implementation"
echo "  - Mutes and Blocks endpoints"
echo "  - User-level domain blocking"
echo "  - Account endorsements (pinning accounts)"
echo "  - Timeline position markers"
echo "  - Private account notes"
echo "  - Reports endpoint"
echo "  - Scheduled task system for auto-delete posts"
echo ""
echo "Next steps:"
echo "  1. Ensure Stator is running to process scheduled tasks:"
echo "     python manage.py runstator"
echo ""
echo "  2. Configure auto-delete for users (optional):"
echo "     python manage.py set_auto_delete user@domain.com 1week"
echo ""
echo "  3. View scheduled tasks in Django admin:"
echo "     /admin/core/scheduledtask/"
echo ""
echo "See NEW_FEATURES_IMPLEMENTATION.md for detailed documentation."
echo ""
