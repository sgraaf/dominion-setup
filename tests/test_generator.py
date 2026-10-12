"""Tests for ``dominion_setup.generator``.

The sections follow ``generator.py``: ``generate_game`` end to end, then how it
assembles the ``Game``, then one section per numbered setup step. The step
tests call the step's helper directly, with real cards from the database, so
every rule is checked on a known set of cards instead of on whatever a random
seed happens to draw.
"""

import os
import random
import subprocess
import sys
from collections.abc import Callable, Iterable, Sequence
from dataclasses import replace

import pytest

from dominion_setup import generator
from dominion_setup.cli import SET_EDITION_CHOICES
from dominion_setup.generator import (
    SetupGenerationError,
    _basic_cards,
    _choose_ally,
    _choose_druid_boons,
    _choose_extra_piles,
    _choose_obelisk_pile,
    _choose_trait_piles,
    _companion_cards,
    _draw_kingdom,
    _heirlooms,
    _materials,
    _setup_instructions,
    generate_game,
)
from dominion_setup.models import (
    Card,
    CardDatabase,
    CardSet,
    CardSetEdition,
    CardType,
    Game,
    KingdomSortOrder,
    Material,
    Pile,
)

BASIC_SUPPLY = ["Copper", "Silver", "Gold", "Estate", "Duchy", "Province", "Curse"]


def get_cards(db: CardDatabase, *names: str) -> list[Card]:
    """Look up cards in *db* by name."""
    return [db.get_card_by_name(name) for name in names]


def card_names(cards: Iterable[Card]) -> list[str]:
    return [card.name for card in cards]


def pile_marks(piles: Iterable[Pile]) -> dict[str, list[str]]:
    """Map each pile's card name to its marks, as displayed (e.g. "Bane")."""
    return {pile.card.name: [str(mark) for mark in pile.marks] for pile in piles}


# ── generate_game ────────────────────────────────────────────────────────────


def test_generates_ten_distinct_kingdom_piles(db: CardDatabase) -> None:
    game = generate_game(
        db, sets_editions={(CardSet.BASE, CardSetEdition.SECOND_EDITION)}
    )
    assert len(set(card_names(game.kingdom_cards))) == 10


SELECTIONS: dict[str, set[tuple[CardSet, CardSetEdition]]] = {
    **{choice: {set_edition} for choice, set_edition in SET_EDITION_CHOICES.items()},
    "base_1e+intrigue_2e": {
        (CardSet.BASE, CardSetEdition.FIRST_EDITION),
        (CardSet.INTRIGUE, CardSetEdition.SECOND_EDITION),
    },
}


@pytest.mark.parametrize("sets_editions", SELECTIONS.values(), ids=SELECTIONS)
def test_draws_only_from_the_selected_sets_and_editions(
    db: CardDatabase, sets_editions: set[tuple[CardSet, CardSetEdition]]
) -> None:
    game = generate_game(db, sets_editions=sets_editions)
    for card in [*game.kingdom_cards, *game.landscapes]:
        assert {(card.set, edition) for edition in card.editions} & sets_editions


@pytest.mark.parametrize("sort_order", KingdomSortOrder)
def test_sorts_kingdom_piles_and_landscapes(
    db: CardDatabase, sort_order: KingdomSortOrder
) -> None:
    game = generate_game(db, sort_order=sort_order, max_landscapes=10)
    assert len(game.landscapes) > 1
    assert game.kingdom_cards == sorted(game.kingdom_cards, key=sort_order.sort_key)
    assert game.landscapes == sorted(game.landscapes, key=sort_order.sort_key)


@pytest.mark.parametrize(
    ("use_colony", "set_"),
    [(True, CardSet.BASE), (False, CardSet.PROSPERITY)],
)
def test_use_colony_overrides_the_random_choice(
    db: CardDatabase,
    use_colony: bool,  # noqa: FBT001
    set_: CardSet,
) -> None:
    game = generate_game(
        db,
        sets_editions={(set_, CardSetEdition.SECOND_EDITION)},
        use_colony=use_colony,
    )
    basic_names = card_names(game.basic_cards)
    assert ("Colony" in basic_names) is use_colony
    assert ("Platinum" in basic_names) is use_colony


