"""Generate a complete Dominion game setup.

``generate_game`` is the entry point: it runs the numbered setup steps in turn.
The rest of the module has a section for each step, holding the rules
(constants, patterns and tables) that step applies.
"""

from __future__ import annotations

import random
import re
from collections import defaultdict
from dataclasses import dataclass, replace
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
    SetupInstruction,
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
    include: Iterable[str] = (),
    exclude: Iterable[str] = (),
    promos: Iterable[str] = (),
    black_market_size: int = 15,
    players: int | None = None,
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
        include: Names of Kingdom cards and Landscapes that must be in the
            game, from any set. Defaults to none.
        exclude: Names of Kingdom cards and Landscapes that must not be drawn.
            Defaults to none.
        promos: Names of Promo cards to draw from, without the rest of the
            Promo set, also when *sets_editions* is ``None``. Has no effect on
            the draw if *sets_editions* includes the Promo set, but the names
            are still checked. Defaults to none.
        black_market_size: How many unused Kingdom cards to deal into the
            Black Market deck, if Black Market is in use. Defaults to 15.
        players: The number of players (2 to 6), to work out how many cards
            go in each pile. Defaults to ``None``, which leaves the pile sizes
            unknown.
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
    if players is not None and not MIN_PLAYERS <= players <= MAX_PLAYERS:
        msg = f"Dominion is for {MIN_PLAYERS} to {MAX_PLAYERS} players, not {players}"
        raise SetupGenerationError(msg)
    if rng is None:
        rng = random.Random()

    include = list(include)
    sets_editions, exclude = _restrict_promos(
        db,
        promos,
        sets_editions=sets_editions,
        include=include,
        exclude=exclude,
    )

    # 1. Kingdom: 10 Kingdom piles that meet the *requirements*, and up to
    # *max_landscapes* Landscapes, with the *include*d cards and without the
    # *exclude*d ones
    kingdom_cards, landscapes, unused_kingdom_cards = _draw_kingdom(
        db,
        sets_editions=sets_editions,
        max_landscapes=max_landscapes,
        requirements=requirements,
        include=include,
        exclude=exclude,
        rng=rng,
    )

    # 2. Extra Kingdom piles (Bane, Ferryman, …), the Prophecy and the Black
    # Market deck
    extra_piles, prophecy, black_market_deck = _choose_extra_piles(
        db,
        kingdom_cards,
        landscapes,
        unused_kingdom_cards,
        black_market_size=black_market_size,
        rng=rng,
    )
    kingdom_cards += [card for rule, card in extra_piles if rule.in_supply]
    set_aside_cards = [card for rule, card in extra_piles if not rule.in_supply]
    single_set_aside_cards = {card for rule, card in extra_piles if rule.is_single_card}

    # cards set aside for Ferryman, Way of the Mouse and Riverboat, and those in
    # the Black Market deck, can still be gained or played, so they trigger
    # setup just like Supply Kingdom cards
    cards_in_use = [*kingdom_cards, *set_aside_cards, *black_market_deck]

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
        _materials([*cards_in_use, *landscapes]),
        key=MATERIAL_ORDER.__getitem__,
    )

    # 8. Setup instructions
    setup_instructions = _setup_instructions(
        [*cards_in_use, *landscapes, *basic_cards],
        heirlooms,
        sort_order,
        players=players,
    )

    # collect each pile's marks (Bane, Trait, Obelisk, …)
    extra_pile_marks = [(card, PileMark(rule.mark)) for rule, card in extra_piles]
    marks: dict[Card, list[PileMark]] = defaultdict(list)
    for card, mark in [*extra_pile_marks, *trait_marks, *obelisk_marks]:
        marks[card].append(mark)

    def pile(card: Card) -> Pile:
        """Return the Pile of *card*, with its marks and (9.) its size."""
        if players is None:
            size = None
        elif card in single_set_aside_cards:
            size = 1
        else:
            size = _pile_size(card, players=players, heirloom_count=len(heirlooms))
        return Pile(card=card, marks=tuple(marks[card]), size=size)

    return Game(
        basic_piles=[pile(card) for card in basic_cards],
        kingdom_piles=[
            pile(card) for card in sorted(kingdom_cards, key=sort_order.sort_key)
        ],
        non_supply_piles=[pile(card) for card in non_supply_cards],
        landscapes=sorted(landscapes, key=sort_order.sort_key),
        ally=ally,
        prophecy=prophecy,
        druid_boons=druid_boons,
        black_market_deck=sorted(black_market_deck, key=sort_order.sort_key),
        materials=materials,
        setup_instructions=setup_instructions,
        players=players,
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
    },
)

