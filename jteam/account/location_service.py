"""Управление локацией проживания и недавними местами."""

from __future__ import annotations

import uuid
from decimal import Decimal, InvalidOperation

RECENT_LOCATIONS_LIMIT = 12


def _to_float(value):
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _to_decimal(value):
    number = _to_float(value)
    if number is None:
        return None
    try:
        return Decimal(str(round(number, 6)))
    except (InvalidOperation, ValueError):
        return None


def normalize_location_payload(data):
    """Приводит payload выбора адреса к словарю локации или None."""
    if not isinstance(data, dict):
        return None

    title = (data.get("title") or "").strip()
    address = (data.get("address") or data.get("value") or data.get("label") or "").strip()
    if not title and address:
        title = address.split(",")[0].strip()
    if not address and title:
        address = title
    if not title:
        return None

    location = {
        "id": (data.get("id") or "").strip() or str(uuid.uuid4()),
        "title": title[:255],
        "address": address[:512],
        "uri": (data.get("uri") or "").strip()[:512],
        "latitude": _to_float(data.get("latitude")),
        "longitude": _to_float(data.get("longitude")),
    }
    return location


def location_key(location):
    uri = (location.get("uri") or "").strip()
    if uri:
        return f"uri:{uri}"
    address = (location.get("address") or "").strip().lower()
    title = (location.get("title") or "").strip().lower()
    return f"addr:{address}|{title}"


def serialize_location(location):
    if not location:
        return None
    return {
        "id": location.get("id"),
        "title": location.get("title") or "",
        "address": location.get("address") or "",
        "uri": location.get("uri") or "",
        "latitude": location.get("latitude"),
        "longitude": location.get("longitude"),
    }


def get_current_location(profile):
    if not profile.location_title and not profile.location_address:
        return None
    return {
        "id": "current",
        "title": profile.location_title or profile.location_address,
        "address": profile.location_address or profile.location_title,
        "uri": "",
        "latitude": (
            float(profile.location_latitude)
            if profile.location_latitude is not None
            else None
        ),
        "longitude": (
            float(profile.location_longitude)
            if profile.location_longitude is not None
            else None
        ),
    }


def set_living_location(profile, location, *, save=True):
    """Сохраняет локацию проживания и обновляет список недавних мест."""
    location = normalize_location_payload(location)
    if not location:
        return None

    profile.location_title = location["title"]
    profile.location_address = location["address"]
    profile.location_latitude = _to_decimal(location.get("latitude"))
    profile.location_longitude = _to_decimal(location.get("longitude"))

    recent = [
        item
        for item in (profile.recent_locations or [])
        if isinstance(item, dict) and location_key(item) != location_key(location)
    ]
    recent.insert(0, serialize_location(location))
    profile.recent_locations = recent[:RECENT_LOCATIONS_LIMIT]

    if save:
        profile.save(
            update_fields=[
                "location_title",
                "location_address",
                "location_latitude",
                "location_longitude",
                "recent_locations",
            ]
        )
    return serialize_location(location)


def delete_recent_location(profile, location_id, *, save=True):
    location_id = (location_id or "").strip()
    if not location_id:
        return False

    recent = list(profile.recent_locations or [])
    filtered = [
        item
        for item in recent
        if not (isinstance(item, dict) and str(item.get("id")) == location_id)
    ]
    if len(filtered) == len(recent):
        return False

    profile.recent_locations = filtered
    if save:
        profile.save(update_fields=["recent_locations"])
    return True
