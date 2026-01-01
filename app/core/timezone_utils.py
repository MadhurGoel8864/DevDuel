"""Timezone utilities for IST (Indian Standard Time) handling.

This module provides utilities for consistent timezone handling across the application.
All datetime operations should use IST (Asia/Kolkata, UTC+5:30).
"""

from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from pydantic import field_validator

# IST Timezone constant
IST_TIMEZONE = "Asia/Kolkata"


def get_ist_timezone() -> ZoneInfo:
    """Get the IST timezone object.

    Returns:
        ZoneInfo: ZoneInfo object for Asia/Kolkata timezone
    """
    return ZoneInfo(IST_TIMEZONE)


def get_ist_now() -> datetime:
    """Get the current datetime in IST timezone.

    Returns:
        datetime: Current datetime with IST timezone
    """
    return datetime.now(get_ist_timezone())


def convert_to_ist(dt: datetime | None) -> datetime | None:
    """Convert any datetime to IST timezone.

    Args:
        dt: Datetime object to convert (can be naive or timezone-aware)

    Returns:
        datetime: Datetime converted to IST timezone, or None if input is None
    """
    if dt is None:
        return None
    if dt.tzinfo is None:
        # If naive datetime, assume it's UTC and make it aware
        dt = dt.replace(tzinfo=ZoneInfo("UTC"))
    return dt.astimezone(get_ist_timezone())


class ISTDatetimeMixin:
    """Mixin to automatically convert all datetime fields to IST timezone.

    Add this mixin to any Pydantic model to ensure all datetime fields
    are automatically converted to IST timezone without needing field serializers.
    """

    @field_validator("*", mode="before")
    @classmethod
    def convert_datetimes_to_ist(cls, v: Any) -> Any:
        """Automatically convert all datetime fields to IST."""
        if isinstance(v, datetime):
            return convert_to_ist(v)
        return v
