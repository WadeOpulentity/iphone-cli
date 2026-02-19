"""Calendar commands: events, reminders."""

from __future__ import annotations

import click

from ..output import output_json


@click.group()
def calendar():
    """Access calendar events and reminders."""
    pass


@calendar.command()
@click.option("--days", default=7, help="Number of days ahead to look")
@click.pass_context
def events(ctx, days: int):
    """List upcoming calendar events."""
    from ..companion import CompanionClient, CompanionNotAvailableError
    try:
        client = CompanionClient(url=ctx.obj.get("companion_url"))
        output_json(client.calendar_events(days))
    except CompanionNotAvailableError as e:
        output_json({"error": str(e)})
        raise SystemExit(1)


@calendar.command()
@click.pass_context
def reminders(ctx):
    """List reminders."""
    from ..companion import CompanionClient, CompanionNotAvailableError
    try:
        client = CompanionClient(url=ctx.obj.get("companion_url"))
        output_json(client.calendar_reminders())
    except CompanionNotAvailableError as e:
        output_json({"error": str(e)})
        raise SystemExit(1)
