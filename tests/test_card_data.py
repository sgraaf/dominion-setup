"""Tests for the bundled card data in ``data/cards/*.json``.

These pin down facts about the cards themselves, so that re-scraping the card
list cannot silently add, drop or change cards.
"""

import pytest

from dominion_setup.cli import SET_EDITION_CHOICES
from dominion_setup.models import (
    CARD_SETS_WITH_SECOND_EDITIONS,
    Card,
    CardCost,
    CardDatabase,
    CardSet,
    CardSetEdition,
    CardType,
)

# ── Sets & editions ──────────────────────────────────────────────────────────


def test_basic_cards(db: CardDatabase) -> None:
    assert set(db.basic_cards) == {
        "Copper",
        "Silver",
        "Gold",
        "Estate",
        "Duchy",
        "Province",
        "Curse",
        "Potion",
        "Platinum",
        "Colony",
        "Ruins",
        "Shelters",
    }


def test_kingdom_card_count(db: CardDatabase) -> None:
    assert len(db.kingdom_cards) == 498


KINGDOM_CARD_COUNTS: dict[str, int] = {
    "base_1e": 25,
    "base_2e": 26,
    "intrigue_1e": 25,
    "intrigue_2e": 26,
    "seaside_1e": 26,
    "seaside_2e": 27,
    "alchemy": 12,
    "prosperity_1e": 25,
    "prosperity_2e": 25,
    "cornucopia_guilds_1e": 26,
    "cornucopia_guilds_2e": 26,
    "hinterlands_1e": 26,
    "hinterlands_2e": 26,
    "dark_ages": 35,
    "adventures": 30,
    "empires": 24,
    "nocturne": 33,
    "renaissance": 25,
    "menagerie": 30,
    "allies": 31,
    "plunder": 40,
    "rising_sun": 25,
    "promo": 11,
}


@pytest.mark.parametrize(
    ("choice", "count"), KINGDOM_CARD_COUNTS.items(), ids=KINGDOM_CARD_COUNTS
)
def test_kingdom_card_count_per_set_edition(
    db: CardDatabase, choice: str, count: int
) -> None:
    assert len(db.get_cards_by_set_edition(*SET_EDITION_CHOICES[choice])) == count


def test_sets_with_a_second_edition(db: CardDatabase) -> None:
    sets = {card.set for card in db if CardSetEdition.SECOND_EDITION in card.editions}
    assert sets == CARD_SETS_WITH_SECOND_EDITIONS


EDITION_EXCLUSIVE_CARDS: dict[str, set[str]] = {
    "base_1e": {"Adventurer", "Chancellor", "Feast", "Spy", "Thief", "Woodcutter"},
    "base_2e": {
        "Artisan",
        "Bandit",
        "Harbinger",
        "Merchant",
        "Poacher",
        "Sentry",
        "Vassal",
    },
    "intrigue_1e": {
        "Coppersmith",
        "Great Hall",
        "Saboteur",
        "Scout",
        "Secret Chamber",
        "Tribute",
    },
    "intrigue_2e": {
        "Courtier",
        "Diplomat",
        "Lurker",
        "Mill",
        "Patrol",
        "Replace",
        "Secret Passage",
    },
    "seaside_1e": {
        "Ambassador",
        "Embargo",
        "Explorer",
        "Ghost Ship",
        "Navigator",
        "Pearl Diver",
        "Pirate Ship",
        "Sea Hag",
    },
    "seaside_2e": {
        "Astrolabe",
        "Blockade",
        "Corsair",
        "Monkey",
        "Pirate",
        "Sailor",
        "Sea Chart",
        "Sea Witch",
        "Tide Pools",
    },
    "prosperity_1e": {
        "Contraband",
        "Counting House",
        "Goons",
        "Loan",
        "Mountebank",
        "Royal Seal",
        "Talisman",
        "Trade Route",
        "Venture",
    },
    "prosperity_2e": {
        "Anvil",
        "Charlatan",
        "Clerk",
        "Collection",
        "Crystal Ball",
        "Investment",
        "Magnate",
        "Tiara",
        "War Chest",
    },
    "cornucopia_guilds_1e": {
        "Doctor",
        "Farming Village",
        "Fortune Teller",
        "Harvest",
        "Horse Traders",
        "Masterpiece",
        "Taxman",
        "Tournament",
    },
    "cornucopia_guilds_2e": {
        "Carnival",
        "Farmhands",
        "Farrier",
        "Ferryman",
        "Footpad",
        "Infirmary",
        "Joust",
        "Shop",
    },
    "hinterlands_1e": {
        "Cache",
        "Duchess",
        "Embassy",
        "Ill-Gotten Gains",
        "Mandarin",
        "Noble Brigand",
        "Nomad Camp",
        "Oracle",
        "Silk Road",
    },
    "hinterlands_2e": {
        "Berserker",
        "Cauldron",
        "Guard Dog",
        "Nomads",
        "Souk",
        "Trail",
        "Weaver",
        "Wheelwright",
        "Witch's Hut",
    },
}


