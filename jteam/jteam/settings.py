import json
import os
from pathlib import Path
from dotenv import load_dotenv

from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")
print("SECRET_KEY =", os.getenv("SECRET_KEY"))
SECRET_KEY = os.getenv("SECRET_KEY")

DEBUG = True
THUMBNAIL_DEBUG = True

# ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", "").split(",")
ALLOWED_HOSTS = []

INSTALLED_APPS = [
    # app
    "account.apps.AccountConfig",
    "games.apps.GamesConfig",
    "actions.apps.ActionsConfig",
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
    "social_django",
    # 'django_extensions',
    "crispy_forms",
    "crispy_bootstrap5",
    "fontawesomefree",
    "easy_thumbnails",
    "debug_toolbar",
    "bootstrap5",
    "rosetta",
]

MIDDLEWARE = [
    "debug_toolbar.middleware.DebugToolbarMiddleware",
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
                "cart.context_processors.cart",
            ],
        },
    },
]

WSGI_APPLICATION = "jteam.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "HOST": os.environ.get("DB_HOST"),
        "NAME": os.environ.get("DB_NAME"),
        "USER": os.environ.get("DB_USER"),
        "PASSWORD": os.environ.get("DB_PASS"),
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

LANGUAGES = [
    ("en", _("English")),
    ("ru", _("Russian")),
]

LANGUAGE_CODE = "en"

TIME_ZONE = "Europe/Samara"

USE_I18N = True

USE_TZ = True

LOCALE_PATHS = [os.path.join(BASE_DIR / "locale")]

STATIC_URL = "/static/"
STATICFILES_DIRS = [os.path.join(BASE_DIR, "static")]
STATIC_ROOT = os.path.join(BASE_DIR, "account", "static")

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

# celery
# CELERY_BROKER_URL = 'amqp://guest:guest@localhost'
CELERY_BROKER_URL = "redis://redis:6379/0"

CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"

AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "account.authentication.EmailAuthBackend",
    "social_core.backends.facebook.FacebookOAuth2",
    "social_core.backends.google.GoogleOAuth2",
]

SOCIAL_AUTH_FACEBOOK_KEY = os.getenv("SOCIAL_AUTH_FACEBOOK_KEY")
SOCIAL_AUTH_FACEBOOK_SECRET = os.getenv("SOCIAL_AUTH_FACEBOOK_SECRET")
SOCIAL_AUTH_FACEBOOK_SCOPE = [
    "email",
]

# ИД клиента Google
SOCIAL_AUTH_GOOGLE_OAUTH2_KEY = os.getenv("SOCIAL_AUTH_GOOGLE_OAUTH2_KEY")
SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET = os.getenv("SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET")

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

# debug_toolbar
INTERNAL_IPS = ["127.0.0.1", "localhost", ".jteam.ru"]

# db redis
REDIS_HOST = "redis"
REDIS_PORT = 6379
REDIS_DB = 0

# ключ, который будет использоваться для хранения корзины в пользовательском сеансе.
CART_SESSION_ID = "cart"

# Настроечные параметры Stripe
STRIPE_PUBLISHABLE_KEY = os.getenv("STRIPE_PUBLISHABLE_KEY")
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")
STRIPE_API_VERSION = os.getenv("STRIPE_API_VERSION")
# веб-перехватчика Stripe
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")
