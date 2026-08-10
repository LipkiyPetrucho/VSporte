from django.conf import settings


def social_login(request):
    return {
        "telegram_bot_username": getattr(settings, "TELEGRAM_BOT_USERNAME", "") or "",
        "telegram_login_enabled": bool(
            getattr(settings, "SOCIAL_AUTH_TELEGRAM_BOT_TOKEN", None)
            and getattr(settings, "TELEGRAM_BOT_USERNAME", None)
        ),
    }