@pytest.mark.parametrize(
    ("choice", "names"), EDITION_EXCLUSIVE_CARDS.items(), ids=EDITION_EXCLUSIVE_CARDS
)
def test_kingdom_cards_in_one_edition_only(
    db: CardDatabase, choice: str, names: set[str]
) -> None:
    set_, edition = SET_EDITION_CHOICES[choice]
    cards = db.get_cards_by_set_edition(set_, edition)
    assert {card.name for card in cards if card.editions == (edition,)} == names


# ── Kingdom cards by type ────────────────────────────────────────────────────

KINGDOM_CARDS_BY_TYPE: dict[CardType, set[str]] = {
    CardType.ATTACK: {
        # Base
        "Bandit",
        "Bureaucrat",
        "Militia",
        "Spy",
        "Thief",
        "Witch",
        # Intrigue
        "Minion",
        "Replace",
        "Saboteur",
        "Swindler",
        "Torturer",
        # Seaside
        "Ambassador",
        "Blockade",
        "Corsair",
        "Cutpurse",
        "Ghost Ship",
        "Pirate Ship",
        "Sea Hag",
        "Sea Witch",
        # Alchemy
        "Familiar",
        "Scrying Pool",
        # Prosperity
        "Charlatan",
        "Clerk",
        "Goons",
        "Mountebank",
        "Rabble",
        # Cornucopia & Guilds
        "Footpad",
        "Fortune Teller",
        "Jester",
        "Soothsayer",
        "Taxman",
        "Young Witch",
        # Hinterlands
        "Berserker",
        "Cauldron",
        "Margrave",
        "Noble Brigand",
        "Oracle",
        "Witch's Hut",
        # Dark Ages
        "Cultist",
        "Knights",
        "Marauder",
        "Pillage",
        "Rogue",
        "Urchin",
        # Adventures
        "Bridge Troll",
        "Giant",
        "Haunted Woods",
        "Relic",
        "Swamp Hag",
        # Empires
        "Catapult/Rocks",
        "Enchantress",
        "Legionary",
        # Nocturne
        "Idol",
        "Raider",
        "Skulk",
        "Tormentor",
        "Vampire",
        "Werewolf",
        # Renaissance
        "Old Witch",
        "Villain",
        # Menagerie
        "Black Cat",
        "Cardinal",
        "Coven",
        "Gatekeeper",
        # Allies
        "Barbarian",
        "Highwayman",
        "Skirmisher",
        # Plunder
        "Cutthroat",
        "Frigate",
        "Siren",
        "Trickster",
        # Rising Sun
        "Kitsune",
        "Ninja",
        "Samurai",
        "Snake Witch",
    },
    CardType.DURATION: {
        # Seaside
        "Astrolabe",
        "Blockade",
        "Caravan",
        "Corsair",
        "Fishing Village",
        "Haven",
        "Lighthouse",
        "Merchant Ship",
        "Monkey",
        "Outpost",
        "Pirate",
        "Sailor",
        "Sea Witch",
        "Tactician",
        "Tide Pools",
        "Wharf",
        # Adventures
        "Amulet",
        "Bridge Troll",
        "Caravan Guard",
        "Dungeon",
        "Gear",
        "Haunted Woods",
        "Hireling",
        "Swamp Hag",
        # Empires
        "Archive",
        "Enchantress",
        # Nocturne
        "Cobbler",
        "Crypt",
        "Den of Sin",
        "Ghost Town",
        "Guardian",
        "Raider",
        "Secret Cave",
        # Renaissance
        "Cargo Ship",
        "Research",
        # Menagerie
        "Barge",
        "Gatekeeper",
        "Mastermind",
        "Village Green",
        # Allies
        "Contract",
        "Highwayman",
        "Importer",
        "Royal Galley",
        # Plunder
        "Abundance",
        "Buried Treasure",
        "Cabin Boy",
        "Cage",
        "Crew",
        "Cutthroat",
        "Enlarge",
        "Flagship",
        "Frigate",
        "Gondola",
        "Grotto",
        "Landing Party",
        "Longship",
        "Quartermaster",
        "Rope",
        "Search",
        "Secluded Shrine",
        "Siren",
        "Stowaway",
        "Taskmaster",
        # Rising Sun
        "Riverboat",
        "Samurai",
        # Promo
        "Captain",
        "Church",
        "Prince",
    },
    CardType.REACTION: {
        # Base
        "Moat",
        # Intrigue
        "Diplomat",
        "Secret Chamber",
        # Seaside
        "Pirate",
        # Prosperity
        "Clerk",
        "Watchtower",
        # Cornucopia & Guilds
        "Horse Traders",
        # Hinterlands
        "Fool's Gold",
        "Guard Dog",
        "Trader",
        "Trail",
        "Tunnel",
        "Weaver",
        # Dark Ages
        "Beggar",
        "Market Square",
        # Adventures
        "Caravan Guard",
        # Nocturne
        "Faithful Hound",
        # Renaissance
        "Patron",
        # Menagerie
        "Black Cat",
        "Falconer",
        "Sheepdog",
        "Sleigh",
        "Village Green",
        # Plunder
        "Mapmaker",
        "Stowaway",
    },
    CardType.LOOTER: {
        # Dark Ages
        "Cultist",
        "Death Cart",
        "Marauder",
    },
    CardType.OMEN: {
        # Rising Sun
        "Kitsune",
        "Mountain Shrine",
        "Poet",
        "River Shrine",
        "Rustic Village",
        "Tea House",
    },
    CardType.SHADOW: {
        # Rising Sun
        "Alley",
        "Fishmonger",
        "Ninja",
        "Ronin",
        "Tanuki",
    },
}


