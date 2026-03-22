"""dominion-setup is a Python library and CLI tool to set up a game of Dominion, the classic deck-building game."""

from dominion_setup.generator import generate_game
from dominion_setup.loader import load_card_database
from dominion_setup.models import (
    CardDatabase,
    CardSet,
    Game,
    KingdomSortOrder,
    Pile,
    PileMark,
    PileMarkKind,
)

__all__ = [
    "CardDatabase",
    "CardSet",
    "Game",
    "KingdomSortOrder",
    "Pile",
    "PileMark",
    "PileMarkKind",
    "generate_game",
    "load_card_database",
]
