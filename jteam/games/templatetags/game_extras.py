from django import template
from django.utils import timezone

register = template.Library()

RU_MONTHS = (
    "",
    "янв.",
    "февр.",
    "мар.",
    "апр.",
    "мая",
    "июн.",
    "июл.",
    "авг.",
    "сент.",
    "окт.",
    "нояб.",
    "дек.",
)

GAME_STATUS_LABELS = {
    "open": "Открыта",
    "started": "Идёт",
    "finished": "Завершена",
}


@register.filter
def game_status_label(status):
    return GAME_STATUS_LABELS.get(status, status)


SPORT_ICONS = {
    "football": "fa-futbol",
    "tennis": "fa-table-tennis-paddle-ball",
    "bowling": "fa-bowling-ball",
    "beach volleyball": "fa-volleyball",
    "volleyball": "fa-volleyball",
    "ice hockey": "fa-hockey-puck",
    "chess": "fa-chess",
}


@register.filter
def get_item(dictionary, key):
    return dictionary.get(key, "")


@register.filter
def sport_icon(sport):
    return SPORT_ICONS.get(sport, "fa-futbol")


@register.filter
def game_datetime_mobile(value):
    local = timezone.localtime(value)
    hour = local.strftime("%I").lstrip("0") or "12"
    minute = local.strftime("%M")
    ampm = "AM" if local.hour < 12 else "PM"
    return f"{RU_MONTHS[local.month]} {local.day}, {local.year}, {hour}:{minute} {ampm}"


@register.filter
def game_date_ru(value):
    """Дата карточки игры: «17 авг. 2026», без зависимости от локали браузера."""
    if not value:
        return ""
    local = timezone.localtime(value)
    return f"{local.day} {RU_MONTHS[local.month]} {local.year}"


@register.filter
def going_label(count):
    count = int(count)
    if count % 10 == 1 and count % 100 != 11:
        return "идёт"
    return "идут" 