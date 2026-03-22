"""Shared test fixtures for dominion-setup."""

from typing import Any, Literal, Protocol

import pytest

from dominion_setup.loader import load_card_database
from dominion_setup.models import (
    DEFAULT_BASIC_CARD_NAMES,
    Card,
    CardCost,
    CardDatabase,
    CardPurpose,
    CardSet,
    CardSetEdition,
    CardType,
)


@pytest.fixture
def db() -> CardDatabase:
    """Load the full card database from bundled JSON data."""
    return load_card_database()


class CardFactory(Protocol):
    """Type annotation for card factory function.

    Due to its complex nature, it cannot be expressed as a ``Callable``.
    """

    def __call__(  # noqa: PLR0913
        self,
        *,
        name: str = "Smithy",
        types: tuple[CardType, ...] = (CardType.ACTION,),
        purpose: CardPurpose = CardPurpose.KINGDOM_PILE,
        cost_coins: int = 4,
        cost_potion: bool = False,
        cost_debt: int = 0,
        cost_extra: Literal["+", "*"] | None = None,
        set_: CardSet = CardSet.BASE,
        editions: tuple[CardSetEdition, ...] = (
            CardSetEdition.FIRST_EDITION,
            CardSetEdition.SECOND_EDITION,
        ),
        quantity: int = 10,
        image: str = "Smithy.jpg",
        instructions: str = "+3 Cards",
    ) -> Card: ...


@pytest.fixture
def make_card() -> CardFactory:
    """``Card`` factory fixture."""

    def _make_card(  # noqa: PLR0913
        *,
        name: str = "Smithy",
        types: tuple[CardType, ...] = (CardType.ACTION,),
        purpose: CardPurpose = CardPurpose.KINGDOM_PILE,
        cost_coins: int = 4,
        cost_potion: bool = False,
        cost_debt: int = 0,
        cost_extra: Literal["+", "*"] | None = None,
        set_: CardSet = CardSet.BASE,
        editions: tuple[CardSetEdition, ...] = (
            CardSetEdition.FIRST_EDITION,
            CardSetEdition.SECOND_EDITION,
        ),
        quantity: int = 10,
        image: str = "Smithy.jpg",
        instructions: str = "+3 Cards",
    ) -> Card:
        return Card(
            name=name,
            types=types,
            purpose=purpose,
            cost=CardCost(cost_coins, cost_potion, cost_debt, cost_extra),
            set=set_,
            editions=editions,
            quantity=quantity,
            image=image,
            instructions=instructions,
        )

    return _make_card


@pytest.fixture
def smithy(make_card: CardFactory) -> Card:
    """A hand-built "Smithy" ``Card`` for unit tests that don't need the full DB."""
    return make_card()


class CardDatabaseFactory(Protocol):
    """Type annotation for card database factory function.

    Due to its complex nature, it cannot be expressed as a ``Callable``.
    """

    def __call__(self, **kwargs: Any) -> CardDatabase: ...  # noqa: ANN401


@pytest.fixture
def ten_card_db(db: CardDatabase, make_card: CardFactory) -> CardDatabaseFactory:
    """``CardDatabase`` factory fixture."""

    def _ten_card_db(**kwargs: Any) -> CardDatabase:  # noqa: ANN401
        """A 10-kingdom-card DB where the first card has *kwargs* applied.

        Includes the 7 standard basic supply cards so generate_game can run.
        """
        basic_cards = [
            db.get_card_by_name(card_name) for card_name in DEFAULT_BASIC_CARD_NAMES
        ]
        special_card = make_card(name="Special", **kwargs)  # type: ignore[arg-type]
        other_cards = [
            make_card(name=f"Filler{i}", cost_coins=i, image=f"Filler{i}.jpg")
            for i in range(9)
        ]
        return CardDatabase([*basic_cards, special_card, *other_cards])

    return _ten_card_db
