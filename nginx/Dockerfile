FROM nginx:1.27-alpine

RUN sed -i '/http {/a \    server_tokens off;' /etc/nginx/nginx.conf

# ❌ ESKI: COPY nginx.conf /etc/nginx/conf.d/default.conf
# ✅ YANGI (Context '.' bo'lgani uchun aniq yo'l ko'rsatamiz):
COPY nginx/nginx.conf /etc/nginx/conf.d/default.conf

# Static va media papkalari
RUN mkdir -p /app/staticfiles /app/media

EXPOSE 80 443