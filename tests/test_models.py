"""Tests for ``dominion_setup.models``.

The sections follow ``models.py``. The cards here are hand-built (variations
on the ``smithy`` fixture), so these tests do not depend on the card data.
"""

from dataclasses import replace
from typing import Any

import pytest

from dominion_setup.models import (
    CARD_SETS_WITH_SECOND_EDITIONS,
    SET_EDITION_CHOICES,
    Board,
    Card,
    CardCost,
    CardDatabase,
    CardPurpose,
    CardSet,
    CardSetEdition,
    CardType,
    Game,
    KingdomSortOrder,
    Material,
    Pile,
    PileMark,
    PileMarkKind,
    SetupInstruction,
    slugify,
)

# ── Sets & editions ──────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("choice", "set_edition"),
    [
        ("base_1e", (CardSet.BASE, CardSetEdition.FIRST_EDITION)),
        ("base_2e", (CardSet.BASE, CardSetEdition.SECOND_EDITION)),
        (
            "cornucopia_guilds_2e",
            (CardSet.CORNUCOPIA_GUILDS, CardSetEdition.SECOND_EDITION),
        ),
        ("nocturne", (CardSet.NOCTURNE, CardSetEdition.FIRST_EDITION)),
        ("promo", (CardSet.PROMO, CardSetEdition.FIRST_EDITION)),
    ],
)
def test_set_edition_choices(
    choice: str,
    set_edition: tuple[CardSet, CardSetEdition],
) -> None:
    assert SET_EDITION_CHOICES[choice] == set_edition


def test_set_edition_choices_cover_every_set_and_edition() -> None:
    assert set(SET_EDITION_CHOICES.values()) == {
        *(
            (set_, edition)
            for set_ in CARD_SETS_WITH_SECOND_EDITIONS
            for edition in CardSetEdition
        ),
        *(
            (set_, CardSetEdition.FIRST_EDITION)
            for set_ in CardSet
            if set_ not in CARD_SETS_WITH_SECOND_EDITIONS
        ),
    }


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
        },
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


@pytest.mark.parametrize(
    ("name", "slug"),
    [
        ("Smithy", "smithy"),
        ("Way of the Mouse", "way-of-the-mouse"),
        ("Devil's Workshop", "devils-workshop"),
        ("Farmers' Market", "farmers-market"),
        ("Catapult/Rocks", "catapult-rocks"),
        ("Will-o'-Wisp", "will-o-wisp"),
        ("City-state", "city-state"),
        # a name in any case, or a slug, gives the same slug
        ("DEVIL'S WORKSHOP", "devils-workshop"),
        ("devils-workshop", "devils-workshop"),
        (" Village ", "village"),
    ],
)
def test_slugify(name: str, slug: str) -> None:
    assert slugify(name) == slug