@pytest.mark.parametrize(
    ("card_type", "names"),
    KINGDOM_CARDS_BY_TYPE.items(),
    ids=[str(card_type) for card_type in KINGDOM_CARDS_BY_TYPE],
)
def test_kingdom_cards_by_type(
    db: CardDatabase, card_type: CardType, names: set[str]
) -> None:
    assert {card.name for card in db.get_cards_by_type(card_type)} == names


def test_kingdom_piles_made_of_other_cards(db: CardDatabase) -> None:
    """Split piles, mixed piles and the like list their cards separately."""
    assert {card.name for card in db.kingdom_cards.values() if card.quantity == 0} == {
        "Augurs",
        "Castles",
        "Catapult/Rocks",
        "Clashes",
        "Encampment/Plunder",
        "Forts",
        "Gladiator/Fortune",
        "Knights",
        "Odysseys",
        "Patrician/Emporium",
        "Sauna/Avanto",
        "Settlers/Bustling Village",
        "Townsfolk",
        "Wizards",
    }


# ── Other cards ──────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("set_", "card_type", "names"),
    [
        pytest.param(
            CardSet.DARK_AGES,
            CardType.KNIGHT,
            {
                "Dame Anna",
                "Dame Josephine",
                "Dame Molly",
                "Dame Natalie",
                "Dame Sylvia",
                "Sir Bailey",
                "Sir Destry",  # codespell:ignore
                "Sir Martin",
                "Sir Michael",
                "Sir Vander",
            },
            id="Knights",
        ),
        pytest.param(
            CardSet.DARK_AGES,
            CardType.RUINS,
            {
                "Abandoned Mine",
                "Ruined Library",
                "Ruined Market",
                "Ruined Village",
                "Survivors",
            },
            id="Ruins",
        ),
        pytest.param(
            CardSet.EMPIRES,
            None,
            {
                "Bustling Village",
                "Catapult",
                "Crumbling Castle",
                "Emporium",
                "Encampment",
                "Fortune",
                "Gladiator",
                "Grand Castle",
                "Haunted Castle",
                "Humble Castle",
                "King's Castle",
                "Opulent Castle",
                "Patrician",
                "Plunder",
                "Rocks",
                "Settlers",
                "Small Castle",
                "Sprawling Castle",
            },
            id="Empires",
        ),
        pytest.param(
            CardSet.ALLIES,
            None,
            {
                # Augurs
                "Herb Gatherer",
                "Acolyte",
                "Sorceress",
                "Sibyl",
                # Clashes
                "Battle Plan",
                "Archer",
                "Warlord",
                "Territory",
                # Forts
                "Tent",
                "Garrison",
                "Hill Fort",
                "Stronghold",
                # Odysseys
                "Old Map",
                "Voyage",
                "Sunken Treasure",
                "Distant Shore",
                # Townsfolk
                "Town Crier",
                "Blacksmith",
                "Miller",
                "Elder",
                # Wizards
                "Student",
                "Conjurer",
                "Sorcerer",
                "Lich",
            },
            id="Allies",
        ),
        pytest.param(
            CardSet.PLUNDER,
            CardType.LOOT,
            {
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
            },
            id="Loot",
        ),
        pytest.param(CardSet.PROMO, None, {"Avanto", "Sauna"}, id="Promo"),
    ],
)
def test_mixed_pile_cards(
    db: CardDatabase, set_: CardSet, card_type: CardType | None, names: set[str]
) -> None:
    assert {
        card.name
        for card in db.mixed_pile_cards.values()
        if card.set == set_ and (card_type is None or card_type in card.types)
    } == names


