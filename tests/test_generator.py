import random
from collections.abc import Callable
from typing import Any

import pytest

from dominion_setup.generator import generate_game
from dominion_setup.models import (
    DEFAULT_BASIC_CARD_NAMES,
    CardDatabase,
    CardPurpose,
    CardSet,
    CardSetEdition,
    CardType,
    Game,
    KingdomSortOrder,
    Material,
    Pile,
    PileMarkKind,
)
from dominion_setup.utils import CARD_SET_ORDER

from .conftest import CardDatabaseFactory, CardFactory

BASE_2E_ONLY = {
    "Artisan",
    "Bandit",
    "Harbinger",
    "Merchant",
    "Poacher",
    "Sentry",
    "Vassal",
}
BASE_1E_ONLY = {"Adventurer", "Chancellor", "Feast", "Spy", "Thief", "Woodcutter"}
INTRIGUE_2E_ONLY = {
    "Courtier",
    "Diplomat",
    "Lurker",
    "Mill",
    "Patrol",
    "Replace",
    "Secret Passage",
}
INTRIGUE_1E_ONLY = {
    "Coppersmith",
    "Great Hall",
    "Saboteur",
    "Scout",
    "Secret Chamber",
    "Tribute",
}
SEASIDE_2E_ONLY = {
    "Astrolabe",
    "Blockade",
    "Corsair",
    "Monkey",
    "Pirate",
    "Sailor",
    "Sea Chart",
    "Sea Witch",
    "Tide Pools",
}
SEASIDE_1E_ONLY = {
    "Ambassador",
    "Embargo",
    "Explorer",
    "Ghost Ship",
    "Navigator",
    "Pearl Diver",
    "Pirate Ship",
    "Sea Hag",
}
PROSPERITY_2E_ONLY = {
    "Anvil",
    "Charlatan",
    "Clerk",
    "Collection",
    "Crystal Ball",
    "Investment",
    "Magnate",
    "Tiara",
    "War Chest",
}
PROSPERITY_1E_ONLY = {
    "Contraband",
    "Counting House",
    "Goons",
    "Loan",
    "Mountebank",
    "Royal Seal",
    "Talisman",
    "Trade Route",
    "Venture",
}
CORNUCOPIA_GUILDS_2E_ONLY = {
    "Carnival",
    "Farmhands",
    "Farrier",
    "Ferryman",
    "Footpad",
    "Infirmary",
    "Joust",
    "Shop",
}
CORNUCOPIA_GUILDS_1E_ONLY = {
    "Doctor",
    "Farming Village",
    "Fortune Teller",
    "Harvest",
    "Horse Traders",
    "Masterpiece",
    "Taxman",
    "Tournament",
}
HINTERLANDS_2E_ONLY = {
    "Berserker",
    "Cauldron",
    "Guard Dog",
    "Nomads",
    "Souk",
    "Trail",
    "Weaver",
    "Wheelwright",
    "Witch's Hut",
}
HINTERLANDS_1E_ONLY = {
    "Cache",
    "Duchess",
    "Embassy",
    "Ill-Gotten Gains",
    "Mandarin",
    "Noble Brigand",
    "Nomad Camp",
    "Oracle",
    "Silk Road",
}


def _find_seed(
    db: CardDatabase,
    sets_editions: set[tuple[CardSet, CardSetEdition]],
    predicate: Callable[[Game], bool],
    *,
    max_seeds: int = 1000,
    **generate_kwargs: Any,  # noqa: ANN401
) -> int | None:
    """Return the first seed (0-based) for which predicate(game) is True, or None."""
    for seed in range(max_seeds):
        random.seed(seed)
        game = generate_game(db, sets_editions=sets_editions, **generate_kwargs)
        if predicate(game):
            return seed
    return None


def _find_seed_with_card(
    db: CardDatabase,
    card_name: str,
    sets_editions: set[tuple[CardSet, CardSetEdition]],
    *,
    max_seeds: int = 1000,
) -> int | None:
    """Return the first seed that includes *card_name* in kingdom_piles, or None."""
    return _find_seed(
        db,
        sets_editions,
        lambda g: any(c.name == card_name for c in g.kingdom_cards),
        max_seeds=max_seeds,
        use_colony=False,
    )


def _find_seed_with_any_kingdom_card(
    db: CardDatabase,
    card_names: set[str],
    sets_editions: set[tuple[CardSet, CardSetEdition]],
    *,
    max_seeds: int = 1000,
) -> int | None:
    """Return the first seed that has any card from *card_names* in kingdom_piles, or None."""
    return _find_seed(
        db,
        sets_editions,
        lambda g: any(c.name in card_names for c in g.kingdom_cards),
        max_seeds=max_seeds,
    )


def _bane_piles(game: Game) -> list[Pile]:
    return [
        p
        for p in game.kingdom_piles
        if any(m.kind == PileMarkKind.BANE for m in p.marks)
    ]


def _ferryman_piles(game: Game) -> list[Pile]:
    return [
        p
        for p in game.non_supply_piles
        if any(m.kind == PileMarkKind.FERRYMAN for m in p.marks)
    ]


def test_generate_game_returns_game(db: CardDatabase) -> None:
    game = generate_game(db)
    assert isinstance(game, Game)


def test_exactly_10_kingdom_piles(db: CardDatabase) -> None:
    # Constrained to BASE so that Young Witch (which adds an 11th Bane pile)
    # cannot be drawn.
    game = generate_game(
        db, sets_editions={(CardSet.BASE, CardSetEdition.SECOND_EDITION)}
    )
    assert len(game.kingdom_piles) == 10
    assert len(game.kingdom_cards) == 10


def test_no_duplicate_kingdom_cards(db: CardDatabase) -> None:
    game = generate_game(db)
    names = [card.name for card in game.kingdom_cards]
    assert len(names) == len(set(names))


def test_kingdom_cards_from_allowed_sets(db: CardDatabase) -> None:
    game = generate_game(
        db, sets_editions={(CardSet.BASE, CardSetEdition.FIRST_EDITION)}
    )
    for card in game.kingdom_cards:
        assert card.set == CardSet.BASE


def test_sets_used(db: CardDatabase) -> None:
    game = generate_game(db)
    # default includes all kingdom card sets
    assert set(game.sets_used) <= {
        CardSet.BASE,
        CardSet.INTRIGUE,
        CardSet.SEASIDE,
        CardSet.ALCHEMY,
        CardSet.PROSPERITY,
        CardSet.CORNUCOPIA_GUILDS,
        CardSet.HINTERLANDS,
        CardSet.DARK_AGES,
        CardSet.ADVENTURES,
        CardSet.EMPIRES,
        CardSet.NOCTURNE,
        CardSet.RENAISSANCE,
        CardSet.MENAGERIE,
        CardSet.ALLIES,
        CardSet.PLUNDER,
        CardSet.RISING_SUN,
        CardSet.PROMO,
    }
    assert len(game.sets_used) >= 1


def test_basic_piles_has_7_piles(db: CardDatabase) -> None:
    game = generate_game(
        db, sets_editions={(CardSet.BASE, CardSetEdition.FIRST_EDITION)}
    )
    assert len(game.basic_cards) == 7


def test_kingdom_piles_sorted_by_cost_then_name(db: CardDatabase) -> None:
    game = generate_game(db)
    keys = [
        (card.cost.coins, card.cost.potion, card.name) for card in game.kingdom_cards
    ]
    assert keys == sorted(keys)


def test_dominion_1e_set_only(db: CardDatabase) -> None:
    game = generate_game(
        db, sets_editions={(CardSet.BASE, CardSetEdition.FIRST_EDITION)}
    )
    names = {card.name for card in game.kingdom_cards}
    assert not names & BASE_2E_ONLY


def test_base_2e_set_only(db: CardDatabase) -> None:
    game = generate_game(
        db, sets_editions={(CardSet.BASE, CardSetEdition.SECOND_EDITION)}
    )
    names = {card.name for card in game.kingdom_cards}
    assert not names & BASE_1E_ONLY


def test_mixed_dominion_1e_intrigue_2e(db: CardDatabase) -> None:
    game = generate_game(
        db,
        sets_editions={
            (CardSet.BASE, CardSetEdition.FIRST_EDITION),
            (CardSet.INTRIGUE, CardSetEdition.SECOND_EDITION),
        },
    )
    names = {card.name for card in game.kingdom_cards}
    assert not names & BASE_2E_ONLY
    assert not names & INTRIGUE_1E_ONLY


def test_seaside_1e_set_only(db: CardDatabase) -> None:
    game = generate_game(
        db, sets_editions={(CardSet.SEASIDE, CardSetEdition.FIRST_EDITION)}
    )
    names = {card.name for card in game.kingdom_cards}
    assert not names & SEASIDE_2E_ONLY


def test_seaside_2e_set_only(db: CardDatabase) -> None:
    game = generate_game(
        db, sets_editions={(CardSet.SEASIDE, CardSetEdition.SECOND_EDITION)}
    )
    names = {card.name for card in game.kingdom_cards}
    assert not names & SEASIDE_1E_ONLY


def test_mixed_base_2e_seaside_2e(db: CardDatabase) -> None:
    game = generate_game(
        db,
        sets_editions={
            (CardSet.BASE, CardSetEdition.SECOND_EDITION),
            (CardSet.SEASIDE, CardSetEdition.SECOND_EDITION),
        },
    )
    names = {card.name for card in game.kingdom_cards}
    assert not names & BASE_1E_ONLY
    assert not names & SEASIDE_1E_ONLY


def test_kingdom_piles_sorted_by_name(db: CardDatabase) -> None:
    game = generate_game(db, sort_order=KingdomSortOrder.NAME)
    names = [card.name for card in game.kingdom_cards]
    assert names == sorted(names)


def test_kingdom_piles_sorted_by_cost(db: CardDatabase) -> None:
    game = generate_game(db, sort_order=KingdomSortOrder.COST)
    keys = [
        (card.cost.coins, card.cost.potion, card.name) for card in game.kingdom_cards
    ]
    assert keys == sorted(keys)


def test_kingdom_piles_sorted_by_set(db: CardDatabase) -> None:
    game = generate_game(
        db,
        sort_order=KingdomSortOrder.SET,
    )
    keys = [
        (CARD_SET_ORDER[card.set], card.cost.coins, card.cost.potion, card.name)
        for card in game.kingdom_cards
    ]
    assert keys == sorted(keys)


def test_alchemy_set_only(db: CardDatabase) -> None:
    game = generate_game(
        db, sets_editions={(CardSet.ALCHEMY, CardSetEdition.FIRST_EDITION)}
    )
    assert len(game.kingdom_cards) == 10
    for card in game.kingdom_cards:
        assert card.set == CardSet.ALCHEMY


def test_potion_pile_present_when_potion_cost_cards(db: CardDatabase) -> None:
    random.seed(0)
    game = generate_game(
        db, sets_editions={(CardSet.ALCHEMY, CardSetEdition.FIRST_EDITION)}
    )
    if any(card.has_potion_cost for card in game.kingdom_cards):
        potion_piles = [card for card in game.basic_cards if card.name == "Potion"]
        assert len(potion_piles) == 1


def test_no_potion_pile_without_potion_cost_cards(db: CardDatabase) -> None:
    game = generate_game(
        db, sets_editions={(CardSet.BASE, CardSetEdition.FIRST_EDITION)}
    )
    names = {card.name for card in game.basic_cards}
    assert "Potion" not in names


def test_basic_piles_count_with_potion(db: CardDatabase) -> None:
    random.seed(0)
    game = generate_game(
        db, sets_editions={(CardSet.ALCHEMY, CardSetEdition.FIRST_EDITION)}
    )
    if any(card.has_potion_cost for card in game.kingdom_cards):
        assert len(game.basic_cards) == 8


def test_prosperity_1e_set_only(db: CardDatabase) -> None:
    game = generate_game(
        db,
        sets_editions={(CardSet.PROSPERITY, CardSetEdition.FIRST_EDITION)},
        use_colony=False,
    )
    names = {card.name for card in game.kingdom_cards}
    assert not names & PROSPERITY_2E_ONLY


def test_prosperity_2e_set_only(db: CardDatabase) -> None:
    game = generate_game(
        db,
        sets_editions={(CardSet.PROSPERITY, CardSetEdition.SECOND_EDITION)},
        use_colony=False,
    )
    names = {card.name for card in game.kingdom_cards}
    assert not names & PROSPERITY_1E_ONLY


def test_colony_forced_on(db: CardDatabase) -> None:
    game = generate_game(
        db,
        sets_editions={(CardSet.BASE, CardSetEdition.FIRST_EDITION)},
        use_colony=True,
    )
    names = {card.name for card in game.basic_cards}
    assert "Colony" in names
    assert "Platinum" in names


def test_colony_forced_off(db: CardDatabase) -> None:
    game = generate_game(
        db,
        sets_editions={(CardSet.PROSPERITY, CardSetEdition.FIRST_EDITION)},
        use_colony=False,
    )
    names = {card.name for card in game.basic_cards}
    assert "Colony" not in names
    assert "Platinum" not in names


def test_colony_never_without_prosperity(db: CardDatabase) -> None:
    game = generate_game(
        db, sets_editions={(CardSet.BASE, CardSetEdition.FIRST_EDITION)}
    )
    names = {card.name for card in game.basic_cards}
    assert "Colony" not in names
    assert "Platinum" not in names


def test_colony_always_with_all_prosperity(db: CardDatabase) -> None:
    game = generate_game(
        db, sets_editions={(CardSet.PROSPERITY, CardSetEdition.FIRST_EDITION)}
    )
    names = {card.name for card in game.basic_cards}
    assert "Colony" in names
    assert "Platinum" in names


def test_basic_piles_count_with_colony(db: CardDatabase) -> None:
    game = generate_game(
        db, sets_editions={(CardSet.PROSPERITY, CardSetEdition.FIRST_EDITION)}
    )
    # 7 standard + 2 (Colony + Platinum)
    assert len(game.basic_cards) == 9


def test_mixed_base_2e_prosperity_2e(db: CardDatabase) -> None:
    game = generate_game(
        db,
        sets_editions={
            (CardSet.BASE, CardSetEdition.SECOND_EDITION),
            (CardSet.PROSPERITY, CardSetEdition.SECOND_EDITION),
        },
        use_colony=False,
    )
    names = {card.name for card in game.kingdom_cards}
    assert not names & BASE_1E_ONLY
    assert not names & PROSPERITY_1E_ONLY


