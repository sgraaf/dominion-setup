"""Generate a complete Dominion game setup.

``generate_game`` is the entry point: it runs the numbered setup steps in turn.
The rest of the module has a section for each step, holding the rules
(constants, patterns and tables) that step applies.
"""

from __future__ import annotations

import random
import re
from collections import defaultdict
from dataclasses import dataclass
from typing import TYPE_CHECKING

from .models import (
    MATERIAL_ORDER,
    Card,
    CardCost,
    CardDatabase,
    CardSet,
    CardSetEdition,
    CardType,
    Game,
    KingdomRequirement,
    KingdomSortOrder,
    Material,
    Pile,
    PileMark,
    PileMarkKind,
)

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable


class SetupGenerationError(ValueError):
    """The selected sets cannot produce a valid game setup.

    Raised for problems with the inputs (e.g. too few Kingdom cards, or no
    eligible card for a Bane pile), as opposed to bugs or bad card data.
    Subclasses ``ValueError`` for backwards compatibility.
    """


def generate_game(  # noqa: PLR0913
    db: CardDatabase,
    *,
    sets_editions: set[tuple[CardSet, CardSetEdition]] | None = None,
    sort_order: KingdomSortOrder = KingdomSortOrder.COST,
    use_colony: bool | None = None,
    use_shelters: bool | None = None,
    max_landscapes: int = 2,
    requirements: Iterable[KingdomRequirement] = (),
    rng: random.Random | None = None,
) -> Game:
    """Generate a complete, rules-accurate Dominion game setup.

    For a given *rng* seed, the result is the same in every process.

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
        requirements: Effects (e.g. ``KingdomRequirement.BUYS``) that at least
            one of the 10 Kingdom cards must provide. Defaults to none.
        rng: The random number generator to draw with, e.g.
            ``random.Random(42)`` to reproduce a game. Defaults to a new,
            unseeded one, so the global ``random`` state is never changed.

    Returns:
        A Game object with selected Kingdom piles and basic supply.

    Raises:
        SetupGenerationError: If the selected sets cannot produce a valid
            setup.
    """
    # NOTE: the steps below consume *rng* in a fixed order, so reordering them
    # changes which game a given seed produces.
    if rng is None:
        rng = random.Random()

    # 1. Kingdom: 10 Kingdom piles that meet the *requirements*, and up to
    # *max_landscapes* Landscapes
    kingdom_cards, landscapes, unused_kingdom_cards = _draw_kingdom(
        db,
        sets_editions=sets_editions,
        max_landscapes=max_landscapes,
        requirements=requirements,
        rng=rng,
    )

    # 2. Extra Kingdom piles (Bane, Ferryman, …) and the Prophecy
    extra_piles, prophecy = _choose_extra_piles(
        db, kingdom_cards, landscapes, unused_kingdom_cards, rng=rng
    )
    kingdom_cards += [card for rule, card in extra_piles if rule.in_supply]
    set_aside_cards = [card for rule, card in extra_piles if not rule.in_supply]

    # cards set aside for Ferryman, Way of the Mouse and Riverboat can still be
    # gained or played, so they trigger setup just like Supply Kingdom cards
    cards_in_use = [*kingdom_cards, *set_aside_cards]

    # 3. Cards dealt out for specific cards in use
    druid_boons = _choose_druid_boons(db, cards_in_use, rng=rng)
    ally = _choose_ally(db, cards_in_use, rng=rng)
    trait_marks = _choose_trait_piles(kingdom_cards, landscapes, rng=rng)

    # 4. Non-Supply piles
    non_supply_cards = [
        *set_aside_cards,
        *_companion_cards(db, cards_in_use, landscapes),
    ]

    # 5. Basic Supply piles, then the Heirlooms that go with them
    basic_cards = _basic_cards(
        db,
        kingdom_cards,
        cards_in_use,
        use_colony=use_colony,
        use_shelters=use_shelters,
        rng=rng,
    )
    heirlooms = sorted(_heirlooms(db, cards_in_use), key=sort_order.sort_key)
    basic_cards += heirlooms

    # 6. Obelisk
    obelisk_marks = _choose_obelisk_pile(kingdom_cards, landscapes, rng=rng)

    # 7. Materials (mats & tokens)
    materials = sorted(
        _materials([*cards_in_use, *landscapes]), key=MATERIAL_ORDER.__getitem__
    )

    # 8. Setup instructions
    setup_instructions = _setup_instructions(
        [*cards_in_use, *landscapes, *basic_cards], heirlooms, sort_order
    )

    # collect each pile's marks (Bane, Trait, Obelisk, …)
    extra_pile_marks = [(card, PileMark(rule.mark)) for rule, card in extra_piles]
    marks: dict[Card, list[PileMark]] = defaultdict(list)
    for card, mark in [*extra_pile_marks, *trait_marks, *obelisk_marks]:
        marks[card].append(mark)

    return Game(
        basic_piles=[Pile(card=card) for card in basic_cards],
        kingdom_piles=[
            Pile(card=card, marks=tuple(marks[card]))
            for card in sorted(kingdom_cards, key=sort_order.sort_key)
        ],
        non_supply_piles=[
            Pile(card=card, marks=tuple(marks[card])) for card in non_supply_cards
        ],
        landscapes=sorted(landscapes, key=sort_order.sort_key),
        ally=ally,
        prophecy=prophecy,
        druid_boons=druid_boons,
        materials=materials,
        setup_instructions=setup_instructions,
    )


