"""Прод-алертинг: письма ADMINS и опциональный Sentry."""

from __future__ import annotations

import os
import warnings


def apply_prod_error_logging(logging_config: dict) -> dict:
    """Письма ADMINS на HTTP 500, django.security и ошибки Celery."""
    logging_config.setdefault("filters", {})
    logging_config["filters"]["require_debug_false"] = {
        "()": "django.utils.log.RequireDebugFalse",
    }
    logging_config.setdefault("handlers", {})
    logging_config["handlers"]["mail_admins"] = {
        "level": "ERROR",
        "class": "django.utils.log.AdminEmailHandler",
        "filters": ["require_debug_false"],
        "include_html": False,
    }
    logging_config.setdefault("loggers", {})
    for name in ("django.request", "django.security", "celery"):
        existing = logging_config["loggers"].get(name, {})
        handlers = list(existing.get("handlers", ["console", "file"]))
        if "mail_admins" not in handlers:
            handlers.append("mail_admins")
        logging_config["loggers"][name] = {
            **existing,
            "handlers": handlers,
            "level": existing.get("level", "ERROR"),
            "propagate": False,
        }
    return logging_config


def init_sentry(
    dsn: str | None,
    *,
    traces_sample_rate: float = 0.0,
    environment: str = "prod",
) -> bool:
    """Инициализирует Sentry, если задан DSN. Иначе — no-op."""
    dsn = (dsn or "").strip()
    if not dsn:
        return False
    try:
        import sentry_sdk
        from sentry_sdk.integrations.celery import CeleryIntegration
        from sentry_sdk.integrations.django import DjangoIntegration
    except ImportError as exc:
        raise RuntimeError(
            "SENTRY_DSN is set but sentry-sdk is not installed"
        ) from exc
    sentry_sdk.init(
        dsn=dsn,
        integrations=[DjangoIntegration(), CeleryIntegration()],
        traces_sample_rate=traces_sample_rate,
        send_default_pii=False,
        environment=environment,
    )
    return True


def warn_if_no_error_reporting(admins, sentry_dsn: str | None) -> None:
    if admins:
        return
    if (sentry_dsn or "").strip():
        return
    warnings.warn(
        "DJANGO_ENV=prod without ADMINS or SENTRY_DSN: "
        "server errors will not be emailed or sent to Sentry",
        RuntimeWarning,
        stacklevel=2,
    )


def sentry_traces_sample_rate() -> float:
    raw = os.getenv("SENTRY_TRACES_SAMPLE_RATE", "0.0")
    try:
        return float(raw)
    except ValueError:
        return 0.0
