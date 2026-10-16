"""Tests for ``dominion_setup.models``.

The sections follow ``models.py``. The cards here are hand-built (variations
on the ``smithy`` fixture), so these tests do not depend on the card data.
"""

from dataclasses import replace
from typing import Any

import pytest

from dominion_setup.models import (
    Card,
    CardCost,
    CardDatabase,
    CardPurpose,
    CardSet,
    CardSetEdition,
    CardType,
    Game,
    KingdomSortOrder,
    Pile,
    PileMark,
    PileMarkKind,
)

# ── Cards ────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("data", "cost"),
    [
        ({}, CardCost(coins=None, potion=False, debt=0, extra=None)),
        ({"coins": 0}, CardCost(coins=0)),
        ({"coins": 5}, CardCost(coins=5)),
        ({"coins": 2, "potion": True}, CardCost(coins=2, potion=True)),
        ({"debt": 8}, CardCost(debt=8)),
        ({"coins": 3, "extra": "+"}, CardCost(coins=3, extra="+")),
    ],
)
def test_card_cost_from_dict(data: dict[str, Any], cost: CardCost) -> None:
    assert CardCost.from_dict(data) == cost


def test_card_cost_without_coins_is_not_a_zero_coin_cost() -> None:
    assert CardCost() != CardCost(coins=0)


@pytest.mark.parametrize(
    ("cost", "data"),
    [
        (CardCost(), {}),
        (CardCost(coins=0), {"coins": 0}),
        (CardCost(coins=5), {"coins": 5}),
        (CardCost(coins=2, potion=True), {"coins": 2, "potion": True}),
        (CardCost(debt=8), {"debt": 8}),
        (CardCost(coins=3, extra="+"), {"coins": 3, "extra": "+"}),
        (
            CardCost(coins=2, potion=True, debt=4, extra="*"),
            {"coins": 2, "potion": True, "debt": 4, "extra": "*"},
        ),
    ],
)
def test_card_cost_to_dict(cost: CardCost, data: dict[str, Any]) -> None:
    assert cost.to_dict() == data


@pytest.mark.parametrize(
    ("cost", "text"),
    [
        (CardCost(), ""),
        (CardCost(coins=0), "$0"),
        (CardCost(coins=5), "$5"),
        (CardCost(coins=3, potion=True), "$3P"),
        (CardCost(potion=True), "P"),
        (CardCost(debt=8), "8D"),
        (CardCost(coins=4, debt=3), "$43D"),
        (CardCost(coins=3, extra="+"), "$3+"),
        (CardCost(coins=0, extra="*"), "$0*"),
        (CardCost(coins=2, potion=True, debt=4, extra="+"), "$2P4D+"),
    ],
)
def test_card_cost_str(cost: CardCost, text: str) -> None:
    assert str(cost) == text


def test_card_cost_orders_no_coins_as_zero_coins() -> None:
    costs = [
        CardCost(coins=5),
        CardCost(coins=2),
        CardCost(debt=8),
        CardCost(coins=0),
        CardCost(coins=3, potion=True),
        CardCost(coins=3),
    ]
    assert sorted(costs) == [
        CardCost(coins=0),
        CardCost(debt=8),
        CardCost(coins=2),
        CardCost(coins=3),
        CardCost(coins=3, potion=True),
        CardCost(coins=5),
    ]
    assert CardCost() <= CardCost(coins=0) <= CardCost()
    assert CardCost() >= CardCost(coins=0) >= CardCost()
    assert CardCost(debt=4) < CardCost(coins=2)
    assert CardCost(coins=2) > CardCost(debt=4)


def test_card_cost_is_frozen() -> None:
    cost = CardCost(coins=3)
    with pytest.raises(AttributeError):
        cost.coins = 5  # type: ignore # noqa: PGH003


def test_card_from_dict() -> None:
    card = Card.from_dict(
        {
            "name": "Familiar",
            "types": ["Action", "Attack"],
            "purpose": "Kingdom Pile",
            "cost": {"coins": 3, "potion": True},
            "set": "Alchemy",
            "editions": [1],
            "quantity": 10,
            "image": "Familiar.jpg",
            "instructions": "+1 Card\n+1 Action\nEach other player gains a Curse.",
        }
    )
    assert card == Card(
        name="Familiar",
        types=(CardType.ACTION, CardType.ATTACK),
        purpose=CardPurpose.KINGDOM_PILE,
        cost=CardCost(coins=3, potion=True),
        set=CardSet.ALCHEMY,
        editions=(CardSetEdition.FIRST_EDITION,),
        quantity=10,
        image="Familiar.jpg",
        instructions="+1 Card\n+1 Action\nEach other player gains a Curse.",
    )


def test_card_is_frozen(smithy: Card) -> None:
    with pytest.raises(AttributeError):
        smithy.name = "Village"  # type: ignore # noqa: PGH003


