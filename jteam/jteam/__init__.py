from .celery import app as celery_app

__all__ = ("celery_app",)  # использование кортежа вместо списка
