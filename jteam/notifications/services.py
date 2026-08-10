import datetime

from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from django.utils import timezone

from .models import Notification

FRIENDSHIP_NOTIFICATION_TYPES = {
    Notification.TYPE_FRIENDSHIP_REQUEST,
    Notification.TYPE_FRIENDSHIP_ACCEPTED,
}

GAME_NOTIFICATION_TYPES = {
    Notification.TYPE_GAME_PARTICIPATION_REQUEST,
    Notification.TYPE_GAME_INVITATION,
    Notification.TYPE_GAME_PARTICIPATION_ACCEPTED,
    Notification.TYPE_GAME_PARTICIPATION_REJECTED,
    Notification.TYPE_GAME_PLAYER_REMOVED,
    Notification.TYPE_CHAT_MESSAGE,
    Notification.TYPE_GAME_UPDATED,
}

GROUP_NOTIFICATION_TYPES = {
    Notification.TYPE_GROUP_JOIN_REQUEST,
    Notification.TYPE_GROUP_INVITATION,
    Notification.TYPE_GROUP_JOIN_ACCEPTED,
    Notification.TYPE_GROUP_JOIN_REJECTED,
    Notification.TYPE_GROUP_MEMBER_REMOVED,
}

# Категории настроек → существующие типы in-app уведомлений.
# Напоминания об играх пока без бэкенда-источника.
NOTIFICATION_TYPE_PREF_FIELD = {
    Notification.TYPE_FRIENDSHIP_REQUEST: "notify_social_updates",
    Notification.TYPE_FRIENDSHIP_ACCEPTED: "notify_social_updates",
    Notification.TYPE_GROUP_JOIN_REQUEST: "notify_social_updates",
    Notification.TYPE_GROUP_INVITATION: "notify_social_updates",
    Notification.TYPE_GROUP_JOIN_ACCEPTED: "notify_social_updates",
    Notification.TYPE_GROUP_JOIN_REJECTED: "notify_social_updates",
    Notification.TYPE_GROUP_MEMBER_REMOVED: "notify_social_updates",
    Notification.TYPE_GAME_PARTICIPATION_REQUEST: "notify_activity_updates",
    Notification.TYPE_GAME_INVITATION: "notify_activity_updates",
    Notification.TYPE_GAME_PARTICIPATION_ACCEPTED: "notify_activity_updates",
    Notification.TYPE_GAME_PARTICIPATION_REJECTED: "notify_activity_updates",
    Notification.TYPE_GAME_PLAYER_REMOVED: "notify_activity_updates",
    Notification.TYPE_CHAT_MESSAGE: "notify_chat_messages",
    Notification.TYPE_GAME_UPDATED: "notify_activity_updates",
}


def _actor_display_name(user):
    return user.get_full_name() or user.username


def _game_sport_label(game):
    return game.get_sport_display()


def _community_name(community):
    return getattr(community, "name", "группу")


def get_notification_message(notification):
    actor = _actor_display_name(notification.actor)
    target = notification.target
    notification_type = notification.notification_type

    if notification_type == Notification.TYPE_FRIENDSHIP_REQUEST:
        return f"{actor} отправил вам заявку в друзья"

    if notification_type == Notification.TYPE_FRIENDSHIP_ACCEPTED:
        return f"{actor} принял вашу заявку в друзья"

    if notification_type == Notification.TYPE_GAME_PARTICIPATION_REQUEST:
        game = getattr(target, "game", target)
        sport = _game_sport_label(game)
        return f"{actor} запросил участие в вашем мероприятии {sport}"

    if notification_type == Notification.TYPE_GAME_INVITATION:
        game = getattr(target, "game", target)
        sport = _game_sport_label(game)
        return f"{actor} пригласил вас на мероприятие {sport}"

    if notification_type == Notification.TYPE_GAME_PARTICIPATION_ACCEPTED:
        game = getattr(target, "game", target)
        sport = _game_sport_label(game)
        return f"{actor} принял вашу заявку на участие в мероприятии {sport}"

    if notification_type == Notification.TYPE_GAME_PARTICIPATION_REJECTED:
        game = getattr(target, "game", target)
        sport = _game_sport_label(game)
        return f"{actor} отклонил вашу заявку на участие в мероприятии {sport}"

    if notification_type == Notification.TYPE_GAME_PLAYER_REMOVED:
        sport = _game_sport_label(target)
        return f"{actor} исключил вас из мероприятия {sport}"

    if notification_type == Notification.TYPE_CHAT_MESSAGE:
        game = getattr(target, "game", target)
        sport = _game_sport_label(game)
        return f"{actor} написал в чате {sport}"

    if notification_type == Notification.TYPE_GAME_UPDATED:
        sport = _game_sport_label(target)
        return f"{actor} изменил условия мероприятия {sport}"

    if notification_type == Notification.TYPE_GROUP_JOIN_REQUEST:
        community = getattr(target, "community", target)
        name = _community_name(community)
        return f"{actor} запросил вступление в группу {name}"

    if notification_type == Notification.TYPE_GROUP_INVITATION:
        community = getattr(target, "community", target)
        name = _community_name(community)
        return f"{actor} пригласил вас в группу {name}"

    if notification_type == Notification.TYPE_GROUP_JOIN_ACCEPTED:
        community = getattr(target, "community", target)
        name = _community_name(community)
        return f"{actor} принял вашу заявку на вступление в группу {name}"

    if notification_type == Notification.TYPE_GROUP_JOIN_REJECTED:
        community = getattr(target, "community", target)
        name = _community_name(community)
        return f"{actor} отклонил вашу заявку на вступление в группу {name}"

    if notification_type == Notification.TYPE_GROUP_MEMBER_REMOVED:
        name = _community_name(target)
        return f"{actor} исключил вас из группы {name}"

    return f"{actor} отправил вам уведомление"


