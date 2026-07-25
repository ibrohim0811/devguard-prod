#!/bin/sh

# Xatolik bo'lsa skriptni to'xtatish
set -e

# manage.py joylashgan papkaga o'tamiz
cd /app/services/drf

# Agar biror alohida buyruq berilgan bo'lsa (masalan, docker-compose dagi `command: celery...`)
# o'sha buyruqni ishga tushiramiz:
if [ $# -gt 0 ]; then
    echo "⚡ Berilgan buyruq bajarilmoqda: $@"
    exec "$@"
fi

# Agar hech qanday buyruq berilmagan bo'lsa (default holatda Django server uchun):
echo "🗄️ Migratsiyalar bajarilmoqda..."
python manage.py migrate --noinput

echo "📦 Static fayllar yig'ilmoqda..."
python manage.py collectstatic --noinput

echo "🚀 Gunicorn HTTP server ishga tushirilmoqda..."
exec gunicorn devshield.wsgi:application --bind 0.0.0.0:8000 --workers "${GUNICORN_WORKERS:-3}" --access-logfile - --error-logfile -