def test_generate_game_default_sets_editions(db: CardDatabase) -> None:
    game = generate_game(db)
    assert 10 <= len(game.kingdom_cards) <= 12
    for card in game.kingdom_cards:
        assert card.set in {
            CardSet.BASE,
            CardSet.INTRIGUE,
            CardSet.SEASIDE,
            CardSet.ALCHEMY,
            CardSet.PROSPERITY,
            CardSet.CORNUCOPIA_GUILDS,
            CardSet.HINTERLANDS,
            CardSet.DARK_AGES,
            CardSet.ADVENTURES,
            CardSet.EMPIRES,
            CardSet.NOCTURNE,
            CardSet.RENAISSANCE,
            CardSet.MENAGERIE,
            CardSet.ALLIES,
            CardSet.PLUNDER,
            CardSet.RISING_SUN,
            CardSet.PROMO,
        }


def test_bane_no_eligible_candidates(make_card: CardFactory) -> None:
    # All 10 cards cost $5 (no $2-$3 candidates for Bane), one is "Young Witch"
    cards = [make_card(name="Young Witch", cost_coins=5, image="Young Witch.jpg")] + [
        make_card(name=f"Card{i}", cost_coins=5, image=f"Card{i}.jpg") for i in range(9)
    ]
    db = CardDatabase(cards)
    with pytest.raises(ValueError, match="No eligible Bane card"):
        generate_game(db)


def test_ferryman_no_eligible_candidates(make_card: CardFactory) -> None:
    # All 10 cards cost $5 (no $3-$4 candidates for Ferryman), one is "Ferryman"
    cards = [make_card(name="Ferryman", cost_coins=5, image="Ferryman.jpg")] + [
        make_card(name=f"Card{i}", cost_coins=5, image=f"Card{i}.jpg") for i in range(9)
    ]
    db = CardDatabase(cards)
    with pytest.raises(ValueError, match="No eligible Ferryman card"):
        generate_game(db)


def test_generate_game_insufficient_candidates(make_card: CardFactory) -> None:
    cards = [
        make_card(
            name=f"Card{i}",
            cost_coins=i,
            editions=(CardSetEdition.FIRST_EDITION,),
            image=f"Card{i}.jpg",
            instructions="Card instructions",
        )
        for i in range(5)
    ]
    small_db = CardDatabase(cards)
    with pytest.raises(ValueError, match="Not enough kingdom cards"):
        generate_game(
            small_db, sets_editions={(CardSet.BASE, CardSetEdition.FIRST_EDITION)}
        )


def test_generate_game_deterministic_with_seed(db: CardDatabase) -> None:
    random.seed(42)
    game1 = generate_game(
        db, sets_editions={(CardSet.BASE, CardSetEdition.SECOND_EDITION)}
    )
    random.seed(42)
    game2 = generate_game(
        db, sets_editions={(CardSet.BASE, CardSetEdition.SECOND_EDITION)}
    )
    names1 = [card.name for card in game1.kingdom_cards]
    names2 = [card.name for card in game2.kingdom_cards]
    assert names1 == names2


def test_colony_mixed_prosperity_deterministic(db: CardDatabase) -> None:
    colony_results = set()
    for seed in range(100):
        random.seed(seed)
        game = generate_game(
            db,
            sets_editions={
                (CardSet.BASE, CardSetEdition.SECOND_EDITION),
                (CardSet.PROSPERITY, CardSetEdition.SECOND_EDITION),
            },
        )
        basic_names = {card.name for card in game.basic_cards}
        colony_results.add("Colony" in basic_names)
        if len(colony_results) == 2:
            break
    assert True in colony_results
    assert False in colony_results


def test_basic_piles_contain_default_names(db: CardDatabase) -> None:
    game = generate_game(
        db, sets_editions={(CardSet.BASE, CardSetEdition.SECOND_EDITION)}
    )
    basic_names = [card.name for card in game.basic_cards[:7]]
    assert basic_names == [
        "Copper",
        "Silver",
        "Gold",
        "Estate",
        "Duchy",
        "Province",
        "Curse",
    ]


def test_sets_used_reflects_selected_cards(db: CardDatabase) -> None:
    game = generate_game(
        db, sets_editions={(CardSet.INTRIGUE, CardSetEdition.SECOND_EDITION)}
    )
    assert game.sets_used == [CardSet.INTRIGUE]


def test_cornucopia_guilds_1e_set_only(db: CardDatabase) -> None:
    game = generate_game(
        db, sets_editions={(CardSet.CORNUCOPIA_GUILDS, CardSetEdition.FIRST_EDITION)}
    )
    names = {card.name for card in game.kingdom_cards}
    assert not names & CORNUCOPIA_GUILDS_2E_ONLY


def test_cornucopia_guilds_2e_set_only(db: CardDatabase) -> None:
    game = generate_game(
        db, sets_editions={(CardSet.CORNUCOPIA_GUILDS, CardSetEdition.SECOND_EDITION)}
    )
    names = {card.name for card in game.kingdom_cards}
    assert not names & CORNUCOPIA_GUILDS_1E_ONLY


def test_mixed_base_2e_cornucopia_guilds_2e(db: CardDatabase) -> None:
    game = generate_game(
        db,
        sets_editions={
            (CardSet.BASE, CardSetEdition.SECOND_EDITION),
            (CardSet.CORNUCOPIA_GUILDS, CardSetEdition.SECOND_EDITION),
        },
    )
    names = {card.name for card in game.kingdom_cards}
    assert not names & BASE_1E_ONLY
    assert not names & CORNUCOPIA_GUILDS_1E_ONLY


def test_hinterlands_1e_set_only(db: CardDatabase) -> None:
    game = generate_game(
        db, sets_editions={(CardSet.HINTERLANDS, CardSetEdition.FIRST_EDITION)}
    )
    names = {card.name for card in game.kingdom_cards}
    assert not names & HINTERLANDS_2E_ONLY


def test_hinterlands_2e_set_only(db: CardDatabase) -> None:
    game = generate_game(
        db, sets_editions={(CardSet.HINTERLANDS, CardSetEdition.SECOND_EDITION)}
    )
    names = {card.name for card in game.kingdom_cards}
    assert not names & HINTERLANDS_1E_ONLY


def test_mixed_base_2e_hinterlands_2e(db: CardDatabase) -> None:
    game = generate_game(
        db,
        sets_editions={
            (CardSet.BASE, CardSetEdition.SECOND_EDITION),
            (CardSet.HINTERLANDS, CardSetEdition.SECOND_EDITION),
        },
    )
    names = {card.name for card in game.kingdom_cards}
    assert not names & BASE_1E_ONLY
    assert not names & HINTERLANDS_1E_ONLY


def test_young_witch_triggers_bane_pile(db: CardDatabase) -> None:
    sets_editions = {(CardSet.CORNUCOPIA_GUILDS, CardSetEdition.FIRST_EDITION)}
    seed = _find_seed_with_card(db, "Young Witch", sets_editions)
    if seed is None:
        pytest.skip("no seed found with Young Witch in kingdom_piles")
    random.seed(seed)
    game = generate_game(db, sets_editions=sets_editions, use_colony=False)
    bane_piles = _bane_piles(game)
    assert len(bane_piles) == 1
    bane = bane_piles[0].card
    # Bane is the 11th kingdom pile (Young Witch + 9 others + Bane)
    assert len(game.kingdom_piles) == 11
    other_names = {p.card.name for p in game.kingdom_piles if p.card is not bane}
    assert bane.name not in other_names
    assert 2 <= bane.cost.coins <= 3
    assert bane.cost.potion is False
    assert bane.cost.debt == 0


def test_no_bane_without_young_witch(db: CardDatabase) -> None:
    game = generate_game(
        db, sets_editions={(CardSet.BASE, CardSetEdition.SECOND_EDITION)}
    )
    assert _bane_piles(game) == []


def test_bane_pile_in_sets_used(db: CardDatabase) -> None:
    sets_editions = {
        (CardSet.CORNUCOPIA_GUILDS, CardSetEdition.FIRST_EDITION),
        (CardSet.BASE, CardSetEdition.FIRST_EDITION),
    }
    seed = _find_seed_with_card(db, "Young Witch", sets_editions)
    if seed is None:
        pytest.skip("no seed found with Young Witch in kingdom_piles")
    random.seed(seed)
    game = generate_game(db, sets_editions=sets_editions, use_colony=False)
    bane_piles = _bane_piles(game)
    assert len(bane_piles) == 1
    assert bane_piles[0].card.set in game.sets_used


def test_ferryman_triggers_ferryman_pile(db: CardDatabase) -> None:
    sets_editions = {(CardSet.CORNUCOPIA_GUILDS, CardSetEdition.SECOND_EDITION)}
    seed = _find_seed_with_card(db, "Ferryman", sets_editions)
    if seed is None:
        pytest.skip("no seed found with Ferryman in kingdom_piles")
    random.seed(seed)
    game = generate_game(db, sets_editions=sets_editions, use_colony=False)
    ferryman_piles = _ferryman_piles(game)
    assert len(ferryman_piles) == 1
    ferryman = ferryman_piles[0].card
    kingdom_names = {c.name for c in game.kingdom_cards}
    assert ferryman.name not in kingdom_names
    assert 3 <= ferryman.cost.coins <= 4
    assert ferryman.cost.potion is False


def test_no_ferryman_pile_without_ferryman(db: CardDatabase) -> None:
    # Ferryman is 2E-only; generating with 1E should never produce a ferryman pile.
    game = generate_game(
        db,
        sets_editions={(CardSet.CORNUCOPIA_GUILDS, CardSetEdition.FIRST_EDITION)},
    )
    assert _ferryman_piles(game) == []


def test_tournament_triggers_prizes(db: CardDatabase) -> None:
    sets_editions = {(CardSet.CORNUCOPIA_GUILDS, CardSetEdition.FIRST_EDITION)}
    seed = _find_seed_with_card(db, "Tournament", sets_editions)
    if seed is None:
        pytest.skip("no seed found with Tournament in kingdom_piles")
    random.seed(seed)
    game = generate_game(db, sets_editions=sets_editions, use_colony=False)
    assert len(game.non_supply_cards) == 5
    assert all(CardType.PRIZE in c.types for c in game.non_supply_cards)
    assert {c.name for c in game.non_supply_cards} == {
        "Bag of Gold",
        "Diadem",
        "Followers",
        "Princess",
        "Trusty Steed",
    }


def test_joust_triggers_rewards(db: CardDatabase) -> None:
    sets_editions = {(CardSet.CORNUCOPIA_GUILDS, CardSetEdition.SECOND_EDITION)}
    seed = _find_seed_with_card(db, "Joust", sets_editions)
    if seed is None:
        pytest.skip("no seed found with Joust in kingdom_piles")
    random.seed(seed)
    game = generate_game(db, sets_editions=sets_editions, use_colony=False)
    rewards = [c for c in game.non_supply_cards if CardType.REWARD in c.types]
    assert len(rewards) == 6
    assert {c.name for c in rewards} == {
        "Coronet",
        "Courser",
        "Demesne",
        "Housecarl",
        "Huge Turnip",
        "Renown",
    }


def test_no_non_supply_without_triggers(db: CardDatabase) -> None:
    game = generate_game(
        db, sets_editions={(CardSet.BASE, CardSetEdition.SECOND_EDITION)}
    )
    assert game.non_supply_cards == []


def test_baker_setup_instruction(db: CardDatabase) -> None:
    sets_editions = {(CardSet.CORNUCOPIA_GUILDS, CardSetEdition.SECOND_EDITION)}
    seed = _find_seed_with_card(db, "Baker", sets_editions)
    if seed is None:
        pytest.skip("no seed found with Baker in kingdom_piles")
    random.seed(seed)
    game = generate_game(db, sets_editions=sets_editions, use_colony=False)
    assert Material.COFFERS_MAT in game.materials
    assert Material.COIN_TOKENS in game.materials
    assert "Baker: Each player gets +1 Coffers." in game.setup_instructions


def test_coffers_card_setup_instruction(db: CardDatabase) -> None:
    sets_editions = {(CardSet.CORNUCOPIA_GUILDS, CardSetEdition.SECOND_EDITION)}
    seed = _find_seed(
        db,
        sets_editions,
        lambda g: (
            bool(names := {c.name for c in g.kingdom_cards})
            and bool(
                names
                & {
                    "Butcher",
                    "Candlestick Maker",
                    "Footpad",
                    "Joust",
                    "Merchant Guild",
                    "Plaza",
                }
            )
            and "Baker" not in names
        ),
        use_colony=False,
    )
    if seed is None:
        pytest.skip("no seed found with Coffers card (not Baker) without Baker")
    random.seed(seed)
    game = generate_game(db, sets_editions=sets_editions, use_colony=False)
    assert Material.COFFERS_MAT in game.materials
    assert Material.COIN_TOKENS in game.materials
    assert "Baker: Each player gets +1 Coffers." not in game.setup_instructions


def test_no_setup_instructions_without_triggers(db: CardDatabase) -> None:
    game = generate_game(
        db, sets_editions={(CardSet.BASE, CardSetEdition.SECOND_EDITION)}
    )
    assert game.setup_instructions == []


def test_dark_ages_set_only(db: CardDatabase) -> None:
    game = generate_game(
        db, sets_editions={(CardSet.DARK_AGES, CardSetEdition.FIRST_EDITION)}
    )
    assert len(game.kingdom_cards) == 10
    for card in game.kingdom_cards:
        assert card.set == CardSet.DARK_AGES


def test_dark_ages_sets_used(db: CardDatabase) -> None:
    game = generate_game(
        db, sets_editions={(CardSet.DARK_AGES, CardSetEdition.FIRST_EDITION)}
    )
    assert game.sets_used == [CardSet.DARK_AGES]


def test_ruins_pile_present_with_looter(db: CardDatabase) -> None:
    seed = _find_seed(
        db,
        {(CardSet.DARK_AGES, CardSetEdition.FIRST_EDITION)},
        lambda g: any(CardType.LOOTER in c.types for c in g.kingdom_cards),
    )
    if seed is None:
        pytest.skip("no seed found with a Looter in kingdom_piles")
    random.seed(seed)
    game = generate_game(
        db, sets_editions={(CardSet.DARK_AGES, CardSetEdition.FIRST_EDITION)}
    )
    ruins = [c for c in game.basic_cards if CardType.RUINS in c.types]
    assert len(ruins) == 1
    assert ruins[0].name == "Ruins"


def test_no_ruins_without_looter(db: CardDatabase) -> None:
    # Base 2E has no Looters — Ruins should never appear.
    game = generate_game(
        db, sets_editions={(CardSet.BASE, CardSetEdition.SECOND_EDITION)}
    )
    ruins = [c for c in game.basic_cards if CardType.RUINS in c.types]
    assert ruins == []