def get_notification_game(notification):
    if notification.notification_type not in GAME_NOTIFICATION_TYPES:
        return None
    target = notification.target
    if target is None:
        return None
    return getattr(target, "game", target)


def get_notification_community(notification):
    if notification.notification_type not in GROUP_NOTIFICATION_TYPES:
        return None
    target = notification.target
    if target is None:
        return None
    return getattr(target, "community", target)


def get_notification_url(notification):
    if notification.notification_type in FRIENDSHIP_NOTIFICATION_TYPES:
        return reverse("user_detail", args=[notification.actor.username])
    game = get_notification_game(notification)
    if game is not None:
        if notification.notification_type == Notification.TYPE_CHAT_MESSAGE:
            return game.get_chat_url()
        return game.get_absolute_url()
    community = get_notification_community(notification)
    if community is not None:
        return community.get_absolute_url()
    return reverse("dashboard")


def _recipient_allows_notification(recipient, notification_type):
    pref_field = NOTIFICATION_TYPE_PREF_FIELD.get(notification_type)
    if not pref_field:
        return True
    profile = getattr(recipient, "profile", None)
    if profile is None:
        return True
    return bool(getattr(profile, pref_field, True))


def create_notification(recipient, actor, notification_type, target):
    if recipient == actor:
        return None

    if not _recipient_allows_notification(recipient, notification_type):
        return None

    now = timezone.now()
    last_minute = now - datetime.timedelta(seconds=60)
    target_ct = ContentType.objects.get_for_model(target)
    similar = Notification.objects.filter(
        recipient=recipient,
        actor=actor,
        notification_type=notification_type,
        target_ct=target_ct,
        target_id=target.pk,
        created__gte=last_minute,
    )
    if similar.exists():
        return None

    return Notification.objects.create(
        recipient=recipient,
        actor=actor,
        notification_type=notification_type,
        target=target,
    )


def notify_game_chat_message(message):
    """Уведомляет организатора и участников о новом сообщении (кроме автора)."""
    game = message.game
    actor = message.author
    recipients = {game.user}
    recipients.update(game.joined_players.all())
    for recipient in recipients:
        create_notification(
            recipient,
            actor,
            Notification.TYPE_CHAT_MESSAGE,
            message,
        )


def notify_game_updated(game, actor):
    """Уведомляет участников об изменении условий мероприятия."""
    for recipient in game.joined_players.all():
        create_notification(
            recipient,
            actor,
            Notification.TYPE_GAME_UPDATED,
            game,
        )


def get_unread_count(user):
    return Notification.objects.filter(recipient=user, read_at__isnull=True).count()


def mark_as_read(notification, user):
    if notification.recipient_id != user.id:
        return False
    if notification.read_at is not None:
        return True
    notification.read_at = timezone.now()
    notification.save(update_fields=["read_at"])
    return True


def mark_all_as_read(user):
    return Notification.objects.filter(
        recipient=user, read_at__isnull=True
    ).update(read_at=timezone.now())