PLUS_ACTIONS_PATTERN = re.compile(r"\+\d+ Actions?\b")
PLUS_CARDS_PATTERN = re.compile(r"\+\d+ Cards?\b")
PLUS_BUY_PATTERN = re.compile(r"\+\d+ Buys?\b")
# telling you to trash a card other than this one: "trash this or a card from
# your hand" (Raze) counts, "trash this" (Feast), "the trash" (Rogue) and "they
# trash" (Saboteur) do not
TRASHING_PATTERN = re.compile(r"(?<!the )(?<![Tt]hey )\b[Tt]rash (?!this\b(?! or\b))")


def _restrict_promos(
    db: CardDatabase,
    promos: Iterable[str],
    *,
    sets_editions: set[tuple[CardSet, CardSetEdition]] | None,
    include: Iterable[str],
    exclude: Iterable[str],
) -> tuple[set[tuple[CardSet, CardSetEdition]] | None, Iterable[str]]:
    """Return *sets_editions* and *exclude* that draw from the given *promos* only.

    The Promo set is added to *sets_editions*, and the other Promos (except the
    *include*d ones) to *exclude*, unless *sets_editions* includes the Promo set.
    """
    promos = list(promos)
    if not promos:
        return sets_editions, exclude
    promo_names = {
        card.name
        for card in (*db.kingdom_cards.values(), *db.landscape_cards.values())
        if card.set == CardSet.PROMO
    }
    for name in promos:
        if name not in promo_names:
            msg = f"{name!r} is not a Promo card"
            raise SetupGenerationError(msg)
    promo_set_edition = (CardSet.PROMO, CardSetEdition.FIRST_EDITION)
    if sets_editions is not None and promo_set_edition in sets_editions:
        return sets_editions, exclude
    if sets_editions is not None:  # None is every set, the Promo set included
        sets_editions = {*sets_editions, promo_set_edition}
    return sets_editions, [*exclude, *sorted(promo_names - {*promos, *include})]


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


def is_selectable(card: Card) -> bool:
    """Return whether *card* is a Kingdom card or a selectable Landscape."""
    return card.is_kingdom or bool(SELECTABLE_LANDSCAPE_TYPES & set(card.types))


def _selectable_cards_by_name(db: CardDatabase, names: Iterable[str]) -> list[Card]:
    """Look up the Kingdom cards and selectable Landscapes called *names*."""
    cards = []
    for name in dict.fromkeys(names):  # each name once, in order
        if (card := db.card_name_to_card.get(name)) is None:
            msg = f"Card {name!r} not found"
            raise SetupGenerationError(msg)
        if not is_selectable(card):
            msg = f"{name!r} is not a Kingdom card or Landscape"
            raise SetupGenerationError(msg)
        cards.append(card)
    return cards


def _included_and_excluded_cards(
    db: CardDatabase,
    include: Iterable[str],
    exclude: Iterable[str],
    *,
    max_landscapes: int,
) -> tuple[list[Card], list[Card], list[Card]]:
    """Return the included Kingdom cards, the included Landscapes and the excluded cards."""
    included_cards = _selectable_cards_by_name(db, include)
    excluded_cards = _selectable_cards_by_name(db, exclude)
    for card in included_cards:
        if card in excluded_cards:
            msg = f"{card.name!r} is both included and excluded"
            raise SetupGenerationError(msg)

    kingdom_cards = [card for card in included_cards if card.is_kingdom]
    landscapes = [card for card in included_cards if not card.is_kingdom]
    if len(kingdom_cards) > KINGDOM_PILE_COUNT:
        msg = f"Cannot include {len(kingdom_cards)} Kingdom cards: the Kingdom has {KINGDOM_PILE_COUNT}"
        raise SetupGenerationError(msg)
    if len(landscapes) > max_landscapes:
        msg = (
            f"Cannot include {len(landscapes)} Landscapes with at most {max_landscapes}"
        )
        raise SetupGenerationError(msg)
    return kingdom_cards, landscapes, excluded_cards


