"""Smoke tests for the dominion-setup package.

These tests verify that the most critical functionality of the package works.
They are designed to catch major breakage and ensure basic operations succeed.
"""

import re
from importlib import metadata

import pytest
from click.testing import CliRunner

import dominion_setup
from dominion_setup.cli import cli
from dominion_setup.generator import generate_game
from dominion_setup.loader import load_card_database
from dominion_setup.models import (
    Card,
    CardCost,
    CardDatabase,
    CardPurpose,
    CardSet,
    CardSetEdition,
    CardType,
    Game,
    KingdomSortOrder,
    Pile,
)


def test_import() -> None:
    """Test importing the package."""
    import dominion_setup  # noqa: F401, PLC0415


def test_public_api_exports() -> None:
    """All documented public names are importable from the top-level package."""
    expected = {
        "CardDatabase",
        "CardSet",
        "Game",
        "KingdomSortOrder",
        "Pile",
        "PileMark",
        "PileMarkKind",
        "generate_game",
        "load_card_database",
    }
    assert expected <= set(dominion_setup.__all__)


def test_load_card_database_returns_card_database() -> None:
    """load_card_database() returns a populated CardDatabase instance."""
    db = load_card_database()
    assert isinstance(db, CardDatabase)
    assert len(db) > 0


def test_load_card_database_has_kingdom_cards() -> None:
    """The database contains kingdom cards."""
    db = load_card_database()
    assert len(db.kingdom_cards) > 0


def test_load_card_database_has_basic_supply_cards() -> None:
    """The database contains all standard basic supply cards."""
    db = load_card_database()
    for name in ("Copper", "Silver", "Gold", "Estate", "Duchy", "Province", "Curse"):
        assert name in db.card_name_to_card, f"Missing basic card: {name}"


def test_load_card_database_has_landscape_cards() -> None:
    """The database contains landscape cards (Events, Projects, Ways, etc.)."""
    db = load_card_database()
    assert len(db.landscape_cards) > 0


def test_load_card_database_covers_multiple_sets() -> None:
    """The database covers cards from more than one expansion set."""
    db = load_card_database()
    sets_represented = {card.set for card in db.kingdom_cards.values()}
    assert len(sets_represented) > 1


def test_load_card_database_iteration() -> None:
    """CardDatabase is iterable and yields Card objects."""
    db = load_card_database()
    cards = list(db)
    assert len(cards) == len(db)
    assert all(isinstance(c, Card) for c in cards)


def test_load_card_database_get_card_by_name() -> None:
    """get_card_by_name returns the correct card."""
    db = load_card_database()
    copper = db.get_card_by_name("Copper")
    assert copper.name == "Copper"


def test_load_card_database_get_card_by_name_missing() -> None:
    """get_card_by_name raises ValueError for an unknown card."""
    db = load_card_database()
    with pytest.raises(ValueError, match="not found"):
        db.get_card_by_name("Nonexistent Card XYZ")


@pytest.fixture(scope="module")
def db() -> CardDatabase:
    """Module-scoped database fixture to avoid repeated I/O in smoke tests."""
    return load_card_database()


@pytest.fixture(scope="module")
def default_game(db: CardDatabase) -> Game:
    """A game generated with default settings, shared across tests in this module."""
    return generate_game(db)


def test_generate_game_returns_game(default_game: Game) -> None:
    """generate_game returns a Game instance."""
    assert isinstance(default_game, Game)


def test_generate_game_has_ten_kingdom_piles(default_game: Game) -> None:
    """A generated game always contains exactly 10 kingdom piles."""
    assert len(default_game.kingdom_piles) == 10


def test_generate_game_kingdom_piles_are_pile_objects(default_game: Game) -> None:
    """Each kingdom pile is a Pile wrapping a Card."""
    for pile in default_game.kingdom_piles:
        assert isinstance(pile, Pile)
        assert isinstance(pile.card, Card)


def test_generate_game_basic_piles_include_standard_supply(default_game: Game) -> None:
    """The basic supply always includes the 7 standard cards."""
    basic_names = {pile.card.name for pile in default_game.basic_piles}
    for name in ("Copper", "Silver", "Gold", "Estate", "Duchy", "Province", "Curse"):
        assert name in basic_names, f"Missing basic supply card: {name}"


def test_generate_game_sets_used_is_non_empty(default_game: Game) -> None:
    """Game.sets_used returns a non-empty list of CardSet values."""
    sets_used = default_game.sets_used
    assert len(sets_used) > 0
    assert all(isinstance(s, CardSet) for s in sets_used)


def test_generate_game_kingdom_cards_property(default_game: Game) -> None:
    """Game.kingdom_cards is a flat list of the cards in kingdom_piles."""
    assert default_game.kingdom_cards == [p.card for p in default_game.kingdom_piles]


