# ─────────────────────────────────────────
#   Stage 1: Builder (paketlarni o'rnatish)
# ─────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /app

# System dependencies (psycopg2-binary uchun)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
 && rm -rf /var/lib/apt/lists/*

# Pip upgrade + wheels build
COPY requirements.txt .
RUN pip install --upgrade pip \
 && pip install --no-cache-dir --prefix=/install -r requirements.txt


# ─────────────────────────────────────────
#   Stage 2: Production Image
# ─────────────────────────────────────────
FROM python:3.11-slim

WORKDIR /app

# Runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    wget \
 && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Application source
COPY . .

# entrypoint.sh ni executable qilamiz
RUN chmod +x entrypoint.sh

# Static va media papkalari
RUN mkdir -p /app/staticfiles /app/media

# Non-root user (xavfsizlik uchun)
RUN useradd --no-create-home --shell /bin/false appuser \
 && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

ENTRYPOINT ["./entrypoint.sh"]
