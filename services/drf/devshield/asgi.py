import os
from django.core.asgi import get_asgi_application

# 1. Django settings moduli o'rnatiladi
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'devshield.settings')

# 2. Django ilovasi initialize qilinadi (IMPORTLARDAN OLDIN!)
django_asgi_app = get_asgi_application()

# 3. Muhit tayyor bo'lgach, Channels va routing import qilinadi
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
import users.routing

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": AuthMiddlewareStack(
        URLRouter(
            users.routing.websocket_urlpatterns
        )
    ),
})