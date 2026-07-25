from django.urls import re_path
from users import consumers  # yoki o'zingizning consumer joylashgan faylingiz

websocket_urlpatterns = [
    # [\w-]+ orqali harflar, raqamlar va '-' (UUID) belgilari ham qamrab olinadi:
    re_path(r'^ws/scan/(?P<task_id>[\w-]+)/?$', consumers.ScanProgressConsumer.as_asgi()),
]