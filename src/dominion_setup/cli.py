"""Main CLI for dominion-setup."""

from __future__ import annotations

from importlib import metadata

import rich_click as click
from click_default_group import DefaultGroup
from rich.console import Console
from rich.table import Table

from .generator import generate_game
from .loader import load_card_database
from .models import (
    CARD_SETS_WITH_SECOND_EDITIONS,
    Card,
    CardSet,
    CardSetEdition,
    CardType,
    Game,
    KingdomSortOrder,
    Pile,
)
from .utils import card_sort_key, parse_raw_set_edition


class RichDefaultGroup(DefaultGroup, click.RichGroup):  # pyrefly: ignore[inconsistent-inheritance]
    """DefaultGroup with Rich-formatted help output."""


# shared CLI choices
SET_CHOICES: list[str] = []
for set_ in CardSet:
    set_name = set_.name.lower()
    if set_ in CARD_SETS_WITH_SECOND_EDITIONS:
        SET_CHOICES.append(f"{set_name}_1e")
        SET_CHOICES.append(f"{set_name}_2e")
    else:
        SET_CHOICES.append(set_name)

# single shared console for all status output.
console = Console()


@click.group(
    cls=RichDefaultGroup,
    default="generate",
    default_if_no_args=True,
    context_settings={"help_option_names": ["-h", "--help"], "show_default": True},
)
@click.version_option(metadata.version("dominion_setup"), "-V", "--version")
def cli() -> None:
    """Dominion game setup generator."""


def _print_pile_table(piles: list[Pile], *, title: str, numbered: bool) -> None:
    """Print a table of Piles, with a Marks column when any pile carries marks."""
    has_marks = any(pile.marks for pile in piles)
    table = Table(title=title)
    if numbered:
        table.add_column("#", justify="right", style="dim")
    table.add_column("Name", style="bold")
    table.add_column("Cost", justify="right")
    table.add_column("Types")
    table.add_column("Set")
    if has_marks:
        table.add_column("Marks", style="cyan")
    for i, pile in enumerate(piles, start=1):
        row = [
            pile.card.name,
            str(pile.card.cost),
            ", ".join(pile.card.types),
            pile.card.display_set,
        ]
        if numbered:
            row.insert(0, str(i))
        if has_marks:
            row.append(", ".join(str(mark) for mark in pile.marks))
        table.add_row(*row)
    console.print(table)


def _print_card_only_table(*cards: Card, title: str) -> None:
    """Print a small table of cards (e.g. Ally, Druid Boons)."""
    table = Table(title=title)
    table.add_column("Name", style="bold")
    table.add_column("Cost", justify="right")
    table.add_column("Types")
    table.add_column("Set")
    for card in cards:
        table.add_row(
            card.name,
            str(card.cost),
            ", ".join(card.types),
            card.display_set,
        )
    console.print(table)


def _print_game(game: Game) -> None:
    """Print a Game as rich-formatted table output."""
    # header
    console.print("[bold]Dominion Setup:[/bold]")
    console.print(f"Sets: {', '.join(game.sets_used)}")

    # kingdom piles (includes Bane, Obelisk and Trait marks if present)
    console.print()
    _print_pile_table(game.kingdom_piles, title="Kingdom", numbered=True)

    # landscape cards (Events, Landmarks, Projects, Ways, Traits, …)
    if game.landscapes:
        console.print()
        _print_card_only_table(*game.landscapes, title="Landscapes")

    # ally
    if game.ally is not None:
        console.print()
        _print_card_only_table(game.ally, title="Ally")

    # Prophecy
    if game.prophecy is not None:
        console.print()
        _print_card_only_table(game.prophecy, title="Prophecy")

    if game.druid_boons:
        console.print()
        _print_card_only_table(*game.druid_boons, title="Druid Boons")

    # non-supply piles (Prizes / Rewards / Ferryman / Travellers / …)
    if game.non_supply_piles:
        console.print()
        _print_pile_table(game.non_supply_piles, title="Non-Supply", numbered=False)

    # basic supply
    console.print()
    _print_pile_table(game.basic_piles, title="Basic Supply", numbered=False)

    # Materials (mats / tokens)  # noqa: ERA001
    if game.materials:
        console.print()
        console.print("[bold]Materials:[/bold]")
        for material in game.materials:
            console.print(f"  • {material}")

    # setup instructions
    if game.setup_instructions:
        console.print()
        console.print("[bold]Setup:[/bold]")
        for instruction in game.setup_instructions:
            console.print(f"  • {instruction}")


