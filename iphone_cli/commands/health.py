"""Health data commands: steps, heart rate, sleep, workouts, summary."""

from __future__ import annotations

import click

from ..output import output_json


@click.group()
def health():
    """Access HealthKit data from the companion app."""
    pass


@health.command()
@click.option("--days", default=7, help="Number of days to retrieve")
@click.pass_context
def steps(ctx, days: int):
    """Get daily step counts."""
    from ..companion import CompanionClient, CompanionNotAvailableError
    try:
        client = CompanionClient(url=ctx.obj.get("companion_url"))
        output_json(client.health_steps(days))
    except CompanionNotAvailableError as e:
        output_json({"error": str(e)})
        raise SystemExit(1)


@health.command()
@click.option("--limit", default=10, help="Number of readings to retrieve")
@click.pass_context
def heartrate(ctx, limit: int):
    """Get recent heart rate readings."""
    from ..companion import CompanionClient, CompanionNotAvailableError
    try:
        client = CompanionClient(url=ctx.obj.get("companion_url"))
        output_json(client.health_heartrate(limit))
    except CompanionNotAvailableError as e:
        output_json({"error": str(e)})
        raise SystemExit(1)


@health.command()
@click.option("--days", default=7, help="Number of days to retrieve")
@click.pass_context
def sleep(ctx, days: int):
    """Get sleep session data."""
    from ..companion import CompanionClient, CompanionNotAvailableError
    try:
        client = CompanionClient(url=ctx.obj.get("companion_url"))
        output_json(client.health_sleep(days))
    except CompanionNotAvailableError as e:
        output_json({"error": str(e)})
        raise SystemExit(1)


@health.command()
@click.option("--days", default=7, help="Number of days to retrieve")
@click.pass_context
def workouts(ctx, days: int):
    """Get recent workouts."""
    from ..companion import CompanionClient, CompanionNotAvailableError
    try:
        client = CompanionClient(url=ctx.obj.get("companion_url"))
        output_json(client.health_workouts(days))
    except CompanionNotAvailableError as e:
        output_json({"error": str(e)})
        raise SystemExit(1)


@health.command()
@click.pass_context
def summary(ctx):
    """Get today's health summary."""
    from ..companion import CompanionClient, CompanionNotAvailableError
    try:
        client = CompanionClient(url=ctx.obj.get("companion_url"))
        output_json(client.health_summary())
    except CompanionNotAvailableError as e:
        output_json({"error": str(e)})
        raise SystemExit(1)
