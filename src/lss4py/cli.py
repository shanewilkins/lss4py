"""LSS4PY command-line interface (CLI).

Provides diagnostic and utility commands for LSS4PY package.
"""

import click
from rich.console import Console

from lss4py.observability import configure_logging


@click.group()
@click.option("--debug", is_flag=True, default=False, help="Enable debug logging.")
def main(debug: bool) -> None:
    """LSS4PY command-line entry point."""
    configure_logging(debug=debug)


@main.command("doctor")
def doctor() -> None:
    """Run diagnostic checks for LSS4PY installation and environment."""
    console = Console()
    console.print("[green]lss4py[/green] scaffold is ready.")
