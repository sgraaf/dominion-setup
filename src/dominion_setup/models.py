"""Domain models for Dominion game setup."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum, StrEnum
from typing import TYPE_CHECKING, Any, Literal

if TYPE_CHECKING:
    from collections.abc import Iterator


class CardType(StrEnum):
    """Card types in the game."""

    # introduced by Base
    ACTION = "Action"
    ATTACK = "Attack"
    CURSE = "Curse"
    REACTION = "Reaction"
    TREASURE = "Treasure"
    VICTORY = "Victory"

    # introduced by Seaside
    DURATION = "Duration"

    # introduced by Cornucopia & Guilds
    PRIZE = "Prize"
    REWARD = "Reward"

    # introduced by Dark Ages
    COMMAND = "Command"
    KNIGHT = "Knight"
    LOOTER = "Looter"
    RUINS = "Ruins"
    SHELTER = "Shelter"

    # introduced by Adventures
    EVENT = "Event"
    RESERVE = "Reserve"
    TRAVELLER = "Traveller"

    # introduced by Empires
    CASTLE = "Castle"
    GATHERING = "Gathering"
    LANDMARK = "Landmark"

    # introduced by Nocturne
    BOON = "Boon"
    DOOM = "Doom"
    FATE = "Fate"
    HEIRLOOM = "Heirloom"
    HEX = "Hex"
    NIGHT = "Night"
    SPIRIT = "Spirit"
    STATE = "State"
    ZOMBIE = "Zombie"

    # introduced by Renaissance
    ARTIFACT = "Artifact"
    PROJECT = "Project"

    # introduced by Menagerie
    WAY = "Way"

    # introduced by Allies
    ALLY = "Ally"
    AUGUR = "Augur"
    CLASH = "Clash"
    FORT = "Fort"
    LIAISON = "Liaison"
    ODYSSEY = "Odyssey"
    TOWNSFOLK = "Townsfolk"
    WIZARD = "Wizard"

    # introduced by Plunder
    LOOT = "Loot"
    TRAIT = "Trait"

    # introduced by Rising Sun
    OMEN = "Omen"
    PROPHECY = "Prophecy"
    SHADOW = "Shadow"


# Landscape card types eligible for selection during kingdom generation.
SELECTABLE_LANDSCAPE_TYPES: frozenset[CardType] = frozenset(
    {
        CardType.EVENT,
        CardType.LANDMARK,
        CardType.PROJECT,
        CardType.WAY,
        CardType.TRAIT,
    }
)


class CardPurpose(StrEnum):
    """Card purposes in the game."""

    BASIC = "Basic"
    KINGDOM_PILE = "Kingdom Pile"
    LANDSCAPE = "Landscape"
    MIXED_PILE_CARD = "Mixed Pile Card"
    NON_SUPPLY = "Non-Supply"
    STATUS = "Status"


@dataclass(order=True, frozen=True, slots=True)
class CardCost:
    """Card cost, supporting coins and Potion."""

    coins: int = 0
    potion: bool = False
    debt: int = 0
    extra: Literal["+", "*"] | None = field(default=None, compare=False)

    def __str__(self) -> str:
        """Format cost for display (e.g. '$3', '$2P', '$0P')."""
        s = ""
        if self.coins or not any((self.coins, self.potion, self.debt)):
            s += f"${self.coins}"
        if self.potion:
            s += "P"
        if self.debt:
            s += f"{self.debt}D"
        if self.extra is not None:
            s += self.extra
        return s

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CardCost:
        """Create a Cost from a JSON-derived dictionary."""
        return cls(
            coins=data.get("coins", 0),
            potion=data.get("potion", False),
            debt=data.get("debt", 0),
            extra=data.get("extra"),
        )


class CardSet(StrEnum):
    """Card sets -- the base game along with all expansions and promotional cards."""

    BASE = "Base"
    INTRIGUE = "Intrigue"
    SEASIDE = "Seaside"
    ALCHEMY = "Alchemy"
    PROSPERITY = "Prosperity"
    CORNUCOPIA_GUILDS = "Cornucopia & Guilds"
    HINTERLANDS = "Hinterlands"
    DARK_AGES = "Dark Ages"
    ADVENTURES = "Adventures"
    EMPIRES = "Empires"
    NOCTURNE = "Nocturne"
    RENAISSANCE = "Renaissance"
    MENAGERIE = "Menagerie"
    ALLIES = "Allies"
    PLUNDER = "Plunder"
    RISING_SUN = "Rising Sun"
    PROMO = "Promo"


class CardSetEdition(IntEnum):
    """Card set editions."""

    FIRST_EDITION = 1
    SECOND_EDITION = 2


CARD_SET_ORDER: dict[CardSet, int] = {s: i for i, s in enumerate(CardSet)}


CARD_SETS_WITH_SECOND_EDITIONS: frozenset[CardSet] = frozenset(
    {
        CardSet.BASE,
        CardSet.INTRIGUE,
        CardSet.SEASIDE,
        CardSet.PROSPERITY,
        CardSet.CORNUCOPIA_GUILDS,
        CardSet.HINTERLANDS,
    }
)


DEFAULT_BASIC_CARD_NAMES: tuple[str, ...] = (
    "Copper",
    "Silver",
    "Gold",
    "Estate",
    "Duchy",
    "Province",
    "Curse",
)


@dataclass(frozen=True, slots=True)
class Card:
    """A single card definition loaded from JSON."""

    name: str
    types: tuple[CardType, ...]
    purpose: CardPurpose
    cost: CardCost
    set: CardSet
    editions: tuple[CardSetEdition, ...]
    quantity: int
    image: str
    instructions: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Card:
        """Create a Card from a JSON-derived dictionary."""
        return cls(
            name=data["name"],
            types=tuple(CardType(t) for t in data["types"]),
            purpose=CardPurpose(data["purpose"]),
            cost=CardCost.from_dict(data["cost"]),
            set=CardSet(data["set"]),
            editions=tuple(CardSetEdition(edition) for edition in data["editions"]),
            quantity=data["quantity"],
            image=data["image"],
            instructions=data["instructions"],
        )

    @property
    def display_set(self) -> str:
        return f"{self.set}{f', {self.editions[0]}E' if len(self.editions) == 1 and self.set in CARD_SETS_WITH_SECOND_EDITIONS else ''}"

    @property
    def has_potion_cost(self) -> bool:
        return self.cost.potion

    @property
    def has_debt_cost(self) -> bool:
        return bool(self.cost.debt)

    @property
    def is_basic(self) -> bool:
        return self.purpose == CardPurpose.BASIC

    @property
    def is_kingdom(self) -> bool:
        return self.purpose == CardPurpose.KINGDOM_PILE

    @property
    def is_landscape(self) -> bool:
        return self.purpose == CardPurpose.LANDSCAPE

    @property
    def is_mixed_pile_card(self) -> bool:
        return self.purpose == CardPurpose.MIXED_PILE_CARD

    @property
    def is_non_supply(self) -> bool:
        return self.purpose == CardPurpose.NON_SUPPLY

    @property
    def is_status(self) -> bool:
        return self.purpose == CardPurpose.STATUS


class Material(StrEnum):
    """Materials other than cards or "card-shaped things"."""

    # player mats
    ISLAND_MAT = "Island mat"
    PIRATE_SHIP_MAT = "Pirate Ship mat"
    NATIVE_VILLAGE_MAT = "Native Village mat"
    TRADE_ROUTE_MAT = "Trade Route mat"
    TAVERN_MAT = "Tavern mat"
    COFFERS_MAT = "Coffers mat"
    COFFERS_VILLAGERS_MAT = "Coffers / Villagers mat"
    EXILE_MAT = "Exile mat"
    FAVORS_MAT = "Favors mat"

    # tokens
    VICTORY_TOKENS = "Victory tokens"
    COIN_TOKENS = "Coin tokens"
    EMBARGO_TOKENS = "Embargo tokens"
    PLUS_ONE_CARD_TOKEN = "+1 Card token"  # noqa: S105
    PLUS_ONE_ACTION_TOKEN = "+1 Action token"  # noqa: S105
    PLUS_ONE_BUY_TOKEN = "+1 Buy token"  # noqa: S105
    PLUS_ONE_COIN_TOKEN = "+1 Coin token"  # noqa: S105
    TRASHING_TOKEN = "Trashing token"  # noqa: S105
    MINUS_ONE_CARD_TOKEN = "-1 Card token"  # noqa: S105
    MINUS_ONE_COIN_TOKEN = "-1 Coin token"  # noqa: S105
    JOURNEY_TOKEN = "Journey token"  # noqa: S105
    ESTATE_TOKEN = "Estate token"  # noqa: S105
    DEBT_TOKENS = "Debt tokens"
    WOODEN_CUBES = "Wooden cubes"
    SUN_TOKENS = "Sun tokens"


# Canonical Material ordering for stable output.
MATERIAL_ORDER: dict[Material, int] = {m: i for i, m in enumerate(Material)}


class PileMarkKind(StrEnum):
    """Kinds of annotations that can decorate a ``Pile``."""

    BANE = "Bane"
    OBELISK = "Obelisk"
    FERRYMAN = "Ferryman"
    WAY_OF_THE_MOUSE = "Way of the Mouse"
    TRAIT = "Trait"
    APPROACHING_ARMY = "Approaching Army"
    RIVERBOAT = "Riverboat"


@dataclass(frozen=True, slots=True)
class PileMark:
    """An annotation attached to a ``Pile``."""

    kind: PileMarkKind
    trait: Card | None = None

    def __post_init__(self) -> None:
        if (self.kind == PileMarkKind.TRAIT) is not (self.trait is not None):
            msg = "PileMark with kind TRAIT requires a trait card; other kinds must not have one"
            raise ValueError(msg)

    def __str__(self) -> str:
        if self.kind == PileMarkKind.TRAIT:
            assert self.trait is not None  # guaranteed by __post_init__
            return f"{self.trait.name} (Trait)"
        return str(self.kind)


@dataclass(frozen=True, slots=True)
class Pile:
    """A pile of a single card, optionally decorated with marks (Bane, Obelisk, Trait, …)."""

    card: Card
    marks: tuple[PileMark, ...] = ()


@dataclass(slots=True)
class Game:
    """Complete output representing a ready-to-play Dominion setup."""

    basic_piles: list[Pile]
    kingdom_piles: list[Pile]
    non_supply_piles: list[Pile] = field(default_factory=list)
    landscapes: list[Card] = field(default_factory=list)
    ally: Card | None = None
    prophecy: Card | None = None
    druid_boons: list[Card] = field(default_factory=list)
    materials: list[Material] = field(default_factory=list)
    setup_instructions: list[str] = field(default_factory=list)

    @property
    def basic_cards(self) -> list[Card]:
        """The Cards in ``basic_piles``, dropping marks."""
        return [pile.card for pile in self.basic_piles]

    @property
    def kingdom_cards(self) -> list[Card]:
        """The Cards in ``kingdom_piles``, dropping marks."""
        return [pile.card for pile in self.kingdom_piles]

    @property
    def non_supply_cards(self) -> list[Card]:
        """The Cards in ``non_supply_piles``, dropping marks."""
        return [pile.card for pile in self.non_supply_piles]

    @property
    def sets_used(self) -> list[CardSet]:
        cards = self.kingdom_cards + self.non_supply_cards + self.landscapes
        return sorted(
            {card.set for card in cards},
            key=CARD_SET_ORDER.__getitem__,
        )


@dataclass(slots=True)
class CardDatabase:
    """All loaded card data, indexed for fast lookup."""

    cards: list[Card]
    card_name_to_card: dict[str, Card] = field(init=False)
    basic_cards: dict[str, Card] = field(init=False)
    kingdom_cards: dict[str, Card] = field(init=False)
    landscape_cards: dict[str, Card] = field(init=False)
    mixed_pile_cards: dict[str, Card] = field(init=False)
    non_supply_cards: dict[str, Card] = field(init=False)
    status_cards: dict[str, Card] = field(init=False)

    def __post_init__(self) -> None:
        self.card_name_to_card = {}
        self.basic_cards = {}
        self.kingdom_cards = {}
        self.landscape_cards = {}
        self.mixed_pile_cards = {}
        self.non_supply_cards = {}
        self.status_cards = {}
        for card in self.cards:
            self.card_name_to_card[card.name] = card
            match card.purpose:
                case CardPurpose.BASIC:
                    self.basic_cards[card.name] = card
                case CardPurpose.KINGDOM_PILE:
                    self.kingdom_cards[card.name] = card
                case CardPurpose.LANDSCAPE:
                    self.landscape_cards[card.name] = card
                case CardPurpose.MIXED_PILE_CARD:
                    self.mixed_pile_cards[card.name] = card
                case CardPurpose.NON_SUPPLY:
                    self.non_supply_cards[card.name] = card
                case CardPurpose.STATUS:
                    self.status_cards[card.name] = card

    def __iter__(self) -> Iterator[Card]:
        return iter(self.cards)

    def __len__(self) -> int:
        return len(self.cards)

    def get_card_by_name(self, name: str) -> Card:
        if (card := self.card_name_to_card.get(name)) is None:
            msg = f"Card {name!r} not found"
            raise ValueError(msg)
        return card

    def get_cards_by_set_edition(
        self, set_: CardSet, edition: CardSetEdition
    ) -> list[Card]:
        """Return all kingdom cards belonging to the given set and edition."""
        return [
            card
            for card in self.kingdom_cards.values()
            if card.set == set_ and edition in card.editions
        ]

    def get_cards_by_type(self, card_type: CardType) -> list[Card]:
        """Return all kingdom cards that include the given type."""
        return [card for card in self.kingdom_cards.values() if card_type in card.types]

    def get_cards_by_cost(self, card_cost: CardCost) -> list[Card]:
        """Return all kingdom cards of the given cost."""
        return [card for card in self.kingdom_cards.values() if card.cost == card_cost]


class KingdomSortOrder(StrEnum):
    """Sort order for kingdom piles in the game output."""

    NAME = "name"
    COST = "cost"
    SET = "set"
