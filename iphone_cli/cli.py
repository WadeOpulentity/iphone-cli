"""CLI entry point for iphone-cli.

Usage:
    iphone screenshot [--save PATH] [--compress]
    iphone tap <x> <y>
    iphone swipe <x1> <y1> <x2> <y2> [--duration 0.5]
    iphone type <text>
    iphone key <button>
    iphone launch <bundle_id>
    iphone kill <bundle_id>
    iphone elements [--raw]
    iphone info
    iphone list-apps
    iphone context
    iphone serve --mcp
    iphone doctor
"""

from __future__ import annotations

import json
import os
import sys
import tempfile

import click

LAST_FIND_PATH = os.path.join(tempfile.gettempdir(), "iphone-cli-last-find.json")


def _save_last_find(results: list[dict]):
    with open(LAST_FIND_PATH, "w") as f:
        json.dump(results, f)


def _load_last_find() -> list[dict]:
    try:
        with open(LAST_FIND_PATH) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []
from rich.console import Console
from rich.json import JSON as RichJSON
from rich.table import Table

console = Console()


def get_wda(url: str | None = None):
    from .core.wda import WDAClient
    return WDAClient(url=url or os.environ.get("WDA_URL", "http://localhost:8100"))


def output_json(data: dict | list):
    """Standard JSON output for agent consumption."""
    if sys.stdout.isatty():
        console.print(RichJSON(json.dumps(data, indent=2, default=str)))
    else:
        print(json.dumps(data, default=str))


@click.group()
@click.option("--wda-url", envvar="WDA_URL", default="http://localhost:8100", help="WDA server URL")
@click.option("--udid", envvar="IPHONE_UDID", default=None, help="Target device UDID")
@click.pass_context
def main(ctx, wda_url: str, udid: str | None):
    """iphone-cli: Give AI agents eyes and hands on any iPhone app."""
    ctx.ensure_object(dict)
    ctx.obj["wda_url"] = wda_url
    ctx.obj["udid"] = udid


# ------------------------------------------------------------------
# Screenshots
# ------------------------------------------------------------------

@main.command()
@click.option("--save", "-o", default=None, help="Save screenshot to file")
@click.option("--compress", is_flag=True, help="Compress for LLM consumption")
@click.pass_context
def screenshot(ctx, save: str | None, compress: bool):
    """Capture the current screen."""
    wda = get_wda(ctx.obj["wda_url"])

    if save:
        path = wda.screenshot_save(save)
        output_json({"status": "saved", "path": path})
    elif compress:
        from .core.screenshot import ScreenCapture
        sc = ScreenCapture(wda)
        b64 = wda.screenshot_base64()
        compressed = sc.compress_screenshot(b64)
        output_json({"screenshot": compressed, "format": "jpeg", "compressed": True})
    else:
        b64 = wda.screenshot_base64()
        output_json({"screenshot": b64, "format": "png"})


# ------------------------------------------------------------------
# Touch actions
# ------------------------------------------------------------------

@main.command()
@click.argument("x", type=str)
@click.argument("y", type=int, required=False, default=None)
@click.pass_context
def tap(ctx, x: str, y: int | None):
    """Tap at coordinates, or tap a recent find result.

    Usage:
        iphone tap 200 450        # tap coordinates
        iphone tap recent         # tap first find result
        iphone tap recent 2       # tap second find result
    """
    if x in ("recent", "last"):
        results = _load_last_find()
        index = (int(y) if y else 1) - 1
        if not results:
            console.print("[red]No recent find results. Run 'iphone find' first.[/red]")
            sys.exit(1)
        if index < 0 or index >= len(results):
            console.print(f"[red]Only {len(results)} result(s) found. Pick 1-{len(results)}.[/red]")
            sys.exit(1)
        target = results[index]
        cx, cy = target["center"]
        wda = get_wda(ctx.obj["wda_url"])
        wda.tap(cx, cy)
        label = target.get("label") or target.get("type", "element")
        output_json({"action": "tap", "target": label, "x": cx, "y": cy, "status": "ok"})
    else:
        if y is None:
            raise click.UsageError("Usage: iphone tap <x> <y>  or  iphone tap recent [N]")
        wda = get_wda(ctx.obj["wda_url"])
        wda.tap(int(x), y)
        output_json({"action": "tap", "x": int(x), "y": y, "status": "ok"})


