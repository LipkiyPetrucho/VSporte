import json
import os
from pathlib import Path
from dotenv import load_dotenv

from django.urls import reverse_lazy

BASE_DIR = Path(__file__).resolve().parent.parent.parent
for env_path in (BASE_DIR / ".env", BASE_DIR.parent / ".env"):
    if env_path.exists():
        load_dotenv(env_path)
        break
SECRET_KEY = os.getenv("SECRET_KEY")

INSTALLED_APPS = [
    # daphne должен быть выше staticfiles — иначе runserver останется на WSGI
    "daphne",
    # app
    "account.apps.AccountConfig",
    "games.apps.GamesConfig",
    "groups.apps.GroupsConfig",
    "actions.apps.ActionsConfig",
    "notifications.apps.NotificationsConfig",
    "location.apps.LocationConfig",
    "cart.apps.CartConfig",
    "orders.apps.OrdersConfig",
    "payment.apps.PaymentConfig",
    "coupons.apps.CouponsConfig",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.postgres",
    # lib
    "channels",
    "social_django",
    # 'django_extensions',
    "crispy_forms",
    "crispy_bootstrap5",
    "fontawesomefree",
    "easy_thumbnails",
    "bootstrap5",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "social_django.middleware.SocialAuthExceptionMiddleware",
]

ROOT_URLCONF = "jteam.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "social_django.context_processors.backends",
                "account.context_processors.social_login",
                "cart.context_processors.cart",
                "notifications.context_processors.notifications",
                "location.context_processors.cities",
            ],
        },
    },
]

WSGI_APPLICATION = "jteam.wsgi.application"
ASGI_APPLICATION = "jteam.asgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "HOST": os.environ.get("DB_HOST") or os.environ.get("POSTGRES_DB_HOST", "localhost"),
        "NAME": os.environ.get("DB_NAME") or os.environ.get("POSTGRES_DB_NAME"),
        "USER": os.environ.get("DB_USER") or os.environ.get("POSTGRES_DB_USER"),
        "PASSWORD": os.environ.get("DB_PASS") or os.environ.get("POSTGRES_DB_PASSWORD"),
        "PORT": os.environ.get("DB_PORT") or os.environ.get("POSTGRES_DB_PORT", "5432"),
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

LANGUAGE_CODE = "ru"

TIME_ZONE = "Europe/Samara"

DATE_INPUT_FORMATS = [
    '%d/%m/%Y',
]

USE_I18N = True

USE_L10N = True

USE_TZ = True

STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LOGIN_REDIRECT_URL = "dashboard"
LOGOUT_REDIRECT_URL = "login"
LOGIN_URL = "login"
LOGOUT_URL = "logout"

# mail config
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
# EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# yandex
EMAIL_HOST = "smtp.yandex.ru"
EMAIL_PORT = 465
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD")
EMAIL_USE_SSL = True

DEFAULT_FROM_EMAIL = EMAIL_HOST_USER
SERVER_EMAIL = EMAIL_HOST_USER
EMAIL_ADMIN = EMAIL_HOST_USER
ADMINS = json.loads(os.getenv("ADMINS", "[]"))

# Yandex Maps API
YANDEX_MAPS_API_KEY = os.getenv("YANDEX_MAPS_API_KEY")
YANDEX_MAPS_API_KEY_STATIC = os.getenv("YANDEX_MAPS_API_KEY_STATIC")
YANDEX_MAPS_SUGGEST_API_KEY = os.getenv("YANDEX_MAPS_SUGGEST_API_KEY") or YANDEX_MAPS_API_KEY
YANDEX_GEOCODER_API_KEY = os.getenv("YANDEX_GEOCODER_API_KEY") or YANDEX_MAPS_API_KEY
YANDEX_MAPS_REFERER = os.getenv("YANDEX_MAPS_REFERER", "http://localhost:8000/")

# db redis (уже используется Celery и кешем игр; channel layer — отдельная DB)
REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_DB = int(os.getenv("REDIS_DB", 0))
# Channels: DB /1, чтобы не пересекаться с Celery broker (/0)
REDIS_CHANNEL_LAYER_DB = int(os.getenv("REDIS_CHANNEL_LAYER_DB", 1))

# celery
# CELERY_BROKER_URL = 'amqp://guest:guest@localhost'
CELERY_BROKER_URL = os.getenv(
    "CELERY_BROKER_URL", f"redis://{REDIS_HOST}:{REDIS_PORT}/0"
)

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [
                f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_CHANNEL_LAYER_DB}"
            ],
        },
    },
}

CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"

AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "account.authentication.EmailAuthBackend",
    "social_core.backends.google.GoogleOAuth2",
    "social_core.backends.telegram.TelegramAuth",
]

SOCIAL_AUTH_GOOGLE_OAUTH2_KEY = os.getenv("SOCIAL_AUTH_GOOGLE_OAUTH2_KEY")
SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET = os.getenv("SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET")

# Telegram Login Widget: токен бота от @BotFather + username без @
SOCIAL_AUTH_TELEGRAM_BOT_TOKEN = os.getenv("SOCIAL_AUTH_TELEGRAM_BOT_TOKEN")
TELEGRAM_BOT_USERNAME = os.getenv("TELEGRAM_BOT_USERNAME", "")

SOCIAL_AUTH_PIPELINE = [
    "social_core.pipeline.social_auth.social_details",
    "social_core.pipeline.social_auth.social_uid",
    "social_core.pipeline.social_auth.auth_allowed",
    "social_core.pipeline.social_auth.social_user",
    "social_core.pipeline.user.get_username",
    "social_core.pipeline.user.create_user",
    "account.authentication.create_profile",
    "social_core.pipeline.social_auth.associate_user",
    "social_core.pipeline.social_auth.load_extra_data",
    "social_core.pipeline.user.user_details",
]

# В случае использования Chromebook
MESSAGE_STORAGE = "django.contrib.messages.storage.session.SessionStorage"

CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"

CRISPY_TEMPLATE_PACK = "bootstrap5"

# Для указания URL-адреса для модели добавляем в проект настроечный параметр
ABSOLUTE_URL_OVERRIDES = {
    "auth.user": lambda u: reverse_lazy("user_detail", args=[u.username])
}

# ключ, который будет использоваться для хранения корзины в пользовательском сеансе.
CART_SESSION_ID = "cart"

# SMS: console (лог) или twilio
SMS_BACKEND = os.getenv("SMS_BACKEND", "console")
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_FROM_NUMBER = os.getenv("TWILIO_FROM_NUMBER")
PHONE_CODE_TTL_MINUTES = int(os.getenv("PHONE_CODE_TTL_MINUTES", "10"))
PHONE_CODE_MAX_ATTEMPTS = int(os.getenv("PHONE_CODE_MAX_ATTEMPTS", "5"))
PHONE_CODE_RESEND_COOLDOWN = int(os.getenv("PHONE_CODE_RESEND_COOLDOWN", "60"))

# Маркетплейс площадок: корзина, заказы, оплата. Выключено до появления партнёров.
MARKETPLACE_ENABLED = os.getenv("MARKETPLACE_ENABLED", "false").lower() in (
    "1",
    "true",
    "yes",
    "on",
)

# Настроечные параметры Stripe
STRIPE_PUBLISHABLE_KEY = os.getenv("STRIPE_PUBLISHABLE_KEY")
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")
STRIPE_API_VERSION = os.getenv("STRIPE_API_VERSION")
# веб-перехватчика Stripe
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")

# THUMBNAIL
THUMBNAIL_ALIASES = {
    '': {
        'player_avatar': {'size': (80, 80), 'crop': True, 'upscale': True},
    },
}

# Настройки логирования

LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    # ---------- форматтеры ----------
    "formatters": {
        "verbose": {
            "format": "{asctime} {levelname:<8} {name}:{lineno} {message}",
            "style": "{",
        },
        "simple": {"format": "{levelname:<8} {message}", "style": "{"},
    },
    # ---------- обработчики ----------
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "simple",          # лаконичнее при разработке
            "level": "DEBUG",               # всегда подробно в терминал
        },
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": LOG_DIR / "django.log",
            "formatter": "verbose",
            "level": "INFO",                # в файл — только INFO+
            "maxBytes": 5 * 1024 * 1024,    # 5 MB
            "backupCount": 5,               # хранить 5 архивов
            "encoding": "utf-8",
        },
    },
    # ---------- корневой логгер ----------
    "root": {
        "handlers": ["console", "file"],
        "level": "INFO",                    # DEBUG включаем точечно
    },
    # ---------- логгеры приложений ----------
    "loggers": {
        # примеры: при разработке можно временно поднять уровень
        # конкретному приложению, не задевая все остальные.
        "django.db.backends": {
            "handlers": ["console"],
            "level": "WARNING",             # убирает SQL-трасс в консоли
            "propagate": False,
        },
        "games": {
            "handlers": ["console"],
            "level": "DEBUG",
            "propagate": False,
        },
    },
}

LOGGING["loggers"]["django"] = {
    "handlers": ["console", "file"],
    "level": "INFO",       # по умолчанию
    "propagate": False,
}
