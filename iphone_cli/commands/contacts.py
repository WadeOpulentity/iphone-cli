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


@contacts.command()
@click.option("--first", required=True, help="First name")
@click.option("--last", required=True, help="Last name")
@click.option("--phone", multiple=True, help="Phone number (can specify multiple)")
@click.option("--email", multiple=True, help="Email address (can specify multiple)")
@click.pass_context
def create(ctx, first: str, last: str, phone: tuple, email: tuple):
    """Create a new contact."""
    from ..companion import CompanionClient, CompanionNotAvailableError
    try:
        client = CompanionClient(url=ctx.obj.get("companion_url"))
        output_json(client.contacts_create(
            first, last,
            list(phone) if phone else None,
            list(email) if email else None,
        ))
    except CompanionNotAvailableError as e:
        output_json({"error": str(e)})
        raise SystemExit(1)
