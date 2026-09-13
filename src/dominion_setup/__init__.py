"""dominion-setup is a Python library and CLI tool to set up a game of Dominion, the classic deck-building game."""

from dominion_setup.generator import SetupGenerationError, generate_game
from dominion_setup.loader import load_card_database
from dominion_setup.models import (
    Card,
    CardCost,
    CardDatabase,
    CardSet,
    CardSetEdition,
    CardType,
    Game,
    KingdomSortOrder,
    Material,
    Pile,
    PileMark,
    PileMarkKind,
)

__all__ = [
    "Card",
    "CardCost",
    "CardDatabase",
    "CardSet",
    "CardSetEdition",
    "CardType",
    "Game",
    "KingdomSortOrder",
    "Material",
    "Pile",
    "PileMark",
    "PileMarkKind",
    "SetupGenerationError",
    "generate_game",
    "load_card_database",
]
