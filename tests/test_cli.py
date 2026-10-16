"""Tests for ``dominion_setup.cli``.

The tests invoke the CLI and parse the tables it prints (see ``parse_tables``),
so they can check exactly which cards it lists.
"""

import subprocess
import sys
from collections.abc import Callable
from importlib import import_module, metadata
from pathlib import Path
from typing import Any, NoReturn

import pytest
from click.testing import CliRunner

from dominion_setup.cli import SET_EDITION_CHOICES, cli
from dominion_setup.generator import SetupGenerationError
from dominion_setup.models import (
    CARD_SETS_WITH_SECOND_EDITIONS,
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
def runner() -> CliRunner:
    # wide enough that no table cell wraps onto a second line
    return CliRunner(env={"COLUMNS": "200"})


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
        [executable, "--help"], capture_output=True, check=False
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
    runner: CliRunner, choices: list[str]
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
    runner: CliRunner, db: CardDatabase, sort_order: KingdomSortOrder
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
        cli, ["generate", "--set", "adventures", "--max-landscapes", "0"]
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
    monkeypatch: pytest.MonkeyPatch,
    flag: str,
    requirement: KingdomRequirement,
) -> None:
    calls: list[dict[str, Any]] = []

    def _generate_game(*_args: Any, **kwargs: Any) -> Game:  # noqa: ANN401
        calls.append(kwargs)
        return Game(basic_piles=[], kingdom_piles=[])

    monkeypatch.setattr("dominion_setup.cli.generate_game", _generate_game)
    assert runner.invoke(cli, ["generate", flag]).exit_code == 0
    assert calls[0]["requirements"] == [requirement]


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
    runner: CliRunner, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[dict[str, Any]] = []

    def _generate_game(*_args: Any, **kwargs: Any) -> Game:  # noqa: ANN401
        calls.append(kwargs)
        return Game(basic_piles=[], kingdom_piles=[])

    monkeypatch.setattr("dominion_setup.cli.generate_game", _generate_game)
    args = ["--include", "Witch", "--include", "Alms", "--exclude", "Moat"]
    assert runner.invoke(cli, ["generate", *args]).exit_code == 0
    assert calls[0]["include"] == ("Witch", "Alms")
    assert calls[0]["exclude"] == ("Moat",)


def test_generate_includes_a_card_from_another_set(runner: CliRunner) -> None:
    result = runner.invoke(
        cli, ["generate", "--set", "base_2e", "--include", "Young Witch"]
    )
    assert result.exit_code == 0
    assert "Young Witch" in [row[1] for row in parse_tables(result.output)["Kingdom"]]


def test_generate_unknown_card_is_a_usage_error(runner: CliRunner) -> None:
    result = runner.invoke(cli, ["generate", "--exclude", "Smithee"])
    assert result.exit_code == 2
    assert "Card 'Smithee' not found" in result.output


def test_generate_prints_every_part_of_the_game(
    runner: CliRunner, db: CardDatabase, monkeypatch: pytest.MonkeyPatch
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
        materials=[Material.COIN_TOKENS],
        setup_instructions=["Young Witch: Add an extra Kingdom card pile."],
    )
    monkeypatch.setattr(
        "dominion_setup.cli.generate_game", lambda *_args, **_kwargs: game
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
        "Basic Supply",
    ]
    assert tables["Kingdom"] == [
        ["1", "Hamlet", "$2", "Action", "Cornucopia & Guilds", "Bane"],
        ["2", "Young Witch", "$4", "Action, Attack", "Cornucopia & Guilds", ""],
    ]
    assert "Materials:\n  • Coin tokens" in result.output
    assert "Setup:\n  • Young Witch: Add an extra Kingdom card pile." in result.output


def test_generate_setup_error_is_a_usage_error(
    runner: CliRunner, monkeypatch: pytest.MonkeyPatch
) -> None:
    def _raise(*_args: Any, **_kwargs: Any) -> NoReturn:  # noqa: ANN401
        msg = "No eligible Bane card"
        raise SetupGenerationError(msg)

    monkeypatch.setattr("dominion_setup.cli.generate_game", _raise)
    result = runner.invoke(cli, ["generate"])
    assert result.exit_code == 2
    assert "No eligible Bane card" in result.output


def test_generate_unexpected_error_is_not_a_usage_error(
    runner: CliRunner, monkeypatch: pytest.MonkeyPatch
) -> None:
    def _raise(*_args: Any, **_kwargs: Any) -> NoReturn:  # noqa: ANN401
        msg = "Card 'Madman' not found"
        raise ValueError(msg)

    monkeypatch.setattr("dominion_setup.cli.generate_game", _raise)
    result = runner.invoke(cli, ["generate"])
    assert result.exit_code == 1
    assert isinstance(result.exception, ValueError)


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
            ["--type", "attack"], lambda card: CardType.ATTACK in card.types, id="type"
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
        f"Kingdom Cards ({len(cards)})": card_rows(cards)
    }


@pytest.mark.parametrize("sort_order", KingdomSortOrder)
def test_list_cards_sorts(
    runner: CliRunner, db: CardDatabase, sort_order: KingdomSortOrder
) -> None:
    result = runner.invoke(
        cli, ["list-cards", "--set", "base_2e", "--sort", sort_order.value]
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
