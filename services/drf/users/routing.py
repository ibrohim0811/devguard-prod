from django.urls import path, re_path
from users import consumers

websocket_urlpatterns = [
    path('ws/scan/<str:task_id>/', consumers.ScanProgressConsumer.as_asgi()),
    path('ws/scan/<str:task_id>', consumers.ScanProgressConsumer.as_asgi()),
    re_path(r'^/?ws/scan/(?P<task_id>[a-zA-Z0-9-]+)/?$', consumers.ScanProgressConsumer.as_asgi()),
]