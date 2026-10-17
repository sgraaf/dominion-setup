"""Tests for ``dominion_setup.cli``.

The tests invoke the CLI and parse the tables it prints (see ``parse_tables``),
so they can check exactly which cards it lists.
"""

import json
import subprocess
import sys
from collections.abc import Callable
from importlib import import_module, metadata
from pathlib import Path
from typing import Any, NoReturn

import pytest
from click.testing import CliRunner

from dominion_setup.cli import cli
from dominion_setup.generator import SetupGenerationError
from dominion_setup.models import (
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
    Material,
    Pile,
    PileMark,
    PileMarkKind,
)

BASIC_SUPPLY = ["Copper", "Silver", "Gold", "Estate", "Duchy", "Province", "Curse"]


@pytest.fixture
def config_dir(tmp_path: Path) -> Path:
    """An empty config directory, so the tests never read the user's own config."""
    return tmp_path / "config"


@pytest.fixture
def runner(config_dir: Path, monkeypatch: pytest.MonkeyPatch) -> CliRunner:
    # rich-click forces terminal output (colors, padding) when $GITHUB_ACTIONS
    # is set, which it reads once on import
    monkeypatch.setattr("rich_click.rich_click.FORCE_TERMINAL", False)
    # wide enough that no table cell wraps onto a second line
    return CliRunner(env={"COLUMNS": "200", "XDG_CONFIG_HOME": str(config_dir)})


def write_config(config_dir: Path, text: str) -> None:
    """Write *text* to the ``config.toml`` in *config_dir*."""
    path = config_dir / "dominion-setup" / "config.toml"
    path.parent.mkdir(parents=True)
    path.write_text(text)


@pytest.fixture
def generate_game_calls(monkeypatch: pytest.MonkeyPatch) -> list[dict[str, Any]]:
    """The keyword arguments of each call to ``generate_game``, which returns an empty Game."""
    calls: list[dict[str, Any]] = []

    def _generate_game(*_args: Any, **kwargs: Any) -> Game:  # noqa: ANN401
        calls.append(kwargs)
        return Game(basic_piles=[], kingdom_piles=[])

    monkeypatch.setattr("dominion_setup.cli.generate_game", _generate_game)
    return calls


def parse_tables(output: str) -> dict[str, list[list[str]]]:
    """Parse the tables in *output* into their rows of cells, keyed by title."""
    tables: dict[str, list[list[str]]] = {}
    rows: list[list[str]] = []
    lines = output.splitlines()
    for i, line in enumerate(lines):
        if line.startswith("┏"):  # top border, below the title
            rows = tables[lines[i - 1].strip()] = []
        elif line.startswith("│"):  # body row
            rows.append([cell.strip() for cell in line.strip("│").split("│")])
    return tables


def card_rows(cards: list[Card]) -> list[list[str]]:
    """The numbered rows of a table listing *cards*, as printed by the CLI."""
    return [
        [str(i), card.name, str(card.cost), ", ".join(card.types), card.display_set]
        for i, card in enumerate(cards, start=1)
    ]


# ── Entry points ─────────────────────────────────────────────────────────────


def test_main_module() -> None:
    """Exercise (most of) the code in the `__main__` module."""
    import_module("dominion_setup.__main__")


def test_run_as_module() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "dominion_setup", "--help"],
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0


