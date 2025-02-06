import datetime

from django.contrib.contenttypes.models import ContentType
from django.utils import timezone

from .models import Action


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
    if not similar_action:
        # никаких существующих действий не найдено
        action = Action(user=user, verb=verb, target=target)
        action.save()
        return True
    return False
