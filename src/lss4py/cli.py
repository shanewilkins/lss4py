import click
from rich.console import Console

from lss4py.observability import configure_logging


@click.group()
@click.option("--debug", is_flag=True, default=False, help="Enable debug logging.")
def main(debug: bool) -> None:
    configure_logging(debug=debug)


@main.command("doctor")
def doctor() -> None:
    console = Console()
    console.print("[green]lss4py[/green] scaffold is ready.")
