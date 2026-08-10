from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models


class Notification(models.Model):
    TYPE_FRIENDSHIP_REQUEST = "friendship_request"
    TYPE_FRIENDSHIP_ACCEPTED = "friendship_accepted"
    TYPE_GAME_PARTICIPATION_REQUEST = "game_participation_request"
    TYPE_GAME_INVITATION = "game_invitation"
    TYPE_GAME_PARTICIPATION_ACCEPTED = "game_participation_accepted"
    TYPE_GAME_PARTICIPATION_REJECTED = "game_participation_rejected"
    TYPE_GAME_PLAYER_REMOVED = "game_player_removed"
    TYPE_CHAT_MESSAGE = "chat_message"
    TYPE_GAME_UPDATED = "game_updated"
    TYPE_GROUP_JOIN_REQUEST = "group_join_request"
    TYPE_GROUP_INVITATION = "group_invitation"
    TYPE_GROUP_JOIN_ACCEPTED = "group_join_accepted"
    TYPE_GROUP_JOIN_REJECTED = "group_join_rejected"
    TYPE_GROUP_MEMBER_REMOVED = "group_member_removed"

    TYPE_CHOICES = (
        (TYPE_FRIENDSHIP_REQUEST, "Заявка в друзья"),
        (TYPE_FRIENDSHIP_ACCEPTED, "Заявка в друзья принята"),
        (TYPE_GAME_PARTICIPATION_REQUEST, "Заявка на участие в игре"),
        (TYPE_GAME_INVITATION, "Приглашение на игру"),
        (TYPE_GAME_PARTICIPATION_ACCEPTED, "Заявка на участие принята"),
        (TYPE_GAME_PARTICIPATION_REJECTED, "Заявка на участие отклонена"),
        (TYPE_GAME_PLAYER_REMOVED, "Исключение из мероприятия"),
        (TYPE_CHAT_MESSAGE, "Сообщение в чате игры"),
        (TYPE_GAME_UPDATED, "Изменение условий игры"),
        (TYPE_GROUP_JOIN_REQUEST, "Заявка на вступление в группу"),
        (TYPE_GROUP_INVITATION, "Приглашение в группу"),
        (TYPE_GROUP_JOIN_ACCEPTED, "Заявка на вступление принята"),
        (TYPE_GROUP_JOIN_REJECTED, "Заявка на вступление отклонена"),
        (TYPE_GROUP_MEMBER_REMOVED, "Исключение из группы"),
    )

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="notifications",
        on_delete=models.CASCADE,
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="notifications_sent",
        on_delete=models.CASCADE,
    )
    notification_type = models.CharField(max_length=50, choices=TYPE_CHOICES)
    target_ct = models.ForeignKey(
        ContentType,
        related_name="notification_targets",
        on_delete=models.CASCADE,
    )
    target_id = models.PositiveIntegerField()
    target = GenericForeignKey("target_ct", "target_id")
    read_at = models.DateTimeField(null=True, blank=True)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["recipient", "-created"]),
            models.Index(fields=["recipient", "read_at"]),
        ]
        ordering = ["-created"]

    def __str__(self):
        return f"{self.notification_type} → {self.recipient}"

    @property
    def is_read(self):
        return self.read_at is not None
