from django.urls import re_path
from users import consumers

websocket_urlpatterns = [
    re_path(r'^ws/scan/(?P<task_id>[\w-]+)/?$', consumers.ScanProgressConsumer.as_asgi()),
]