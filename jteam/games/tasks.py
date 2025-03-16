from celery import shared_task
from django.utils import timezone
from games.models import Game
import logging

logger = logging.getLogger(__name__)

@shared_task
def update_game_status():
    """
    Обновляет статусы игр на основе времени начала и продолжительности.
    
    Логика:
    1. Игры со статусом 'open', время начала которых наступило, переводятся в 'started'
    2. Игры со статусом 'started', время окончания которых прошло, переводятся в 'finished'
    """
    now = timezone.now()
    logger.info(f"Запуск обновления статусов игр в {now}")
    
    # Обновляем игры со статусом "open", время начала которых уже наступило
    games_to_start = Game.objects.filter(
        status="open",
        start_time__lte=now
    )
    if games_to_start.exists():
        count_to_start = games_to_start.count()
        logger.info(f"Найдено {count_to_start} игр для перевода в статус 'started'")
        games_to_start.update(status="started")
    else:
        logger.info("Нет игр для перевода в статус 'started'")
    
    # Обновляем игры со статусом "started", у которых время завершения прошло
    games_to_finish = Game.objects.filter(status="started")
    finished_count = 0
    for game in games_to_finish:
        game_finish = game.start_time + game.duration
        if now >= game_finish:
            logger.info(f"Игра {game.id} завершается (start_time: {game.start_time}, duration: {game.duration})")
            game.status = "finished"
            game.save()
            finished_count += 1
    
    if games_to_finish:
        logger.info(f"Проверено {games_to_finish.count()} started игр, завершено {finished_count}")
    else:
        logger.info("Нет игр со статусом 'started'")
    
    result = f"Updated: {games_to_start.count() if 'games_to_start' in locals() else 0} games started, {finished_count} games finished"
    logger.info(result)
    return result
