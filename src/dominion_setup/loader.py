"""Load card data from JSON files into a CardDatabase."""

from __future__ import annotations

import json
from importlib.resources import files
from pathlib import Path
from typing import Any

from .models import Card, CardDatabase


def load_card_database(data_dir: Path | None = None) -> CardDatabase:
    """Load all card data from JSON files and return a populated CardDatabase.

    Args:
        data_dir: Optional path to the data directory. Defaults to the
            package's bundled data directory.

    Returns:
        A CardDatabase containing all base cards and kingdom cards.
    """
    if data_dir is None:
        data_dir = Path(str(files("dominion_setup") / "data"))

    cards_dir = data_dir / "cards"

    cards: list[Card] = []
    cards += _load_cards_from_file(cards_dir / "base.json")
    cards += _load_cards_from_file(cards_dir / "intrigue.json")
    cards += _load_cards_from_file(cards_dir / "seaside.json")
    cards += _load_cards_from_file(cards_dir / "alchemy.json")
    cards += _load_cards_from_file(cards_dir / "prosperity.json")
    cards += _load_cards_from_file(cards_dir / "cornucopia_guilds.json")
    cards += _load_cards_from_file(cards_dir / "hinterlands.json")
    cards += _load_cards_from_file(cards_dir / "dark_ages.json")
    cards += _load_cards_from_file(cards_dir / "adventures.json")
    cards += _load_cards_from_file(cards_dir / "empires.json")
    cards += _load_cards_from_file(cards_dir / "nocturne.json")
    cards += _load_cards_from_file(cards_dir / "renaissance.json")
    cards += _load_cards_from_file(cards_dir / "menagerie.json")
    cards += _load_cards_from_file(cards_dir / "allies.json")
    cards += _load_cards_from_file(cards_dir / "plunder.json")
    cards += _load_cards_from_file(cards_dir / "rising_sun.json")
    cards += _load_cards_from_file(cards_dir / "promo.json")
    return CardDatabase(cards)


def _load_cards_from_file(path: Path) -> list[Card]:
    """Parse a JSON file into a list of Card objects."""
    with path.open(encoding="utf-8") as f:
        raw_cards: list[dict[str, Any]] = json.load(f)
    cards: list[Card] = []
    for i, raw_card in enumerate(raw_cards):
        try:
            cards.append(Card.from_dict(raw_card))
        except (KeyError, ValueError) as e:
            msg = f"Error parsing card at index {i} in {path}: {e}"
            raise ValueError(msg) from e
    return cards
