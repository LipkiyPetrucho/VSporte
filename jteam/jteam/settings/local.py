import os

from .settings import *

DEBUG = True
THUMBNAIL_DEBUG = True

MIDDLEWARE = [
    "jteam.middleware.LocalhostRedirectMiddleware",
    *MIDDLEWARE,
]

ALLOWED_HOSTS = [
    "localhost",
    "127.0.0.1",
    "localhost:8000",
    "jteam.ru",
    "www.jteam.ru",
    ".ngrok-free.app",  # Разрешает все поддомены ngrok
    "3e15-192-119-10-202.ngrok-free.app",  # Конкретный домен
]

# В контейнере хост БД — "database"; на хосте с тем же .env — localhost (проброшенный порт).
_in_docker = os.path.exists("/.dockerenv")
if os.environ.get("LOCAL_DB_HOST"):
    DATABASES["default"]["HOST"] = os.environ["LOCAL_DB_HOST"]
elif not _in_docker and os.environ.get("POSTGRES_DB_HOST") == "database":
    DATABASES["default"]["HOST"] = "localhost"

# В Docker хост Redis — "redis", локально — 127.0.0.1.
REDIS_HOST = os.environ.get("REDIS_HOST", "redis" if _in_docker else "127.0.0.1")
REDIS_PORT = int(os.environ.get("REDIS_PORT", REDIS_PORT))
CELERY_BROKER_URL = os.environ.get(
    "CELERY_BROKER_URL",
    f"redis://{REDIS_HOST}:{REDIS_PORT}/0",
)
CHANNEL_LAYERS["default"]["CONFIG"]["hosts"] = [
    f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_CHANNEL_LAYER_DB}",
]

# Настройки логирования для разработки
LOGGING["root"]["level"] = "DEBUG"
LOGGING["handlers"]["file"]["level"] = "DEBUG"

CSRF_TRUSTED_ORIGINS = [
    "https://jteam.ru",
    "https://www.jteam.ru",
    "https://*.ngrok-free.app",
    "https://3e15-192-119-10-202.ngrok-free.app"
]

SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SESSION_COOKIE_SECURE = True

