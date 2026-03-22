import re
import subprocess
from collections.abc import Sequence
from dataclasses import dataclass
from importlib import import_module, metadata
from os import PathLike
from typing import Any

import pytest
from click.testing import CliRunner

from dominion_setup.cli import cli

# copied from `typeshed`
StrOrBytesPath = str | bytes | PathLike
Command = StrOrBytesPath | Sequence[StrOrBytesPath]


@dataclass
class CommandResult:
    """Holds the captured result of an invoked command.

    Inspired by `click.testing.Result`.
    """

    exit_code: int
    stdout: str
    stderr: str


def run_command_in_shell(command: Command, **kwargs: Any) -> CommandResult:  # noqa: ANN401
    """Execute a command through the shell, capturing the exit code and output."""
    result = subprocess.run(  # noqa: S602
        command,
        shell=True,
        capture_output=True,
        check=False,
        **kwargs,
    )
    return CommandResult(
        result.returncode,
        result.stdout.decode().replace("\r\n", "\n"),
        result.stderr.decode().replace("\r\n", "\n"),
    )


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


def test_main_module() -> None:
    """Exercise (most of) the code in the `__main__` module."""
    import_module("dominion_setup.__main__")


def test_run_as_module() -> None:
    """Is the script runnable as a Python module?"""
    result = run_command_in_shell("python -m dominion_setup --help")
    assert result.exit_code == 0


def test_run_as_executable() -> None:
    """Is the script installed (as a `console_script`) and runnable as an executable?"""
    result = run_command_in_shell("dominion-setup --help")
    assert result.exit_code == 0


def test_version_runner(runner: CliRunner) -> None:
    """Does `--version` display the correct version?"""
    result = runner.invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert result.output == f"cli, version {metadata.version('dominion-setup')}\n"


def test_generate_default(runner: CliRunner) -> None:
    result = runner.invoke(cli, ["generate"])
    assert result.exit_code == 0
    assert "Kingdom" in result.output


def test_generate_shows_basic_piles(runner: CliRunner) -> None:
    result = runner.invoke(cli, ["generate"])
    assert result.exit_code == 0
    for name in ("Copper", "Silver", "Gold", "Estate", "Duchy", "Province", "Curse"):
        assert name in result.output


def test_generate_shows_10_kingdom_cards(runner: CliRunner) -> None:
    result = runner.invoke(cli, ["generate", "-s", "base_2e"])
    assert result.exit_code == 0
    # Kingdom table rows are numbered; match lines like "│  1 │ ..."
    kingdom_rows = [
        line
        for line in result.output.splitlines()
        if "│" in line and re.search(r"│\s+\d+\s+│", line)
    ]
    assert len(kingdom_rows) == 10


def test_generate_with_sort_name(runner: CliRunner) -> None:
    result = runner.invoke(cli, ["generate", "--sort", "name"])
    assert result.exit_code == 0
    assert "Kingdom" in result.output


def test_generate_with_sort_cost(runner: CliRunner) -> None:
    result = runner.invoke(cli, ["generate", "--sort", "cost"])
    assert result.exit_code == 0
    assert "Kingdom" in result.output


def test_generate_with_sort_set(runner: CliRunner) -> None:
    result = runner.invoke(cli, ["generate", "--sort", "set"])
    assert result.exit_code == 0
    assert "Kingdom" in result.output


def test_generate_with_invalid_sort(runner: CliRunner) -> None:
    result = runner.invoke(cli, ["generate", "--sort", "invalid"])
    assert result.exit_code != 0


def test_generate_with_single_set(runner: CliRunner) -> None:
    result = runner.invoke(cli, ["generate", "-s", "intrigue_2e"])
    assert result.exit_code == 0
    assert "Kingdom" in result.output
    assert "Intrigue" in result.output


def test_generate_with_multiple_sets(runner: CliRunner) -> None:
    result = runner.invoke(cli, ["generate", "-s", "intrigue_2e", "-s", "base_2e"])
    assert result.exit_code == 0
    assert "Kingdom" in result.output


def test_generate_invalid_set(runner: CliRunner) -> None:
    result = runner.invoke(cli, ["generate", "-s", "Nonexistent"])
    assert result.exit_code != 0


def test_generate_default_uses_base_2e(runner: CliRunner) -> None:
    # Base 1E-only cards are never in the Base 2E pool.  Asserting their
    # absence is deterministic (unlike checking for a 2E-exclusive card name,
    # which only appears when that specific card is randomly drawn).
    base_1e_only = {"Chancellor", "Feast", "Spy", "Thief", "Woodcutter"}
    result = runner.invoke(cli, ["generate"])
    assert result.exit_code == 0
    for name in base_1e_only:
        assert name not in result.output


