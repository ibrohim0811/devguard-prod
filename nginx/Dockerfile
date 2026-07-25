FROM nginx:1.27-alpine

RUN sed -i '/http {/a \    server_tokens off;' /etc/nginx/nginx.conf

# ❌ ESKI: COPY nginx.conf /etc/nginx/conf.d/default.conf
# ✅ YANGI (Context '.' bo'lgani uchun aniq yo'l ko'rsatamiz):
COPY nginx.conf /etc/nginx/conf.d/default.conf

RUN apk add --no-cache openssl && \
    mkdir -p /etc/letsencrypt/live/api.devguard.uz && \
    openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout /etc/letsencrypt/live/api.devguard.uz/privkey.pem \
    -out /etc/letsencrypt/live/api.devguard.uz/fullchain.pem \
    -subj "/CN=api.devguard.uz"

# Static va media papkalari
RUN mkdir -p /app/staticfiles /app/media

EXPOSE 80 443