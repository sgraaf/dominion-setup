"""Tests for ``dominion_setup.generator``.

The sections follow ``generator.py``: ``generate_game`` end to end, then how it
assembles the ``Game``, then one section per numbered setup step. The step
tests call the step's helper directly, with real cards from the database, so
every rule is checked on a known set of cards instead of on whatever a random
seed happens to draw.
"""

import os
import random
import re
import subprocess
import sys
from collections.abc import Callable, Iterable, Sequence
from dataclasses import replace
from typing import Any

import pytest

from dominion_setup import generator
from dominion_setup.generator import (
    EMPTY_BOARD,
    EXTRA_PILE_RULES,
    REQUIREMENT_RULES,
    SetupGenerationError,
    _basic_cards,
    _cards_of_type,
    _choose_ally,
    _choose_druid_boons,
    _choose_extra_piles,
    _choose_obelisk_pile,
    _choose_trait_piles,
    _companion_cards,
    _draw_kingdom,
    _heirlooms,
    _materials,
    _pile_size,
    _setup_instructions,
    generate_game,
    is_selectable,
    read_board_code,
)
from dominion_setup.models import (
    SET_EDITION_CHOICES,
    Board,
    Card,
    CardDatabase,
    CardSet,
    CardSetEdition,
    CardType,
    Game,
    KingdomRequirement,
    KingdomSortOrder,
    Material,
    Pile,
    PileMarkKind,
    SetupInstruction,
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


def pile_sizes(piles: Iterable[Pile]) -> dict[str, int | None]:
    """Map each pile's card name to its size."""
    return {pile.card.name: pile.size for pile in piles}


# ── generate_game ────────────────────────────────────────────────────────────


def test_generates_ten_distinct_kingdom_piles(db: CardDatabase) -> None:
    game = generate_game(
        db,
        sets_editions={(CardSet.BASE, CardSetEdition.SECOND_EDITION)},
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
    db: CardDatabase,
    sets_editions: set[tuple[CardSet, CardSetEdition]],
) -> None:
    game = generate_game(db, sets_editions=sets_editions)
    for card in [*game.kingdom_cards, *game.landscapes]:
        assert {(card.set, edition) for edition in card.editions} & sets_editions


@pytest.mark.parametrize("sort_order", KingdomSortOrder)
def test_sorts_kingdom_piles_and_landscapes(
    db: CardDatabase,
    sort_order: KingdomSortOrder,
    rng: random.Random,
) -> None:
    game = generate_game(db, sort_order=sort_order, max_landscapes=10, rng=rng)
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


def test_includes_and_excludes_cards(db: CardDatabase, rng: random.Random) -> None:
    game = generate_game(
        db,
        sets_editions={(CardSet.BASE, CardSetEdition.SECOND_EDITION)},
        include=["Witch"],
        exclude=["Moat"],
        rng=rng,
    )
    assert "Witch" in card_names(game.kingdom_cards)
    assert "Moat" not in card_names(game.kingdom_cards)


@pytest.fixture
def draw_kingdom_calls(monkeypatch: pytest.MonkeyPatch) -> list[dict[str, Any]]:
    """The keyword arguments of each call to ``_draw_kingdom``, which still draws."""
    calls: list[dict[str, Any]] = []

    def _spy(
        *args: Any,  # noqa: ANN401
        **kwargs: Any,  # noqa: ANN401
    ) -> tuple[list[Card], list[Card], list[Card]]:
        calls.append(kwargs)
        return _draw_kingdom(*args, **kwargs)

    monkeypatch.setattr(generator, "_draw_kingdom", _spy)
    return calls


def promo_names(db: CardDatabase) -> set[str]:
    """Return the names of the Promo Kingdom cards and Landscapes in *db*."""
    return {
        card.name
        for card in (*db.kingdom_cards.values(), *db.landscape_cards.values())
        if card.set == CardSet.PROMO
    }


def test_draws_from_the_given_promos_only(
    db: CardDatabase,
    rng: random.Random,
    draw_kingdom_calls: list[dict[str, Any]],
) -> None:
    sets_editions: set[tuple[CardSet, CardSetEdition]] = {BASE_2E}
    generate_game(
        db,
        sets_editions=sets_editions,
        promos=["Stash", "Summon"],
        rng=rng,
    )
    (kwargs,) = draw_kingdom_calls
    assert kwargs["sets_editions"] == {
        BASE_2E,
        (CardSet.PROMO, CardSetEdition.FIRST_EDITION),
    }
    assert sets_editions == {BASE_2E}  # not changed
    other_promos = promo_names(db) - {"Stash", "Summon"}
    assert "Walled Village" in other_promos
    assert set(kwargs["exclude"]) == other_promos


def test_includes_a_promo_that_is_not_given(
    db: CardDatabase,
    rng: random.Random,
    draw_kingdom_calls: list[dict[str, Any]],
) -> None:
    game = generate_game(
        db,
        sets_editions={BASE_2E},
        promos=["Stash"],
        include=["Envoy"],
        exclude=["Moat"],
        rng=rng,
    )
    assert "Envoy" in card_names(game.kingdom_cards)
    (kwargs,) = draw_kingdom_calls
    assert "Envoy" not in kwargs["exclude"]
    assert "Moat" in kwargs["exclude"]


def test_promos_with_every_set_draws_from_the_given_promos_only(
    db: CardDatabase,
    rng: random.Random,
    draw_kingdom_calls: list[dict[str, Any]],
) -> None:
    generate_game(db, promos=["Stash"], rng=rng)
    (kwargs,) = draw_kingdom_calls
    assert kwargs["sets_editions"] is None
    assert set(kwargs["exclude"]) == promo_names(db) - {"Stash"}


def test_promos_with_the_whole_promo_set_excludes_nothing(
    db: CardDatabase,
    rng: random.Random,
    draw_kingdom_calls: list[dict[str, Any]],
) -> None:
    sets_editions: set[tuple[CardSet, CardSetEdition]] = {
        (CardSet.PROMO, CardSetEdition.FIRST_EDITION),
    }
    generate_game(db, sets_editions=sets_editions, promos=["Stash"], rng=rng)
    (kwargs,) = draw_kingdom_calls
    assert kwargs["sets_editions"] == sets_editions
    assert list(kwargs["exclude"]) == []


@pytest.mark.parametrize("name", ["Smithy", "Smithee"])
def test_promo_that_is_not_a_promo_raises(db: CardDatabase, name: str) -> None:
    with pytest.raises(SetupGenerationError, match=f"{name!r} is not a Promo card"):
        generate_game(db, sets_editions={BASE_2E}, promos=[name])


@pytest.mark.parametrize("seed", range(10))
def test_including_a_whole_kingdom_sets_up_that_kingdom(
    db: CardDatabase,
    seed: int,
) -> None:
    """Including 10 Kingdom cards skips the draw (step 1) but runs steps 2-8.

    This is how to set up a given Kingdom: the extra piles and the Black Market
    deck come from the selected sets, and no other Landscapes are drawn.
    """
    kingdom = [
        "Young Witch",
        "Black Market",
        # the $4 cards of Base 2E, so the Bane ($2-$3) is not one of them
        "Bureaucrat",
        "Gardens",
        "Militia",
        "Moneylender",
        "Poacher",
        "Remodel",
        "Smithy",
        "Throne Room",
    ]
    game = generate_game(
        db,
        sets_editions={BASE_2E},
        include=[*kingdom, "Obelisk"],
        black_market_size=5,
        rng=random.Random(seed),
    )

    marks = pile_marks(game.kingdom_piles)
    [bane] = [name for name, card_marks in marks.items() if "Bane" in card_marks]
    assert sorted(marks) == sorted([*kingdom, bane])
    assert card_names(game.landscapes) == ["Obelisk"]
    assert any("Obelisk" in card_marks for card_marks in marks.values())
    assert len(game.black_market_deck) == 5
    base_cards = set(card_names(db.get_cards_by_set_edition(*BASE_2E)))
    assert {bane, *card_names(game.black_market_deck)} <= base_cards - set(kingdom)
    assert "Black Market" in [
        instruction.label for instruction in game.setup_instructions
    ]


# a Kingdom of Base 2E cards, and Base 2E cards that are not in it
BASE_KINGDOM = [
    "Cellar",
    "Chapel",
    "Moat",
    "Village",
    "Smithy",
    "Militia",
    "Market",
    "Mine",
    "Witch",
    "Artisan",
]
NOT_IN_BASE_KINGDOM = ["Festival", "Laboratory"]


def marked_piles(game: Game) -> dict[str, list[str]]:
    """Map the Kingdom piles and the marked non-Supply piles to their marks."""
    set_aside_marks = {
        name: marks
        for name, marks in pile_marks(game.non_supply_piles).items()
        if marks
    }
    return pile_marks(game.kingdom_piles) | set_aside_marks


@pytest.mark.parametrize("seed", range(20))
def test_swap_redraws_only_the_swapped_card(db: CardDatabase, seed: int) -> None:
    """A swapped card is redrawn, and the rest of the game stays the same.

    Some of these games have fewer Landscapes than they could, so the redraw
    must not add one.
    """
    special = ["Young Witch", "Black Market", "Druid", "Sycophant", "Kitsune"]
    options: dict[str, Any] = {
        "sets_editions": {BASE_2E, (CardSet.ADVENTURES, CardSetEdition.FIRST_EDITION)},
        "include": [*special, "Cheap", "Obelisk"],
        "max_landscapes": 3,
        "black_market_size": 5,
    }
    game = generate_game(db, rng=random.Random(seed), **options)
    marks = marked_piles(game)
    # a drawn card without marks, so no Trait or Obelisk moves
    [swapped, *_] = [
        name
        for name, card_marks in marks.items()
        if not card_marks and name not in special
    ]

    swapped_game = generate_game(
        db,
        swaps=[(swapped, None)],
        rng=random.Random(seed),
        **options,
    )

    swapped_marks = marked_piles(swapped_game)
    [new_card] = set(swapped_marks) - set(marks)
    assert set(marks) - set(swapped_marks) == {swapped}
    assert swapped_marks.pop(new_card) == []
    del marks[swapped]
    assert swapped_marks == marks
    assert swapped_game.landscapes == game.landscapes
    assert swapped_game.ally == game.ally
    assert swapped_game.prophecy == game.prophecy
    assert swapped_game.druid_boons == game.druid_boons
    assert swapped_game.black_market_deck == game.black_market_deck
    assert swapped_game.basic_piles == game.basic_piles


def test_swap_puts_the_replacement_in_the_place_of_the_card(db: CardDatabase) -> None:
    game = generate_game(
        db,
        sets_editions={BASE_2E},
        include=BASE_KINGDOM,
        swaps=[("Cellar", "Festival")],
    )
    assert sorted(card_names(game.kingdom_cards)) == sorted(
        [*BASE_KINGDOM[1:], "Festival"],
    )


def test_swapped_in_card_brings_its_own_setup(db: CardDatabase) -> None:
    game = generate_game(
        db,
        sets_editions={BASE_2E},
        include=BASE_KINGDOM,
        swaps=[("Village", "Young Witch")],
    )
    marks = pile_marks(game.kingdom_piles)
    assert marks["Young Witch"] == []
    assert list(marks.values()).count(["Bane"]) == 1


def test_swap_redraws_or_replaces_a_landscape(db: CardDatabase) -> None:
    options: dict[str, Any] = {
        "sets_editions": {BASE_2E, (CardSet.ADVENTURES, CardSetEdition.FIRST_EDITION)},
        "include": [*BASE_KINGDOM, "Alms", "Ball"],
    }

    game = generate_game(db, swaps=[("Ball", None)], **options)
    assert sorted(card_names(game.kingdom_cards)) == sorted(BASE_KINGDOM)
    assert len(game.landscapes) == 2
    assert "Alms" in card_names(game.landscapes)
    assert "Ball" not in card_names(game.landscapes)

    game = generate_game(db, swaps=[("Ball", "Bonfire")], **options)
    assert card_names(game.landscapes) == ["Alms", "Bonfire"]


# the $4 cards of Base 2E, so the Bane ($2-$3) is not one of them
YOUNG_WITCH_KINGDOM = [
    "Young Witch",
    "Bureaucrat",
    "Gardens",
    "Militia",
    "Moneylender",
    "Poacher",
    "Remodel",
    "Smithy",
    "Throne Room",
    "Village",
]


def bane(game: Game) -> str:
    [name] = [
        name
        for name, marks in pile_marks(game.kingdom_piles).items()
        if "Bane" in marks
    ]
    return name


@pytest.mark.parametrize("seed", range(5))
def test_swap_redraws_the_bane(db: CardDatabase, seed: int) -> None:
    options: dict[str, Any] = {
        "sets_editions": {BASE_2E},
        "include": YOUNG_WITCH_KINGDOM,
    }
    old_bane = bane(generate_game(db, rng=random.Random(seed), **options))
    game = generate_game(
        db,
        swaps=[(old_bane, None)],
        rng=random.Random(seed),
        **options,
    )
    new_bane = db.get_card_by_name(bane(game))
    assert new_bane.name != old_bane
    assert new_bane.cost.coins in {2, 3}
    assert set(card_names(game.kingdom_cards)) == {*YOUNG_WITCH_KINGDOM, new_bane.name}


def test_swap_replaces_the_bane(db: CardDatabase) -> None:
    options: dict[str, Any] = {
        "sets_editions": {BASE_2E},
        "include": YOUNG_WITCH_KINGDOM,
    }
    old_bane = bane(generate_game(db, rng=random.Random(0), **options))
    new_bane = "Moat" if old_bane == "Cellar" else "Cellar"
    game = generate_game(
        db,
        swaps=[(old_bane, new_bane)],
        rng=random.Random(0),
        **options,
    )
    assert bane(game) == new_bane


@pytest.mark.parametrize(
    ("kingdom", "drawable", "black_market_size"),
    [
        pytest.param(YOUNG_WITCH_KINGDOM, ["Cellar", "Chapel"], 15, id="Bane"),
        pytest.param(
            ["Black Market", *BASE_KINGDOM[1:]],
            ["Festival", "Laboratory", "Library"],
            2,
            id="Black Market",
        ),
    ],
)
@pytest.mark.parametrize("seed", range(5))
def test_swap_never_draws_the_bane_or_a_black_market_card(
    db: CardDatabase,
    seed: int,
    kingdom: list[str],
    drawable: list[str],
    black_market_size: int,
) -> None:
    """With the Bane or the Black Market deck taking all but one of the cards
    left to draw, the redraw takes that one.
    """
    base_cards = card_names(db.get_cards_by_set_edition(*BASE_2E))
    options: dict[str, Any] = {
        "sets_editions": {BASE_2E},
        "include": kingdom,
        "exclude": [name for name in base_cards if name not in {*kingdom, *drawable}],
        "black_market_size": black_market_size,
    }
    game = generate_game(db, rng=random.Random(seed), **options)
    set_aside = {
        *(name for name, marks in pile_marks(game.kingdom_piles).items() if marks),
        *card_names(game.black_market_deck),
    }
    [left_over] = set(drawable) - set_aside

    swapped_game = generate_game(
        db,
        swaps=[(kingdom[-1], None)],
        rng=random.Random(seed),
        **options,
    )
    assert left_over in card_names(swapped_game.kingdom_cards)


def test_swapping_in_a_black_market_card_takes_it_out_of_the_deck(
    db: CardDatabase,
) -> None:
    options: dict[str, Any] = {
        "sets_editions": {BASE_2E},
        "include": ["Black Market", *BASE_KINGDOM[1:]],
        "black_market_size": 5,
    }
    deck = card_names(
        generate_game(db, rng=random.Random(0), **options).black_market_deck,
    )
    replacement = deck[0]
    game = generate_game(
        db,
        swaps=[("Chapel", replacement)],
        rng=random.Random(0),
        **options,
    )
    assert replacement in card_names(game.kingdom_cards)
    new_deck = card_names(game.black_market_deck)
    assert len(new_deck) == 5
    assert replacement not in new_deck
    assert set(deck[1:]) <= set(new_deck)


@pytest.mark.parametrize("seed", range(10))
def test_swapping_the_pile_of_a_trait_or_obelisk_moves_its_mark(
    db: CardDatabase,
    seed: int,
) -> None:
    options: dict[str, Any] = {
        "sets_editions": {BASE_2E},
        "include": [*BASE_KINGDOM, "Cheap", "Obelisk"],
    }
    marks = pile_marks(
        generate_game(db, rng=random.Random(seed), **options).kingdom_piles,
    )
    [cheap_pile] = [
        name for name, card_marks in marks.items() if "Cheap (Trait)" in card_marks
    ]
    [obelisk_pile] = [
        name for name, card_marks in marks.items() if "Obelisk" in card_marks
    ]

    game = generate_game(
        db,
        swaps=[(cheap_pile, None)],
        rng=random.Random(seed),
        **options,
    )
    new_marks = pile_marks(game.kingdom_piles)
    assert (
        sum(card_marks.count("Cheap (Trait)") for card_marks in new_marks.values()) == 1
    )
    assert sum(card_marks.count("Obelisk") for card_marks in new_marks.values()) == 1
    if obelisk_pile != cheap_pile:
        assert "Obelisk" in new_marks[obelisk_pile]


def test_swapped_out_card_is_not_drawn_again_but_can_be_picked_back(
    db: CardDatabase,
) -> None:
    base_cards = card_names(db.get_cards_by_set_edition(*BASE_2E))
    left_out = [name for name in base_cards if name not in BASE_KINGDOM]
    # only Festival is left to draw
    options: dict[str, Any] = {
        "sets_editions": {BASE_2E},
        "include": BASE_KINGDOM,
        "exclude": [name for name in left_out if name != "Festival"],
    }

    game = generate_game(db, swaps=[("Cellar", None)], **options)
    assert sorted(card_names(game.kingdom_cards)) == sorted(
        [*BASE_KINGDOM[1:], "Festival"],
    )

    with pytest.raises(SetupGenerationError, match="need 1, found 0"):
        generate_game(db, swaps=[("Cellar", None), ("Festival", None)], **options)

    game = generate_game(
        db,
        swaps=[("Cellar", None), ("Festival", "Cellar")],
        **options,
    )
    assert sorted(card_names(game.kingdom_cards)) == sorted(BASE_KINGDOM)


def test_same_seed_and_swaps_generate_the_same_game(db: CardDatabase) -> None:
    swaps = [("Cellar", None), ("Moat", "Festival")]
    options: dict[str, Any] = {"include": BASE_KINGDOM, "swaps": swaps}
    game = generate_game(db, rng=random.Random(42), **options)
    assert generate_game(db, rng=random.Random(42), **options) == game


@pytest.mark.parametrize(
    ("swap", "message"),
    [
        (("Copper", None), "'Copper' is not a Kingdom card or Landscape"),
        (
            ("Festival", None),
            "'Festival' is not a Kingdom card, extra pile or Landscape of the game",
        ),
        (("Cellar", "Smithee"), "Card 'Smithee' not found"),
        (("Cellar", "Moat"), "'Moat' is already in the game"),
        (("Cellar", "Bonfire"), "'Bonfire' is not a Kingdom card"),
        (("Alms", "Festival"), "'Festival' is not a Landscape"),
        (("Alms", "Alms"), "'Alms' is already in the game"),
    ],
)
def test_invalid_swap_raises(
    db: CardDatabase,
    swap: tuple[str, str | None],
    message: str,
) -> None:
    with pytest.raises(SetupGenerationError, match=re.escape(message)):
        generate_game(
            db,
            sets_editions={BASE_2E},
            include=[*BASE_KINGDOM, "Alms"],
            swaps=[swap],
        )


def test_replacement_bane_must_be_eligible(db: CardDatabase) -> None:
    options: dict[str, Any] = {
        "sets_editions": {BASE_2E},
        "include": YOUNG_WITCH_KINGDOM,
    }
    old_bane = bane(generate_game(db, rng=random.Random(0), **options))
    with pytest.raises(
        SetupGenerationError,
        match=r"'Market' is not eligible for Bane",
    ):
        generate_game(db, swaps=[(old_bane, "Market")], rng=random.Random(0), **options)


def test_replacement_must_not_be_excluded(db: CardDatabase) -> None:
    """For a Kingdom card and for an extra pile alike."""
    with pytest.raises(SetupGenerationError, match="'Festival' is excluded"):
        generate_game(
            db,
            sets_editions={BASE_2E},
            include=BASE_KINGDOM,
            exclude=["Festival"],
            swaps=[("Village", "Festival")],
        )

    options: dict[str, Any] = {
        "sets_editions": {BASE_2E},
        "include": YOUNG_WITCH_KINGDOM,
        "exclude": ["Moat"],
    }
    old_bane = bane(generate_game(db, rng=random.Random(0), **options))
    with pytest.raises(SetupGenerationError, match="'Moat' is excluded"):
        generate_game(db, swaps=[(old_bane, "Moat")], rng=random.Random(0), **options)


@pytest.mark.parametrize("seed", range(10))
def test_swap_meets_the_requirements_given_as_an_iterator(
    db: CardDatabase,
    seed: int,
) -> None:
    """The redraw for the only +Buy card must give +Buy, also if the
    *requirements* can be iterated over only once.
    """
    game = generate_game(
        db,
        sets_editions={BASE_2E},
        include=BASE_KINGDOM,  # Market is the only +Buy card
        requirements=iter([KingdomRequirement.BUYS]),
        swaps=[("Market", None)],
        rng=random.Random(seed),
    )
    assert any(
        REQUIREMENT_RULES[KingdomRequirement.BUYS](card) for card in game.kingdom_cards
    )


def test_swap_draws_from_the_given_promos_given_as_an_iterator(
    db: CardDatabase,
    rng: random.Random,
    draw_kingdom_calls: list[dict[str, Any]],
) -> None:
    generate_game(
        db,
        include=BASE_KINGDOM,
        promos=iter(["Stash"]),
        swaps=[("Cellar", None)],
        rng=rng,
    )
    other_promos = promo_names(db) - {"Stash"}
    assert len(draw_kingdom_calls) == 2
    for kwargs in draw_kingdom_calls:
        assert other_promos <= set(kwargs["exclude"])


def test_replacement_must_keep_the_requirements_met(db: CardDatabase) -> None:
    """A replacement is included like the *include*d cards, so the Kingdom must
    still meet the requirements.
    """
    options: dict[str, Any] = {
        "sets_editions": {BASE_2E},
        "include": BASE_KINGDOM,  # Market is the only +Buy card
        "requirements": [KingdomRequirement.BUYS],
    }
    game = generate_game(db, swaps=[("Market", "Festival")], **options)
    assert "Festival" in card_names(game.kingdom_cards)
    with pytest.raises(SetupGenerationError, match="requirement"):
        generate_game(db, swaps=[("Market", "Laboratory")], **options)


# options for a game that makes every kind of choice on a Board but Ferryman's,
# Way of the Mouse's and Riverboat's, with 3 Landscapes and a Black Market deck
# of 5
BOARD_OPTIONS: dict[str, Any] = {
    "sets_editions": {
        (CardSet.BASE, CardSetEdition.SECOND_EDITION),
        (CardSet.ADVENTURES, CardSetEdition.FIRST_EDITION),
    },
    "include": [
        "Young Witch",
        "Black Market",
        "Druid",
        "Sycophant",
        "Kitsune",
        "Cheap",
        "Obelisk",
        "Alms",
    ],
    "max_landscapes": 3,
    "black_market_size": 5,
}


def piles_by_mark(game: Game) -> dict[str, str]:
    """Map each mark of the game, as displayed (e.g. "Bane"), to its pile."""
    return {mark: name for name, marks in marked_piles(game).items() for mark in marks}


@pytest.mark.parametrize("seed", range(5))
def test_game_has_the_board_it_was_set_up_with(db: CardDatabase, seed: int) -> None:
    game = generate_game(db, rng=random.Random(seed), **BOARD_OPTIONS)
    board = game.board

    in_supply_extra_piles = [
        card
        for mark, card in board.extra_piles.items()
        if mark in {PileMarkKind.BANE, PileMarkKind.APPROACHING_ARMY}
    ]
    assert len(board.kingdom_cards) == 10
    assert sorted(card_names([*board.kingdom_cards, *in_supply_extra_piles])) == sorted(
        card_names(game.kingdom_cards),
    )
    assert set(board.landscapes) == set(game.landscapes)
    assert board.obelisk is not None
    assert piles_by_mark(game) == {
        **{str(mark): card.name for mark, card in board.extra_piles.items()},
        **{f"{trait.name} (Trait)": pile.name for trait, pile in board.traits.items()},
        "Obelisk": board.obelisk.name,
    }
    assert board.ally is not None
    assert board.ally == game.ally
    assert board.prophecy is not None
    assert board.prophecy == game.prophecy
    assert len(board.druid_boons) == 3
    assert list(board.druid_boons) == game.druid_boons
    assert len(board.black_market_deck) == 5
    assert set(board.black_market_deck) == set(game.black_market_deck)
    assert board.use_colony == ("Colony" in card_names(game.basic_cards))
    assert board.use_shelters == ("Shelters" in card_names(game.basic_cards))


@pytest.mark.parametrize("seed", range(10))
def test_complete_board_gives_the_same_game_for_any_seed(
    db: CardDatabase,
    seed: int,
) -> None:
    """Also from every set, with the default *max_landscapes* of 2 and
    *black_market_size* of 15: the Board keeps its 3 Landscapes and its Black
    Market deck of 5.
    """
    game = generate_game(db, rng=random.Random(seed), **BOARD_OPTIONS)
    assert generate_game(db, board=game.board, rng=random.Random(seed + 1)) == game


def test_board_fills_up_the_kingdom(db: CardDatabase, rng: random.Random) -> None:
    board = Board(kingdom_cards=tuple(get_cards(db, *BASE_KINGDOM[:9])))
    game = generate_game(
        db,
        sets_editions={BASE_2E},
        board=board,
        max_landscapes=0,
        rng=rng,
    )
    kingdom = card_names(game.board.kingdom_cards)
    assert len(kingdom) == 10
    [drawn] = set(kingdom) - set(BASE_KINGDOM[:9])
    assert drawn in card_names(db.get_cards_by_set_edition(*BASE_2E))


def test_board_draws_the_choices_it_leaves_out(
    db: CardDatabase,
    rng: random.Random,
) -> None:
    board = Board(kingdom_cards=tuple(get_cards(db, *YOUNG_WITCH_KINGDOM)))
    game = generate_game(db, sets_editions={BASE_2E}, board=board, rng=rng)
    assert game.board.extra_piles == {
        PileMarkKind.BANE: db.get_card_by_name(bane(game)),
    }
    assert game.board.use_colony is not None
    assert game.board.use_shelters is not None


def test_board_drops_the_choices_that_do_not_apply(
    db: CardDatabase,
    rng: random.Random,
) -> None:
    kingdom_cards = tuple(get_cards(db, *BASE_KINGDOM))
    board = Board(
        kingdom_cards=kingdom_cards,
        extra_piles={PileMarkKind.BANE: db.get_card_by_name("Vassal")},
        traits={db.get_card_by_name("Cheap"): db.get_card_by_name("Smithy")},
        obelisk=db.get_card_by_name("Smithy"),
        ally=db.get_card_by_name("Band of Nomads"),
        prophecy=db.get_card_by_name("Bureaucracy"),
        druid_boons=tuple(
            get_cards(db, "The Sun's Gift", "The Earth's Gift", "The Moon's Gift"),
        ),
        black_market_deck=tuple(get_cards(db, "Festival")),
        use_colony=False,
        use_shelters=False,
    )
    game = generate_game(db, board=board, rng=rng)
    assert game.board == Board(
        kingdom_cards=kingdom_cards,
        use_colony=False,
        use_shelters=False,
    )


def black_market_board(db: CardDatabase, deck_size: int) -> Board:
    """Return a Board with Black Market and a deck of *deck_size* cards."""
    kingdom = ["Black Market", *BASE_KINGDOM[1:]]
    deck = [
        card
        for card in sorted(
            db.kingdom_cards.values(),
            key=KingdomSortOrder.NAME.sort_key,
        )
        if card.name not in kingdom
    ][:deck_size]
    return Board(
        kingdom_cards=tuple(get_cards(db, *kingdom)),
        black_market_deck=tuple(deck),
    )


@pytest.mark.parametrize("deck_size", [3, 20])
def test_board_keeps_its_black_market_deck(
    db: CardDatabase,
    rng: random.Random,
    deck_size: int,
) -> None:
    """Smaller or larger than *black_market_size*."""
    board = black_market_board(db, deck_size)
    game = generate_game(db, board=board, black_market_size=15, rng=rng)
    assert game.board.black_market_deck == board.black_market_deck


def test_swapping_in_a_card_of_the_board_black_market_deck_tops_it_up(
    db: CardDatabase,
    rng: random.Random,
) -> None:
    """To the size of the Board's deck, not *black_market_size*."""
    board = black_market_board(db, 3)
    replacement, *rest = board.black_market_deck
    game = generate_game(db, board=board, swaps=[("Chapel", replacement.name)], rng=rng)
    assert replacement in game.kingdom_cards
    assert len(game.black_market_deck) == 3
    assert replacement not in game.black_market_deck
    assert set(rest) <= set(game.black_market_deck)


@pytest.mark.parametrize(
    ("on_board", "use", "expected"),
    [
        (True, False, True),
        (False, True, False),
        (None, True, True),
        (None, False, False),
    ],
)
def test_board_colony_and_shelters_win_over_use_colony_and_use_shelters(
    db: CardDatabase,
    rng: random.Random,
    on_board: bool | None,  # noqa: FBT001
    use: bool,  # noqa: FBT001
    expected: bool,  # noqa: FBT001
) -> None:
    board = Board(
        kingdom_cards=tuple(get_cards(db, *BASE_KINGDOM)),
        use_colony=on_board,
        use_shelters=on_board,
    )
    game = generate_game(db, board=board, use_colony=use, use_shelters=use, rng=rng)
    basic_names = card_names(game.basic_cards)
    assert ("Colony" in basic_names) is expected
    assert ("Shelters" in basic_names) is expected


def test_swaps_swap_cards_of_the_board(db: CardDatabase, rng: random.Random) -> None:
    board = Board(kingdom_cards=tuple(get_cards(db, *BASE_KINGDOM)))
    game = generate_game(db, board=board, swaps=[("Cellar", "Festival")], rng=rng)
    assert sorted(card_names(game.kingdom_cards)) == sorted(
        [*BASE_KINGDOM[1:], "Festival"],
    )

    # only Laboratory is left to draw
    base_cards = card_names(db.get_cards_by_set_edition(*BASE_2E))
    game = generate_game(
        db,
        sets_editions={BASE_2E},
        board=board,
        exclude=[
            name for name in base_cards if name not in {*BASE_KINGDOM, "Laboratory"}
        ],
        swaps=[("Cellar", None)],
        rng=rng,
    )
    assert sorted(card_names(game.kingdom_cards)) == sorted(
        [*BASE_KINGDOM[1:], "Laboratory"],
    )


@pytest.mark.parametrize(
    ("make_board", "message"),
    [
        pytest.param(
            lambda c: Board(kingdom_cards=tuple(map(c, [*BASE_KINGDOM, "Festival"]))),
            "11 Kingdom cards on the Board: the Kingdom has 10",
            id="11 Kingdom cards",
        ),
        pytest.param(
            lambda c: Board(kingdom_cards=(c("Smithy"), c("Smithy"))),
            "'Smithy' is on the Board twice",
            id="Kingdom card twice",
        ),
        pytest.param(
            lambda c: Board(
                kingdom_cards=(c("Young Witch"), c("Moat")),
                extra_piles={PileMarkKind.BANE: c("Moat")},
            ),
            "'Moat' is on the Board twice",
            id="Bane in the Kingdom",
        ),
        pytest.param(
            lambda c: Board(
                kingdom_cards=(c("Black Market"), c("Smithy")),
                black_market_deck=(c("Smithy"),),
            ),
            "'Smithy' is on the Board twice",
            id="Black Market card in the Kingdom",
        ),
        pytest.param(
            lambda c: Board(
                druid_boons=(
                    c("The Sun's Gift"),
                    c("The Sun's Gift"),
                    c("The Sky's Gift"),
                ),
            ),
            '"The Sun\'s Gift" is on the Board twice',
            id="Boon twice",
        ),
        pytest.param(
            lambda c: Board(kingdom_cards=(c("Alms"),)),
            "'Alms' is not a Kingdom card",
            id="Landscape in the Kingdom",
        ),
        pytest.param(
            lambda c: Board(extra_piles={PileMarkKind.BANE: c("Alms")}),
            "'Alms' is not a Kingdom card",
            id="Landscape as the Bane",
        ),
        pytest.param(
            lambda c: Board(black_market_deck=(c("Copper"),)),
            "'Copper' is not a Kingdom card",
            id="Basic card in the Black Market deck",
        ),
        pytest.param(
            lambda c: Board(traits={c("Cheap"): c("Copper")}),
            "'Copper' is not a Kingdom card",
            id="Trait on a basic pile",
        ),
        pytest.param(
            lambda c: Board(landscapes=(c("Smithy"),)),
            "'Smithy' is not a Landscape",
            id="Kingdom card as a Landscape",
        ),
        pytest.param(
            lambda c: Board(landscapes=(c("Band of Nomads"),)),
            "'Band of Nomads' is not a Landscape",
            id="Ally as a Landscape",
        ),
        pytest.param(
            lambda c: Board(traits={c("Alms"): c("Smithy")}),
            "'Alms' is not a Trait",
            id="Event as a Trait",
        ),
        pytest.param(
            lambda c: Board(ally=c("Alms")),
            "'Alms' is not an Ally",
            id="Event as the Ally",
        ),
        pytest.param(
            lambda c: Board(prophecy=c("Alms")),
            "'Alms' is not a Prophecy",
            id="Event as the Prophecy",
        ),
        pytest.param(
            lambda c: Board(
                druid_boons=(c("The Sun's Gift"), c("Alms"), c("The Sky's Gift")),
            ),
            "'Alms' is not a Boon",
            id="Event as a Boon",
        ),
        pytest.param(
            lambda c: Board(extra_piles={PileMarkKind.OBELISK: c("Smithy")}),
            "Obelisk is not an extra pile",
            id="Obelisk as an extra pile",
        ),
        pytest.param(
            lambda c: Board(extra_piles={PileMarkKind.BANE: c("Market")}),
            "'Market' is not eligible for Bane (Kingdom card costing $2-$3)",
            id="Bane not eligible",
        ),
        pytest.param(
            lambda c: Board(extra_piles={PileMarkKind.RIVERBOAT: c("Wharf")}),
            "'Wharf' is not eligible for Riverboat",
            id="Riverboat not eligible",
        ),
        pytest.param(
            lambda c: Board(traits={c("Cheap"): c("Gardens")}),
            "'Cheap' is on 'Gardens', which is not an Action or Treasure",
            id="Trait on a Victory pile",
        ),
        pytest.param(
            lambda c: Board(obelisk=c("Copper")),
            "'Copper' is not a Kingdom card",
            id="Obelisk on a basic pile",
        ),
        pytest.param(
            lambda c: Board(obelisk=c("Gardens")),
            "'Obelisk' is on 'Gardens', which is not an Action",
            id="Obelisk on a Victory pile",
        ),
        pytest.param(
            lambda c: Board(druid_boons=(c("The Sun's Gift"), c("The Sky's Gift"))),
            "Druid needs 3 Boons, not 2",
            id="2 Boons",
        ),
    ],
)
def test_invalid_board_raises(
    db: CardDatabase,
    make_board: Callable[[Callable[[str], Card]], Board],
    message: str,
) -> None:
    with pytest.raises(SetupGenerationError, match=re.escape(message)):
        generate_game(db, board=make_board(db.get_card_by_name))


def test_read_board_code(db: CardDatabase) -> None:
    code = (
        "players=4"
        "&kingdom=bridge,clerk,young-witch"
        "&landscapes=baths,cheap,way-of-the-mouse"
        "&bane=moat"
        "&ferryman=moneylender"
        "&way-of-the-mouse=village"
        "&approaching-army=militia"
        "&riverboat=laboratory"
        "&traits=cheap:bridge"
        "&obelisk=clerk"
        "&ally=architects-guild"
        "&prophecy=approaching-army"
        "&boons=the-earths-gift,the-skys-gift,the-suns-gift"
        "&black-market=catapult-rocks,smithy"
        "&colony=on"
        "&shelters=on"
    )
    card = db.get_card_by_name
    board, players = read_board_code(db, code)
    assert board == Board(
        kingdom_cards=tuple(get_cards(db, "Bridge", "Clerk", "Young Witch")),
        landscapes=tuple(get_cards(db, "Baths", "Cheap", "Way of the Mouse")),
        extra_piles={
            PileMarkKind.BANE: card("Moat"),
            PileMarkKind.FERRYMAN: card("Moneylender"),
            PileMarkKind.WAY_OF_THE_MOUSE: card("Village"),
            PileMarkKind.APPROACHING_ARMY: card("Militia"),
            PileMarkKind.RIVERBOAT: card("Laboratory"),
        },
        traits={card("Cheap"): card("Bridge")},
        obelisk=card("Clerk"),
        ally=card("Architects' Guild"),
        prophecy=card("Approaching Army"),
        druid_boons=tuple(
            get_cards(db, "The Earth's Gift", "The Sky's Gift", "The Sun's Gift"),
        ),
        black_market_deck=tuple(get_cards(db, "Catapult/Rocks", "Smithy")),
        use_colony=True,
        use_shelters=True,
    )
    assert players == 4
    assert board.to_code(players=players) == code


def test_read_board_code_reads_full_names_in_any_case(db: CardDatabase) -> None:
    """Also escaped, as in a link."""
    board, _ = read_board_code(
        db,
        "kingdom=Devil%27s+Workshop,FARMERS' MARKET,smithy&traits=Cheap:Smithy",
    )
    assert board.kingdom_cards == tuple(
        get_cards(db, "Devil's Workshop", "Farmers' Market", "Smithy"),
    )
    assert board.traits == {db.get_card_by_name("Cheap"): db.get_card_by_name("Smithy")}


def test_read_board_code_reads_old_names(db: CardDatabase) -> None:
    """So a code from before a card was renamed still reads."""
    board, _ = read_board_code(db, "kingdom=harem,smithy")
    assert board.kingdom_cards == tuple(get_cards(db, "Farm", "Smithy"))


@pytest.mark.parametrize(
    "code",
    [
        "https://example.com/dominion/?players=2&kingdom=smithy#top",
        "?players=2&kingdom=smithy",
        # unknown keys and blank cards
        "seed=42&players=2&kingdom=smithy,,+&v=2026.4.0",
    ],
)
def test_read_board_code_reads_a_link_leniently(db: CardDatabase, code: str) -> None:
    assert read_board_code(db, code) == (
        Board(
            kingdom_cards=(db.get_card_by_name("Smithy"),),
            use_colony=False,
            use_shelters=False,
        ),
        2,
    )


@pytest.mark.parametrize("code", ["", "colony=off&shelters=OFF"])
def test_read_board_code_colony_and_shelters_are_off_unless_on(
    db: CardDatabase,
    code: str,
) -> None:
    assert read_board_code(db, code) == (
        Board(use_colony=False, use_shelters=False),
        None,
    )


@pytest.mark.parametrize(
    ("code", "message"),
    [
        ("kingdom=smithy,witchcraft", "Card 'witchcraft' not found"),
        ("bane=nope", "Card 'nope' not found"),
        ("traits=cheap:nope", "Card 'nope' not found"),
        ("players=many", "'many' is not a number of players"),
        ("traits=cheap", "'cheap' is not a Trait and its pile, like 'cheap:village'"),
        ("colony=maybe", "'colony' must be 'on' or 'off', not 'maybe'"),
    ],
)
def test_read_invalid_board_code_raises(
    db: CardDatabase,
    code: str,
    message: str,
) -> None:
    with pytest.raises(SetupGenerationError, match=re.escape(message)):
        read_board_code(db, code)


def test_extra_pile_rules_match_the_extra_pile_marks() -> None:
    """Each extra pile rule has an extra-pile mark, and no other kind is one.

    ``Board.to_code`` writes only extra piles from ``extra_piles``, and
    ``read_board_code`` reads only the rules' keys, so the two must agree.
    """
    assert {rule.mark for rule in EXTRA_PILE_RULES} == {
        mark for mark in PileMarkKind if mark.is_extra_pile
    }


@pytest.mark.parametrize("seed", range(10))
def test_board_code_sets_up_the_same_game(db: CardDatabase, seed: int) -> None:
    game = generate_game(db, players=4, rng=random.Random(seed), **BOARD_OPTIONS)
    code = game.to_dict()["code"]
    board, players = read_board_code(db, code)
    assert board.to_code(players=players) == code

    game_of_code = generate_game(
        db,
        board=board,
        players=players,
        rng=random.Random(seed + 1),
    )
    # the Druid Boons are in the order of the Board
    assert set(game_of_code.druid_boons) == set(game.druid_boons)
    game_of_code = replace(game_of_code, druid_boons=game.druid_boons)
    assert game_of_code.to_dict() == game.to_dict()


def test_same_seed_generates_the_same_game(db: CardDatabase) -> None:
    game = generate_game(db, rng=random.Random(42))
    assert generate_game(db, rng=random.Random(42)) == game


def test_does_not_change_the_global_random_state(db: CardDatabase) -> None:
    state = random.getstate()
    generate_game(db)
    generate_game(db, rng=random.Random(42))
    assert random.getstate() == state


def test_same_seed_generates_the_same_game_in_every_process() -> None:
    """A given seed yields the same setup regardless of string hash randomization."""
    script = (
        "import random; from dominion_setup import generate_game, load_card_database; "
        "game = generate_game(load_card_database(), rng=random.Random(42)); "
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
    db: CardDatabase,
    monkeypatch: pytest.MonkeyPatch,
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
        black_market_size: int = 15,
        players: int | None = None,
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
        return generate_game(
            db,
            use_colony=False,
            use_shelters=False,
            black_market_size=black_market_size,
            players=players,
        )

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


def test_black_market_deck_is_sorted(generate_with: Callable[..., Game]) -> None:
    game = generate_with(
        kingdom=["Black Market"],
        unused=["Smithy", "Village", "Market"],
        black_market_size=2,
    )
    assert card_names(game.black_market_deck) == ["Village", "Smithy"]


def test_black_market_deck_brings_its_own_setup(
    generate_with: Callable[..., Game],
) -> None:
    """Cards in the Black Market deck can be bought, so they need their components."""
    game = generate_with(kingdom=["Black Market"], unused=["Tormentor", "Pooka"])
    assert card_names(game.black_market_deck) == ["Pooka", "Tormentor"]
    assert card_names(game.non_supply_cards) == ["Hexes", "Deluded", "Miserable", "Imp"]
    assert card_names(game.basic_cards) == [*BASIC_SUPPLY, "Cursed Gold"]
    assert game.setup_instructions[-1].label == "Starting decks"


def test_no_black_market_deck_without_black_market(
    generate_with: Callable[..., Game],
) -> None:
    game = generate_with(kingdom=["Village"], unused=["Smithy"])
    assert game.black_market_deck == []


def test_pile_can_carry_several_marks(generate_with: Callable[..., Game]) -> None:
    game = generate_with(kingdom=["Village"], landscapes=["Cursed", "Obelisk"])
    assert pile_marks(game.kingdom_piles) == {"Village": ["Cursed (Trait)", "Obelisk"]}


def test_heirlooms_join_the_basic_supply_in_sort_order(
    generate_with: Callable[..., Game],
) -> None:
    game = generate_with(kingdom=["Pooka", "Tracker"])
    assert card_names(game.basic_cards) == [*BASIC_SUPPLY, "Pouch", "Cursed Gold"]
    assert game.setup_instructions[-1].text.startswith(
        "Each player starts with 5 Coppers, Pouch, Cursed Gold",
    )


def test_dealt_cards_get_their_own_fields(generate_with: Callable[..., Game]) -> None:
    game = generate_with(kingdom=["Druid", "Sycophant", "Kitsune"], unused=["Militia"])
    assert len(game.druid_boons) == 3
    assert game.ally is not None
    assert game.prophecy is not None


def test_players_size_every_pile(generate_with: Callable[..., Game]) -> None:
    game = generate_with(kingdom=["Pooka", "Gardens", "Hermit"], players=2)
    assert game.players == 2
    assert pile_sizes(game.kingdom_piles) == {"Gardens": 8, "Hermit": 10, "Pooka": 10}
    assert pile_sizes(game.non_supply_piles) == {"Madman": 10}
    # each player starts with Cursed Gold instead of a Copper
    assert pile_sizes(game.basic_piles) == {
        "Copper": 48,
        "Silver": 40,
        "Gold": 30,
        "Estate": 8,
        "Duchy": 8,
        "Province": 8,
        "Curse": 10,
        "Cursed Gold": None,
    }


@pytest.mark.parametrize(
    ("kingdom", "landscapes", "unused", "size"),
    [
        pytest.param(["Ferryman"], [], ["Smithy"], 10, id="Ferryman: a whole pile"),
        pytest.param(["Riverboat"], [], ["Market"], 1, id="Riverboat: one card"),
        pytest.param(
            ["Village"],
            ["Way of the Mouse"],
            ["Hamlet"],
            1,
            id="Way of the Mouse: one card",
        ),
    ],
)
def test_set_aside_pile_size(
    generate_with: Callable[..., Game],
    kingdom: list[str],
    landscapes: list[str],
    unused: list[str],
    size: int,
) -> None:
    game = generate_with(kingdom, landscapes, unused, players=3)
    assert pile_sizes(game.non_supply_piles) == {unused[0]: size}


def test_no_pile_sizes_without_players(generate_with: Callable[..., Game]) -> None:
    game = generate_with(kingdom=["Gardens", "Hermit"])
    assert game.players is None
    piles = [*game.kingdom_piles, *game.non_supply_piles, *game.basic_piles]
    assert {pile.size for pile in piles} == {None}


@pytest.mark.parametrize("players", [0, 1, 7])
def test_players_outside_two_to_six_raise(db: CardDatabase, players: int) -> None:
    with pytest.raises(SetupGenerationError, match="2 to 6 players"):
        generate_game(db, players=players)


def test_no_dealt_cards_without_their_triggers(
    generate_with: Callable[..., Game],
) -> None:
    game = generate_with(kingdom=["Village"])
    assert game.druid_boons == []
    assert game.ally is None
    assert game.prophecy is None


# ── 1. Kingdom ───────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("name", "selectable"),
    [
        ("Village", True),  # Kingdom card
        ("Alms", True),  # Event
        ("Aqueduct", True),  # Landmark
        ("Academy", True),  # Project
        ("Way of the Mole", True),  # Way
        ("Cheap", True),  # Trait
        ("Architects' Guild", False),  # Ally
        ("Approaching Army", False),  # Prophecy
        ("Copper", False),  # basic card
        ("Spoils", False),  # non-Supply card
    ],
)
def test_is_selectable(db: CardDatabase, name: str, *, selectable: bool) -> None:
    assert is_selectable(db.get_card_by_name(name)) is selectable


def test_draw_kingdom_draws_ten_cards_and_leaves_the_rest_unused(
    db: CardDatabase,
    rng: random.Random,
) -> None:
    kingdom, _landscapes, unused = _draw_kingdom(
        db,
        sets_editions=None,
        max_landscapes=2,
        rng=rng,
    )
    assert len(kingdom) == 10
    assert sorted(card_names([*kingdom, *unused])) == sorted(db.kingdom_cards)


@pytest.mark.parametrize("max_landscapes", [0, 1, 2, 10])
def test_draw_kingdom_draws_at_most_max_landscapes(
    db: CardDatabase,
    max_landscapes: int,
    rng: random.Random,
) -> None:
    _kingdom, landscapes, _unused = _draw_kingdom(
        db,
        sets_editions=None,
        max_landscapes=max_landscapes,
        rng=rng,
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


@pytest.mark.parametrize("seed", range(10))
def test_draw_kingdom_draws_at_least_min_landscapes(
    db: CardDatabase,
    seed: int,
) -> None:
    """Landscapes are drawn on past the 10th Kingdom card, which stay unused."""
    kingdom = card_names(db.get_cards_by_set_edition(*BASE_2E))[:10]
    kingdom_cards, landscapes, unused = _draw_kingdom(
        db,
        sets_editions=None,
        max_landscapes=3,
        min_landscapes=2,
        include=[*kingdom, "Alms"],
        rng=random.Random(seed),
    )
    assert card_names(kingdom_cards) == kingdom
    assert len(landscapes) == 2
    assert landscapes[0].name == "Alms"
    assert sorted(card_names([*kingdom_cards, *unused])) == sorted(db.kingdom_cards)


@pytest.mark.parametrize("seed", range(10))
def test_min_landscapes_does_not_change_the_rest_of_the_draw(
    db: CardDatabase,
    seed: int,
) -> None:
    kingdom_cards, landscapes, unused = _draw_kingdom(
        db,
        sets_editions=None,
        max_landscapes=3,
        rng=random.Random(seed),
    )
    kingdom_cards_2, landscapes_2, unused_2 = _draw_kingdom(
        db,
        sets_editions=None,
        max_landscapes=3,
        min_landscapes=3,
        rng=random.Random(seed),
    )
    assert kingdom_cards_2 == kingdom_cards
    assert unused_2 == unused
    assert landscapes_2[: len(landscapes)] == landscapes
    assert len(landscapes_2) == 3


def test_draw_kingdom_without_min_landscapes_raises(
    db: CardDatabase,
    smithy: Card,
    rng: random.Random,
) -> None:
    kingdom_cards = [replace(smithy, name=f"Card {i}") for i in range(10)]
    with pytest.raises(SetupGenerationError, match="need 2, found 1"):
        _draw_kingdom(
            CardDatabase([*kingdom_cards, *get_cards(db, "Alms")]),
            sets_editions=None,
            max_landscapes=2,
            min_landscapes=2,
            rng=rng,
        )


def test_draw_kingdom_never_draws_allies_or_prophecies(
    db: CardDatabase,
    smithy: Card,
    rng: random.Random,
) -> None:
    kingdom_cards = [replace(smithy, name=f"Card {i}") for i in range(10)]
    ally_and_prophecy = get_cards(db, "Architects' Guild", "Approaching Army")
    _kingdom, landscapes, _unused = _draw_kingdom(
        CardDatabase([*kingdom_cards, *ally_and_prophecy]),
        sets_editions=None,
        max_landscapes=2,
        rng=rng,
    )
    assert landscapes == []


def test_draw_kingdom_needs_ten_kingdom_cards(
    db: CardDatabase,
    smithy: Card,
    rng: random.Random,
) -> None:
    kingdom_cards = [replace(smithy, name=f"Card {i}") for i in range(9)]
    events = get_cards(db, "Alms", "Ball")  # Landscapes do not count
    with pytest.raises(SetupGenerationError, match="need 10, found 9"):
        _draw_kingdom(
            CardDatabase([*kingdom_cards, *events]),
            sets_editions=None,
            max_landscapes=2,
            rng=rng,
        )


@pytest.mark.parametrize(
    ("requirement", "card", "is_provider"),
    [
        (KingdomRequirement.ACTIONS, "Village", True),
        (KingdomRequirement.ACTIONS, "Smithy", False),
        (KingdomRequirement.CARDS, "Smithy", True),
        (KingdomRequirement.CARDS, "Chapel", False),
        (KingdomRequirement.BUYS, "Market", True),
        (KingdomRequirement.BUYS, "Village", False),
        (KingdomRequirement.ATTACK, "Militia", True),
        (KingdomRequirement.ATTACK, "Moat", False),
        (KingdomRequirement.REACTION, "Moat", True),
        (KingdomRequirement.REACTION, "Militia", False),
        # trashing other cards
        (KingdomRequirement.TRASHING, "Chapel", True),
        (KingdomRequirement.TRASHING, "Remodel", True),
        (KingdomRequirement.TRASHING, "Raze", True),  # "Trash this or a card …"
        (KingdomRequirement.TRASHING, "Loan", True),  # "Discard it or trash it"
        # trashing only itself, or only other players' cards
        (KingdomRequirement.TRASHING, "Feast", False),
        (KingdomRequirement.TRASHING, "Mining Village", False),
        (KingdomRequirement.TRASHING, "Saboteur", False),
        (KingdomRequirement.TRASHING, "Rogue", False),  # "cards in the trash"
    ],
)
def test_requirement_rules(
    db: CardDatabase,
    requirement: KingdomRequirement,
    card: str,
    is_provider: bool,  # noqa: FBT001
) -> None:
    assert REQUIREMENT_RULES[requirement](db.get_card_by_name(card)) is is_provider


@pytest.mark.parametrize("seed", range(10))
@pytest.mark.parametrize(
    "requirements",
    [*([requirement] for requirement in KingdomRequirement), list(KingdomRequirement)],
    ids=[*KingdomRequirement, "all"],
)
def test_draw_kingdom_meets_the_requirements(
    db: CardDatabase,
    requirements: list[KingdomRequirement],
    seed: int,
) -> None:
    """Base 2E has a single Reaction (Moat), so requiring one often forces it in."""
    base_2e = (CardSet.BASE, CardSetEdition.SECOND_EDITION)
    kingdom, _landscapes, unused = _draw_kingdom(
        db,
        sets_editions={base_2e},
        max_landscapes=2,
        requirements=requirements,
        rng=random.Random(seed),
    )
    for requirement in requirements:
        assert any(REQUIREMENT_RULES[requirement](card) for card in kingdom)
    # cards skipped to make room are unused, not lost
    assert sorted(card_names([*kingdom, *unused])) == sorted(
        card_names(db.get_cards_by_set_edition(*base_2e)),
    )


@pytest.mark.parametrize("seed", range(20))
def test_one_card_can_meet_several_requirements(smithy: Card, seed: int) -> None:
    """Market is the only card with +Action(s), +Card(s) or +Buy(s), so it meets all three."""
    market = replace(smithy, name="Market", instructions="+1 Card\n+1 Action\n+1 Buy")
    fillers = [replace(smithy, name=f"Card {i}", instructions="+$2") for i in range(19)]
    requirements = [
        KingdomRequirement.ACTIONS,
        KingdomRequirement.CARDS,
        KingdomRequirement.BUYS,
    ]
    kingdom, _landscapes, unused = _draw_kingdom(
        CardDatabase([market, *fillers]),
        sets_editions=None,
        max_landscapes=0,
        requirements=requirements,
        rng=random.Random(seed),
    )
    assert len(kingdom) == 10
    assert "Market" in card_names(kingdom)
    assert len(unused) == 10


def test_requirement_already_met_does_not_change_the_draw(db: CardDatabase) -> None:
    draw = _draw_kingdom(db, sets_editions=None, max_landscapes=2, rng=random.Random(0))
    kingdom, _landscapes, _unused = draw
    met_requirements = [
        requirement
        for requirement, is_provider in REQUIREMENT_RULES.items()
        if any(is_provider(card) for card in kingdom)
    ]
    assert met_requirements
    draw_with_requirements = _draw_kingdom(
        db,
        sets_editions=None,
        max_landscapes=2,
        requirements=met_requirements,
        rng=random.Random(0),
    )
    assert draw_with_requirements == draw


def test_draw_kingdom_without_a_provider_raises(
    smithy: Card,
    rng: random.Random,
) -> None:
    db = CardDatabase([replace(smithy, name=f"Card {i}") for i in range(10)])
    with pytest.raises(SetupGenerationError, match="selected sets provides Attack"):
        _draw_kingdom(
            db,
            sets_editions=None,
            max_landscapes=2,
            requirements=[KingdomRequirement.ATTACK],
            rng=rng,
        )


BASE_2E = (CardSet.BASE, CardSetEdition.SECOND_EDITION)


@pytest.mark.parametrize("seed", range(10))
def test_draw_kingdom_never_draws_excluded_cards(db: CardDatabase, seed: int) -> None:
    """Base 2E has 26 Kingdom cards, so excluding 16 leaves exactly 10."""
    base_2e_cards = sorted(card_names(db.get_cards_by_set_edition(*BASE_2E)))
    kingdom, _landscapes, unused = _draw_kingdom(
        db,
        sets_editions={BASE_2E},
        max_landscapes=2,
        exclude=base_2e_cards[10:],
        rng=random.Random(seed),
    )
    assert sorted(card_names(kingdom)) == base_2e_cards[:10]
    assert unused == []


@pytest.mark.parametrize("seed", range(10))
def test_draw_kingdom_never_draws_excluded_landscapes(
    db: CardDatabase,
    seed: int,
) -> None:
    adventures = (CardSet.ADVENTURES, CardSetEdition.FIRST_EDITION)
    events = _cards_of_type(db.landscape_cards.values(), CardType.EVENT)
    adventures_events = [card.name for card in events if card.set == CardSet.ADVENTURES]
    _kingdom, landscapes, _unused = _draw_kingdom(
        db,
        sets_editions={adventures},
        max_landscapes=10,
        exclude=adventures_events,
        rng=random.Random(seed),
    )
    assert not set(card_names(landscapes)) & set(adventures_events)


@pytest.mark.parametrize("seed", range(10))
def test_draw_kingdom_includes_the_included_cards(db: CardDatabase, seed: int) -> None:
    """Included cards need not come from the selected sets."""
    included = ["Moat", "Young Witch", "Alms"]  # Young Witch and Alms are not Base
    kingdom, landscapes, unused = _draw_kingdom(
        db,
        sets_editions={BASE_2E},
        max_landscapes=1,
        include=included,
        rng=random.Random(seed),
    )
    assert len(kingdom) == 10
    assert {"Moat", "Young Witch"} <= set(card_names(kingdom))
    assert card_names(landscapes) == ["Alms"]
    assert not set(card_names(unused)) & set(included)


def test_draw_kingdom_includes_a_repeated_card_once(
    db: CardDatabase,
    rng: random.Random,
) -> None:
    kingdom, _landscapes, _unused = _draw_kingdom(
        db,
        sets_editions={BASE_2E},
        max_landscapes=2,
        include=["Village", "Village"],
        rng=rng,
    )
    assert card_names(kingdom).count("Village") == 1


def test_draw_kingdom_can_include_all_ten_cards(db: CardDatabase) -> None:
    included = sorted(card_names(db.get_cards_by_set_edition(*BASE_2E)))[:10]
    kingdom, _landscapes, _unused = _draw_kingdom(
        db,
        sets_editions={BASE_2E},
        max_landscapes=2,
        include=included,
        rng=random.Random(0),
    )
    assert sorted(card_names(kingdom)) == included


def test_included_card_meets_a_requirement(smithy: Card, rng: random.Random) -> None:
    militia = replace(smithy, name="Militia", types=(CardType.ACTION, CardType.ATTACK))
    fillers = [replace(smithy, name=f"Card {i}") for i in range(9)]
    kingdom, _landscapes, _unused = _draw_kingdom(
        CardDatabase([militia, *fillers]),
        sets_editions=None,
        max_landscapes=2,
        requirements=[KingdomRequirement.ATTACK],
        include=["Militia"],
        rng=rng,
    )
    assert "Militia" in card_names(kingdom)


def test_including_and_excluding_nothing_does_not_change_the_draw(
    db: CardDatabase,
) -> None:
    draw = _draw_kingdom(db, sets_editions=None, max_landscapes=2, rng=random.Random(0))
    assert (
        _draw_kingdom(
            db,
            sets_editions=None,
            max_landscapes=2,
            include=[],
            exclude=[],
            rng=random.Random(0),
        )
        == draw
    )


@pytest.mark.parametrize(
    ("include", "exclude", "max_landscapes", "requirements", "message"),
    [
        (["Smithee"], [], 2, [], "Card 'Smithee' not found"),
        ([], ["Smithee"], 2, [], "Card 'Smithee' not found"),
        (["Copper"], [], 2, [], "'Copper' is not a Kingdom card or Landscape"),
        ([], ["Approaching Army"], 2, [], "'Approaching Army' is not a Kingdom"),
        (["Moat"], ["Moat"], 2, [], "'Moat' is both included and excluded"),
        (
            [
                *("Artisan", "Bandit", "Bureaucrat", "Cellar", "Chapel"),
                *("Council Room", "Festival", "Gardens", "Harbinger"),
                *("Laboratory", "Library"),
            ],
            [],
            2,
            [],
            "Cannot include 11 Kingdom cards",
        ),
        (
            ["Alms", "Ball"],
            [],
            1,
            [],
            "Cannot include 2 Landscapes with at most 1",
        ),
        (
            # 9 included cards, none an Attack or Reaction, leave 1 slot for 2
            # requirements
            [
                *("Artisan", "Cellar", "Chapel", "Council Room", "Festival"),
                *("Gardens", "Harbinger", "Laboratory", "Library"),
            ],
            [],
            2,
            [KingdomRequirement.ATTACK, KingdomRequirement.REACTION],
            "1 free Kingdom slot(s) for 2 requirement(s)",
        ),
        (
            # Moat is the only Reaction in Base 2E
            [],
            ["Moat"],
            2,
            [KingdomRequirement.REACTION],
            "provides Reaction",
        ),
        (
            # 26 - 17 = 9 Kingdom cards left
            [],
            [
                *("Artisan", "Bandit", "Bureaucrat", "Cellar", "Chapel"),
                *("Council Room", "Festival", "Gardens", "Harbinger"),
                *("Laboratory", "Library", "Market", "Merchant", "Militia"),
                *("Mine", "Moat", "Moneylender"),
            ],
            2,
            [],
            "need 10, found 9",
        ),
    ],
)
def test_draw_kingdom_with_invalid_includes_or_excludes_raises(  # noqa: PLR0913, PLR0917
    db: CardDatabase,
    include: list[str],
    exclude: list[str],
    max_landscapes: int,
    requirements: list[KingdomRequirement],
    message: str,
    rng: random.Random,
) -> None:
    with pytest.raises(SetupGenerationError, match=re.escape(message)):
        _draw_kingdom(
            db,
            sets_editions={BASE_2E},
            max_landscapes=max_landscapes,
            requirements=requirements,
            include=include,
            exclude=exclude,
            rng=rng,
        )


def test_draw_kingdom_counts_the_included_cards_as_drawn(
    db: CardDatabase,
    rng: random.Random,
) -> None:
    """With 9 of Base 2E's 26 cards included and 16 excluded, 1 is left for 1 slot."""
    base_2e_cards = sorted(card_names(db.get_cards_by_set_edition(*BASE_2E)))
    kingdom, _landscapes, _unused = _draw_kingdom(
        db,
        sets_editions={BASE_2E},
        max_landscapes=2,
        include=base_2e_cards[:9],
        exclude=base_2e_cards[9:25],
        rng=rng,
    )
    assert sorted(card_names(kingdom)) == [*base_2e_cards[:9], base_2e_cards[25]]


# ── 2. Extra Kingdom piles & Prophecy ────────────────────────────────────────

ExtraPiles = tuple[list[tuple[str, str]], str | None, list[str]]


@pytest.fixture
def choose_extra_piles(
    db: CardDatabase,
    rng: random.Random,
) -> Callable[..., ExtraPiles]:
    """Return ``_choose_extra_piles`` taking and returning card names.

    Extra piles are returned as ``(mark, card name)`` pairs in the order they
    were chosen, along with the Prophecy and the Black Market deck. Approaching
    Army is the only Prophecy on offer, so any Omen deals it, unless the
    *given* choices have another.
    """
    prophecies = CardDatabase(get_cards(db, "Approaching Army"))

    def _choose_extra_piles_by_name(
        kingdom: Sequence[str],
        landscapes: Sequence[str] = (),
        unused: Sequence[str] = (),
        black_market_size: int = 15,
        given: Board = EMPTY_BOARD,
    ) -> ExtraPiles:
        extra_piles, prophecy, black_market_deck = _choose_extra_piles(
            prophecies,
            get_cards(db, *kingdom),
            get_cards(db, *landscapes),
            get_cards(db, *unused),
            black_market_size=black_market_size,
            given=given,
            rng=rng,
        )
        return (
            [(str(rule.mark), card.name) for rule, card in extra_piles],
            None if prophecy is None else prophecy.name,
            card_names(black_market_deck),
        )

    return _choose_extra_piles_by_name


def test_no_extra_piles_without_triggers(
    choose_extra_piles: Callable[..., ExtraPiles],
) -> None:
    assert choose_extra_piles(["Village", "Smithy"], unused=["Hamlet"]) == (
        [],
        None,
        [],
    )


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
    extra_piles, _prophecy, _deck = choose_extra_piles(kingdom, landscapes, unused)
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
    extra_piles, _prophecy, _deck = choose_extra_piles(
        ["Young Witch"],
        ["Way of the Mouse"],
        unused=["Hamlet", "Village"],
    )
    assert extra_piles == [("Bane", "Hamlet"), ("Way of the Mouse", "Village")]


@pytest.mark.parametrize(
    ("kingdom", "unused", "expected"),
    [
        pytest.param(
            ["Ferryman"],
            ["Young Witch", "Hamlet"],
            ([("Ferryman", "Young Witch"), ("Bane", "Hamlet")], None, []),
            id="Ferryman sets aside Young Witch, who needs a Bane",
        ),
        pytest.param(
            ["Riverboat"],
            ["Ferryman", "Smithy"],
            ([("Riverboat", "Ferryman"), ("Ferryman", "Smithy")], None, []),
            id="Riverboat sets aside Ferryman, who needs a Ferryman pile",
        ),
        pytest.param(
            ["Kitsune"],
            ["Young Witch", "Hamlet"],
            (
                [("Approaching Army", "Young Witch"), ("Bane", "Hamlet")],
                "Approaching Army",
                [],
            ),
            id="Approaching Army adds Young Witch, who needs a Bane",
        ),
        pytest.param(
            ["Ferryman"],
            ["Poet", "Militia"],
            (
                [("Ferryman", "Poet"), ("Approaching Army", "Militia")],
                "Approaching Army",
                [],
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


def test_black_market_deck_is_the_first_unused_cards(
    choose_extra_piles: Callable[..., ExtraPiles],
) -> None:
    assert choose_extra_piles(
        ["Black Market"],
        unused=["Village", "Smithy", "Hamlet"],
        black_market_size=2,
    ) == ([], None, ["Village", "Smithy"])


def test_black_market_deck_can_be_smaller_than_its_size(
    choose_extra_piles: Callable[..., ExtraPiles],
) -> None:
    assert choose_extra_piles(
        ["Black Market"],
        unused=["Village", "Smithy"],
        black_market_size=15,
    ) == ([], None, ["Village", "Smithy"])


def test_black_market_deck_and_extra_piles_are_different_cards(
    choose_extra_piles: Callable[..., ExtraPiles],
) -> None:
    assert choose_extra_piles(
        ["Young Witch", "Black Market"],
        unused=["Hamlet", "Village", "Smithy"],
        black_market_size=1,
    ) == ([("Bane", "Village")], None, ["Hamlet"])


@pytest.mark.parametrize(
    ("kingdom", "unused", "expected"),
    [
        pytest.param(
            ["Black Market"],
            ["Young Witch", "Hamlet"],
            ([("Bane", "Hamlet")], None, ["Young Witch"]),
            id="Black Market deals Young Witch, who needs a Bane",
        ),
        pytest.param(
            ["Black Market"],
            ["Poet", "Militia"],
            ([("Approaching Army", "Militia")], "Approaching Army", ["Poet"]),
            id="Black Market deals an Omen, which needs a Prophecy",
        ),
        pytest.param(
            ["Ferryman"],
            ["Black Market", "Smithy"],
            ([("Ferryman", "Black Market")], None, ["Smithy"]),
            id="Ferryman sets aside Black Market, which needs a deck",
        ),
    ],
)
def test_black_market_deck_can_trigger_further_extra_piles(
    choose_extra_piles: Callable[..., ExtraPiles],
    kingdom: list[str],
    unused: list[str],
    expected: ExtraPiles,
) -> None:
    assert choose_extra_piles(kingdom, unused=unused, black_market_size=1) == expected


def test_omens_deal_one_prophecy(db: CardDatabase, rng: random.Random) -> None:
    _extra_piles, prophecy, _deck = _choose_extra_piles(
        db,
        get_cards(db, "Kitsune", "Poet"),
        [],
        get_cards(db, "Militia"),
        black_market_size=15,
        rng=rng,
    )
    assert prophecy is not None
    assert CardType.PROPHECY in prophecy.types


def test_given_extra_piles_and_prophecy_are_used(
    db: CardDatabase,
    choose_extra_piles: Callable[..., ExtraPiles],
) -> None:
    given = Board(
        extra_piles={PileMarkKind.BANE: db.get_card_by_name("Moat")},
        prophecy=db.get_card_by_name("Bureaucracy"),
    )
    assert choose_extra_piles(
        ["Young Witch", "Ferryman", "Kitsune"],
        unused=["Hamlet", "Smithy", "Militia"],
        given=given,
    ) == ([("Bane", "Moat"), ("Ferryman", "Smithy")], "Bureaucracy", [])


def test_given_black_market_deck_is_topped_up(
    db: CardDatabase,
    choose_extra_piles: Callable[..., ExtraPiles],
) -> None:
    given = Board(black_market_deck=tuple(get_cards(db, "Market")))
    assert choose_extra_piles(
        ["Black Market"],
        unused=["Smithy", "Hamlet", "Village"],
        black_market_size=2,
        given=given,
    ) == ([], None, ["Market", "Smithy"])


def test_given_choices_without_their_triggers_are_ignored(
    db: CardDatabase,
    choose_extra_piles: Callable[..., ExtraPiles],
) -> None:
    given = Board(
        extra_piles={PileMarkKind.BANE: db.get_card_by_name("Moat")},
        black_market_deck=tuple(get_cards(db, "Market")),
        prophecy=db.get_card_by_name("Bureaucracy"),
    )
    assert choose_extra_piles(["Village"], unused=["Hamlet"], given=given) == (
        [],
        None,
        [],
    )


# ── 3. Cards dealt out for specific cards in use ─────────────────────────────


def test_druid_deals_three_boons(db: CardDatabase, rng: random.Random) -> None:
    boons = _choose_druid_boons(db, get_cards(db, "Druid"), rng=rng)
    assert len(set(card_names(boons))) == 3
    for boon in boons:
        assert CardType.BOON in boon.types


def test_no_boons_dealt_without_druid(db: CardDatabase, rng: random.Random) -> None:
    assert _choose_druid_boons(db, get_cards(db, "Bard"), rng=rng) == []


def test_liaison_deals_an_ally(db: CardDatabase, rng: random.Random) -> None:
    ally = _choose_ally(db, get_cards(db, "Sycophant"), rng=rng)
    assert ally is not None
    assert CardType.ALLY in ally.types


def test_no_ally_dealt_without_liaison(db: CardDatabase, rng: random.Random) -> None:
    assert _choose_ally(db, get_cards(db, "Village"), rng=rng) is None


def test_each_trait_marks_a_different_action_or_treasure_pile(
    db: CardDatabase,
    rng: random.Random,
) -> None:
    trait_marks = _choose_trait_piles(
        get_cards(db, "Village", "Ducat", "Duke"),
        get_cards(db, "Cheap", "Cursed"),
        rng=rng,
    )
    assert sorted(card.name for card, _mark in trait_marks) == ["Ducat", "Village"]
    assert sorted(str(mark) for _card, mark in trait_marks) == [
        "Cheap (Trait)",
        "Cursed (Trait)",
    ]


def test_given_druid_boons_and_ally_are_dealt(
    db: CardDatabase,
    rng: random.Random,
) -> None:
    boons = get_cards(db, "The Sun's Gift", "The Earth's Gift", "The Moon's Gift")
    given = Board(
        druid_boons=tuple(boons),
        ally=db.get_card_by_name("Band of Nomads"),
    )
    cards_in_use = get_cards(db, "Druid", "Sycophant")
    assert _choose_druid_boons(db, cards_in_use, given=given, rng=rng) == boons
    assert _choose_ally(db, cards_in_use, given=given, rng=rng) == given.ally


def test_trait_goes_on_its_given_pile_if_it_is_in_the_kingdom(
    db: CardDatabase,
    rng: random.Random,
) -> None:
    """A Trait whose given pile is gone goes on another pile, but not on a given one."""
    cheap, cursed = get_cards(db, "Cheap", "Cursed")
    given = Board(
        traits={
            cheap: db.get_card_by_name("Militia"),
            cursed: db.get_card_by_name("Village"),
        },
    )
    trait_marks = _choose_trait_piles(
        get_cards(db, "Village", "Smithy", "Duke"),
        [cheap, cursed],
        given=given,
        rng=rng,
    )
    assert [(card.name, str(mark)) for card, mark in trait_marks] == [
        ("Smithy", "Cheap (Trait)"),
        ("Village", "Cursed (Trait)"),
    ]


def test_no_trait_piles_without_traits(db: CardDatabase, rng: random.Random) -> None:
    assert (
        _choose_trait_piles(get_cards(db, "Village"), get_cards(db, "Alms"), rng=rng)
        == []
    )


def test_traits_without_enough_action_or_treasure_piles_raise(
    db: CardDatabase,
    rng: random.Random,
) -> None:
    with pytest.raises(SetupGenerationError, match="Not enough Action/Treasure"):
        _choose_trait_piles(
            get_cards(db, "Village", "Duke"),
            get_cards(db, "Cheap", "Cursed"),
            rng=rng,
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
    ("card", "companions"),
    COMPANION_CARDS.items(),
    ids=COMPANION_CARDS,
)
def test_companion_cards_of_a_card_in_use(
    db: CardDatabase,
    card: str,
    companions: list[str],
) -> None:
    assert card_names(_companion_cards(db, get_cards(db, card), [])) == companions


@pytest.mark.parametrize(
    ("landscape", "companions"),
    [("Looting", ["Loot"]), ("Cursed", ["Loot"]), ("Ride", ["Horse"])],
)
def test_companion_cards_of_a_landscape(
    db: CardDatabase,
    landscape: str,
    companions: list[str],
) -> None:
    assert card_names(_companion_cards(db, [], get_cards(db, landscape))) == companions


def test_no_companion_cards_without_triggers(db: CardDatabase) -> None:
    companions = _companion_cards(
        db,
        get_cards(db, "Village", "Smithy"),
        get_cards(db, "Alms"),
    )
    assert companions == []


def test_shared_companion_card_is_set_out_once(db: CardDatabase) -> None:
    companions = _companion_cards(db, get_cards(db, "Devil's Workshop", "Exorcist"), [])
    assert card_names(companions) == ["Imp", "Will-o'-Wisp", "Ghost"]


# ── 5. Basic Supply piles & Heirlooms ────────────────────────────────────────


def basic_card_names(  # noqa: PLR0913
    db: CardDatabase,
    kingdom: Sequence[str],
    *,
    other_cards_in_use: Sequence[str] = (),
    use_colony: bool | None = None,
    use_shelters: bool | None = None,
    seed: int = 0,
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
        rng=random.Random(seed),
    )
    return card_names(basic_cards)


def test_basic_cards_are_the_seven_defaults(db: CardDatabase) -> None:
    assert basic_card_names(db, ["Village", "Smithy"]) == BASIC_SUPPLY


@pytest.mark.parametrize(
    ("card", "pile"),
    [("Familiar", "Potion"), ("Marauder", "Ruins")],
)
def test_card_in_use_adds_a_basic_pile(db: CardDatabase, card: str, pile: str) -> None:
    basic_names = basic_card_names(db, ["Village"], other_cards_in_use=[card])
    assert basic_names == [*BASIC_SUPPLY, pile]


def test_basic_cards_add_optional_piles_in_a_fixed_order(db: CardDatabase) -> None:
    basic_names = basic_card_names(
        db,
        ["Familiar", "Marauder"],
        use_colony=True,
        use_shelters=True,
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
    db: CardDatabase,
    kingdom: list[str],
    pile: str,
) -> None:
    outcomes = {pile in basic_card_names(db, kingdom, seed=seed) for seed in range(20)}
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


def test_obelisk_marks_an_action_pile(db: CardDatabase, rng: random.Random) -> None:
    obelisk_marks = _choose_obelisk_pile(
        get_cards(db, "Duke", "Village"),
        get_cards(db, "Obelisk"),
        rng=rng,
    )
    assert [(card.name, str(mark)) for card, mark in obelisk_marks] == [
        ("Village", "Obelisk"),
    ]


@pytest.mark.parametrize(
    ("kingdom", "pile"),
    [(["Duke", "Village", "Smithy"], "Smithy"), (["Duke", "Village"], "Village")],
    ids=["in the Kingdom", "not in the Kingdom"],
)
def test_obelisk_goes_on_its_given_pile_if_it_is_in_the_kingdom(
    db: CardDatabase,
    rng: random.Random,
    kingdom: list[str],
    pile: str,
) -> None:
    obelisk_marks = _choose_obelisk_pile(
        get_cards(db, *kingdom),
        get_cards(db, "Obelisk"),
        given=Board(obelisk=db.get_card_by_name("Smithy")),
        rng=rng,
    )
    assert [card.name for card, _mark in obelisk_marks] == [pile]


def test_no_obelisk_pile_without_obelisk(db: CardDatabase, rng: random.Random) -> None:
    assert (
        _choose_obelisk_pile(get_cards(db, "Village"), get_cards(db, "Arena"), rng=rng)
        == []
    )


def test_obelisk_without_an_action_pile_raises(
    db: CardDatabase,
    rng: random.Random,
) -> None:
    with pytest.raises(SetupGenerationError, match="available for Obelisk"):
        _choose_obelisk_pile(
            get_cards(db, "Duke", "Gardens"),
            get_cards(db, "Obelisk"),
            rng=rng,
        )


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
    db: CardDatabase,
    card: str,
    materials: set[Material],
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
    smithy: Card,
    instructions: list[str],
    materials: set[Material],
) -> None:
    cards = [replace(smithy, instructions=text) for text in instructions]
    assert _materials(cards) == materials


# ── 8. Setup instructions ────────────────────────────────────────────────────


def test_setup_instruction_is_labelled_with_the_card_name(db: CardDatabase) -> None:
    instructions = _setup_instructions(
        get_cards(db, "Baker"),
        [],
        KingdomSortOrder.COST,
    )
    assert instructions == [SetupInstruction("Baker", "Each player gets +1 Coffers.")]


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
        # landscape cards
        "Obelisk",
    ],
)
def test_card_with_a_setup_instruction(db: CardDatabase, card: str) -> None:
    [instruction] = _setup_instructions(get_cards(db, card), [], KingdomSortOrder.COST)
    assert instruction.label == card


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
    db: CardDatabase,
    sort_order: KingdomSortOrder,
    card_order: list[str],
) -> None:
    cards = get_cards(db, "Baker", "Necromancer")
    instructions = _setup_instructions(cards, [], sort_order)
    assert [instruction.label for instruction in instructions] == card_order


@pytest.mark.parametrize(
    "card",
    ["Arena", "Basilica", "Baths", "Battlefield", "Colonnade", "Labyrinth"],
)
@pytest.mark.parametrize(("players", "vp"), [(2, 12), (3, 18), (6, 36)])
def test_players_count_out_the_vp_per_player(
    db: CardDatabase,
    card: str,
    players: int,
    vp: int,
) -> None:
    [instruction] = _setup_instructions(
        get_cards(db, card),
        [],
        KingdomSortOrder.COST,
        players=players,
    )
    assert instruction == SetupInstruction(card, f"Put {vp} VP here (6 VP per player).")


def test_vp_per_player_without_players(db: CardDatabase) -> None:
    [instruction] = _setup_instructions(
        get_cards(db, "Arena"),
        [],
        KingdomSortOrder.COST,
    )
    assert instruction == SetupInstruction("Arena", "Put 6 VP here per player.")


def test_players_count_out_the_vp_in_a_game(
    generate_with: Callable[..., Game],
) -> None:
    game = generate_with(["Village"], landscapes=["Arena"], players=4)
    assert (
        SetupInstruction("Arena", "Put 24 VP here (6 VP per player).")
        in game.setup_instructions
    )


def test_heirlooms_get_a_starting_decks_instruction(db: CardDatabase) -> None:
    heirlooms = get_cards(db, "Haunted Mirror", "Lucky Coin")
    assert _setup_instructions([], heirlooms, KingdomSortOrder.COST) == [
        SetupInstruction(
            "Starting decks",
            "Each player starts with 5 Coppers, Haunted Mirror, Lucky Coin, "
            "3 Estates. The unused Coppers go in the Copper pile.",
        ),
    ]


def test_shelters_get_a_starting_decks_instruction(db: CardDatabase) -> None:
    """Shelters' own setup, which also says when to use Shelters, is left out."""
    instructions = _setup_instructions(
        get_cards(db, "Shelters"),
        [],
        KingdomSortOrder.COST,
    )
    assert instructions == [
        SetupInstruction(
            "Starting decks",
            "Each player starts with 7 Coppers, Hovel, Necropolis, Overgrown Estate.",
        ),
    ]


def test_shelters_and_heirlooms_share_a_starting_decks_instruction(
    db: CardDatabase,
) -> None:
    instructions = _setup_instructions(
        get_cards(db, "Shelters"),
        get_cards(db, "Pouch"),
        KingdomSortOrder.COST,
    )
    assert instructions == [
        SetupInstruction(
            "Starting decks",
            "Each player starts with 6 Coppers, Pouch, Hovel, Necropolis, "
            "Overgrown Estate. The unused Coppers go in the Copper pile.",
        ),
    ]


def test_no_starting_decks_instruction_for_the_usual_starting_decks(
    db: CardDatabase,
) -> None:
    cards = get_cards(db, "Copper", "Estate")
    assert _setup_instructions(cards, [], KingdomSortOrder.COST) == []


# ── 9. Pile sizes ────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("card", "players", "size"),
    [
        # Victory piles: 8 for two players, 12 otherwise
        ("Estate", 2, 8),
        ("Estate", 6, 12),
        ("Duchy", 2, 8),
        ("Duchy", 4, 12),
        ("Colony", 2, 8),
        ("Colony", 6, 12),
        ("Gardens", 2, 8),
        ("Gardens", 3, 12),
        ("Castles", 2, 8),
        ("Castles", 4, 12),
        # ... except Provinces for five or six players
        ("Province", 2, 8),
        ("Province", 4, 12),
        ("Province", 5, 15),
        ("Province", 6, 18),
        # 10 per player after the first
        ("Curse", 2, 10),
        ("Curse", 6, 50),
        ("Ruins", 3, 20),
        # the Coppers not in starting decks
        ("Copper", 2, 46),
        ("Copper", 4, 32),
        # as many as there are cards
        ("Silver", 4, 40),
        ("Gold", 4, 30),
        ("Platinum", 4, 12),
        ("Potion", 4, 16),
        ("Smithy", 2, 10),
        ("Rats", 4, 20),
        ("Spoils", 4, 15),
        ("Lost in the Woods", 4, 1),
        # piles with several different cards
        ("Knights", 4, 10),
        ("Encampment/Plunder", 4, 10),
        ("Augurs", 4, 16),
        ("Boons", 4, 12),
        ("Hexes", 4, 12),
        ("Loot", 4, 30),
    ],
)
def test_pile_size(db: CardDatabase, card: str, players: int, size: int) -> None:
    assert (
        _pile_size(db.get_card_by_name(card), players=players, heirloom_count=0) == size
    )


def test_heirlooms_return_their_coppers_to_the_pile(db: CardDatabase) -> None:
    copper = db.get_card_by_name("Copper")
    assert _pile_size(copper, players=2, heirloom_count=1) == 48


@pytest.mark.parametrize("card", ["Shelters", "Pouch"])
def test_starting_deck_cards_have_no_pile_size(db: CardDatabase, card: str) -> None:
    assert _pile_size(db.get_card_by_name(card), players=4, heirloom_count=0) is None


def test_every_pile_has_a_size(db: CardDatabase) -> None:
    companion_names = {name for _, names in generator.COMPANION_CARDS for name in names}
    cards = [
        *db.basic_cards.values(),
        *db.kingdom_cards.values(),
        *db.non_supply_cards.values(),
        *get_cards(db, *companion_names),
    ]
    sizes = {
        card.name: _pile_size(card, players=4, heirloom_count=0)
        for card in cards
        if card.name != "Shelters" and CardType.HEIRLOOM not in card.types
    }
    assert {name: size for name, size in sizes.items() if not size} == {}
