"""
ASGI config for jteam project.

HTTP — обычный Django ASGI; WebSocket — Channels (AuthMiddlewareStack + URLRouter).
Точка входа продакшена: daphne jteam.asgi:application (см. entrypoint.sh).
"""

import os

from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator
from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "jteam.settings")

# Django ASGI app нужно инициализировать до импорта routing/consumers (модели).
django_asgi_app = get_asgi_application()

from games.routing import websocket_urlpatterns  # noqa: E402

application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        "websocket": AllowedHostsOriginValidator(
            AuthMiddlewareStack(URLRouter(websocket_urlpatterns))
        ),
    }
)
