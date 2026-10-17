"""Domain models for Dominion game setup.

The module is organised in four sections:

- **Sets & editions**: ``CardSet`` and ``CardSetEdition``.
- **Cards**: ``Card`` and the enums and value objects that describe it.
- **Card database**: ``CardDatabase``, all cards indexed for lookup.
- **Game**: ``Game``, the generated setup, the ``Pile``, ``PileMark``,
  ``Material`` and ``SetupInstruction`` types it is made of, and the
  ``KingdomSortOrder`` and ``KingdomRequirement`` options for generating it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum, StrEnum
from typing import TYPE_CHECKING, Any, Literal

if TYPE_CHECKING:
    from collections.abc import Iterator


# ── Sets & editions ──────────────────────────────────────────────────────────


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


CARD_SET_ORDER: dict[CardSet, int] = {s: i for i, s in enumerate(CardSet)}


class CardSetEdition(IntEnum):
    """Card set editions."""

    FIRST_EDITION = 1
    SECOND_EDITION = 2


CARD_SETS_WITH_SECOND_EDITIONS: frozenset[CardSet] = frozenset(
    {
        CardSet.BASE,
        CardSet.INTRIGUE,
        CardSet.SEASIDE,
        CardSet.PROSPERITY,
        CardSet.CORNUCOPIA_GUILDS,
        CardSet.HINTERLANDS,
    },
)

# Set and edition choices, as for ``--set`` (e.g. "base_2e", "nocturne"), and
# the set and edition each one selects. Only sets with a second edition carry an
# edition suffix.
SET_EDITION_CHOICES: dict[str, tuple[CardSet, CardSetEdition]] = {}
for set_ in CardSet:
    if set_ in CARD_SETS_WITH_SECOND_EDITIONS:
        for edition in CardSetEdition:
            SET_EDITION_CHOICES[f"{set_.name.lower()}_{edition}e"] = (set_, edition)
    else:
        SET_EDITION_CHOICES[set_.name.lower()] = (set_, CardSetEdition.FIRST_EDITION)


# ── Cards ────────────────────────────────────────────────────────────────────


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


class CardPurpose(StrEnum):
    """Card purposes in the game."""

    BASIC = "Basic"
    KINGDOM_PILE = "Kingdom Pile"
    LANDSCAPE = "Landscape"
    MIXED_PILE_CARD = "Mixed Pile Card"
    NON_SUPPLY = "Non-Supply"
    STATUS = "Status"


@dataclass(frozen=True, slots=True)
class CardCost:
    """Card cost, supporting coins, Potion and Debt.

    ``coins`` is ``None`` for a cost without coins (e.g. Engineer's 4D, or a
    Landmark that has no cost), which orders like a cost of $0.
    """

    coins: int | None = None
    potion: bool = False
    debt: int = 0
    extra: Literal["+", "*"] | None = field(default=None, compare=False)

    def _sort_key(self) -> tuple[int, bool, int]:
        return (self.coins or 0, self.potion, self.debt)

    def __lt__(self, other: CardCost) -> bool:
        return self._sort_key() < other._sort_key()

    def __le__(self, other: CardCost) -> bool:
        return self._sort_key() <= other._sort_key()

    def __gt__(self, other: CardCost) -> bool:
        return self._sort_key() > other._sort_key()

    def __ge__(self, other: CardCost) -> bool:
        return self._sort_key() >= other._sort_key()

    def __str__(self) -> str:
        """Format cost for display (e.g. '$3', '$2P', 'P', '8D', or '' for no cost)."""
        s = ""
        if self.coins is not None:
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
            coins=data.get("coins"),
            potion=data.get("potion", False),
            debt=data.get("debt", 0),
            extra=data.get("extra"),
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to a JSON-serializable dictionary, omitting default fields like the card data."""
        data: dict[str, Any] = {}
        if self.coins is not None:
            data["coins"] = self.coins
        if self.potion:
            data["potion"] = self.potion
        if self.debt:
            data["debt"] = self.debt
        if self.extra is not None:
            data["extra"] = self.extra
        return data


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
        if self.set in CARD_SETS_WITH_SECOND_EDITIONS and len(self.editions) == 1:
            return f"{self.set}, {self.editions[0]}E"
        return str(self.set)

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