@main.command()
@click.argument("x", type=int)
@click.argument("y", type=int)
@click.option("--duration", "-d", type=float, default=1.0)
@click.pass_context
def long_press(ctx, x: int, y: int, duration: float):
    """Long press at coordinates."""
    wda = get_wda(ctx.obj["wda_url"])
    wda.long_press(x, y, duration)
    output_json({"action": "long_press", "x": x, "y": y, "duration": duration, "status": "ok"})


@main.command()
@click.argument("x1", type=int)
@click.argument("y1", type=int)
@click.argument("x2", type=int)
@click.argument("y2", type=int)
@click.option("--duration", "-d", type=float, default=0.5)
@click.pass_context
def swipe(ctx, x1: int, y1: int, x2: int, y2: int, duration: float):
    """Swipe from (x1,y1) to (x2,y2)."""
    wda = get_wda(ctx.obj["wda_url"])
    wda.swipe(x1, y1, x2, y2, duration)
    output_json({"action": "swipe", "from": [x1, y1], "to": [x2, y2], "status": "ok"})


@main.command(name="type")
@click.argument("text")
@click.pass_context
def type_text(ctx, text: str):
    """Type text into the focused field."""
    wda = get_wda(ctx.obj["wda_url"])
    wda.type_text(text)
    output_json({"action": "type", "text": text, "status": "ok"})


@main.command()
@click.argument("button", type=click.Choice(["home", "lock", "volume_up", "volume_down"]))
@click.pass_context
def key(ctx, button: str):
    """Press a hardware button."""
    wda = get_wda(ctx.obj["wda_url"])
    match button:
        case "home": wda.press_home()
        case "lock": wda.press_lock()
        case "volume_up": wda.volume_up()
        case "volume_down": wda.volume_down()
    output_json({"action": "key", "button": button, "status": "ok"})


# ------------------------------------------------------------------
# UI elements
# ------------------------------------------------------------------

@main.command()
@click.option("--raw", is_flag=True, help="Return full unfiltered tree")
@click.pass_context
def elements(ctx, raw: bool):
    """List all interactive elements on screen.

    Shows a numbered table of buttons, links, fields, etc.
    Then use 'iphone tap recent N' to tap any of them.

    Use --raw for the full unfiltered element tree.
    """
    wda = get_wda(ctx.obj["wda_url"])

    if raw:
        tree = wda.elements(accessible_only=False)
        output_json(tree)
        return

    from .core.screenshot import ScreenCapture
    sc = ScreenCapture(wda)
    tree = wda.elements(accessible_only=True)
    flat = sc._flatten_elements(tree)
    _save_last_find(flat)

    if not flat:
        console.print("[yellow]No interactive elements found on screen.[/yellow]")
        return

    if sys.stdout.isatty():
        table = Table(title=f"{len(flat)} elements on screen")
        table.add_column("#", style="bold", width=4)
        table.add_column("Type", width=12)
        table.add_column("Label", max_width=40)
        table.add_column("Center", width=10)
        for i, el in enumerate(flat, 1):
            label = el.get("label") or el.get("value") or "-"
            center = f"{el['center'][0]}, {el['center'][1]}" if el.get("center") else "?"
            table.add_row(str(i), el.get("type", "?"), label, center)
        console.print(table)
        console.print(f"\n[dim]Tap any element: iphone tap recent [#][/dim]")
    else:
        print(json.dumps(flat, default=str))