def test_ruins_in_basic_piles_not_non_supply(db: CardDatabase) -> None:
    seed = _find_seed(
        db,
        {(CardSet.DARK_AGES, CardSetEdition.FIRST_EDITION)},
        lambda g: any(CardType.LOOTER in c.types for c in g.kingdom_cards),
    )
    if seed is None:
        pytest.skip("no seed found with a Looter in kingdom_piles")
    random.seed(seed)
    game = generate_game(
        db, sets_editions={(CardSet.DARK_AGES, CardSetEdition.FIRST_EDITION)}
    )
    ruins_in_non_supply = [
        c for c in game.non_supply_cards if CardType.RUINS in c.types
    ]
    assert ruins_in_non_supply == []


def test_spoils_present_with_bandit_camp(db: CardDatabase) -> None:
    seed = _find_seed_with_card(
        db, "Bandit Camp", {(CardSet.DARK_AGES, CardSetEdition.FIRST_EDITION)}
    )
    if seed is None:
        pytest.skip("no seed found with Bandit Camp in kingdom_piles")
    random.seed(seed)
    game = generate_game(
        db, sets_editions={(CardSet.DARK_AGES, CardSetEdition.FIRST_EDITION)}
    )
    assert any(c.name == "Spoils" for c in game.non_supply_cards)


def test_spoils_present_with_marauder(db: CardDatabase) -> None:
    seed = _find_seed_with_card(
        db, "Marauder", {(CardSet.DARK_AGES, CardSetEdition.FIRST_EDITION)}
    )
    if seed is None:
        pytest.skip("no seed found with Marauder in kingdom_piles")
    random.seed(seed)
    game = generate_game(
        db, sets_editions={(CardSet.DARK_AGES, CardSetEdition.FIRST_EDITION)}
    )
    assert any(c.name == "Spoils" for c in game.non_supply_cards)


def test_spoils_present_with_pillage(db: CardDatabase) -> None:
    seed = _find_seed_with_card(
        db, "Pillage", {(CardSet.DARK_AGES, CardSetEdition.FIRST_EDITION)}
    )
    if seed is None:
        pytest.skip("no seed found with Pillage in kingdom_piles")
    random.seed(seed)
    game = generate_game(
        db, sets_editions={(CardSet.DARK_AGES, CardSetEdition.FIRST_EDITION)}
    )
    assert any(c.name == "Spoils" for c in game.non_supply_cards)


def test_no_spoils_without_triggers(db: CardDatabase) -> None:
    game = generate_game(
        db, sets_editions={(CardSet.BASE, CardSetEdition.SECOND_EDITION)}
    )
    assert not any(c.name == "Spoils" for c in game.non_supply_cards)


def test_madman_present_with_hermit(db: CardDatabase) -> None:
    seed = _find_seed_with_card(
        db, "Hermit", {(CardSet.DARK_AGES, CardSetEdition.FIRST_EDITION)}
    )
    if seed is None:
        pytest.skip("no seed found with Hermit in kingdom_piles")
    random.seed(seed)
    game = generate_game(
        db, sets_editions={(CardSet.DARK_AGES, CardSetEdition.FIRST_EDITION)}
    )
    assert any(c.name == "Madman" for c in game.non_supply_cards)


def test_no_madman_without_hermit(db: CardDatabase) -> None:
    game = generate_game(
        db, sets_editions={(CardSet.BASE, CardSetEdition.SECOND_EDITION)}
    )
    assert not any(c.name == "Madman" for c in game.non_supply_cards)


def test_mercenary_present_with_urchin(db: CardDatabase) -> None:
    seed = _find_seed_with_card(
        db, "Urchin", {(CardSet.DARK_AGES, CardSetEdition.FIRST_EDITION)}
    )
    if seed is None:
        pytest.skip("no seed found with Urchin in kingdom_piles")
    random.seed(seed)
    game = generate_game(
        db, sets_editions={(CardSet.DARK_AGES, CardSetEdition.FIRST_EDITION)}
    )
    assert any(c.name == "Mercenary" for c in game.non_supply_cards)


def test_no_mercenary_without_urchin(db: CardDatabase) -> None:
    game = generate_game(
        db, sets_editions={(CardSet.BASE, CardSetEdition.SECOND_EDITION)}
    )
    assert not any(c.name == "Mercenary" for c in game.non_supply_cards)


def test_shelters_forced_on(db: CardDatabase) -> None:
    game = generate_game(
        db,
        sets_editions={(CardSet.BASE, CardSetEdition.FIRST_EDITION)},
        use_shelters=True,
    )
    shelters = {card for card in game.basic_cards if CardType.SHELTER in card.types}
    assert len(shelters) == 1
    assert next(iter(shelters)).name == "Shelters"


def test_shelters_forced_off(db: CardDatabase) -> None:
    game = generate_game(
        db,
        sets_editions={(CardSet.DARK_AGES, CardSetEdition.FIRST_EDITION)},
        use_shelters=False,
    )
    assert not any(CardType.SHELTER in c.types for c in game.basic_cards)


def test_shelters_never_without_dark_ages(db: CardDatabase) -> None:
    game = generate_game(
        db, sets_editions={(CardSet.BASE, CardSetEdition.FIRST_EDITION)}
    )
    assert not any(CardType.SHELTER in c.types for c in game.basic_cards)


def test_shelters_always_with_all_dark_ages(db: CardDatabase) -> None:
    game = generate_game(
        db, sets_editions={(CardSet.DARK_AGES, CardSetEdition.FIRST_EDITION)}
    )
    assert any(CardType.SHELTER in c.types for c in game.basic_cards)


def test_shelters_random_with_mixed_sets(db: CardDatabase) -> None:
    shelter_results = set()
    for seed in range(100):
        random.seed(seed)
        game = generate_game(
            db,
            sets_editions={
                (CardSet.BASE, CardSetEdition.SECOND_EDITION),
                (CardSet.DARK_AGES, CardSetEdition.FIRST_EDITION),
            },
        )
        has_shelters = any(CardType.SHELTER in c.types for c in game.basic_cards)
        shelter_results.add(has_shelters)
        if len(shelter_results) == 2:
            break
    assert True in shelter_results
    assert False in shelter_results


def test_shelters_setup_instruction_present_when_shelters_used(
    db: CardDatabase,
) -> None:
    game = generate_game(
        db,
        sets_editions={(CardSet.DARK_AGES, CardSetEdition.FIRST_EDITION)},
        use_shelters=True,
    )
    assert any("Shelters" in instr for instr in game.setup_instructions)


def test_shelters_setup_instruction_absent_without_shelters(db: CardDatabase) -> None:
    game = generate_game(
        db,
        sets_editions={(CardSet.BASE, CardSetEdition.SECOND_EDITION)},
        use_shelters=False,
    )
    assert not any("Shelters" in instr for instr in game.setup_instructions)


def test_shelters_sorted_by_name_in_non_supply(db: CardDatabase) -> None:
    game = generate_game(
        db,
        sets_editions={(CardSet.DARK_AGES, CardSetEdition.FIRST_EDITION)},
        use_shelters=True,
    )
    shelters = [c for c in game.basic_cards if CardType.SHELTER in c.types]
    names = [c.name for c in shelters]
    assert names == sorted(names)


def test_material_villagers_detected(ten_card_db: CardDatabaseFactory) -> None:
    db = ten_card_db(instructions="+2 Villagers")
    game = generate_game(db)
    assert Material.COFFERS_VILLAGERS_MAT in game.materials
    assert Material.COIN_TOKENS in game.materials
    assert Material.COFFERS_MAT not in game.materials


def test_material_exile_detected(ten_card_db: CardDatabaseFactory) -> None:
    db = ten_card_db(instructions="Exile a card from your hand.")
    game = generate_game(db)
    assert Material.EXILE_MAT in game.materials


def test_material_liaison_detected(
    ten_card_db: CardDatabaseFactory, make_card: CardFactory
) -> None:
    db = ten_card_db(
        types=(CardType.ACTION, CardType.LIAISON),
        instructions="",
    )
    ally_card = make_card(
        name="Test Ally",
        types=(CardType.ALLY,),
        purpose=CardPurpose.LANDSCAPE,
        image="Test Ally.jpg",
        instructions="",
    )
    db = CardDatabase([*db.cards, ally_card])
    game = generate_game(db)
    assert Material.FAVORS_MAT in game.materials
    assert Material.COIN_TOKENS in game.materials


def test_material_minus_one_coin_token_detected(
    ten_card_db: CardDatabaseFactory,
) -> None:
    db = ten_card_db(instructions="Place a -$1 token on a Supply pile.")
    game = generate_game(db)
    assert Material.MINUS_ONE_COIN_TOKEN in game.materials


def test_material_omen_detected(
    ten_card_db: CardDatabaseFactory, make_card: CardFactory
) -> None:
    db = ten_card_db(
        types=(CardType.ACTION, CardType.OMEN),
        instructions="",
    )
    prophecy_card = make_card(
        name="Test Prophecy",
        types=(CardType.PROPHECY,),
        purpose=CardPurpose.LANDSCAPE,
        image="Test Prophecy.jpg",
        instructions="",
    )
    db = CardDatabase([*db.cards, prophecy_card])
    game = generate_game(db)
    assert Material.SUN_TOKENS in game.materials


def test_adventures_set_only(db: CardDatabase) -> None:
    game = generate_game(
        db, sets_editions={(CardSet.ADVENTURES, CardSetEdition.FIRST_EDITION)}
    )
    assert len(game.kingdom_cards) == 10
    for card in game.kingdom_cards:
        assert card.set == CardSet.ADVENTURES


def test_adventures_sets_used(db: CardDatabase) -> None:
    game = generate_game(
        db, sets_editions={(CardSet.ADVENTURES, CardSetEdition.FIRST_EDITION)}
    )
    assert CardSet.ADVENTURES in game.sets_used


def test_mixed_base_2e_adventures_1e(db: CardDatabase) -> None:
    game = generate_game(
        db,
        sets_editions={
            (CardSet.BASE, CardSetEdition.SECOND_EDITION),
            (CardSet.ADVENTURES, CardSetEdition.FIRST_EDITION),
        },
    )
    names = {card.name for card in game.kingdom_cards}
    assert not names & BASE_1E_ONLY


PAGE_CHAIN = {"Treasure Hunter", "Warrior", "Hero", "Champion"}
PEASANT_CHAIN = {"Soldier", "Fugitive", "Disciple", "Teacher"}


def test_page_triggers_traveller_chain(db: CardDatabase) -> None:
    sets_editions = {(CardSet.ADVENTURES, CardSetEdition.FIRST_EDITION)}
    seed = _find_seed_with_card(db, "Page", sets_editions)
    if seed is None:
        pytest.skip("no seed found with Page in kingdom_piles")
    random.seed(seed)
    game = generate_game(db, sets_editions=sets_editions)
    non_supply_names = {c.name for c in game.non_supply_cards}
    assert PAGE_CHAIN <= non_supply_names


def test_page_chain_cards_are_non_supply(db: CardDatabase) -> None:
    sets_editions = {(CardSet.ADVENTURES, CardSetEdition.FIRST_EDITION)}
    seed = _find_seed_with_card(db, "Page", sets_editions)
    if seed is None:
        pytest.skip("no seed found with Page in kingdom_piles")
    random.seed(seed)
    game = generate_game(db, sets_editions=sets_editions)
    page_chain = [c for c in game.non_supply_cards if c.name in PAGE_CHAIN]
    assert len(page_chain) == 4
    # Treasure Hunter, Warrior, Hero are Travellers; Champion is the chain's end (Action/Duration)
    traveller_names = {c.name for c in page_chain if CardType.TRAVELLER in c.types}
    assert traveller_names == {"Treasure Hunter", "Warrior", "Hero"}


def test_page_chain_not_in_kingdom_piles(db: CardDatabase) -> None:
    sets_editions = {(CardSet.ADVENTURES, CardSetEdition.FIRST_EDITION)}
    seed = _find_seed_with_card(db, "Page", sets_editions)
    if seed is None:
        pytest.skip("no seed found with Page in kingdom_piles")
    random.seed(seed)
    game = generate_game(db, sets_editions=sets_editions)
    kingdom_names = {c.name for c in game.kingdom_cards}
    assert not PAGE_CHAIN & kingdom_names


def test_peasant_triggers_traveller_chain(db: CardDatabase) -> None:
    sets_editions = {(CardSet.ADVENTURES, CardSetEdition.FIRST_EDITION)}
    seed = _find_seed_with_card(db, "Peasant", sets_editions)
    if seed is None:
        pytest.skip("no seed found with Peasant in kingdom_piles")
    random.seed(seed)
    game = generate_game(db, sets_editions=sets_editions)
    non_supply_names = {c.name for c in game.non_supply_cards}
    assert PEASANT_CHAIN <= non_supply_names


def test_peasant_chain_cards_are_non_supply(db: CardDatabase) -> None:
    sets_editions = {(CardSet.ADVENTURES, CardSetEdition.FIRST_EDITION)}
    seed = _find_seed_with_card(db, "Peasant", sets_editions)
    if seed is None:
        pytest.skip("no seed found with Peasant in kingdom_piles")
    random.seed(seed)
    game = generate_game(db, sets_editions=sets_editions)
    peasant_chain = [c for c in game.non_supply_cards if c.name in PEASANT_CHAIN]
    assert len(peasant_chain) == 4
    # Soldier, Fugitive, Disciple are Travellers; Teacher is the chain's end (Action/Reserve)
    traveller_names = {c.name for c in peasant_chain if CardType.TRAVELLER in c.types}
    assert traveller_names == {"Soldier", "Fugitive", "Disciple"}


def test_peasant_chain_not_in_kingdom_piles(db: CardDatabase) -> None:
    sets_editions = {(CardSet.ADVENTURES, CardSetEdition.FIRST_EDITION)}
    seed = _find_seed_with_card(db, "Peasant", sets_editions)
    if seed is None:
        pytest.skip("no seed found with Peasant in kingdom_piles")
    random.seed(seed)
    game = generate_game(db, sets_editions=sets_editions)
    kingdom_names = {c.name for c in game.kingdom_cards}
    assert not PEASANT_CHAIN & kingdom_names


def test_no_traveller_chain_without_page_or_peasant(db: CardDatabase) -> None:
    # Base 2E has no Page or Peasant — no Traveller chain should appear.
    game = generate_game(
        db, sets_editions={(CardSet.BASE, CardSetEdition.SECOND_EDITION)}
    )
    non_supply_names = {c.name for c in game.non_supply_cards}
    assert not (PAGE_CHAIN | PEASANT_CHAIN) & non_supply_names


