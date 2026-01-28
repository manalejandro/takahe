#!/bin/bash
cd /home/ale/projects/activitypub/takahe
source .venv/bin/activate
set -a
source development.env
set +a
python manage.py runserver 0.0.0.0:8000