@pytest.mark.parametrize(
    ("use_shelters", "set_"),
    [(True, CardSet.BASE), (False, CardSet.DARK_AGES)],
)
def test_use_shelters_overrides_the_random_choice(
    db: CardDatabase,
    use_shelters: bool,  # noqa: FBT001
    set_: CardSet,
) -> None:
    game = generate_game(
        db,
        sets_editions={(set_, CardSetEdition.FIRST_EDITION)},
        use_shelters=use_shelters,
    )
    assert ("Shelters" in card_names(game.basic_cards)) is use_shelters


def test_same_seed_generates_the_same_game(db: CardDatabase) -> None:
    random.seed(42)
    game = generate_game(db)
    random.seed(42)
    assert generate_game(db) == game


def test_same_seed_generates_the_same_game_in_every_process() -> None:
    """A given seed yields the same setup regardless of string hash randomization."""
    script = (
        "import random; from dominion_setup import generate_game, load_card_database; "
        "random.seed(42); game = generate_game(load_card_database()); "
        "print([pile.card.name for pile in game.kingdom_piles + game.non_supply_piles])"
    )
    outputs = {
        subprocess.run(  # noqa: S603
            [sys.executable, "-c", script],
            env={**os.environ, "PYTHONHASHSEED": hash_seed},
            capture_output=True,
            check=True,
            text=True,
        ).stdout
        for hash_seed in ("1", "2", "3")
    }
    assert len(outputs) == 1


def test_setup_generation_error_is_a_value_error() -> None:
    """``SetupGenerationError`` subclasses ``ValueError`` for backwards compatibility."""
    assert issubclass(SetupGenerationError, ValueError)


# ── Assembling the Game ──────────────────────────────────────────────────────


@pytest.fixture
def generate_with(
    db: CardDatabase, monkeypatch: pytest.MonkeyPatch
) -> Callable[..., Game]:
    """Return ``generate_game`` with the kingdom draw (step 1) pinned.

    The returned function takes the names of the drawn Kingdom cards and, if
    any, of the drawn Landscapes and of the unused Kingdom cards (in the order
    extra piles are chosen from them), so the other steps run on known cards.
    Colony and Shelters are off.
    """

    def _generate_with(
        kingdom: Sequence[str],
        landscapes: Sequence[str] = (),
        unused: Sequence[str] = (),
    ) -> Game:
        monkeypatch.setattr(
            generator,
            "_draw_kingdom",
            lambda *_args, **_kwargs: (
                get_cards(db, *kingdom),
                get_cards(db, *landscapes),
                get_cards(db, *unused),
            ),
        )
        return generate_game(db, use_colony=False, use_shelters=False)

    return _generate_with


def test_extra_supply_pile_joins_the_kingdom_with_its_mark(
    generate_with: Callable[..., Game],
) -> None:
    game = generate_with(kingdom=["Young Witch"], unused=["Hamlet"])
    assert pile_marks(game.kingdom_piles) == {"Hamlet": ["Bane"], "Young Witch": []}


def test_set_aside_pile_goes_beside_the_supply_with_its_mark(
    generate_with: Callable[..., Game],
) -> None:
    game = generate_with(kingdom=["Ferryman"], unused=["Smithy"])
    assert pile_marks(game.kingdom_piles) == {"Ferryman": []}
    assert pile_marks(game.non_supply_piles) == {"Smithy": ["Ferryman"]}


def test_set_aside_card_brings_its_own_setup(
    generate_with: Callable[..., Game],
) -> None:
    """A card set aside for Riverboat can still be played, so it needs its components."""
    game = generate_with(kingdom=["Riverboat"], unused=["Tormentor"])
    assert pile_marks(game.non_supply_piles) == {
        "Tormentor": ["Riverboat"],
        "Hexes": [],
        "Deluded": [],
        "Miserable": [],
        "Imp": [],
    }


def test_pile_can_carry_several_marks(generate_with: Callable[..., Game]) -> None:
    game = generate_with(kingdom=["Village"], landscapes=["Cursed", "Obelisk"])
    assert pile_marks(game.kingdom_piles) == {"Village": ["Cursed (Trait)", "Obelisk"]}


def test_heirlooms_join_the_basic_supply_in_sort_order(
    generate_with: Callable[..., Game],
) -> None:
    game = generate_with(kingdom=["Pooka", "Tracker"])
    assert card_names(game.basic_cards) == [*BASIC_SUPPLY, "Pouch", "Cursed Gold"]
    assert game.setup_instructions[-1].startswith(
        "Heirlooms: Each player replaces 2 starting Coppers with Pouch, Cursed Gold."
    )


