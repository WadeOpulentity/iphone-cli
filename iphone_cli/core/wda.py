"""WebDriverAgent client for UI automation.

WDA runs as an app on the iPhone and exposes a REST API for:
- Tapping, swiping, typing
- Reading the UI element tree
- Taking screenshots
- Getting/setting device state

The WDA server is typically at http://localhost:8100 after port-forwarding
via usbmuxd.
"""

from __future__ import annotations

import base64
import json
import time
from dataclasses import dataclass, field, asdict
from typing import Optional

import requests


DEFAULT_WDA_URL = "http://localhost:8100"
DEFAULT_TIMEOUT = 30


@dataclass
class Element:
    """A UI element on screen."""
    uid: str
    type: str
    name: str | None
    label: str | None
    value: str | None
    enabled: bool
    visible: bool
    x: int
    y: int
    width: int
    height: int
    children: list[Element] = field(default_factory=list)

    @property
    def center(self) -> tuple[int, int]:
        return (self.x + self.width // 2, self.y + self.height // 2)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["center"] = list(self.center)
        return d


@dataclass
class ScreenSize:
    width: int
    height: int
    scale: float


class WDAClient:
    """Client for WebDriverAgent REST API."""

    def __init__(self, url: str = DEFAULT_WDA_URL, timeout: int = DEFAULT_TIMEOUT):
        self.url = url.rstrip("/")
        self.timeout = timeout
        self._session_id: Optional[str] = None
        self.session = requests.Session()

    # ------------------------------------------------------------------
    # Session management
    # ------------------------------------------------------------------

    def ensure_session(self) -> str:
        """Create or reuse a WDA session."""
        if self._session_id:
            # Verify session is still alive
            try:
                r = self._get(f"/session/{self._session_id}")
                if r.get("sessionId"):
                    return self._session_id
            except Exception:
                pass

        # Create new session
        r = self._post("/session", {"capabilities": {}})
        self._session_id = r.get("sessionId")
        return self._session_id

    def _s(self) -> str:
        """Get session URL prefix."""
        sid = self.ensure_session()
        return f"/session/{sid}"

    # ------------------------------------------------------------------
    # Screenshots
    # ------------------------------------------------------------------

    def screenshot_base64(self) -> str:
        """Take screenshot, return base64 PNG."""
        r = self._get("/screenshot")
        return r.get("value", "")

    def screenshot_bytes(self) -> bytes:
        """Take screenshot, return raw PNG bytes."""
        b64 = self.screenshot_base64()
        return base64.b64decode(b64)

    def screenshot_save(self, path: str) -> str:
        """Take screenshot and save to file."""
        data = self.screenshot_bytes()
        with open(path, "wb") as f:
            f.write(data)
        return path

    # ------------------------------------------------------------------
    # Touch actions
    # ------------------------------------------------------------------

    def tap(self, x: int, y: int) -> dict:
        """Tap at coordinates using W3C actions for a precise, quick touch."""
        actions = [{
            "type": "pointer",
            "id": "finger1",
            "parameters": {"pointerType": "touch"},
            "actions": [
                {"type": "pointerMove", "duration": 0, "x": x, "y": y},
                {"type": "pointerDown", "button": 0},
                {"type": "pause", "duration": 30},
                {"type": "pointerUp", "button": 0},
            ],
        }]
        try:
            return self._post(f"{self._s()}/actions", {"actions": actions})
        except Exception:
            # Fall back to legacy WDA tap if W3C actions not supported
            return self._post(f"{self._s()}/wda/tap", {"x": x, "y": y})

    def double_tap(self, x: int, y: int) -> dict:
        """Double tap at coordinates."""
        return self._post(f"{self._s()}/wda/doubleTap", {"x": x, "y": y})

    def long_press(self, x: int, y: int, duration: float = 1.0) -> dict:
        """Long press at coordinates."""
        return self._post(f"{self._s()}/wda/touchAndHold", {
            "x": x, "y": y, "duration": duration
        })

    def swipe(self, x1: int, y1: int, x2: int, y2: int, duration: float = 0.5) -> dict:
        """Swipe from (x1,y1) to (x2,y2) using W3C pointer actions for real momentum.

        Uses a fast finger move to generate iOS scroll inertia, unlike
        dragfromtoforduration which drags with zero momentum.
        """
        # Convert duration to ms for W3C actions (clamped for good momentum)
        ms = max(80, min(int(duration * 1000), 300))
        actions = [{
            "type": "pointer",
            "id": "swipe1",
            "parameters": {"pointerType": "touch"},
            "actions": [
                {"type": "pointerMove", "duration": 0, "x": x1, "y": y1},
                {"type": "pointerDown", "button": 0},
                {"type": "pointerMove", "duration": ms, "x": x2, "y": y2},
                {"type": "pointerUp", "button": 0},
            ],
        }]
        try:
            return self._post(f"{self._s()}/actions", {"actions": actions})
        except Exception:
            # Fall back to legacy drag if W3C actions not supported
            return self._post(f"{self._s()}/wda/dragfromtoforduration", {
                "fromX": x1, "fromY": y1,
                "toX": x2, "toY": y2,
                "duration": duration,
            })

    def scroll_down(self, amount: int = 300) -> dict:
        """Scroll down by pixel amount."""
        size = self.screen_size()
        cx, cy = size.width // 2, size.height // 2
        return self.swipe(cx, cy + amount // 2, cx, cy - amount // 2)

    def scroll_up(self, amount: int = 300) -> dict:
        """Scroll up by pixel amount."""
        size = self.screen_size()
        cx, cy = size.width // 2, size.height // 2
        return self.swipe(cx, cy - amount // 2, cx, cy + amount // 2)

    # ------------------------------------------------------------------
    # Text input
    # ------------------------------------------------------------------

    def type_text(self, text: str) -> dict:
        """Type text into the currently focused element."""
        return self._post(f"{self._s()}/wda/keys", {"value": list(text)})

    def clear_text(self) -> dict:
        """Clear text in the currently focused element."""
        # Select all and delete
        focused = self._get_focused_element()
        if focused:
            return self._post(f"{self._s()}/element/{focused}/clear", {})
        return {"status": "no_focused_element"}

    # ------------------------------------------------------------------
    # Hardware buttons
    # ------------------------------------------------------------------

    def press_home(self) -> dict:
        """Press the home button."""
        return self._post("/wda/homescreen", {})

    def press_lock(self) -> dict:
        """Press lock button."""
        return self._post("/wda/lock", {})

    def press_unlock(self) -> dict:
        """Unlock device."""
        return self._post("/wda/unlock", {})

    def volume_up(self) -> dict:
        return self._post("/wda/pressButton", {"name": "volumeUp"})

    def volume_down(self) -> dict:
        return self._post("/wda/pressButton", {"name": "volumeDown"})

    # ------------------------------------------------------------------
    # UI element tree
    # ------------------------------------------------------------------

    def elements(self, accessible_only: bool = True) -> dict:
        """Get the full UI element tree.

        This is the structured representation of everything on screen.
        Agents can use this instead of (or alongside) screenshots for
        understanding screen state.
        """
        r = self._get("/source", params={"format": "json"})
        tree = r.get("value", {})
        if accessible_only:
            tree = self._filter_accessible(tree)
        return tree

    def find_elements(self, using: str, value: str) -> list[dict]:
        """Find elements by various strategies.

        Strategies:
            - "name": accessibility label
            - "class name": element type (e.g., XCUIElementTypeButton)
            - "xpath": XPath expression
            - "predicate string": NSPredicate
        """
        r = self._post(f"{self._s()}/elements", {
            "using": using, "value": value
        })
        return r.get("value", [])

    def get_element_info(self, element_id: str) -> dict:
        """Get useful info (label, type, rect, center) for an element."""
        sid = self._s()
        info = {}

        try:
            r = self._get(f"{sid}/element/{element_id}/rect")
            rect = r.get("value", {})
            info["rect"] = rect
            info["center"] = [
                rect.get("x", 0) + rect.get("width", 0) // 2,
                rect.get("y", 0) + rect.get("height", 0) // 2,
            ]
        except Exception:
            pass

        try:
            r = self._get(f"{sid}/element/{element_id}/attribute/label")
            info["label"] = r.get("value")
        except Exception:
            pass

        try:
            r = self._get(f"{sid}/element/{element_id}/name")
            raw_type = r.get("value", "")
            info["type"] = raw_type.replace("XCUIElementType", "")
        except Exception:
            pass

        return info

    def find_by_text(self, text: str) -> list[dict]:
        """Find elements containing specific text, enriched with coordinates."""
        predicate = f'label CONTAINS "{text}" OR name CONTAINS "{text}" OR value CONTAINS "{text}"'
        raw = self.find_elements("predicate string", predicate)

        results = []
        for el in raw:
            eid = el.get("ELEMENT") or el.get("element-6066-11e4-a52e-4f735466cecf")
            if not eid:
                continue
            info = self.get_element_info(eid)
            if info.get("center"):
                results.append(info)
        return results

    # ------------------------------------------------------------------
    # URL opening
    # ------------------------------------------------------------------

    def open_url(self, url: str) -> dict:
        """Open a URL on the device (any URL scheme: https, sms, tel, mailto, etc.).

        Uses WDA's /url endpoint which calls XCUIDevice to open the URL
        at the device level — works regardless of which app is in the foreground.
        """
        return self._post(f"{self._s()}/url", {"url": url})

    # ------------------------------------------------------------------
    # App management
    # ------------------------------------------------------------------

    def launch_app(self, bundle_id: str) -> dict:
        """Launch an app by bundle ID."""
        return self._post(f"{self._s()}/wda/apps/launch", {
            "bundleId": bundle_id,
        })

    def kill_app(self, bundle_id: str) -> dict:
        """Terminate an app by bundle ID."""
        return self._post(f"{self._s()}/wda/apps/terminate", {
            "bundleId": bundle_id,
        })

    def active_app(self) -> dict:
        """Get info about the currently active app."""
        return self._get(f"{self._s()}/wda/activeAppInfo")

    # ------------------------------------------------------------------
    # Device state
    # ------------------------------------------------------------------

    def screen_size(self) -> ScreenSize:
        """Get screen dimensions."""
        r = self._get(f"{self._s()}/window/size")
        val = r.get("value", {})
        return ScreenSize(
            width=val.get("width", 0),
            height=val.get("height", 0),
            scale=1.0,  # WDA returns logical points
        )

    def is_locked(self) -> bool:
        r = self._get("/wda/locked")
        return r.get("value", False)

    def status(self) -> dict:
        """Check WDA server status."""
        return self._get("/status")

    # ------------------------------------------------------------------
    # Alert handling
    # ------------------------------------------------------------------

    def alert_text(self) -> str | None:
        """Get text of any visible alert/dialog."""
        try:
            r = self._get(f"{self._s()}/alert/text")
            return r.get("value")
        except Exception:
            return None

    def alert_accept(self) -> dict:
        """Accept/dismiss an alert."""
        return self._post(f"{self._s()}/alert/accept", {})

    def alert_dismiss(self) -> dict:
        """Dismiss an alert."""
        return self._post(f"{self._s()}/alert/dismiss", {})

    # ------------------------------------------------------------------
    # Clipboard
    # ------------------------------------------------------------------

    def get_clipboard(self) -> str:
        """Get clipboard content."""
        r = self._post(f"{self._s()}/wda/getPasteboard", {})
        b64 = r.get("value", "")
        return base64.b64decode(b64).decode("utf-8", errors="replace")

    def set_clipboard(self, text: str) -> dict:
        """Set clipboard content."""
        b64 = base64.b64encode(text.encode()).decode()
        return self._post(f"{self._s()}/wda/setPasteboard", {
            "content": b64, "contentType": "plaintext"
        })

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _get(self, path: str, params: dict | None = None) -> dict:
        r = self.session.get(f"{self.url}{path}", params=params, timeout=self.timeout)
        r.raise_for_status()
        return r.json()

    def _post(self, path: str, data: dict) -> dict:
        r = self.session.post(
            f"{self.url}{path}", json=data, timeout=self.timeout
        )
        r.raise_for_status()
        return r.json()

    def _get_focused_element(self) -> str | None:
        """Try to find the currently focused element UID."""
        try:
            elements = self.find_elements(
                "predicate string", "hasFocus == true"
            )
            if elements:
                return elements[0].get("ELEMENT")
        except Exception:
            pass
        return None

    @staticmethod
    def _filter_accessible(tree: dict) -> dict:
        """Strip non-accessible elements to reduce noise for agents."""
        if not tree:
            return tree

        def _walk(node: dict) -> dict | None:
            # Keep nodes that have a label, name, or value
            has_info = any([
                node.get("label"),
                node.get("name"),
                node.get("value"),
                node.get("type") in (
                    "Button", "TextField", "TextView", "Switch",
                    "Slider", "Link", "Image", "StaticText",
                    "SearchField", "SecureTextField",
                    "XCUIElementTypeButton", "XCUIElementTypeTextField",
                    "XCUIElementTypeTextView", "XCUIElementTypeSwitch",
                    "XCUIElementTypeSlider", "XCUIElementTypeLink",
                    "XCUIElementTypeImage", "XCUIElementTypeStaticText",
                    "XCUIElementTypeSearchField", "XCUIElementTypeSecureTextField",
                ),
            ])

            children = [
                c for c in (
                    _walk(child) for child in node.get("children", [])
                ) if c is not None
            ]

            if has_info or children:
                result = {k: v for k, v in node.items() if k != "children" and v}
                if children:
                    result["children"] = children
                return result
            return None

        return _walk(tree) or tree
