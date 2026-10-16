"""Main CLI for dominion-setup."""

from __future__ import annotations

import json
import random
from importlib import metadata
from typing import Any

import rich_click as click
from click_default_group import DefaultGroup
from rich.console import Console
from rich.table import Table

from .generator import SetupGenerationError, generate_game
from .loader import load_card_database
from .models import (
    CARD_SETS_WITH_SECOND_EDITIONS,
    Card,
    CardSet,
    CardSetEdition,
    CardType,
    Game,
    KingdomRequirement,
    KingdomSortOrder,
    Pile,
)


class RichDefaultGroup(DefaultGroup, click.RichGroup):  # ty: ignore[invalid-method-override]
    """DefaultGroup with Rich-formatted help output."""


# ``--set`` choices (e.g. "base_2e", "nocturne") and the set and edition each
# one selects. Only sets with a second edition carry an edition suffix.
SET_EDITION_CHOICES: dict[str, tuple[CardSet, CardSetEdition]] = {}
for set_ in CardSet:
    if set_ in CARD_SETS_WITH_SECOND_EDITIONS:
        for edition in CardSetEdition:
            SET_EDITION_CHOICES[f"{set_.name.lower()}_{edition}e"] = (set_, edition)
    else:
        SET_EDITION_CHOICES[set_.name.lower()] = (set_, CardSetEdition.FIRST_EDITION)

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


def _print_card_table(cards: list[Card], *, title: str, numbered: bool) -> None:
    """Print a table of cards (e.g. Landscapes, Ally, Druid Boons), which carry no marks."""
    _print_pile_table([Pile(card) for card in cards], title=title, numbered=numbered)


def _print_game(game: Game, *, seed: int) -> None:
    """Print a Game, generated with *seed*, as rich-formatted table output."""
    # header
    console.print("[bold]Dominion Setup:[/bold]")
    console.print(f"Sets: {', '.join(game.sets_used)}")
    console.print(f"Seed: {seed}")

    # kingdom piles (includes Bane, Obelisk and Trait marks if present)
    console.print()
    _print_pile_table(game.kingdom_piles, title="Kingdom", numbered=True)

    # landscape cards (Events, Landmarks, Projects, Ways, Traits, …)
    if game.landscapes:
        console.print()
        _print_card_table(game.landscapes, title="Landscapes", numbered=False)

    # ally
    if game.ally is not None:
        console.print()
        _print_card_table([game.ally], title="Ally", numbered=False)

    # Prophecy
    if game.prophecy is not None:
        console.print()
        _print_card_table([game.prophecy], title="Prophecy", numbered=False)

    if game.druid_boons:
        console.print()
        _print_card_table(game.druid_boons, title="Druid Boons", numbered=False)

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


def _pile_to_dict(pile: Pile) -> dict[str, Any]:
    """Convert a Pile to a JSON-serializable dict, with the columns of its table row."""
    return {
        "name": pile.card.name,
        "cost": pile.card.cost.to_dict(),
        "types": list(pile.card.types),
        "set": pile.card.display_set,
        "marks": [str(mark) for mark in pile.marks],
    }


def _card_to_dict(card: Card | None) -> dict[str, Any] | None:
    """Convert a card (e.g. a Landscape, Ally) to a JSON-serializable dict, if any."""
    return None if card is None else _pile_to_dict(Pile(card))


def _print_game_json(game: Game, *, seed: int) -> None:
    """Print a Game, generated with *seed*, as JSON."""
    output = {
        "seed": seed,
        "sets": game.sets_used,
        "kingdom": [_pile_to_dict(pile) for pile in game.kingdom_piles],
        "landscapes": [_card_to_dict(card) for card in game.landscapes],
        "ally": _card_to_dict(game.ally),
        "prophecy": _card_to_dict(game.prophecy),
        "druid_boons": [_card_to_dict(card) for card in game.druid_boons],
        "non_supply": [_pile_to_dict(pile) for pile in game.non_supply_piles],
        "basic_supply": [_pile_to_dict(pile) for pile in game.basic_piles],
        "materials": game.materials,
        "setup": game.setup_instructions,
    }
    click.echo(json.dumps(output, indent=2))


def _print_game_names(game: Game) -> None:
    """Print the names of a Game's Kingdom cards, Landscapes, Ally and Prophecy on one line."""
    cards = [*game.kingdom_cards, *game.landscapes, game.ally, game.prophecy]
    click.echo(", ".join(card.name for card in cards if card is not None))