# ── 1. Kingdom ───────────────────────────────────────────────────────────────

KINGDOM_PILE_COUNT = 10

# Landscape card types eligible for selection during kingdom generation.
SELECTABLE_LANDSCAPE_TYPES: frozenset[CardType] = frozenset(
    {
        CardType.EVENT,
        CardType.LANDMARK,
        CardType.PROJECT,
        CardType.WAY,
        CardType.TRAIT,
    }
)

PLUS_ACTIONS_PATTERN = re.compile(r"\+\d+ Actions?\b")
PLUS_CARDS_PATTERN = re.compile(r"\+\d+ Cards?\b")
PLUS_BUY_PATTERN = re.compile(r"\+\d+ Buys?\b")
# telling you to trash a card other than this one: "trash this or a card from
# your hand" (Raze) counts, "trash this" (Feast), "the trash" (Rogue) and "they
# trash" (Saboteur) do not
TRASHING_PATTERN = re.compile(r"(?<!the )(?<![Tt]hey )\b[Tt]rash (?!this\b(?! or\b))")


def _instructions_match(pattern: re.Pattern[str]) -> Callable[[Card], bool]:
    """Return a rule that is met by the cards whose instructions match *pattern*."""
    return lambda card: bool(pattern.search(card.instructions))


# Whether a Kingdom card provides each requirement.
REQUIREMENT_RULES: dict[KingdomRequirement, Callable[[Card], bool]] = {
    KingdomRequirement.ACTIONS: _instructions_match(PLUS_ACTIONS_PATTERN),
    KingdomRequirement.CARDS: _instructions_match(PLUS_CARDS_PATTERN),
    KingdomRequirement.BUYS: _instructions_match(PLUS_BUY_PATTERN),
    KingdomRequirement.ATTACK: lambda card: CardType.ATTACK in card.types,
    KingdomRequirement.REACTION: lambda card: CardType.REACTION in card.types,
    KingdomRequirement.TRASHING: _instructions_match(TRASHING_PATTERN),
}


