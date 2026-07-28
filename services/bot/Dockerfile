FROM python:3.11-slim

WORKDIR /app

# Tizim paketlarini o'rnatamiz
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    build-essential \
    libpq-dev \
 && rm -rf /var/lib/apt/lists/*

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# ❌ ESKI: COPY bot/requirements.txt ./requirements.txt
# ✅ YANGI (Aniq yo'l):
COPY services/bot/requirements.txt ./requirements.txt

RUN pip install --upgrade pip \
 && pip install --no-cache-dir -r requirements.txt

COPY . .

# Non-root user
RUN useradd --no-create-home --shell /bin/false appuser \
 && chown -R appuser:appuser /app
USER appuser

# Botni ishga tushirish (papkani to'g'ri ko'rsatish)
CMD python -m http.server $PORT & python services/bot/main.py