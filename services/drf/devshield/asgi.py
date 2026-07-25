import os
from django.core.asgi import get_asgi_application

# 1. Django sozlamalarini ko'rsatamiz
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'devshield.settings')

# 2. Django ASGI ilovasini yuklaymiz (BOSHQA IMPORTLARDAN OLDIN!)
django_asgi_app = get_asgi_application()

# 3. Importlarni get_asgi_application() dan KEYIN qilamiz
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
import users.routing  # users app ichidagi routing.py

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": AuthMiddlewareStack(
        URLRouter(
            users.routing.websocket_urlpatterns
        )
    ),
})