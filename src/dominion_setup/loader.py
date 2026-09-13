"""Load card data from JSON files into a CardDatabase."""

from __future__ import annotations

import json
from importlib.resources import files
from typing import TYPE_CHECKING, Any

from .models import Card, CardDatabase, CardSet

if TYPE_CHECKING:
    from importlib.resources.abc import Traversable


def load_card_database(data_dir: Traversable | None = None) -> CardDatabase:
    """Load all card data from JSON files and return a populated CardDatabase.

    Args:
        data_dir: Optional path to the data directory, containing a
            ``cards/<set>.json`` file for every ``CardSet``. Defaults to the
            package's bundled data directory.

    Returns:
        A CardDatabase containing all base cards and kingdom cards.
    """
    if data_dir is None:
        data_dir = files("dominion_setup") / "data"

    cards_dir = data_dir / "cards"

    cards: list[Card] = []
    for set_ in CardSet:
        cards += _load_cards_from_file(cards_dir / f"{set_.name.lower()}.json")
    return CardDatabase(cards)


def _load_cards_from_file(path: Traversable) -> list[Card]:
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
