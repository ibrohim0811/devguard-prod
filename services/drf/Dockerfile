# ─────────────────────────────────────────
#   Stage 1: Builder (paketlarni o'rnatish)
# ─────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /app

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
 && rm -rf /var/lib/apt/lists/*

# Pip upgrade + requirements.txt
COPY services/drf/requirements.txt ./requirements.txt
RUN pip install --upgrade pip \
 && pip install --no-cache-dir --prefix=/install -r requirements.txt


# ─────────────────────────────────────────
#   Stage 2: Production Image
# ─────────────────────────────────────────
FROM python:3.12-slim

WORKDIR /app

# Environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/services/drf:/app

# Runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    wget \
 && rm -rf /var/lib/apt/lists/*

# Builder bosqichidan paketlarni ko'chirib olish
COPY --from=builder /install /usr/local

# Loyihaning barcha fayllarini ko'chirish
COPY . .

# Static, media va appuser uy papkalarini yaratish
RUN mkdir -p /app/staticfiles /app/media /home/appuser

# entrypoint.sh ga ijro huquqini berish
RUN chmod +x /app/services/drf/entrypoint.sh

# Non-root user yaratish va barcha ruxsatlarni bir martada berish
RUN useradd -m -d /home/appuser --shell /bin/false appuser \
 && chown -R appuser:appuser /app /home/appuser

USER appuser

EXPOSE 8000

ENTRYPOINT ["/app/services/drf/entrypoint.sh"]