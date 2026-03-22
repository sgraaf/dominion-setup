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