def test_both_traveller_chains_when_page_and_peasant(db: CardDatabase) -> None:
    sets_editions = {(CardSet.ADVENTURES, CardSetEdition.FIRST_EDITION)}
    # Search for a seed where both Page and Peasant are in kingdom_piles
    found_seed = None
    for seed in range(2000):
        random.seed(seed)
        game = generate_game(db, sets_editions=sets_editions)
        names = {c.name for c in game.kingdom_cards}
        if "Page" in names and "Peasant" in names:
            found_seed = seed
            break
    if found_seed is None:
        pytest.skip("no seed found with both Page and Peasant in kingdom_piles")
    random.seed(found_seed)
    game = generate_game(db, sets_editions=sets_editions)
    non_supply_names = {c.name for c in game.non_supply_cards}
    assert PAGE_CHAIN <= non_supply_names
    assert PEASANT_CHAIN <= non_supply_names


def test_tavern_mat_detected_with_reserve_card(db: CardDatabase) -> None:
    # Reserve cards say "Put this on your Tavern mat." — material must be detected.
    reserve_cards = {
        "Coin of the Realm",
        "Duplicate",
        "Guide",
        "Ratcatcher",
        "Royal Carriage",
        "Transmogrify",
        "Wine Merchant",
    }
    sets_editions = {(CardSet.ADVENTURES, CardSetEdition.FIRST_EDITION)}
    seed = _find_seed_with_any_kingdom_card(db, reserve_cards, sets_editions)
    if seed is None:
        pytest.skip("no seed found with a Reserve card in kingdom_piles")
    random.seed(seed)
    game = generate_game(db, sets_editions=sets_editions)
    assert Material.TAVERN_MAT in game.materials


def test_journey_token_detected_with_giant_or_ranger(db: CardDatabase) -> None:
    # Giant and Ranger reference the Journey token in their instructions.
    sets_editions = {(CardSet.ADVENTURES, CardSetEdition.FIRST_EDITION)}
    seed = _find_seed_with_any_kingdom_card(db, {"Giant", "Ranger"}, sets_editions)
    if seed is None:
        pytest.skip("no seed found with Giant or Ranger in kingdom_piles")
    random.seed(seed)
    game = generate_game(db, sets_editions=sets_editions)
    assert Material.JOURNEY_TOKEN in game.materials


def test_minus_one_card_token_detected_with_relic(db: CardDatabase) -> None:
    # Relic says "puts their -1 Card token on their deck."
    sets_editions = {(CardSet.ADVENTURES, CardSetEdition.FIRST_EDITION)}
    seed = _find_seed_with_card(db, "Relic", sets_editions)
    if seed is None:
        pytest.skip("no seed found with Relic in kingdom_piles")
    random.seed(seed)
    game = generate_game(db, sets_editions=sets_editions)
    assert Material.MINUS_ONE_CARD_TOKEN in game.materials


def test_adventures_generates_two_landscape_cards(db: CardDatabase) -> None:
    sets_editions = {(CardSet.ADVENTURES, CardSetEdition.FIRST_EDITION)}
    seed = _find_seed(
        db,
        sets_editions,
        lambda g: any(CardType.EVENT in c.types for c in g.landscapes),
    )
    if seed is None:
        pytest.skip("no seed found with at least one Event as a landscape card")
    random.seed(seed)
    game = generate_game(db, sets_editions=sets_editions)
    assert 0 < len(game.landscapes) <= 2


def test_landscape_cards_are_events_in_adventures(db: CardDatabase) -> None:
    sets_editions = {(CardSet.ADVENTURES, CardSetEdition.FIRST_EDITION)}
    seed = _find_seed(
        db,
        sets_editions,
        lambda g: any(CardType.EVENT in c.types for c in g.landscapes),
    )
    if seed is None:
        pytest.skip("no seed found with at least one Event as a landscape card")
    random.seed(seed)
    game = generate_game(db, sets_editions=sets_editions)
    for card in game.landscapes:
        assert CardType.EVENT in card.types


def test_landscape_cards_not_in_kingdom_piles(db: CardDatabase) -> None:
    sets_editions = {(CardSet.ADVENTURES, CardSetEdition.FIRST_EDITION)}
    seed = _find_seed(
        db,
        sets_editions,
        lambda g: any(CardType.EVENT in c.types for c in g.landscapes),
    )
    if seed is None:
        pytest.skip("no seed found with at least one Event as a landscape card")
    random.seed(seed)
    game = generate_game(db, sets_editions=sets_editions)
    kingdom_names = {c.name for c in game.kingdom_cards}
    for card in game.landscapes:
        assert card.name not in kingdom_names


def test_landscape_cards_are_distinct(db: CardDatabase) -> None:
    sets_editions = {(CardSet.ADVENTURES, CardSetEdition.FIRST_EDITION)}
    seed = _find_seed(
        db,
        sets_editions,
        lambda g: any(CardType.EVENT in c.types for c in g.landscapes),
    )
    if seed is None:
        pytest.skip("no seed found with at least one Event as a landscape card")
    random.seed(seed)
    game = generate_game(db, sets_editions=sets_editions)
    names = [c.name for c in game.landscapes]
    assert len(names) == len(set(names))


def test_no_landscape_cards_for_sets_without_events(db: CardDatabase) -> None:
    # Base 2E has no landscape cards — landscape_cards should be empty.
    game = generate_game(
        db, sets_editions={(CardSet.BASE, CardSetEdition.SECOND_EDITION)}
    )
    assert game.landscapes == []


def test_empires_set_only(db: CardDatabase) -> None:
    game = generate_game(
        db, sets_editions={(CardSet.EMPIRES, CardSetEdition.FIRST_EDITION)}
    )
    assert len(game.kingdom_cards) == 10
    for card in game.kingdom_cards:
        assert card.set == CardSet.EMPIRES


def test_empires_sets_used(db: CardDatabase) -> None:
    game = generate_game(
        db, sets_editions={(CardSet.EMPIRES, CardSetEdition.FIRST_EDITION)}
    )
    assert CardSet.EMPIRES in game.sets_used


def test_mixed_base_2e_empires_1e(db: CardDatabase) -> None:
    game = generate_game(
        db,
        sets_editions={
            (CardSet.BASE, CardSetEdition.SECOND_EDITION),
            (CardSet.EMPIRES, CardSetEdition.FIRST_EDITION),
        },
    )
    names = {card.name for card in game.kingdom_cards}
    assert not names & BASE_1E_ONLY


def test_debt_tokens_added_with_debt_cost_card(db: CardDatabase) -> None:
    # Engineer (4D), City Quarter (8D), Overlord (8D), Royal Blacksmith (8D) cost debt.
    debt_cost_cards = {"Engineer", "City Quarter", "Overlord", "Royal Blacksmith"}
    sets_editions = {(CardSet.EMPIRES, CardSetEdition.FIRST_EDITION)}
    seed = _find_seed_with_any_kingdom_card(db, debt_cost_cards, sets_editions)
    if seed is None:
        pytest.skip("no seed found with a debt-cost kingdom card")
    random.seed(seed)
    game = generate_game(db, sets_editions=sets_editions)
    assert Material.DEBT_TOKENS in game.materials


def test_debt_tokens_added_with_capital(db: CardDatabase) -> None:
    # Capital gives +6D when discarded from play, so debt tokens are needed.
    sets_editions = {(CardSet.EMPIRES, CardSetEdition.FIRST_EDITION)}
    seed = _find_seed_with_card(db, "Capital", sets_editions)
    if seed is None:
        pytest.skip("no seed found with Capital in kingdom_piles")
    random.seed(seed)
    game = generate_game(db, sets_editions=sets_editions)
    assert Material.DEBT_TOKENS in game.materials


def test_debt_tokens_added_with_debt_event(db: CardDatabase) -> None:
    # Donate, Annex, and Triumph are Events that cost debt.
    # Tax adds 2D to a supply pile.  Any of these in landscapes requires debt tokens.
    sets_editions = {(CardSet.EMPIRES, CardSetEdition.FIRST_EDITION)}
    seed = _find_seed(
        db,
        sets_editions,
        lambda g: any(CardType.LANDMARK in c.types for c in g.landscapes),
    )  # ensures some landscapes present
    # More targeted: search for a seed with a debt-cost event in landscapes
    for s in range(1000):
        random.seed(s)
        game = generate_game(db, sets_editions=sets_editions)
        if any(c.has_debt_cost for c in game.landscapes):
            seed = s
            break
    else:
        pytest.skip("no seed found with a debt-cost landscape card")
    random.seed(seed)
    game = generate_game(db, sets_editions=sets_editions)
    assert Material.DEBT_TOKENS in game.materials


def test_no_debt_tokens_without_debt_cards(ten_card_db: CardDatabaseFactory) -> None:
    # A kingdom with only pure coin-cost cards should never require debt tokens.
    db = ten_card_db(instructions="+1 Card")
    game = generate_game(db)
    assert Material.DEBT_TOKENS not in game.materials


def test_vp_tokens_with_farmers_market(db: CardDatabase) -> None:
    # Farmers' Market uses "add 1 VP to the pile" — not matched by +\d+ VP regex.
    sets_editions = {(CardSet.EMPIRES, CardSetEdition.FIRST_EDITION)}
    seed = _find_seed_with_card(db, "Farmers' Market", sets_editions)
    if seed is None:
        pytest.skip("no seed found with Farmers' Market in kingdom_piles")
    random.seed(seed)
    game = generate_game(db, sets_editions=sets_editions)
    assert Material.VICTORY_TOKENS in game.materials


def test_vp_tokens_with_wild_hunt(db: CardDatabase) -> None:
    # Wild Hunt uses "add 1 VP to the Wild Hunt pile" — not matched by +\d+ VP regex.
    sets_editions = {(CardSet.EMPIRES, CardSetEdition.FIRST_EDITION)}
    seed = _find_seed_with_card(db, "Wild Hunt", sets_editions)
    if seed is None:
        pytest.skip("no seed found with Wild Hunt in kingdom_piles")
    random.seed(seed)
    game = generate_game(db, sets_editions=sets_editions)
    assert Material.VICTORY_TOKENS in game.materials


# Cards that have a paired Heirloom (Non-Supply).
HEIRLOOM_PAIRS: dict[str, str] = {
    "Cemetery": "Haunted Mirror",
    "Fool": "Lucky Coin",
    "Pixie": "Goat",
    "Pooka": "Cursed Gold",
    "Secret Cave": "Magic Lamp",
    "Shepherd": "Pasture",
    "Tracker": "Pouch",
}

# Fate cards (give Boons): trigger Will-o'-Wisp via The Swamp's Gift.
FATE_CARDS = {
    "Bard",
    "Blessed Village",
    "Druid",
    "Fool",
    "Idol",
    "Pixie",
    "Sacred Grove",
    "Tracker",
}


def test_nocturne_set_only(db: CardDatabase) -> None:
    game = generate_game(
        db, sets_editions={(CardSet.NOCTURNE, CardSetEdition.FIRST_EDITION)}
    )
    assert len(game.kingdom_cards) == 10
    for card in game.kingdom_cards:
        assert card.set == CardSet.NOCTURNE


def test_nocturne_sets_used(db: CardDatabase) -> None:
    game = generate_game(
        db, sets_editions={(CardSet.NOCTURNE, CardSetEdition.FIRST_EDITION)}
    )
    assert CardSet.NOCTURNE in game.sets_used


def test_mixed_base_2e_nocturne_1e(db: CardDatabase) -> None:
    game = generate_game(
        db,
        sets_editions={
            (CardSet.BASE, CardSetEdition.SECOND_EDITION),
            (CardSet.NOCTURNE, CardSetEdition.FIRST_EDITION),
        },
    )
    names = {card.name for card in game.kingdom_cards}
    assert not names & BASE_1E_ONLY


@pytest.mark.parametrize(("kingdom_card", "heirloom"), HEIRLOOM_PAIRS.items())
def test_heirloom_present_with_kingdom_card(
    db: CardDatabase, kingdom_card: str, heirloom: str
) -> None:
    seed = _find_seed_with_card(
        db, kingdom_card, {(CardSet.NOCTURNE, CardSetEdition.FIRST_EDITION)}
    )
    if seed is None:
        pytest.skip(f"no seed found with {kingdom_card} in kingdom_piles")
    random.seed(seed)
    game = generate_game(
        db, sets_editions={(CardSet.NOCTURNE, CardSetEdition.FIRST_EDITION)}
    )
    basic_names = {c.name for c in game.basic_cards}
    assert heirloom in basic_names


def test_no_heirloom_without_kingdom_card(db: CardDatabase) -> None:
    # Base 2E has no heirloom kingdom cards — no heirlooms should appear.
    game = generate_game(
        db, sets_editions={(CardSet.BASE, CardSetEdition.SECOND_EDITION)}
    )
    heirlooms = {c.name for c in game.non_supply_cards} & set(HEIRLOOM_PAIRS.values())
    assert heirlooms == set()


def test_heirloom_not_in_kingdom_piles(db: CardDatabase) -> None:
    seed = _find_seed_with_card(
        db, "Pooka", {(CardSet.NOCTURNE, CardSetEdition.FIRST_EDITION)}
    )
    if seed is None:
        pytest.skip("no seed found with Pooka in kingdom_piles")
    random.seed(seed)
    game = generate_game(
        db, sets_editions={(CardSet.NOCTURNE, CardSetEdition.FIRST_EDITION)}
    )
    kingdom_names = {c.name for c in game.kingdom_cards}
    assert "Cursed Gold" not in kingdom_names


def test_bat_present_with_vampire(db: CardDatabase) -> None:
    seed = _find_seed_with_card(
        db, "Vampire", {(CardSet.NOCTURNE, CardSetEdition.FIRST_EDITION)}
    )
    if seed is None:
        pytest.skip("no seed found with Vampire in kingdom_piles")
    random.seed(seed)
    game = generate_game(
        db, sets_editions={(CardSet.NOCTURNE, CardSetEdition.FIRST_EDITION)}
    )
    non_supply_names = {c.name for c in game.non_supply_cards}
    assert "Bat" in non_supply_names


def test_no_bat_without_vampire(db: CardDatabase) -> None:
    game = generate_game(
        db, sets_editions={(CardSet.BASE, CardSetEdition.SECOND_EDITION)}
    )
    assert not any(c.name == "Bat" for c in game.non_supply_cards)


def test_bat_not_in_kingdom_piles(db: CardDatabase) -> None:
    seed = _find_seed_with_card(
        db, "Vampire", {(CardSet.NOCTURNE, CardSetEdition.FIRST_EDITION)}
    )
    if seed is None:
        pytest.skip("no seed found with Vampire in kingdom_piles")
    random.seed(seed)
    game = generate_game(
        db, sets_editions={(CardSet.NOCTURNE, CardSetEdition.FIRST_EDITION)}
    )
    kingdom_names = {c.name for c in game.kingdom_cards}
    assert "Bat" not in kingdom_names