def test_run_as_executable() -> None:
    # console scripts are installed next to the interpreter, which need not be on PATH
    executable = Path(sys.executable).parent / "dominion-setup"
    result = subprocess.run(  # noqa: S603
        [executable, "--help"],
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0


def test_version(runner: CliRunner) -> None:
    result = runner.invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert result.output == f"cli, version {metadata.version('dominion-setup')}\n"


def test_help_lists_the_commands(runner: CliRunner) -> None:
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    for command in ("generate", "list-cards", "list-sets"):
        assert command in result.output


def test_no_command_runs_generate(runner: CliRunner) -> None:
    result = runner.invoke(cli, [])
    assert result.exit_code == 0
    assert "Kingdom" in parse_tables(result.output)


@pytest.mark.parametrize(
    "args",
    [
        ["generate", "--set", "nonexistent"],
        ["generate", "--sort", "nonexistent"],
        ["generate", "--format", "nonexistent"],
        ["list-cards", "--set", "nonexistent"],
        ["list-cards", "--type", "nonexistent"],
    ],
)
def test_invalid_choice_is_a_usage_error(runner: CliRunner, args: list[str]) -> None:
    assert runner.invoke(cli, args).exit_code == 2


# ── generate ─────────────────────────────────────────────────────────────────


def test_generate_defaults_to_base_2e(runner: CliRunner) -> None:
    result = runner.invoke(cli, ["generate"])
    assert result.exit_code == 0
    tables = parse_tables(result.output)
    kingdom = tables["Kingdom"]
    assert [row[0] for row in kingdom] == [str(i) for i in range(1, 11)]
    assert {row[4] for row in kingdom} <= {"Base", "Base, 2E"}
    assert [row[0] for row in tables["Basic Supply"]] == BASIC_SUPPLY


def test_generate_prints_the_seed(runner: CliRunner) -> None:
    result = runner.invoke(cli, ["generate", "--seed", "42"])
    assert result.exit_code == 0
    assert "Seed: 42" in result.output.splitlines()


def test_generate_same_seed_generates_the_same_game(runner: CliRunner) -> None:
    args = ["generate", "--set", "base_2e", "--set", "intrigue_2e", "--seed", "42"]
    outputs = {runner.invoke(cli, args).output for _ in range(2)}
    assert len(outputs) == 1


def test_generate_without_a_seed_prints_one_that_replays_the_game(
    runner: CliRunner,
) -> None:
    args = ["generate", "--set", "base_2e", "--set", "intrigue_2e"]
    result = runner.invoke(cli, args)
    assert result.exit_code == 0
    (seed,) = (
        line.removeprefix("Seed: ")
        for line in result.output.splitlines()
        if line.startswith("Seed: ")
    )
    assert runner.invoke(cli, [*args, "--seed", seed]).output == result.output


@pytest.mark.parametrize(
    "choices",
    [*([choice] for choice in SET_EDITION_CHOICES), ["base_2e", "intrigue_2e"]],
    ids="+".join,
)
def test_generate_draws_from_the_given_sets(
    runner: CliRunner,
    choices: list[str],
) -> None:
    args = [arg for choice in choices for arg in ("--set", choice)]
    result = runner.invoke(cli, ["generate", *args])
    assert result.exit_code == 0
    allowed_sets = set()
    for choice in choices:
        set_, edition = SET_EDITION_CHOICES[choice]
        allowed_sets |= {str(set_), f"{set_}, {edition}E"}
    for row in parse_tables(result.output)["Kingdom"]:
        assert row[4] in allowed_sets


@pytest.mark.parametrize("sort_order", KingdomSortOrder)
def test_generate_sorts_the_kingdom(
    runner: CliRunner,
    db: CardDatabase,
    sort_order: KingdomSortOrder,
) -> None:
    result = runner.invoke(cli, ["generate", "--sort", sort_order.value])
    assert result.exit_code == 0
    kingdom = [
        db.get_card_by_name(row[1]) for row in parse_tables(result.output)["Kingdom"]
    ]
    assert kingdom == sorted(kingdom, key=sort_order.sort_key)


@pytest.mark.parametrize(
    ("args", "piles", "included"),
    [
        (["--colony"], {"Colony", "Platinum"}, True),
        (["--no-colony", "--set", "prosperity_2e"], {"Colony", "Platinum"}, False),
        (["--shelters"], {"Shelters"}, True),
        (["--no-shelters", "--set", "dark_ages"], {"Shelters"}, False),
    ],
)
def test_generate_forces_basic_piles_on_or_off(
    runner: CliRunner,
    args: list[str],
    piles: set[str],
    included: bool,  # noqa: FBT001
) -> None:
    result = runner.invoke(cli, ["generate", *args])
    assert result.exit_code == 0
    basic_names = {row[0] for row in parse_tables(result.output)["Basic Supply"]}
    expected = piles if included else set()
    assert piles & basic_names == expected


def test_generate_without_landscapes(runner: CliRunner) -> None:
    result = runner.invoke(
        cli,
        ["generate", "--set", "adventures", "--max-landscapes", "0"],
    )
    assert result.exit_code == 0
    assert "Landscapes" not in parse_tables(result.output)


@pytest.mark.parametrize(
    ("flag", "requirement"),
    [
        ("--require-actions", KingdomRequirement.ACTIONS),
        ("--require-cards", KingdomRequirement.CARDS),
        ("--require-buys", KingdomRequirement.BUYS),
        ("--require-attack", KingdomRequirement.ATTACK),
        ("--require-reaction", KingdomRequirement.REACTION),
        ("--require-trashing", KingdomRequirement.TRASHING),
    ],
)
def test_generate_require_flag(
    runner: CliRunner,
    generate_game_calls: list[dict[str, Any]],
    flag: str,
    requirement: KingdomRequirement,
) -> None:
    assert runner.invoke(cli, ["generate", flag]).exit_code == 0
    assert generate_game_calls[0]["requirements"] == [requirement]


def test_generate_requires_the_only_reaction(runner: CliRunner) -> None:
    result = runner.invoke(cli, ["generate", "--set", "base_2e", "--require-reaction"])
    assert result.exit_code == 0
    assert "Moat" in [row[1] for row in parse_tables(result.output)["Kingdom"]]


def test_generate_requirement_without_a_provider_is_a_usage_error(
    runner: CliRunner,
) -> None:
    result = runner.invoke(cli, ["generate", "--set", "alchemy", "--require-reaction"])
    assert result.exit_code == 2
    assert "No Kingdom card in the selected sets provides Reaction" in result.output


def test_generate_includes_and_excludes_cards(
    runner: CliRunner,
    generate_game_calls: list[dict[str, Any]],
) -> None:
    args = ["--include", "Witch", "--include", "Alms", "--exclude", "Moat"]
    assert runner.invoke(cli, ["generate", *args]).exit_code == 0
    assert generate_game_calls[0]["include"] == ("Witch", "Alms")
    assert generate_game_calls[0]["exclude"] == ("Moat",)


def test_generate_includes_a_card_from_another_set(runner: CliRunner) -> None:
    result = runner.invoke(
        cli,
        ["generate", "--set", "base_2e", "--include", "Young Witch"],
    )
    assert result.exit_code == 0
    assert "Young Witch" in [row[1] for row in parse_tables(result.output)["Kingdom"]]


def test_generate_unknown_card_is_a_usage_error(runner: CliRunner) -> None:
    result = runner.invoke(cli, ["generate", "--exclude", "Smithee"])
    assert result.exit_code == 2
    assert "Card 'Smithee' not found" in result.output


def test_generate_prints_every_part_of_the_game(
    runner: CliRunner,
    db: CardDatabase,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    game = Game(
        basic_piles=[Pile(db.get_card_by_name(name)) for name in BASIC_SUPPLY],
        kingdom_piles=[
            Pile(db.get_card_by_name("Hamlet"), marks=(PileMark(PileMarkKind.BANE),)),
            Pile(db.get_card_by_name("Young Witch")),
        ],
        non_supply_piles=[Pile(db.get_card_by_name("Madman"))],
        landscapes=[db.get_card_by_name("Alms")],
        ally=db.get_card_by_name("Architects' Guild"),
        prophecy=db.get_card_by_name("Approaching Army"),
        druid_boons=[db.get_card_by_name("The Earth's Gift")],
        black_market_deck=[db.get_card_by_name("Smithy")],
        materials=[Material.COIN_TOKENS],
        setup_instructions=["Young Witch: Add an extra Kingdom card pile."],
    )
    monkeypatch.setattr(
        "dominion_setup.cli.generate_game",
        lambda *_args, **_kwargs: game,
    )
    result = runner.invoke(cli, ["generate"])
    assert result.exit_code == 0
    tables = parse_tables(result.output)
    assert list(tables) == [
        "Kingdom",
        "Landscapes",
        "Ally",
        "Prophecy",
        "Druid Boons",
        "Non-Supply",
        "Black Market Deck",
        "Basic Supply",
    ]
    assert tables["Kingdom"] == [
        ["1", "Hamlet", "$2", "Action", "Cornucopia & Guilds", "Bane"],
        ["2", "Young Witch", "$4", "Action, Attack", "Cornucopia & Guilds", ""],
    ]
    assert "Materials:\n  • Coin tokens" in result.output
    assert "Setup:\n  • Young Witch: Add an extra Kingdom card pile." in result.output


def test_generate_prints_pile_sizes_for_the_players(runner: CliRunner) -> None:
    result = runner.invoke(cli, ["generate", "--players", "2", "--include", "Gardens"])
    assert result.exit_code == 0
    assert "Players: 2" in result.output
    tables = parse_tables(result.output)
    assert ["Gardens", "$4", "Victory", "Base", "8"] in [
        row[1:] for row in tables["Kingdom"]
    ]
    assert tables["Basic Supply"][0] == ["Copper", "$0", "Treasure", "Base", "46"]


def test_generate_prints_no_pile_sizes_without_players(runner: CliRunner) -> None:
    result = runner.invoke(cli, ["generate"])
    assert result.exit_code == 0
    assert "Players:" not in result.output
    assert parse_tables(result.output)["Basic Supply"][0] == [
        "Copper",
        "$0",
        "Treasure",
        "Base",
    ]


@pytest.mark.parametrize("players", ["1", "7"])
def test_generate_players_must_be_two_to_six(runner: CliRunner, players: str) -> None:
    result = runner.invoke(cli, ["generate", "--players", players])
    assert result.exit_code == 2


def test_generate_formats_pile_sizes_as_json(runner: CliRunner) -> None:
    args = ["generate", "--players", "3", "--include", "Gardens", "--format", "json"]
    result = runner.invoke(cli, args)
    assert result.exit_code == 0
    game = json.loads(result.output)
    assert game["players"] == 3
    assert {pile["name"]: pile["size"] for pile in game["kingdom"]}["Gardens"] == 12


def test_generate_formats_the_game_as_json(
    runner: CliRunner,
    db: CardDatabase,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    game = Game(
        basic_piles=[Pile(db.get_card_by_name("Copper"))],
        kingdom_piles=[
            Pile(db.get_card_by_name("Hamlet"), marks=(PileMark(PileMarkKind.BANE),)),
            Pile(db.get_card_by_name("Young Witch")),
        ],
        non_supply_piles=[Pile(db.get_card_by_name("Madman"))],
        landscapes=[db.get_card_by_name("Alms")],
        ally=db.get_card_by_name("Architects' Guild"),
        prophecy=db.get_card_by_name("Approaching Army"),
        druid_boons=[db.get_card_by_name("The Earth's Gift")],
        black_market_deck=[db.get_card_by_name("Smithy")],
        materials=[Material.COIN_TOKENS],
        setup_instructions=["Young Witch: Add an extra Kingdom card pile."],
    )
    monkeypatch.setattr(
        "dominion_setup.cli.generate_game",
        lambda *_args, **_kwargs: game,
    )
    result = runner.invoke(cli, ["generate", "--seed", "42", "--format", "json"])
    assert result.exit_code == 0

    def card_dict(name: str, *marks: str) -> dict[str, Any]:
        card = db.get_card_by_name(name)
        return {
            "name": card.name,
            "cost": card.cost.to_dict(),
            "types": list(card.types),
            "purpose": str(card.purpose),
            "set": card.display_set,
            "marks": list(marks),
            "size": None,
            "image": card.image,
            "instructions": card.instructions,
        }

    assert json.loads(result.output) == {
        "seed": 42,
        "players": None,
        "sets": [str(set_) for set_ in game.sets_used],
        "kingdom": [card_dict("Hamlet", "Bane"), card_dict("Young Witch")],
        "landscapes": [card_dict("Alms")],
        "ally": card_dict("Architects' Guild"),
        "prophecy": card_dict("Approaching Army"),
        "druid_boons": [card_dict("The Earth's Gift")],
        "non_supply": [card_dict("Madman")],
        "black_market": [card_dict("Smithy")],
        "basic_supply": [card_dict("Copper")],
        "materials": ["Coin tokens"],
        "setup": ["Young Witch: Add an extra Kingdom card pile."],
    }


def test_generate_formats_a_game_without_ally_or_prophecy_as_json(
    runner: CliRunner,
) -> None:
    result = runner.invoke(cli, ["generate", "--seed", "42", "--format", "json"])
    assert result.exit_code == 0
    game = json.loads(result.output)
    assert game["ally"] is None
    assert game["prophecy"] is None
    assert len(game["kingdom"]) == 10


@pytest.mark.parametrize("size", [1, 3])
def test_generate_deals_a_black_market_deck_of_the_given_size(
    runner: CliRunner,
    size: int,
) -> None:
    args = ["generate", "--include", "Black Market", "--format", "json"]
    result = runner.invoke(cli, [*args, "--black-market-size", str(size)])
    assert result.exit_code == 0
    assert len(json.loads(result.output)["black_market"]) == size


def test_generate_black_market_size_must_be_positive(runner: CliRunner) -> None:
    result = runner.invoke(cli, ["generate", "--black-market-size", "0"])
    assert result.exit_code == 2


def test_generate_formats_the_game_as_names(
    runner: CliRunner,
    db: CardDatabase,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    game = Game(
        basic_piles=[Pile(db.get_card_by_name("Copper"))],
        kingdom_piles=[
            Pile(db.get_card_by_name("Hamlet"), marks=(PileMark(PileMarkKind.BANE),)),
            Pile(db.get_card_by_name("Young Witch")),
        ],
        landscapes=[db.get_card_by_name("Alms")],
        ally=db.get_card_by_name("Architects' Guild"),
        prophecy=db.get_card_by_name("Approaching Army"),
    )
    monkeypatch.setattr(
        "dominion_setup.cli.generate_game",
        lambda *_args, **_kwargs: game,
    )
    result = runner.invoke(cli, ["generate", "--format", "names", "--seed", "7"])
    assert result.exit_code == 0
    assert result.stdout == (
        "Hamlet, Young Witch, Alms, Architects' Guild, Approaching Army\n"
    )
    assert result.stderr == "Seed: 7\n"


def test_generate_same_seed_formats_the_same_names(runner: CliRunner) -> None:
    args = ["generate", "--seed", "42"]
    table = parse_tables(runner.invoke(cli, args).output)
    names = runner.invoke(cli, [*args, "--format", "names"]).stdout
    assert names.rstrip("\n").split(", ")[:10] == [row[1] for row in table["Kingdom"]]


def test_generate_setup_error_is_a_usage_error(
    runner: CliRunner,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _raise(*_args: Any, **_kwargs: Any) -> NoReturn:  # noqa: ANN401
        msg = "No eligible Bane card"
        raise SetupGenerationError(msg)

    monkeypatch.setattr("dominion_setup.cli.generate_game", _raise)
    result = runner.invoke(cli, ["generate"])
    assert result.exit_code == 2
    assert "No eligible Bane card" in result.output


def test_generate_unexpected_error_is_not_a_usage_error(
    runner: CliRunner,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _raise(*_args: Any, **_kwargs: Any) -> NoReturn:  # noqa: ANN401
        msg = "Card 'Madman' not found"
        raise ValueError(msg)

    monkeypatch.setattr("dominion_setup.cli.generate_game", _raise)
    result = runner.invoke(cli, ["generate"])
    assert result.exit_code == 1
    assert isinstance(result.exception, ValueError)


def test_generate_passes_the_given_promos(
    runner: CliRunner,
    generate_game_calls: list[dict[str, Any]],
) -> None:
    args = ["--set", "base_2e", "--promo", "Stash", "--promo", "Summon"]
    assert runner.invoke(cli, ["generate", *args]).exit_code == 0
    (kwargs,) = generate_game_calls
    assert kwargs["sets_editions"] == {(CardSet.BASE, CardSetEdition.SECOND_EDITION)}
    assert kwargs["promos"] == ("Stash", "Summon")


@pytest.mark.parametrize("name", ["Smithy", "Smithee"])
def test_generate_promo_that_is_not_a_promo_is_a_usage_error(
    runner: CliRunner,
    name: str,
) -> None:
    result = runner.invoke(cli, ["generate", "--promo", name])
    assert result.exit_code == 2
    assert f"{name!r} is not a Promo card" in result.output


def test_generate_reads_its_defaults_from_the_config_file(
    runner: CliRunner,
    config_dir: Path,
    generate_game_calls: list[dict[str, Any]],
) -> None:
    write_config(
        config_dir,
        """
set = ["intrigue_2e", "seaside_2e"]
promo = ["Stash"]
exclude = ["Masquerade"]
require-buys = true
colony = false
max-landscapes = 1
players = 3
""",
    )
    assert runner.invoke(cli, ["generate"]).exit_code == 0
    (kwargs,) = generate_game_calls
    assert kwargs["sets_editions"] == {
        (CardSet.INTRIGUE, CardSetEdition.SECOND_EDITION),
        (CardSet.SEASIDE, CardSetEdition.SECOND_EDITION),
    }
    assert kwargs["promos"] == ("Stash",)
    assert kwargs["exclude"] == ("Masquerade",)
    assert kwargs["requirements"] == [KingdomRequirement.BUYS]
    assert kwargs["use_colony"] is False
    assert kwargs["max_landscapes"] == 1
    assert kwargs["players"] == 3


def test_generate_options_override_the_config_file(
    runner: CliRunner,
    config_dir: Path,
    generate_game_calls: list[dict[str, Any]],
) -> None:
    write_config(config_dir, 'set = ["intrigue_2e"]\nexclude = ["Masquerade"]\n')
    args = ["--set", "base_2e", "--exclude", "Moat"]
    assert runner.invoke(cli, ["generate", *args]).exit_code == 0
    (kwargs,) = generate_game_calls
    assert kwargs["sets_editions"] == {(CardSet.BASE, CardSetEdition.SECOND_EDITION)}
    assert kwargs["exclude"] == ("Moat",)


def test_generate_reads_the_config_file_in_the_home_directory(
    tmp_path: Path,
    generate_game_calls: list[dict[str, Any]],
) -> None:
    write_config(tmp_path / ".config", "players = 5\n")
    runner = CliRunner(env={"HOME": str(tmp_path), "XDG_CONFIG_HOME": None})
    assert runner.invoke(cli, ["generate"]).exit_code == 0
    assert generate_game_calls[0]["players"] == 5


def test_generate_reads_the_given_config_file(
    runner: CliRunner,
    config_dir: Path,
    tmp_path: Path,
    generate_game_calls: list[dict[str, Any]],
) -> None:
    write_config(config_dir, "players = 5\nmax-landscapes = 1\n")
    path = tmp_path / "game-night.toml"
    path.write_text("players = 3\n")
    args = ["generate", "--config-file", str(path)]
    assert runner.invoke(cli, args).exit_code == 0
    (kwargs,) = generate_game_calls
    assert kwargs["players"] == 3
    assert kwargs["max_landscapes"] == 2  # not read from the default config file


def test_generate_given_config_file_that_does_not_exist_is_a_usage_error(
    runner: CliRunner,
    tmp_path: Path,
) -> None:
    path = tmp_path / "missing.toml"
    result = runner.invoke(cli, ["generate", "--config-file", str(path)])
    assert result.exit_code == 2
    assert "Invalid value for '--config-file'" in result.output


def test_generate_config_value_is_validated(
    runner: CliRunner,
    config_dir: Path,
) -> None:
    write_config(config_dir, "players = 7\n")
    result = runner.invoke(cli, ["generate"])
    assert result.exit_code == 2
    assert "Invalid value for '--players'" in result.output


@pytest.mark.parametrize(
    ("text", "message"),
    [
        ("seats = 4\n", "unknown option 'seats'"),
        ("players = \n", "Invalid value"),
    ],
)
def test_generate_invalid_config_file_is_an_error(
    runner: CliRunner,
    config_dir: Path,
    text: str,
    message: str,
) -> None:
    write_config(config_dir, text)
    result = runner.invoke(cli, ["generate"])
    assert result.exit_code == 1
    assert "config.toml" in result.output
    assert message in result.output


# ── list-cards ───────────────────────────────────────────────────────────────


def is_base_2e(card: Card) -> bool:
    return card.set == CardSet.BASE and CardSetEdition.SECOND_EDITION in card.editions


@pytest.mark.parametrize(
    ("args", "is_listed"),
    [
        pytest.param([], lambda _card: True, id="all"),
        pytest.param(["--set", "base_2e"], is_base_2e, id="set"),
        pytest.param(
            ["--set", "base_2e", "--set", "alchemy"],
            lambda card: is_base_2e(card) or card.set == CardSet.ALCHEMY,
            id="sets",
        ),
        pytest.param(
            ["--type", "attack"],
            lambda card: CardType.ATTACK in card.types,
            id="type",
        ),
        pytest.param(
            ["--type", "treasure", "--type", "victory"],
            lambda card: {CardType.TREASURE, CardType.VICTORY} <= set(card.types),
            id="types",
        ),
        pytest.param(["--cost", "2"], lambda card: card.cost.coins == 2, id="cost"),
        pytest.param(["--cost", "99"], lambda _card: False, id="no cards"),
        pytest.param(
            ["--set", "base_2e", "--type", "action", "--cost", "5"],
            lambda card: (
                is_base_2e(card)
                and CardType.ACTION in card.types
                and card.cost.coins == 5
            ),
            id="set, type and cost",
        ),
    ],
)
def test_list_cards_filters(
    runner: CliRunner,
    db: CardDatabase,
    args: list[str],
    is_listed: Callable[[Card], bool],
) -> None:
    result = runner.invoke(cli, ["list-cards", *args])
    assert result.exit_code == 0
    cards = sorted(
        filter(is_listed, db.kingdom_cards.values()),
        key=KingdomSortOrder.COST.sort_key,
    )
    assert parse_tables(result.output) == {
        f"Kingdom Cards ({len(cards)})": card_rows(cards),
    }


@pytest.mark.parametrize("sort_order", KingdomSortOrder)
def test_list_cards_sorts(
    runner: CliRunner,
    db: CardDatabase,
    sort_order: KingdomSortOrder,
) -> None:
    result = runner.invoke(
        cli,
        ["list-cards", "--set", "base_2e", "--sort", sort_order.value],
    )
    assert result.exit_code == 0
    cards = sorted(
        db.get_cards_by_set_edition(CardSet.BASE, CardSetEdition.SECOND_EDITION),
        key=sort_order.sort_key,
    )
    assert parse_tables(result.output) == {"Kingdom Cards (26)": card_rows(cards)}


# ── list-sets ────────────────────────────────────────────────────────────────


def test_list_sets(runner: CliRunner, db: CardDatabase) -> None:
    result = runner.invoke(cli, ["list-sets"])
    assert result.exit_code == 0
    expected_rows = [
        [
            f"{set_}, {edition}E"
            if set_ in CARD_SETS_WITH_SECOND_EDITIONS
            else str(set_),
            str(len(db.get_cards_by_set_edition(set_, edition))),
        ]
        for set_, edition in SET_EDITION_CHOICES.values()
    ]
    assert parse_tables(result.output) == {"Sets": expected_rows}