def _unmet_requirements(
    requirements: Iterable[KingdomRequirement],
    kingdom_cards: list[Card],
    candidates: list[Card],
) -> set[KingdomRequirement]:
    """Return the *requirements* that the (included) *kingdom_cards* do not meet.

    Raises ``SetupGenerationError`` if the *candidates* cannot meet them in the
    free Kingdom slots.
    """
    unmet_requirements = [
        requirement
        for requirement in requirements
        if not any(REQUIREMENT_RULES[requirement](card) for card in kingdom_cards)
    ]
    for requirement in unmet_requirements:
        is_provider = REQUIREMENT_RULES[requirement]
        if not any(card.is_kingdom and is_provider(card) for card in candidates):
            msg = f"No Kingdom card in the selected sets provides {requirement}"
            raise SetupGenerationError(msg)
    # ``_draw_kingdom`` keeps a free slot for each unmet requirement
    free_slot_count = KINGDOM_PILE_COUNT - len(kingdom_cards)
    if len(unmet_requirements) > free_slot_count:
        msg = f"Only {free_slot_count} free Kingdom slot(s) for {len(unmet_requirements)} requirement(s) the included cards do not meet"
        raise SetupGenerationError(msg)
    return set(unmet_requirements)


def _draw_kingdom(  # noqa: PLR0913
    db: CardDatabase,
    *,
    sets_editions: set[tuple[CardSet, CardSetEdition]] | None,
    max_landscapes: int,
    requirements: Iterable[KingdomRequirement] = (),
    include: Iterable[str] = (),
    exclude: Iterable[str] = (),
    rng: random.Random,
) -> tuple[list[Card], list[Card], list[Card]]:
    """Draw 10 Kingdom cards and at most *max_landscapes* Landscapes.

    Each of the *requirements* is met by at least one of the Kingdom cards. The
    cards named in *include* (from any set) are always used, and the cards
    named in *exclude* never are.

    Returns the Kingdom cards, the Landscapes, and the unused Kingdom cards in
    random order.
    """
    # the included cards are drawn before the randomizer deck is shuffled
    kingdom_cards, landscapes, excluded_cards = _included_and_excluded_cards(
        db,
        include,
        exclude,
        max_landscapes=max_landscapes,
    )

    unavailable_cards = {*kingdom_cards, *landscapes, *excluded_cards}
    candidates = [
        card
        for card in (*db.kingdom_cards.values(), *db.landscape_cards.values())
        if is_selectable(card)
        and card not in unavailable_cards
        and (
            sets_editions is None
            or any((card.set, edition) in sets_editions for edition in card.editions)
        )
    ]

    free_slot_count = KINGDOM_PILE_COUNT - len(kingdom_cards)
    kingdom_candidate_count = sum(card.is_kingdom for card in candidates)
    if kingdom_candidate_count < free_slot_count:
        msg = f"Not enough kingdom cards: need {free_slot_count}, found {kingdom_candidate_count}"
        raise SetupGenerationError(msg)

    unmet_requirements = _unmet_requirements(requirements, kingdom_cards, candidates)

    # shuffle the randomizer deck and draw until there are 10 Kingdom cards,
    # keeping the first *max_landscapes* Landscapes drawn along the way. Sorting
    # first makes the outcome depend only on the *rng* state, never on the
    # order of the database (or of any set it was built from, which varies
    # between processes because string hashing is randomized).
    deck = sorted(candidates, key=KingdomSortOrder.NAME.sort_key)
    rng.shuffle(deck)
    skipped_cards: list[Card] = []

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


# ── 2. Extra Kingdom piles, Prophecy & Black Market deck ─────────────────────


@dataclass(frozen=True, slots=True)
class ExtraPileRule:
    """An extra Kingdom pile that must be chosen when *trigger* is in use."""

    trigger: str
    mark: PileMarkKind
    in_supply: bool
    requirement: str
    is_eligible: Callable[[Card], bool]
    # whether a single card is set aside, instead of a whole pile
    is_single_card: bool = False


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
        is_single_card=True,
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
        is_single_card=True,
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