def _draw_kingdom(
    db: CardDatabase,
    *,
    sets_editions: set[tuple[CardSet, CardSetEdition]] | None,
    max_landscapes: int,
    requirements: Iterable[KingdomRequirement] = (),
    rng: random.Random,
) -> tuple[list[Card], list[Card], list[Card]]:
    """Draw 10 Kingdom cards and at most *max_landscapes* Landscapes.

    Each of the *requirements* is met by at least one of the Kingdom cards.

    Returns the Kingdom cards, the Landscapes, and the unused Kingdom cards in
    random order.
    """
    candidates = [
        card
        for card in (*db.kingdom_cards.values(), *db.landscape_cards.values())
        if (card.is_kingdom or SELECTABLE_LANDSCAPE_TYPES & set(card.types))
        and (
            sets_editions is None
            or any((card.set, edition) in sets_editions for edition in card.editions)
        )
    ]

    kingdom_candidate_count = sum(card.is_kingdom for card in candidates)
    if kingdom_candidate_count < KINGDOM_PILE_COUNT:
        msg = f"Not enough kingdom cards: need {KINGDOM_PILE_COUNT}, found {kingdom_candidate_count}"
        raise SetupGenerationError(msg)

    requirements = list(requirements)
    for requirement in requirements:
        is_provider = REQUIREMENT_RULES[requirement]
        if not any(card.is_kingdom and is_provider(card) for card in candidates):
            msg = f"No Kingdom card in the selected sets provides {requirement}"
            raise SetupGenerationError(msg)

    # shuffle the randomizer deck and draw until there are 10 Kingdom cards,
    # keeping the first *max_landscapes* Landscapes drawn along the way. Sorting
    # first makes the outcome depend only on the *rng* state, never on the
    # order of the database (or of any set it was built from, which varies
    # between processes because string hashing is randomized).
    deck = sorted(candidates, key=KingdomSortOrder.NAME.sort_key)
    rng.shuffle(deck)
    kingdom_cards: list[Card] = []
    landscapes: list[Card] = []
    skipped_cards: list[Card] = []
    unmet_requirements = set(requirements)

    def spare_slots() -> int:
        """Return the free Kingdom slots beyond one for each unmet requirement."""
        return KINGDOM_PILE_COUNT - len(kingdom_cards) - len(unmet_requirements)

    # keep a free slot for each requirement still unmet, so only a card that
    # meets one can take it. Such cards are never skipped, and skipped cards go
    # back on the deck once there are spare slots again, so the draw completes.
    while len(kingdom_cards) < KINGDOM_PILE_COUNT:
        card = deck.pop()
        if card.is_kingdom:
            met_requirements = {
                requirement
                for requirement in unmet_requirements
                if REQUIREMENT_RULES[requirement](card)
            }
            if met_requirements or spare_slots() > 0:
                kingdom_cards.append(card)
                unmet_requirements -= met_requirements
                # a card that meets several requirements frees kept slots
                if spare_slots() > 0:
                    deck += reversed(skipped_cards)
                    skipped_cards.clear()
            else:
                skipped_cards.append(card)
        elif len(landscapes) < max_landscapes:
            landscapes.append(card)

    unused_kingdom_cards = [card for card in deck if card.is_kingdom]
    return kingdom_cards, landscapes, [*unused_kingdom_cards, *skipped_cards]


# ── 2. Extra Kingdom piles & Prophecy ────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class ExtraPileRule:
    """An extra Kingdom pile that must be chosen when *trigger* is in use."""

    trigger: str
    mark: PileMarkKind
    in_supply: bool
    requirement: str
    is_eligible: Callable[[Card], bool]


