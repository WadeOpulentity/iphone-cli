"""Shortcuts commands: run, list."""

from __future__ import annotations

import click

from ..output import output_json


@click.group()
def shortcut():
    """Run and list Siri Shortcuts."""
    pass


@shortcut.command(name="list")
@click.pass_context
def list_shortcuts(ctx):
    """List available shortcuts."""
    from ..companion import CompanionClient, CompanionNotAvailableError
    try:
        client = CompanionClient(url=ctx.obj.get("companion_url"))
        output_json(client.shortcuts_list())
    except CompanionNotAvailableError as e:
        output_json({"error": str(e)})
        raise SystemExit(1)


@shortcut.command()
@click.argument("name")
@click.pass_context
def run(ctx, name: str):
    """Run a shortcut by name."""
    from ..companion import CompanionClient, CompanionNotAvailableError
    try:
        client = CompanionClient(url=ctx.obj.get("companion_url"))
        output_json(client.shortcut_run(name))
    except CompanionNotAvailableError as e:
        output_json({"error": str(e)})
        raise SystemExit(1)