@pytest.mark.parametrize(
    ("set_", "editions", "display_set"),
    [
        (CardSet.BASE, (CardSetEdition.FIRST_EDITION,), "Base, 1E"),
        (CardSet.BASE, (CardSetEdition.SECOND_EDITION,), "Base, 2E"),
        (
            CardSet.BASE,
            (CardSetEdition.FIRST_EDITION, CardSetEdition.SECOND_EDITION),
            "Base",
        ),
        # Alchemy has no second edition, so its edition goes unmentioned
        (CardSet.ALCHEMY, (CardSetEdition.FIRST_EDITION,), "Alchemy"),
    ],
)
def test_card_display_set(
    smithy: Card,
    set_: CardSet,
    editions: tuple[CardSetEdition, ...],
    display_set: str,
) -> None:
    assert replace(smithy, set=set_, editions=editions).display_set == display_set


@pytest.mark.parametrize(
    ("cost", "has_potion_cost", "has_debt_cost"),
    [
        (CardCost(coins=4), False, False),
        (CardCost(coins=3, potion=True), True, False),
        (CardCost(debt=4), False, True),
    ],
)
def test_card_cost_properties(
    smithy: Card,
    cost: CardCost,
    has_potion_cost: bool,  # noqa: FBT001
    has_debt_cost: bool,  # noqa: FBT001
) -> None:
    card = replace(smithy, cost=cost)
    assert card.has_potion_cost is has_potion_cost
    assert card.has_debt_cost is has_debt_cost


PURPOSE_PROPERTIES: dict[CardPurpose, str] = {
    CardPurpose.BASIC: "is_basic",
    CardPurpose.KINGDOM_PILE: "is_kingdom",
    CardPurpose.LANDSCAPE: "is_landscape",
    CardPurpose.MIXED_PILE_CARD: "is_mixed_pile_card",
    CardPurpose.NON_SUPPLY: "is_non_supply",
    CardPurpose.STATUS: "is_status",
}


@pytest.mark.parametrize("purpose", CardPurpose)
def test_card_purpose_properties(smithy: Card, purpose: CardPurpose) -> None:
    card = replace(smithy, purpose=purpose)
    for other_purpose, prop_name in PURPOSE_PROPERTIES.items():
        assert getattr(card, prop_name) is (other_purpose == purpose)


# ── Card database ────────────────────────────────────────────────────────────

PURPOSE_INDEXES: dict[CardPurpose, str] = {
    CardPurpose.BASIC: "basic_cards",
    CardPurpose.KINGDOM_PILE: "kingdom_cards",
    CardPurpose.LANDSCAPE: "landscape_cards",
    CardPurpose.MIXED_PILE_CARD: "mixed_pile_cards",
    CardPurpose.NON_SUPPLY: "non_supply_cards",
    CardPurpose.STATUS: "status_cards",
}


def test_card_database_indexes_cards_by_purpose(smithy: Card) -> None:
    cards = {
        purpose: replace(smithy, name=f"{purpose} card", purpose=purpose)
        for purpose in CardPurpose
    }
    db = CardDatabase(list(cards.values()))
    for purpose, index in PURPOSE_INDEXES.items():
        assert getattr(db, index) == {cards[purpose].name: cards[purpose]}


def test_card_database_iter_and_len(smithy: Card) -> None:
    witch = replace(smithy, name="Witch")
    db = CardDatabase([smithy, witch])
    assert list(db) == [smithy, witch]
    assert len(db) == 2


def test_card_database_get_card_by_name(smithy: Card) -> None:
    db = CardDatabase([smithy])
    assert db.get_card_by_name("Smithy") == smithy
    with pytest.raises(ValueError, match="Card 'Witch' not found"):
        db.get_card_by_name("Witch")


def test_card_database_get_cards_by_set_edition(smithy: Card) -> None:
    adventurer = replace(
        smithy, name="Adventurer", editions=(CardSetEdition.FIRST_EDITION,)
    )
    db = CardDatabase([adventurer, smithy])
    assert db.get_cards_by_set_edition(CardSet.BASE, CardSetEdition.FIRST_EDITION) == [
        adventurer,
        smithy,
    ]
    assert db.get_cards_by_set_edition(CardSet.BASE, CardSetEdition.SECOND_EDITION) == [
        smithy
    ]


def test_card_database_get_cards_by_type(smithy: Card) -> None:
    witch = replace(smithy, name="Witch", types=(CardType.ACTION, CardType.ATTACK))
    db = CardDatabase([witch, smithy])
    assert db.get_cards_by_type(CardType.ATTACK) == [witch]
    assert db.get_cards_by_type(CardType.ACTION) == [witch, smithy]