def test_loot_cards_cost_seven_star(db: CardDatabase) -> None:
    for card in db.mixed_pile_cards.values():
        if CardType.LOOT in card.types:
            assert str(card.cost) == "$7*"
            assert card.set == CardSet.PLUNDER


def test_artifacts(db: CardDatabase) -> None:
    artifacts = {
        card.name
        for card in db.status_cards.values()
        if CardType.ARTIFACT in card.types
    }
    assert artifacts == {"Flag", "Horn", "Key", "Lantern", "Treasure Chest"}


@pytest.mark.parametrize(
    ("set_", "card_type", "count"),
    [
        (CardSet.MENAGERIE, CardType.WAY, 20),
        (CardSet.MENAGERIE, CardType.EVENT, 20),
        (CardSet.ALLIES, CardType.ALLY, 23),
        (CardSet.PLUNDER, CardType.TRAIT, 15),
        (CardSet.PLUNDER, CardType.EVENT, 15),
        (CardSet.RISING_SUN, CardType.PROPHECY, 15),
        (CardSet.RISING_SUN, CardType.EVENT, 10),
    ],
)
def test_landscape_count(
    db: CardDatabase, set_: CardSet, card_type: CardType, count: int
) -> None:
    landscapes = [
        card
        for card in db.landscape_cards.values()
        if card.set == set_ and card_type in card.types
    ]
    assert len(landscapes) == count