@cli.command()
@click.option(
    "raw_sets_editions",
    "-s",
    "--set",
    multiple=True,
    type=click.Choice(SET_CHOICES),
    default=(f"{CardSet.BASE.name.lower()}_2e",),
    help="Set(s) to include (repeatable).",
)
@click.option(
    "sort_order",
    "--sort",
    type=click.Choice([s.name.lower() for s in KingdomSortOrder]),
    default=KingdomSortOrder.COST.name.lower(),
    help="Sort order for kingdom cards.",
)
@click.option(
    "use_colony",
    "--colony/--no-colony",
    default=None,
    help="Force Platinum/Colony on or off.",
)
@click.option(
    "use_shelters",
    "--shelters/--no-shelters",
    default=None,
    help="Force Shelters on or off.",
)
@click.option(
    "--max-landscapes",
    type=click.IntRange(0),
    default=2,
    help="Maximum number of landscapes to include.",
)
def generate(
    raw_sets_editions: tuple[str, ...],
    sort_order: str,
    use_colony: bool | None,
    use_shelters: bool | None,
    max_landscapes: int,
) -> None:
    """Generate a random Dominion game setup."""
    db = load_card_database()

    try:
        game = generate_game(
            db,
            sets_editions={
                parse_raw_set_edition(raw_set_edition)
                for raw_set_edition in raw_sets_editions
            },
            sort_order=KingdomSortOrder(sort_order),
            use_colony=use_colony,
            use_shelters=use_shelters,
            max_landscapes=max_landscapes,
        )
    except ValueError as exc:
        raise click.UsageError(str(exc)) from exc
    _print_game(game)


def _print_card_table(cards: list[Card]) -> None:
    """Print a list of cards as a rich-formatted table."""
    table = Table(title=f"Kingdom Cards ({len(cards)})")
    table.add_column("#", justify="right", style="dim")
    table.add_column("Name", style="bold")
    table.add_column("Cost", justify="right")
    table.add_column("Types")
    table.add_column("Set")

    for i, card in enumerate(cards, start=1):
        table.add_row(
            str(i),
            card.name,
            str(card.cost),
            ", ".join(card.types),
            card.display_set,
        )

    console.print(table)


@cli.command("list-cards")
@click.option(
    "raw_sets_editions",
    "-s",
    "--set",
    multiple=True,
    type=click.Choice(SET_CHOICES),
    help="Filter by set (repeatable).",
)
@click.option(
    "types",
    "-t",
    "--type",
    multiple=True,
    type=click.Choice([type_.name.lower() for type_ in CardType]),
    help="Filter by card type (repeatable; all must match).",
)
@click.option(
    "--cost",
    type=int,
    default=None,
    help="Filter by exact coin cost.",
)
@click.option(
    "--sort",
    type=click.Choice([s.name.lower() for s in KingdomSortOrder]),
    default=KingdomSortOrder.COST.name.lower(),
    help="Sort order for kingdom cards.",
)
def list_cards(
    raw_sets_editions: tuple[str, ...],
    types: tuple[str, ...],
    cost: int | None,
    sort: str,
) -> None:
    """List available kingdom cards with optional filters."""
    db = load_card_database()
    cards = list(db.kingdom_cards.values())

    sets_editions: set[tuple[CardSet, CardSetEdition]] = {
        parse_raw_set_edition(raw_set_edition) for raw_set_edition in raw_sets_editions
    }

    if sets_editions:
        filtered: set[Card] = set()
        for set_, edition in sets_editions:
            filtered.update(db.get_cards_by_set_edition(set_, edition=edition))
        cards = list(filtered)

    if types:
        type_set = {CardType[t.upper()] for t in types}
        cards = [card for card in cards if type_set <= set(card.types)]

    if cost is not None:
        cards = [card for card in cards if card.cost.coins == cost]

    cards.sort(key=card_sort_key(KingdomSortOrder(sort)))
    _print_card_table(cards)


@cli.command("list-sets")
def list_sets() -> None:
    """List available sets and their kingdom card counts."""
    db = load_card_database()

    table = Table(title="Sets")
    table.add_column("Set", style="bold")
    table.add_column("Kingdom Cards", justify="right")

    for set_ in CardSet:
        if set_ in CARD_SETS_WITH_SECOND_EDITIONS:
            for edition in CardSetEdition:
                count = len(db.get_cards_by_set_edition(set_, edition=edition))
                table.add_row(f"{set_.value}, {edition}E", str(count))
        else:
            count = len(db.get_cards_by_set_edition(set_, CardSetEdition.FIRST_EDITION))
            table.add_row(set_.value, str(count))

    console.print(table)
