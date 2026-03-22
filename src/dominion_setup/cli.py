"""Main CLI for dominion-setup."""

from importlib import metadata

import click
from click_default_group import DefaultGroup


@click.group(
    cls=DefaultGroup,
    default="generate",
    default_if_no_args=True,
    context_settings={"help_option_names": ["-h", "--help"], "show_default": True},
)
@click.version_option(metadata.version("dominion_setup"), "-V", "--version")
def cli() -> None:
    """Dominion game setup generator."""


@cli.command()
def generate(players: int, seed: int | None) -> None:
    """Generate a random Dominion game setup."""
