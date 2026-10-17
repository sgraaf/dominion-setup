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
)
from dominion_setup.models import (
    SET_EDITION_CHOICES,
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
    assert any(line.startswith("Black Market: ") for line in game.setup_instructions)


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
    assert game.setup_instructions[-1].startswith("Starting decks: ")


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
    assert game.setup_instructions[-1].startswith(
        "Starting decks: Each player starts with 5 Coppers, Pouch, Cursed Gold",
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
    Army is the only Prophecy on offer, so any Omen deals it.
    """
    prophecies = CardDatabase(get_cards(db, "Approaching Army"))

    def _choose_extra_piles_by_name(
        kingdom: Sequence[str],
        landscapes: Sequence[str] = (),
        unused: Sequence[str] = (),
        black_market_size: int = 15,
    ) -> ExtraPiles:
        extra_piles, prophecy, black_market_deck = _choose_extra_piles(
            prophecies,
            get_cards(db, *kingdom),
            get_cards(db, *landscapes),
            get_cards(db, *unused),
            black_market_size=black_market_size,
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


def test_setup_instruction_is_prefixed_with_the_card_name(db: CardDatabase) -> None:
    instructions = _setup_instructions(
        get_cards(db, "Baker"),
        [],
        KingdomSortOrder.COST,
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
        # landscape cards
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
    db: CardDatabase,
    sort_order: KingdomSortOrder,
    card_order: list[str],
) -> None:
    cards = get_cards(db, "Baker", "Necromancer")
    instructions = _setup_instructions(cards, [], sort_order)
    assert [instruction.split(":")[0] for instruction in instructions] == card_order


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
    assert instruction == f"{card}: Put {vp} VP here (6 VP per player)."


def test_vp_per_player_without_players(db: CardDatabase) -> None:
    [instruction] = _setup_instructions(
        get_cards(db, "Arena"),
        [],
        KingdomSortOrder.COST,
    )
    assert instruction == "Arena: Put 6 VP here per player."


def test_players_count_out_the_vp_in_a_game(
    generate_with: Callable[..., Game],
) -> None:
    game = generate_with(["Village"], landscapes=["Arena"], players=4)
    assert "Arena: Put 24 VP here (6 VP per player)." in game.setup_instructions


def test_heirlooms_get_a_starting_decks_instruction(db: CardDatabase) -> None:
    heirlooms = get_cards(db, "Haunted Mirror", "Lucky Coin")
    assert _setup_instructions([], heirlooms, KingdomSortOrder.COST) == [
        (
            "Starting decks: Each player starts with 5 Coppers, Haunted Mirror, "
            "Lucky Coin, 3 Estates. The unused Coppers go in the Copper pile."
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
        (
            "Starting decks: Each player starts with 7 Coppers, Hovel, Necropolis, "
            "Overgrown Estate."
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
        (
            "Starting decks: Each player starts with 6 Coppers, Pouch, Hovel, "
            "Necropolis, Overgrown Estate. The unused Coppers go in the Copper pile."
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
