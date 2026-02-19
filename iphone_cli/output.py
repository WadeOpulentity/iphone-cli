"""Shared output utilities used by CLI and command modules."""

from __future__ import annotations

import json
import sys

from rich.console import Console
from rich.json import JSON as RichJSON

console = Console()


def output_json(data: dict | list):
    """Standard JSON output for agent consumption."""
    if sys.stdout.isatty():
        console.print(RichJSON(json.dumps(data, indent=2, default=str)))
    else:
        print(json.dumps(data, default=str))