def test_dealt_cards_get_their_own_fields(generate_with: Callable[..., Game]) -> None:
    game = generate_with(kingdom=["Druid", "Sycophant", "Kitsune"], unused=["Militia"])
    assert len(game.druid_boons) == 3
    assert game.ally is not None
    assert game.prophecy is not None


def test_no_dealt_cards_without_their_triggers(
    generate_with: Callable[..., Game],
) -> None:
    game = generate_with(kingdom=["Village"])
    assert game.druid_boons == []
    assert game.ally is None
    assert game.prophecy is None


# ── 1. Kingdom ───────────────────────────────────────────────────────────────


def test_draw_kingdom_draws_ten_cards_and_leaves_the_rest_unused(
    db: CardDatabase,
) -> None:
    kingdom, _landscapes, unused = _draw_kingdom(
        db, sets_editions=None, max_landscapes=2
    )
    assert len(kingdom) == 10
    assert sorted(card_names([*kingdom, *unused])) == sorted(db.kingdom_cards)


@pytest.mark.parametrize("max_landscapes", [0, 1, 2, 10])
def test_draw_kingdom_draws_at_most_max_landscapes(
    db: CardDatabase, max_landscapes: int
) -> None:
    _kingdom, landscapes, _unused = _draw_kingdom(
        db, sets_editions=None, max_landscapes=max_landscapes
    )
    assert len(landscapes) <= max_landscapes
    selectable_types = {
        CardType.EVENT,
        CardType.LANDMARK,
        CardType.PROJECT,
        CardType.WAY,
        CardType.TRAIT,
    }
    for landscape in landscapes:
        assert selectable_types & set(landscape.types)


def test_draw_kingdom_never_draws_allies_or_prophecies(
    db: CardDatabase, smithy: Card
) -> None:
    kingdom_cards = [replace(smithy, name=f"Card {i}") for i in range(10)]
    ally_and_prophecy = get_cards(db, "Architects' Guild", "Approaching Army")
    _kingdom, landscapes, _unused = _draw_kingdom(
        CardDatabase([*kingdom_cards, *ally_and_prophecy]),
        sets_editions=None,
        max_landscapes=2,
    )
    assert landscapes == []


def test_draw_kingdom_needs_ten_kingdom_cards(db: CardDatabase, smithy: Card) -> None:
    kingdom_cards = [replace(smithy, name=f"Card {i}") for i in range(9)]
    events = get_cards(db, "Alms", "Ball")  # Landscapes do not count
    with pytest.raises(SetupGenerationError, match="need 10, found 9"):
        _draw_kingdom(
            CardDatabase([*kingdom_cards, *events]),
            sets_editions=None,
            max_landscapes=2,
        )


# ── 2. Extra Kingdom piles & Prophecy ────────────────────────────────────────

ExtraPiles = tuple[list[tuple[str, str]], str | None]


@pytest.fixture
def choose_extra_piles(db: CardDatabase) -> Callable[..., ExtraPiles]:
    """Return ``_choose_extra_piles`` taking and returning card names.

    Extra piles are returned as ``(mark, card name)`` pairs in the order they
    were chosen, along with the Prophecy. Approaching Army is the only Prophecy
    on offer, so any Omen deals it.
    """
    prophecies = CardDatabase(get_cards(db, "Approaching Army"))

    def _choose_extra_piles_by_name(
        kingdom: Sequence[str],
        landscapes: Sequence[str] = (),
        unused: Sequence[str] = (),
    ) -> ExtraPiles:
        extra_piles, prophecy = _choose_extra_piles(
            prophecies,
            get_cards(db, *kingdom),
            get_cards(db, *landscapes),
            get_cards(db, *unused),
        )
        return (
            [(str(rule.mark), card.name) for rule, card in extra_piles],
            None if prophecy is None else prophecy.name,
        )

    return _choose_extra_piles_by_name


def test_no_extra_piles_without_triggers(
    choose_extra_piles: Callable[..., ExtraPiles],
) -> None:
    assert choose_extra_piles(["Village", "Smithy"], unused=["Hamlet"]) == ([], None)


