import pytest

from dominion_setup.models import (
    CARD_SETS_WITH_SECOND_EDITIONS,
    DEFAULT_BASIC_CARD_NAMES,
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

from .conftest import CardFactory


def test_card_type_enum_values() -> None:
    assert CardType.ACTION == "Action"
    assert CardType.TREASURE == "Treasure"
    assert CardType.VICTORY == "Victory"
    assert CardType.CURSE == "Curse"
    assert CardType.ATTACK == "Attack"
    assert CardType.REACTION == "Reaction"
    assert CardType.DURATION == "Duration"
    assert CardType.PRIZE == "Prize"
    assert CardType.REWARD == "Reward"
    assert CardType.COMMAND == "Command"
    assert CardType.KNIGHT == "Knight"
    assert CardType.LOOTER == "Looter"
    assert CardType.RUINS == "Ruins"
    assert CardType.SHELTER == "Shelter"
    assert CardType.EVENT == "Event"
    assert CardType.RESERVE == "Reserve"
    assert CardType.TRAVELLER == "Traveller"
    assert CardType.CASTLE == "Castle"
    assert CardType.GATHERING == "Gathering"
    assert CardType.LANDMARK == "Landmark"
    assert CardType.BOON == "Boon"
    assert CardType.DOOM == "Doom"
    assert CardType.FATE == "Fate"
    assert CardType.HEIRLOOM == "Heirloom"
    assert CardType.HEX == "Hex"
    assert CardType.NIGHT == "Night"
    assert CardType.SPIRIT == "Spirit"
    assert CardType.STATE == "State"
    assert CardType.ZOMBIE == "Zombie"
    assert CardType.ARTIFACT == "Artifact"
    assert CardType.PROJECT == "Project"
    assert CardType.WAY == "Way"
    assert CardType.ALLY == "Ally"
    assert CardType.AUGUR == "Augur"
    assert CardType.CLASH == "Clash"
    assert CardType.FORT == "Fort"
    assert CardType.LIAISON == "Liaison"
    assert CardType.ODYSSEY == "Odyssey"
    assert CardType.TOWNSFOLK == "Townsfolk"
    assert CardType.WIZARD == "Wizard"
    assert CardType.LOOT == "Loot"
    assert CardType.TRAIT == "Trait"
    assert CardType.OMEN == "Omen"
    assert CardType.PROPHECY == "Prophecy"
    assert CardType.SHADOW == "Shadow"
    assert len(CardType) == 45


def test_card_purpose_enum_values() -> None:
    assert CardPurpose.BASIC == "Basic"
    assert CardPurpose.KINGDOM_PILE == "Kingdom Pile"
    assert CardPurpose.LANDSCAPE == "Landscape"
    assert CardPurpose.MIXED_PILE_CARD == "Mixed Pile Card"
    assert CardPurpose.NON_SUPPLY == "Non-Supply"
    assert CardPurpose.STATUS == "Status"
    assert len(CardPurpose) == 6


def test_cost_defaults() -> None:
    cost = CardCost()
    assert cost.coins == 0
    assert cost.potion is False
    assert cost.debt == 0
    assert cost.extra is None


def test_cost_frozen() -> None:
    cost = CardCost(coins=3)
    with pytest.raises(AttributeError):
        cost.coins = 5  # type: ignore # noqa: PGH003


def test_cost_from_dict() -> None:
    cost = CardCost.from_dict({"coins": 5})
    assert cost.coins == 5


def test_cost_from_dict_zero() -> None:
    cost = CardCost.from_dict({"coins": 0})
    assert cost.coins == 0


def test_cost_potion_default() -> None:
    cost = CardCost()
    assert cost.potion is False


def test_cost_with_potion() -> None:
    cost = CardCost(coins=3, potion=True)
    assert cost.potion is True


def test_cost_from_dict_with_potion() -> None:
    cost = CardCost.from_dict({"coins": 2, "potion": True})
    assert cost == CardCost(coins=2, potion=True)


def test_cost_from_dict_without_potion_key() -> None:
    cost = CardCost.from_dict({"coins": 5})
    assert cost == CardCost(coins=5, potion=False)


def test_cost_str_coins_only() -> None:
    assert str(CardCost(coins=5)) == "$5"


def test_cost_str_with_potion() -> None:
    assert str(CardCost(coins=3, potion=True)) == "$3P"


def test_cost_str_potion_only() -> None:
    assert str(CardCost(coins=0, potion=True)) == "P"


def test_cost_str_with_debt() -> None:
    assert str(CardCost(coins=0, debt=8)) == "8D"


def test_cost_str_coins_and_debt() -> None:
    assert str(CardCost(coins=4, debt=3)) == "$43D"


def test_cost_str_with_extra_plus() -> None:
    assert str(CardCost(coins=3, extra="+")) == "$3+"


def test_cost_str_with_extra_star() -> None:
    assert str(CardCost(coins=0, extra="*")) == "$0*"


def test_cost_str_all_components() -> None:
    assert str(CardCost(coins=2, potion=True, debt=4, extra="+")) == "$2P4D+"


def test_cost_from_dict_with_debt() -> None:
    cost = CardCost.from_dict({"coins": 0, "debt": 8})
    assert cost == CardCost(coins=0, debt=8)


def test_cost_from_dict_with_extra() -> None:
    cost = CardCost.from_dict({"coins": 3, "extra": "+"})
    assert cost == CardCost(coins=3, extra="+")


def test_cost_from_dict_empty() -> None:
    cost = CardCost.from_dict({})
    assert cost == CardCost()


def test_set_enum_values() -> None:
    assert CardSet.BASE == "Base"
    assert CardSet.INTRIGUE == "Intrigue"
    assert CardSet.SEASIDE == "Seaside"
    assert CardSet.ALCHEMY == "Alchemy"
    assert CardSet.PROSPERITY == "Prosperity"
    assert CardSet.CORNUCOPIA_GUILDS == "Cornucopia & Guilds"
    assert CardSet.HINTERLANDS == "Hinterlands"
    assert CardSet.DARK_AGES == "Dark Ages"
    assert CardSet.ADVENTURES == "Adventures"
    assert CardSet.EMPIRES == "Empires"
    assert CardSet.NOCTURNE == "Nocturne"
    assert CardSet.RENAISSANCE == "Renaissance"
    assert CardSet.MENAGERIE == "Menagerie"
    assert CardSet.ALLIES == "Allies"
    assert CardSet.PLUNDER == "Plunder"
    assert CardSet.RISING_SUN == "Rising Sun"
    assert CardSet.PROMO == "Promo"
    assert len(CardSet) == 17


def test_card_set_edition_enum_values() -> None:
    assert CardSetEdition.FIRST_EDITION == 1
    assert CardSetEdition.SECOND_EDITION == 2
    assert len(CardSetEdition) == 2


def test_card_sets_with_second_editions() -> None:
    assert CARD_SETS_WITH_SECOND_EDITIONS == frozenset(
        {
            CardSet.BASE,
            CardSet.INTRIGUE,
            CardSet.SEASIDE,
            CardSet.PROSPERITY,
            CardSet.CORNUCOPIA_GUILDS,
            CardSet.HINTERLANDS,
        }
    )


def test_default_basic_card_names() -> None:
    assert DEFAULT_BASIC_CARD_NAMES == (
        "Copper",
        "Silver",
        "Gold",
        "Estate",
        "Duchy",
        "Province",
        "Curse",
    )


def test_card_construction(smithy: Card) -> None:
    assert smithy.name == "Smithy"
    assert smithy.types == (CardType.ACTION,)
    assert smithy.purpose == CardPurpose.KINGDOM_PILE
    assert smithy.cost.coins == 4
    assert smithy.set == CardSet.BASE
    assert smithy.editions == (
        CardSetEdition.FIRST_EDITION,
        CardSetEdition.SECOND_EDITION,
    )
    assert smithy.quantity == 10
    assert smithy.image == "Smithy.jpg"
    assert smithy.instructions == "+3 Cards"


def test_card_has_potion_cost_default(smithy: Card) -> None:
    assert smithy.has_potion_cost is False


def test_card_frozen(smithy: Card) -> None:
    with pytest.raises(AttributeError):
        smithy.name = "Village"  # type: ignore # noqa: PGH003


def test_card_types_are_tuple(make_card: CardFactory) -> None:
    moat = make_card(
        name="Moat",
        types=(CardType.ACTION, CardType.REACTION),
        cost_coins=2,
        image="Moat.jpg",
        instructions="+2 Cards\n-----\nWhen another player plays an Attack card, you may first reveal this from your hand, to be unaffected by it.",
    )
    assert isinstance(moat.types, tuple)
    assert moat.types == (CardType.ACTION, CardType.REACTION)


def test_card_from_dict_minimal() -> None:
    data = {
        "name": "Smithy",
        "types": ["Action"],
        "purpose": "Kingdom Pile",
        "cost": {"coins": 4},
        "set": "Base",
        "editions": [1, 2],
        "quantity": 10,
        "image": "Smithy.jpg",
        "instructions": "+3 Cards",
    }
    card = Card.from_dict(data)
    assert card.name == "Smithy"
    assert card.types == (CardType.ACTION,)
    assert card.cost == CardCost(coins=4)
    assert card.set == CardSet.BASE
    assert card.editions == (
        CardSetEdition.FIRST_EDITION,
        CardSetEdition.SECOND_EDITION,
    )
    assert card.quantity == 10
    assert card.image == "Smithy.jpg"
    assert card.instructions == "+3 Cards"


def test_card_from_dict_with_potion_cost() -> None:
    data = {
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
    card = Card.from_dict(data)
    assert card.name == "Familiar"
    assert card.types == (CardType.ACTION, CardType.ATTACK)
    assert card.cost == CardCost(coins=3, potion=True)
    assert card.cost.potion is True
    assert card.set == CardSet.ALCHEMY
    assert card.editions == (CardSetEdition.FIRST_EDITION,)
    assert card.quantity == 10
    assert card.image == "Familiar.jpg"
    assert card.instructions == "+1 Card\n+1 Action\nEach other player gains a Curse."
    assert card.has_potion_cost is True


def test_card_from_dict_multiple_types() -> None:
    data = {
        "name": "Witch",
        "types": ["Action", "Attack"],
        "purpose": "Kingdom Pile",
        "cost": {"coins": 5},
        "set": "Base",
        "editions": [1, 2],
        "quantity": 10,
        "image": "Witch.jpg",
        "instructions": "+2 Cards\nEach other player gains a Curse.",
    }
    card = Card.from_dict(data)
    assert card.types == (CardType.ACTION, CardType.ATTACK)


def test_card_from_dict_multi_editions() -> None:
    data = {
        "name": "Smithy",
        "types": ["Action"],
        "purpose": "Kingdom Pile",
        "cost": {"coins": 4},
        "set": "Base",
        "editions": [1, 2],
        "quantity": 10,
        "image": "Smithy.jpg",
        "instructions": "+3 Cards",
    }
    card = Card.from_dict(data)
    assert card.set == CardSet.BASE
    assert card.editions == (
        CardSetEdition.FIRST_EDITION,
        CardSetEdition.SECOND_EDITION,
    )


def test_game_construction() -> None:
    game = Game(basic_piles=[], kingdom_piles=[])
    assert game.kingdom_piles == []
    assert game.kingdom_cards == []
    assert game.basic_piles == []
    assert game.sets_used == []
    assert game.landscapes == []
    assert game.non_supply_piles == []
    assert game.non_supply_cards == []
    assert game.setup_instructions == []


def test_game_construction_with_all_fields(make_card: CardFactory) -> None:
    copper = make_card(
        name="Copper",
        types=(CardType.TREASURE,),
        purpose=CardPurpose.BASIC,
        cost_coins=0,
    )
    village = make_card(name="Village", cost_coins=3)
    market = make_card(name="Market", cost_coins=5)
    bane = make_card(name="Hamlet", cost_coins=2)
    ferryman = make_card(name="Weaver", cost_coins=4, set_=CardSet.CORNUCOPIA_GUILDS)
    alms = make_card(
        name="Alms",
        types=(CardType.EVENT,),
        purpose=CardPurpose.LANDSCAPE,
        cost_coins=0,
        set_=CardSet.ADVENTURES,
        editions=(CardSetEdition.FIRST_EDITION,),
        quantity=1,
        image="Alms.jpg",
        instructions="Once per turn: If you have no Treasures in play, gain a card costing up to $4.",
    )
    prize = make_card(
        name="Bag of Gold",
        types=(CardType.PRIZE,),
        purpose=CardPurpose.NON_SUPPLY,
        cost_coins=0,
    )
    game = Game(
        basic_piles=[Pile(card=copper)],
        kingdom_piles=[
            Pile(card=village),
            Pile(card=market),
            Pile(card=bane, marks=(PileMark(PileMarkKind.BANE),)),
        ],
        landscapes=[alms],
        non_supply_piles=[
            Pile(card=ferryman, marks=(PileMark(PileMarkKind.FERRYMAN),)),
            Pile(card=prize),
        ],
        setup_instructions=["Baker: Each player gets +1 Coffers."],
    )
    assert game.basic_piles == [Pile(card=copper)]
    assert game.kingdom_cards == [village, market, bane]
    assert game.non_supply_cards == [ferryman, prize]
    assert game.setup_instructions == ["Baker: Each player gets +1 Coffers."]
    assert game.sets_used == [
        CardSet.BASE,
        CardSet.CORNUCOPIA_GUILDS,
        CardSet.ADVENTURES,
    ]


def test_card_database_construction() -> None:
    db = CardDatabase([])
    assert db.kingdom_cards == {}
    assert db.basic_cards == {}


def test_card_database_get_cards_by_set_edition(make_card: CardFactory) -> None:
    adventurer = make_card(
        name="Adventurer",
        cost_coins=6,
        editions=(CardSetEdition.FIRST_EDITION,),
        image="Adventurer.jpg",
        instructions="Reveal cards from your deck until you reveal 2 Treasure cards. Put those Treasure cards into your hand and discard the other revealed cards.",
    )
    village = make_card(
        name="Village",
        cost_coins=3,
        image="Village.jpg",
        instructions="+1 Card\n+2 Actions",
    )
    db = CardDatabase([adventurer, village])
    dominion = db.get_cards_by_set_edition(CardSet.BASE, CardSetEdition.FIRST_EDITION)
    assert len(dominion) == 2
    assert adventurer in dominion
    assert village in dominion
    base_2e = db.get_cards_by_set_edition(CardSet.BASE, CardSetEdition.SECOND_EDITION)
    assert len(base_2e) == 1
    assert village in base_2e


def test_card_database_get_cards_by_type(make_card: CardFactory, smithy: Card) -> None:
    witch = make_card(
        name="Witch",
        types=(CardType.ACTION, CardType.ATTACK),
        cost_coins=5,
        image="Witch.jpg",
        instructions="+2 Cards\nEach other player gains a Curse.",
    )
    db = CardDatabase([witch, smithy])
    attacks = db.get_cards_by_type(CardType.ATTACK)
    assert len(attacks) == 1
    assert attacks[0] == witch

    actions = db.get_cards_by_type(CardType.ACTION)
    assert len(actions) == 2


def test_kingdom_sort_order_enum_values() -> None:
    assert KingdomSortOrder.NAME == "name"
    assert KingdomSortOrder.COST == "cost"
    assert KingdomSortOrder.SET == "set"
    assert len(KingdomSortOrder) == 3


def test_card_has_debt_cost_false(smithy: Card) -> None:
    assert smithy.has_debt_cost is False


def test_card_has_debt_cost_true(make_card: CardFactory) -> None:
    card = make_card(
        name="Engineer",
        cost_coins=0,
        cost_debt=4,
        set_=CardSet.EMPIRES,
        editions=(CardSetEdition.FIRST_EDITION,),
        image="Engineer.jpg",
        instructions="Gain a card costing up to $4.",
    )
    assert card.has_debt_cost is True


@pytest.mark.parametrize(
    ("purpose", "prop_name"),
    [
        (CardPurpose.BASIC, "is_basic"),
        (CardPurpose.KINGDOM_PILE, "is_kingdom"),
        (CardPurpose.LANDSCAPE, "is_landscape"),
        (CardPurpose.MIXED_PILE_CARD, "is_mixed_pile_card"),
        (CardPurpose.NON_SUPPLY, "is_non_supply"),
        (CardPurpose.STATUS, "is_status"),
    ],
)
def test_card_purpose_property(
    make_card: CardFactory, purpose: CardPurpose, prop_name: str
) -> None:
    card = make_card(name="TestCard", purpose=purpose)
    assert getattr(card, prop_name) is True
    # verify all other purpose properties are False
    all_props = {
        "is_basic",
        "is_kingdom",
        "is_landscape",
        "is_mixed_pile_card",
        "is_non_supply",
        "is_status",
    }
    for other_prop in all_props - {prop_name}:
        assert getattr(card, other_prop) is False


def test_card_database_landscape_cards(make_card: CardFactory, smithy: Card) -> None:
    landscape = make_card(
        name="Obelisk",
        types=(CardType.LANDMARK,),
        purpose=CardPurpose.LANDSCAPE,
        cost_coins=0,
        set_=CardSet.EMPIRES,
        editions=(CardSetEdition.FIRST_EDITION,),
        quantity=1,
        image="Obelisk.jpg",
        instructions="When scoring, 2 VP per card you have from the chosen pile.Setup: Choose a random Action Supply pile.",
    )
    db = CardDatabase([landscape, smithy])
    assert db.landscape_cards == {"Obelisk": landscape}
    assert db.kingdom_cards == {"Smithy": smithy}


def test_card_database_mixed_pile_cards(make_card: CardFactory) -> None:
    encampment = make_card(
        name="Encampment",
        purpose=CardPurpose.MIXED_PILE_CARD,
        cost_coins=2,
        set_=CardSet.EMPIRES,
        editions=(CardSetEdition.FIRST_EDITION,),
        quantity=5,
        image="Encampment.jpg",
        instructions="+2 Cards\n+2 Actions\nYou may reveal a Gold or Plunder from your hand. If you do not, set this aside, and return it to its pile at the start of Clean-up.",
    )
    db = CardDatabase([encampment])
    assert db.mixed_pile_cards == {"Encampment": encampment}
    assert db.kingdom_cards == {}


def test_card_database_non_supply_cards(make_card: CardFactory) -> None:
    madman = make_card(
        name="Madman",
        purpose=CardPurpose.NON_SUPPLY,
        cost_coins=0,
        cost_extra="*",
        set_=CardSet.DARK_AGES,
        editions=(CardSetEdition.FIRST_EDITION,),
        quantity=10,
        image="Madman.jpg",
        instructions="+2 Actions\nReturn this to the Madman pile. If you do, +1 Card per card in your hand.\n(This is not in the Supply.)",
    )
    db = CardDatabase([madman])
    assert db.non_supply_cards == {"Madman": madman}
    assert db.kingdom_cards == {}


def test_card_database_status_cards(make_card: CardFactory) -> None:
    flag = make_card(
        name="Flag",
        types=(CardType.ARTIFACT,),
        purpose=CardPurpose.STATUS,
        cost_coins=0,
        set_=CardSet.RENAISSANCE,
        editions=(CardSetEdition.FIRST_EDITION,),
        quantity=1,
        image="Flag.jpg",
        instructions="When drawing your hand, +1 Card.",
    )
    db = CardDatabase([flag])
    assert db.status_cards == {"Flag": flag}
    assert db.kingdom_cards == {}


def test_card_database_get_card_by_name_not_found() -> None:
    db = CardDatabase([])
    with pytest.raises(ValueError, match="Card 'Nonexistent' not found"):
        db.get_card_by_name("Nonexistent")


def test_card_database_get_card_by_name_success(smithy: Card) -> None:
    db = CardDatabase([smithy])
    assert db.get_card_by_name("Smithy") == smithy


def test_card_display_set_single_edition_with_second_editions(
    make_card: CardFactory,
) -> None:
    adventurer = make_card(
        name="Adventurer",
        cost_coins=6,
        editions=(CardSetEdition.FIRST_EDITION,),
        image="Adventurer.jpg",
        instructions="Reveal cards from your deck until you reveal 2 Treasure cards. Put those Treasure cards into your hand and discard the other revealed cards.",
    )
    assert adventurer.display_set == "Base, 1E"


def test_card_display_set_both_editions(smithy: Card) -> None:
    assert smithy.display_set == "Base"


def test_card_display_set_no_second_edition_set(make_card: CardFactory) -> None:
    herbalist = make_card(
        name="Herbalist",
        cost_coins=2,
        set_=CardSet.ALCHEMY,
        editions=(CardSetEdition.FIRST_EDITION,),
        image="Herbalist.jpg",
        instructions="+1 Buy\n+$1\nOnce this turn, when you discard a Treasure from play, you may put it onto your deck.",
    )
    assert herbalist.display_set == "Alchemy"


def test_card_database_iter(make_card: CardFactory, smithy: Card) -> None:
    witch = make_card(name="Witch", cost_coins=5, image="Witch.jpg")
    db = CardDatabase([smithy, witch])
    assert list(db) == [smithy, witch]


def test_card_database_len(make_card: CardFactory, smithy: Card) -> None:
    witch = make_card(name="Witch", cost_coins=5, image="Witch.jpg")
    db = CardDatabase([smithy, witch])
    assert len(db) == 2


def test_card_database_get_cards_by_cost(make_card: CardFactory) -> None:
    cheap = make_card(name="Cellar", cost_coins=2, image="Cellar.jpg")
    mid = make_card(name="Smithy", cost_coins=4, image="Smithy.jpg")
    expensive = make_card(name="Witch", cost_coins=5, image="Witch.jpg")
    db = CardDatabase([cheap, mid, expensive])
    fours = db.get_cards_by_cost(CardCost(coins=4))
    assert fours == [mid]
    assert db.get_cards_by_cost(CardCost(coins=99)) == []


def test_game_is_mutable(smithy: Card) -> None:
    game = Game(basic_piles=[], kingdom_piles=[])
    smithy_pile = Pile(card=smithy)
    game.kingdom_piles.append(smithy_pile)
    assert len(game.kingdom_piles) == 1
    assert game.kingdom_cards == [smithy]
    game.non_supply_piles.append(smithy_pile)
    assert len(game.non_supply_piles) == 1
    assert game.non_supply_cards == [smithy]
    game.setup_instructions.append("test")
    assert len(game.setup_instructions) == 1


def test_pile_mark_kind_enum_values() -> None:
    assert PileMarkKind.BANE == "Bane"
    assert PileMarkKind.OBELISK == "Obelisk"
    assert PileMarkKind.FERRYMAN == "Ferryman"
    assert PileMarkKind.WAY_OF_THE_MOUSE == "Way of the Mouse"
    assert PileMarkKind.TRAIT == "Trait"
    assert PileMarkKind.APPROACHING_ARMY == "Approaching Army"
    assert PileMarkKind.RIVERBOAT == "Riverboat"
    assert len(PileMarkKind) == 7


def test_pile_mark_str_non_trait() -> None:
    assert str(PileMark(PileMarkKind.BANE)) == "Bane"
    assert str(PileMark(PileMarkKind.OBELISK)) == "Obelisk"
    assert str(PileMark(PileMarkKind.FERRYMAN)) == "Ferryman"


def test_pile_mark_str_trait(make_card: CardFactory) -> None:
    cursed = make_card(
        name="Cursed",
        types=(CardType.TRAIT,),
        purpose=CardPurpose.LANDSCAPE,
        cost_coins=5,
        set_=CardSet.PLUNDER,
        editions=(CardSetEdition.FIRST_EDITION,),
        quantity=1,
        image="Cursed.jpg",
        instructions="",
    )
    assert str(PileMark(PileMarkKind.TRAIT, trait=cursed)) == "Cursed (Trait)"


def test_pile_mark_trait_requires_card() -> None:
    with pytest.raises(ValueError, match="kind TRAIT requires a trait card"):
        PileMark(PileMarkKind.TRAIT)


def test_pile_mark_non_trait_must_not_have_card(make_card: CardFactory) -> None:
    cursed = make_card(name="Cursed")
    with pytest.raises(ValueError, match="other kinds must not have one"):
        PileMark(PileMarkKind.BANE, trait=cursed)


def test_pile_default_marks(smithy: Card) -> None:
    pile = Pile(card=smithy)
    assert pile.card is smithy
    assert pile.marks == ()


def test_pile_with_marks(smithy: Card) -> None:
    pile = Pile(card=smithy, marks=(PileMark(PileMarkKind.OBELISK),))
    assert pile.marks == (PileMark(PileMarkKind.OBELISK),)


def test_pile_frozen(smithy: Card) -> None:
    pile = Pile(card=smithy)
    with pytest.raises(AttributeError):
        pile.card = smithy  # type: ignore # noqa: PGH003


def test_game_kingdom_cards_drops_marks(make_card: CardFactory) -> None:
    village = make_card(name="Village", cost_coins=3)
    market = make_card(name="Market", cost_coins=5)
    game = Game(
        basic_piles=[],
        kingdom_piles=[
            Pile(card=village, marks=(PileMark(PileMarkKind.OBELISK),)),
            Pile(card=market),
        ],
    )
    assert game.kingdom_cards == [village, market]


def test_game_non_supply_cards_drops_marks(make_card: CardFactory) -> None:
    weaver = make_card(name="Weaver", cost_coins=4)
    game = Game(
        basic_piles=[],
        kingdom_piles=[],
        non_supply_piles=[
            Pile(card=weaver, marks=(PileMark(PileMarkKind.FERRYMAN),)),
        ],
    )
    assert game.non_supply_cards == [weaver]