@cli.command()
@click.option(
    "raw_sets_editions",
    "-s",
    "--set",
    multiple=True,
    type=click.Choice(list(SET_EDITION_CHOICES)),
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
@click.option(
    "require_actions",
    "--require-actions",
    is_flag=True,
    help="Require a Kingdom card with +Action(s).",
)
@click.option(
    "require_cards",
    "--require-cards",
    is_flag=True,
    help="Require a Kingdom card with +Card(s).",
)
@click.option(
    "require_buys",
    "--require-buys",
    is_flag=True,
    help="Require a Kingdom card with +Buy(s).",
)
@click.option(
    "require_attack",
    "--require-attack",
    is_flag=True,
    help="Require an Attack Kingdom card.",
)
@click.option(
    "require_reaction",
    "--require-reaction",
    is_flag=True,
    help="Require a Reaction Kingdom card.",
)
@click.option(
    "require_trashing",
    "--require-trashing",
    is_flag=True,
    help="Require a Kingdom card that trashes other cards.",
)
@click.option(
    "--include",
    metavar="CARD",
    multiple=True,
    help="Kingdom card or Landscape to include, from any set (repeatable).",
)
@click.option(
    "--exclude",
    metavar="CARD",
    multiple=True,
    help="Kingdom card or Landscape to exclude (repeatable).",
)
@click.option(
    "--seed",
    type=int,
    default=None,
    help="Seed that reproduces a game. Defaults to a random one.",
)
@click.option(
    "output_format",
    "--format",
    type=click.Choice(["table", "json", "names"]),
    default="table",
    help="Output format: tables, JSON, or a one-line list of card names.",
)
def generate(
    raw_sets_editions: tuple[str, ...],
    sort_order: str,
    use_colony: bool | None,
    use_shelters: bool | None,
    max_landscapes: int,
    require_actions: bool,
    require_cards: bool,
    require_buys: bool,
    require_attack: bool,
    require_reaction: bool,
    require_trashing: bool,
    include: tuple[str, ...],
    exclude: tuple[str, ...],
    seed: int | None,
    output_format: str,
) -> None:
    """Generate a random Dominion game setup."""
    db = load_card_database()
    if seed is None:
        seed = random.randrange(1_000_000)

    requirement_flags = {
        KingdomRequirement.ACTIONS: require_actions,
        KingdomRequirement.CARDS: require_cards,
        KingdomRequirement.BUYS: require_buys,
        KingdomRequirement.ATTACK: require_attack,
        KingdomRequirement.REACTION: require_reaction,
        KingdomRequirement.TRASHING: require_trashing,
    }

    try:
        game = generate_game(
            db,
            sets_editions={SET_EDITION_CHOICES[choice] for choice in raw_sets_editions},
            sort_order=KingdomSortOrder(sort_order),
            use_colony=use_colony,
            use_shelters=use_shelters,
            max_landscapes=max_landscapes,
            requirements=[
                requirement
                for requirement, is_required in requirement_flags.items()
                if is_required
            ],
            include=include,
            exclude=exclude,
            rng=random.Random(seed),
        )
    except SetupGenerationError as exc:
        raise click.UsageError(str(exc)) from exc
    if output_format == "json":
        _print_game_json(game, seed=seed)
    elif output_format == "names":
        _print_game_names(game)
    else:
        _print_game(game, seed=seed)


@cli.command("list-cards")
@click.option(
    "raw_sets_editions",
    "-s",
    "--set",
    multiple=True,
    type=click.Choice(list(SET_EDITION_CHOICES)),
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
    "sort_order",
    "--sort",
    type=click.Choice([s.name.lower() for s in KingdomSortOrder]),
    default=KingdomSortOrder.COST.name.lower(),
    help="Sort order for kingdom cards.",
)
def list_cards(
    raw_sets_editions: tuple[str, ...],
    types: tuple[str, ...],
    cost: int | None,
    sort_order: str,
) -> None:
    """List available kingdom cards with optional filters."""
    db = load_card_database()
    cards = list(db.kingdom_cards.values())

    sets_editions = {SET_EDITION_CHOICES[choice] for choice in raw_sets_editions}

    if sets_editions:
        cards = [
            card
            for card in cards
            if any((card.set, edition) in sets_editions for edition in card.editions)
        ]

    if types:
        type_set = {CardType[t.upper()] for t in types}
        cards = [card for card in cards if type_set <= set(card.types)]

    if cost is not None:
        cards = [card for card in cards if card.cost.coins == cost]

    cards.sort(key=KingdomSortOrder(sort_order).sort_key)
    _print_card_table(cards, title=f"Kingdom Cards ({len(cards)})", numbered=True)


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