@pytest.mark.parametrize(
    ("kingdom", "landscapes", "unused", "extra_pile"),
    [
        pytest.param(
            ["Young Witch"],
            [],
            ["Familiar", "Smithy", "Hamlet"],
            ("Bane", "Hamlet"),
            id="Young Witch: $2-$3",
        ),
        pytest.param(
            ["Ferryman"],
            [],
            ["Hamlet", "Market", "Smithy"],
            ("Ferryman", "Smithy"),
            id="Ferryman: $3-$4",
        ),
        pytest.param(
            [],
            ["Way of the Mouse"],
            ["Lighthouse", "Ducat", "Hamlet"],
            ("Way of the Mouse", "Hamlet"),
            id="Way of the Mouse: non-Duration Action $2-$3",
        ),
        pytest.param(
            ["Riverboat"],
            [],
            ["Wharf", "Duke", "Market"],
            ("Riverboat", "Market"),
            id="Riverboat: non-Duration Action $5",
        ),
        pytest.param(
            ["Kitsune"],
            [],
            ["Smithy", "Militia"],
            ("Approaching Army", "Militia"),
            id="Approaching Army: Attack",
        ),
    ],
)
def test_extra_pile_is_the_first_eligible_unused_card(
    choose_extra_piles: Callable[..., ExtraPiles],
    kingdom: list[str],
    landscapes: list[str],
    unused: list[str],
    extra_pile: tuple[str, str],
) -> None:
    extra_piles, _prophecy = choose_extra_piles(kingdom, landscapes, unused)
    assert extra_piles == [extra_pile]


@pytest.mark.parametrize(
    ("kingdom", "landscapes", "unused", "message"),
    [
        (["Young Witch"], [], ["Smithy"], "No eligible Bane card"),
        (["Ferryman"], [], ["Hamlet"], "No eligible Ferryman card"),
        ([], ["Way of the Mouse"], ["Lighthouse"], "No eligible Way of the Mouse card"),
        (["Riverboat"], [], ["Wharf"], "No eligible Riverboat card"),
        (["Kitsune"], [], ["Smithy"], "No eligible Approaching Army card"),
    ],
)
def test_extra_pile_without_an_eligible_card_raises(
    choose_extra_piles: Callable[..., ExtraPiles],
    kingdom: list[str],
    landscapes: list[str],
    unused: list[str],
    message: str,
) -> None:
    with pytest.raises(SetupGenerationError, match=message):
        choose_extra_piles(kingdom, landscapes, unused)


def test_each_extra_pile_is_a_different_card(
    choose_extra_piles: Callable[..., ExtraPiles],
) -> None:
    extra_piles, _prophecy = choose_extra_piles(
        ["Young Witch"], ["Way of the Mouse"], unused=["Hamlet", "Village"]
    )
    assert extra_piles == [("Bane", "Hamlet"), ("Way of the Mouse", "Village")]


@pytest.mark.parametrize(
    ("kingdom", "unused", "expected"),
    [
        pytest.param(
            ["Ferryman"],
            ["Young Witch", "Hamlet"],
            ([("Ferryman", "Young Witch"), ("Bane", "Hamlet")], None),
            id="Ferryman sets aside Young Witch, who needs a Bane",
        ),
        pytest.param(
            ["Riverboat"],
            ["Ferryman", "Smithy"],
            ([("Riverboat", "Ferryman"), ("Ferryman", "Smithy")], None),
            id="Riverboat sets aside Ferryman, who needs a Ferryman pile",
        ),
        pytest.param(
            ["Kitsune"],
            ["Young Witch", "Hamlet"],
            (
                [("Approaching Army", "Young Witch"), ("Bane", "Hamlet")],
                "Approaching Army",
            ),
            id="Approaching Army adds Young Witch, who needs a Bane",
        ),
        pytest.param(
            ["Ferryman"],
            ["Poet", "Militia"],
            (
                [("Ferryman", "Poet"), ("Approaching Army", "Militia")],
                "Approaching Army",
            ),
            id="Ferryman sets aside an Omen, which needs a Prophecy",
        ),
    ],
)
def test_extra_pile_can_trigger_further_extra_piles(
    choose_extra_piles: Callable[..., ExtraPiles],
    kingdom: list[str],
    unused: list[str],
    expected: ExtraPiles,
) -> None:
    assert choose_extra_piles(kingdom, unused=unused) == expected