def test_generate_with_1e_set(runner: CliRunner) -> None:
    result = runner.invoke(cli, ["generate", "-s", "base_1e"])
    assert result.exit_code == 0
    assert "Base" in result.output


def test_generate_with_seaside_set(runner: CliRunner) -> None:
    result = runner.invoke(cli, ["generate", "-s", "seaside_2e"])
    assert result.exit_code == 0
    assert "Kingdom" in result.output
    assert "Seaside" in result.output


def test_generate_with_seaside_1e_set(runner: CliRunner) -> None:
    result = runner.invoke(cli, ["generate", "-s", "seaside_1e"])
    assert result.exit_code == 0
    assert "Seaside" in result.output


def test_list_cards_default(runner: CliRunner) -> None:
    result = runner.invoke(cli, ["list-cards"])
    assert result.exit_code == 0
    assert "Kingdom Cards" in result.output


def test_list_cards_filter_by_set(runner: CliRunner) -> None:
    result = runner.invoke(cli, ["list-cards", "-s", "base_2e"])
    assert result.exit_code == 0
    assert "Kingdom Cards" in result.output
    # should not contain Seaside-only cards
    assert "Base, 2E" in result.output


def test_list_cards_filter_by_type(runner: CliRunner) -> None:
    result = runner.invoke(cli, ["list-cards", "-t", "attack"], env={"COLUMNS": "200"})
    assert result.exit_code == 0
    assert "Kingdom Cards" in result.output
    # all rows should contain Attack type
    for line in result.output.splitlines():
        if "\u2502" in line and "$" in line:  # table data rows with cost
            assert "Attack" in line


def test_list_cards_filter_by_cost(runner: CliRunner) -> None:
    result = runner.invoke(cli, ["list-cards", "--cost", "2"])
    assert result.exit_code == 0
    # all listed cards should have cost $2
    for line in result.output.splitlines():
        if "\u2502" in line and "$" in line:
            assert "$2" in line


def test_list_cards_combined_filters(runner: CliRunner) -> None:
    result = runner.invoke(
        cli, ["list-cards", "-s", "base_2e", "-t", "action", "--cost", "5"]
    )
    assert result.exit_code == 0
    assert "Kingdom Cards" in result.output
    for line in result.output.splitlines():
        if "\u2502" in line and "$" in line:
            assert "$5" in line
            assert "Action" in line


def test_list_cards_no_results(runner: CliRunner) -> None:
    # cost 99 doesn't exist — should succeed with 0 results
    result = runner.invoke(cli, ["list-cards", "--cost", "99"])
    assert result.exit_code == 0
    assert "Kingdom Cards (0)" in result.output


def test_list_cards_invalid_set(runner: CliRunner) -> None:
    result = runner.invoke(cli, ["list-cards", "-s", "nonexistent"])
    assert result.exit_code != 0


def test_list_cards_invalid_type(runner: CliRunner) -> None:
    result = runner.invoke(cli, ["list-cards", "-t", "nonexistent"])
    assert result.exit_code != 0


def test_list_cards_multiple_sets(runner: CliRunner) -> None:
    result = runner.invoke(cli, ["list-cards", "-s", "base_2e", "-s", "intrigue_2e"])
    assert result.exit_code == 0
    assert "Kingdom Cards" in result.output


def test_list_sets(runner: CliRunner) -> None:
    result = runner.invoke(cli, ["list-sets"])
    assert result.exit_code == 0
    assert "Sets" in result.output
    assert "Base" in result.output
    assert "Base, 2E" in result.output
    assert "Intrigue" in result.output


def test_list_sets_shows_card_counts(runner: CliRunner) -> None:
    result = runner.invoke(cli, ["list-sets"])
    assert result.exit_code == 0
    # at least some set should have a non-zero count
    # dominion 2E has 26 kingdom cards in the bundled data
    lines = result.output.splitlines()
    data_lines = [
        row for row in lines if "\u2502" in row and any(c.isdigit() for c in row)
    ]
    assert len(data_lines) > 0


def test_generate_with_alchemy_set(runner: CliRunner) -> None:
    result = runner.invoke(cli, ["generate", "-s", "alchemy"])
    assert result.exit_code == 0
    assert "Kingdom" in result.output
    assert "Alchemy" in result.output


