#!/bin/bash

# IdeaHunter Start Script for Render Free Tier
# Runs both the API and the Scheduler in one container

echo "Starting IdeaHunter Scheduler in background..."
python -m backend.main &

echo "Starting IdeaHunter API via Gunicorn..."
# Gunicorn is the foreground process to keep the container running
gunicorn --bind 0.0.0.0:${PORT:-5000} --workers 2 --timeout 120 backend.api.routes:app
