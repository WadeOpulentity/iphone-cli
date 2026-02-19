"""Response dataclasses for companion app API responses."""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any


def to_dict(obj) -> dict:
    """Convert a dataclass to a dict, dropping None values."""
    d = asdict(obj)
    return {k: v for k, v in d.items() if v is not None}


# ------------------------------------------------------------------
# Health
# ------------------------------------------------------------------

@dataclass
class HealthSteps:
    date: str
    count: int
    distance_km: float | None = None
    mock: bool = False


@dataclass
class HealthHeartRate:
    timestamp: str
    bpm: int
    context: str | None = None  # e.g. "resting", "workout", "walking"
    mock: bool = False


@dataclass
class SleepSession:
    date: str
    start: str
    end: str
    duration_hours: float
    stages: dict[str, float] | None = None  # e.g. {"deep": 1.5, "rem": 2.0}
    mock: bool = False


@dataclass
class Workout:
    date: str
    type: str  # e.g. "running", "cycling", "swimming"
    duration_minutes: float
    calories: float | None = None
    distance_km: float | None = None
    heart_rate_avg: int | None = None
    mock: bool = False


# ------------------------------------------------------------------
# Location
# ------------------------------------------------------------------

@dataclass
class Location:
    latitude: float
    longitude: float
    altitude: float | None = None
    accuracy: float | None = None
    timestamp: str | None = None
    mock: bool = False


# ------------------------------------------------------------------
# Contacts
# ------------------------------------------------------------------

@dataclass
class Contact:
    id: str
    first_name: str
    last_name: str
    phone_numbers: list[str] = field(default_factory=list)
    email_addresses: list[str] = field(default_factory=list)
    mock: bool = False


# ------------------------------------------------------------------
# Calendar
# ------------------------------------------------------------------

@dataclass
class CalendarEvent:
    id: str
    title: str
    start: str
    end: str
    location: str | None = None
    calendar_name: str | None = None
    all_day: bool = False
    mock: bool = False


@dataclass
class Reminder:
    id: str
    title: str
    due_date: str | None = None
    completed: bool = False
    list_name: str | None = None
    mock: bool = False


# ------------------------------------------------------------------
# Notifications
# ------------------------------------------------------------------

@dataclass
class Notification:
    id: str
    app: str
    title: str
    body: str | None = None
    timestamp: str | None = None
    mock: bool = False


# ------------------------------------------------------------------
# Shortcuts
# ------------------------------------------------------------------

@dataclass
class Shortcut:
    name: str
    id: str | None = None
    description: str | None = None
    mock: bool = False


@dataclass
class ShortcutResult:
    name: str
    output: Any = None
    error: str | None = None
    mock: bool = False


# ------------------------------------------------------------------
# Companion status
# ------------------------------------------------------------------

@dataclass
class CompanionStatus:
    connected: bool
    version: str | None = None
    device_name: str | None = None
    battery_level: int | None = None
    mock: bool = False