def test_list_cards_alchemy(runner: CliRunner) -> None:
    result = runner.invoke(cli, ["list-cards", "-s", "alchemy"])
    assert result.exit_code == 0
    assert "Kingdom Cards" in result.output


def test_list_sets_includes_alchemy(runner: CliRunner) -> None:
    result = runner.invoke(cli, ["list-sets"])
    assert result.exit_code == 0
    assert "Alchemy" in result.output


def test_generate_alchemy_shows_potion_cost(runner: CliRunner) -> None:
    result = runner.invoke(cli, ["list-cards", "-s", "alchemy"])
    assert result.exit_code == 0
    # alchemy has 10/12 cards with potion cost displayed as $NP
    lines = [
        line for line in result.output.splitlines() if "\u2502" in line and "$" in line
    ]
    potion_lines = [
        line for line in lines if "P" in line.split("$")[1].split("\u2502")[0]
    ]
    assert len(potion_lines) > 0


def test_list_cards_sort_by_name(runner: CliRunner) -> None:
    result = runner.invoke(cli, ["list-cards", "--sort", "name"])
    assert result.exit_code == 0
    assert "Kingdom Cards" in result.output


def test_list_cards_sort_by_set(runner: CliRunner) -> None:
    result = runner.invoke(cli, ["list-cards", "--sort", "set"])
    assert result.exit_code == 0
    assert "Kingdom Cards" in result.output


def test_list_cards_sort_by_cost(runner: CliRunner) -> None:
    result = runner.invoke(cli, ["list-cards", "--sort", "cost"])
    assert result.exit_code == 0
    assert "Kingdom Cards" in result.output


def test_list_cards_filter_by_non_edition_set(runner: CliRunner) -> None:
    result = runner.invoke(cli, ["list-cards", "-s", "alchemy"])
    assert result.exit_code == 0
    assert "Kingdom Cards" in result.output
    assert "Alchemy" in result.output


def test_list_cards_filter_by_multiple_types(runner: CliRunner) -> None:
    result = runner.invoke(
        cli, ["list-cards", "-t", "action", "-t", "attack"], env={"COLUMNS": "200"}
    )
    assert result.exit_code == 0
    for line in result.output.splitlines():
        if "\u2502" in line and "$" in line:
            assert "Action" in line
            assert "Attack" in line


def test_default_command_no_args(runner: CliRunner) -> None:
    result = runner.invoke(cli, [])
    assert result.exit_code == 0
    assert "Kingdom" in result.output


def test_help_text(runner: CliRunner) -> None:
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "generate" in result.output
    assert "list-cards" in result.output
    assert "list-sets" in result.output


def test_generate_help(runner: CliRunner) -> None:
    result = runner.invoke(cli, ["generate", "--help"])
    assert result.exit_code == 0
    assert "--sort" in result.output
    assert "--set" in result.output


def test_list_cards_filter_by_1e_set(runner: CliRunner) -> None:
    result = runner.invoke(cli, ["list-cards", "-s", "base_1e"])
    assert result.exit_code == 0
    assert "Kingdom Cards" in result.output
    assert "Base" in result.output


def test_generate_cornucopia_guilds_1e(runner: CliRunner) -> None:
    result = runner.invoke(cli, ["generate", "-s", "cornucopia_guilds_1e"])
    assert result.exit_code == 0
    assert "Cornucopia & Guilds" in result.output


def test_generate_cornucopia_guilds_2e(runner: CliRunner) -> None:
    result = runner.invoke(cli, ["generate", "-s", "cornucopia_guilds_2e"])
    assert result.exit_code == 0
    assert "Cornucopia & Guilds" in result.output


def test_list_cards_cornucopia_guilds(runner: CliRunner) -> None:
    result = runner.invoke(cli, ["list-cards", "-s", "cornucopia_guilds_1e"])
    assert result.exit_code == 0
    assert "Kingdom Cards" in result.output


def test_list_sets_includes_cornucopia_guilds(runner: CliRunner) -> None:
    result = runner.invoke(cli, ["list-sets"])
    assert result.exit_code == 0
    assert "Cornucopia & Guilds" in result.output


def test_generate_cornucopia_guilds_shows_setup(runner: CliRunner) -> None:
    """C&G 2E has many Coffers-triggering cards; verify setup section appears when they do."""
    result = runner.invoke(cli, ["generate", "-s", "cornucopia_guilds_2e"])
    assert result.exit_code == 0
    if "Coffers" in result.output:
        assert "Setup" in result.output
