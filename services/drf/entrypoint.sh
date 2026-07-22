#!/bin/bash
# services/drf/entrypoint.sh
set -e

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  DevShield — Django ASGI Startup"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

echo "🔄 [1/3] Ma'lumotlar bazasi migratsiyalari..."
python manage.py migrate --noinput

echo "📁 [2/3] Static fayllarni yig'ish..."
python manage.py collectstatic --noinput --clear

echo "🚀 [3/3] Daphne ASGI serverni ishga tushirish..."
exec daphne \
  -b 0.0.0.0 \
  -p 8000 \
  --access-log - \
  devshield.asgi:application