@main.command()
@click.argument("text")
@click.pass_context
def find(ctx, text: str):
    """Find elements containing text.

    Results are numbered so you can tap them:
        iphone find "Login"
        iphone tap recent       # taps first match
        iphone tap recent 2     # taps second match
    """
    wda = get_wda(ctx.obj["wda_url"])
    results = wda.find_by_text(text)
    _save_last_find(results)

    if not results:
        output_json({"query": text, "matches": []})
        return

    # Show numbered results in terminal
    if sys.stdout.isatty():
        from rich.table import Table
        table = Table(title=f"Found {len(results)} match(es) for \"{text}\"")
        table.add_column("#", style="bold")
        table.add_column("Type")
        table.add_column("Label")
        table.add_column("Center")
        for i, el in enumerate(results, 1):
            table.add_row(
                str(i),
                el.get("type", "?"),
                el.get("label", "-"),
                f"{el['center'][0]}, {el['center'][1]}" if el.get("center") else "?",
            )
        console.print(table)
        console.print("\n[dim]Tap a result: iphone tap recent [#][/dim]")
    else:
        print(json.dumps({"query": text, "matches": results}, default=str))


# ------------------------------------------------------------------
# Scroll to element
# ------------------------------------------------------------------

@main.command(name="scroll-to")
@click.argument("text")
@click.option("--tap/--no-tap", default=True, help="Tap the element once found (default: tap)")
@click.option("--max-scrolls", default=15, help="Maximum scroll attempts")
@click.pass_context
def scroll_to(ctx, text: str, tap: bool, max_scrolls: int):
    """Scroll until an element with matching text is visible, then tap it.

    Usage:
        iphone scroll-to "Post your reply"
        iphone scroll-to "Settings" --no-tap
    """
    import time

    wda = get_wda(ctx.obj["wda_url"])
    VISIBLE_TOP = 150
    VISIBLE_BOTTOM = 750

    for attempt in range(max_scrolls + 1):
        results = wda.find_by_text(text)

        if not results:
            # Not in tree at all -- scroll down and retry
            if attempt < max_scrolls:
                wda.swipe(200, 600, 200, 200, duration=0.3)
                time.sleep(0.3)
                continue
            output_json({"error": f"'{text}' not found after {max_scrolls} scrolls"})
            return

        # Find best match (closest to or inside visible area)
        best = None
        best_dist = float("inf")
        for m in results:
            cy = m.get("center", [0, 0])[1]
            if VISIBLE_TOP <= cy <= VISIBLE_BOTTOM:
                best = m
                best_dist = 0
                break
            dist = min(abs(cy - VISIBLE_TOP), abs(cy - VISIBLE_BOTTOM))
            if dist < best_dist:
                best = m
                best_dist = dist

        if not best:
            best = results[0]

        cx, cy = best["center"]

        # Already visible -- done
        if VISIBLE_TOP <= cy <= VISIBLE_BOTTOM:
            _save_last_find([best])
            if tap:
                wda.tap(cx, cy)
                output_json({
                    "status": "found_and_tapped",
                    "label": best.get("label", text)[:100],
                    "center": [cx, cy],
                })
            else:
                output_json({
                    "status": "found",
                    "label": best.get("label", text)[:100],
                    "center": [cx, cy],
                })
            return

        # Off-screen -- scroll toward it
        if cy < VISIBLE_TOP:
            wda.swipe(200, 200, 200, 600, duration=0.3)
        else:
            wda.swipe(200, 600, 200, 200, duration=0.3)
        time.sleep(0.3)

    output_json({"error": f"Could not bring '{text}' into view after {max_scrolls} scrolls"})


# ------------------------------------------------------------------
# App management
# ------------------------------------------------------------------

@main.command()
@click.argument("bundle_id")
@click.pass_context
def launch(ctx, bundle_id: str):
    """Launch an app by bundle ID."""
    wda = get_wda(ctx.obj["wda_url"])
    wda.launch_app(bundle_id)
    output_json({"action": "launch", "bundle_id": bundle_id, "status": "ok"})


@main.command()
@click.argument("bundle_id")
@click.pass_context
def kill(ctx, bundle_id: str):
    """Terminate an app by bundle ID."""
    wda = get_wda(ctx.obj["wda_url"])
    wda.kill_app(bundle_id)
    output_json({"action": "kill", "bundle_id": bundle_id, "status": "ok"})


