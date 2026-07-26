#!/bin/sh
set -e

# Ждем, пока база данных будет доступна
echo "Waiting for database..."
while ! nc -z "$DB_HOST" 5432; do
    sleep 1
done
echo "Database is available"

echo "Running migrations..."
python manage.py migrate --noinput

# ASGI-сервер: HTTP + WebSocket (Channels). gunicorn/wsgi больше не используем.
echo "Starting Daphne (ASGI)..."
exec daphne -b 0.0.0.0 -p 8000 jteam.asgi:application
