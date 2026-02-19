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


@calendar.command(name="create-event")
@click.option("--title", required=True, help="Event title")
@click.option("--start", required=True, help="Start date (ISO8601)")
@click.option("--end", required=True, help="End date (ISO8601)")
@click.option("--location", default=None, help="Event location")
@click.option("--notes", default=None, help="Event notes")
@click.option("--calendar", "calendar_name", default=None, help="Calendar name")
@click.pass_context
def create_event(ctx, title: str, start: str, end: str, location: str | None, notes: str | None, calendar_name: str | None):
    """Create a calendar event."""
    from ..companion import CompanionClient, CompanionNotAvailableError
    try:
        client = CompanionClient(url=ctx.obj.get("companion_url"))
        output_json(client.calendar_create_event(title, start, end, location, notes, calendar_name))
    except CompanionNotAvailableError as e:
        output_json({"error": str(e)})
        raise SystemExit(1)


@calendar.command(name="create-reminder")
@click.option("--title", required=True, help="Reminder title")
@click.option("--due", default=None, help="Due date (ISO8601)")
@click.option("--notes", default=None, help="Reminder notes")
@click.option("--list", "list_name", default=None, help="Reminders list name")
@click.pass_context
def create_reminder(ctx, title: str, due: str | None, notes: str | None, list_name: str | None):
    """Create a reminder."""
    from ..companion import CompanionClient, CompanionNotAvailableError
    try:
        client = CompanionClient(url=ctx.obj.get("companion_url"))
        output_json(client.calendar_create_reminder(title, due, notes, list_name))
    except CompanionNotAvailableError as e:
        output_json({"error": str(e)})
        raise SystemExit(1)