def test_menagerie_landscapes(db: CardDatabase) -> None:
    menagerie = [
        card for card in db.landscape_cards.values() if card.set == CardSet.MENAGERIE
    ]
    assert {card.name for card in menagerie if CardType.WAY in card.types} == {
        "Way of the Butterfly",
        "Way of the Camel",
        "Way of the Chameleon",
        "Way of the Frog",
        "Way of the Goat",
        "Way of the Horse",
        "Way of the Mole",
        "Way of the Monkey",
        "Way of the Mouse",
        "Way of the Mule",
        "Way of the Otter",
        "Way of the Owl",
        "Way of the Ox",
        "Way of the Pig",
        "Way of the Rat",
        "Way of the Seal",
        "Way of the Sheep",
        "Way of the Squirrel",
        "Way of the Turtle",
        "Way of the Worm",
    }
    assert {card.name for card in menagerie if CardType.EVENT in card.types} == {
        "Alliance",
        "Banish",
        "Bargain",
        "Commerce",
        "Delay",
        "Demand",
        "Desperation",
        "Enclave",
        "Enhance",
        "Gamble",
        "Invest",
        "March",
        "Populate",
        "Pursue",
        "Reap",
        "Ride",
        "Seize the Day",
        "Stampede",
        "Toil",
        "Transport",
    }


def test_ways_cost_nothing(db: CardDatabase) -> None:
    for card in db.landscape_cards.values():
        if CardType.WAY in card.types:
            assert card.cost == CardCost()


# ── Individual cards ─────────────────────────────────────────────────────────


def describe(card: Card) -> str:
    """Summarise *card* on one line: purpose | types | cost | set | quantity.

    For a set with a second edition, the set reads e.g. "Base" for a card in
    both editions and "Base, 1E" for a card in the first edition only.
    """
    return " | ".join(
        [
            card.purpose,
            ", ".join(card.types),
            str(card.cost),
            card.display_set,
            str(card.quantity),
        ]
    )