EXTRA_PILE_RULES: tuple[ExtraPileRule, ...] = (
    # in games using Young Witch, choose an additional Kingdom card costing $2
    # or $3, and put its pile into the Supply. This is the "Bane" pile.
    ExtraPileRule(
        trigger="Young Witch",
        mark=PileMarkKind.BANE,
        in_supply=True,
        requirement="Kingdom card costing $2-$3",
        is_eligible=lambda card: card.cost in {CardCost(coins=2), CardCost(coins=3)},
    ),
    # in games using Ferryman, choose an additional Kingdom card costing $3 or
    # $4, and put its pile near the Supply. This pile is not part of the
    # Supply.
    ExtraPileRule(
        trigger="Ferryman",
        mark=PileMarkKind.FERRYMAN,
        in_supply=False,
        requirement="kingdom card costing $3-$4",
        is_eligible=lambda card: card.cost in {CardCost(coins=3), CardCost(coins=4)},
    ),
    # in games using Way of the Mouse, set aside an unused non-Duration Action
    # costing $2 or $3
    ExtraPileRule(
        trigger="Way of the Mouse",
        mark=PileMarkKind.WAY_OF_THE_MOUSE,
        in_supply=False,
        requirement="non-Duration Action kingdom card costing $2-$3",
        is_eligible=lambda card: (
            card.cost in {CardCost(coins=2), CardCost(coins=3)}
            and CardType.ACTION in card.types
            and CardType.DURATION not in card.types
        ),
    ),
    # in games using Riverboat, set aside an unused non-Duration Action costing
    # $5
    ExtraPileRule(
        trigger="Riverboat",
        mark=PileMarkKind.RIVERBOAT,
        in_supply=False,
        requirement="non-Duration Action kingdom card costing $5",
        is_eligible=lambda card: (
            card.cost == CardCost(coins=5)
            and CardType.ACTION in card.types
            and CardType.DURATION not in card.types
        ),
    ),
    # in games using Approaching Army, add an Attack Kingdom card to the Supply
    ExtraPileRule(
        trigger="Approaching Army",
        mark=PileMarkKind.APPROACHING_ARMY,
        in_supply=True,
        requirement="Attack kingdom card",
        is_eligible=lambda card: CardType.ATTACK in card.types,
    ),
)


def _choose_extra_piles(
    db: CardDatabase,
    kingdom_cards: list[Card],
    landscapes: list[Card],
    unused_kingdom_cards: list[Card],
    *,
    rng: random.Random,
) -> tuple[list[tuple[ExtraPileRule, Card]], Card | None]:
    """Choose the extra Kingdom piles required by ``EXTRA_PILE_RULES``, and the Prophecy.

    Extra piles are chosen from *unused_kingdom_cards*, which must be in random
    order. Returns each extra pile along with the rule that required it, in
    the order they were chosen, and the Prophecy.
    """
    candidates = list(unused_kingdom_cards)  # copy, as chosen cards are removed
    extra_piles: list[tuple[ExtraPileRule, Card]] = []
    prophecy: Card | None = None
    resolved_triggers: set[str] = set()

    # an extra pile can trigger further setup (e.g. Ferryman choosing Young
    # Witch, which needs a Bane; or a Bane that is an Omen, which needs a
    # Prophecy), so repeat until nothing new is triggered
    while True:
        cards_in_use = [*kingdom_cards, *(card for _, card in extra_piles)]

        # in every game with one or more Omen cards, deal out one Prophecy for
        # it. Only use one Prophecy no matter how many Omens you have.
        if prophecy is None and any(
            CardType.OMEN in card.types for card in cards_in_use
        ):
            prophecy = rng.choice(
                _cards_of_type(db.landscape_cards.values(), CardType.PROPHECY)
            )

        triggers = {card.name for card in (*cards_in_use, *landscapes)}
        if prophecy is not None:
            triggers.add(prophecy.name)
        pending_rules = [
            rule
            for rule in EXTRA_PILE_RULES
            if rule.trigger in triggers and rule.trigger not in resolved_triggers
        ]
        if not pending_rules:
            return extra_piles, prophecy

        for rule in pending_rules:
            resolved_triggers.add(rule.trigger)
            # the unused cards are in random order, so the first eligible one
            # is a uniformly random choice
            card = next(filter(rule.is_eligible, candidates), None)
            if card is None:
                msg = f"No eligible {rule.mark} card ({rule.requirement}) available for {rule.trigger}"
                raise SetupGenerationError(msg)
            candidates.remove(card)
            extra_piles.append((rule, card))


# ── 3. Cards dealt out for specific cards in use ─────────────────────────────

