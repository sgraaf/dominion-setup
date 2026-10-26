"""dominion-setup is a Python library and CLI tool to set up a game of Dominion, the classic deck-building game."""

from dominion_setup.generator import (
    SetupGenerationError,
    generate_game,
    is_selectable,
    read_board_code,
)
from dominion_setup.loader import load_card_database
from dominion_setup.models import (
    CARD_SETS_WITH_SECOND_EDITIONS,
    SET_EDITION_CHOICES,
    Board,
    Card,
    CardCost,
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
    SetupInstruction,
)

__all__ = [
    "CARD_SETS_WITH_SECOND_EDITIONS",
    "SET_EDITION_CHOICES",
    "Board",
    "Card",
    "CardCost",
    "CardDatabase",
    "CardSet",
    "CardSetEdition",
    "CardType",
    "Game",
    "KingdomRequirement",
    "KingdomSortOrder",
    "Material",
    "Pile",
    "PileMark",
    "PileMarkKind",
    "SetupGenerationError",
    "SetupInstruction",
    "generate_game",
    "is_selectable",
    "load_card_database",
    "read_board_code",
]
