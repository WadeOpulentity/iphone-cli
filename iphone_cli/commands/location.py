"""Location commands: current, stream."""

from __future__ import annotations

import time

import click

from ..output import output_json


@click.group()
def location():
    """Access device location."""
    pass


@location.command()
@click.pass_context
def current(ctx):
    """Get the current device location."""
    from ..companion import CompanionClient, CompanionNotAvailableError
    try:
        client = CompanionClient(url=ctx.obj.get("companion_url"))
        output_json(client.location())
    except CompanionNotAvailableError as e:
        output_json({"error": str(e)})
        raise SystemExit(1)


@location.command()
@click.option("--interval", default=5, help="Polling interval in seconds")
@click.pass_context
def stream(ctx, interval: int):
    """Stream location updates (polls at interval)."""
    from ..companion import CompanionClient, CompanionNotAvailableError
    try:
        client = CompanionClient(url=ctx.obj.get("companion_url"))
        while True:
            output_json(client.location())
            time.sleep(interval)
    except CompanionNotAvailableError as e:
        output_json({"error": str(e)})
        raise SystemExit(1)
    except KeyboardInterrupt:
        pass
