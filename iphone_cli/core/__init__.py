"""Core device management using pymobiledevice3.

Handles device discovery, pairing, and info retrieval over USB.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class DeviceInfo:
    """Basic device information."""
    udid: str
    name: str
    model: str
    ios_version: str
    battery_level: int | None = None
    wifi_address: str | None = None


class Device:
    """Manages iPhone device connection via pymobiledevice3."""

    def __init__(self, udid: Optional[str] = None):
        self.udid = udid
        self._lockdown = None

    def _get_lockdown(self):
        """Create or reuse a lockdown client."""
        if self._lockdown is None:
            from pymobiledevice3.lockdown import create_using_usbmux

            if self.udid:
                self._lockdown = create_using_usbmux(serial=self.udid)
            else:
                self._lockdown = create_using_usbmux()
                self.udid = self._lockdown.udid
        return self._lockdown

    def info(self) -> DeviceInfo:
        """Get device information."""
        ld = self._get_lockdown()
        values = ld.all_values

        return DeviceInfo(
            udid=values.get("UniqueDeviceID", self.udid or "unknown"),
            name=values.get("DeviceName", "unknown"),
            model=values.get("ProductType", "unknown"),
            ios_version=values.get("ProductVersion", "unknown"),
            battery_level=values.get("BatteryCurrentCapacity"),
            wifi_address=values.get("WiFiAddress"),
        )

    def pair(self) -> dict:
        """Pair with the device (triggers trust dialog on iPhone)."""
        ld = self._get_lockdown()
        try:
            ld.pair()
            return {"status": "paired", "udid": self.udid}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    @staticmethod
    def list_connected() -> list[dict]:
        """List all connected iOS devices."""
        from pymobiledevice3.usbmux import list_devices

        devices = list_devices()
        return [
            {
                "udid": d.serial,
                "connection_type": d.connection_type,
            }
            for d in devices
        ]
