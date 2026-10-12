"""Shared test fixtures for dominion-setup."""

import random

import pytest

from dominion_setup.loader import load_card_database
from dominion_setup.models import (
    Card,
    CardCost,
    CardDatabase,
    CardPurpose,
    CardSet,
    CardSetEdition,
    CardType,
)


@pytest.fixture(autouse=True)
def _seed_random() -> None:
    """Seed ``random`` before every test, so generated games are reproducible."""
    random.seed(0)


@pytest.fixture(scope="session")
def db() -> CardDatabase:
    """The full card database, loaded once from the bundled JSON data."""
    return load_card_database()


@pytest.fixture
def smithy() -> Card:
    """A hand-built Smithy, to vary with ``dataclasses.replace`` in unit tests."""
    return Card(
        name="Smithy",
        types=(CardType.ACTION,),
        purpose=CardPurpose.KINGDOM_PILE,
        cost=CardCost(coins=4),
        set=CardSet.BASE,
        editions=(CardSetEdition.FIRST_EDITION, CardSetEdition.SECOND_EDITION),
        quantity=10,
        image="Smithy.jpg",
        instructions="+3 Cards",
    )
