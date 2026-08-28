import datetime

from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone

from games.models import Game

from .models import Action


def get_user_activity(user, limit=10):
    actions = list(
        Action.objects.filter(user=user)
        .select_related("user", "user__profile", "target_ct")
        .order_by("-created")[:limit]
    )
    if not actions:
        return actions

    user_ids = []
    game_ids = []
    for action in actions:
        if not action.target_id:
            continue
        if action.target_ct.model == "user":
            user_ids.append(action.target_id)
        elif action.target_ct.model == "game":
            game_ids.append(action.target_id)

    users_by_id = {
        u.pk: u
        for u in User.objects.filter(pk__in=user_ids).select_related("profile")
    }
    games_by_id = {g.pk: g for g in Game.objects.filter(pk__in=game_ids)}

    for action in actions:
        if not action.target_id:
            continue
        if action.target_ct.model == "user":
            action.target = users_by_id.get(action.target_id)
        elif action.target_ct.model == "game":
            action.target = games_by_id.get(action.target_id)

    return actions


def create_action(user, verb, target=None):
    """функция быстрого доступа, которая
    позволяет создавать новые объекты Action простым способом"""

    # Игнорирование повторных действий в потоке активности
    # проверить, не было ли каких-либо аналогичных действий, совершенных за последнюю минуту
    now = timezone.now()
    last_minute = now - datetime.timedelta(seconds=60)
    similar_action = Action.objects.filter(
        user_id=user.id, verb=verb, created__gte=last_minute
    )
    if target:
        target_ct = ContentType.objects.get_for_model(target)
        similar_action = similar_action.filter(target_ct=target_ct, target_id=target.id)
    if similar_action.exists():
        return False
    action = Action(user=user, verb=verb, target=target)
    action.save()
    return True
