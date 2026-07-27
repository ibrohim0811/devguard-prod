FROM python:3.11-slim-bookworm

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

WORKDIR /app

# 1. Tizim paketlari, dos2unix va zaruriy utilitalarni o'rnatish
RUN apt-get update && apt-get install -y --no-install-recommends \
    nmap \
    sqlmap \
    wget \
    curl \
    unzip \
    git \
    perl \
    libnet-ssleay-perl \
    ca-certificates \
    build-essential \
    libpq-dev \
    dos2unix \
 && rm -rf /var/lib/apt/lists/*

# 2. Nikto'ni GitHub'dan o'rnatish va tizimga symlink qilish
RUN git clone --depth=1 https://github.com/sullo/nikto.git /opt/nikto \
 && ln -s /opt/nikto/program/nikto.pl /usr/local/bin/nikto \
 && chmod +x /usr/local/bin/nikto

# 3. Nuclei binarini yuklab olish va o'rnatish
RUN NUCLEI_VERSION=$(curl -s https://api.github.com/repos/projectdiscovery/nuclei/releases/latest | grep '"tag_name":' | sed -E 's/.*"v([^"]+)".*/\1/') \
 && curl -sL "https://github.com/projectdiscovery/nuclei/releases/download/v${NUCLEI_VERSION}/nuclei_${NUCLEI_VERSION}_linux_amd64.zip" -o /tmp/nuclei.zip \
 && unzip /tmp/nuclei.zip -d /usr/local/bin nuclei \
 && chmod +x /usr/local/bin/nuclei \
 && rm /tmp/nuclei.zip

# 4. Requirements o'rnatish
COPY services/fastapi/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# 5. Loyiha kodini ko'chirish
COPY . .

# 6. Skriptlarga bajarish huquqini berish va Windows CRLF formatini Linux LF formatiga o'tkazish
RUN if [ -d "scripts" ]; then \
        chmod +x scripts/*.sh && \
        dos2unix scripts/*.sh ; \
    fi

# 7. Worker'ni ishga tushirish
CMD ["python", "services/fastapi/main.py"]