def test_omens_deal_one_prophecy(db: CardDatabase) -> None:
    _extra_piles, prophecy = _choose_extra_piles(
        db, get_cards(db, "Kitsune", "Poet"), [], get_cards(db, "Militia")
    )
    assert prophecy is not None
    assert CardType.PROPHECY in prophecy.types


# ── 3. Cards dealt out for specific cards in use ─────────────────────────────


def test_druid_deals_three_boons(db: CardDatabase) -> None:
    boons = _choose_druid_boons(db, get_cards(db, "Druid"))
    assert len(set(card_names(boons))) == 3
    for boon in boons:
        assert CardType.BOON in boon.types


def test_no_boons_dealt_without_druid(db: CardDatabase) -> None:
    assert _choose_druid_boons(db, get_cards(db, "Bard")) == []


def test_liaison_deals_an_ally(db: CardDatabase) -> None:
    ally = _choose_ally(db, get_cards(db, "Sycophant"))
    assert ally is not None
    assert CardType.ALLY in ally.types


def test_no_ally_dealt_without_liaison(db: CardDatabase) -> None:
    assert _choose_ally(db, get_cards(db, "Village")) is None


def test_each_trait_marks_a_different_action_or_treasure_pile(
    db: CardDatabase,
) -> None:
    trait_marks = _choose_trait_piles(
        get_cards(db, "Village", "Ducat", "Duke"), get_cards(db, "Cheap", "Cursed")
    )
    assert sorted(card.name for card, _mark in trait_marks) == ["Ducat", "Village"]
    assert sorted(str(mark) for _card, mark in trait_marks) == [
        "Cheap (Trait)",
        "Cursed (Trait)",
    ]


def test_no_trait_piles_without_traits(db: CardDatabase) -> None:
    assert _choose_trait_piles(get_cards(db, "Village"), get_cards(db, "Alms")) == []


def test_traits_without_enough_action_or_treasure_piles_raise(
    db: CardDatabase,
) -> None:
    with pytest.raises(SetupGenerationError, match="Not enough Action/Treasure"):
        _choose_trait_piles(
            get_cards(db, "Village", "Duke"), get_cards(db, "Cheap", "Cursed")
        )


# ── 4. Non-Supply piles ──────────────────────────────────────────────────────

COMPANION_CARDS: dict[str, list[str]] = {
    # by name
    "Hermit": ["Madman"],
    "Urchin": ["Mercenary"],
    "Bandit Camp": ["Spoils"],
    "Marauder": ["Spoils"],
    "Pillage": ["Spoils"],
    "Page": ["Treasure Hunter", "Warrior", "Hero", "Champion"],
    "Peasant": ["Soldier", "Fugitive", "Disciple", "Teacher"],
    "Necromancer": ["Zombie Apprentice", "Zombie Mason", "Zombie Spy"],
    "Secret Cave": ["Wish"],
    "Devil's Workshop": ["Imp"],
    "Cemetery": ["Ghost"],
    "Exorcist": ["Will-o'-Wisp", "Imp", "Ghost"],
    "Flag Bearer": ["Flag"],
    "Border Guard": ["Horn", "Lantern"],
    "Treasurer": ["Key"],
    "Swashbuckler": ["Treasure Chest"],
    # by type (Fate, Doom), and maybe also by name
    "Bard": ["Boons", "Will-o'-Wisp"],
    "Fool": ["Boons", "Will-o'-Wisp", "Lost in the Woods"],
    "Leprechaun": ["Hexes", "Deluded", "Miserable", "Wish"],
    "Tormentor": ["Hexes", "Deluded", "Miserable", "Imp"],
    "Vampire": ["Hexes", "Deluded", "Miserable", "Bat"],
    # Prizes and Rewards, sorted by name
    "Tournament": ["Bag of Gold", "Diadem", "Followers", "Princess", "Trusty Steed"],
    "Joust": ["Coronet", "Courser", "Demesne", "Housecarl", "Huge Turnip", "Renown"],
    # by instructions: gaining Loot or Horses
    "Cutthroat": ["Loot"],
    "Groom": ["Horse"],
}


@pytest.mark.parametrize(
    ("card", "companions"), COMPANION_CARDS.items(), ids=COMPANION_CARDS
)
def test_companion_cards_of_a_card_in_use(
    db: CardDatabase, card: str, companions: list[str]
) -> None:
    assert card_names(_companion_cards(db, get_cards(db, card), [])) == companions


