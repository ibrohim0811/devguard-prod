FROM nginx:1.27-alpine

# Custom nginx config
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Static va media papkalari (volume mount uchun)
RUN mkdir -p /app/staticfiles /app/media

EXPOSE 80
