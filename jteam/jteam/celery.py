import os
import time

from celery import Celery
from django.conf import settings

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "jteam.settings")
app = Celery("jteam")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.conf.broker_url = settings.CELERY_BROKER_URL
app.autodiscover_tasks()


@app.task()
def debug_task():
    time.sleep(15)
    print("Hello form debug_task")


app.conf.beat_schedule = {
    'update-game-status-every-10-seconds': {
        'task': 'games.tasks.update_game_status',
        'schedule': 10.0,  # каждые 10 секунд
    },
}