CARDS: dict[str, str] = {
    # Base
    "Witch": "Kingdom Pile | Action, Attack | $5 | Base | 10",
    # Intrigue
    "Minion": "Kingdom Pile | Action, Attack | $5 | Intrigue | 10",
    "Harem": "Kingdom Pile | Treasure, Victory | $6 | Intrigue | 12",
    # Seaside
    "Wharf": "Kingdom Pile | Action, Duration | $5 | Seaside | 10",
    "Ghost Ship": "Kingdom Pile | Action, Attack | $5 | Seaside, 1E | 10",
    "Corsair": "Kingdom Pile | Action, Duration, Attack | $5 | Seaside, 2E | 10",
    "Bazaar": "Kingdom Pile | Action | $5 | Seaside | 10",
    # Alchemy
    "Familiar": "Kingdom Pile | Action, Attack | $3P | Alchemy | 10",
    "Herbalist": "Kingdom Pile | Action | $2 | Alchemy | 10",
    "Potion": "Basic | Treasure | $4 | Alchemy | 16",
    # Prosperity
    "King's Court": "Kingdom Pile | Action | $7 | Prosperity | 10",
    "Goons": "Kingdom Pile | Action, Attack | $6 | Prosperity, 1E | 10",
    "Charlatan": "Kingdom Pile | Action, Attack | $5 | Prosperity, 2E | 10",
    "Bank": "Kingdom Pile | Treasure | $7 | Prosperity | 10",
    "Quarry": "Kingdom Pile | Treasure | $4 | Prosperity | 10",
    "Clerk": "Kingdom Pile | Action, Reaction, Attack | $4 | Prosperity, 2E | 10",
    "Platinum": "Basic | Treasure | $9 | Prosperity | 12",
    "Colony": "Basic | Victory | $11 | Prosperity | 12",
    # Cornucopia & Guilds
    "Baker": "Kingdom Pile | Action | $5 | Cornucopia & Guilds | 10",
    "Tournament": "Kingdom Pile | Action | $4 | Cornucopia & Guilds, 1E | 10",
    "Carnival": "Kingdom Pile | Action | $5 | Cornucopia & Guilds, 2E | 10",
    "Hamlet": "Kingdom Pile | Action | $2 | Cornucopia & Guilds | 10",
    "Herald": "Kingdom Pile | Action | $4+ | Cornucopia & Guilds | 10",
    "Bag of Gold": "Non-Supply | Action, Prize | $0* | Cornucopia & Guilds, 1E | 1",
    "Coronet": "Non-Supply | Action, Treasure, Reward | $0* | Cornucopia & Guilds, 2E | 2",
    "Fairgrounds": "Kingdom Pile | Victory | $6 | Cornucopia & Guilds | 12",
    # Hinterlands
    "Margrave": "Kingdom Pile | Action, Attack | $5 | Hinterlands | 10",
    "Cache": "Kingdom Pile | Treasure | $5 | Hinterlands, 1E | 10",
    "Berserker": "Kingdom Pile | Action, Attack | $5 | Hinterlands, 2E | 10",
    "Border Village": "Kingdom Pile | Action | $6 | Hinterlands | 10",
    "Farmland": "Kingdom Pile | Victory | $6 | Hinterlands | 12",
    "Fool's Gold": "Kingdom Pile | Treasure, Reaction | $2 | Hinterlands | 10",
    # Dark Ages
    "Altar": "Kingdom Pile | Action | $6 | Dark Ages | 10",
    "Counterfeit": "Kingdom Pile | Treasure | $5 | Dark Ages | 10",
    "Feodum": "Kingdom Pile | Victory | $4 | Dark Ages | 12",
    "Knights": "Kingdom Pile | Action, Attack, Knight | $5 | Dark Ages | 0",
    "Dame Josephine": "Mixed Pile Card | Action, Attack, Knight, Victory | $5 | Dark Ages | 1",
    "Spoils": "Non-Supply | Treasure | $0* | Dark Ages | 15",
    "Madman": "Non-Supply | Action | $0* | Dark Ages | 10",
    "Mercenary": "Non-Supply | Action, Attack | $0* | Dark Ages | 10",
    "Rats": "Kingdom Pile | Action | $4 | Dark Ages | 20",
    "Band of Misfits": "Kingdom Pile | Action, Command | $5 | Dark Ages | 10",
    "Beggar": "Kingdom Pile | Action, Reaction | $2 | Dark Ages | 10",
    "Market Square": "Kingdom Pile | Action, Reaction | $3 | Dark Ages | 10",
    # Empires
    "Archive": "Kingdom Pile | Action, Duration | $5 | Empires | 10",
    "Engineer": "Kingdom Pile | Action | 4D | Empires | 10",
    "City Quarter": "Kingdom Pile | Action | 8D | Empires | 10",
    "Castles": "Kingdom Pile | Victory, Castle | $3 | Empires | 0",
    "Farmers' Market": "Kingdom Pile | Action, Gathering | $3 | Empires | 10",
    "Wild Hunt": "Kingdom Pile | Action, Gathering | $5 | Empires | 10",
    "Temple": "Kingdom Pile | Action, Gathering | $4 | Empires | 10",
    "Catapult/Rocks": "Kingdom Pile | Action, Attack | $3 | Empires | 0",
    "Arena": "Landscape | Landmark | $0 | Empires | 1",
    "Donate": "Landscape | Event | 8D | Empires | 1",
    "Overlord": "Kingdom Pile | Action, Command | 8D | Empires | 10",
    # Renaissance
    "Old Witch": "Kingdom Pile | Action, Attack | $5 | Renaissance | 10",
    "Ducat": "Kingdom Pile | Treasure | $2 | Renaissance | 10",
    "Cargo Ship": "Kingdom Pile | Action, Duration | $3 | Renaissance | 10",
    "Scepter": "Kingdom Pile | Treasure, Command | $5 | Renaissance | 10",
    "Patron": "Kingdom Pile | Action, Reaction | $4 | Renaissance | 10",
    "Academy": "Landscape | Project | $5 | Renaissance | 1",
    "Flag": "Status | Artifact | $0 | Renaissance | 1",
    # Menagerie
    "Barge": "Kingdom Pile | Action, Duration | $5 | Menagerie | 10",
    "Stockpile": "Kingdom Pile | Treasure | $3 | Menagerie | 10",
    "Supplies": "Kingdom Pile | Treasure | $2 | Menagerie | 10",
    "Fisherman": "Kingdom Pile | Action | $5* | Menagerie | 10",
    "Destrier": "Kingdom Pile | Action | $6* | Menagerie | 10",
    "Wayfarer": "Kingdom Pile | Action | $6* | Menagerie | 10",
    "Animal Fair": "Kingdom Pile | Action | $7* | Menagerie | 10",
    "Way of the Butterfly": "Landscape | Way | $0 | Menagerie | 1",
    "Ride": "Landscape | Event | $2 | Menagerie | 1",
    "Horse": "Non-Supply | Action | $3* | Menagerie | 30",
    "Black Cat": "Kingdom Pile | Action, Attack, Reaction | $2 | Menagerie | 10",
    "Village Green": "Kingdom Pile | Action, Duration, Reaction | $4 | Menagerie | 10",
    "Gatekeeper": "Kingdom Pile | Action, Duration, Attack | $5 | Menagerie | 10",
    "Delay": "Landscape | Event | $0 | Menagerie | 1",
    "Desperation": "Landscape | Event | $0 | Menagerie | 1",
    "Alliance": "Landscape | Event | $10 | Menagerie | 1",
    "Populate": "Landscape | Event | $10 | Menagerie | 1",
    "Enclave": "Landscape | Event | $8 | Menagerie | 1",
    # Allies
    "Barbarian": "Kingdom Pile | Action, Attack | $5 | Allies | 10",
    "Sycophant": "Kingdom Pile | Action, Liaison | $2 | Allies | 10",
    "Architects' Guild": "Landscape | Ally | $0 | Allies | 1",
    "Bauble": "Kingdom Pile | Treasure, Liaison | $2 | Allies | 10",
    # Plunder
    "Cutthroat": "Kingdom Pile | Action, Duration, Attack | $5 | Plunder | 10",
    "Abundance": "Kingdom Pile | Treasure, Duration | $4 | Plunder | 10",
    "Flagship": "Kingdom Pile | Action, Duration, Command | $4 | Plunder | 10",
    "Loot": "Non-Supply | Treasure, Loot | $7* | Plunder | 0",
    "Doubloons": "Mixed Pile Card | Treasure, Loot | $7* | Plunder | 2",
    "Cheap": "Landscape | Trait | $0 | Plunder | 1",
    "Looting": "Landscape | Event | $6 | Plunder | 1",
    "Shield": "Mixed Pile Card | Treasure, Reaction, Loot | $7* | Plunder | 2",
    "Spell Scroll": "Mixed Pile Card | Action, Treasure, Loot | $7* | Plunder | 2",
    # Rising Sun
    "Ninja": "Kingdom Pile | Action, Attack, Shadow | $4 | Rising Sun | 10",
    "Artist": "Kingdom Pile | Action | 8D | Rising Sun | 10",
    "Continue": "Landscape | Event | 8D | Rising Sun | 1",
    "Daimyo": "Kingdom Pile | Action, Command | 6D | Rising Sun | 10",
    "Rice": "Kingdom Pile | Treasure | $7 | Rising Sun | 10",
    "Approaching Army": "Landscape | Prophecy | $0 | Rising Sun | 1",
    "Kitsune": "Kingdom Pile | Action, Attack, Omen | $5 | Rising Sun | 10",
    "Samurai": "Kingdom Pile | Action, Duration, Attack | $6 | Rising Sun | 10",
    # Promo
    "Black Market": "Kingdom Pile | Action | $3 | Promo | 10",
    "Summon": "Landscape | Event | $5 | Promo | 1",
    "Sauna/Avanto": "Kingdom Pile | Action | $4 | Promo | 0",
    "Sauna": "Mixed Pile Card | Action | $4 | Promo | 5",
    "Avanto": "Mixed Pile Card | Action | $5 | Promo | 5",
    "Marchland": "Kingdom Pile | Victory | $5 | Promo | 12",
    "Captain": "Kingdom Pile | Action, Duration, Command | $6 | Promo | 10",
    "Prince": "Kingdom Pile | Action, Duration, Command | $8 | Promo | 10",
    "Stash": "Kingdom Pile | Treasure | $5 | Promo | 10",
}


@pytest.mark.parametrize(("name", "description"), CARDS.items(), ids=CARDS)
def test_card(db: CardDatabase, name: str, description: str) -> None:
    assert describe(db.get_card_by_name(name)) == description
