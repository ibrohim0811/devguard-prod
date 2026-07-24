FROM python:3.11-slim

WORKDIR /app

# Tizim paketlarini (PostgreSQL va C compilation uchun) o'rnatamiz
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    build-essential \
    libpq-dev \
 && rm -rf /var/lib/apt/lists/*

# Environment o'zgaruvchilari (Keshlamaslik va Python Yo'lini ko'rsatish)
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

COPY bot/requirements.txt ./requirements.txt
RUN pip install --upgrade pip \
 && pip install --no-cache-dir -r requirements.txt

COPY . .

# Non-root user (Xavfsizlik uchun)
RUN useradd --no-create-home --shell /bin/false appuser \
 && chown -R appuser:appuser /app
USER appuser

# Botni ishga tushirish (agar bot main.py bot papkasi ichida bo'lsa)
CMD ["python", "bot/main.py"]