def test_generate_game_basic_cards_property(default_game: Game) -> None:
    """Game.basic_cards is a flat list of the cards in basic_piles."""
    assert default_game.basic_cards == [p.card for p in default_game.basic_piles]


@pytest.mark.parametrize("sort_order", list(KingdomSortOrder))
def test_generate_game_all_sort_orders(
    db: CardDatabase, sort_order: KingdomSortOrder
) -> None:
    """generate_game succeeds for every KingdomSortOrder without raising."""
    game = generate_game(db, sort_order=sort_order)
    assert len(game.kingdom_piles) == 10


def test_generate_game_force_colony_on(db: CardDatabase) -> None:
    """use_colony=True adds Colony and Platinum to the basic supply."""
    game = generate_game(db, use_colony=True)
    basic_names = {pile.card.name for pile in game.basic_piles}
    assert "Colony" in basic_names
    assert "Platinum" in basic_names


def test_generate_game_force_colony_off(db: CardDatabase) -> None:
    """use_colony=False excludes Colony and Platinum from the basic supply."""
    game = generate_game(db, use_colony=False)
    basic_names = {pile.card.name for pile in game.basic_piles}
    assert "Colony" not in basic_names
    assert "Platinum" not in basic_names


def test_generate_game_force_shelters_on(db: CardDatabase) -> None:
    """use_shelters=True adds Shelters to the basic supply."""
    game = generate_game(db, use_shelters=True)
    basic_names = {pile.card.name for pile in game.basic_piles}
    assert "Shelters" in basic_names


def test_generate_game_force_shelters_off(db: CardDatabase) -> None:
    """use_shelters=False excludes Shelters from the basic supply."""
    game = generate_game(db, use_shelters=False)
    basic_names = {pile.card.name for pile in game.basic_piles}
    assert "Shelters" not in basic_names


def test_generate_game_single_set_base_2e(db: CardDatabase) -> None:
    """Filtering to Base 2E yields only Base-set kingdom cards."""
    game = generate_game(
        db,
        sets_editions={(CardSet.BASE, CardSetEdition.SECOND_EDITION)},
    )
    assert len(game.kingdom_piles) == 10
    for pile in game.kingdom_piles:
        assert pile.card.set == CardSet.BASE


def test_generate_game_multiple_sets(db: CardDatabase) -> None:
    """Filtering to multiple sets produces a valid 10-pile kingdom."""
    game = generate_game(
        db,
        sets_editions={
            (CardSet.BASE, CardSetEdition.SECOND_EDITION),
            (CardSet.INTRIGUE, CardSetEdition.SECOND_EDITION),
        },
    )
    assert len(game.kingdom_piles) == 10


def test_generate_game_no_landscapes(db: CardDatabase) -> None:
    """max_landscapes=0 produces a game with no landscape cards."""
    game = generate_game(db, max_landscapes=0)
    assert game.landscapes == []


def test_generate_game_too_few_cards_raises(db: CardDatabase) -> None:
    """generate_game raises ValueError when too few candidate cards are available."""
    # Build a DB with only 5 kingdom cards (need 10)
    basic_cards = [
        db.get_card_by_name(n)
        for n in ("Copper", "Silver", "Gold", "Estate", "Duchy", "Province", "Curse")
    ]
    kingdom_cards = [
        Card(
            name=f"Tiny{i}",
            types=(CardType.ACTION,),
            purpose=CardPurpose.KINGDOM_PILE,
            cost=CardCost(coins=i),
            set=CardSet.BASE,
            editions=(CardSetEdition.FIRST_EDITION,),
            quantity=10,
            image=f"tiny{i}.jpg",
            instructions="",
        )
        for i in range(5)
    ]
    tiny_db = CardDatabase([*basic_cards, *kingdom_cards])
    with pytest.raises(ValueError, match="Not enough kingdom cards"):
        generate_game(tiny_db)


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


def test_cli_help(runner: CliRunner) -> None:
    """--help exits cleanly and lists all subcommands."""
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "generate" in result.output
    assert "list-cards" in result.output
    assert "list-sets" in result.output


def test_cli_version(runner: CliRunner) -> None:
    """--version prints the installed package version."""
    result = runner.invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert metadata.version("dominion-setup") in result.output


def test_cli_generate_default(runner: CliRunner) -> None:
    """The default generate command exits cleanly and shows a Kingdom table."""
    result = runner.invoke(cli, ["generate"])
    assert result.exit_code == 0
    assert "Kingdom" in result.output


