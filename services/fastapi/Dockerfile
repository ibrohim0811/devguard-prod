FROM python:3.11-slim

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

WORKDIR /app

# Skanerlash va tizim vositalarini o'rnatish
RUN apt-get update && apt-get install -y --no-install-recommends \
    nmap \
    sqlmap \
    nikto \
    dirb \
    wget \
    curl \
    unzip \
    git \
    ca-certificates \
    build-essential \
    libpq-dev \
 && rm -rf /var/lib/apt/lists/*

# Nuclei binarini o'rnatish
RUN curl -sL https://github.com/projectdiscovery/nuclei/releases/download/v3.3.7/nuclei_3.3.7_linux_amd64.zip -o /tmp/nuclei.zip \
 && unzip /tmp/nuclei.zip -d /usr/local/bin nuclei \
 && chmod +x /usr/local/bin/nuclei \
 && rm /tmp/nuclei.zip

# Aniq ko'rsatilgan yo'l bo'yicha requirements o'rnatish
COPY services/fastapi/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Butun loyiha kodini ko'chirish
COPY . .

# Worker'ni ishga tushirish (agar faylingiz services/fastapi/main.py bo'lsa)
CMD ["python", "services/fastapi/main.py"]