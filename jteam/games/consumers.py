"""
WebSocket consumer чата игры.

Контракт JSON:
  inbound:  {"type": "chat.message", "text": "..."}
  outbound: {"type": "chat.message", "id", "text", "created_at", "author", "is_own"}
  errors:   {"type": "error", "message": "..."}  (сокет не закрываем)
"""

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer

from notifications.services import notify_game_chat_message

from .models import Game, GameMessage
from .views import _serialize_chat_message

MAX_MESSAGE_LENGTH = 2000


class GameChatConsumer(AsyncJsonWebsocketConsumer):
    """Realtime-чат: участники/организатор → группа game_chat_{id}."""

    async def connect(self):
        self.game_id = self.scope["url_route"]["kwargs"]["game_id"]
        self.group_name = f"game_chat_{self.game_id}"
        self.user = self.scope["user"]

        if not self.user.is_authenticated:
            await self.close()
            return

        game = await self._get_game()
        if game is None or not await self._user_can_access(game):
            await self.close()
            return

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(
                self.group_name, self.channel_name
            )

    async def receive_json(self, content, **kwargs):
        if content.get("type") != "chat.message":
            await self.send_json(
                {"type": "error", "message": "Неизвестный тип события"}
            )
            return

        text = (content.get("text") or "").strip()
        if not text:
            await self.send_json(
                {"type": "error", "message": "Сообщение не может быть пустым"}
            )
            return
        if len(text) > MAX_MESSAGE_LENGTH:
            await self.send_json(
                {
                    "type": "error",
                    "message": f"Сообщение длиннее {MAX_MESSAGE_LENGTH} символов",
                }
            )
            return

        # Повторная проверка доступа на случай исключения из игры после connect.
        game = await self._get_game()
        if game is None or not await self._user_can_access(game):
            await self.send_json(
                {"type": "error", "message": "Нет доступа к чату этой игры"}
            )
            return

        message_payload = await self._create_and_serialize(text)
        await self.channel_layer.group_send(
            self.group_name,
            {
                "type": "chat.message",
                "message": message_payload,
            },
        )

    async def chat_message(self, event):
        """Handlers group_send → рассылка payload клиенту."""
        payload = event["message"]
        # is_own зависит от получателя: пересчитываем на стороне consumer.
        author = payload.get("author") or {}
        is_own = (
            self.user.is_authenticated
            and author.get("id") == self.user.pk
        )
        await self.send_json({
            "type": "chat.message",
            **payload,
            "is_own": is_own,
        })

    @database_sync_to_async
    def _get_game(self):
        try:
            return Game.objects.get(pk=self.game_id)
        except Game.DoesNotExist:
            return None

    @database_sync_to_async
    def _user_can_access(self, game):
        return game.user_can_access_chat(self.user)

    @database_sync_to_async
    def _create_and_serialize(self, text):
        message = GameMessage.objects.create(
            game_id=self.game_id,
            author=self.user,
            text=text,
        )
        # Подтягиваем author/profile/game для фото и уведомлений.
        message = (
            GameMessage.objects.select_related(
                "author",
                "author__profile",
                "game",
                "game__user",
                "game__user__profile",
            )
            .prefetch_related("game__joined_players__profile")
            .get(pk=message.pk)
        )
        notify_game_chat_message(message)
        # is_own в group_send не фиксируем — chat_message пересчитает для каждого.
        return _serialize_chat_message(message, current_user=None)
