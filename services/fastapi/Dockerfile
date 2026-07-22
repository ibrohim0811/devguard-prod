# ─────────────────────────────────────────
#   FastAPI RabbitMQ Worker
#   Includes: nmap, nikto, dirb, sqlmap, nuclei
# ─────────────────────────────────────────
FROM python:3.11-slim

WORKDIR /app

# ─── Scan Tools o'rnatish ───────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
    nmap \
    nikto \
    dirb \
    sqlmap \
    wget \
    unzip \
    curl \
    ca-certificates \
 && rm -rf /var/lib/apt/lists/*

# ─── Nuclei (ProjectDiscovery) ──────────
# GitHub releases dan so'nggi versiyani yuklaymiz
RUN ARCH=$(uname -m) && \
    case "$ARCH" in \
      x86_64) NUCLEI_ARCH="amd64" ;; \
      aarch64) NUCLEI_ARCH="arm64" ;; \
      *) NUCLEI_ARCH="amd64" ;; \
    esac && \
    NUCLEI_VERSION=$(curl -s https://api.github.com/repos/projectdiscovery/nuclei/releases/latest \
      | grep '"tag_name"' | sed -E 's/.*"([^"]+)".*/\1/') && \
    wget -q "https://github.com/projectdiscovery/nuclei/releases/download/${NUCLEI_VERSION}/nuclei_${NUCLEI_VERSION#v}_linux_${NUCLEI_ARCH}.zip" \
      -O nuclei.zip && \
    unzip -q nuclei.zip nuclei && \
    mv nuclei /usr/local/bin/nuclei && \
    chmod +x /usr/local/bin/nuclei && \
    rm nuclei.zip

# ─── Python dependencies ────────────────
COPY requirements.txt .
RUN pip install --upgrade pip \
 && pip install --no-cache-dir -r requirements.txt

# ─── Application source ─────────────────
COPY . .

# Non-root user
RUN useradd --no-create-home --shell /bin/false appuser \
 && chown -R appuser:appuser /app

# Nuclei templates papkasi uchun ruxsat
RUN mkdir -p /home/appuser && chown appuser:appuser /home/appuser
USER appuser

CMD ["python", "main.py"]