@pytest.mark.parametrize(
    ("landscape", "companions"),
    [("Looting", ["Loot"]), ("Cursed", ["Loot"]), ("Ride", ["Horse"])],
)
def test_companion_cards_of_a_landscape(
    db: CardDatabase, landscape: str, companions: list[str]
) -> None:
    assert card_names(_companion_cards(db, [], get_cards(db, landscape))) == companions


def test_no_companion_cards_without_triggers(db: CardDatabase) -> None:
    companions = _companion_cards(
        db, get_cards(db, "Village", "Smithy"), get_cards(db, "Alms")
    )
    assert companions == []


def test_shared_companion_card_is_set_out_once(db: CardDatabase) -> None:
    companions = _companion_cards(db, get_cards(db, "Devil's Workshop", "Exorcist"), [])
    assert card_names(companions) == ["Imp", "Will-o'-Wisp", "Ghost"]


# ── 5. Basic Supply piles & Heirlooms ────────────────────────────────────────


def basic_card_names(
    db: CardDatabase,
    kingdom: Sequence[str],
    *,
    other_cards_in_use: Sequence[str] = (),
    use_colony: bool | None = None,
    use_shelters: bool | None = None,
) -> list[str]:
    """Return the names ``_basic_cards`` picks for the Kingdom cards named *kingdom*."""
    kingdom_cards = get_cards(db, *kingdom)
    cards_in_use = [*kingdom_cards, *get_cards(db, *other_cards_in_use)]
    basic_cards = _basic_cards(
        db,
        kingdom_cards,
        cards_in_use,
        use_colony=use_colony,
        use_shelters=use_shelters,
    )
    return card_names(basic_cards)


def test_basic_cards_are_the_seven_defaults(db: CardDatabase) -> None:
    assert basic_card_names(db, ["Village", "Smithy"]) == BASIC_SUPPLY


@pytest.mark.parametrize(
    ("card", "pile"), [("Familiar", "Potion"), ("Marauder", "Ruins")]
)
def test_card_in_use_adds_a_basic_pile(db: CardDatabase, card: str, pile: str) -> None:
    basic_names = basic_card_names(db, ["Village"], other_cards_in_use=[card])
    assert basic_names == [*BASIC_SUPPLY, pile]


def test_basic_cards_add_optional_piles_in_a_fixed_order(db: CardDatabase) -> None:
    basic_names = basic_card_names(
        db, ["Familiar", "Marauder"], use_colony=True, use_shelters=True
    )
    assert basic_names == [
        *BASIC_SUPPLY,
        "Colony",
        "Platinum",
        "Potion",
        "Ruins",
        "Shelters",
    ]


@pytest.mark.parametrize(
    ("use_colony", "kingdom", "has_colony"),
    [
        pytest.param(True, ["Village"], True, id="forced on"),
        pytest.param(False, ["Bank", "Bishop"], False, id="forced off"),
        pytest.param(None, ["Bank", "Bishop"], True, id="all Prosperity"),
        pytest.param(None, ["Village", "Smithy"], False, id="no Prosperity"),
    ],
)
def test_colony_and_platinum(
    db: CardDatabase,
    use_colony: bool | None,  # noqa: FBT001
    kingdom: list[str],
    has_colony: bool,  # noqa: FBT001
) -> None:
    basic_names = basic_card_names(db, kingdom, use_colony=use_colony)
    assert ("Colony" in basic_names) is has_colony
    assert ("Platinum" in basic_names) is has_colony


@pytest.mark.parametrize(
    ("use_shelters", "kingdom", "has_shelters"),
    [
        pytest.param(True, ["Village"], True, id="forced on"),
        pytest.param(False, ["Hermit", "Urchin"], False, id="forced off"),
        pytest.param(None, ["Hermit", "Urchin"], True, id="all Dark Ages"),
        pytest.param(None, ["Village", "Smithy"], False, id="no Dark Ages"),
    ],
)
def test_shelters(
    db: CardDatabase,
    use_shelters: bool | None,  # noqa: FBT001
    kingdom: list[str],
    has_shelters: bool,  # noqa: FBT001
) -> None:
    basic_names = basic_card_names(db, kingdom, use_shelters=use_shelters)
    assert ("Shelters" in basic_names) is has_shelters