DRUID_BOON_COUNT = 3


def _choose_druid_boons(
    db: CardDatabase, cards_in_use: list[Card], *, rng: random.Random
) -> list[Card]:
    """Return the Boons dealt face up for Druid, if Druid is in use."""
    # if Druid is being used, deal three Boon cards face up for use with it.
    if not any(card.name == "Druid" for card in cards_in_use):
        return []
    return rng.sample(
        _cards_of_type(db.mixed_pile_cards.values(), CardType.BOON),
        DRUID_BOON_COUNT,
    )


def _choose_ally(
    db: CardDatabase, cards_in_use: list[Card], *, rng: random.Random
) -> Card | None:
    """Return the Ally, if any Liaison is in use."""
    # in any game using Liaisons, exactly one Ally is chosen, and it determines
    # what effect Favor tokens have in that game.
    if not any(CardType.LIAISON in card.types for card in cards_in_use):
        return None
    return rng.choice(_cards_of_type(db.landscape_cards.values(), CardType.ALLY))


def _choose_trait_piles(
    kingdom_cards: list[Card], landscapes: list[Card], *, rng: random.Random
) -> list[tuple[Card, PileMark]]:
    """Return the Kingdom pile each Trait applies to, with its mark."""
    # each Trait landscape applies to a different randomly chosen Action or
    # Treasure Supply pile.
    trait_landscapes = _cards_of_type(landscapes, CardType.TRAIT)
    if not trait_landscapes:
        return []
    trait_eligible_cards = [
        card
        for card in kingdom_cards
        if {CardType.ACTION, CardType.TREASURE} & set(card.types)
    ]
    if len(trait_eligible_cards) < len(trait_landscapes):
        msg = f"Not enough Action/Treasure kingdom piles ({len(trait_eligible_cards)}) for {len(trait_landscapes)} Trait landscape(s)"
        raise SetupGenerationError(msg)
    trait_targets = rng.sample(trait_eligible_cards, len(trait_landscapes))
    return [
        (target, PileMark(PileMarkKind.TRAIT, trait=trait))
        for target, trait in zip(trait_targets, trait_landscapes, strict=True)
    ]


# ── 4. Non-Supply piles ──────────────────────────────────────────────────────

# Non-Supply cards set out when a trigger is in use. A trigger is either the
# name of a card in use, or a type that any card in use has.
COMPANION_CARDS: tuple[tuple[str | CardType, tuple[str, ...]], ...] = (
    ("Hermit", ("Madman",)),
    ("Urchin", ("Mercenary",)),
    ("Bandit Camp", ("Spoils",)),
    ("Marauder", ("Spoils",)),
    ("Pillage", ("Spoils",)),
    # Traveller upgrade chains
    ("Page", ("Treasure Hunter", "Warrior", "Hero", "Champion")),
    ("Peasant", ("Soldier", "Fugitive", "Disciple", "Teacher")),
    # shuffle the Boons and put them near the Supply, along with Will-o'-Wisp
    (CardType.FATE, ("Boons", "Will-o'-Wisp")),
    # shuffle the Hexes and put them near the Supply, along with
    # Deluded/Envious and Miserable/Twice Miserable
    (CardType.DOOM, ("Hexes", "Deluded", "Miserable")),
    # put the three Zombies into the trash
    ("Necromancer", ("Zombie Apprentice", "Zombie Mason", "Zombie Spy")),
    ("Fool", ("Lost in the Woods",)),
    ("Vampire", ("Bat",)),
    ("Leprechaun", ("Wish",)),
    ("Secret Cave", ("Wish",)),
    # Spirits
    ("Devil's Workshop", ("Imp",)),
    ("Tormentor", ("Imp",)),
    ("Cemetery", ("Ghost",)),
    ("Exorcist", ("Will-o'-Wisp", "Imp", "Ghost")),
    # Artifacts
    ("Flag Bearer", ("Flag",)),
    ("Border Guard", ("Horn", "Lantern")),
    ("Treasurer", ("Key",)),
    ("Swashbuckler", ("Treasure Chest",)),
)

