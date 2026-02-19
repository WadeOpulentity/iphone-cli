"""Companion app client for on-device APIs (HealthKit, Contacts, etc.)."""

from .client import CompanionClient, CompanionNotAvailableError
from .types import CompanionStatus

__all__ = ["CompanionClient", "CompanionNotAvailableError", "CompanionStatus"]
