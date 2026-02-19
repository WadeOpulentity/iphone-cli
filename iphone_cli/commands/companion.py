"""Companion app management: status, ping."""

from __future__ import annotations

import click

from ..output import output_json


@click.group()
def companion():
    """Check companion app connection status."""
    pass


@companion.command()
@click.pass_context
def status(ctx):
    """Show companion app connection status."""
    from ..companion import CompanionClient, CompanionNotAvailableError
    try:
        client = CompanionClient(url=ctx.obj.get("companion_url"))
        output_json(client.status())
    except CompanionNotAvailableError as e:
        output_json({"error": str(e)})
        raise SystemExit(1)


@companion.command()
@click.pass_context
def ping(ctx):
    """Ping the companion app and measure latency."""
    from ..companion import CompanionClient, CompanionNotAvailableError
    try:
        client = CompanionClient(url=ctx.obj.get("companion_url"))
        output_json(client.ping())
    except CompanionNotAvailableError as e:
        output_json({"error": str(e)})
        raise SystemExit(1)


@companion.command(name="open-url")
@click.argument("url")
@click.pass_context
def open_url(ctx, url: str):
    """Open a URL on the iPhone (supports sms:, tel:, mailto:, https://, etc.).

    Tries WDA first (works regardless of foreground app), then falls back
    to the companion app (activating it first if needed).
    """
    import time

    wda = None
    try:
        from ..core.wda import WDAClient
        wda = WDAClient(url=ctx.obj.get("wda_url", "http://localhost:8100"))
    except Exception:
        pass

    # Strategy 1: WDA open_url — device-level, no foreground requirement
    if wda:
        try:
            wda.open_url(url)
            output_json({"url": url, "status": "opened", "via": "wda"})
            return
        except Exception:
            pass

    # Strategy 2: Companion API — bring companion to foreground first
    if wda:
        try:
            wda.launch_app("com.wadehunter.minime-companion")
            time.sleep(0.5)
        except Exception:
            pass

    from ..companion import CompanionClient, CompanionNotAvailableError
    try:
        client = CompanionClient(url=ctx.obj.get("companion_url"))
        output_json(client.open_url(url))
    except CompanionNotAvailableError as e:
        output_json({"error": str(e)})
        raise SystemExit(1)