@pytest.mark.parametrize(
    ("kingdom", "pile"),
    [(["Bank", "Village"], "Colony"), (["Hermit", "Village"], "Shelters")],
)
def test_some_cards_from_the_set_make_the_pile_random(
    db: CardDatabase, kingdom: list[str], pile: str
) -> None:
    outcomes = {pile in basic_card_names(db, kingdom) for _ in range(20)}
    assert outcomes == {True, False}


HEIRLOOMS: dict[str, str] = {
    "Cemetery": "Haunted Mirror",
    "Fool": "Lucky Coin",
    "Pixie": "Goat",
    "Pooka": "Cursed Gold",
    "Secret Cave": "Magic Lamp",
    "Shepherd": "Pasture",
    "Tracker": "Pouch",
}


@pytest.mark.parametrize(("card", "heirloom"), HEIRLOOMS.items(), ids=HEIRLOOMS)
def test_heirloom_of_a_card_in_use(db: CardDatabase, card: str, heirloom: str) -> None:
    assert card_names(_heirlooms(db, get_cards(db, card))) == [heirloom]


def test_no_heirlooms_without_heirloom_cards(db: CardDatabase) -> None:
    assert _heirlooms(db, get_cards(db, "Village")) == []


# ── 6. Obelisk ───────────────────────────────────────────────────────────────


def test_obelisk_marks_an_action_pile(db: CardDatabase) -> None:
    obelisk_marks = _choose_obelisk_pile(
        get_cards(db, "Duke", "Village"), get_cards(db, "Obelisk")
    )
    assert [(card.name, str(mark)) for card, mark in obelisk_marks] == [
        ("Village", "Obelisk")
    ]


def test_no_obelisk_pile_without_obelisk(db: CardDatabase) -> None:
    assert _choose_obelisk_pile(get_cards(db, "Village"), get_cards(db, "Arena")) == []


def test_obelisk_without_an_action_pile_raises(db: CardDatabase) -> None:
    with pytest.raises(SetupGenerationError, match="available for Obelisk"):
        _choose_obelisk_pile(get_cards(db, "Duke", "Gardens"), get_cards(db, "Obelisk"))


# ── 7. Materials ─────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("card", "materials"),
    [
        # mats and tokens named in the instructions
        ("Island", {Material.ISLAND_MAT}),
        ("Native Village", {Material.NATIVE_VILLAGE_MAT}),
        ("Pirate Ship", {Material.PIRATE_SHIP_MAT, Material.COIN_TOKENS}),
        ("Trade Route", {Material.TRADE_ROUTE_MAT, Material.COIN_TOKENS}),
        ("Coin of the Realm", {Material.TAVERN_MAT}),
        ("Giant", {Material.JOURNEY_TOKEN}),
        ("Ranger", {Material.JOURNEY_TOKEN}),
        ("Pilgrimage", {Material.JOURNEY_TOKEN}),
        ("Relic", {Material.MINUS_ONE_CARD_TOKEN}),
        ("Raid", {Material.MINUS_ONE_CARD_TOKEN}),
        ("Inheritance", {Material.ESTATE_TOKEN}),
        ("Lost Arts", {Material.PLUS_ONE_ACTION_TOKEN}),
        ("Seaway", {Material.PLUS_ONE_BUY_TOKEN}),
        ("Plan", {Material.TRASHING_TOKEN}),
        ("Ball", {Material.MINUS_ONE_COIN_TOKEN}),
        ("Bridge Troll", {Material.MINUS_ONE_COIN_TOKEN}),
        ("Embargo", {Material.EMBARGO_TOKENS}),
        # Coffers and Villagers
        ("Baker", {Material.COFFERS_MAT, Material.COIN_TOKENS}),
        ("Ducat", {Material.COFFERS_MAT, Material.COIN_TOKENS}),
        ("Acting Troupe", {Material.COFFERS_VILLAGERS_MAT, Material.COIN_TOKENS}),
        # Exile
        ("Bounty Hunter", {Material.EXILE_MAT}),
        ("Stockpile", {Material.EXILE_MAT}),
        # Favors, for Liaisons
        ("Sycophant", {Material.FAVORS_MAT, Material.COIN_TOKENS}),
        # Victory tokens: Gatherings, "+N VP" and Landmarks that start with VP
        ("Farmers' Market", {Material.VICTORY_TOKENS}),
        ("Wild Hunt", {Material.VICTORY_TOKENS}),
        ("Monument", {Material.VICTORY_TOKENS}),
        ("Arena", {Material.VICTORY_TOKENS}),
        # Debt: a Debt cost, or Debt in the instructions
        ("Engineer", {Material.DEBT_TOKENS}),
        ("Donate", {Material.DEBT_TOKENS}),
        ("Capital", {Material.DEBT_TOKENS}),
        # Projects and Omens
        (
            "Academy",
            {
                Material.WOODEN_CUBES,
                Material.COFFERS_VILLAGERS_MAT,
                Material.COIN_TOKENS,
            },
        ),
        ("Kitsune", {Material.SUN_TOKENS}),
        # nothing
        ("Smithy", set()),
    ],
)
def test_materials_of_a_card(
    db: CardDatabase, card: str, materials: set[Material]
) -> None:
    assert _materials(get_cards(db, card)) == materials


