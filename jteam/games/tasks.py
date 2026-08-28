from celery import shared_task
from django.db import connection
from django.utils import timezone
from games.models import Game
import logging

logger = logging.getLogger(__name__)


def sync_game_statuses():
    """
    Обновляет статусы игр на основе времени начала и продолжительности.

    Логика:
    1. Игры со статусом 'open', время начала которых наступило, переводятся в 'started'
    2. Игры со статусом 'started', время окончания которых прошло, переводятся в 'finished'
    """
    now = timezone.now()

    started_count = Game.objects.filter(
        status="open", start_time__lte=now
    ).update(status="started")

    table = connection.ops.quote_name(Game._meta.db_table)
    with connection.cursor() as cursor:
        cursor.execute(
            f"UPDATE {table} "
            "SET status = %s "
            "WHERE status = %s AND start_time + duration <= %s",
            ["finished", "started", now],
        )
        finished_count = cursor.rowcount

    return started_count, finished_count


@shared_task
def update_game_status():
    now = timezone.now()
    logger.info(f"Запуск обновления статусов игр в {now}")

    started_count, finished_count = sync_game_statuses()

    result = f"Updated: {started_count} games started, {finished_count} games finished"
    logger.info(result)
    return result
