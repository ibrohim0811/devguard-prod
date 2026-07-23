FROM nginx:1.27-alpine

# ─── Asosiy nginx konfiguratsiyasida server_tokens o'chirish ───
# Bu nginx versiyasini javob headerlaridan yashiradi
RUN sed -i '/http {/a \    server_tokens off;' /etc/nginx/nginx.conf

# Custom nginx konfiguratsiya
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Static va media papkalari (volume mount uchun)
RUN mkdir -p /app/staticfiles /app/media

EXPOSE 80 443
