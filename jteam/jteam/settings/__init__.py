import os
from .settings import *

ENVIRONMENT = os.getenv("DJANGO_ENV", "local").lower()
if ENVIRONMENT not in ("local", "prod"):
    raise RuntimeError(f"Unknown DJANGO_ENV={ENVIRONMENT}")

_PLACEHOLDER_SECRET_KEYS = frozenset(
    {
        "",
        "replace_me_with_random_64_chars",
        "changeme",
        "secret",
        "django-insecure",
    }
)

if ENVIRONMENT == "prod":
    _secret = (SECRET_KEY or "").strip()
    if (
        not _secret
        or _secret in _PLACEHOLDER_SECRET_KEYS
        or _secret.startswith("django-insecure-")
        or len(_secret) < 32
    ):
        raise RuntimeError(
            "SECRET_KEY must be set to a strong non-placeholder value when DJANGO_ENV=prod"
        )
    from .prod import *

    if SMS_BACKEND == "twilio":
        _twilio_missing = [
            name
            for name, value in (
                ("TWILIO_ACCOUNT_SID", TWILIO_ACCOUNT_SID),
                ("TWILIO_AUTH_TOKEN", TWILIO_AUTH_TOKEN),
                ("TWILIO_FROM_NUMBER", TWILIO_FROM_NUMBER),
            )
            if not (value or "").strip()
            or (value or "").startswith("your_")
            or "xxxx" in (value or "").lower()
        ]
        if _twilio_missing:
            raise RuntimeError(
                "SMS_BACKEND=twilio requires valid "
                + ", ".join(_twilio_missing)
                + " when DJANGO_ENV=prod"
            )
else:
    from .local import *