def test_wish_present_with_leprechaun(db: CardDatabase) -> None:
    seed = _find_seed_with_card(
        db, "Leprechaun", {(CardSet.NOCTURNE, CardSetEdition.FIRST_EDITION)}
    )
    if seed is None:
        pytest.skip("no seed found with Leprechaun in kingdom_piles")
    random.seed(seed)
    game = generate_game(
        db, sets_editions={(CardSet.NOCTURNE, CardSetEdition.FIRST_EDITION)}
    )
    non_supply_names = {c.name for c in game.non_supply_cards}
    assert "Wish" in non_supply_names


def test_no_wish_without_leprechaun(db: CardDatabase) -> None:
    game = generate_game(
        db, sets_editions={(CardSet.BASE, CardSetEdition.SECOND_EDITION)}
    )
    assert not any(c.name == "Wish" for c in game.non_supply_cards)


def test_imp_present_with_devils_workshop(db: CardDatabase) -> None:
    seed = _find_seed_with_card(
        db, "Devil's Workshop", {(CardSet.NOCTURNE, CardSetEdition.FIRST_EDITION)}
    )
    if seed is None:
        pytest.skip("no seed found with Devil's Workshop in kingdom_piles")
    random.seed(seed)
    game = generate_game(
        db, sets_editions={(CardSet.NOCTURNE, CardSetEdition.FIRST_EDITION)}
    )
    assert any(c.name == "Imp" for c in game.non_supply_cards)


def test_imp_present_with_tormentor(db: CardDatabase) -> None:
    seed = _find_seed_with_card(
        db, "Tormentor", {(CardSet.NOCTURNE, CardSetEdition.FIRST_EDITION)}
    )
    if seed is None:
        pytest.skip("no seed found with Tormentor in kingdom_piles")
    random.seed(seed)
    game = generate_game(
        db, sets_editions={(CardSet.NOCTURNE, CardSetEdition.FIRST_EDITION)}
    )
    assert any(c.name == "Imp" for c in game.non_supply_cards)


def test_imp_present_with_exorcist(db: CardDatabase) -> None:
    seed = _find_seed_with_card(
        db, "Exorcist", {(CardSet.NOCTURNE, CardSetEdition.FIRST_EDITION)}
    )
    if seed is None:
        pytest.skip("no seed found with Exorcist in kingdom_piles")
    random.seed(seed)
    game = generate_game(
        db, sets_editions={(CardSet.NOCTURNE, CardSetEdition.FIRST_EDITION)}
    )
    assert any(c.name == "Imp" for c in game.non_supply_cards)


def test_will_o_wisp_present_with_fate_card(db: CardDatabase) -> None:
    # The Swamp's Gift Boon gives Will-o'-Wisp; it's always in the Boon deck
    # whenever any Fate card is present.
    seed = _find_seed_with_any_kingdom_card(
        db, FATE_CARDS, {(CardSet.NOCTURNE, CardSetEdition.FIRST_EDITION)}
    )
    if seed is None:
        pytest.skip("no seed found with a Fate card in kingdom_piles")
    random.seed(seed)
    game = generate_game(
        db, sets_editions={(CardSet.NOCTURNE, CardSetEdition.FIRST_EDITION)}
    )
    assert any(c.name == "Will-o'-Wisp" for c in game.non_supply_cards)


def test_will_o_wisp_present_with_exorcist(db: CardDatabase) -> None:
    seed = _find_seed_with_card(
        db, "Exorcist", {(CardSet.NOCTURNE, CardSetEdition.FIRST_EDITION)}
    )
    if seed is None:
        pytest.skip("no seed found with Exorcist in kingdom_piles")
    random.seed(seed)
    game = generate_game(
        db, sets_editions={(CardSet.NOCTURNE, CardSetEdition.FIRST_EDITION)}
    )
    assert any(c.name == "Will-o'-Wisp" for c in game.non_supply_cards)


def test_ghost_present_with_exorcist(db: CardDatabase) -> None:
    seed = _find_seed_with_card(
        db, "Exorcist", {(CardSet.NOCTURNE, CardSetEdition.FIRST_EDITION)}
    )
    if seed is None:
        pytest.skip("no seed found with Exorcist in kingdom_piles")
    random.seed(seed)
    game = generate_game(
        db, sets_editions={(CardSet.NOCTURNE, CardSetEdition.FIRST_EDITION)}
    )
    assert any(c.name == "Ghost" for c in game.non_supply_cards)


def test_ghost_present_with_cemetery(db: CardDatabase) -> None:
    # Cemetery's Heirloom is Haunted Mirror; trashing it can gain a Ghost.
    seed = _find_seed_with_card(
        db, "Cemetery", {(CardSet.NOCTURNE, CardSetEdition.FIRST_EDITION)}
    )
    if seed is None:
        pytest.skip("no seed found with Cemetery in kingdom_piles")
    random.seed(seed)
    game = generate_game(
        db, sets_editions={(CardSet.NOCTURNE, CardSetEdition.FIRST_EDITION)}
    )
    assert any(c.name == "Ghost" for c in game.non_supply_cards)


def test_no_spirit_piles_without_triggers(db: CardDatabase) -> None:
    game = generate_game(
        db, sets_editions={(CardSet.BASE, CardSetEdition.SECOND_EDITION)}
    )
    spirit_names = {"Imp", "Will-o'-Wisp", "Ghost"}
    assert not any(c.name in spirit_names for c in game.non_supply_cards)


def test_exorcist_triggers_all_three_spirit_piles(db: CardDatabase) -> None:
    seed = _find_seed_with_card(
        db, "Exorcist", {(CardSet.NOCTURNE, CardSetEdition.FIRST_EDITION)}
    )
    if seed is None:
        pytest.skip("no seed found with Exorcist in kingdom_piles")
    random.seed(seed)
    game = generate_game(
        db, sets_editions={(CardSet.NOCTURNE, CardSetEdition.FIRST_EDITION)}
    )
    non_supply_names = {c.name for c in game.non_supply_cards}
    assert {"Imp", "Will-o'-Wisp", "Ghost"} <= non_supply_names


def test_spirit_piles_not_in_kingdom_piles(db: CardDatabase) -> None:
    seed = _find_seed_with_card(
        db, "Exorcist", {(CardSet.NOCTURNE, CardSetEdition.FIRST_EDITION)}
    )
    if seed is None:
        pytest.skip("no seed found with Exorcist in kingdom_piles")
    random.seed(seed)
    game = generate_game(
        db, sets_editions={(CardSet.NOCTURNE, CardSetEdition.FIRST_EDITION)}
    )
    kingdom_names = {c.name for c in game.kingdom_cards}
    assert not {"Imp", "Will-o'-Wisp", "Ghost"} & kingdom_names


def test_necromancer_setup_instruction(db: CardDatabase) -> None:
    seed = _find_seed_with_card(
        db, "Necromancer", {(CardSet.NOCTURNE, CardSetEdition.FIRST_EDITION)}
    )
    if seed is None:
        pytest.skip("no seed found with Necromancer in kingdom_piles")
    random.seed(seed)
    game = generate_game(
        db, sets_editions={(CardSet.NOCTURNE, CardSetEdition.FIRST_EDITION)}
    )
    assert any("Zombie" in instr for instr in game.setup_instructions)


def test_druid_setup_instruction(db: CardDatabase) -> None:
    seed = _find_seed_with_card(
        db, "Druid", {(CardSet.NOCTURNE, CardSetEdition.FIRST_EDITION)}
    )
    if seed is None:
        pytest.skip("no seed found with Druid in kingdom_piles")
    random.seed(seed)
    game = generate_game(
        db, sets_editions={(CardSet.NOCTURNE, CardSetEdition.FIRST_EDITION)}
    )
    assert any("Boon" in instr for instr in game.setup_instructions)


def test_vp_tokens_with_landmark(db: CardDatabase) -> None:
    # Any Landmark landscape requires VP tokens (VP go on Landmark cards).
    sets_editions = {(CardSet.EMPIRES, CardSetEdition.FIRST_EDITION)}
    seed = _find_seed(
        db,
        sets_editions,
        lambda g: any(CardType.LANDMARK in c.types for c in g.landscapes),
    )
    if seed is None:
        pytest.skip("no seed found with a Landmark in landscapes")
    random.seed(seed)
    game = generate_game(db, sets_editions=sets_editions)
    assert Material.VICTORY_TOKENS in game.materials


def test_castles_setup_instruction_when_selected(db: CardDatabase) -> None:
    sets_editions = {(CardSet.EMPIRES, CardSetEdition.FIRST_EDITION)}
    seed = _find_seed_with_card(db, "Castles", sets_editions)
    if seed is None:
        pytest.skip("no seed found with Castles in kingdom_piles")
    random.seed(seed)
    game = generate_game(db, sets_editions=sets_editions)
    assert any("Castles" in instr for instr in game.setup_instructions)


def test_split_pile_setup_instruction_when_selected(db: CardDatabase) -> None:
    # All split pile cards (Catapult/Rocks, Encampment/Plunder, etc.) have Setup instructions.
    split_pile_names = {
        "Catapult/Rocks",
        "Encampment/Plunder",
        "Gladiator/Fortune",
        "Patrician/Emporium",
        "Settlers/Bustling Village",
    }
    sets_editions = {(CardSet.EMPIRES, CardSetEdition.FIRST_EDITION)}
    seed = _find_seed_with_any_kingdom_card(db, split_pile_names, sets_editions)
    if seed is None:
        pytest.skip("no seed found with a split pile in kingdom_piles")
    random.seed(seed)
    game = generate_game(db, sets_editions=sets_editions)
    selected_split = split_pile_names & {c.name for c in game.kingdom_cards}
    for name in selected_split:
        pile_name = name.split("/")[0]  # e.g. "Catapult" from "Catapult/Rocks"
        assert any(pile_name in instr for instr in game.setup_instructions), (
            f"Expected setup instruction for {name}"
        )


def test_empires_landscape_can_be_event_or_landmark(db: CardDatabase) -> None:
    # Empires has both Events and Landmarks as landscape cards.
    sets_editions = {(CardSet.EMPIRES, CardSetEdition.FIRST_EDITION)}
    event_found = False
    landmark_found = False
    for seed in range(500):
        random.seed(seed)
        game = generate_game(db, sets_editions=sets_editions)
        for card in game.landscapes:
            if CardType.EVENT in card.types:
                event_found = True
            if CardType.LANDMARK in card.types:
                landmark_found = True
        if event_found and landmark_found:
            break
    assert event_found, "Expected at least one Event in landscapes across seeds"
    assert landmark_found, "Expected at least one Landmark in landscapes across seeds"


def test_landscape_cards_contribute_to_sets_used(db: CardDatabase) -> None:
    sets_editions = {(CardSet.ADVENTURES, CardSetEdition.FIRST_EDITION)}
    seed = _find_seed(
        db,
        sets_editions,
        lambda g: any(CardType.EVENT in c.types for c in g.landscapes),
    )
    if seed is None:
        pytest.skip("no seed found with at least one Event as a landscape card")
    random.seed(seed)
    game = generate_game(db, sets_editions=sets_editions)
    assert CardSet.ADVENTURES in game.sets_used


def test_landscape_cards_sorted_by_cost_then_name(db: CardDatabase) -> None:
    sets_editions = {(CardSet.ADVENTURES, CardSetEdition.FIRST_EDITION)}
    seed = _find_seed(
        db,
        sets_editions,
        lambda g: any(CardType.EVENT in c.types for c in g.landscapes),
    )
    if seed is None:
        pytest.skip("no seed found with at least one Event as a landscape card")
    random.seed(seed)
    game = generate_game(db, sets_editions=sets_editions)
    keys = [(card.cost.coins, card.cost.potion, card.name) for card in game.landscapes]
    assert keys == sorted(keys)


def test_event_estate_token_detected(db: CardDatabase) -> None:
    # Inheritance says "Move your Estate token to it." — ESTATE_TOKEN must appear.
    sets_editions = {(CardSet.ADVENTURES, CardSetEdition.FIRST_EDITION)}
    seed = _find_seed(
        db,
        sets_editions,
        lambda g: any(c.name == "Inheritance" for c in g.landscapes),
        max_seeds=500,
    )
    if seed is None:
        pytest.skip("no seed found with Inheritance as a landscape card")
    random.seed(seed)
    game = generate_game(db, sets_editions=sets_editions)
    assert Material.ESTATE_TOKEN in game.materials


def test_event_minus_one_coin_token_detected(db: CardDatabase) -> None:
    # Ball says "Take your -$1 token." — MINUS_ONE_COIN_TOKEN must appear.
    sets_editions = {(CardSet.ADVENTURES, CardSetEdition.FIRST_EDITION)}
    seed = _find_seed(
        db,
        sets_editions,
        lambda g: any(c.name == "Ball" for c in g.landscapes),
        max_seeds=500,
    )
    if seed is None:
        pytest.skip("no seed found with Ball as a landscape card")
    random.seed(seed)
    game = generate_game(db, sets_editions=sets_editions)
    assert Material.MINUS_ONE_COIN_TOKEN in game.materials


def test_event_minus_one_card_token_detected(db: CardDatabase) -> None:
    # Raid says "puts their -1 Card token on their deck."
    sets_editions = {(CardSet.ADVENTURES, CardSetEdition.FIRST_EDITION)}
    seed = _find_seed(
        db,
        sets_editions,
        lambda g: any(c.name == "Raid" for c in g.landscapes),
        max_seeds=500,
    )
    if seed is None:
        pytest.skip("no seed found with Raid as a landscape card")
    random.seed(seed)
    game = generate_game(db, sets_editions=sets_editions)
    assert Material.MINUS_ONE_CARD_TOKEN in game.materials


def test_event_plus_one_action_token_detected(db: CardDatabase) -> None:
    # Lost Arts says "Move your +1 Action token to an Action Supply pile."
    sets_editions = {(CardSet.ADVENTURES, CardSetEdition.FIRST_EDITION)}
    seed = _find_seed(
        db,
        sets_editions,
        lambda g: any(c.name == "Lost Arts" for c in g.landscapes),
        max_seeds=500,
    )
    if seed is None:
        pytest.skip("no seed found with Lost Arts as a landscape card")
    random.seed(seed)
    game = generate_game(db, sets_editions=sets_editions)
    assert Material.PLUS_ONE_ACTION_TOKEN in game.materials


def test_event_journey_token_detected_from_pilgrimage(db: CardDatabase) -> None:
    # Pilgrimage says "Turn your Journey token over."
    sets_editions = {(CardSet.ADVENTURES, CardSetEdition.FIRST_EDITION)}
    seed = _find_seed(
        db,
        sets_editions,
        lambda g: any(c.name == "Pilgrimage" for c in g.landscapes),
        max_seeds=500,
    )
    if seed is None:
        pytest.skip("no seed found with Pilgrimage as a landscape card")
    random.seed(seed)
    game = generate_game(db, sets_editions=sets_editions)
    assert Material.JOURNEY_TOKEN in game.materials


