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