def test_card_database_get_cards_by_cost(smithy: Card) -> None:
    cellar = replace(smithy, name="Cellar", cost=CardCost(coins=2))
    db = CardDatabase([cellar, smithy])
    assert db.get_cards_by_cost(CardCost(coins=4)) == [smithy]
    assert db.get_cards_by_cost(CardCost(coins=99)) == []


# ── Game ─────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "kind", [kind for kind in PileMarkKind if kind != PileMarkKind.TRAIT]
)
def test_pile_mark_str(kind: PileMarkKind) -> None:
    assert str(PileMark(kind)) == kind.value


def test_trait_pile_mark_str(smithy: Card) -> None:
    cursed = replace(smithy, name="Cursed", purpose=CardPurpose.LANDSCAPE)
    assert str(PileMark(PileMarkKind.TRAIT, trait=cursed)) == "Cursed (Trait)"


def test_trait_pile_mark_requires_a_trait() -> None:
    with pytest.raises(ValueError, match="kind TRAIT requires a trait card"):
        PileMark(PileMarkKind.TRAIT)


def test_other_pile_marks_must_not_have_a_trait(smithy: Card) -> None:
    with pytest.raises(ValueError, match="other kinds must not have one"):
        PileMark(PileMarkKind.BANE, trait=smithy)


def test_pile_has_no_marks_by_default(smithy: Card) -> None:
    assert Pile(card=smithy).marks == ()


def test_pile_is_frozen(smithy: Card) -> None:
    pile = Pile(card=smithy)
    with pytest.raises(AttributeError):
        pile.card = smithy  # type: ignore # noqa: PGH003


@pytest.mark.parametrize(
    ("sort_order", "expected_names"),
    [
        (KingdomSortOrder.NAME, ["Bazaar", "Cellar", "Engineer", "Moat", "Smithy"]),
        (KingdomSortOrder.COST, ["Engineer", "Cellar", "Moat", "Smithy", "Bazaar"]),
        (KingdomSortOrder.SET, ["Moat", "Smithy", "Cellar", "Bazaar", "Engineer"]),
    ],
)
def test_kingdom_sort_order_sort_key(
    smithy: Card, sort_order: KingdomSortOrder, expected_names: list[str]
) -> None:
    cards = [
        replace(smithy, name="Bazaar", cost=CardCost(coins=5), set=CardSet.SEASIDE),
        smithy,
        replace(smithy, name="Cellar", cost=CardCost(coins=2), set=CardSet.INTRIGUE),
        replace(smithy, name="Moat", cost=CardCost(coins=2)),
        replace(smithy, name="Engineer", cost=CardCost(debt=4), set=CardSet.EMPIRES),
    ]
    sorted_names = [card.name for card in sorted(cards, key=sort_order.sort_key)]
    assert sorted_names == expected_names


def test_game_is_empty_by_default() -> None:
    game = Game(basic_piles=[], kingdom_piles=[])
    assert game.non_supply_piles == []
    assert game.landscapes == []
    assert game.ally is None
    assert game.prophecy is None
    assert game.druid_boons == []
    assert game.materials == []
    assert game.setup_instructions == []
    assert game.sets_used == []


def test_game_card_properties_drop_the_marks(smithy: Card) -> None:
    copper = replace(smithy, name="Copper", purpose=CardPurpose.BASIC)
    hamlet = replace(smithy, name="Hamlet")
    weaver = replace(smithy, name="Weaver")
    game = Game(
        basic_piles=[Pile(card=copper)],
        kingdom_piles=[
            Pile(card=smithy),
            Pile(card=hamlet, marks=(PileMark(PileMarkKind.BANE),)),
        ],
        non_supply_piles=[Pile(card=weaver, marks=(PileMark(PileMarkKind.FERRYMAN),))],
    )
    assert game.basic_cards == [copper]
    assert game.kingdom_cards == [smithy, hamlet]
    assert game.non_supply_cards == [weaver]


def test_game_sets_used(smithy: Card) -> None:
    """The sets of the Kingdom, non-Supply and Landscape cards, in set order."""
    game = Game(
        basic_piles=[
            Pile(card=replace(smithy, name="Platinum", set=CardSet.PROSPERITY))
        ],
        kingdom_piles=[
            Pile(card=replace(smithy, name="Hamlet", set=CardSet.CORNUCOPIA_GUILDS)),
            Pile(card=smithy),
            Pile(card=replace(smithy, name="Village")),
        ],
        non_supply_piles=[
            Pile(card=replace(smithy, name="Madman", set=CardSet.DARK_AGES))
        ],
        landscapes=[replace(smithy, name="Alms", set=CardSet.ADVENTURES)],
    )
    assert game.sets_used == [
        CardSet.BASE,
        CardSet.CORNUCOPIA_GUILDS,
        CardSet.DARK_AGES,
        CardSet.ADVENTURES,
    ]