def _choose_extra_piles(  # noqa: PLR0913
    db: CardDatabase,
    kingdom_cards: list[Card],
    landscapes: list[Card],
    unused_kingdom_cards: list[Card],
    *,
    black_market_size: int,
    rng: random.Random,
) -> tuple[list[tuple[ExtraPileRule, Card]], Card | None, list[Card]]:
    """Choose the extra Kingdom piles, the Prophecy and the Black Market deck.

    Extra piles (required by ``EXTRA_PILE_RULES``) and the Black Market deck
    are chosen from *unused_kingdom_cards*, which must be in random order.
    Returns each extra pile along with the rule that required it, in the order
    they were chosen, the Prophecy, and the (at most *black_market_size*) cards
    of the Black Market deck.
    """
    candidates = list(unused_kingdom_cards)  # copy, as chosen cards are removed
    extra_piles: list[tuple[ExtraPileRule, Card]] = []
    prophecy: Card | None = None
    black_market_deck: list[Card] = []
    resolved_triggers: set[str] = set()

    # an extra pile can trigger further setup (e.g. Ferryman choosing Young
    # Witch, which needs a Bane; or a Bane that is an Omen, which needs a
    # Prophecy), and so can a card in the Black Market deck, so repeat until
    # nothing new is triggered
    while True:
        cards_in_use = [
            *kingdom_cards,
            *(card for _, card in extra_piles),
            *black_market_deck,
        ]

        # in every game with one or more Omen cards, deal out one Prophecy for
        # it. Only use one Prophecy no matter how many Omens you have.
        if prophecy is None and any(
            CardType.OMEN in card.types for card in cards_in_use
        ):
            prophecy = rng.choice(
                _cards_of_type(db.landscape_cards.values(), CardType.PROPHECY),
            )

        triggers = {card.name for card in (*cards_in_use, *landscapes)}
        if prophecy is not None:
            triggers.add(prophecy.name)

        # make a Black Market deck out of different unused Kingdom cards. They
        # are in random order, so the first ones are a uniformly random choice.
        if "Black Market" in triggers and "Black Market" not in resolved_triggers:
            resolved_triggers.add("Black Market")
            black_market_deck = candidates[:black_market_size]
            del candidates[:black_market_size]
            continue

        pending_rules = [
            rule
            for rule in EXTRA_PILE_RULES
            if rule.trigger in triggers and rule.trigger not in resolved_triggers
        ]
        if not pending_rules:
            return extra_piles, prophecy, black_market_deck

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
    db: CardDatabase,
    cards_in_use: list[Card],
    *,
    rng: random.Random,
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
    db: CardDatabase,
    cards_in_use: list[Card],
    *,
    rng: random.Random,
) -> Card | None:
    """Return the Ally, if any Liaison is in use."""
    # in any game using Liaisons, exactly one Ally is chosen, and it determines
    # what effect Favor tokens have in that game.
    if not any(CardType.LIAISON in card.types for card in cards_in_use):
        return None
    return rng.choice(_cards_of_type(db.landscape_cards.values(), CardType.ALLY))


