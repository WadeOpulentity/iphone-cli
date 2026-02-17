"""High-level iPhone SDK for programmatic control.

Usage:
    from iphone_cli import iPhone

    phone = iPhone()
    phone.screenshot("screen.png")
    phone.tap(200, 450)
    phone.type_text("hello world")
    phone.launch("com.apple.mobilesafari")
"""

from __future__ import annotations

from typing import Optional

from .core.wda import WDAClient
from .core.screenshot import ScreenCapture, ScreenContext
from .core import Device


class iPhone:
    """High-level interface for controlling an iPhone."""

    def __init__(
        self,
        udid: Optional[str] = None,
        wda_url: str = "http://localhost:8100",
    ):
        self.device = Device(udid=udid)
        self.wda = WDAClient(url=wda_url)
        self._screen = ScreenCapture(self.wda)

    # -- Screen observation --

    def screenshot(self, path: Optional[str] = None) -> str:
        """Take a screenshot. Returns base64 PNG or saves to path."""
        if path:
            return self.wda.screenshot_save(path)
        return self.wda.screenshot_base64()

    def context(self, compress: bool = True) -> ScreenContext:
        """Capture full screen context (screenshot + elements + metadata)."""
        ctx = self._screen.capture()
        if compress:
            ctx.screenshot_base64 = self._screen.compress_screenshot(
                ctx.screenshot_base64
            )
        return ctx

    def elements(self) -> dict:
        """Get the UI element tree."""
        return self.wda.elements()

    def find(self, text: str) -> list[dict]:
        """Find elements containing text."""
        return self.wda.find_by_text(text)

    # -- Touch actions --

    def tap(self, x: int, y: int):
        self.wda.tap(x, y)

    def tap_element(self, element: dict):
        """Tap the center of a found element."""
        rect = element.get("rect", {})
        cx = rect.get("x", 0) + rect.get("width", 0) // 2
        cy = rect.get("y", 0) + rect.get("height", 0) // 2
        self.wda.tap(cx, cy)

    def double_tap(self, x: int, y: int):
        self.wda.double_tap(x, y)

    def long_press(self, x: int, y: int, duration: float = 1.0):
        self.wda.long_press(x, y, duration)

    def swipe(self, x1: int, y1: int, x2: int, y2: int, duration: float = 0.5):
        self.wda.swipe(x1, y1, x2, y2, duration)

    def scroll_down(self, amount: int = 300):
        self.wda.scroll_down(amount)

    def scroll_up(self, amount: int = 300):
        self.wda.scroll_up(amount)

    # -- Text input --

    def type_text(self, text: str):
        self.wda.type_text(text)

    def clear(self):
        self.wda.clear_text()

    # -- App control --

    def launch(self, bundle_id: str):
        self.wda.launch_app(bundle_id)

    def kill(self, bundle_id: str):
        self.wda.kill_app(bundle_id)

    def active_app(self) -> dict:
        return self.wda.active_app()

    # -- Hardware --

    def home(self):
        self.wda.press_home()

    def lock(self):
        self.wda.press_lock()

    def unlock(self):
        self.wda.press_unlock()

    # -- Clipboard --

    def get_clipboard(self) -> str:
        return self.wda.get_clipboard()

    def set_clipboard(self, text: str):
        self.wda.set_clipboard(text)

    # -- Alerts --

    def alert_text(self) -> str | None:
        return self.wda.alert_text()

    def alert_accept(self):
        self.wda.alert_accept()

    def alert_dismiss(self):
        self.wda.alert_dismiss()

    # -- Device info --

    def info(self):
        return self.device.info()