@pytest.mark.parametrize(
    ("instructions", "materials"),
    [
        (["+2 Villagers"], {Material.COFFERS_VILLAGERS_MAT, Material.COIN_TOKENS}),
        (["+1 Villager"], {Material.COFFERS_VILLAGERS_MAT, Material.COIN_TOKENS}),
        (["Take a Coin token."], {Material.COIN_TOKENS}),
        (["Place a -$1 token on a Supply pile."], {Material.MINUS_ONE_COIN_TOKEN}),
        pytest.param(
            ["+1 Coffers", "+1 Villager"],
            {Material.COFFERS_VILLAGERS_MAT, Material.COIN_TOKENS},
            id="Coffers / Villagers mat replaces the Coffers mat",
        ),
    ],
)
def test_materials_from_instructions(
    smithy: Card, instructions: list[str], materials: set[Material]
) -> None:
    cards = [replace(smithy, instructions=text) for text in instructions]
    assert _materials(cards) == materials


# ── 8. Setup instructions ────────────────────────────────────────────────────


def test_setup_instruction_is_prefixed_with_the_card_name(db: CardDatabase) -> None:
    instructions = _setup_instructions(
        get_cards(db, "Baker"), [], KingdomSortOrder.COST
    )
    assert instructions == ["Baker: Each player gets +1 Coffers."]


@pytest.mark.parametrize(
    "card",
    [
        "Necromancer",
        "Druid",
        "Importer",
        # piles with several different cards
        "Castles",
        "Catapult/Rocks",
        "Encampment/Plunder",
        "Gladiator/Fortune",
        "Patrician/Emporium",
        "Settlers/Bustling Village",
        "Augurs",
        "Clashes",
        "Forts",
        "Odysseys",
        "Townsfolk",
        "Wizards",
        # basic and landscape cards
        "Shelters",
        "Obelisk",
    ],
)
def test_card_with_a_setup_instruction(db: CardDatabase, card: str) -> None:
    [instruction] = _setup_instructions(get_cards(db, card), [], KingdomSortOrder.COST)
    assert instruction.startswith(f"{card}: ")


def test_no_setup_instructions_without_setup(db: CardDatabase) -> None:
    cards = get_cards(db, "Village", "Copper", "Alms")
    assert _setup_instructions(cards, [], KingdomSortOrder.COST) == []


@pytest.mark.parametrize(
    ("sort_order", "card_order"),
    [
        (KingdomSortOrder.COST, ["Necromancer", "Baker"]),
        (KingdomSortOrder.NAME, ["Baker", "Necromancer"]),
    ],
)
def test_setup_instructions_follow_the_sort_order(
    db: CardDatabase, sort_order: KingdomSortOrder, card_order: list[str]
) -> None:
    cards = get_cards(db, "Baker", "Necromancer")
    instructions = _setup_instructions(cards, [], sort_order)
    assert [instruction.split(":")[0] for instruction in instructions] == card_order


def test_heirlooms_get_a_setup_instruction(db: CardDatabase) -> None:
    heirlooms = get_cards(db, "Haunted Mirror", "Lucky Coin")
    assert _setup_instructions([], heirlooms, KingdomSortOrder.COST) == [
        (
            "Heirlooms: Each player replaces 2 starting Coppers with Haunted Mirror, "
            "Lucky Coin. The unused Coppers go in the Copper pile."
        )
    ]
