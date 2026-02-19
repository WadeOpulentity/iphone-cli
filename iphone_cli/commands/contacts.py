"""Contacts commands: list, search."""

from __future__ import annotations

import click

from ..output import output_json


@click.group()
def contacts():
    """Access device contacts."""
    pass


@contacts.command(name="list")
@click.pass_context
def list_contacts(ctx):
    """List all contacts."""
    from ..companion import CompanionClient, CompanionNotAvailableError
    try:
        client = CompanionClient(url=ctx.obj.get("companion_url"))
        output_json(client.contacts_list())
    except CompanionNotAvailableError as e:
        output_json({"error": str(e)})
        raise SystemExit(1)


@contacts.command()
@click.argument("query")
@click.pass_context
def search(ctx, query: str):
    """Search contacts by name."""
    from ..companion import CompanionClient, CompanionNotAvailableError
    try:
        client = CompanionClient(url=ctx.obj.get("companion_url"))
        output_json(client.contacts_search(query))
    except CompanionNotAvailableError as e:
        output_json({"error": str(e)})
        raise SystemExit(1)
