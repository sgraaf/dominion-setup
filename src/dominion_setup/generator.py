"""Generate a complete Dominion game setup."""

from __future__ import annotations

import random
import re
from collections import defaultdict
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable

from .models import (
    DEFAULT_BASIC_CARD_NAMES,
    MATERIAL_ORDER,
    SELECTABLE_LANDSCAPE_TYPES,
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
)
from .utils import card_sort_key

KINGDOM_PILE_COUNT = 10

# Compiled regex patterns used for material / special-pile detection.
GAIN_LOOT_PATTERN = re.compile(r"[gG]ain a Loot")
GAIN_HORSES_PATTERN = re.compile(r"[gG]ains? (?:a|that many|\d+) Horses?")
COFFERS_PATTERN = re.compile(r"\+\d+ Coffers")
VILLAGERS_PATTERN = re.compile(r"\+\d+ Villagers")
EXILE_PATTERN = re.compile(r"Exile")
VP_PLUS_PATTERN = re.compile(r"\+\d+ VP")
VP_SETUP_PATTERN = re.compile(r"Setup: Put \d+ VP")
MINUS_ONE_COIN_PATTERN = re.compile(r"-\$1 token")
DEBT_PATTERN = re.compile(r"\d+D")
HEIRLOOM_PATTERN = re.compile(r"Heirloom: (.*)$")
SETUP_PATTERN = re.compile(r"(Setup: .*$)")


def _pick_special_card(
    candidate_cards: set[Card],
    predicate: Callable[[Card], bool],
    error_msg: str,
    selected_cards_names: set[str],
) -> Card:
    """Pick one card matching *predicate* from *candidate_cards*.

    Raises ``ValueError`` with *error_msg* if no candidates exist.
    Removes the chosen card from *candidate_cards* and registers its name in
    *selected_cards_names* before returning it.
    """
    candidates = [c for c in candidate_cards if predicate(c)]
    if not candidates:
        raise ValueError(error_msg)
    card = random.choice(candidates)
    selected_cards_names.add(card.name)
    candidate_cards.discard(card)
    return card


