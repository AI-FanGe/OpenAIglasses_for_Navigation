#!/bin/bash

# We deliberately DO NOT use 'set -e' here so the server always tries to start
# even if a migration or initialization step fails. This makes debugging much easier.

echo "====================================="
echo "Starting AI Glass Backend Entrypoint"
echo "====================================="

echo "[1/4] Waiting for PostgreSQL at $DB_HOST:$DB_PORT..."
MAX_RETRIES=30
RETRY_COUNT=0
while ! nc -z $DB_HOST $DB_PORT; do
  sleep 1
  RETRY_COUNT=$((RETRY_COUNT+1))
  if [ $RETRY_COUNT -ge $MAX_RETRIES ]; then
      echo "Error: Database did not start in time. Continuing anyway..."
      break
  fi
done
echo "Database check complete."

echo "[2/4] Applying migrations..."
python manage.py makemigrations users devices || echo "makemigrations failed, moving on..."
python manage.py migrate || echo "migrate failed, moving on..."

echo "[3/4] Creating default users and generating tokens..."
python init_db.py || echo "init_db.py failed, moving on..."

echo "[4/4] Starting Django Server on 0.0.0.0:8000..."
echo "====================================="
exec python manage.py runserver 0.0.0.0:8000
