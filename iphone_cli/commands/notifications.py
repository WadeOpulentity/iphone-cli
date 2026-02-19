"""Notifications commands: list, stream."""

from __future__ import annotations

import time

import click

from ..output import output_json


@click.group()
def notifications():
    """Access device notifications."""
    pass


@notifications.command(name="list")
@click.pass_context
def list_notifications(ctx):
    """List recent notifications."""
    from ..companion import CompanionClient, CompanionNotAvailableError
    try:
        client = CompanionClient(url=ctx.obj.get("companion_url"))
        output_json(client.notifications_list())
    except CompanionNotAvailableError as e:
        output_json({"error": str(e)})
        raise SystemExit(1)


@notifications.command()
@click.option("--interval", default=10, help="Polling interval in seconds")
@click.pass_context
def stream(ctx, interval: int):
    """Stream notifications (polls at interval)."""
    from ..companion import CompanionClient, CompanionNotAvailableError
    try:
        client = CompanionClient(url=ctx.obj.get("companion_url"))
        while True:
            output_json(client.notifications_list())
            time.sleep(interval)
    except CompanionNotAvailableError as e:
        output_json({"error": str(e)})
        raise SystemExit(1)
    except KeyboardInterrupt:
        pass
