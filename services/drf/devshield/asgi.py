import os
from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'devshield.settings')

# 1. Django HTTP application
django_asgi_app = get_asgi_application()

# 2. Routing va Channels importlari
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from channels.security.websocket import AllowedHostsOriginValidator
import users.routing  # 👈 users.routing import qilinganiga e'tibor bering

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": AllowedHostsOriginValidator(
        AuthMiddlewareStack(
            URLRouter(
                users.routing.websocket_urlpatterns  # 👈 Mana shu joyda ulangan bo'lishi shart
            )
        )
    ),
})