GAIN_LOOT_PATTERN = re.compile(r"[gG]ain a Loot")
GAIN_HORSES_PATTERN = re.compile(r"[gG]ains? (?:a|that many|\d+) Horses?")


def _companion_cards(
    db: CardDatabase, cards_in_use: list[Card], landscapes: list[Card]
) -> list[Card]:
    """Return the non-Supply cards (Prizes, Spirits, Loot, …) required by the cards in use."""
    names_in_use = {card.name for card in cards_in_use}
    types_in_use = {card_type for card in cards_in_use for card_type in card.types}
    companions: list[Card] = []

    # in games using Joust (Tournament), set the Rewards (Prizes) out near the
    # Supply. These are not in the Supply.
    for trigger, card_type in (
        ("Joust", CardType.REWARD),
        ("Tournament", CardType.PRIZE),
    ):
        if trigger in names_in_use:
            companions += sorted(
                _cards_of_type(db.non_supply_cards.values(), card_type),
                key=KingdomSortOrder.NAME.sort_key,
            )

    companion_names: list[str] = []
    for trigger, names in COMPANION_CARDS:
        if isinstance(trigger, CardType):
            is_triggered = trigger in types_in_use
        else:
            is_triggered = trigger in names_in_use
        if is_triggered:
            companion_names += names

    # if any Kingdom or Landscape cards give Loot (or Horses), shuffle the Loot
    # cards (put the Horse pile) and set them out near the Supply.
    cards_with_instructions = [*cards_in_use, *landscapes]
    if any(
        GAIN_LOOT_PATTERN.search(card.instructions) for card in cards_with_instructions
    ):
        companion_names.append("Loot")
    if any(
        GAIN_HORSES_PATTERN.search(card.instructions)
        for card in cards_with_instructions
    ):
        companion_names.append("Horse")

    # several triggers can share a companion (e.g. Imp), so drop duplicates
    companions += [db.get_card_by_name(name) for name in dict.fromkeys(companion_names)]
    return companions


# ── 5. Basic Supply piles & Heirlooms ────────────────────────────────────────

DEFAULT_BASIC_CARD_NAMES: tuple[str, ...] = (
    "Copper",
    "Silver",
    "Gold",
    "Estate",
    "Duchy",
    "Province",
    "Curse",
)

HEIRLOOM_PATTERN = re.compile(r"Heirloom: (.*)$")


def _basic_cards(  # noqa: PLR0913
    db: CardDatabase,
    kingdom_cards: list[Card],
    cards_in_use: list[Card],
    *,
    use_colony: bool | None,
    use_shelters: bool | None,
    rng: random.Random,
) -> list[Card]:
    """Return the basic Supply cards, plus Colony/Platinum, Potion, Ruins and Shelters as needed."""
    basic_cards = [db.get_card_by_name(name) for name in DEFAULT_BASIC_CARD_NAMES]

    # add Colony/Platinum if ``use_colony`` or determined by Prosperity presence
    if use_colony or (
        use_colony is None and rng.choice(kingdom_cards).set == CardSet.PROSPERITY
    ):
        basic_cards.append(db.get_card_by_name("Colony"))
        basic_cards.append(db.get_card_by_name("Platinum"))

    # add Potion if any kingdom card has a potion cost
    if any(card.has_potion_cost for card in cards_in_use):
        basic_cards.append(db.get_card_by_name("Potion"))

    # add Ruins pile if any kingdom card is of Looter type
    if any(CardType.LOOTER in card.types for card in cards_in_use):
        basic_cards.append(db.get_card_by_name("Ruins"))

    # add Shelters if ``use_shelters`` or determined by Dark Ages presence
    if use_shelters or (
        use_shelters is None and rng.choice(kingdom_cards).set == CardSet.DARK_AGES
    ):
        basic_cards.append(db.get_card_by_name("Shelters"))

    return basic_cards