def test_card_slug(smithy: Card) -> None:
    assert replace(smithy, name="Devil's Workshop").slug == "devils-workshop"


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
        smithy,
        name="Adventurer",
        editions=(CardSetEdition.FIRST_EDITION,),
    )
    db = CardDatabase([adventurer, smithy])
    assert db.get_cards_by_set_edition(CardSet.BASE, CardSetEdition.FIRST_EDITION) == [
        adventurer,
        smithy,
    ]
    assert db.get_cards_by_set_edition(CardSet.BASE, CardSetEdition.SECOND_EDITION) == [
        smithy,
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
    "kind",
    [kind for kind in PileMarkKind if kind != PileMarkKind.TRAIT],
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


def test_pile_mark_kind_is_extra_pile() -> None:
    """Extra piles are keyed in ``Board.extra_piles``; Obelisk and Trait are not."""
    assert {mark for mark in PileMarkKind if mark.is_extra_pile} == {
        PileMarkKind.BANE,
        PileMarkKind.FERRYMAN,
        PileMarkKind.WAY_OF_THE_MOUSE,
        PileMarkKind.APPROACHING_ARMY,
        PileMarkKind.RIVERBOAT,
    }


def test_pile_has_no_marks_by_default(smithy: Card) -> None:
    assert Pile(card=smithy).marks == ()


def test_pile_is_frozen(smithy: Card) -> None:
    pile = Pile(card=smithy)
    with pytest.raises(AttributeError):
        pile.card = smithy  # type: ignore # noqa: PGH003


def test_pile_to_dict(smithy: Card) -> None:
    pile = Pile(card=smithy, marks=(PileMark(PileMarkKind.BANE),), size=10)
    assert pile.to_dict() == {
        "name": "Smithy",
        "cost": {"coins": 4},
        "types": ["Action"],
        "purpose": "Kingdom Pile",
        "set": "Base",
        "marks": ["Bane"],
        "size": 10,
        "image": "Smithy.jpg",
        "instructions": "+3 Cards",
    }


def test_setup_instruction_str() -> None:
    instruction = SetupInstruction("Baker", "Each player gets +1 Coffers.")
    assert str(instruction) == "Baker: Each player gets +1 Coffers."


def test_setup_instruction_to_dict() -> None:
    instruction = SetupInstruction("Baker", "Each player gets +1 Coffers.")
    assert instruction.to_dict() == {
        "label": "Baker",
        "text": "Each player gets +1 Coffers.",
    }


@pytest.mark.parametrize(
    ("sort_order", "expected_names"),
    [
        (KingdomSortOrder.NAME, ["Bazaar", "Cellar", "Engineer", "Moat", "Smithy"]),
        (KingdomSortOrder.COST, ["Engineer", "Cellar", "Moat", "Smithy", "Bazaar"]),
        (KingdomSortOrder.SET, ["Moat", "Smithy", "Cellar", "Bazaar", "Engineer"]),
    ],
)
def test_kingdom_sort_order_sort_key(
    smithy: Card,
    sort_order: KingdomSortOrder,
    expected_names: list[str],
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


@pytest.mark.parametrize("sort_order", [KingdomSortOrder.COST, KingdomSortOrder.SET])
def test_kingdom_sort_order_sorts_by_name_after_a_cost_without_coins_or_zero(
    smithy: Card,
    sort_order: KingdomSortOrder,
) -> None:
    """A cost without coins sorts like $0, so the cards are sorted by name."""
    cards = [
        replace(smithy, name="Cheap", cost=CardCost()),
        replace(smithy, name="Alms", cost=CardCost(coins=0)),
        replace(smithy, name="Obelisk", cost=CardCost()),
    ]
    for order in (cards, cards[::-1]):
        sorted_names = [card.name for card in sorted(order, key=sort_order.sort_key)]
        assert sorted_names == ["Alms", "Cheap", "Obelisk"]


def test_board_to_code(smithy: Card) -> None:
    """Cards as slugs, with the keys in a fixed order and each list sorted."""

    def card(name: str) -> Card:
        return replace(smithy, name=name)

    board = Board(
        kingdom_cards=(card("Young Witch"), card("Devil's Workshop"), card("Bridge")),
        landscapes=(card("Way of the Mouse"), card("Cheap"), card("Fated")),
        extra_piles={
            PileMarkKind.RIVERBOAT: card("Cellar"),
            PileMarkKind.APPROACHING_ARMY: card("Militia"),
            PileMarkKind.WAY_OF_THE_MOUSE: card("Village"),
            PileMarkKind.FERRYMAN: card("Moneylender"),
            PileMarkKind.BANE: card("Moat"),
        },
        traits={card("Fated"): card("Young Witch"), card("Cheap"): card("Bridge")},
        obelisk=card("Young Witch"),
        ally=card("Architects' Guild"),
        prophecy=card("Approaching Army"),
        druid_boons=(
            card("The Sun's Gift"),
            card("The Earth's Gift"),
            card("The Sky's Gift"),
        ),
        black_market_deck=(card("Smithy"), card("Catapult/Rocks")),
        use_colony=True,
        use_shelters=True,
    )
    assert board.to_code(players=4) == (
        "players=4"
        "&kingdom=bridge,devils-workshop,young-witch"
        "&landscapes=cheap,fated,way-of-the-mouse"
        "&bane=moat"
        "&ferryman=moneylender"
        "&way-of-the-mouse=village"
        "&approaching-army=militia"
        "&riverboat=cellar"
        "&traits=cheap:bridge,fated:young-witch"
        "&obelisk=young-witch"
        "&ally=architects-guild"
        "&prophecy=approaching-army"
        "&boons=the-earths-gift,the-skys-gift,the-suns-gift"
        "&black-market=catapult-rocks,smithy"
        "&colony=on"
        "&shelters=on"
    )


@pytest.mark.parametrize(("players", "code"), [(None, ""), (3, "players=3")])
def test_empty_board_to_code(players: int | None, code: str) -> None:
    assert Board().to_code(players=players) == code


@pytest.mark.parametrize("use", [None, False])
def test_board_to_code_leaves_out_colony_and_shelters_unless_on(
    smithy: Card,
    use: bool | None,  # noqa: FBT001
) -> None:
    board = Board(kingdom_cards=(smithy,), use_colony=use, use_shelters=use)
    assert board.to_code() == "kingdom=smithy"


def test_board_to_code_writes_only_extra_piles(smithy: Card) -> None:
    """Marks in ``extra_piles`` that are not extra piles are left out.

    ``_check_board`` rejects them, but an unvalidated Board can hold one,
    and it must not be written: an Obelisk would collide with the
    ``obelisk`` key, and a Trait is an unknown key.
    """
    board = Board(
        kingdom_cards=(smithy,),
        extra_piles={
            PileMarkKind.OBELISK: replace(smithy, name="Cellar"),
            PileMarkKind.TRAIT: replace(smithy, name="Militia"),
            PileMarkKind.BANE: replace(smithy, name="Moat"),
        },
    )
    assert board.to_code() == "kingdom=smithy&bane=moat"


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
    """The sets of the Kingdom, non-Supply, Black Market and Landscape cards, in set order."""
    game = Game(
        basic_piles=[
            Pile(card=replace(smithy, name="Platinum", set=CardSet.PROSPERITY)),
        ],
        kingdom_piles=[
            Pile(card=replace(smithy, name="Hamlet", set=CardSet.CORNUCOPIA_GUILDS)),
            Pile(card=smithy),
            Pile(card=replace(smithy, name="Village")),
        ],
        non_supply_piles=[
            Pile(card=replace(smithy, name="Madman", set=CardSet.DARK_AGES)),
        ],
        landscapes=[replace(smithy, name="Alms", set=CardSet.ADVENTURES)],
        black_market_deck=[replace(smithy, name="Pooka", set=CardSet.NOCTURNE)],
    )
    assert game.sets_used == [
        CardSet.BASE,
        CardSet.CORNUCOPIA_GUILDS,
        CardSet.DARK_AGES,
        CardSet.ADVENTURES,
        CardSet.NOCTURNE,
    ]


def test_game_to_dict(smithy: Card) -> None:
    copper = replace(smithy, name="Copper", purpose=CardPurpose.BASIC)
    alms = replace(smithy, name="Alms", set=CardSet.ADVENTURES)
    game = Game(
        basic_piles=[Pile(card=copper, size=46)],
        kingdom_piles=[Pile(card=smithy, size=10)],
        landscapes=[alms],
        materials=[Material.COIN_TOKENS],
        setup_instructions=[SetupInstruction("Starting decks", "…")],
        players=2,
        board=Board(kingdom_cards=(smithy,), landscapes=(alms,)),
    )
    assert game.to_dict() == {
        "code": "players=2&kingdom=smithy&landscapes=alms",
        "players": 2,
        "sets": ["Base", "Adventures"],
        "kingdom": [Pile(card=smithy, size=10).to_dict()],
        "landscapes": [Pile(card=alms).to_dict()],
        "ally": None,
        "prophecy": None,
        "druid_boons": [],
        "non_supply": [],
        "black_market": [],
        "basic_supply": [Pile(card=copper, size=46).to_dict()],
        "materials": ["Coin tokens"],
        "setup": [{"label": "Starting decks", "text": "…"}],
    }
