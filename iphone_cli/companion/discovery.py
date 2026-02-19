"""Bonjour/mDNS discovery for the companion app.

Discovers the companion app's HTTP server on the local network
via the _minime._tcp.local. service type.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Optional


SERVICE_TYPE = "_minime._tcp.local."
DEFAULT_TIMEOUT = 8.0


@dataclass
class CompanionService:
    """A discovered companion app instance."""
    host: str
    port: int
    name: str
    properties: dict
    all_addresses: list[str] = field(default_factory=list)


def _is_link_local_only(addresses: list[str]) -> bool:
    """True if all addresses are link-local (169.254.x.x / fe80::) — indicates an iPhone over USB."""
    if not addresses:
        return False
    for addr in addresses:
        if addr.startswith("169.254.") or addr.startswith("fe80::"):
            continue
        return False
    return True


def _pick_best_address(addresses: list[str]) -> str:
    """Pick the best connectable address from a list."""
    for addr in addresses:
        if addr.startswith("169.254."):
            return addr
    for addr in addresses:
        if "." in addr and not addr.startswith("127."):
            return addr
    return addresses[0]


def _verify_is_iphone(host: str, port: int) -> bool:
    """Quick check: hit /api/status and see if device_name contains 'iPhone'."""
    try:
        import urllib.request
        import json
        url = f"http://{host}:{port}/api/status"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=3) as resp:
            data = json.loads(resp.read())
            name = data.get("device_name", "")
            return "iphone" in name.lower() or "ipad" in name.lower()
    except Exception:
        return False


class CompanionDiscovery:
    """Discovers companion app instances via Bonjour/mDNS.

    Lazy-imports zeroconf to avoid slowing down non-companion commands.
    Prefers verified iPhone instances over Mac/simulator.
    """

    def __init__(self, timeout: float = DEFAULT_TIMEOUT):
        self.timeout = timeout

    def find(self) -> Optional[CompanionService]:
        """Block until a companion app is found or timeout expires.

        Returns CompanionService or None if not found.
        Prefers iPhone instances — verified via /api/status when ambiguous.
        """
        from zeroconf import ServiceBrowser, Zeroconf, ServiceStateChange

        candidates: list[CompanionService] = []
        iphone_found = False
        first_non_iphone_at: float | None = None

        def on_state_change(**kwargs):
            nonlocal iphone_found, first_non_iphone_at
            zc = kwargs.get("zeroconf")
            service_type = kwargs.get("service_type")
            name = kwargs.get("name")
            state_change = kwargs.get("state_change")

            if state_change != ServiceStateChange.Added:
                return
            info = zc.get_service_info(service_type, name)
            if info is None:
                return

            addresses = info.parsed_addresses()
            if not addresses:
                return

            host = _pick_best_address(addresses)
            port = info.port
            props = {}
            if info.properties:
                for k, v in info.properties.items():
                    try:
                        props[k.decode("utf-8", errors="replace")] = v.decode("utf-8", errors="replace")
                    except (AttributeError, UnicodeDecodeError):
                        props[str(k)] = str(v)

            svc = CompanionService(
                host=host, port=port, name=name,
                properties=props, all_addresses=addresses,
            )
            candidates.append(svc)

            if _is_link_local_only(addresses):
                iphone_found = True
            elif first_non_iphone_at is None:
                first_non_iphone_at = time.monotonic()

        zc = Zeroconf()
        try:
            ServiceBrowser(zc, SERVICE_TYPE, handlers=[on_state_change])

            # Wait for discovery — stop early if we find a link-local-only instance.
            # If we find a non-iPhone candidate first, wait a grace period (3s)
            # for a potential iPhone instance before giving up.
            grace_period = 3.0
            deadline = time.monotonic() + self.timeout
            while time.monotonic() < deadline:
                if iphone_found:
                    break
                # If we have a non-iPhone candidate, only wait grace_period more
                if first_non_iphone_at is not None:
                    if time.monotonic() - first_non_iphone_at >= grace_period:
                        break
                time.sleep(0.1)

            if not candidates:
                return None

            # First pass: prefer link-local-only instances (strong iPhone signal)
            for svc in candidates:
                if _is_link_local_only(svc.all_addresses):
                    return svc

            # Second pass: verify each candidate via /api/status
            for svc in candidates:
                if _verify_is_iphone(svc.host, svc.port):
                    return svc

            # Third pass: any non-localhost instance
            for svc in candidates:
                if not svc.host.startswith("127."):
                    return svc

            return candidates[0]
        finally:
            zc.close()