@main.command(name="active-app")
@click.pass_context
def active_app(ctx):
    """Show the currently active app."""
    wda = get_wda(ctx.obj["wda_url"])
    output_json(wda.active_app())


# ------------------------------------------------------------------
# Context (combined screenshot + elements for agents)
# ------------------------------------------------------------------

@main.command()
@click.option("--compress", is_flag=True, help="Compress screenshot for LLMs")
@click.option("--no-screenshot", is_flag=True, help="Elements only, no image")
@click.pass_context
def context(ctx, compress: bool, no_screenshot: bool):
    """Capture full screen context for agent consumption.

    Returns screenshot + element tree + app info in one call.
    This is the primary command agents should use.
    """
    wda = get_wda(ctx.obj["wda_url"])
    from .core.screenshot import ScreenCapture
    sc = ScreenCapture(wda)
    screen_ctx = sc.capture(include_screenshot=not no_screenshot)

    if compress and not no_screenshot:
        screen_ctx.screenshot_base64 = sc.compress_screenshot(
            screen_ctx.screenshot_base64
        )

    output_json(screen_ctx.for_llm(include_screenshot=not no_screenshot))


# ------------------------------------------------------------------
# Device info
# ------------------------------------------------------------------

@main.command()
@click.pass_context
def info(ctx):
    """Show device information."""
    from .core import Device
    device = Device(udid=ctx.obj.get("udid"))
    output_json(device.info().__dict__)


@main.command()
def devices():
    """List all connected devices."""
    from .core import Device
    output_json(Device.list_connected())


@main.command()
@click.pass_context
def pair(ctx):
    """Pair with the connected iPhone."""
    from .core import Device
    device = Device(udid=ctx.obj.get("udid"))
    output_json(device.pair())


# ------------------------------------------------------------------
# Alerts
# ------------------------------------------------------------------

@main.command(name="alert")
@click.argument("action", type=click.Choice(["text", "accept", "dismiss"]))
@click.pass_context
def alert(ctx, action: str):
    """Handle system alerts/dialogs."""
    wda = get_wda(ctx.obj["wda_url"])
    match action:
        case "text":
            output_json({"alert_text": wda.alert_text()})
        case "accept":
            wda.alert_accept()
            output_json({"action": "alert_accept", "status": "ok"})
        case "dismiss":
            wda.alert_dismiss()
            output_json({"action": "alert_dismiss", "status": "ok"})


# ------------------------------------------------------------------
# Clipboard
# ------------------------------------------------------------------

@main.command()
@click.argument("action", type=click.Choice(["get", "set"]))
@click.argument("text", required=False)
@click.pass_context
def clipboard(ctx, action: str, text: str | None):
    """Get or set clipboard content."""
    wda = get_wda(ctx.obj["wda_url"])
    if action == "get":
        output_json({"clipboard": wda.get_clipboard()})
    elif action == "set":
        if not text:
            raise click.BadParameter("Text required for clipboard set")
        wda.set_clipboard(text)
        output_json({"action": "clipboard_set", "status": "ok"})


# ------------------------------------------------------------------
# Health check
# ------------------------------------------------------------------

@main.command()
@click.pass_context
def doctor(ctx):
    """Check that everything is working."""
    checks = {}

    # Check device connection
    console.print("Checking device connection...", end=" ")
    try:
        from .core import Device
        devices = Device.list_connected()
        if devices:
            console.print("[green]✓[/green]")
            checks["device"] = {"status": "ok", "count": len(devices)}
        else:
            console.print("[red]✗ No devices found[/red]")
            checks["device"] = {"status": "error", "error": "No devices"}
    except Exception as e:
        console.print(f"[red]✗ {e}[/red]")
        checks["device"] = {"status": "error", "error": str(e)}

    # Check WDA
    console.print("Checking WebDriverAgent...", end=" ")
    try:
        wda = get_wda(ctx.obj["wda_url"])
        status = wda.status()
        console.print("[green]✓[/green]")
        checks["wda"] = {"status": "ok", "info": status}
    except Exception as e:
        console.print(f"[red]✗ {e}[/red]")
        checks["wda"] = {"status": "error", "error": str(e)}

    # Check screenshot capability
    if checks.get("wda", {}).get("status") == "ok":
        console.print("Checking screenshots...", end=" ")
        try:
            b64 = wda.screenshot_base64()
            if b64:
                console.print("[green]✓[/green]")
                checks["screenshot"] = {"status": "ok"}
            else:
                console.print("[red]✗ Empty screenshot[/red]")
                checks["screenshot"] = {"status": "error", "error": "Empty"}
        except Exception as e:
            console.print(f"[red]✗ {e}[/red]")
            checks["screenshot"] = {"status": "error", "error": str(e)}

    console.print()
    all_ok = all(c.get("status") == "ok" for c in checks.values())
    if all_ok:
        console.print("[bold green]All systems operational! 🚀[/bold green]")
    else:
        console.print("[bold yellow]Some checks failed. See above.[/bold yellow]")

    output_json(checks)


