#!/bin/sh

# Exception yuzaga kelsa skriptni to'xtatish
set -e

# manage.py joylashgan papkaga o'tamiz
cd /app/services/drf

echo "🗄️ Migratsiyalar bajarilmoqda..."
python manage.py migrate --noinput

echo "📦 Static fayllar yig'ilmoqda..."
python manage.py collectstatic --noinput

echo "🚀 Daphne server ishga tushirilmoqda..."
exec daphne -b 0.0.0.0 -p 8000 devshield.asgi:application