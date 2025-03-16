#!/bin/sh

# Ждем, пока база данных будет доступна
echo "Waiting for database..."
while ! nc -z $DB_HOST 5432; do
    sleep 1
done
echo "Database is available"

# Проверяем, нужно ли выполнять миграции
python manage.py showmigrations --plan | grep -q "[ ]"
if [ $? -eq 0 ]; then
    echo "Running migrations..."
    python manage.py migrate
else
    echo "No migrations needed"
fi

# Запускаем сервер
echo "Starting server..."
python manage.py runserver 0.0.0.0:8000
