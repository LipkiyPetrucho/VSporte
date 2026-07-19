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

# Запускаем сервер
echo "Starting server..."
exec gunicorn jteam.wsgi:application \
     --bind 0.0.0.0:8000 \
     --workers 3