# Artifact → the Kingdom card that makes it available
ARTIFACT_PAIRS: dict[str, str] = {
    "Flag Bearer": "Flag",
    "Treasurer": "Key",
    "Swashbuckler": "Treasure Chest",
}


def test_renaissance_set_only(db: CardDatabase) -> None:
    game = generate_game(
        db, sets_editions={(CardSet.RENAISSANCE, CardSetEdition.FIRST_EDITION)}
    )
    assert len(game.kingdom_cards) == 10
    for card in game.kingdom_cards:
        assert card.set == CardSet.RENAISSANCE


def test_renaissance_sets_used(db: CardDatabase) -> None:
    game = generate_game(
        db, sets_editions={(CardSet.RENAISSANCE, CardSetEdition.FIRST_EDITION)}
    )
    assert CardSet.RENAISSANCE in game.sets_used


def test_mixed_base_2e_renaissance(db: CardDatabase) -> None:
    game = generate_game(
        db,
        sets_editions={
            (CardSet.BASE, CardSetEdition.SECOND_EDITION),
            (CardSet.RENAISSANCE, CardSetEdition.FIRST_EDITION),
        },
    )
    names = {card.name for card in game.kingdom_cards}
    assert not names & BASE_1E_ONLY


def test_renaissance_project_appears_in_landscapes(db: CardDatabase) -> None:
    sets_editions = {(CardSet.RENAISSANCE, CardSetEdition.FIRST_EDITION)}
    seed = _find_seed(
        db,
        sets_editions,
        lambda g: any(CardType.PROJECT in c.types for c in g.landscapes),
    )
    if seed is None:
        pytest.skip("no seed found with a Project in landscapes")
    random.seed(seed)
    game = generate_game(db, sets_editions=sets_editions)
    assert any(CardType.PROJECT in c.types for c in game.landscapes)


def test_wooden_cubes_with_project(db: CardDatabase) -> None:
    sets_editions = {(CardSet.RENAISSANCE, CardSetEdition.FIRST_EDITION)}
    seed = _find_seed(
        db,
        sets_editions,
        lambda g: any(CardType.PROJECT in c.types for c in g.landscapes),
    )
    if seed is None:
        pytest.skip("no seed found with a Project in landscapes")
    random.seed(seed)
    game = generate_game(db, sets_editions=sets_editions)
    assert Material.WOODEN_CUBES in game.materials


def test_no_wooden_cubes_without_project(db: CardDatabase) -> None:
    # Base 2E has no Projects — wooden cubes should never appear.
    game = generate_game(
        db, sets_editions={(CardSet.BASE, CardSetEdition.SECOND_EDITION)}
    )
    assert Material.WOODEN_CUBES not in game.materials


def test_project_not_in_kingdom_piles(db: CardDatabase) -> None:
    sets_editions = {(CardSet.RENAISSANCE, CardSetEdition.FIRST_EDITION)}
    seed = _find_seed(
        db,
        sets_editions,
        lambda g: any(CardType.PROJECT in c.types for c in g.landscapes),
    )
    if seed is None:
        pytest.skip("no seed found with a Project in landscapes")
    random.seed(seed)
    game = generate_game(db, sets_editions=sets_editions)
    kingdom_names = {c.name for c in game.kingdom_cards}
    project_names = {c.name for c in game.landscapes if CardType.PROJECT in c.types}
    assert not project_names & kingdom_names


@pytest.mark.parametrize(("kingdom_card", "artifact"), ARTIFACT_PAIRS.items())
def test_artifact_present_with_trigger_card(
    db: CardDatabase, kingdom_card: str, artifact: str
) -> None:
    seed = _find_seed_with_card(
        db, kingdom_card, {(CardSet.RENAISSANCE, CardSetEdition.FIRST_EDITION)}
    )
    if seed is None:
        pytest.skip(f"no seed found with {kingdom_card} in kingdom_piles")
    random.seed(seed)
    game = generate_game(
        db, sets_editions={(CardSet.RENAISSANCE, CardSetEdition.FIRST_EDITION)}
    )
    non_supply_names = {c.name for c in game.non_supply_cards}
    assert artifact in non_supply_names


def test_horn_and_lantern_present_with_border_guard(db: CardDatabase) -> None:
    seed = _find_seed_with_card(
        db, "Border Guard", {(CardSet.RENAISSANCE, CardSetEdition.FIRST_EDITION)}
    )
    if seed is None:
        pytest.skip("no seed found with Border Guard in kingdom_piles")
    random.seed(seed)
    game = generate_game(
        db, sets_editions={(CardSet.RENAISSANCE, CardSetEdition.FIRST_EDITION)}
    )
    non_supply_names = {c.name for c in game.non_supply_cards}
    assert "Horn" in non_supply_names
    assert "Lantern" in non_supply_names


def test_no_artifacts_without_trigger_cards(db: CardDatabase) -> None:
    # Base 2E has none of the Renaissance trigger cards.
    game = generate_game(
        db, sets_editions={(CardSet.BASE, CardSetEdition.SECOND_EDITION)}
    )
    artifact_names = {"Flag", "Horn", "Key", "Lantern", "Treasure Chest"}
    non_supply_names = {c.name for c in game.non_supply_cards}
    assert not artifact_names & non_supply_names


def test_artifacts_not_in_kingdom_piles(db: CardDatabase) -> None:
    sets_editions = {(CardSet.RENAISSANCE, CardSetEdition.FIRST_EDITION)}
    seed = _find_seed_with_card(db, "Flag Bearer", sets_editions)
    if seed is None:
        pytest.skip("no seed found with Flag Bearer in kingdom_piles")
    random.seed(seed)
    game = generate_game(db, sets_editions=sets_editions)
    kingdom_names = {c.name for c in game.kingdom_cards}
    assert "Flag" not in kingdom_names


def test_coffers_material_detected_with_renaissance_treasure(db: CardDatabase) -> None:
    # Ducat, Spices, and Villain all give Coffers; Ducat/Spices are Treasures.
    coffers_cards = {"Ducat", "Villain", "Spices"}
    sets_editions = {(CardSet.RENAISSANCE, CardSetEdition.FIRST_EDITION)}
    seed = _find_seed_with_any_kingdom_card(db, coffers_cards, sets_editions)
    if seed is None:
        pytest.skip("no seed found with a Coffers-giving card in kingdom_piles")
    random.seed(seed)
    game = generate_game(db, sets_editions=sets_editions)
    # Coffers OR Coffers/Villagers mat must be present
    assert (
        Material.COFFERS_MAT in game.materials
        or Material.COFFERS_VILLAGERS_MAT in game.materials
    )
    assert Material.COIN_TOKENS in game.materials


def test_villagers_material_detected_with_renaissance_cards(db: CardDatabase) -> None:
    # Acting Troupe gives +4 Villagers; triggers the Coffers/Villagers mat.
    sets_editions = {(CardSet.RENAISSANCE, CardSetEdition.FIRST_EDITION)}
    seed = _find_seed_with_card(db, "Acting Troupe", sets_editions)
    if seed is None:
        pytest.skip("no seed found with Acting Troupe in kingdom_piles")
    random.seed(seed)
    game = generate_game(db, sets_editions=sets_editions)
    assert Material.COFFERS_VILLAGERS_MAT in game.materials
    assert Material.COIN_TOKENS in game.materials


def test_allies_set_only(db: CardDatabase) -> None:
    game = generate_game(
        db, sets_editions={(CardSet.ALLIES, CardSetEdition.FIRST_EDITION)}
    )
    assert len(game.kingdom_cards) == 10
    for card in game.kingdom_cards:
        assert card.set == CardSet.ALLIES


MENAGERIE_HORSE_GAINERS = {
    # Kingdom cards that can gain Horses
    "Cavalry",
    "Groom",
    "Hostelry",
    "Livery",
    "Paddock",
    "Scrap",
    "Sleigh",
    "Supplies",
    # Events that can gain Horses
    "Bargain",
    "Demand",
    "Ride",
    "Stampede",
}


def test_menagerie_set_only(db: CardDatabase) -> None:
    game = generate_game(
        db, sets_editions={(CardSet.MENAGERIE, CardSetEdition.FIRST_EDITION)}
    )
    assert len(game.kingdom_cards) == 10
    for card in game.kingdom_cards:
        assert card.set == CardSet.MENAGERIE


def test_menagerie_sets_used(db: CardDatabase) -> None:
    game = generate_game(
        db, sets_editions={(CardSet.MENAGERIE, CardSetEdition.FIRST_EDITION)}
    )
    assert game.sets_used == [CardSet.MENAGERIE]


def test_horse_pile_present_with_horse_gaining_card(db: CardDatabase) -> None:
    sets_editions = {(CardSet.MENAGERIE, CardSetEdition.FIRST_EDITION)}
    seed = _find_seed(
        db,
        sets_editions,
        lambda g: bool(
            ({c.name for c in g.kingdom_cards} | {c.name for c in g.landscapes})
            & MENAGERIE_HORSE_GAINERS
        ),
    )
    if seed is None:
        pytest.skip("no seed found with a Horse-gaining card selected")
    random.seed(seed)
    game = generate_game(db, sets_editions=sets_editions)
    assert any(c.name == "Horse" for c in game.non_supply_cards)


def test_horse_pile_not_in_kingdom(db: CardDatabase) -> None:
    sets_editions = {(CardSet.MENAGERIE, CardSetEdition.FIRST_EDITION)}
    seed = _find_seed(
        db,
        sets_editions,
        lambda g: bool(
            ({c.name for c in g.kingdom_cards} | {c.name for c in g.landscapes})
            & MENAGERIE_HORSE_GAINERS
        ),
    )
    if seed is None:
        pytest.skip("no seed found with a Horse-gaining card selected")
    random.seed(seed)
    game = generate_game(db, sets_editions=sets_editions)
    # Horse is Non-Supply and must never appear as a Kingdom pile
    assert not any(c.name == "Horse" for c in game.kingdom_cards)


def test_no_horse_pile_without_horse_gaining_cards(db: CardDatabase) -> None:
    # Base 2E has no Horse-gaining cards; Horse should never be added.
    game = generate_game(
        db, sets_editions={(CardSet.BASE, CardSetEdition.SECOND_EDITION)}
    )
    assert not any(c.name == "Horse" for c in game.non_supply_cards)


def test_menagerie_exile_mat_detected(db: CardDatabase) -> None:
    # Bounty Hunter has "Exile" in its instructions; playing it needs the Exile mat.
    sets_editions = {(CardSet.MENAGERIE, CardSetEdition.FIRST_EDITION)}
    seed = _find_seed_with_card(db, "Bounty Hunter", sets_editions)
    if seed is None:
        pytest.skip("no seed found with Bounty Hunter in kingdom_piles")
    random.seed(seed)
    game = generate_game(db, sets_editions=sets_editions)
    assert Material.EXILE_MAT in game.materials


def test_menagerie_no_exile_mat_without_exile_card(db: CardDatabase) -> None:
    # Base 2E has no Exile mechanic — Exile mat should never appear.
    game = generate_game(
        db, sets_editions={(CardSet.BASE, CardSetEdition.SECOND_EDITION)}
    )
    assert Material.EXILE_MAT not in game.materials


def test_menagerie_way_of_the_mouse_with_full_db(db: CardDatabase) -> None:
    """Way of the Mouse in a real Menagerie-only game sets aside one card."""
    sets_editions = {(CardSet.MENAGERIE, CardSetEdition.FIRST_EDITION)}
    for seed in range(500):
        random.seed(seed)
        game = generate_game(db, sets_editions=sets_editions)
        if any(c.name == "Way of the Mouse" for c in game.landscapes):
            break
    else:
        pytest.skip("no seed found with Way of the Mouse in landscapes")

    # The set-aside card must be a non-Duration Action costing $2 or $3
    mouse_piles = [
        p
        for p in game.non_supply_piles
        if any(m.kind == PileMarkKind.WAY_OF_THE_MOUSE for m in p.marks)
    ]
    assert len(mouse_piles) == 1
    mouse_card = mouse_piles[0].card
    assert CardType.ACTION in mouse_card.types
    assert CardType.DURATION not in mouse_card.types
    assert mouse_card.cost.coins in {2, 3}
    # Must not also appear in the Kingdom
    kingdom_names = {c.name for c in game.kingdom_cards}
    assert mouse_card.name not in kingdom_names


def test_menagerie_landscapes_only_events_and_ways(db: CardDatabase) -> None:
    """All Menagerie landscapes are Events or Ways — no other landscape types."""
    game = generate_game(
        db, sets_editions={(CardSet.MENAGERIE, CardSetEdition.FIRST_EDITION)}
    )
    for landscape in game.landscapes:
        if landscape.set == CardSet.MENAGERIE:
            assert CardType.EVENT in landscape.types or CardType.WAY in landscape.types


def test_menagerie_at_most_2_landscapes_default(db: CardDatabase) -> None:
    game = generate_game(
        db, sets_editions={(CardSet.MENAGERIE, CardSetEdition.FIRST_EDITION)}
    )
    assert len(game.landscapes) <= 2


def test_menagerie_mixed_with_base(db: CardDatabase) -> None:
    game = generate_game(
        db,
        sets_editions={
            (CardSet.BASE, CardSetEdition.SECOND_EDITION),
            (CardSet.MENAGERIE, CardSetEdition.FIRST_EDITION),
        },
    )
    for card in game.kingdom_cards:
        assert card.set in {CardSet.BASE, CardSet.MENAGERIE}


def test_menagerie_stockpile_is_treasure(db: CardDatabase) -> None:
    """Stockpile is a Treasure Kingdom card — verify it appears correctly."""
    sets_editions = {(CardSet.MENAGERIE, CardSetEdition.FIRST_EDITION)}
    seed = _find_seed_with_card(db, "Stockpile", sets_editions)
    if seed is None:
        pytest.skip("no seed found with Stockpile in kingdom_piles")
    random.seed(seed)
    game = generate_game(db, sets_editions=sets_editions)
    stockpile = next(c for c in game.kingdom_cards if c.name == "Stockpile")
    assert CardType.TREASURE in stockpile.types
    # Stockpile Exiles itself → Exile mat required
    assert Material.EXILE_MAT in game.materials


def test_allies_sets_used(db: CardDatabase) -> None:
    game = generate_game(
        db, sets_editions={(CardSet.ALLIES, CardSetEdition.FIRST_EDITION)}
    )
    assert CardSet.ALLIES in game.sets_used


