"""Main CLI for dominion-setup."""

from __future__ import annotations

import json
import os
import random
import tomllib
from importlib import metadata
from pathlib import Path

import rich_click as click
from click.core import ParameterSource
from click_default_group import DefaultGroup
from rich.console import Console
from rich.table import Table

from .generator import (
    MAX_PLAYERS,
    MIN_PLAYERS,
    SetupGenerationError,
    generate_game,
    read_board_code,
)
from .loader import load_card_database
from .models import (
    CARD_SETS_WITH_SECOND_EDITIONS,
    SET_EDITION_CHOICES,
    Card,
    CardDatabase,
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


def _config_path() -> Path:
    """Return the path of the config file, in ``$XDG_CONFIG_HOME`` or ``~/.config``."""
    config_home = os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config"
    return Path(config_home) / "dominion-setup" / "config.toml"


def _read_config(
    ctx: click.Context,
    _param: click.Parameter,
    path: Path | None,
) -> None:
    """Set the defaults of the command's options to the config file's values.

    The config file is the one at *path*, or else the one at ``_config_path()``,
    if any.
    The config file's keys are the options' long names (e.g. ``set`` or
    ``require-buys``).
    """
    if path is None:
        path = _config_path()
    try:
        with path.open("rb") as file:
            config = tomllib.load(file)
    except FileNotFoundError:
        return
    except tomllib.TOMLDecodeError as exc:
        msg = f"Invalid config file {path}: {exc}"
        raise click.ClickException(msg) from exc

    param_names = _long_options(ctx.command)
    # one config file serves every command that reads it, so the keys of the
    # others' options (e.g. generate's require-buys) are known, but not used
    config_commands = [
        command
        for command in cli.commands.values()
        if any(param.name == "config_file" for param in command.params)
    ]
    known_keys = {key for command in config_commands for key in _long_options(command)}
    defaults = {}
    for key, value in config.items():
        if key not in known_keys:
            msg = f"Invalid config file {path}: unknown option {key!r}"
            raise click.ClickException(msg)
        if key in param_names:
            defaults[param_names[key]] = value
    ctx.default_map = defaults


def _long_options(command: click.Command) -> dict[str, str]:
    """Return the parameter name of each of *command*'s long options, by its name without "--"."""
    return {
        opt.removeprefix("--"): param.name
        for param in command.params
        for opt in param.opts
        if opt.startswith("--") and param.expose_value and param.name is not None
    }


def _parse_swaps(
    _ctx: click.Context,
    _param: click.Parameter,
    values: tuple[str, ...],
) -> list[tuple[str, str | None]]:
    """Return the ``CARD[=REPLACEMENT]`` values of ``--swap`` as ``(card, replacement)`` pairs."""
    swaps: list[tuple[str, str | None]] = []
    for value in values:
        card, separator, replacement = value.partition("=")
        if not card or (separator and not replacement):
            msg = f"{value!r} is not of the form CARD or CARD=REPLACEMENT"
            raise click.BadParameter(msg)
        swaps.append((card, replacement or None))
    return swaps


def _card_name(db: CardDatabase, name: str) -> str:
    """Return the name of the card that *name* finds (see ``CardDatabase.find_card``).

    An unknown *name* is returned as it is, for ``generate_game`` to reject.
    """
    card = db.find_card(name)
    return name if card is None else card.name


def _swap_card_names(
    db: CardDatabase,
    swaps: list[tuple[str, str | None]],
) -> list[tuple[str, str | None]]:
    """Return the *swaps* with the names of the cards they find (see ``_card_name``)."""
    return [
        (
            _card_name(db, card),
            None if replacement is None else _card_name(db, replacement),
        )
        for card, replacement in swaps
    ]


def _print_pile_table(piles: list[Pile], *, title: str, numbered: bool) -> None:
    """Print a table of Piles, with Marks and Size columns when any pile has them."""
    has_marks = any(pile.marks for pile in piles)
    has_sizes = any(pile.size is not None for pile in piles)
    table = Table(title=title)
    if numbered:
        table.add_column("#", justify="right", style="dim")
    table.add_column("Name", style="bold")
    table.add_column("Cost", justify="right")
    table.add_column("Types")
    table.add_column("Set")
    if has_marks:
        table.add_column("Marks", style="cyan")
    if has_sizes:
        table.add_column("Size", justify="right")
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
        if has_sizes:
            row.append("" if pile.size is None else str(pile.size))
        table.add_row(*row)
    console.print(table)


def _print_card_table(cards: list[Card], *, title: str, numbered: bool) -> None:
    """Print a table of cards (e.g. Landscapes, Ally, Druid Boons), which carry no marks."""
    _print_pile_table([Pile(card) for card in cards], title=title, numbered=numbered)


def _print_game(game: Game, *, seed: int | None) -> None:
    """Print a Game, generated with *seed* (if any), as rich-formatted table output."""
    # header
    console.print("[bold]Dominion Setup:[/bold]")
    console.print(f"Sets: {', '.join(game.sets_used)}")
    if seed is not None:
        console.print(f"Seed: {seed}")
    # on one line, however wide, so it copies whole
    console.print(f"Code: {game.code}", soft_wrap=True)
    if game.players is not None:
        console.print(f"Players: {game.players}")

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

    if game.black_market_deck:
        console.print()
        _print_card_table(
            game.black_market_deck,
            title="Black Market Deck",
            numbered=False,
        )

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


def _print_game_json(game: Game, *, seed: int | None) -> None:
    """Print a Game, generated with *seed* (if any), as JSON."""
    game_dict = game.to_dict() if seed is None else {"seed": seed, **game.to_dict()}
    click.echo(json.dumps(game_dict, indent=2))


def _print_game_names(game: Game, *, seed: int | None) -> None:
    """Print the names of a Game's Kingdom cards, Landscapes, Ally and Prophecy on one line.

    The *seed* (if any) and the Board code go to stderr, so the line of names
    can be piped on its own.
    """
    if seed is not None:
        click.echo(f"Seed: {seed}", err=True)
    click.echo(f"Code: {game.code}", err=True)
    cards = [*game.kingdom_cards, *game.landscapes, game.ally, game.prophecy]
    click.echo(", ".join(card.name for card in cards if card is not None))


def _print_game_in(output_format: str, game: Game, *, seed: int | None = None) -> None:
    """Print a Game, generated with *seed* (if any), in the ``--format`` *output_format*."""
    if output_format == "json":
        _print_game_json(game, seed=seed)
    elif output_format == "names":
        _print_game_names(game, seed=seed)
    else:
        _print_game(game, seed=seed)


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
    "promos",
    "--promo",
    metavar="CARD",
    multiple=True,
    help="Promo card to draw from, without the rest of the Promo set (repeatable).",
)
@click.option(
    "--black-market-size",
    type=click.IntRange(1),
    default=15,
    help="Number of cards in the Black Market deck, if Black Market is in use.",
)
@click.option(
    "--players",
    type=click.IntRange(MIN_PLAYERS, MAX_PLAYERS),
    default=None,
    help="Number of players, to work out how many cards go in each pile.",
)
@click.option(
    "--seed",
    type=int,
    default=None,
    help="Seed that reproduces a game. Defaults to a random one.",
)
@click.option(
    "swaps",
    "--swap",
    metavar="CARD[=REPLACEMENT]",
    multiple=True,
    callback=_parse_swaps,
    help="Kingdom card, extra pile (e.g. the Bane) or Landscape of the game to swap for a random one, or for REPLACEMENT (repeatable, in order).",
)
@click.option(
    "output_format",
    "--format",
    type=click.Choice(["table", "json", "names"]),
    default="table",
    help="Output format: tables, JSON, or a one-line list of card names.",
)
@click.option(
    "--config-file",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    is_eager=True,  # read before the options it sets the defaults of
    expose_value=False,
    callback=_read_config,
    help="Config file with defaults for these options. [default: dominion-setup/config.toml in $XDG_CONFIG_HOME, or else in ~/.config]",
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
    promos: tuple[str, ...],
    black_market_size: int,
    players: int | None,
    seed: int | None,
    swaps: list[tuple[str, str | None]],
    output_format: str,
) -> None:
    """Generate a random Dominion game setup.

    Options default to the values in the config file (see --config-file), if
    any.
    """
    db = load_card_database()
    if seed is None:
        seed = random.randrange(1_000_000)

    sets_editions = {SET_EDITION_CHOICES[choice] for choice in raw_sets_editions}

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
            sets_editions=sets_editions,
            sort_order=KingdomSortOrder(sort_order),
            use_colony=use_colony,
            use_shelters=use_shelters,
            max_landscapes=max_landscapes,
            requirements=[
                requirement
                for requirement, is_required in requirement_flags.items()
                if is_required
            ],
            include=tuple(_card_name(db, name) for name in include),
            exclude=tuple(_card_name(db, name) for name in exclude),
            promos=tuple(_card_name(db, name) for name in promos),
            black_market_size=black_market_size,
            swaps=_swap_card_names(db, swaps),
            players=players,
            rng=random.Random(seed),
        )
    except SetupGenerationError as exc:
        raise click.UsageError(str(exc)) from exc
    _print_game_in(output_format, game, seed=seed)


