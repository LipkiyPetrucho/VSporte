"""
WebSocket URL routing для games.
"""

from django.urls import path

from . import consumers

websocket_urlpatterns = [
    path(
        "ws/games/<int:game_id>/chat/",
        consumers.GameChatConsumer.as_asgi(),
    ),
]
