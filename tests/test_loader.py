from dominion_setup.loader import load_card_database
from dominion_setup.models import (
    CardDatabase,
    CardPurpose,
    CardSet,
    CardSetEdition,
    CardType,
)


def test_load_card_database_returns_card_database() -> None:
    db = load_card_database()
    assert isinstance(db, CardDatabase)


def test_basic_cards_loaded(db: CardDatabase) -> None:
    assert len(db.basic_cards) == 12
    expected = {
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
    assert set(db.basic_cards) == expected


def test_kingdom_cards_loaded(db: CardDatabase) -> None:
    assert len(db.kingdom_cards) == 498


def test_card_fields_parsed_correctly(db: CardDatabase) -> None:
    witch = db.kingdom_cards["Witch"]
    assert witch.cost.coins == 5
    assert witch.types == (CardType.ACTION, CardType.ATTACK)
    assert witch.set == CardSet.BASE


def test_get_base_1e_cards_by_set(db: CardDatabase) -> None:
    cards = db.get_cards_by_set_edition(
        CardSet.BASE, edition=CardSetEdition.FIRST_EDITION
    )
    assert len(cards) == 25


def test_get_base_2e_cards_by_set(db: CardDatabase) -> None:
    cards = db.get_cards_by_set_edition(
        CardSet.BASE, edition=CardSetEdition.SECOND_EDITION
    )
    assert len(cards) == 26


def test_get_cards_by_type_attack(db: CardDatabase) -> None:
    attacks = db.get_cards_by_type(CardType.ATTACK)
    assert len(attacks) == 75
    names = {c.name for c in attacks}
    assert names == {
        "Bureaucrat",
        "Militia",
        "Bandit",
        "Witch",
        "Spy",
        "Thief",
        "Swindler",
        "Minion",
        "Saboteur",
        "Torturer",
        "Replace",
        "Ambassador",
        "Cutpurse",
        "Pirate Ship",
        "Sea Hag",
        "Ghost Ship",
        "Blockade",
        "Corsair",
        "Sea Witch",
        "Familiar",
        "Scrying Pool",
        "Charlatan",
        "Clerk",
        "Goons",
        "Mountebank",
        "Rabble",
        "Fortune Teller",
        "Jester",
        "Soothsayer",
        "Taxman",
        "Young Witch",
        "Footpad",
        "Berserker",
        "Cauldron",
        "Margrave",
        "Noble Brigand",
        "Oracle",
        "Witch's Hut",
        "Cultist",
        "Knights",
        "Marauder",
        "Pillage",
        "Rogue",
        "Urchin",
        "Bridge Troll",
        "Giant",
        "Haunted Woods",
        "Relic",
        "Swamp Hag",
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
    }


def test_get_cards_by_type_reaction(db: CardDatabase) -> None:
    reactions = db.get_cards_by_type(CardType.REACTION)
    assert len(reactions) == 25
    names = {c.name for c in reactions}
    assert names == {
        "Moat",
        "Secret Chamber",
        "Diplomat",
        "Pirate",
        "Watchtower",
        "Clerk",
        "Horse Traders",
        "Fool's Gold",
        "Guard Dog",
        "Trader",
        "Trail",
        "Tunnel",
        "Weaver",
        "Beggar",
        "Market Square",
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
    }


def test_get_intrigue_1e_cards_by_set(db: CardDatabase) -> None:
    cards = db.get_cards_by_set_edition(CardSet.INTRIGUE, CardSetEdition.FIRST_EDITION)
    assert len(cards) == 25


def test_get_intrigue_2e_cards_by_set(db: CardDatabase) -> None:
    cards = db.get_cards_by_set_edition(
        CardSet.INTRIGUE, edition=CardSetEdition.SECOND_EDITION
    )
    assert len(cards) == 26


def test_intrigue_card_fields_parsed_correctly(db: CardDatabase) -> None:
    minion = db.kingdom_cards["Minion"]
    assert minion.cost.coins == 5
    assert minion.types == (CardType.ACTION, CardType.ATTACK)
    assert minion.set == CardSet.INTRIGUE


def test_intrigue_dual_type_treasure_victory(db: CardDatabase) -> None:
    harem = db.kingdom_cards["Harem"]
    assert harem.types == (CardType.TREASURE, CardType.VICTORY)


def test_get_alchemy_cards_by_set(db: CardDatabase) -> None:
    cards = db.get_cards_by_set_edition(CardSet.ALCHEMY, CardSetEdition.FIRST_EDITION)
    assert len(cards) == 12


def test_alchemy_card_fields_parsed_correctly(db: CardDatabase) -> None:
    familiar = db.kingdom_cards["Familiar"]
    assert familiar.cost.coins == 3
    assert familiar.cost.potion is True
    assert familiar.types == (CardType.ACTION, CardType.ATTACK)
    assert familiar.set == CardSet.ALCHEMY
    assert familiar.has_potion_cost is True


def test_alchemy_non_potion_card(db: CardDatabase) -> None:
    herbalist = db.kingdom_cards["Herbalist"]
    assert herbalist.cost.potion is False
    assert herbalist.has_potion_cost is False


def test_potion_base_card_loaded(db: CardDatabase) -> None:
    potion = db.basic_cards["Potion"]
    assert potion.types == (CardType.TREASURE,)
    assert potion.cost.coins == 4


def test_get_seaside_1e_cards_by_set(db: CardDatabase) -> None:
    cards = db.get_cards_by_set_edition(CardSet.SEASIDE, CardSetEdition.FIRST_EDITION)
    assert len(cards) == 26


def test_get_seaside_2e_cards_by_set(db: CardDatabase) -> None:
    cards = db.get_cards_by_set_edition(
        CardSet.SEASIDE, edition=CardSetEdition.SECOND_EDITION
    )
    assert len(cards) == 27


def test_seaside_card_fields_parsed_correctly(db: CardDatabase) -> None:
    wharf = db.kingdom_cards["Wharf"]
    assert wharf.cost.coins == 5
    assert wharf.types == (CardType.ACTION, CardType.DURATION)
    assert wharf.set == CardSet.SEASIDE


def test_seaside_1e_only_card(db: CardDatabase) -> None:
    ghost_ship = db.kingdom_cards["Ghost Ship"]
    assert ghost_ship.set == CardSet.SEASIDE
    assert ghost_ship.editions == (CardSetEdition.FIRST_EDITION,)


def test_seaside_2e_only_card(db: CardDatabase) -> None:
    corsair = db.kingdom_cards["Corsair"]
    assert corsair.set == CardSet.SEASIDE
    assert corsair.editions == (CardSetEdition.SECOND_EDITION,)


def test_seaside_both_editions_card(db: CardDatabase) -> None:
    bazaar = db.kingdom_cards["Bazaar"]
    assert bazaar.set == CardSet.SEASIDE
    assert bazaar.editions == (
        CardSetEdition.FIRST_EDITION,
        CardSetEdition.SECOND_EDITION,
    )


def test_seaside_duration_type(db: CardDatabase) -> None:
    durations = db.get_cards_by_type(CardType.DURATION)
    assert len(durations) == 68
    duration_names = {c.name for c in durations}
    assert "Wharf" in duration_names
    assert "Caravan" in duration_names
    assert "Astrolabe" in duration_names
    assert "Amulet" in duration_names
    assert "Bridge Troll" in duration_names
    assert "Archive" in duration_names
    assert "Enchantress" in duration_names
    assert "Riverboat" in duration_names
    assert "Samurai" in duration_names
    # Menagerie durations
    assert "Barge" in duration_names
    assert "Gatekeeper" in duration_names
    assert "Mastermind" in duration_names
    assert "Village Green" in duration_names


def test_get_prosperity_1e_cards_by_set(db: CardDatabase) -> None:
    cards = db.get_cards_by_set_edition(
        CardSet.PROSPERITY, CardSetEdition.FIRST_EDITION
    )
    assert len(cards) == 25


def test_get_prosperity_2e_cards_by_set(db: CardDatabase) -> None:
    cards = db.get_cards_by_set_edition(
        CardSet.PROSPERITY, edition=CardSetEdition.SECOND_EDITION
    )
    assert len(cards) == 25


def test_prosperity_card_fields_parsed_correctly(db: CardDatabase) -> None:
    kings_court = db.kingdom_cards["King's Court"]
    assert kings_court.cost.coins == 7
    assert kings_court.types == (CardType.ACTION,)
    assert kings_court.set == CardSet.PROSPERITY


def test_prosperity_1e_only_card(db: CardDatabase) -> None:
    goons = db.kingdom_cards["Goons"]
    assert goons.set == CardSet.PROSPERITY
    assert goons.editions == (CardSetEdition.FIRST_EDITION,)


def test_prosperity_2e_only_card(db: CardDatabase) -> None:
    charlatan = db.kingdom_cards["Charlatan"]
    assert charlatan.set == CardSet.PROSPERITY
    assert charlatan.editions == (CardSetEdition.SECOND_EDITION,)


def test_prosperity_both_editions_card(db: CardDatabase) -> None:
    bank = db.kingdom_cards["Bank"]
    assert bank.set == CardSet.PROSPERITY
    assert bank.editions == (
        CardSetEdition.FIRST_EDITION,
        CardSetEdition.SECOND_EDITION,
    )


def test_prosperity_treasure_kingdom_card(db: CardDatabase) -> None:
    quarry = db.kingdom_cards["Quarry"]
    assert quarry.types == (CardType.TREASURE,)
    assert quarry.cost.coins == 4


def test_prosperity_clerk_types(db: CardDatabase) -> None:
    clerk = db.kingdom_cards["Clerk"]
    assert clerk.types == (CardType.ACTION, CardType.REACTION, CardType.ATTACK)
    assert clerk.cost.coins == 4


def test_platinum_base_card_loaded(db: CardDatabase) -> None:
    platinum = db.basic_cards["Platinum"]
    assert platinum.types == (CardType.TREASURE,)
    assert platinum.cost.coins == 9


def test_colony_base_card_loaded(db: CardDatabase) -> None:
    colony = db.basic_cards["Colony"]
    assert colony.types == (CardType.VICTORY,)
    assert colony.cost.coins == 11


def test_get_cornucopia_guilds_1e_cards_by_set(db: CardDatabase) -> None:
    cards = db.get_cards_by_set_edition(
        CardSet.CORNUCOPIA_GUILDS, CardSetEdition.FIRST_EDITION
    )
    assert len(cards) == 26


def test_get_cornucopia_guilds_2e_cards_by_set(db: CardDatabase) -> None:
    cards = db.get_cards_by_set_edition(
        CardSet.CORNUCOPIA_GUILDS, edition=CardSetEdition.SECOND_EDITION
    )
    assert len(cards) == 26


def test_cornucopia_guilds_card_fields_parsed_correctly(db: CardDatabase) -> None:
    baker = db.kingdom_cards["Baker"]
    assert baker.cost.coins == 5
    assert baker.types == (CardType.ACTION,)
    assert baker.set == CardSet.CORNUCOPIA_GUILDS


def test_cornucopia_guilds_1e_only_card(db: CardDatabase) -> None:
    tournament = db.kingdom_cards["Tournament"]
    assert tournament.set == CardSet.CORNUCOPIA_GUILDS
    assert tournament.editions == (CardSetEdition.FIRST_EDITION,)


def test_cornucopia_guilds_2e_only_card(db: CardDatabase) -> None:
    carnival = db.kingdom_cards["Carnival"]
    assert carnival.set == CardSet.CORNUCOPIA_GUILDS
    assert carnival.editions == (CardSetEdition.SECOND_EDITION,)


def test_cornucopia_guilds_both_editions_card(db: CardDatabase) -> None:
    hamlet = db.kingdom_cards["Hamlet"]
    assert hamlet.set == CardSet.CORNUCOPIA_GUILDS
    assert hamlet.editions == (
        CardSetEdition.FIRST_EDITION,
        CardSetEdition.SECOND_EDITION,
    )


def test_cornucopia_guilds_overpay_cost(db: CardDatabase) -> None:
    herald = db.kingdom_cards["Herald"]
    assert herald.cost.coins == 4
    assert herald.cost.extra == "+"


def test_cornucopia_guilds_prize_type(db: CardDatabase) -> None:
    bag_of_gold = db.non_supply_cards["Bag of Gold"]
    assert CardType.PRIZE in bag_of_gold.types
    assert bag_of_gold.purpose == CardPurpose.NON_SUPPLY


def test_cornucopia_guilds_reward_type(db: CardDatabase) -> None:
    coronet = db.non_supply_cards["Coronet"]
    assert CardType.REWARD in coronet.types
    assert coronet.purpose == CardPurpose.NON_SUPPLY


def test_cornucopia_guilds_victory_kingdom_card(db: CardDatabase) -> None:
    fairgrounds = db.kingdom_cards["Fairgrounds"]
    assert CardType.VICTORY in fairgrounds.types
    assert fairgrounds.purpose == CardPurpose.KINGDOM_PILE
    assert fairgrounds.quantity == 12


def test_get_hinterlands_1e_cards_by_set(db: CardDatabase) -> None:
    cards = db.get_cards_by_set_edition(
        CardSet.HINTERLANDS, CardSetEdition.FIRST_EDITION
    )
    assert len(cards) == 26


def test_get_hinterlands_2e_cards_by_set(db: CardDatabase) -> None:
    cards = db.get_cards_by_set_edition(
        CardSet.HINTERLANDS, edition=CardSetEdition.SECOND_EDITION
    )
    assert len(cards) == 26


def test_hinterlands_card_fields_parsed_correctly(db: CardDatabase) -> None:
    margrave = db.kingdom_cards["Margrave"]
    assert margrave.cost.coins == 5
    assert margrave.types == (CardType.ACTION, CardType.ATTACK)
    assert margrave.set == CardSet.HINTERLANDS


def test_hinterlands_1e_only_card(db: CardDatabase) -> None:
    cache = db.kingdom_cards["Cache"]
    assert cache.set == CardSet.HINTERLANDS
    assert cache.editions == (CardSetEdition.FIRST_EDITION,)


def test_hinterlands_2e_only_card(db: CardDatabase) -> None:
    berserker = db.kingdom_cards["Berserker"]
    assert berserker.set == CardSet.HINTERLANDS
    assert berserker.editions == (CardSetEdition.SECOND_EDITION,)


def test_hinterlands_both_editions_card(db: CardDatabase) -> None:
    border_village = db.kingdom_cards["Border Village"]
    assert border_village.set == CardSet.HINTERLANDS
    assert border_village.editions == (
        CardSetEdition.FIRST_EDITION,
        CardSetEdition.SECOND_EDITION,
    )


def test_hinterlands_victory_kingdom_card(db: CardDatabase) -> None:
    farmland = db.kingdom_cards["Farmland"]
    assert CardType.VICTORY in farmland.types
    assert farmland.purpose == CardPurpose.KINGDOM_PILE
    assert farmland.quantity == 12


def test_hinterlands_dual_type_treasure_reaction(db: CardDatabase) -> None:
    fools_gold = db.kingdom_cards["Fool's Gold"]
    assert fools_gold.types == (CardType.TREASURE, CardType.REACTION)
    assert fools_gold.cost.coins == 2


def test_get_dark_ages_cards_by_set(db: CardDatabase) -> None:
    cards = db.get_cards_by_set_edition(CardSet.DARK_AGES, CardSetEdition.FIRST_EDITION)
    assert len(cards) == 35


def test_dark_ages_card_fields_parsed_correctly(db: CardDatabase) -> None:
    altar = db.kingdom_cards["Altar"]
    assert altar.cost.coins == 6
    assert altar.types == (CardType.ACTION,)
    assert altar.set == CardSet.DARK_AGES


def test_dark_ages_treasure_kingdom_card(db: CardDatabase) -> None:
    counterfeit = db.kingdom_cards["Counterfeit"]
    assert counterfeit.types == (CardType.TREASURE,)
    assert counterfeit.cost.coins == 5
    assert counterfeit.set == CardSet.DARK_AGES


def test_dark_ages_victory_kingdom_card(db: CardDatabase) -> None:
    feodum = db.kingdom_cards["Feodum"]
    assert CardType.VICTORY in feodum.types
    assert feodum.purpose == CardPurpose.KINGDOM_PILE
    assert feodum.quantity == 12


def test_dark_ages_looter_type(db: CardDatabase) -> None:
    looters = db.get_cards_by_type(CardType.LOOTER)
    assert len(looters) == 3
    assert {c.name for c in looters} == {"Cultist", "Death Cart", "Marauder"}


def test_dark_ages_knight_kingdom_pile(db: CardDatabase) -> None:
    knights = db.kingdom_cards["Knights"]
    assert CardType.KNIGHT in knights.types
    assert CardType.ATTACK in knights.types
    assert knights.set == CardSet.DARK_AGES
    assert knights.purpose == CardPurpose.KINGDOM_PILE


def test_dark_ages_mixed_pile_knights(db: CardDatabase) -> None:
    knight_names = {
        c.name
        for c in db.mixed_pile_cards.values()
        if c.set == CardSet.DARK_AGES and "Knight" in c.types
    }
    assert knight_names == {
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
    }


def test_dark_ages_mixed_pile_ruins(db: CardDatabase) -> None:
    ruins_names = {
        c.name
        for c in db.mixed_pile_cards.values()
        if c.set == CardSet.DARK_AGES and "Ruins" in c.types
    }
    assert ruins_names == {
        "Ruined Village",
        "Ruined Market",
        "Abandoned Mine",
        "Survivors",
        "Ruined Library",
    }


def test_dark_ages_dame_josephine_dual_type(db: CardDatabase) -> None:
    dame_josephine = db.mixed_pile_cards["Dame Josephine"]
    assert CardType.VICTORY in dame_josephine.types
    assert CardType.KNIGHT in dame_josephine.types
    assert CardType.ATTACK in dame_josephine.types


def test_dark_ages_ruins_in_basic_cards(db: CardDatabase) -> None:
    ruins = [c for c in db.basic_cards.values() if CardType.RUINS in c.types]
    assert len(ruins) == 1
    assert ruins[0].name == "Ruins"


def test_dark_ages_shelters_in_basic_cards(db: CardDatabase) -> None:
    shelters = [c for c in db.basic_cards.values() if CardType.SHELTER in c.types]
    assert len(shelters) == 1
    assert next(iter(shelters)).name == "Shelters"


def test_dark_ages_spoils_in_non_supply(db: CardDatabase) -> None:
    spoils = db.non_supply_cards["Spoils"]
    assert CardType.TREASURE in spoils.types
    assert spoils.set == CardSet.DARK_AGES


def test_dark_ages_madman_in_non_supply(db: CardDatabase) -> None:
    madman = db.non_supply_cards["Madman"]
    assert CardType.ACTION in madman.types
    assert madman.set == CardSet.DARK_AGES
    assert madman.cost.extra == "*"


def test_dark_ages_mercenary_in_non_supply(db: CardDatabase) -> None:
    mercenary = db.non_supply_cards["Mercenary"]
    assert CardType.ACTION in mercenary.types
    assert CardType.ATTACK in mercenary.types
    assert mercenary.set == CardSet.DARK_AGES
    assert mercenary.cost.extra == "*"


def test_dark_ages_rats_large_pile(db: CardDatabase) -> None:
    rats = db.kingdom_cards["Rats"]
    assert rats.quantity == 20
    assert rats.set == CardSet.DARK_AGES


def test_dark_ages_command_type(db: CardDatabase) -> None:
    band_of_misfits = db.kingdom_cards["Band of Misfits"]
    assert CardType.COMMAND in band_of_misfits.types
    assert band_of_misfits.cost.coins == 5


def test_dark_ages_reaction_kingdom_cards(db: CardDatabase) -> None:
    beggar = db.kingdom_cards["Beggar"]
    assert CardType.REACTION in beggar.types
    market_square = db.kingdom_cards["Market Square"]
    assert CardType.REACTION in market_square.types


def test_get_empires_cards_by_set(db: CardDatabase) -> None:
    cards = db.get_cards_by_set_edition(CardSet.EMPIRES, CardSetEdition.FIRST_EDITION)
    assert len(cards) == 24


def test_empires_card_fields_parsed_correctly(db: CardDatabase) -> None:
    archive = db.kingdom_cards["Archive"]
    assert archive.cost.coins == 5
    assert archive.types == (CardType.ACTION, CardType.DURATION)
    assert archive.set == CardSet.EMPIRES


def test_empires_debt_cost_card(db: CardDatabase) -> None:
    engineer = db.kingdom_cards["Engineer"]
    assert engineer.cost.debt == 4
    assert engineer.cost.coins == 0
    assert engineer.has_debt_cost is True
    assert engineer.set == CardSet.EMPIRES


def test_empires_debt_cost_action_card(db: CardDatabase) -> None:
    city_quarter = db.kingdom_cards["City Quarter"]
    assert city_quarter.cost.debt == 8
    assert city_quarter.types == (CardType.ACTION,)


def test_empires_castle_type(db: CardDatabase) -> None:
    castles = db.kingdom_cards["Castles"]
    assert CardType.CASTLE in castles.types
    assert CardType.VICTORY in castles.types
    assert castles.set == CardSet.EMPIRES
    assert castles.purpose == CardPurpose.KINGDOM_PILE


def test_empires_gathering_type(db: CardDatabase) -> None:
    farmers_market = db.kingdom_cards["Farmers' Market"]
    assert CardType.GATHERING in farmers_market.types
    assert CardType.ACTION in farmers_market.types
    wild_hunt = db.kingdom_cards["Wild Hunt"]
    assert CardType.GATHERING in wild_hunt.types
    temple = db.kingdom_cards["Temple"]
    assert CardType.GATHERING in temple.types


def test_empires_split_pile_kingdom_pile(db: CardDatabase) -> None:
    catapult_rocks = db.kingdom_cards["Catapult/Rocks"]
    assert catapult_rocks.purpose == CardPurpose.KINGDOM_PILE
    assert catapult_rocks.set == CardSet.EMPIRES
    assert CardType.ACTION in catapult_rocks.types
    assert CardType.ATTACK in catapult_rocks.types


def test_empires_mixed_pile_cards(db: CardDatabase) -> None:
    empires_mixed = {
        c.name for c in db.mixed_pile_cards.values() if c.set == CardSet.EMPIRES
    }
    assert empires_mixed == {
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
    }


def test_empires_landmark_in_landscape(db: CardDatabase) -> None:
    arena = db.landscape_cards["Arena"]
    assert CardType.LANDMARK in arena.types
    assert arena.purpose == CardPurpose.LANDSCAPE
    assert arena.set == CardSet.EMPIRES


def test_empires_event_in_landscape(db: CardDatabase) -> None:
    donate = db.landscape_cards["Donate"]
    assert CardType.EVENT in donate.types
    assert donate.cost.debt == 8
    assert donate.set == CardSet.EMPIRES


def test_empires_command_type(db: CardDatabase) -> None:
    overlord = db.kingdom_cards["Overlord"]
    assert CardType.COMMAND in overlord.types
    assert overlord.cost.debt == 8


def test_get_renaissance_cards_by_set(db: CardDatabase) -> None:
    cards = db.get_cards_by_set_edition(
        CardSet.RENAISSANCE, CardSetEdition.FIRST_EDITION
    )
    assert len(cards) == 25


def test_renaissance_card_fields_parsed_correctly(db: CardDatabase) -> None:
    old_witch = db.kingdom_cards["Old Witch"]
    assert old_witch.cost.coins == 5
    assert old_witch.types == (CardType.ACTION, CardType.ATTACK)
    assert old_witch.set == CardSet.RENAISSANCE


def test_renaissance_treasure_kingdom_card(db: CardDatabase) -> None:
    ducat = db.kingdom_cards["Ducat"]
    assert CardType.TREASURE in ducat.types
    assert ducat.cost.coins == 2
    assert ducat.set == CardSet.RENAISSANCE


def test_renaissance_duration_kingdom_card(db: CardDatabase) -> None:
    cargo_ship = db.kingdom_cards["Cargo Ship"]
    assert CardType.DURATION in cargo_ship.types
    assert cargo_ship.cost.coins == 3
    assert cargo_ship.set == CardSet.RENAISSANCE


def test_renaissance_command_treasure(db: CardDatabase) -> None:
    scepter = db.kingdom_cards["Scepter"]
    assert CardType.COMMAND in scepter.types
    assert CardType.TREASURE in scepter.types
    assert scepter.cost.coins == 5


def test_renaissance_reaction_kingdom_card(db: CardDatabase) -> None:
    patron = db.kingdom_cards["Patron"]
    assert CardType.REACTION in patron.types
    assert CardType.ACTION in patron.types
    assert patron.cost.coins == 4
    assert patron.set == CardSet.RENAISSANCE


def test_renaissance_project_in_landscape(db: CardDatabase) -> None:
    academy = db.landscape_cards["Academy"]
    assert CardType.PROJECT in academy.types
    assert academy.purpose == CardPurpose.LANDSCAPE
    assert academy.cost.coins == 5
    assert academy.set == CardSet.RENAISSANCE


def test_renaissance_artifact_in_status(db: CardDatabase) -> None:
    flag = db.status_cards["Flag"]
    assert CardType.ARTIFACT in flag.types
    assert flag.purpose == CardPurpose.STATUS
    assert flag.set == CardSet.RENAISSANCE


def test_renaissance_artifacts_in_status_cards(db: CardDatabase) -> None:
    artifact_names = {
        c.name for c in db.status_cards.values() if c.set == CardSet.RENAISSANCE
    }
    assert artifact_names == {"Flag", "Horn", "Key", "Lantern", "Treasure Chest"}


def test_get_menagerie_cards_by_set(db: CardDatabase) -> None:
    cards = db.get_cards_by_set_edition(CardSet.MENAGERIE, CardSetEdition.FIRST_EDITION)
    assert len(cards) == 30


def test_menagerie_card_fields_parsed_correctly(db: CardDatabase) -> None:
    barge = db.kingdom_cards["Barge"]
    assert barge.cost.coins == 5
    assert barge.types == (CardType.ACTION, CardType.DURATION)
    assert barge.set == CardSet.MENAGERIE


def test_menagerie_treasure_kingdom_card(db: CardDatabase) -> None:
    stockpile = db.kingdom_cards["Stockpile"]
    assert CardType.TREASURE in stockpile.types
    assert stockpile.cost.coins == 3
    assert stockpile.set == CardSet.MENAGERIE
    assert stockpile.purpose == CardPurpose.KINGDOM_PILE
    assert stockpile.quantity == 10


def test_menagerie_supplies_treasure_kingdom_card(db: CardDatabase) -> None:
    supplies = db.kingdom_cards["Supplies"]
    assert CardType.TREASURE in supplies.types
    assert supplies.cost.coins == 2
    assert supplies.set == CardSet.MENAGERIE


def test_menagerie_variable_cost_fisherman(db: CardDatabase) -> None:
    fisherman = db.kingdom_cards["Fisherman"]
    assert fisherman.cost.coins == 5
    assert fisherman.cost.extra == "*"
    assert fisherman.set == CardSet.MENAGERIE
    assert CardType.ACTION in fisherman.types


def test_menagerie_variable_cost_destrier(db: CardDatabase) -> None:
    destrier = db.kingdom_cards["Destrier"]
    assert destrier.cost.coins == 6
    assert destrier.cost.extra == "*"
    assert destrier.set == CardSet.MENAGERIE


def test_menagerie_variable_cost_wayfarer(db: CardDatabase) -> None:
    wayfarer = db.kingdom_cards["Wayfarer"]
    assert wayfarer.cost.coins == 6
    assert wayfarer.cost.extra == "*"
    assert wayfarer.set == CardSet.MENAGERIE


def test_menagerie_variable_cost_animal_fair(db: CardDatabase) -> None:
    animal_fair = db.kingdom_cards["Animal Fair"]
    assert animal_fair.cost.coins == 7
    assert animal_fair.cost.extra == "*"
    assert animal_fair.set == CardSet.MENAGERIE


def test_menagerie_way_in_landscape(db: CardDatabase) -> None:
    way_of_the_butterfly = db.landscape_cards["Way of the Butterfly"]
    assert CardType.WAY in way_of_the_butterfly.types
    assert way_of_the_butterfly.purpose == CardPurpose.LANDSCAPE
    assert way_of_the_butterfly.set == CardSet.MENAGERIE


def test_menagerie_event_in_landscape(db: CardDatabase) -> None:
    ride = db.landscape_cards["Ride"]
    assert CardType.EVENT in ride.types
    assert ride.purpose == CardPurpose.LANDSCAPE
    assert ride.cost.coins == 2
    assert ride.set == CardSet.MENAGERIE


def test_menagerie_horse_in_non_supply(db: CardDatabase) -> None:
    horse = db.non_supply_cards["Horse"]
    assert CardType.ACTION in horse.types
    assert horse.purpose == CardPurpose.NON_SUPPLY
    assert horse.cost.coins == 3
    assert horse.cost.extra == "*"
    assert horse.set == CardSet.MENAGERIE
    assert horse.quantity == 30


def test_menagerie_way_type_count(db: CardDatabase) -> None:
    menagerie_ways = [
        c
        for c in db.landscape_cards.values()
        if c.set == CardSet.MENAGERIE and CardType.WAY in c.types
    ]
    assert len(menagerie_ways) == 20
    way_names = {c.name for c in menagerie_ways}
    assert way_names == {
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


def test_menagerie_event_count(db: CardDatabase) -> None:
    menagerie_events = [
        c
        for c in db.landscape_cards.values()
        if c.set == CardSet.MENAGERIE and CardType.EVENT in c.types
    ]
    assert len(menagerie_events) == 20
    event_names = {c.name for c in menagerie_events}
    assert event_names == {
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


def test_menagerie_attack_reaction_multi_type(db: CardDatabase) -> None:
    black_cat = db.kingdom_cards["Black Cat"]
    assert black_cat.types == (CardType.ACTION, CardType.ATTACK, CardType.REACTION)
    assert black_cat.cost.coins == 2
    assert black_cat.set == CardSet.MENAGERIE


def test_menagerie_duration_reaction_type(db: CardDatabase) -> None:
    village_green = db.kingdom_cards["Village Green"]
    assert CardType.DURATION in village_green.types
    assert CardType.REACTION in village_green.types
    assert CardType.ACTION in village_green.types
    assert village_green.cost.coins == 4
    assert village_green.set == CardSet.MENAGERIE


def test_menagerie_duration_attack_type(db: CardDatabase) -> None:
    gatekeeper = db.kingdom_cards["Gatekeeper"]
    assert CardType.DURATION in gatekeeper.types
    assert CardType.ATTACK in gatekeeper.types
    assert CardType.ACTION in gatekeeper.types
    assert gatekeeper.cost.coins == 5
    assert gatekeeper.set == CardSet.MENAGERIE


def test_menagerie_reaction_kingdom_cards(db: CardDatabase) -> None:
    menagerie_reactions = {
        c.name
        for c in db.kingdom_cards.values()
        if c.set == CardSet.MENAGERIE and CardType.REACTION in c.types
    }
    assert menagerie_reactions == {
        "Black Cat",
        "Falconer",
        "Sheepdog",
        "Sleigh",
        "Village Green",
    }


def test_menagerie_all_kingdom_card_names(db: CardDatabase) -> None:
    menagerie_kingdom_names = {
        c.name for c in db.kingdom_cards.values() if c.set == CardSet.MENAGERIE
    }
    assert menagerie_kingdom_names == {
        "Animal Fair",
        "Barge",
        "Black Cat",
        "Bounty Hunter",
        "Camel Train",
        "Cardinal",
        "Cavalry",
        "Coven",
        "Destrier",
        "Displace",
        "Falconer",
        "Fisherman",
        "Gatekeeper",
        "Goatherd",
        "Groom",
        "Hostelry",
        "Hunting Lodge",
        "Kiln",
        "Livery",
        "Mastermind",
        "Paddock",
        "Sanctuary",
        "Scrap",
        "Sheepdog",
        "Sleigh",
        "Snowy Village",
        "Stockpile",
        "Supplies",
        "Village Green",
        "Wayfarer",
    }


def test_menagerie_zero_cost_events(db: CardDatabase) -> None:
    delay = db.landscape_cards["Delay"]
    assert delay.cost.coins == 0
    assert delay.cost.potion is False
    assert delay.cost.debt == 0
    assert delay.set == CardSet.MENAGERIE

    desperation = db.landscape_cards["Desperation"]
    assert desperation.cost.coins == 0
    assert desperation.set == CardSet.MENAGERIE


def test_menagerie_high_cost_events(db: CardDatabase) -> None:
    alliance = db.landscape_cards["Alliance"]
    assert alliance.cost.coins == 10
    assert alliance.set == CardSet.MENAGERIE

    populate = db.landscape_cards["Populate"]
    assert populate.cost.coins == 10
    assert populate.set == CardSet.MENAGERIE

    enclave = db.landscape_cards["Enclave"]
    assert enclave.cost.coins == 8
    assert enclave.set == CardSet.MENAGERIE


def test_menagerie_way_zero_cost(db: CardDatabase) -> None:
    # All Ways have no cost (empty cost object)
    for way in db.landscape_cards.values():
        if way.set == CardSet.MENAGERIE and CardType.WAY in way.types:
            assert way.cost.coins == 0
            assert way.cost.potion is False
            assert way.cost.debt == 0


def test_get_allies_cards_by_set(db: CardDatabase) -> None:
    cards = db.get_cards_by_set_edition(CardSet.ALLIES, CardSetEdition.FIRST_EDITION)
    assert len(cards) == 31


def test_allies_card_fields_parsed_correctly(db: CardDatabase) -> None:
    barbarian = db.kingdom_cards["Barbarian"]
    assert barbarian.cost.coins == 5
    assert barbarian.types == (CardType.ACTION, CardType.ATTACK)
    assert barbarian.set == CardSet.ALLIES


def test_allies_liaison_type(db: CardDatabase) -> None:
    sycophant = db.kingdom_cards["Sycophant"]
    assert CardType.LIAISON in sycophant.types
    assert CardType.ACTION in sycophant.types
    assert sycophant.cost.coins == 2
    assert sycophant.set == CardSet.ALLIES


def test_allies_ally_in_landscape(db: CardDatabase) -> None:
    architects_guild = db.landscape_cards["Architects' Guild"]
    assert CardType.ALLY in architects_guild.types
    assert architects_guild.purpose == CardPurpose.LANDSCAPE
    assert architects_guild.set == CardSet.ALLIES


def test_allies_mixed_pile_markers(db: CardDatabase) -> None:
    allies_pile_markers = {
        c.name
        for c in db.kingdom_cards.values()
        if c.set == CardSet.ALLIES and c.quantity == 0
    }
    assert allies_pile_markers == {
        "Augurs",
        "Clashes",
        "Forts",
        "Odysseys",
        "Townsfolk",
        "Wizards",
    }


def test_allies_mixed_pile_cards(db: CardDatabase) -> None:
    allies_mixed = {
        c.name for c in db.mixed_pile_cards.values() if c.set == CardSet.ALLIES
    }
    assert allies_mixed == {
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
    }


def test_allies_duration_kingdom_cards(db: CardDatabase) -> None:
    allies_durations = {
        c.name
        for c in db.get_cards_by_type(CardType.DURATION)
        if c.set == CardSet.ALLIES
    }
    assert allies_durations == {"Contract", "Highwayman", "Importer", "Royal Galley"}


def test_allies_treasure_kingdom_cards(db: CardDatabase) -> None:
    bauble = db.kingdom_cards["Bauble"]
    assert CardType.TREASURE in bauble.types
    assert CardType.LIAISON in bauble.types
    assert bauble.cost.coins == 2
    assert bauble.set == CardSet.ALLIES


def test_allies_landscape_allies_count(db: CardDatabase) -> None:
    ally_landscapes = [
        c for c in db.landscape_cards.values() if c.set == CardSet.ALLIES
    ]
    assert len(ally_landscapes) == 23


def test_get_plunder_cards_by_set(db: CardDatabase) -> None:
    cards = db.get_cards_by_set_edition(CardSet.PLUNDER, CardSetEdition.FIRST_EDITION)
    assert len(cards) == 40


def test_plunder_card_fields_parsed_correctly(db: CardDatabase) -> None:
    cutthroat = db.kingdom_cards["Cutthroat"]
    assert cutthroat.cost.coins == 5
    assert cutthroat.types == (CardType.ACTION, CardType.DURATION, CardType.ATTACK)
    assert cutthroat.set == CardSet.PLUNDER


def test_plunder_treasure_duration_kingdom_card(db: CardDatabase) -> None:
    abundance = db.kingdom_cards["Abundance"]
    assert CardType.TREASURE in abundance.types
    assert CardType.DURATION in abundance.types
    assert abundance.cost.coins == 4
    assert abundance.set == CardSet.PLUNDER


def test_plunder_command_type(db: CardDatabase) -> None:
    flagship = db.kingdom_cards["Flagship"]
    assert CardType.COMMAND in flagship.types
    assert CardType.DURATION in flagship.types
    assert flagship.cost.coins == 4
    assert flagship.set == CardSet.PLUNDER


def test_plunder_loot_cards_in_mixed_pile(db: CardDatabase) -> None:
    loot_cards = [c for c in db.mixed_pile_cards.values() if CardType.LOOT in c.types]
    assert len(loot_cards) == 15
    loot_names = {c.name for c in loot_cards}
    assert loot_names == {
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


def test_plunder_loot_meta_pile_in_non_supply(db: CardDatabase) -> None:
    loot = db.non_supply_cards["Loot"]
    assert CardType.LOOT in loot.types
    assert loot.purpose == CardPurpose.NON_SUPPLY
    assert loot.set == CardSet.PLUNDER


def test_plunder_loot_card_fields_parsed_correctly(db: CardDatabase) -> None:
    doubloons = db.mixed_pile_cards["Doubloons"]
    assert CardType.LOOT in doubloons.types
    assert CardType.TREASURE in doubloons.types
    assert doubloons.cost.coins == 7
    assert doubloons.cost.extra == "*"
    assert doubloons.purpose == CardPurpose.MIXED_PILE_CARD
    assert doubloons.set == CardSet.PLUNDER


def test_plunder_trait_in_landscape(db: CardDatabase) -> None:
    cheap = db.landscape_cards["Cheap"]
    assert CardType.TRAIT in cheap.types
    assert cheap.purpose == CardPurpose.LANDSCAPE
    assert cheap.set == CardSet.PLUNDER


def test_plunder_event_in_landscape(db: CardDatabase) -> None:
    looting = db.landscape_cards["Looting"]
    assert CardType.EVENT in looting.types
    assert looting.purpose == CardPurpose.LANDSCAPE
    assert looting.cost.coins == 6
    assert looting.set == CardSet.PLUNDER


def test_plunder_trait_count(db: CardDatabase) -> None:
    plunder_traits = [
        c
        for c in db.landscape_cards.values()
        if c.set == CardSet.PLUNDER and CardType.TRAIT in c.types
    ]
    assert len(plunder_traits) == 15


def test_plunder_event_count(db: CardDatabase) -> None:
    plunder_events = [
        c
        for c in db.landscape_cards.values()
        if c.set == CardSet.PLUNDER and CardType.EVENT in c.types
    ]
    assert len(plunder_events) == 15


def test_plunder_loot_mixed_pile_cost_extra(db: CardDatabase) -> None:
    # All individual Loot cards have cost 7* (coins=7, extra='*')
    for card in db.mixed_pile_cards.values():
        if CardType.LOOT in card.types:
            assert card.cost.coins == 7
            assert card.cost.extra == "*"
            assert card.set == CardSet.PLUNDER


def test_plunder_loot_reaction_card(db: CardDatabase) -> None:
    # Shield is a Loot Reaction that protects against Attacks.
    shield = db.mixed_pile_cards["Shield"]
    assert CardType.LOOT in shield.types
    assert CardType.TREASURE in shield.types
    assert CardType.REACTION in shield.types
    assert shield.set == CardSet.PLUNDER


def test_plunder_loot_action_treasure_card(db: CardDatabase) -> None:
    # Spell Scroll is both an Action and a Treasure Loot.
    spell_scroll = db.mixed_pile_cards["Spell Scroll"]
    assert CardType.LOOT in spell_scroll.types
    assert CardType.ACTION in spell_scroll.types
    assert CardType.TREASURE in spell_scroll.types
    assert spell_scroll.set == CardSet.PLUNDER


def test_get_rising_sun_cards_by_set(db: CardDatabase) -> None:
    cards = db.get_cards_by_set_edition(
        CardSet.RISING_SUN, CardSetEdition.FIRST_EDITION
    )
    assert len(cards) == 25


def test_rising_sun_card_fields_parsed_correctly(db: CardDatabase) -> None:
    ninja = db.kingdom_cards["Ninja"]
    assert ninja.cost.coins == 4
    assert ninja.types == (CardType.ACTION, CardType.ATTACK, CardType.SHADOW)
    assert ninja.set == CardSet.RISING_SUN


def test_rising_sun_shadow_type(db: CardDatabase) -> None:
    shadow_cards = [c for c in db.kingdom_cards.values() if CardType.SHADOW in c.types]
    assert len(shadow_cards) == 5
    assert {c.name for c in shadow_cards} == {
        "Alley",
        "Fishmonger",
        "Ninja",
        "Ronin",
        "Tanuki",
    }


def test_rising_sun_omen_type(db: CardDatabase) -> None:
    omen_cards = [c for c in db.kingdom_cards.values() if CardType.OMEN in c.types]
    assert len(omen_cards) == 6
    assert {c.name for c in omen_cards} == {
        "Kitsune",
        "Mountain Shrine",
        "Poet",
        "River Shrine",
        "Rustic Village",
        "Tea House",
    }


def test_rising_sun_prophecy_in_landscape(db: CardDatabase) -> None:
    rising_sun_prophecies = [
        c
        for c in db.landscape_cards.values()
        if c.set == CardSet.RISING_SUN and CardType.PROPHECY in c.types
    ]
    assert len(rising_sun_prophecies) == 15


def test_rising_sun_event_in_landscape(db: CardDatabase) -> None:
    rising_sun_events = [
        c
        for c in db.landscape_cards.values()
        if c.set == CardSet.RISING_SUN and CardType.EVENT in c.types
    ]
    assert len(rising_sun_events) == 10


def test_rising_sun_debt_cost_kingdom_card(db: CardDatabase) -> None:
    artist = db.kingdom_cards["Artist"]
    assert artist.cost.debt == 8
    assert artist.cost.coins == 0
    assert artist.has_debt_cost is True
    assert artist.set == CardSet.RISING_SUN


def test_rising_sun_debt_cost_event(db: CardDatabase) -> None:
    continue_ = db.landscape_cards["Continue"]
    assert continue_.cost.debt == 8
    assert continue_.set == CardSet.RISING_SUN


def test_rising_sun_duration_kingdom_cards(db: CardDatabase) -> None:
    rising_sun_durations = [
        c
        for c in db.kingdom_cards.values()
        if c.set == CardSet.RISING_SUN and CardType.DURATION in c.types
    ]
    assert len(rising_sun_durations) == 2
    assert {c.name for c in rising_sun_durations} == {"Riverboat", "Samurai"}


def test_rising_sun_command_type(db: CardDatabase) -> None:
    daimyo = db.kingdom_cards["Daimyo"]
    assert CardType.COMMAND in daimyo.types
    assert daimyo.cost.debt == 6
    assert daimyo.set == CardSet.RISING_SUN


def test_rising_sun_treasure_kingdom_card(db: CardDatabase) -> None:
    rice = db.kingdom_cards["Rice"]
    assert CardType.TREASURE in rice.types
    assert rice.cost.coins == 7
    assert rice.set == CardSet.RISING_SUN


def test_rising_sun_prophecy_zero_cost(db: CardDatabase) -> None:
    approaching_army = db.landscape_cards["Approaching Army"]
    assert approaching_army.cost.coins == 0
    assert approaching_army.cost.debt == 0
    assert approaching_army.cost.potion is False
    assert approaching_army.set == CardSet.RISING_SUN


def test_rising_sun_shadow_attack_kingdom_card(db: CardDatabase) -> None:
    # Ninja is both a Shadow and an Attack card
    ninja = db.kingdom_cards["Ninja"]
    assert CardType.SHADOW in ninja.types
    assert CardType.ATTACK in ninja.types
    assert CardType.ACTION in ninja.types


def test_rising_sun_omen_attack_kingdom_card(db: CardDatabase) -> None:
    # Kitsune is an Omen and an Attack
    kitsune = db.kingdom_cards["Kitsune"]
    assert CardType.OMEN in kitsune.types
    assert CardType.ATTACK in kitsune.types
    assert kitsune.cost.coins == 5
    assert kitsune.set == CardSet.RISING_SUN


def test_rising_sun_duration_attack_kingdom_card(db: CardDatabase) -> None:
    # Samurai is Duration + Attack
    samurai = db.kingdom_cards["Samurai"]
    assert CardType.DURATION in samurai.types
    assert CardType.ATTACK in samurai.types
    assert samurai.cost.coins == 6
    assert samurai.set == CardSet.RISING_SUN


def test_get_promo_cards_by_set(db: CardDatabase) -> None:
    cards = db.get_cards_by_set_edition(CardSet.PROMO, CardSetEdition.FIRST_EDITION)
    assert len(cards) == 11


def test_promo_kingdom_card_fields_parsed_correctly(db: CardDatabase) -> None:
    black_market = db.kingdom_cards["Black Market"]
    assert black_market.cost.coins == 3
    assert black_market.types == (CardType.ACTION,)
    assert black_market.set == CardSet.PROMO


def test_promo_event_in_landscape(db: CardDatabase) -> None:
    summon = db.landscape_cards["Summon"]
    assert CardType.EVENT in summon.types
    assert summon.purpose == CardPurpose.LANDSCAPE
    assert summon.cost.coins == 5
    assert summon.set == CardSet.PROMO


def test_promo_split_pile_marker(db: CardDatabase) -> None:
    sauna_avanto = db.kingdom_cards["Sauna/Avanto"]
    assert sauna_avanto.purpose == CardPurpose.KINGDOM_PILE
    assert sauna_avanto.set == CardSet.PROMO
    assert sauna_avanto.quantity == 0
    assert CardType.ACTION in sauna_avanto.types


def test_promo_mixed_pile_cards(db: CardDatabase) -> None:
    promo_mixed = {
        c.name for c in db.mixed_pile_cards.values() if c.set == CardSet.PROMO
    }
    assert promo_mixed == {"Avanto", "Sauna"}


def test_promo_mixed_pile_sauna_fields(db: CardDatabase) -> None:
    sauna = db.mixed_pile_cards["Sauna"]
    assert sauna.cost.coins == 4
    assert sauna.types == (CardType.ACTION,)
    assert sauna.purpose == CardPurpose.MIXED_PILE_CARD
    assert sauna.set == CardSet.PROMO


def test_promo_mixed_pile_avanto_fields(db: CardDatabase) -> None:
    avanto = db.mixed_pile_cards["Avanto"]
    assert avanto.cost.coins == 5
    assert avanto.types == (CardType.ACTION,)
    assert avanto.purpose == CardPurpose.MIXED_PILE_CARD
    assert avanto.set == CardSet.PROMO


def test_promo_victory_kingdom_card(db: CardDatabase) -> None:
    marchland = db.kingdom_cards["Marchland"]
    assert CardType.VICTORY in marchland.types
    assert marchland.purpose == CardPurpose.KINGDOM_PILE
    assert marchland.cost.coins == 5
    assert marchland.quantity == 12
    assert marchland.set == CardSet.PROMO


def test_promo_duration_kingdom_cards(db: CardDatabase) -> None:
    promo_durations = {
        c.name
        for c in db.get_cards_by_type(CardType.DURATION)
        if c.set == CardSet.PROMO
    }
    assert promo_durations == {"Captain", "Church", "Prince"}


def test_promo_command_type(db: CardDatabase) -> None:
    captain = db.kingdom_cards["Captain"]
    assert CardType.COMMAND in captain.types
    assert CardType.ACTION in captain.types
    assert CardType.DURATION in captain.types
    assert captain.cost.coins == 6
    assert captain.set == CardSet.PROMO

    prince = db.kingdom_cards["Prince"]
    assert CardType.COMMAND in prince.types
    assert CardType.ACTION in prince.types
    assert CardType.DURATION in prince.types
    assert prince.cost.coins == 8
    assert prince.set == CardSet.PROMO


def test_promo_treasure_kingdom_card(db: CardDatabase) -> None:
    stash = db.kingdom_cards["Stash"]
    assert stash.types == (CardType.TREASURE,)
    assert stash.cost.coins == 5
    assert stash.set == CardSet.PROMO


def test_promo_all_kingdom_card_names(db: CardDatabase) -> None:
    promo_kingdom_names = {
        c.name for c in db.kingdom_cards.values() if c.set == CardSet.PROMO
    }
    assert promo_kingdom_names == {
        "Black Market",
        "Captain",
        "Church",
        "Dismantle",
        "Envoy",
        "Governor",
        "Marchland",
        "Prince",
        "Sauna/Avanto",
        "Stash",
        "Walled Village",
    }