@cli.command()
@click.argument("code")
@click.option(
    "raw_sets_editions",
    "-s",
    "--set",
    multiple=True,
    type=click.Choice(list(SET_EDITION_CHOICES)),
    default=(f"{CardSet.BASE.name.lower()}_2e",),
    help="Set(s) to draw what the code leaves out from (repeatable).",
)
@click.option(
    "sort_order",
    "--sort",
    type=click.Choice([s.name.lower() for s in KingdomSortOrder]),
    default=KingdomSortOrder.COST.name.lower(),
    help="Sort order for kingdom cards.",
)
@click.option(
    "--exclude",
    metavar="CARD",
    multiple=True,
    help="Kingdom card or Landscape not to draw (repeatable).",
)
@click.option(
    "promos",
    "--promo",
    metavar="CARD",
    multiple=True,
    help="Promo card to draw from, without the rest of the Promo set (repeatable).",
)
@click.option(
    "--players",
    type=click.IntRange(MIN_PLAYERS, MAX_PLAYERS),
    default=None,
    help="Number of players, over the code's.",
)
@click.option(
    "swaps",
    "--swap",
    metavar="CARD[=REPLACEMENT]",
    multiple=True,
    callback=_parse_swaps,
    help="Kingdom card, extra pile (e.g. the Bane) or Landscape of the game to swap for a random one, or for REPLACEMENT (repeatable, in order).",
)
@click.option(
    "output_format",
    "--format",
    type=click.Choice(["table", "json", "names"]),
    default="table",
    help="Output format: tables, JSON, or a one-line list of card names.",
)
@click.option(
    "--config-file",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    is_eager=True,  # read before the options it sets the defaults of
    expose_value=False,
    callback=_read_config,
    help="Config file with defaults for these options. [default: dominion-setup/config.toml in $XDG_CONFIG_HOME, or else in ~/.config]",
)
@click.pass_context
def setup(
    ctx: click.Context,
    code: str,
    raw_sets_editions: tuple[str, ...],
    sort_order: str,
    exclude: tuple[str, ...],
    promos: tuple[str, ...],
    players: int | None,
    swaps: list[tuple[str, str | None]],
    output_format: str,
) -> None:
    """Set up the game of a Board CODE, or of a whole web app link.

    Anything the code leaves out is drawn, except Colony and Shelters, which are
    off unless the code turns them on. Options default to the values in the
    config file (see --config-file), if any, but the code's number of players
    comes before the config file's.
    """
    db = load_card_database()
    try:
        board, code_players = read_board_code(db, code)
        # unknown keys are ignored, so something that is not a code at all
        # (e.g. a card name) would set up a random game
        if not board.to_code(players=code_players):
            msg = f"Nothing to set up in {code!r}: a Board code is like 'players=4&kingdom=smithy,village'"
            raise click.UsageError(msg)
        is_players_given = (
            ctx.get_parameter_source("players") is ParameterSource.COMMANDLINE
        )
        if code_players is not None and not is_players_given:
            players = code_players
        game = generate_game(
            db,
            sets_editions={SET_EDITION_CHOICES[choice] for choice in raw_sets_editions},
            sort_order=KingdomSortOrder(sort_order),
            exclude=tuple(_card_name(db, name) for name in exclude),
            promos=tuple(_card_name(db, name) for name in promos),
            board=board,
            swaps=_swap_card_names(db, swaps),
            players=players,
        )
    except SetupGenerationError as exc:
        raise click.UsageError(str(exc)) from exc
    _print_game_in(output_format, game)


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