# ------------------------------------------------------------------
# MCP Server
# ------------------------------------------------------------------

@main.command()
@click.pass_context
def serve(ctx):
    """Start MCP server exposing all commands as tools."""
    console.print("[bold]Starting iphone-cli MCP server...[/bold]")
    from .mcp.server import run_server
    run_server(wda_url=ctx.obj["wda_url"])


# ------------------------------------------------------------------
# Start (WDA + port forward in one command)
# ------------------------------------------------------------------

@main.command()
@click.option("--udid", envvar="IPHONE_UDID", default=None, help="Device UDID (or set IPHONE_UDID)")
@click.option("--team-id", envvar="IPHONE_TEAM_ID", default=None, help="Apple Developer Team ID (or set IPHONE_TEAM_ID)")
@click.option("--port", default=8100, help="WDA port")
@click.pass_context
def start(ctx, udid: str, team_id: str, port: int):
    """Start WDA + port forwarding. Run this first, then use iphone commands."""
    import subprocess
    import signal
    import time

    if not team_id:
        console.print("[red]--team-id is required (or set IPHONE_TEAM_ID env var)[/red]")
        sys.exit(1)

    if not udid:
        from .core import Device
        devices = Device.list_connected()
        if not devices:
            console.print("[red]No devices found. Plug in your iPhone.[/red]")
            sys.exit(1)
        udid = devices[0]["udid"]
        console.print(f"[dim]Auto-detected device: {udid}[/dim]")

    wda_project = "/tmp/WebDriverAgent/WebDriverAgent.xcodeproj"
    procs = []

    def cleanup(sig=None, frame=None):
        console.print("\n[bold]Shutting down...[/bold]")
        for p in procs:
            try:
                p.terminate()
                p.wait(timeout=5)
            except Exception:
                p.kill()
        sys.exit(0)

    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)

    # Start WDA
    console.print("[bold]Starting WebDriverAgent...[/bold]")
    wda_proc = subprocess.Popen(
        [
            "xcodebuild", "-project", wda_project,
            "-scheme", "WebDriverAgentRunner",
            "-destination", f"id={udid}",
            "-allowProvisioningUpdates",
            f"DEVELOPMENT_TEAM={team_id}",
            "test-without-building",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    procs.append(wda_proc)

    # Start port forward
    time.sleep(3)
    console.print("[bold]Starting port forward...[/bold]")
    fwd_proc = subprocess.Popen(
        ["pymobiledevice3", "usbmux", "forward", str(port), str(port)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    procs.append(fwd_proc)

    # Wait for WDA to be ready
    import requests as req
    for i in range(30):
        try:
            r = req.get(f"http://localhost:{port}/status", timeout=2)
            if r.ok and r.json().get("value", {}).get("ready"):
                console.print(f"[bold green]Ready! WDA running on localhost:{port}[/bold green]")
                console.print("[dim]Use 'iphone' commands in another terminal. Ctrl+C to stop.[/dim]")
                wda_proc.wait()
                cleanup()
                return
        except Exception:
            pass
        time.sleep(1)

    console.print("[bold red]Failed to start WDA after 30s.[/bold red]")
    cleanup()


if __name__ == "__main__":
    main()