def test_mixed_base_2e_allies(db: CardDatabase) -> None:
    game = generate_game(
        db,
        sets_editions={
            (CardSet.BASE, CardSetEdition.SECOND_EDITION),
            (CardSet.ALLIES, CardSetEdition.FIRST_EDITION),
        },
    )
    names = {card.name for card in game.kingdom_cards}
    assert not names & BASE_1E_ONLY


def test_ally_landscape_appears_in_landscapes(db: CardDatabase) -> None:
    sets_editions = {(CardSet.ALLIES, CardSetEdition.FIRST_EDITION)}
    seed = _find_seed(db, sets_editions, lambda g: g.ally is not None)
    if seed is None:
        pytest.skip("no seed found with an Ally-type landscape card")
    random.seed(seed)
    game = generate_game(db, sets_editions=sets_editions)
    assert game.ally is not None
    assert CardType.ALLY in game.ally.types


def test_ally_landscape_not_in_kingdom_piles(db: CardDatabase) -> None:
    sets_editions = {(CardSet.ALLIES, CardSetEdition.FIRST_EDITION)}
    seed = _find_seed(db, sets_editions, lambda g: g.ally is not None)
    if seed is None:
        pytest.skip("no seed found with an Ally-type landscape card")
    random.seed(seed)
    game = generate_game(db, sets_editions=sets_editions)
    kingdom_names = {c.name for c in game.kingdom_cards}
    assert game.ally is not None
    ally_name = game.ally.name
    assert ally_name not in kingdom_names


def test_allies_can_generate_both_ally_and_kingdom_cards(db: CardDatabase) -> None:
    # Verify we can get both an Ally landscape and kingdom piles from Allies.
    sets_editions = {(CardSet.ALLIES, CardSetEdition.FIRST_EDITION)}
    found_ally_landscape = False
    found_kingdom = False
    for seed in range(500):
        random.seed(seed)
        game = generate_game(db, sets_editions=sets_editions)
        if game.ally:
            found_ally_landscape = True
        if game.kingdom_cards:
            found_kingdom = True
        if found_ally_landscape and found_kingdom:
            break
    assert found_ally_landscape, "Expected at least one Ally landscape across seeds"
    assert found_kingdom, "Expected kingdom piles from Allies set"


# Kingdom cards with Liaison type in the Allies set
LIAISON_KINGDOM_CARDS = {
    "Bauble",
    "Broker",
    "Contract",
    "Emissary",
    "Guildmaster",
    "Highwayman",
    "Importer",
    "Skirmisher",
    "Sycophant",
    "Underling",
}


def test_favors_mat_detected_with_liaison_card(db: CardDatabase) -> None:
    sets_editions = {(CardSet.ALLIES, CardSetEdition.FIRST_EDITION)}
    seed = _find_seed_with_any_kingdom_card(db, LIAISON_KINGDOM_CARDS, sets_editions)
    if seed is None:
        pytest.skip("no seed found with a Liaison kingdom card")
    random.seed(seed)
    game = generate_game(db, sets_editions=sets_editions)
    assert Material.FAVORS_MAT in game.materials
    assert Material.COIN_TOKENS in game.materials


def test_no_favors_mat_without_liaison_cards(db: CardDatabase) -> None:
    # Base 2E has no Liaison cards — Favors mat should never appear.
    game = generate_game(
        db, sets_editions={(CardSet.BASE, CardSetEdition.SECOND_EDITION)}
    )
    assert Material.FAVORS_MAT not in game.materials


ALLIES_MIXED_PILES = {
    "Augurs",
    "Clashes",
    "Forts",
    "Odysseys",
    "Townsfolk",
    "Wizards",
}


def test_mixed_pile_setup_instruction_when_selected(db: CardDatabase) -> None:
    sets_editions = {(CardSet.ALLIES, CardSetEdition.FIRST_EDITION)}
    seed = _find_seed_with_any_kingdom_card(db, ALLIES_MIXED_PILES, sets_editions)
    if seed is None:
        pytest.skip("no seed found with an Allies mixed pile in kingdom_piles")
    random.seed(seed)
    game = generate_game(db, sets_editions=sets_editions)
    selected_mixed = ALLIES_MIXED_PILES & {c.name for c in game.kingdom_cards}
    for name in selected_mixed:
        assert any(name in instr for instr in game.setup_instructions), (
            f"Expected setup instruction for mixed pile {name}"
        )


def test_augurs_setup_instruction(db: CardDatabase) -> None:
    sets_editions = {(CardSet.ALLIES, CardSetEdition.FIRST_EDITION)}
    seed = _find_seed_with_card(db, "Augurs", sets_editions)
    if seed is None:
        pytest.skip("no seed found with Augurs in kingdom_piles")
    random.seed(seed)
    game = generate_game(db, sets_editions=sets_editions)
    assert any("Augurs" in instr for instr in game.setup_instructions)


def test_clashes_setup_instruction(db: CardDatabase) -> None:
    sets_editions = {(CardSet.ALLIES, CardSetEdition.FIRST_EDITION)}
    seed = _find_seed_with_card(db, "Clashes", sets_editions)
    if seed is None:
        pytest.skip("no seed found with Clashes in kingdom_piles")
    random.seed(seed)
    game = generate_game(db, sets_editions=sets_editions)
    assert any("Clashes" in instr for instr in game.setup_instructions)


def test_forts_setup_instruction(db: CardDatabase) -> None:
    sets_editions = {(CardSet.ALLIES, CardSetEdition.FIRST_EDITION)}
    seed = _find_seed_with_card(db, "Forts", sets_editions)
    if seed is None:
        pytest.skip("no seed found with Forts in kingdom_piles")
    random.seed(seed)
    game = generate_game(db, sets_editions=sets_editions)
    assert any("Forts" in instr for instr in game.setup_instructions)


def test_odysseys_setup_instruction(db: CardDatabase) -> None:
    sets_editions = {(CardSet.ALLIES, CardSetEdition.FIRST_EDITION)}
    seed = _find_seed_with_card(db, "Odysseys", sets_editions)
    if seed is None:
        pytest.skip("no seed found with Odysseys in kingdom_piles")
    random.seed(seed)
    game = generate_game(db, sets_editions=sets_editions)
    assert any("Odysseys" in instr for instr in game.setup_instructions)


def test_townsfolk_setup_instruction(db: CardDatabase) -> None:
    sets_editions = {(CardSet.ALLIES, CardSetEdition.FIRST_EDITION)}
    seed = _find_seed_with_card(db, "Townsfolk", sets_editions)
    if seed is None:
        pytest.skip("no seed found with Townsfolk in kingdom_piles")
    random.seed(seed)
    game = generate_game(db, sets_editions=sets_editions)
    assert any("Townsfolk" in instr for instr in game.setup_instructions)


def test_wizards_setup_instruction(db: CardDatabase) -> None:
    sets_editions = {(CardSet.ALLIES, CardSetEdition.FIRST_EDITION)}
    seed = _find_seed_with_card(db, "Wizards", sets_editions)
    if seed is None:
        pytest.skip("no seed found with Wizards in kingdom_piles")
    random.seed(seed)
    game = generate_game(db, sets_editions=sets_editions)
    assert any("Wizards" in instr for instr in game.setup_instructions)


def test_importer_setup_instruction(db: CardDatabase) -> None:
    # Importer has "Setup: Each player gets +4 Favors." — must appear in instructions.
    sets_editions = {(CardSet.ALLIES, CardSetEdition.FIRST_EDITION)}
    seed = _find_seed_with_card(db, "Importer", sets_editions)
    if seed is None:
        pytest.skip("no seed found with Importer in kingdom_piles")
    random.seed(seed)
    game = generate_game(db, sets_editions=sets_editions)
    assert any("Importer" in instr for instr in game.setup_instructions)


# Kingdom cards that cause Loot to be set out (instructions contain "Loot")
PLUNDER_LOOT_TRIGGERING_KINGDOM_CARDS = {
    "Cutthroat",
    "Jewelled Egg",
    "Pickaxe",
    "Sack of Loot",
    "Search",
    "Wealthy Village",
}

# Events (landscape cards) that cause Loot to be set out
PLUNDER_LOOT_TRIGGERING_EVENTS = {
    "Foray",
    "Invasion",
    "Looting",
    "Peril",
    "Prosper",
}

# All 15 Loot cards by name
PLUNDER_ALL_LOOT_NAMES = {
    "Amphora",
    "Doubloons",
    "Endless Chalice",
    "Figurehead",
    "Hammer",
    "Insignia",
    "Jewels",
    "Orb",
    "Prize Goat",
    "Puzzle Box",
    "Sextant",
    "Shield",
    "Spell Scroll",
    "Staff",
    "Sword",
}


def test_plunder_set_only(db: CardDatabase) -> None:
    game = generate_game(
        db, sets_editions={(CardSet.PLUNDER, CardSetEdition.FIRST_EDITION)}
    )
    assert len(game.kingdom_cards) == 10
    for card in game.kingdom_cards:
        assert card.set == CardSet.PLUNDER


def test_plunder_sets_used(db: CardDatabase) -> None:
    game = generate_game(
        db, sets_editions={(CardSet.PLUNDER, CardSetEdition.FIRST_EDITION)}
    )
    assert CardSet.PLUNDER in game.sets_used


def test_mixed_base_2e_plunder(db: CardDatabase) -> None:
    game = generate_game(
        db,
        sets_editions={
            (CardSet.BASE, CardSetEdition.SECOND_EDITION),
            (CardSet.PLUNDER, CardSetEdition.FIRST_EDITION),
        },
    )
    names = {card.name for card in game.kingdom_cards}
    assert not names & BASE_1E_ONLY


def test_loot_present_with_loot_triggering_kingdom_card(db: CardDatabase) -> None:
    sets_editions = {(CardSet.PLUNDER, CardSetEdition.FIRST_EDITION)}
    seed = _find_seed_with_any_kingdom_card(
        db, PLUNDER_LOOT_TRIGGERING_KINGDOM_CARDS, sets_editions
    )
    if seed is None:
        pytest.skip(
            "no seed found with a Loot-triggering kingdom card in kingdom_piles"
        )
    random.seed(seed)
    game = generate_game(db, sets_editions=sets_editions)
    non_supply_names = {c.name for c in game.non_supply_cards}
    assert "Loot" in non_supply_names


def test_loot_present_with_loot_triggering_event(db: CardDatabase) -> None:
    sets_editions = {(CardSet.PLUNDER, CardSetEdition.FIRST_EDITION)}
    seed = _find_seed(
        db,
        sets_editions,
        lambda g: any(c.name in PLUNDER_LOOT_TRIGGERING_EVENTS for c in g.landscapes),
    )
    if seed is None:
        pytest.skip("no seed found with a Loot-triggering event in landscapes")
    random.seed(seed)
    game = generate_game(db, sets_editions=sets_editions)
    non_supply_names = {c.name for c in game.non_supply_cards}
    assert "Loot" in non_supply_names


def test_loot_present_with_cursed_trait(db: CardDatabase) -> None:
    # Cursed trait says "When you gain a Cursed card, gain a Loot and a Curse."
    sets_editions = {(CardSet.PLUNDER, CardSetEdition.FIRST_EDITION)}
    seed = _find_seed(
        db, sets_editions, lambda g: any(c.name == "Cursed" for c in g.landscapes)
    )
    if seed is None:
        pytest.skip("no seed found with Cursed trait in landscapes")
    random.seed(seed)
    game = generate_game(db, sets_editions=sets_editions)
    non_supply_names = {c.name for c in game.non_supply_cards}
    assert "Loot" in non_supply_names


def test_loot_pile_present_when_triggered(db: CardDatabase) -> None:
    sets_editions = {(CardSet.PLUNDER, CardSetEdition.FIRST_EDITION)}
    seed = _find_seed_with_any_kingdom_card(
        db, PLUNDER_LOOT_TRIGGERING_KINGDOM_CARDS, sets_editions
    )
    if seed is None:
        pytest.skip("no seed found with a Loot-triggering kingdom card")
    random.seed(seed)
    game = generate_game(db, sets_editions=sets_editions)
    loot_piles = [c for c in game.non_supply_cards if CardType.LOOT in c.types]
    assert len(loot_piles) == 1
    assert loot_piles[0].name == "Loot"


def test_loot_cards_not_in_kingdom_piles(db: CardDatabase) -> None:
    sets_editions = {(CardSet.PLUNDER, CardSetEdition.FIRST_EDITION)}
    seed = _find_seed_with_any_kingdom_card(
        db, PLUNDER_LOOT_TRIGGERING_KINGDOM_CARDS, sets_editions
    )
    if seed is None:
        pytest.skip("no seed found with a Loot-triggering kingdom card")
    random.seed(seed)
    game = generate_game(db, sets_editions=sets_editions)
    kingdom_names = {c.name for c in game.kingdom_cards}
    assert not PLUNDER_ALL_LOOT_NAMES & kingdom_names


def test_no_loot_without_loot_triggering_cards(db: CardDatabase) -> None:
    # Base 2E has no cards that reference gaining Loot.
    game = generate_game(
        db, sets_editions={(CardSet.BASE, CardSetEdition.SECOND_EDITION)}
    )
    loot_piles = [c for c in game.non_supply_cards if CardType.LOOT in c.types]
    assert loot_piles == []


def test_loot_sorted_by_name_in_non_supply(db: CardDatabase) -> None:
    sets_editions = {(CardSet.PLUNDER, CardSetEdition.FIRST_EDITION)}
    seed = _find_seed_with_any_kingdom_card(
        db, PLUNDER_LOOT_TRIGGERING_KINGDOM_CARDS, sets_editions
    )
    if seed is None:
        pytest.skip("no seed found with a Loot-triggering kingdom card")
    random.seed(seed)
    game = generate_game(db, sets_editions=sets_editions)
    loot_piles = [c for c in game.non_supply_cards if CardType.LOOT in c.types]
    names = [c.name for c in loot_piles]
    assert names == sorted(names)


def test_trait_appears_in_landscapes(db: CardDatabase) -> None:
    sets_editions = {(CardSet.PLUNDER, CardSetEdition.FIRST_EDITION)}
    seed = _find_seed(
        db,
        sets_editions,
        lambda g: any(CardType.TRAIT in c.types for c in g.landscapes),
    )
    if seed is None:
        pytest.skip("no seed found with a Trait in landscapes")
    random.seed(seed)
    game = generate_game(db, sets_editions=sets_editions)
    assert any(CardType.TRAIT in c.types for c in game.landscapes)


