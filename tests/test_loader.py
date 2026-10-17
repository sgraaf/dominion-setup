"""Tests for ``dominion_setup.loader``.

Facts about the bundled cards themselves are tested in ``test_card_data.py``.
"""

import json
from pathlib import Path

import pytest

from dominion_setup.loader import load_card_database
from dominion_setup.models import CardSet

SMITHY = {
    "name": "Smithy",
    "types": ["Action"],
    "purpose": "Kingdom Pile",
    "cost": {"coins": 4},
    "set": "Base",
    "editions": [1, 2],
    "quantity": 10,
    "image": "Smithy.jpg",
    "instructions": "+3 Cards",
}


@pytest.fixture
def data_dir(tmp_path: Path) -> Path:
    """A data directory with an empty ``cards/<set>.json`` file for every set."""
    cards_dir = tmp_path / "cards"
    cards_dir.mkdir()
    for set_ in CardSet:
        (cards_dir / f"{set_.name.lower()}.json").write_text("[]")
    return tmp_path


def test_loads_the_bundled_cards_of_every_set() -> None:
    db = load_card_database()
    assert {card.set for card in db} == set(CardSet)


def test_loads_the_cards_in_a_custom_data_dir(data_dir: Path) -> None:
    (data_dir / "cards" / "base.json").write_text(json.dumps([SMITHY]))
    db = load_card_database(data_dir)
    assert [card.name for card in db] == ["Smithy"]


def test_reports_the_card_that_fails_to_parse(data_dir: Path) -> None:
    spell = {**SMITHY, "name": "Spell", "types": ["Spell"]}
    (data_dir / "cards" / "base.json").write_text(json.dumps([SMITHY, spell]))
    with pytest.raises(
        ValueError,
        match=r"Error parsing card at index 1 in .*base\.json",
    ):
        load_card_database(data_dir)