def test_cli_generate_shows_ten_kingdom_rows(runner: CliRunner) -> None:
    """The generated Kingdom table contains exactly 10 numbered rows."""
    result = runner.invoke(cli, ["generate", "-s", "base_2e"])
    assert result.exit_code == 0
    kingdom_rows = [
        line
        for line in result.output.splitlines()
        if "│" in line and re.search(r"│\s+\d+\s+│", line)
    ]
    assert len(kingdom_rows) == 10


def test_cli_generate_shows_basic_supply(runner: CliRunner) -> None:
    """The generate output includes all standard basic supply cards."""
    result = runner.invoke(cli, ["generate"])
    assert result.exit_code == 0
    for name in ("Copper", "Silver", "Gold", "Estate", "Duchy", "Province", "Curse"):
        assert name in result.output


def test_cli_generate_with_colony(runner: CliRunner) -> None:
    """--colony forces Colony and Platinum into the output."""
    result = runner.invoke(cli, ["generate", "--colony"])
    assert result.exit_code == 0
    assert "Colony" in result.output
    assert "Platinum" in result.output


def test_cli_generate_without_colony(runner: CliRunner) -> None:
    """--no-colony keeps Colony and Platinum out of the output."""
    result = runner.invoke(cli, ["generate", "--no-colony"])
    assert result.exit_code == 0
    assert "Colony" not in result.output
    assert "Platinum" not in result.output


def test_cli_generate_with_shelters(runner: CliRunner) -> None:
    """--shelters forces Shelters into the output."""
    result = runner.invoke(cli, ["generate", "--shelters"])
    assert result.exit_code == 0
    assert "Shelters" in result.output


def test_cli_generate_without_shelters(runner: CliRunner) -> None:
    """--no-shelters keeps Shelters out of the output."""
    result = runner.invoke(cli, ["generate", "--no-shelters"])
    assert result.exit_code == 0
    assert "Shelters" not in result.output


def test_cli_generate_no_landscapes(runner: CliRunner) -> None:
    """--max-landscapes 0 suppresses the Landscapes section."""
    result = runner.invoke(cli, ["generate", "--max-landscapes", "0"])
    assert result.exit_code == 0
    assert "Landscapes" not in result.output


def test_cli_generate_default_is_base_2e(runner: CliRunner) -> None:
    """The default set is Base 2E — Base 1E-only cards must not appear."""
    base_1e_only = {"Chancellor", "Feast", "Spy", "Thief", "Woodcutter"}
    result = runner.invoke(cli, ["generate"])
    assert result.exit_code == 0
    for name in base_1e_only:
        assert name not in result.output


def test_cli_generate_no_args_runs_generate(runner: CliRunner) -> None:
    """Invoking the CLI with no arguments runs generate (the default command)."""
    result = runner.invoke(cli, [])
    assert result.exit_code == 0
    assert "Kingdom" in result.output


def test_cli_list_cards_default(runner: CliRunner) -> None:
    """list-cards without filters exits cleanly and shows a Kingdom Cards table."""
    result = runner.invoke(cli, ["list-cards"])
    assert result.exit_code == 0
    assert "Kingdom Cards" in result.output


def test_cli_list_cards_filter_by_set(runner: CliRunner) -> None:
    """list-cards -s base_2e returns only Base 2E cards."""
    result = runner.invoke(cli, ["list-cards", "-s", "base_2e"])
    assert result.exit_code == 0
    assert "Base, 2E" in result.output


def test_cli_list_cards_filter_by_cost(runner: CliRunner) -> None:
    """list-cards --cost 3 returns only cards with a $3 coin cost."""
    result = runner.invoke(cli, ["list-cards", "--cost", "3"])
    assert result.exit_code == 0
    for line in result.output.splitlines():
        if "│" in line and "$" in line:
            assert "$3" in line


def test_cli_list_cards_no_results(runner: CliRunner) -> None:
    """list-cards --cost 99 returns an empty table without error."""
    result = runner.invoke(cli, ["list-cards", "--cost", "99"])
    assert result.exit_code == 0
    assert "Kingdom Cards (0)" in result.output


def test_cli_list_sets(runner: CliRunner) -> None:
    """list-sets exits cleanly and includes every known expansion."""
    result = runner.invoke(cli, ["list-sets"])
    assert result.exit_code == 0
    assert "Sets" in result.output
    for set_name in ("Base", "Intrigue", "Seaside", "Alchemy", "Prosperity"):
        assert set_name in result.output


def test_cli_list_sets_shows_nonzero_counts(runner: CliRunner) -> None:
    """list-sets shows at least one row with a non-zero kingdom card count."""
    result = runner.invoke(cli, ["list-sets"])
    assert result.exit_code == 0
    data_lines = [
        row
        for row in result.output.splitlines()
        if "│" in row and any(c.isdigit() for c in row)
    ]
    assert len(data_lines) > 0
