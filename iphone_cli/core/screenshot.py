"""Screenshot capture and context generation for agents.

Combines visual (screenshot) and structural (element tree) data
into a single context payload that agents can reason about.
"""

from __future__ import annotations

import base64
import json
import time
from dataclasses import dataclass, asdict
from io import BytesIO
from typing import Optional

from PIL import Image

from .wda import WDAClient


@dataclass
class ScreenContext:
    """Everything an agent needs to understand the current screen state."""

    screenshot_base64: str
    screen_width: int
    screen_height: int
    active_app: dict
    elements_summary: list[dict]  # Flattened interactive elements
    alert: str | None = None
    timestamp: float = 0.0

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2)

    def for_llm(self, include_screenshot: bool = True) -> dict:
        """Format for LLM consumption — minimal, focused context."""
        ctx = {
            "screen_size": f"{self.screen_width}x{self.screen_height}",
            "app": self.active_app.get("value", {}).get("bundleId", "unknown"),
            "interactive_elements": self.elements_summary[:50],  # Cap for token efficiency
        }
        if self.alert:
            ctx["alert"] = self.alert
        if include_screenshot:
            ctx["screenshot"] = self.screenshot_base64
        return ctx


class ScreenCapture:
    """Captures and processes screen state."""

    def __init__(self, wda: WDAClient):
        self.wda = wda

    def capture(self, include_screenshot: bool = True) -> ScreenContext:
        """Capture full screen context: screenshot + element tree + metadata."""
        # Screenshot
        screenshot_b64 = ""
        if include_screenshot:
            screenshot_b64 = self.wda.screenshot_base64()

        # Screen dimensions
        size = self.wda.screen_size()

        # Active app
        try:
            active_app = self.wda.active_app()
        except Exception:
            active_app = {"value": {"bundleId": "unknown"}}

        # Element tree → flattened interactive list
        try:
            tree = self.wda.elements(accessible_only=True)
            elements = self._flatten_elements(tree)
        except Exception:
            elements = []

        # Alert check
        alert = self.wda.alert_text()

        return ScreenContext(
            screenshot_base64=screenshot_b64,
            screen_width=size.width,
            screen_height=size.height,
            active_app=active_app,
            elements_summary=elements,
            alert=alert,
            timestamp=time.time(),
        )

    def capture_annotated(self, path: str) -> str:
        """Capture screenshot with element bounding boxes overlaid.

        Useful for debugging — shows what the agent 'sees' structurally.
        """
        screenshot_bytes = self.wda.screenshot_bytes()
        tree = self.wda.elements(accessible_only=True)
        elements = self._flatten_elements(tree)

        img = Image.open(BytesIO(screenshot_bytes))
        from PIL import ImageDraw, ImageFont

        draw = ImageDraw.Draw(img)
        for i, el in enumerate(elements):
            rect = el.get("rect", {})
            x, y = rect.get("x", 0), rect.get("y", 0)
            w, h = rect.get("width", 0), rect.get("height", 0)
            draw.rectangle([x, y, x + w, y + h], outline="red", width=2)
            label = el.get("label") or el.get("name") or el.get("type", "")
            draw.text((x + 2, y + 2), f"{i}: {label[:20]}", fill="red")

        img.save(path)
        return path

    def compress_screenshot(self, b64_png: str, max_width: int = 390, quality: int = 60) -> str:
        """Compress screenshot for token-efficient LLM consumption.

        Reduces to ~iPhone logical width and JPEG compression.
        """
        raw = base64.b64decode(b64_png)
        img = Image.open(BytesIO(raw))

        # Resize if needed
        if img.width > max_width:
            ratio = max_width / img.width
            new_size = (max_width, int(img.height * ratio))
            img = img.resize(new_size, Image.LANCZOS)

        # Convert to JPEG
        buf = BytesIO()
        img.convert("RGB").save(buf, format="JPEG", quality=quality)
        return base64.b64encode(buf.getvalue()).decode()

    @staticmethod
    def _parse_frame(frame_str: str) -> dict | None:
        """Parse WDA frame string '{{x, y}, {w, h}}' into a rect dict."""
        import re
        m = re.match(r"\{\{(\d+(?:\.\d+)?),\s*(\d+(?:\.\d+)?)\},\s*\{(\d+(?:\.\d+)?),\s*(\d+(?:\.\d+)?)\}\}", frame_str or "")
        if not m:
            return None
        return {
            "x": int(float(m.group(1))),
            "y": int(float(m.group(2))),
            "width": int(float(m.group(3))),
            "height": int(float(m.group(4))),
        }

    @staticmethod
    def _flatten_elements(tree: dict, depth: int = 0) -> list[dict]:
        """Flatten element tree into a list of interactive elements with coords."""
        results = []

        if not tree:
            return results

        # Handle both "XCUIElementTypeButton" and "Button" formats
        raw_type = tree.get("type", "")
        el_type = raw_type.replace("XCUIElementType", "")
        label = tree.get("label") or tree.get("name")
        value = tree.get("value")

        # Parse rect from either dict or frame string format
        rect = tree.get("rect")
        if not rect and tree.get("frame"):
            rect = ScreenCapture._parse_frame(tree["frame"])

        interactive_types = {
            "Button", "TextField", "TextView", "Switch",
            "Slider", "Link", "SearchField", "SecureTextField",
            "Cell", "StaticText", "Image",
        }

        if el_type in interactive_types and rect and label:
            entry = {
                "type": el_type,
                "label": label,
                "rect": rect,
                "center": [
                    rect["x"] + rect["width"] // 2,
                    rect["y"] + rect["height"] // 2,
                ],
            }
            if value:
                entry["value"] = str(value)[:100]
            results.append(entry)

        for child in tree.get("children", []):
            results.extend(ScreenCapture._flatten_elements(child, depth + 1))

        return results
