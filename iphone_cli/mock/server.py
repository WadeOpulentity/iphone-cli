"""Mock companion HTTP server with Bonjour advertisement.

Serves realistic sample data for all companion API endpoints.
Every response includes "mock": true so it cannot be confused with real data.

Usage:
    python -m iphone_cli.mock [--port 8200] [--no-bonjour]
"""

from __future__ import annotations

import json
import signal
import sys
from datetime import datetime, timedelta
from functools import partial
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

DEFAULT_PORT = 8200


def _now() -> datetime:
    return datetime.now()


def _date_str(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d")


def _iso(dt: datetime) -> str:
    return dt.isoformat()


# ------------------------------------------------------------------
# Sample data generators (dates relative to now)
# ------------------------------------------------------------------

def _health_steps(days: int = 7) -> list[dict]:
    now = _now()
    return [
        {
            "date": _date_str(now - timedelta(days=i)),
            "count": 8000 + i * 500 - (i % 3) * 1200,
            "distance_km": round(5.5 + i * 0.3 - (i % 3) * 0.8, 1),
            "mock": True,
        }
        for i in range(days)
    ]


def _health_heartrate(limit: int = 10) -> list[dict]:
    now = _now()
    contexts = ["resting", "walking", "workout", "resting", "walking"]
    return [
        {
            "timestamp": _iso(now - timedelta(hours=i * 2)),
            "bpm": 65 + i * 3 + (i % 3) * 10,
            "context": contexts[i % len(contexts)],
            "mock": True,
        }
        for i in range(limit)
    ]


def _health_sleep(days: int = 7) -> list[dict]:
    now = _now()
    return [
        {
            "date": _date_str(now - timedelta(days=i)),
            "start": _iso((now - timedelta(days=i)).replace(hour=23, minute=15)),
            "end": _iso((now - timedelta(days=i - 1)).replace(hour=7, minute=30) if i > 0 else now.replace(hour=7, minute=30)),
            "duration_hours": 7.5 + (i % 3) * 0.5,
            "stages": {"deep": 1.5 + (i % 2) * 0.3, "rem": 2.0, "light": 3.5, "awake": 0.5},
            "mock": True,
        }
        for i in range(days)
    ]


def _health_workouts(days: int = 7) -> list[dict]:
    types = ["running", "cycling", "swimming", "yoga", "walking"]
    now = _now()
    return [
        {
            "date": _date_str(now - timedelta(days=i * 2)),
            "type": types[i % len(types)],
            "duration_minutes": 30 + i * 5,
            "calories": 200 + i * 50,
            "distance_km": round(3.0 + i * 0.5, 1) if types[i % len(types)] != "yoga" else None,
            "heart_rate_avg": 130 + i * 5 if types[i % len(types)] != "yoga" else None,
            "mock": True,
        }
        for i in range(min(days, len(types)))
    ]


def _health_summary() -> dict:
    now = _now()
    return {
        "date": _date_str(now),
        "steps": 8432,
        "distance_km": 5.8,
        "calories_active": 320,
        "exercise_minutes": 45,
        "stand_hours": 10,
        "heart_rate_resting": 62,
        "mock": True,
    }


def _location() -> dict:
    return {
        "latitude": 37.7749,
        "longitude": -122.4194,
        "altitude": 10.5,
        "accuracy": 5.0,
        "timestamp": _iso(_now()),
        "mock": True,
    }


def _contacts() -> list[dict]:
    return [
        {"id": "c1", "first_name": "Jane", "last_name": "Smith", "phone_numbers": ["+1-555-0101"], "email_addresses": ["jane@example.com"], "mock": True},
        {"id": "c2", "first_name": "John", "last_name": "Doe", "phone_numbers": ["+1-555-0102", "+1-555-0103"], "email_addresses": ["john@example.com"], "mock": True},
        {"id": "c3", "first_name": "Alice", "last_name": "Johnson", "phone_numbers": ["+1-555-0104"], "email_addresses": ["alice@example.com", "ajohnson@work.com"], "mock": True},
        {"id": "c4", "first_name": "Bob", "last_name": "Williams", "phone_numbers": ["+1-555-0105"], "email_addresses": [], "mock": True},
        {"id": "c5", "first_name": "Jane", "last_name": "Doe", "phone_numbers": ["+1-555-0106"], "email_addresses": ["jane.doe@example.com"], "mock": True},
    ]


def _calendar_events(days: int = 7) -> list[dict]:
    now = _now()
    return [
        {
            "id": f"evt{i}",
            "title": ["Team Standup", "Lunch with Alex", "Project Review", "Gym", "Dentist"][i % 5],
            "start": _iso((now + timedelta(days=i)).replace(hour=9 + i, minute=0)),
            "end": _iso((now + timedelta(days=i)).replace(hour=10 + i, minute=0)),
            "location": ["Zoom", "Cafe Roma", "Room 3B", "24 Hour Fitness", "Dr. Smith's Office"][i % 5],
            "calendar_name": ["Work", "Personal", "Work", "Personal", "Personal"][i % 5],
            "all_day": False,
            "mock": True,
        }
        for i in range(min(days, 5))
    ]


def _reminders() -> list[dict]:
    now = _now()
    return [
        {"id": "r1", "title": "Buy groceries", "due_date": _date_str(now + timedelta(days=1)), "completed": False, "list_name": "Personal", "mock": True},
        {"id": "r2", "title": "Submit report", "due_date": _date_str(now), "completed": False, "list_name": "Work", "mock": True},
        {"id": "r3", "title": "Call dentist", "due_date": None, "completed": True, "list_name": "Personal", "mock": True},
    ]


def _notifications() -> list[dict]:
    now = _now()
    return [
        {"id": "n1", "app": "Messages", "title": "Jane Smith", "body": "Hey, are you free for lunch?", "timestamp": _iso(now - timedelta(minutes=5)), "mock": True},
        {"id": "n2", "app": "Mail", "title": "Project Update", "body": "The deployment is scheduled for...", "timestamp": _iso(now - timedelta(minutes=30)), "mock": True},
        {"id": "n3", "app": "Calendar", "title": "Team Standup in 15 min", "body": "Zoom meeting starting soon", "timestamp": _iso(now - timedelta(hours=1)), "mock": True},
    ]


def _shortcuts() -> list[dict]:
    return [
        {"name": "Morning Routine", "id": "sc1", "description": "Turn on lights, start coffee, read news", "mock": True},
        {"name": "Work Focus", "id": "sc2", "description": "Enable DND, open Slack and email", "mock": True},
        {"name": "Log Water", "id": "sc3", "description": "Log 8oz of water to Health", "mock": True},
    ]


def _companion_status() -> dict:
    return {
        "connected": True,
        "version": "1.0.0",
        "device_name": "Mock iPhone",
        "battery_level": 85,
        "mock": True,
    }


# ------------------------------------------------------------------
# Request handler
# ------------------------------------------------------------------

class MockHandler(BaseHTTPRequestHandler):
    """Handles all companion API endpoints with mock data."""

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")
        params = parse_qs(parsed.query)

        routes = {
            "/api/health/steps": self._health_steps,
            "/api/health/heartrate": self._health_heartrate,
            "/api/health/sleep": self._health_sleep,
            "/api/health/workouts": self._health_workouts,
            "/api/health/summary": self._health_summary,
            "/api/location": self._location,
            "/api/contacts": self._contacts,
            "/api/calendar/events": self._calendar_events,
            "/api/calendar/reminders": self._calendar_reminders,
            "/api/notifications": self._notifications,
            "/api/shortcuts": self._shortcuts,
            "/api/status": self._status,
            "/api/ping": self._ping,
        }

        handler = routes.get(path)
        if handler:
            handler(params)
        else:
            self._json_response({"error": "not found", "mock": True}, status=404)

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")

        content_length = int(self.headers.get("Content-Length", 0))
        body = {}
        if content_length > 0:
            raw = self.rfile.read(content_length)
            try:
                body = json.loads(raw)
            except json.JSONDecodeError:
                pass

        if path == "/api/shortcuts/run":
            self._shortcut_run(body)
        else:
            self._json_response({"error": "not found", "mock": True}, status=404)

    # --- Route handlers ---

    def _health_steps(self, params):
        days = int(params.get("days", [7])[0])
        self._json_response(_health_steps(days))

    def _health_heartrate(self, params):
        limit = int(params.get("limit", [10])[0])
        self._json_response(_health_heartrate(limit))

    def _health_sleep(self, params):
        days = int(params.get("days", [7])[0])
        self._json_response(_health_sleep(days))

    def _health_workouts(self, params):
        days = int(params.get("days", [7])[0])
        self._json_response(_health_workouts(days))

    def _health_summary(self, params):
        self._json_response(_health_summary())

    def _location(self, params):
        self._json_response(_location())

    def _contacts(self, params):
        contacts = _contacts()
        query = params.get("q", [None])[0]
        if query:
            q = query.lower()
            contacts = [
                c for c in contacts
                if q in c["first_name"].lower() or q in c["last_name"].lower()
            ]
        self._json_response(contacts)

    def _calendar_events(self, params):
        days = int(params.get("days", [7])[0])
        self._json_response(_calendar_events(days))

    def _calendar_reminders(self, params):
        self._json_response(_reminders())

    def _notifications(self, params):
        self._json_response(_notifications())

    def _shortcuts(self, params):
        self._json_response(_shortcuts())

    def _status(self, params):
        self._json_response(_companion_status())

    def _ping(self, params):
        self._json_response({"pong": True, "timestamp": _iso(_now()), "mock": True})

    def _shortcut_run(self, body):
        name = body.get("name", "Unknown")
        self._json_response({
            "name": name,
            "output": f"Mock output from '{name}'",
            "error": None,
            "mock": True,
        })

    # --- Helpers ---

    def _json_response(self, data, status=200):
        body = json.dumps(data, default=str).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        """Override to prefix with [mock]."""
        sys.stderr.write(f"[mock] {args[0]}\n")


# ------------------------------------------------------------------
# Bonjour advertisement
# ------------------------------------------------------------------

def _start_bonjour(port: int):
    """Advertise the mock server via Bonjour/mDNS."""
    try:
        import socket
        from zeroconf import Zeroconf, ServiceInfo

        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)

        info = ServiceInfo(
            "_minime._tcp.local.",
            f"iphone-cli-mock._minime._tcp.local.",
            addresses=[socket.inet_aton(local_ip)],
            port=port,
            properties={"version": "1.0.0", "mock": "true"},
        )
        zc = Zeroconf()
        zc.register_service(info)
        print(f"[mock] Bonjour: advertising _minime._tcp on port {port}")
        return zc, info
    except ImportError:
        print("[mock] zeroconf not installed — skipping Bonjour advertisement")
        return None, None
    except Exception as e:
        print(f"[mock] Bonjour advertisement failed: {e}")
        return None, None


# ------------------------------------------------------------------
# Main
# ------------------------------------------------------------------

def main():
    import argparse

    parser = argparse.ArgumentParser(description="Mock companion server for iphone-cli")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help=f"Port to listen on (default: {DEFAULT_PORT})")
    parser.add_argument("--no-bonjour", action="store_true", help="Skip Bonjour/mDNS advertisement")
    args = parser.parse_args()

    zc, svc_info = (None, None)
    if not args.no_bonjour:
        zc, svc_info = _start_bonjour(args.port)

    server = HTTPServer(("0.0.0.0", args.port), MockHandler)
    print(f"[mock] Companion server listening on http://localhost:{args.port}")
    print(f"[mock] Endpoints: /api/status, /api/health/steps, /api/contacts, etc.")
    print(f"[mock] Press Ctrl+C to stop")

    def shutdown(sig, frame):
        print("\n[mock] Shutting down...")
        if zc and svc_info:
            zc.unregister_service(svc_info)
            zc.close()
        server.shutdown()
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        shutdown(None, None)


if __name__ == "__main__":
    main()