# ── Card database ────────────────────────────────────────────────────────────


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
        self.card_name_to_card = self._create_index(self.cards)
        self.basic_cards = self._create_index(
            self.get_cards_by_purpose(CardPurpose.BASIC),
        )
        self.kingdom_cards = self._create_index(
            self.get_cards_by_purpose(CardPurpose.KINGDOM_PILE),
        )
        self.landscape_cards = self._create_index(
            self.get_cards_by_purpose(CardPurpose.LANDSCAPE),
        )
        self.mixed_pile_cards = self._create_index(
            self.get_cards_by_purpose(CardPurpose.MIXED_PILE_CARD),
        )
        self.non_supply_cards = self._create_index(
            self.get_cards_by_purpose(CardPurpose.NON_SUPPLY),
        )
        self.status_cards = self._create_index(
            self.get_cards_by_purpose(CardPurpose.STATUS),
        )

    @staticmethod
    def _create_index(cards: list[Card]) -> dict[str, Card]:
        """Index cards by name."""
        return {card.name: card for card in cards}

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
        self,
        set_: CardSet,
        edition: CardSetEdition,
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

    def get_cards_by_purpose(self, card_purpose: CardPurpose) -> list[Card]:
        """Return all cards of the given purpose."""
        return [card for card in self.cards if card.purpose == card_purpose]


# ── Game ─────────────────────────────────────────────────────────────────────


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
        if (self.kind == PileMarkKind.TRAIT) != (self.trait is not None):
            msg = "PileMark with kind TRAIT requires a trait card; other kinds must not have one"
            raise ValueError(msg)

    def __str__(self) -> str:
        if self.kind == PileMarkKind.TRAIT:
            assert self.trait is not None  # guaranteed by __post_init__
            return f"{self.trait.name} (Trait)"
        return str(self.kind)


@dataclass(frozen=True, slots=True)
class Pile:
    """A pile of a single card, optionally decorated with marks (Bane, Obelisk, Trait, …).

    ``size`` is how many cards go in the pile, or ``None`` if the number of
    players is unknown, or if the cards go into the starting decks instead
    (Shelters, Heirlooms).
    """

    card: Card
    marks: tuple[PileMark, ...] = ()
    size: int | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to a JSON-serializable dictionary of the card and the pile's marks and size."""
        return {
            "name": self.card.name,
            "cost": self.card.cost.to_dict(),
            "types": list(self.card.types),
            "purpose": str(self.card.purpose),
            "set": self.card.display_set,
            "marks": [str(mark) for mark in self.marks],
            "size": self.size,
            "image": self.card.image,
            "instructions": self.card.instructions,
        }


@dataclass(frozen=True, slots=True)
class SetupInstruction:
    """An instruction for setting up the game, labelled with what it is for.

    The label is the card that needs the setup (e.g. "Arena"), or
    "Starting decks".
    """

    label: str
    text: str

    def __str__(self) -> str:
        return f"{self.label}: {self.text}"

    def to_dict(self) -> dict[str, str]:
        """Convert to a JSON-serializable dictionary of the label and text."""
        return {"label": self.label, "text": self.text}


class KingdomSortOrder(StrEnum):
    """Sort order for kingdom piles in the game output."""

    NAME = "name"
    COST = "cost"
    SET = "set"

    def sort_key(self, card: Card) -> tuple[int | CardCost | str, ...]:
        """Return the key that puts *card* in this sort order."""
        if self == KingdomSortOrder.NAME:
            return (card.name,)
        if self == KingdomSortOrder.SET:
            return (CARD_SET_ORDER[card.set], card.cost, card.name)
        return (card.cost, card.name)


class KingdomRequirement(StrEnum):
    """Effects that the Kingdom of a generated game can be required to include."""

    ACTIONS = "+Action(s)"
    CARDS = "+Card(s)"
    BUYS = "+Buy(s)"
    ATTACK = "Attack"
    REACTION = "Reaction"
    TRASHING = "Trashing"


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
    black_market_deck: list[Card] = field(default_factory=list)
    materials: list[Material] = field(default_factory=list)
    setup_instructions: list[SetupInstruction] = field(default_factory=list)
    players: int | None = None

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
        cards = [
            *self.kingdom_cards,
            *self.non_supply_cards,
            *self.landscapes,
            *self.black_market_deck,
        ]
        return sorted(
            {card.set for card in cards},
            key=CARD_SET_ORDER.__getitem__,
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to a JSON-serializable dictionary, as ``dominion-setup generate --format json`` prints it.

        Cards that are not in a pile (Landscapes, the Ally, …) take the form of
        a pile without marks or size.
        """

        def card_to_dict(card: Card | None) -> dict[str, Any] | None:
            return None if card is None else Pile(card).to_dict()

        return {
            "players": self.players,
            "sets": self.sets_used,
            "kingdom": [pile.to_dict() for pile in self.kingdom_piles],
            "landscapes": [card_to_dict(card) for card in self.landscapes],
            "ally": card_to_dict(self.ally),
            "prophecy": card_to_dict(self.prophecy),
            "druid_boons": [card_to_dict(card) for card in self.druid_boons],
            "non_supply": [pile.to_dict() for pile in self.non_supply_piles],
            "black_market": [card_to_dict(card) for card in self.black_market_deck],
            "basic_supply": [pile.to_dict() for pile in self.basic_piles],
            "materials": self.materials,
            "setup": [instruction.to_dict() for instruction in self.setup_instructions],
        }
