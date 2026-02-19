"""HTTP client for the companion app running on-device.

Mirrors WDAClient patterns: requests.Session, _get/_post helpers,
retry on connection errors, auto-discovery via mDNS.
"""

from __future__ import annotations

import time
from typing import Any, Optional

import requests


DEFAULT_TIMEOUT = 10
DEFAULT_RETRIES = 2


class CompanionNotAvailableError(Exception):
    """Raised when the companion app cannot be reached."""
    pass


class CompanionClient:
    """Client for the companion app HTTP API.

    Discovers the companion app via mDNS if no explicit URL is given.
    Falls back to COMPANION_URL env var if set.
    """

    def __init__(self, url: Optional[str] = None, timeout: int = DEFAULT_TIMEOUT):
        self.url = url.rstrip("/") if url else None
        self.timeout = timeout
        self.session = requests.Session()

        if self.url is None:
            self.url = self._discover()

    def _discover(self) -> str:
        """Auto-discover companion app via mDNS."""
        try:
            from .discovery import CompanionDiscovery
            service = CompanionDiscovery(timeout=8.0).find()
        except ImportError:
            raise CompanionNotAvailableError(
                "Companion app discovery requires the 'zeroconf' package. "
                "Install it with: pip install zeroconf  — or set COMPANION_URL explicitly."
            )

        if service is None:
            raise CompanionNotAvailableError(
                "Companion app not found. Make sure the minime app is running on your iPhone "
                "and both devices are on the same network, or set --companion-url / COMPANION_URL."
            )
        return f"http://{service.host}:{service.port}"

    # ------------------------------------------------------------------
    # Health endpoints
    # ------------------------------------------------------------------

    def health_steps(self, days: int = 7) -> list[dict]:
        return self._get("/api/health/steps", params={"days": days})

    def health_heartrate(self, limit: int = 10) -> list[dict]:
        return self._get("/api/health/heartrate", params={"limit": limit})

    def health_sleep(self, days: int = 7) -> list[dict]:
        return self._get("/api/health/sleep", params={"days": days})

    def health_workouts(self, days: int = 7) -> list[dict]:
        return self._get("/api/health/workouts", params={"days": days})

    def health_summary(self) -> dict:
        return self._get("/api/health/summary")

    # ------------------------------------------------------------------
    # Location
    # ------------------------------------------------------------------

    def location(self) -> dict:
        return self._get("/api/location")

    # ------------------------------------------------------------------
    # Contacts
    # ------------------------------------------------------------------

    def contacts_list(self) -> list[dict]:
        return self._get("/api/contacts")

    def contacts_search(self, query: str) -> list[dict]:
        return self._get("/api/contacts", params={"q": query})

    # ------------------------------------------------------------------
    # Calendar
    # ------------------------------------------------------------------

    def calendar_events(self, days: int = 7) -> list[dict]:
        return self._get("/api/calendar/events", params={"days": days})

    def calendar_reminders(self) -> list[dict]:
        return self._get("/api/calendar/reminders")

    # ------------------------------------------------------------------
    # Notifications
    # ------------------------------------------------------------------

    def notifications_list(self) -> list[dict]:
        return self._get("/api/notifications")

    # ------------------------------------------------------------------
    # Shortcuts
    # ------------------------------------------------------------------

    def shortcuts_list(self) -> list[dict]:
        return self._get("/api/shortcuts")

    def shortcut_run(self, name: str) -> dict:
        return self._post("/api/shortcuts/run", data={"name": name})

    # ------------------------------------------------------------------
    # Status / ping
    # ------------------------------------------------------------------

    def status(self) -> dict:
        return self._get("/api/status")

    def ping(self) -> dict:
        start = time.monotonic()
        result = self._get("/api/ping")
        elapsed_ms = round((time.monotonic() - start) * 1000, 1)
        result["latency_ms"] = elapsed_ms
        return result

    # ------------------------------------------------------------------
    # Internals (mirrors WDAClient pattern)
    # ------------------------------------------------------------------

    def _get(self, path: str, params: dict | None = None) -> Any:
        return self._request("GET", path, params=params)

    def _post(self, path: str, data: dict | None = None) -> Any:
        return self._request("POST", path, json_data=data)

    def _request(
        self,
        method: str,
        path: str,
        params: dict | None = None,
        json_data: dict | None = None,
    ) -> Any:
        url = f"{self.url}{path}"
        retries = DEFAULT_RETRIES

        for attempt in range(retries + 1):
            try:
                if method == "GET":
                    r = self.session.get(url, params=params, timeout=self.timeout)
                else:
                    r = self.session.post(url, json=json_data, timeout=self.timeout)
                r.raise_for_status()
                return r.json()
            except (requests.ConnectionError, requests.Timeout):
                if attempt < retries:
                    time.sleep(0.5)
                    continue
                raise CompanionNotAvailableError(
                    f"Cannot connect to companion app at {self.url}. "
                    "Make sure the minime app is running on your iPhone."
                )
            except requests.HTTPError as e:
                # Server returned an error (4xx/5xx) — try to extract JSON body
                try:
                    body = e.response.json()
                    return {"error": body.get("error", str(body)), "status_code": e.response.status_code}
                except Exception:
                    return {"error": f"Companion app error: {e.response.status_code} {e.response.reason}", "status_code": e.response.status_code}