def _choose_trait_piles(
    kingdom_cards: list[Card],
    landscapes: list[Card],
    *,
    rng: random.Random,
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
    db: CardDatabase,
    cards_in_use: list[Card],
    landscapes: list[Card],
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
    kingdom_cards: list[Card],
    landscapes: list[Card],
    *,
    rng: random.Random,
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
VP_PER_PLAYER_PATTERN = re.compile(r"Put (\d+) VP here per player\.")

STARTING_COPPER_COUNT = 7
STARTING_ESTATE_COUNT = 3
# Shelters replace the starting Estates
SHELTER_NAMES: tuple[str, ...] = ("Hovel", "Necropolis", "Overgrown Estate")


def _setup_instructions(
    cards: list[Card],
    heirlooms: list[Card],
    sort_order: KingdomSortOrder,
    *,
    players: int | None = None,
) -> list[SetupInstruction]:
    """Return the "Setup:" instructions of *cards*, plus the starting decks.

    The starting decks are described if they differ from the usual 7 Coppers
    and 3 Estates: with Shelters (if in *cards*), or with *heirlooms*. This
    replaces Shelters' own setup, which also says when to use Shelters.

    With *players*, the VP to put on a Landmark "per player" (e.g. Arena) are
    counted out.
    """
    setup_instructions = [
        SetupInstruction(card.name, setup_match.group(1))
        for card in sorted(cards, key=sort_order.sort_key)
        if card.name != "Shelters"
        and (setup_match := SETUP_PATTERN.search(card.instructions))
    ]
    if players is not None:

        def count_out_vp(match: re.Match[str]) -> str:
            vp_per_player = int(match.group(1))
            return f"Put {vp_per_player * players} VP here ({vp_per_player} VP per player)."

        setup_instructions = [
            replace(
                instruction,
                text=VP_PER_PLAYER_PATTERN.sub(count_out_vp, instruction.text),
            )
            for instruction in setup_instructions
        ]
    use_shelters = any(card.name == "Shelters" for card in cards)
    if use_shelters or heirlooms:
        # each Heirloom replaces a starting Copper
        starting_cards = [
            f"{STARTING_COPPER_COUNT - len(heirlooms)} Coppers",
            *(heirloom.name for heirloom in heirlooms),
        ]
        if use_shelters:
            starting_cards += SHELTER_NAMES
        else:
            starting_cards.append(f"{STARTING_ESTATE_COUNT} Estates")
        starting_decks = f"Each player starts with {', '.join(starting_cards)}."
        if heirlooms:
            starting_decks += " The unused Coppers go in the Copper pile."
        setup_instructions.append(SetupInstruction("Starting decks", starting_decks))
    return setup_instructions


# ── 9. Pile sizes ────────────────────────────────────────────────────────────

MIN_PLAYERS = 2
MAX_PLAYERS = 6

# Sizes of the piles made of several different cards, whose own card has no
# quantity.
MIXED_PILE_SIZES: dict[str, int] = {
    "Knights": 10,
    "Catapult/Rocks": 10,
    "Encampment/Plunder": 10,
    "Gladiator/Fortune": 10,
    "Patrician/Emporium": 10,
    "Settlers/Bustling Village": 10,
    "Sauna/Avanto": 10,
    "Augurs": 16,
    "Clashes": 16,
    "Forts": 16,
    "Odysseys": 16,
    "Townsfolk": 16,
    "Wizards": 16,
    "Boons": 12,
    "Hexes": 12,
    "Loot": 30,
}

# with five or six players, use 15 or 18 Provinces
PROVINCE_COUNTS: dict[int, int] = {5: 15, 6: 18}


def _pile_size(card: Card, *, players: int, heirloom_count: int) -> int | None:
    """Return how many cards go in the pile of *card* in a game with *players* players.

    Returns ``None`` for Shelters and Heirlooms, which go into the starting
    decks instead. Each of the *heirloom_count* Heirlooms replaces a starting
    Copper, which stays in the Copper pile.
    """
    if card.name == "Shelters" or CardType.HEIRLOOM in card.types:
        return None
    # use 10 Curses (and Ruins) per player after the first
    if card.name in {"Curse", "Ruins"}:
        return 10 * (players - 1)
    # each player starts with 7 Coppers; the rest form the Copper pile
    if card.name == "Copper":
        return card.quantity - (STARTING_COPPER_COUNT - heirloom_count) * players
    if card.name == "Province" and players in PROVINCE_COUNTS:
        return PROVINCE_COUNTS[players]
    # use 8 of each Victory pile (e.g. Estate, Gardens, Castles) for two
    # players, and 12 otherwise
    if CardType.VICTORY in card.types and (card.is_basic or card.is_kingdom):
        return 8 if players == 2 else 12  # noqa: PLR2004
    return MIXED_PILE_SIZES.get(card.name, card.quantity)


# ── Helpers ──────────────────────────────────────────────────────────────────


def _cards_of_type(cards: Iterable[Card], card_type: CardType) -> list[Card]:
    """Return the cards in *cards* that have *card_type*, preserving order."""
    return [card for card in cards if card_type in card.types]
