import os

from .error_reporting import (
    apply_prod_error_logging,
    init_sentry,
    sentry_traces_sample_rate,
    warn_if_no_error_reporting,
)
from .settings import *

DEBUG = False
THUMBNAIL_DEBUG = False

ALLOWED_HOSTS = ["jteam.ru", "www.jteam.ru"]

# В prod коды верификации не должны уходить только в лог (console).
# Переопределите через .env при необходимости; иначе — Twilio.
SMS_BACKEND = os.getenv("SMS_BACKEND", "twilio")

CSRF_TRUSTED_ORIGINS = [
    "https://jteam.ru",
    "https://www.jteam.ru",
]

# Настройки безопасности
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000  # 1 год
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
# TLS на nginx (:443); Django видит HTTPS через SECURE_PROXY_SSL_HEADER
SECURE_SSL_REDIRECT = True

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_STORAGE = "django.contrib.staticfiles.storage.ManifestStaticFilesStorage"

EMAIL_SUBJECT_PREFIX = "[JTeam] "

# Настройки логирования для продакшн
LOGGING["handlers"]["file"]["level"] = "INFO"
LOGGING["loggers"]["django"]["level"] = "INFO"
LOGGING["loggers"]["games"]["level"] = "INFO"
apply_prod_error_logging(LOGGING)

SENTRY_DSN = os.getenv("SENTRY_DSN", "").strip()
warn_if_no_error_reporting(ADMINS, SENTRY_DSN)
init_sentry(
    SENTRY_DSN,
    traces_sample_rate=sentry_traces_sample_rate(),
    environment="prod",
)

# Redis/CHANNEL_LAYERS задаются в settings.py (Celery /0, Channels /1).