def generate_game(  # noqa: C901, PLR0912, PLR0913, PLR0915
    db: CardDatabase,
    *,
    sets_editions: set[tuple[CardSet, CardSetEdition]] | None = None,
    sort_order: KingdomSortOrder = KingdomSortOrder.COST,
    use_colony: bool | None = None,
    use_shelters: bool | None = None,
    max_landscapes: int = 2,
) -> Game:
    """Generate a complete, rules-accurate Dominion game setup.

    Args:
        db: The loaded card database.
        sets_editions: Which sets and editions to draw kingdom cards from.
            Defaults to all sets and editions in the database.
        sort_order: How to sort the kingdom piles in the output.
            Defaults to ``KingdomSortOrder.COST``.
        use_colony: Force Platinum/Colony on or off. ``None`` uses the
            standard random determination based on Prosperity cards.
        use_shelters: Force Shelters on or off. ``None`` uses the standard
            random determination based on Dark Ages cards.
        max_landscapes: Maximum number of landscapes to include. Defaults to 2.

    Returns:
        A Game object with selected Kingdom piles and basic supply.
    """
    # ── Kingdom piles & Landscapes ──────────────────────────────────────────
    # build pool of candidate cards by possibly filtering on set and edition
    if sets_editions is not None:
        candidate_cards = {
            card
            for set_, edition in sets_editions
            for card in db.get_cards_by_set_edition(set_, edition=edition)
        }
        candidate_landscapes = {
            card
            for set_, edition in sets_editions
            for card in db.landscape_cards.values()
            if card.set == set_
            and edition in card.editions
            and SELECTABLE_LANDSCAPE_TYPES & set(card.types)
        }
    else:
        candidate_cards = set(db.kingdom_cards.values())
        candidate_landscapes = {
            card
            for card in db.landscape_cards.values()
            if SELECTABLE_LANDSCAPE_TYPES & set(card.types)
        }

    # if there are not enough candidate cards (should never happen), raise an
    # error
    if len(candidate_cards) < KINGDOM_PILE_COUNT:
        msg = f"Not enough kingdom cards: need {KINGDOM_PILE_COUNT}, found {len(candidate_cards)}"
        raise ValueError(msg)

    # initialize card containers
    basic_cards: list[Card] = []
    kingdom_cards: set[Card] = set()
    non_supply_cards: list[Card] = []
    landscapes: set[Card] = set()

    # marks accumulated per Kingdom and Non-Supply card; materialised into Pile
    # objects below
    kingdom_marks: dict[Card, list[PileMark]] = defaultdict(list)
    non_supply_marks: dict[Card, list[PileMark]] = defaultdict(list)

    # select 10 random Kingdom piles and at most ``max_landscapes`` Landscapes
    while len(kingdom_cards) < KINGDOM_PILE_COUNT:
        drawn_card: Card = random.choice(tuple(candidate_cards | candidate_landscapes))
        if drawn_card.purpose == CardPurpose.LANDSCAPE:
            if len(landscapes) < max_landscapes:
                landscapes.add(drawn_card)
            candidate_landscapes.remove(drawn_card)
        else:
            kingdom_cards.add(drawn_card)
            candidate_cards.remove(drawn_card)

    # remove Kingdom piles from candidate cards
    candidate_cards -= kingdom_cards

    # keep track of the names of all selected cards
    selected_cards_names: set[str] = {card.name for card in kingdom_cards | landscapes}

    # ── Special piles ───────────────────────────────────────────────────────
    # in games using Young Witch, choose an additional Kingdom card costing $2
    # or $3, and put its pile into the Supply. This is the "Bane" pile.
    bane_card: Card | None = None
    if "Young Witch" in selected_cards_names:
        bane_card = _pick_special_card(
            candidate_cards,
            lambda c: c.cost in {CardCost(coins=2), CardCost(coins=3)},
            "No eligible Bane card (Kingdom card costing $2-$3) available for Young Witch",
            selected_cards_names,
        )
        kingdom_cards.add(bane_card)
        kingdom_marks[bane_card].append(PileMark(PileMarkKind.BANE))

    # in games using Ferryman, choose an additional Kingdom card costing $3 or
    # $4, and put its pile near the Supply. This pile is not part of the
    # Supply.
    ferryman_card: Card | None = None
    if "Ferryman" in selected_cards_names:
        ferryman_card = _pick_special_card(
            candidate_cards,
            lambda c: c.cost in {CardCost(coins=3), CardCost(coins=4)},
            "No eligible Ferryman card (kingdom card costing $3-$4) available for Ferryman",
            selected_cards_names,
        )
        non_supply_cards.append(ferryman_card)
        non_supply_marks[ferryman_card].append(PileMark(PileMarkKind.FERRYMAN))

    # in games using Way of the Mouse, set aside an unused non-Duration Action
    # costing $2 or $3
    way_of_the_mouse_card: Card | None = None
    if "Way of the Mouse" in selected_cards_names:
        way_of_the_mouse_card = _pick_special_card(
            candidate_cards,
            lambda c: (
                c.cost in {CardCost(coins=2), CardCost(coins=3)}
                and CardType.ACTION in c.types
                and CardType.DURATION not in c.types
            ),
            "No eligible Way of the Mouse card (non-Duration Action kingdom card costing $2-$3) available for Way of the Mouse",
            selected_cards_names,
        )
        non_supply_cards.append(way_of_the_mouse_card)
        non_supply_marks[way_of_the_mouse_card].append(
            PileMark(PileMarkKind.WAY_OF_THE_MOUSE)
        )

    # in games using Riverboat, set aside an unused non-Duration Action costing
    # $5
    riverboat_card: Card | None = None
    if "Riverboat" in selected_cards_names:
        riverboat_card = _pick_special_card(
            candidate_cards,
            lambda c: (
                c.cost == CardCost(coins=5)
                and CardType.ACTION in c.types
                and CardType.DURATION not in c.types
            ),
            "No eligible Riverboat card (non-Duration Action kingdom card costing $5) available for Riverboat",
            selected_cards_names,
        )
        non_supply_cards.append(riverboat_card)
        non_supply_marks[riverboat_card].append(PileMark(PileMarkKind.RIVERBOAT))

    # if Druid is being used, deal three Boon cards face up for use with it.
    druid_boons: list[Card] = []
    if "Druid" in selected_cards_names:
        boons = [
            card for card in db.mixed_pile_cards.values() if CardType.BOON in card.types
        ]
        druid_boons = random.sample(boons, 3)

    # in any game using Liaisons, exactly one Ally is chosen, and it determines
    # what effect Favor tokens have in that game.
    ally: Card | None = None
    if any(CardType.LIAISON in card.types for card in kingdom_cards):
        ally = random.choice(
            [
                card
                for card in db.landscape_cards.values()
                if CardType.ALLY in card.types
            ]
        )

    # in every game with one or more Omen cards, deal out one Prophecy for it.
    # Only use one Prophecy no matter how many Omens you have.
    prophecy: Card | None = None
    if any(CardType.OMEN in card.types for card in kingdom_cards):
        prophecy = random.choice(
            [
                card
                for card in db.landscape_cards.values()
                if CardType.PROPHECY in card.types
            ]
        )

    # in games using Approaching Army, add an Attack Kingdom card to the Supply
    approaching_army_card: Card | None = None
    if prophecy is not None and prophecy.name == "Approaching Army":
        approaching_army_card = _pick_special_card(
            candidate_cards,
            lambda c: CardType.ATTACK in c.types,
            "No eligible Approaching Army card (Attack kingdom card) available for Approaching Army",
            selected_cards_names,
        )
        kingdom_cards.add(approaching_army_card)
        kingdom_marks[approaching_army_card].append(
            PileMark(PileMarkKind.APPROACHING_ARMY)
        )

    # each Trait landscape applies to a different randomly chosen non-Trait
    # Action or Treasure Supply pile.
    trait_landscapes = [
        landscape for landscape in landscapes if CardType.TRAIT in landscape.types
    ]
    if trait_landscapes:
        trait_eligible_cards = [
            card
            for card in kingdom_cards
            if {CardType.ACTION, CardType.TREASURE} & set(card.types)
        ]
        if len(trait_eligible_cards) < len(trait_landscapes):
            msg = f"Not enough Action/Treasure kingdom piles ({len(trait_eligible_cards)}) for {len(trait_landscapes)} Trait landscape(s)"
            raise ValueError(msg)
        trait_targets = random.sample(trait_eligible_cards, len(trait_landscapes))
        for target, trait in zip(trait_targets, trait_landscapes, strict=True):
            kingdom_marks[target].append(PileMark(PileMarkKind.TRAIT, trait=trait))

    # ── Non-Supply piles ────────────────────────────────────────────────────
    # in games using Joust, set the Rewards out near the Supply. These are not
    # in the Supply.
    if "Joust" in selected_cards_names:
        non_supply_cards += sorted(
            (
                card
                for card in db.non_supply_cards.values()
                if CardType.REWARD in card.types
            ),
            key=card_sort_key(KingdomSortOrder.NAME),
        )

    # in games using Tournament, set the Prizes out near the Supply. These are
    # not in the Supply.
    if "Tournament" in selected_cards_names:
        non_supply_cards += sorted(
            (
                card
                for card in db.non_supply_cards.values()
                if CardType.PRIZE in card.types
            ),
            key=card_sort_key(KingdomSortOrder.NAME),
        )

    # in games using Hermit, set out the Madman pile near the Supply. This card
    # is not in the Supply.
    if "Hermit" in selected_cards_names:
        non_supply_cards.append(db.get_card_by_name("Madman"))

    # in games using Urchin, set out the Mercenary pile near the Supply. This
    # card is not in the Supply.
    if "Urchin" in selected_cards_names:
        non_supply_cards.append(db.get_card_by_name("Mercenary"))

    # in games using Bandit Camp, Marauder, or Pillage, set out the Spoils pile
    # near the supply. This card is not in the Supply.
    if selected_cards_names & {"Bandit Camp", "Marauder", "Pillage"}:
        non_supply_cards.append(db.get_card_by_name("Spoils"))

    # in games using Page, set out its Traveller upgrade chain near the Supply.
    # These cards are not in the Supply.
    if "Page" in selected_cards_names:
        non_supply_cards.append(db.get_card_by_name("Treasure Hunter"))
        non_supply_cards.append(db.get_card_by_name("Warrior"))
        non_supply_cards.append(db.get_card_by_name("Hero"))
        non_supply_cards.append(db.get_card_by_name("Champion"))

    # in games using Peasant, set out its Traveller upgrade chain near the
    # Supply. These cards are not in the Supply.
    if "Peasant" in selected_cards_names:
        non_supply_cards.append(db.get_card_by_name("Soldier"))
        non_supply_cards.append(db.get_card_by_name("Fugitive"))
        non_supply_cards.append(db.get_card_by_name("Disciple"))
        non_supply_cards.append(db.get_card_by_name("Teacher"))

    # if any Kingdom cards being used have the Fate type, shuffle the Boons and
    # put them near the Supply, and put the Will-o'-Wisp pile near the Supply
    # also.
    if any(CardType.FATE in card.types for card in kingdom_cards):
        non_supply_cards.append(db.get_card_by_name("Boons"))
        non_supply_cards.append(db.get_card_by_name("Will-o'-Wisp"))

    # if any Kingdom cards being used have the Doom type, shuffle the Hexes and
    # put them near the Supply, and put Deluded/Envious and Miserable/Twice
    # Miserable near the Supply also.
    if any(CardType.DOOM in card.types for card in kingdom_cards):
        non_supply_cards.append(db.get_card_by_name("Hexes"))
        non_supply_cards.append(db.get_card_by_name("Deluded"))
        non_supply_cards.append(db.get_card_by_name("Miserable"))

    # if Necromancer is being used, put the three Zombies into the trash.
    if "Necromancer" in selected_cards_names:
        non_supply_cards.append(db.get_card_by_name("Zombie Apprentice"))
        non_supply_cards.append(db.get_card_by_name("Zombie Mason"))
        non_supply_cards.append(db.get_card_by_name("Zombie Spy"))

    # if Fool is being used, get Lost in the Woods and have it handy.
    if "Fool" in selected_cards_names:
        non_supply_cards.append(db.get_card_by_name("Lost in the Woods"))

    # if Vampire is being used, put the Bat pile near the Supply.
    if "Vampire" in selected_cards_names:
        non_supply_cards.append(db.get_card_by_name("Bat"))

    # if Leprechaun or Secret Cave is being used, put the Wish pile near the
    # Supply.
    if "Leprechaun" in selected_cards_names or "Secret Cave" in selected_cards_names:
        non_supply_cards.append(db.get_card_by_name("Wish"))

    # if Devil's Workshop or Tormentor are being used, put the Imp pile near
    # the Supply; if Cemetery is being used, put the Ghost pile near the
    # Supply; and if Exorcist is being used, put all three Spirit piles -
    # Will-o'-Wisp, Imp, and Ghost - near the Supply.
    if (
        "Devil's Workshop" in selected_cards_names
        or "Tormentor" in selected_cards_names
    ):
        non_supply_cards.append(db.get_card_by_name("Imp"))
    if "Cemetery" in selected_cards_names:
        non_supply_cards.append(db.get_card_by_name("Ghost"))
    if "Exorcist" in selected_cards_names:
        if (will_o_wisp := db.get_card_by_name("Will-o'-Wisp")) not in non_supply_cards:
            non_supply_cards.append(will_o_wisp)
        if (imp := db.get_card_by_name("Imp")) not in non_supply_cards:
            non_supply_cards.append(imp)
        if (ghost := db.get_card_by_name("Ghost")) not in non_supply_cards:
            non_supply_cards.append(ghost)

    # artifacts are Status cards put near the Supply when their trigger Kingdom
    # card is selected.
    if "Flag Bearer" in selected_cards_names:
        non_supply_cards.append(db.get_card_by_name("Flag"))
    if "Border Guard" in selected_cards_names:
        non_supply_cards.append(db.get_card_by_name("Horn"))
        non_supply_cards.append(db.get_card_by_name("Lantern"))
    if "Treasurer" in selected_cards_names:
        non_supply_cards.append(db.get_card_by_name("Key"))
    if "Swashbuckler" in selected_cards_names:
        non_supply_cards.append(db.get_card_by_name("Treasure Chest"))

    # if any Kingdom cards give Loot, shuffle the Loot cards and set them out
    # near the Supply
    if any(
        GAIN_LOOT_PATTERN.search(card.instructions)
        for card in kingdom_cards | landscapes
    ):
        non_supply_cards.append(db.get_card_by_name("Loot"))

    # if any Kingdom or Landscape cards can gain Horses (Menagerie), set the
    # Horse pile near the Supply. This is not in the Supply.
    if any(
        GAIN_HORSES_PATTERN.search(card.instructions)
        for card in kingdom_cards | landscapes
    ):
        non_supply_cards.append(db.get_card_by_name("Horse"))

    # ── Basic piles ─────────────────────────────────────────────────────────
    basic_cards = [db.get_card_by_name(name) for name in DEFAULT_BASIC_CARD_NAMES]

    # add Colony/Platinum if ``use_colony`` or determined by Prosperity presence
    if use_colony or (
        use_colony is None
        and random.choice(tuple(kingdom_cards)).set == CardSet.PROSPERITY
    ):
        basic_cards.append(db.get_card_by_name("Colony"))
        basic_cards.append(db.get_card_by_name("Platinum"))

    # add Potion if any kingdom card has a potion cost
    if any(card.has_potion_cost for card in kingdom_cards):
        basic_cards.append(db.get_card_by_name("Potion"))

    # add Ruins pile if any kingdom card is of Looter type
    if any(CardType.LOOTER in card.types for card in kingdom_cards):
        basic_cards.append(db.get_card_by_name("Ruins"))

    # add Shelters if ``use_shelters`` or determined by Dark Ages presence
    if use_shelters or (
        use_shelters is None
        and random.choice(tuple(kingdom_cards)).set == CardSet.DARK_AGES
    ):
        basic_cards.append(db.get_card_by_name("Shelters"))

    # add Heirlooms if any Kingdom cards being used have a yellow banner
    # indicating an Heirloom
    heirlooms: list[Card] = []
    for card in kingdom_cards:
        if (heirloom_match := HEIRLOOM_PATTERN.search(card.instructions)) is not None:
            heirlooms.append(db.get_card_by_name(heirloom_match.group(1)))  # noqa: PERF401
    heirlooms = sorted(heirlooms, key=card_sort_key(sort_order))
    basic_cards += heirlooms

    # ── Special piles, cont. ────────────────────────────────────────────────
    # in games using Obelisk, choose a random Action Supply pile whose cards
    # will be worth 2VP each when scoring. This includes the Bane pile (if
    # present) since it is also a Supply pile.
    if "Obelisk" in selected_cards_names:
        obelisk_candidate_cards = [
            card for card in kingdom_cards if CardType.ACTION in card.types
        ]
        if not obelisk_candidate_cards:
            msg = "No eligible card (Action Supply pile) available for Obelisk"
            raise ValueError(msg)
        obelisk_target = random.choice(obelisk_candidate_cards)
        kingdom_marks[obelisk_target].append(PileMark(PileMarkKind.OBELISK))

    # ── Materials ───────────────────────────────────────────────────────────
    materials: set[Material] = set()
    for card in kingdom_cards | landscapes:
        for material in Material:
            if material.value in card.instructions:
                materials.add(material)

        if COFFERS_PATTERN.search(card.instructions):
            materials.add(Material.COFFERS_MAT)
            materials.add(Material.COIN_TOKENS)
        if VILLAGERS_PATTERN.search(card.instructions):
            materials.add(Material.COFFERS_VILLAGERS_MAT)
            materials.add(Material.COIN_TOKENS)
        if EXILE_PATTERN.search(card.instructions):
            materials.add(Material.EXILE_MAT)
        if CardType.LIAISON in card.types:
            materials.add(Material.FAVORS_MAT)
            materials.add(Material.COIN_TOKENS)
        if (
            CardType.GATHERING in card.types
            or VP_PLUS_PATTERN.search(card.instructions)
            or VP_SETUP_PATTERN.search(card.instructions)
        ):
            materials.add(Material.VICTORY_TOKENS)
        if card.name == "Embargo":
            materials.add(Material.EMBARGO_TOKENS)
        if MINUS_ONE_COIN_PATTERN.search(card.instructions):
            materials.add(Material.MINUS_ONE_COIN_TOKEN)
        if card.has_debt_cost or DEBT_PATTERN.search(card.instructions):
            materials.add(Material.DEBT_TOKENS)
        if CardType.PROJECT in card.types:
            materials.add(Material.WOODEN_CUBES)
        if CardType.OMEN in card.types:
            materials.add(Material.SUN_TOKENS)

    if Material.COFFERS_VILLAGERS_MAT in materials:
        materials.discard(Material.COFFERS_MAT)

    # ── Setup instructions ──────────────────────────────────────────────────
    setup_instructions: list[str] = []
    for card in sorted(
        kingdom_cards | landscapes | set(basic_cards),
        key=card_sort_key(sort_order),
    ):
        if (
            setup_instructions_match := SETUP_PATTERN.search(card.instructions)
        ) is not None:
            setup_instructions.append(  # noqa: PERF401
                f"{card.name}: {setup_instructions_match.group(1).removeprefix('Setup: ')}"
            )

    if heirlooms:
        setup_instructions.append(
            f"Heirlooms: Each player replaces {len(heirlooms)} starting Coppers with {', '.join([heirloom.name for heirloom in heirlooms])}. The unused Coppers go in the Copper pile."
        )

    # ── Materialise piles ──────────────────────────────────────────────────
    kingdom_piles = [
        Pile(card=card, marks=tuple(kingdom_marks[card]))
        for card in sorted(kingdom_cards, key=card_sort_key(sort_order))
    ]
    non_supply_piles = [
        Pile(card=card, marks=tuple(non_supply_marks[card]))
        for card in non_supply_cards
    ]

    basic_piles = [Pile(card=card) for card in basic_cards]

    return Game(
        basic_piles=basic_piles,
        kingdom_piles=kingdom_piles,
        druid_boons=druid_boons,
        ally=ally,
        prophecy=prophecy,
        landscapes=sorted(landscapes, key=card_sort_key(sort_order)),
        materials=sorted(
            materials,
            key=MATERIAL_ORDER.__getitem__,
        ),
        non_supply_piles=non_supply_piles,
        setup_instructions=setup_instructions,
    )
