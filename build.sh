#!/usr/bin/env bash
# Exit immediately on any error
set -o errexit

pip install -r requirements.txt
python manage.py collectstatic --no-input
python manage.py migrate
python manage.py createsu