def _heirlooms(db: CardDatabase, cards_in_use: list[Card]) -> list[Card]:
    """Return the Heirlooms of the cards in use."""
    # add Heirlooms if any Kingdom cards being used have a yellow banner
    # indicating an Heirloom
    return [
        db.get_card_by_name(heirloom_match.group(1))
        for card in cards_in_use
        if (heirloom_match := HEIRLOOM_PATTERN.search(card.instructions))
    ]


# ── 6. Obelisk ───────────────────────────────────────────────────────────────


def _choose_obelisk_pile(
    kingdom_cards: list[Card], landscapes: list[Card], *, rng: random.Random
) -> list[tuple[Card, PileMark]]:
    """Return the Kingdom pile Obelisk applies to, with its mark, if Obelisk is in use."""
    # in games using Obelisk, choose a random Action Supply pile whose cards
    # will be worth 2VP each when scoring. This includes the extra Supply piles
    # (e.g. Bane).
    if not any(landscape.name == "Obelisk" for landscape in landscapes):
        return []
    obelisk_candidate_cards = _cards_of_type(kingdom_cards, CardType.ACTION)
    if not obelisk_candidate_cards:
        msg = "No eligible card (Action Supply pile) available for Obelisk"
        raise SetupGenerationError(msg)
    return [(rng.choice(obelisk_candidate_cards), PileMark(PileMarkKind.OBELISK))]


# ── 7. Materials ─────────────────────────────────────────────────────────────

COFFERS_PATTERN = re.compile(r"\+\d+ Coffers")
VILLAGERS_PATTERN = re.compile(r"\+\d+ Villagers?")
COIN_TOKEN_PATTERN = re.compile(r"Coin tokens?")
EXILE_PATTERN = re.compile(r"Exile")
VP_PLUS_PATTERN = re.compile(r"\+\d+ VP")
VP_SETUP_PATTERN = re.compile(r"Setup: Put \d+ VP")
MINUS_ONE_COIN_PATTERN = re.compile(r"-\$1 token")
DEBT_PATTERN = re.compile(r"\d+D")


def _materials(cards: list[Card]) -> set[Material]:  # noqa: C901, PLR0912
    """Return the mats and tokens needed by *cards*."""
    materials: set[Material] = set()
    for card in cards:
        for material in Material:
            if material.value in card.instructions:
                materials.add(material)

        if COFFERS_PATTERN.search(card.instructions):
            materials.add(Material.COFFERS_MAT)
            materials.add(Material.COIN_TOKENS)
        if VILLAGERS_PATTERN.search(card.instructions):
            materials.add(Material.COFFERS_VILLAGERS_MAT)
            materials.add(Material.COIN_TOKENS)
        if COIN_TOKEN_PATTERN.search(card.instructions):
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
    return materials


# ── 8. Setup instructions ────────────────────────────────────────────────────

SETUP_PATTERN = re.compile(r"Setup: (.*)$")


def _setup_instructions(
    cards: list[Card], heirlooms: list[Card], sort_order: KingdomSortOrder
) -> list[str]:
    """Return the "Setup:" instructions of *cards*, plus how to deal out *heirlooms*."""
    setup_instructions = [
        f"{card.name}: {setup_match.group(1)}"
        for card in sorted(cards, key=sort_order.sort_key)
        if (setup_match := SETUP_PATTERN.search(card.instructions))
    ]
    if heirlooms:
        setup_instructions.append(
            f"Heirlooms: Each player replaces {len(heirlooms)} starting Coppers with {', '.join(heirloom.name for heirloom in heirlooms)}. The unused Coppers go in the Copper pile."
        )
    return setup_instructions


# ── Helpers ──────────────────────────────────────────────────────────────────


def _cards_of_type(cards: Iterable[Card], card_type: CardType) -> list[Card]:
    """Return the cards in *cards* that have *card_type*, preserving order."""
    return [card for card in cards if card_type in card.types]
