"""Отправка и проверка SMS-кодов подтверждения телефона."""

from __future__ import annotations

import logging
import random
import re
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.models import User
from django.utils import timezone

from .models import PhoneVerification

logger = logging.getLogger(__name__)

PHONE_RE = re.compile(r"^\+7\d{10}$")
CODE_LENGTH = 4
CODE_TTL_MINUTES = getattr(settings, "PHONE_CODE_TTL_MINUTES", 10)
MAX_ATTEMPTS = getattr(settings, "PHONE_CODE_MAX_ATTEMPTS", 5)
RESEND_COOLDOWN_SECONDS = getattr(settings, "PHONE_CODE_RESEND_COOLDOWN", 60)


class PhoneValidationError(ValueError):
    pass


def normalize_phone(raw: str) -> str:
    """Приводит номер к формату +7XXXXXXXXXX."""
    if not raw:
        raise PhoneValidationError("Укажите номер телефона.")

    digits = re.sub(r"\D", "", raw)
    if len(digits) == 11 and digits.startswith("8"):
        digits = "7" + digits[1:]
    elif len(digits) == 10:
        digits = "7" + digits

    phone = f"+{digits}"
    if not PHONE_RE.match(phone):
        raise PhoneValidationError(
            "Введите корректный номер в формате +7XXXXXXXXXX."
        )
    return phone


def generate_code() -> str:
    return f"{random.randint(0, 10**CODE_LENGTH - 1):0{CODE_LENGTH}d}"


def generate_username_from_phone(phone: str) -> str:
    """Генерирует уникальный username на основе номера телефона."""
    phone = normalize_phone(phone)
    base = f"user_{phone.lstrip('+')}"
    if not User.objects.filter(username=base).exists():
        return base
    suffix = 1
    while User.objects.filter(username=f"{base}_{suffix}").exists():
        suffix += 1
    return f"{base}_{suffix}"


def _send_sms(phone: str, message: str) -> None:
    backend = getattr(settings, "SMS_BACKEND", "console")
    if backend == "twilio":
        _send_via_twilio(phone, message)
        return
    logger.info("SMS to %s: %s", phone, message)


def _send_via_twilio(phone: str, message: str) -> None:
    try:
        from twilio.rest import Client
    except ImportError as exc:
        raise RuntimeError(
            "Для SMS_BACKEND=twilio установите пакет twilio."
        ) from exc

    account_sid = getattr(settings, "TWILIO_ACCOUNT_SID", None)
    auth_token = getattr(settings, "TWILIO_AUTH_TOKEN", None)
    from_number = getattr(settings, "TWILIO_FROM_NUMBER", None)
    if not all([account_sid, auth_token, from_number]):
        raise RuntimeError("Не заданы настройки Twilio.")

    client = Client(account_sid, auth_token)
    client.messages.create(body=message, from_=from_number, to=phone)


def create_and_send_code(
    phone: str, purpose: str = PhoneVerification.PURPOSE_REGISTER
) -> PhoneVerification:
    phone = normalize_phone(phone)
    cooldown = getattr(settings, "PHONE_CODE_RESEND_COOLDOWN", RESEND_COOLDOWN_SECONDS)

    latest = (
        PhoneVerification.objects.filter(phone=phone, purpose=purpose, is_used=False)
        .order_by("-created_at")
        .first()
    )
    if latest and not latest.is_expired and cooldown > 0:
        elapsed = (timezone.now() - latest.created_at).total_seconds()
        if elapsed < cooldown:
            wait = int(cooldown - elapsed)
            raise PhoneValidationError(
                f"Повторная отправка будет доступна через {wait} сек."
            )

    code = generate_code()
    ttl = getattr(settings, "PHONE_CODE_TTL_MINUTES", CODE_TTL_MINUTES)
    verification = PhoneVerification.objects.create(
        phone=phone,
        code=code,
        purpose=purpose,
        expires_at=timezone.now() + timedelta(minutes=ttl),
    )
    _send_sms(
        phone,
        f"Ваш код подтверждения JTeam: {code}. Действует {ttl} мин.",
    )
    return verification


def verify_code(
    phone: str,
    code: str,
    purpose: str = PhoneVerification.PURPOSE_REGISTER,
) -> PhoneVerification:
    phone = normalize_phone(phone)
    code = (code or "").strip()
    if not re.fullmatch(r"\d{4}", code):
        raise PhoneValidationError("Введите четырёхзначный код.")

    max_attempts = getattr(settings, "PHONE_CODE_MAX_ATTEMPTS", MAX_ATTEMPTS)
    verification = (
        PhoneVerification.objects.filter(phone=phone, purpose=purpose, is_used=False)
        .order_by("-created_at")
        .first()
    )
    if verification is None:
        raise PhoneValidationError("Код не найден. Запросите новый.")

    if verification.is_expired:
        raise PhoneValidationError("Срок действия кода истёк. Запросите новый.")

    if verification.attempts >= max_attempts:
        raise PhoneValidationError(
            "Превышено число попыток. Запросите новый код."
        )

    if verification.code != code:
        verification.attempts += 1
        verification.save(update_fields=["attempts"])
        remaining = max_attempts - verification.attempts
        if remaining <= 0:
            raise PhoneValidationError(
                "Превышено число попыток. Запросите новый код."
            )
        raise PhoneValidationError(
            f"Неверный код. Осталось попыток: {remaining}."
        )

    verification.is_used = True
    verification.save(update_fields=["is_used"])
    return verification


def get_user_by_phone(phone: str):
    phone = normalize_phone(phone)
    try:
        return User.objects.select_related("profile").get(
            profile__phone=phone,
            profile__phone_verified=True,
            is_active=True,
        )
    except User.DoesNotExist as exc:
        raise PhoneValidationError(
            "Аккаунт с этим номером не найден."
        ) from exc
