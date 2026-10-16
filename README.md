<!-- start docs-include-index -->

# dominion-setup

[![PyPI](https://img.shields.io/pypi/v/dominion-setup)](https://img.shields.io/pypi/v/dominion-setup)
[![Supported Python Versions](https://img.shields.io/pypi/pyversions/dominion-setup)](https://pypi.org/project/dominion-setup/)
[![CI](https://github.com/sgraaf/dominion-setup/actions/workflows/ci.yml/badge.svg)](https://github.com/sgraaf/dominion-setup/actions/workflows/ci.yml)
[![Test](https://github.com/sgraaf/dominion-setup/actions/workflows/test.yml/badge.svg)](https://github.com/sgraaf/dominion-setup/actions/workflows/test.yml)
[![Documentation Status](https://readthedocs.org/projects/dominion-setup/badge/?version=latest)](https://dominion-setup.readthedocs.io/latest/?badge=latest)
[![OpenSSF Best Practices](https://www.bestpractices.dev/projects/12639/badge)](https://www.bestpractices.dev/projects/12639)

*dominion-setup* is a Python library and CLI tool to set up a game of Dominion, the classic deck-building game.

<!-- end docs-include-index -->

## Features

- **Complete card database** — ships with JSON data for every Dominion set released to date: Base, Intrigue, Seaside, Alchemy, Prosperity, Cornucopia & Guilds, Hinterlands, Dark Ages, Adventures, Empires, Nocturne, Renaissance, Menagerie, Allies, Plunder, Rising Sun, and Promo cards.
- **Edition-aware** — correctly handles 1st and 2nd edition differences for Base, Intrigue, Seaside, Prosperity, Cornucopia & Guilds, and Hinterlands.
- **Rules-accurate generation** — automatically applies all official setup rules, including:
  - Selecting 10 random Kingdom piles from the chosen set(s).
  - Drawing up to a configurable number of Landscape cards (Events, Landmarks, Projects, Ways, Traits).
  - Adding extra piles required by specific cards (Bane for Young Witch, Ferryman pile, Way of the Mouse pile, Riverboat pile, Approaching Army pile, Traveller chains for Page and Peasant, Prizes for Tournament, Rewards for Joust, Spirit/Zombie/Imp/Ghost piles for Nocturne cards, Artifacts for Flag Bearer / Border Guard / Treasurer / Swashbuckler, Loot, Horse pile, and more).
  - Choosing an Ally when any Liaison card is in the Kingdom.
  - Choosing a Prophecy when any Omen card is in the Kingdom.
  - Dealing a Black Market deck (15 unused Kingdom cards by default) when Black Market is in use, with the setup its cards need.
  - Assigning Traits to random Action/Treasure Kingdom piles.
  - Randomly determining Colony/Platinum and Shelters based on Prosperity/Dark Ages representation, or allowing you to force them on or off.
  - Deriving the correct Potion, Ruins, and Heirloom basic piles.
  - Collecting all required materials (mats, tokens, cubes) and per-card setup instructions.
- **Flexible sorting** — kingdom piles can be sorted by cost, name, or set.
- **Rich terminal output** — the CLI renders colour-coded tables with [Rich](https://github.com/Textualize/rich).
- **Fully typed** — ships with a `py.typed` marker and complete type annotations.

## Design

### Architecture

The package is structured around four modules:

| Module      | Responsibility                                                                           |
| ----------- | ---------------------------------------------------------------------------------------- |
| `models`    | Dataclasses and enums (`Card`, `CardCost`, `CardSet`, `CardDatabase`, `Game`, `Pile`, …) |
| `loader`    | Reads the bundled JSON data files and populates a `CardDatabase`                         |
| `generator` | `generate_game()`, which turns a `CardDatabase` into a `Game`, and all setup rules       |
| `cli`       | Click/Rich-Click command group (`generate`, `list-cards`, `list-sets`)                   |

### Card data

Every card in every set is stored in a small JSON file under `dominion_setup/data/cards/`. Each entry records the card's name, types, purpose (Basic, Kingdom Pile, Landscape, Mixed Pile Card, Non-Supply, Status), cost (coins, Potion, debt), set, supported edition(s), supply quantity, and the full instruction text used to derive materials and setup notes.

```json
{
  "name": "Artisan",
  "types": ["Action"],
  "purpose": "Kingdom Pile",
  "cost": {"coins": 6},
  "set": "Base",
  "editions": [2],
  "quantity": 10,
  "image": "Artisan.jpg",
  "instructions": "Gain a card to your hand costing up to $5.\nPut a card from your hand onto your deck."
}
```

### Generation algorithm

`generate_game()` performs the following steps in order. Each step has its own section in the `generator` module, holding the rules it applies.

1. **Kingdom** — start from the `include`d cards (from any set), shuffle the other Kingdom and Landscape cards of the selected sets and editions (minus the `exclude`d ones), and draw until there are 10 Kingdom piles, keeping up to `max_landscapes` Landscapes in total. If `requirements` are given (e.g. +Buy(s), an Attack, Trashing), the last free Kingdom slots are kept for cards that meet a requirement no drawn card meets yet.
1. **Extra Kingdom piles, Prophecy & Black Market deck** — add the piles required by cards in use (Bane for Young Witch, Ferryman, Way of the Mouse, Riverboat, Approaching Army), a Prophecy if any Omen is in use, and a Black Market deck of up to `black_market_size` unused Kingdom cards if Black Market is in use. Repeat until nothing new is required, as an extra pile or a Black Market card can itself require one.
1. **Cards dealt out for specific cards** — Druid Boons, the Ally for Liaisons, and the Kingdom pile each Trait applies to.
1. **Non-Supply piles** — Prizes, Rewards, Traveller chains, Spirits, Zombies, Artifacts, Loot, Horses, etc.
1. **Basic Supply** — standard basics plus conditional Colony/Platinum, Potion, Ruins, Shelters, and Heirlooms.
1. **Obelisk** — the Action Supply pile Obelisk applies to.
1. **Materials** — scan instruction text and card types to determine which mats and tokens are needed.
1. **Setup instructions** — extract `Setup:` sentences from card instructions and synthesise Heirloom setup text.

Finally, the piles are sorted and returned in a `Game` object.

## Installation

<!-- start docs-include-installation -->

*dominion-setup* is available on [PyPI](https://pypi.org/project/dominion-setup/). Install with [uv](https://docs.astral.sh/uv/) or your package manager of choice:

```shell
uv add dominion-setup
```

You can also install the command-line interface of *dominion-setup* as a tool that is available on the `PATH` (i.e., globally):

```shell
uv tool install dominion-setup
```

<!-- end docs-include-installation -->

## Documentation

Check out the [*dominion-setup* documentation](https://dominion-setup.readthedocs.io/en/stable/) for the [User's Guide](https://dominion-setup.readthedocs.io/en/stable/usage.html), [API Reference](https://dominion-setup.readthedocs.io/en/stable/api.html) and [CLI Reference](https://dominion-setup.readthedocs.io/en/stable/cli.html).

## Usage

<!-- start docs-include-usage -->

### As a Library

#### Quick start — generate a random setup

```python
from dominion_setup import load_card_database, generate_game

# Load the bundled card database (all sets, all editions)
db = load_card_database()

# Generate a random game — by default draws from ALL sets and editions
game = generate_game(db)

# Inspect the result
for pile in game.kingdom_piles:
    marks = f" [{', '.join(str(m) for m in pile.marks)}]" if pile.marks else ""
    print(f"  {pile.card.name} ({pile.card.cost}){marks}")
```

#### Choosing specific sets and editions

```python
from dominion_setup import load_card_database, generate_game
from dominion_setup.models import (
    CardSet,
    CardSetEdition,
    KingdomRequirement,
    KingdomSortOrder,
)

db = load_card_database()

game = generate_game(
    db,
    sets_editions={
        (CardSet.BASE, CardSetEdition.SECOND_EDITION),
        (CardSet.INTRIGUE, CardSetEdition.SECOND_EDITION),
        (CardSet.PROSPERITY, CardSetEdition.SECOND_EDITION),
    },
    sort_order=KingdomSortOrder.NAME,  # sort kingdom by name
    use_colony=True,  # always include Colony/Platinum
    use_shelters=False,  # never use Shelters
    max_landscapes=1,  # at most 1 landscape card
    requirements=[KingdomRequirement.BUYS],  # at least 1 kingdom card with +Buy(s)
    include=["Witch"],  # always use Witch
    exclude=["Chapel"],  # never use Chapel
)
```

#### Exploring the `Game` object

```python
from dominion_setup import load_card_database, generate_game

db = load_card_database()
game = generate_game(db)

# Sets used in this game
print("Sets:", ", ".join(str(s) for s in game.sets_used))

# Kingdom piles (always 10, plus any special extras such as Bane)
for pile in game.kingdom_piles:
    print(
        f"  {pile.card.name:25s} {str(pile.card.cost):>5}  {', '.join(pile.card.types)}"
    )

# Landscape cards (Events, Landmarks, Projects, Ways, Traits)
if game.landscapes:
    print("Landscapes:")
    for card in game.landscapes:
        print(f"  {card.name}")

# Ally (present when any Liaison card is in the Kingdom)
if game.ally:
    print("Ally:", game.ally.name)

# Prophecy (present when any Omen card is in the Kingdom)
if game.prophecy:
    print("Prophecy:", game.prophecy.name)

# Druid Boons (present when Druid is in the Kingdom)
if game.druid_boons:
    print("Druid Boons:", ", ".join(b.name for b in game.druid_boons))

# Non-supply piles (Prizes, Rewards, Traveller chains, Spirits, …)
if game.non_supply_piles:
    print("Non-Supply:")
    for pile in game.non_supply_piles:
        print(f"  {pile.card.name}")

# Black Market deck (present when Black Market is in use)
if game.black_market_deck:
    print("Black Market:", ", ".join(c.name for c in game.black_market_deck))

# Basic supply (Copper, Silver, Gold, Estate, Duchy, Province, Curse,
#               + conditional Colony/Platinum, Potion, Ruins, Shelters, Heirlooms)
for pile in game.basic_piles:
    print(f"  {pile.card.name}")

# Required mats and tokens
if game.materials:
    print("Materials:", ", ".join(str(m) for m in game.materials))

# Per-card setup instructions
for instruction in game.setup_instructions:
    print(f"  • {instruction}")
```

#### Querying the card database

```python
from dominion_setup import load_card_database
from dominion_setup.models import CardSet, CardSetEdition, CardType, CardCost

db = load_card_database()

# All kingdom cards in Nocturne
nocturne_cards = db.get_cards_by_set_edition(
    CardSet.NOCTURNE, CardSetEdition.FIRST_EDITION
)
print(f"Nocturne has {len(nocturne_cards)} kingdom cards")

# All Action–Attack cards
attack_actions = [
    card
    for card in db.kingdom_cards.values()
    if CardType.ACTION in card.types and CardType.ATTACK in card.types
]

# All kingdom cards that cost $5
five_cost = db.get_cards_by_cost(CardCost(coins=5))

# Look up a card by name
village = db.get_card_by_name("Village")
print(village.name, village.cost, village.instructions)
```

______________________________________________________________________

### As a CLI Tool

The `dominion-setup` command groups three sub-commands. Running it with no arguments is equivalent to `dominion-setup generate`.

#### `dominion-setup generate` — generate a random setup

Generate a random game from the Base 2nd edition (the default):

```sh
dominion-setup generate
```

Mix Intrigue 2e and Seaside 2e, sorted by name:

```sh
dominion-setup generate --set intrigue_2e --set seaside_2e --sort name
```

Use all cards from Dark Ages (always include Shelters, never Colony):

```sh
dominion-setup generate --set dark_ages --shelters --no-colony
```

Allow up to three landscape cards, mix Base 2e with Adventures:

```sh
dominion-setup generate --set base_2e --set adventures --max-landscapes 3
```

Require a Kingdom card with +Buy(s) and one that trashes cards:

```sh
dominion-setup generate --set base_2e --set intrigue_2e --require-buys --require-trashing
```

Always use Witch (and the Alms Event), never Chapel:

```sh
dominion-setup generate --set base_2e --include Witch --include Alms --exclude Chapel
```

Print the setup as JSON, or as one line of card names to paste elsewhere:

```sh
dominion-setup generate --format json
dominion-setup generate --format names
```

Force Colony/Platinum on when playing with a Prosperity mix:

```sh
dominion-setup generate --set base_2e --set prosperity_2e --colony
```

#### `dominion-setup list-cards` — browse the card database

List all kingdom cards sorted by cost (default):

```sh
dominion-setup list-cards
```

List only Base 2e cards:

```sh
dominion-setup list-cards --set base_2e
```

List all Attack cards across Base 2e and Intrigue 2e:

```sh
dominion-setup list-cards --set base_2e --set intrigue_2e --type attack
```

List all Action–Duration cards that cost exactly \$4:

```sh
dominion-setup list-cards --type action --type duration --cost 4
```

List all Nocturne Night cards, sorted by name:

```sh
dominion-setup list-cards --set nocturne --type night --sort name
```

#### `dominion-setup list-sets` — list available sets

```sh
dominion-setup list-sets
```

This prints a table of every supported set (and edition, where applicable) together with its kingdom card count:

```
              Sets
 ┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━┓
 ┃ Set                            ┃ Kingdom Cards ┃
 ┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━┩
 │ Base, 1E                       │            26 │
 │ Base, 2E                       │            26 │
 │ Intrigue, 1E                   │            26 │
 │ ...                            │           ... │
 └────────────────────────────────┴───────────────┘
```

<!-- end docs-include-usage -->
