#!/bin/sh

# Migratsiya va static fayllar
python manage.py migrate --noinput
python manage.py collectstatic --noinput

# ❌ ESKI (Gunicorn - Faqat HTTP):
# exec gunicorn devshield.wsgi:application --bind 0.0.0.0:8000

# ✅ YANGI (Daphne - HTTP + WebSocket):
exec daphne -b 0.0.0.0 -p 8000 devshield.asgi:application