def test_trait_not_in_kingdom_piles(db: CardDatabase) -> None:
    sets_editions = {(CardSet.PLUNDER, CardSetEdition.FIRST_EDITION)}
    seed = _find_seed(
        db,
        sets_editions,
        lambda g: any(CardType.TRAIT in c.types for c in g.landscapes),
    )
    if seed is None:
        pytest.skip("no seed found with a Trait in landscapes")
    random.seed(seed)
    game = generate_game(db, sets_editions=sets_editions)
    kingdom_names = {c.name for c in game.kingdom_cards}
    trait_names = {c.name for c in game.landscapes if CardType.TRAIT in c.types}
    assert not trait_names & kingdom_names


def test_plunder_can_generate_both_trait_and_event_landscapes(
    db: CardDatabase,
) -> None:
    # Plunder has both Events and Traits as landscape cards.
    sets_editions = {(CardSet.PLUNDER, CardSetEdition.FIRST_EDITION)}
    trait_found = False
    event_found = False
    for seed in range(500):
        random.seed(seed)
        game = generate_game(db, sets_editions=sets_editions)
        for card in game.landscapes:
            if CardType.TRAIT in card.types:
                trait_found = True
            if CardType.EVENT in card.types:
                event_found = True
        if trait_found and event_found:
            break
    assert trait_found, "Expected at least one Trait in landscapes across seeds"
    assert event_found, "Expected at least one Event in landscapes across seeds"


def test_trait_landscape_not_in_kingdom_piles_across_seeds(
    db: CardDatabase,
) -> None:
    # Over multiple seeds, any Trait that appears is always in landscapes, not kingdom.
    sets_editions = {(CardSet.PLUNDER, CardSetEdition.FIRST_EDITION)}
    trait_names_in_landscapes: set[str] = set()
    trait_names_in_kingdom: set[str] = set()
    for seed in range(200):
        random.seed(seed)
        game = generate_game(db, sets_editions=sets_editions)
        trait_names_in_landscapes |= {
            c.name for c in game.landscapes if CardType.TRAIT in c.types
        }
        trait_names_in_kingdom |= {
            c.name for c in game.kingdom_cards if CardType.TRAIT in c.types
        }
    assert trait_names_in_kingdom == set()


def test_plunder_event_appears_in_landscapes(db: CardDatabase) -> None:
    sets_editions = {(CardSet.PLUNDER, CardSetEdition.FIRST_EDITION)}
    seed = _find_seed(
        db,
        sets_editions,
        lambda g: any(CardType.EVENT in c.types for c in g.landscapes),
    )
    if seed is None:
        pytest.skip("no seed found with at least one Event in landscapes")
    random.seed(seed)
    game = generate_game(db, sets_editions=sets_editions)
    assert any(CardType.EVENT in c.types for c in game.landscapes)


def test_plunder_event_not_in_kingdom_piles(db: CardDatabase) -> None:
    sets_editions = {(CardSet.PLUNDER, CardSetEdition.FIRST_EDITION)}
    seed = _find_seed(
        db,
        sets_editions,
        lambda g: any(CardType.EVENT in c.types for c in g.landscapes),
    )
    if seed is None:
        pytest.skip("no seed found with at least one Event in landscapes")
    random.seed(seed)
    game = generate_game(db, sets_editions=sets_editions)
    kingdom_names = {c.name for c in game.kingdom_cards}
    event_names = {c.name for c in game.landscapes if CardType.EVENT in c.types}
    assert not event_names & kingdom_names


def test_rising_sun_set_only(db: CardDatabase) -> None:
    game = generate_game(
        db, sets_editions={(CardSet.RISING_SUN, CardSetEdition.FIRST_EDITION)}
    )
    # Approaching Army prophecy can add an 11th Attack kingdom card when Omen cards are present.
    assert 10 <= len(game.kingdom_cards) <= 11
    for card in game.kingdom_cards:
        assert card.set == CardSet.RISING_SUN


def test_rising_sun_sets_used(db: CardDatabase) -> None:
    game = generate_game(
        db, sets_editions={(CardSet.RISING_SUN, CardSetEdition.FIRST_EDITION)}
    )
    assert game.sets_used == [CardSet.RISING_SUN]


def test_rising_sun_event_appears_in_landscapes(db: CardDatabase) -> None:
    sets_editions = {(CardSet.RISING_SUN, CardSetEdition.FIRST_EDITION)}
    seed = _find_seed(
        db,
        sets_editions,
        lambda g: any(CardType.EVENT in c.types for c in g.landscapes),
    )
    if seed is None:
        pytest.skip("no seed found with a Rising Sun Event in landscapes")
    random.seed(seed)
    game = generate_game(db, sets_editions=sets_editions)
    assert any(CardType.EVENT in c.types for c in game.landscapes)


def test_rising_sun_prophecy_appears_in_landscapes(db: CardDatabase) -> None:
    sets_editions = {(CardSet.RISING_SUN, CardSetEdition.FIRST_EDITION)}
    seed = _find_seed(db, sets_editions, lambda g: g.prophecy is not None)
    if seed is None:
        pytest.skip("no seed found with a Rising Sun Prophecy in landscapes")
    random.seed(seed)
    game = generate_game(db, sets_editions=sets_editions)
    assert game.prophecy is not None
    assert CardType.PROPHECY in game.prophecy.types


def test_rising_sun_event_not_in_kingdom_piles(db: CardDatabase) -> None:
    sets_editions = {(CardSet.RISING_SUN, CardSetEdition.FIRST_EDITION)}
    seed = _find_seed(
        db,
        sets_editions,
        lambda g: any(CardType.EVENT in c.types for c in g.landscapes),
    )
    if seed is None:
        pytest.skip("no seed found with a Rising Sun Event in landscapes")
    random.seed(seed)
    game = generate_game(db, sets_editions=sets_editions)
    kingdom_names = {c.name for c in game.kingdom_cards}
    event_names = {c.name for c in game.landscapes if CardType.EVENT in c.types}
    assert not event_names & kingdom_names


def test_rising_sun_prophecy_not_in_kingdom_piles(db: CardDatabase) -> None:
    sets_editions = {(CardSet.RISING_SUN, CardSetEdition.FIRST_EDITION)}
    seed = _find_seed(db, sets_editions, lambda g: g.prophecy is not None)
    if seed is None:
        pytest.skip("no seed found with a Rising Sun Prophecy in landscapes")
    random.seed(seed)
    game = generate_game(db, sets_editions=sets_editions)
    kingdom_names = {c.name for c in game.kingdom_cards}
    assert game.prophecy is not None
    prophecy_name = game.prophecy.name
    assert prophecy_name not in kingdom_names


def test_rising_sun_omen_cards_trigger_sun_tokens(db: CardDatabase) -> None:
    # Omen cards add Material.SUN_TOKENS. Find a seed where an Omen card appears.
    sets_editions = {(CardSet.RISING_SUN, CardSetEdition.FIRST_EDITION)}
    for seed in range(500):
        random.seed(seed)
        game = generate_game(db, sets_editions=sets_editions)
        if any(CardType.OMEN in c.types for c in game.kingdom_cards):
            assert Material.SUN_TOKENS in game.materials
            return
    pytest.skip("no seed found with an Omen card in kingdom_piles")


def test_rising_sun_debt_cost_card_triggers_debt_tokens(db: CardDatabase) -> None:
    # Cards with debt costs (Artist 8D, Daimyo 6D, Mountain Shrine 5D) trigger Debt tokens.
    # Find a seed where at least one debt-cost kingdom card appears.
    sets_editions = {(CardSet.RISING_SUN, CardSetEdition.FIRST_EDITION)}
    debt_cost_names = {"Artist", "Daimyo", "Mountain Shrine"}
    for seed in range(500):
        random.seed(seed)
        game = generate_game(db, sets_editions=sets_editions)
        if {c.name for c in game.kingdom_cards} & debt_cost_names:
            assert Material.DEBT_TOKENS in game.materials
            return
    pytest.skip("no seed found with a debt-cost kingdom card")


def test_rising_sun_can_generate_both_event_and_prophecy_landscapes(
    db: CardDatabase,
) -> None:
    # Rising Sun has both Events and Prophecies as landscape cards.
    sets_editions = {(CardSet.RISING_SUN, CardSetEdition.FIRST_EDITION)}
    event_found = False
    prophecy_found = False
    for seed in range(500):
        random.seed(seed)
        game = generate_game(db, sets_editions=sets_editions)
        for card in game.landscapes:
            if CardType.EVENT in card.types:
                event_found = True
        if game.prophecy is not None:
            prophecy_found = True
        if event_found and prophecy_found:
            break
    assert event_found, "Expected at least one Event in landscapes across seeds"
    assert prophecy_found, "Expected at least one Prophecy in landscapes across seeds"


def test_obelisk_marks_an_action_pile(db: CardDatabase) -> None:
    sets_editions = {(CardSet.EMPIRES, CardSetEdition.FIRST_EDITION)}
    seed = _find_seed(
        db, sets_editions, lambda g: any(c.name == "Obelisk" for c in g.landscapes)
    )
    if seed is None:
        pytest.skip("no seed found with Obelisk in landscapes")
    random.seed(seed)
    game = generate_game(db, sets_editions=sets_editions)
    obelisk_piles = [
        p
        for p in game.kingdom_piles
        if any(m.kind == PileMarkKind.OBELISK for m in p.marks)
    ]
    assert len(obelisk_piles) == 1
    assert CardType.ACTION in obelisk_piles[0].card.types


def test_obelisk_target_not_in_landscapes(db: CardDatabase) -> None:
    sets_editions = {(CardSet.EMPIRES, CardSetEdition.FIRST_EDITION)}
    seed = _find_seed(
        db, sets_editions, lambda g: any(c.name == "Obelisk" for c in g.landscapes)
    )
    if seed is None:
        pytest.skip("no seed found with Obelisk in landscapes")
    random.seed(seed)
    game = generate_game(db, sets_editions=sets_editions)
    landscape_names = {c.name for c in game.landscapes}
    obelisk_piles = [
        p
        for p in game.kingdom_piles
        if any(m.kind == PileMarkKind.OBELISK for m in p.marks)
    ]
    assert len(obelisk_piles) == 1
    assert obelisk_piles[0].card.name not in landscape_names


def test_way_of_the_mouse_triggers_non_supply_card(
    db: CardDatabase, make_card: CardFactory
) -> None:
    """Way of the Mouse causes a non-Duration Action costing $2-$3 to be set aside."""
    # Build a db with 13 Action kingdom cards (10 get selected, 3 remain as
    # candidates) + Way of the Mouse landscape. Some cards cost $2/$3 so the
    # Way of the Mouse candidate pool is always non-empty.
    basic_cards = [db.get_card_by_name(name) for name in DEFAULT_BASIC_CARD_NAMES]
    way_of_the_mouse = make_card(
        name="Way of the Mouse",
        types=(CardType.WAY,),
        purpose=CardPurpose.LANDSCAPE,
        cost_coins=0,
        set_=CardSet.MENAGERIE,
        editions=(CardSetEdition.FIRST_EDITION,),
        image="Way of the Mouse.jpg",
        instructions="",
    )
    kingdom_cards = [
        make_card(name=f"Card{i}", cost_coins=(i % 4) + 2, image=f"Card{i}.jpg")
        for i in range(13)
    ]
    custom_db = CardDatabase([*basic_cards, way_of_the_mouse, *kingdom_cards])

    # Find a seed that picks Way of the Mouse as a landscape.
    for seed in range(500):
        random.seed(seed)
        game = generate_game(custom_db)
        if any(c.name == "Way of the Mouse" for c in game.landscapes):
            break
    else:
        pytest.skip("no seed found with Way of the Mouse in landscapes")

    # Way of the Mouse should have set aside one card as non-supply.
    assert len(game.non_supply_cards) == 1
    mouse_card = game.non_supply_cards[0]
    assert CardType.ACTION in mouse_card.types
    assert CardType.DURATION not in mouse_card.types
    assert mouse_card.cost.coins in {2, 3}
    # The set-aside card must not also be in kingdom piles.
    kingdom_names = {c.name for c in game.kingdom_cards}
    assert mouse_card.name not in kingdom_names


def test_no_way_of_the_mouse_non_supply_without_trigger(db: CardDatabase) -> None:
    # Base 2E has no Way of the Mouse — no card should be set aside for it.
    game = generate_game(
        db, sets_editions={(CardSet.BASE, CardSetEdition.SECOND_EDITION)}
    )
    # There should be no PileMarkKind.WAY_OF_THE_MOUSE-marked piles.
    assert not any(
        any(m.kind == PileMarkKind.WAY_OF_THE_MOUSE for m in pile.marks)
        for pile in game.non_supply_piles
    )


def test_approaching_army_adds_attack_pile(db: CardDatabase) -> None:
    sets_editions = {(CardSet.RISING_SUN, CardSetEdition.FIRST_EDITION)}
    seed = _find_seed(
        db,
        sets_editions,
        lambda g: g.prophecy is not None and g.prophecy.name == "Approaching Army",
        max_seeds=2000,
    )
    if seed is None:
        pytest.skip("no seed found with Approaching Army prophecy selected")
    random.seed(seed)
    game = generate_game(db, sets_editions=sets_editions)
    assert game.prophecy is not None
    assert game.prophecy.name == "Approaching Army"
    # An Attack kingdom card should have been added (total 11 piles).
    assert len(game.kingdom_cards) == 11
    approaching_army_piles = [
        p
        for p in game.kingdom_piles
        if any(m.kind == PileMarkKind.APPROACHING_ARMY for m in p.marks)
    ]
    assert len(approaching_army_piles) == 1
    assert CardType.ATTACK in approaching_army_piles[0].card.types


def test_approaching_army_added_card_not_in_landscapes(db: CardDatabase) -> None:
    sets_editions = {(CardSet.RISING_SUN, CardSetEdition.FIRST_EDITION)}
    seed = _find_seed(
        db,
        sets_editions,
        lambda g: g.prophecy is not None and g.prophecy.name == "Approaching Army",
        max_seeds=2000,
    )
    if seed is None:
        pytest.skip("no seed found with Approaching Army prophecy selected")
    random.seed(seed)
    game = generate_game(db, sets_editions=sets_editions)
    landscape_names = {c.name for c in game.landscapes}
    approaching_army_piles = [
        p
        for p in game.kingdom_piles
        if any(m.kind == PileMarkKind.APPROACHING_ARMY for m in p.marks)
    ]
    assert len(approaching_army_piles) == 1
    assert approaching_army_piles[0].card.name not in landscape_names


def test_no_approaching_army_without_omen_cards(db: CardDatabase) -> None:
    # Base 2E has no Omen cards — Approaching Army can never be triggered.
    game = generate_game(
        db, sets_editions={(CardSet.BASE, CardSetEdition.SECOND_EDITION)}
    )
    assert game.prophecy is None
    assert not any(
        any(m.kind == PileMarkKind.APPROACHING_ARMY for m in p.marks)
        for p in game.kingdom_piles
    )
