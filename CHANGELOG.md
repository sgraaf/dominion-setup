# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and this project adheres to [Calendar Versioning](https://calver.org/).

The **first number** of the version is the year.
The **second number** is incremented with each release, starting at 1 for each year.
The **third number** is for emergencies when we need to start branches for older releases.

## [2026.5.0](https://github.com/sgraaf/dominion-setup/compare/2026.4.0...2026.5.0) - 2026-10-27

This release lets you share a game with others. Every game now comes with a *Board code*: a short line of text, such as `players=4&kingdom=bridge,clerk,…&bane=moat`, that lists its Kingdom cards, Landscapes, extra piles and other choices. The CLI prints the code next to the seed, and `dominion-setup setup CODE` sets up the game of a code or a whole web app link. In the library, the new `Board` holds those choices, `generate_game(board=...)` sets one up, and `read_board_code` reads a code. Cards can now be looked up by their slug or by their old name, so Farm is still found under its old name, Harem. Finally, sorting by cost no longer depends on the order in which cards were drawn.

### Added

- Board codes: every game now has a Board code, a line of text that holds the choices it was set up with and the number of players, e.g. `players=4&kingdom=bridge,clerk,…&landscapes=baths,way-of-the-mouse&bane=moat&way-of-the-mouse=village&colony=on`. It is the query string of a web app link, and `dominion-setup setup` sets the game up again from it. The CLI prints it with every game, next to the seed, on a single line (even if that is wider than the terminal) so that it copies whole. With `--format names`, it goes to stderr, like the seed. `Game.code` returns it, and `Game.to_dict` (and so `--format json`) includes it as `code`.
- `dominion-setup setup CODE` sets up the game of a Board code, or of a whole web app link. What the code leaves out is drawn from the `--set` and `--promo` cards, except Colony and Shelters, which are off unless the code turns them on. `--exclude` keeps cards from being drawn, but doesn't take the code's own cards out of the game. `--players` overrides the code's number of players, and `--sort`, `--swap` and `--format` work as for `generate`. `setup` prints no seed: the code it prints sets the game up again, swaps included. It reads the same config file as `generate`, and ignores the keys of options that only `generate` has (e.g. `require-buys`). The code's number of players takes precedence over the config file's. A CODE with nothing to set up (e.g. a card name, or only unknown keys) is an error.
- `Board` (exported from `dominion_setup`) holds the choices that make up a game: the 10 Kingdom cards (without the extra piles), the Landscapes, the extra piles (Bane, Ferryman, …), the pile of each Trait, the Obelisk pile, the Ally, the Prophecy, the Druid Boons, the Black Market deck, and whether Colony and Shelters are used. The rest of the setup follows from these. Every generated `Game` has its `board`.
- `generate_game(board=...)` sets up the game of a Board. Its Kingdom cards and Landscapes are always used, like `include`d cards, even past `max_landscapes` and even if they are `exclude`d, as `exclude` only keeps cards from being drawn. If it has fewer than 10 Kingdom cards, the rest are drawn. Its other choices are used where they apply (e.g. the Bane if Young Witch is in use), and those it leaves out are drawn. A given Black Market deck is used as it is, whatever `black_market_size`, and a given Colony and Shelters override `use_colony` and `use_shelters`. A complete Board (e.g. `game.board`) gives the same game for any seed, and `swaps` swap cards of the Board. A Board that can't be set up raises `SetupGenerationError`: one with more than 10 Kingdom cards, the same card twice (e.g. a Black Market card that is also in the Kingdom), a card in the wrong place (e.g. a Landscape among the Kingdom cards), an extra pile that isn't eligible (e.g. a Bane that doesn't cost \$2 or \$3), a Trait on a pile that isn't an Action or Treasure, two Traits on one pile, an Obelisk pile that isn't an Action, or a number of Druid Boons other than 3.
- `Board.to_code(players=...)` writes a Board, and the number of players if given, as a Board code. Cards are written as slugs (the new `Card.slug`, e.g. `devils-workshop` for Devil's Workshop), the keys in a fixed order and the lists sorted, so each Board has one code. `read_board_code(db, code)` (exported from `dominion_setup`) reads a code, or a whole link, back into a Board and the number of players. It takes cards as slugs, as names in any case, or by their old names, ignores unknown keys, and turns Colony and Shelters off unless the code turns them on. It raises `SetupGenerationError` for an unknown card or a value it can't read (e.g. `players=many`).
- `CardDatabase.find_card(name)` finds a card by its name in any case, its slug, or an old name, and returns `None` if there is none. Renamed cards keep their old names in the new `Card.old_names` (`"old_names"` in the card data), so that codes and links still find a card after it is renamed.

### Changed

- The `--include`, `--exclude`, `--promo` and `--swap` options (and their keys in the config file) now find cards as `CardDatabase.find_card` does: by name in any case, by slug, or by old name. For example, `--exclude "devil's workshop"` and `--exclude devils-workshop` both exclude Devil's Workshop.
- Harem is now called Farm, as in newer printings. "Harem" still finds it (e.g. `--exclude Harem`, or `kingdom=harem` in a Board code). As the randomizer deck is sorted by name before it is shuffled, a seed may deal a different game than in 2026.4.0 when Farm can be drawn.

### Fixed

- Sorting by cost (and by set) now orders cards whose costs sort the same, such as \$0 and no cost, by name. A \$0 Event (e.g. Alms) and a Landscape without a cost (e.g. Obelisk) used to stay in the order in which they were drawn.

## [2026.4.0](https://github.com/sgraaf/dominion-setup/compare/2026.3.0...2026.4.0) - 2026-10-18

This release lets you swap out cards you don't like: `--swap CARD` (or `--swap CARD=REPLACEMENT`) replaces a Kingdom card, extra pile or Landscape and keeps the rest of the game the same. It also makes the library easier to build front ends on. Each card in the JSON output now says what it's for (e.g. Kingdom Pile or Landscape), setup instructions keep their label and text apart, and `generate_game` takes a list of Promos, like `--promo`. Helpers such as `is_selectable` and `SET_EDITION_CHOICES` are now exported from `dominion_setup`.

### Added

- Swaps: `generate_game(swaps=...)` takes `(card, replacement)` pairs, and the repeatable `--swap CARD[=REPLACEMENT]` option swaps a Kingdom card, extra pile (e.g. the Bane) or Landscape of the game for a random card, or for the replacement. Everything that doesn't depend on the swapped card stays the same: the rest of the Kingdom and the Landscapes, the extra piles, the Black Market deck, the Prophecy, the Ally, the Druid Boons, the Traits, the Obelisk pile, Colony and Shelters. A game with swaps is replayed by its seed and swaps, e.g. `--seed 42 --swap Smithy --swap Moat=Village`.
- Each card in `Pile.to_dict` and `Game.to_dict` (and so in `--format json`) now includes its `purpose` (e.g. "Kingdom Pile" or "Landscape"), so front ends can tell Landscapes from Kingdom cards without keeping their own list of Landscape types.
- `generate_game(promos=...)`, which draws from the given Promos only, like `--promo CARD`. It also works with every set (`sets_editions=None`), and raises `SetupGenerationError` for a name that isn't a Promo card.
- `is_selectable(card)`, which returns whether a card can be drawn, included or excluded: a Kingdom card, or an Event, Landmark, Project, Way or Trait. It used to be private, as `generator._is_selectable`.
- `is_selectable`, `SetupInstruction`, `SET_EDITION_CHOICES` (the `--set` choices, e.g. "base_2e" or "nocturne", and the set and edition each one selects) and `CARD_SETS_WITH_SECOND_EDITIONS` are now exported from `dominion_setup`.

### Changed

- `Game.setup_instructions` is now a list of `SetupInstruction`s, which keep the label (the card, or "Starting decks") and the text apart, so front ends don't have to split the string. `str()` of one gives the old string, e.g. "Arena: Put 6 VP here per player." In `Game.to_dict` (and so in `--format json`), `setup` is now a list of `{"label": …, "text": …}` objects instead of strings.
- `SET_EDITION_CHOICES` moved from `dominion_setup.cli` to `dominion_setup.models`.

## [2026.3.0](https://github.com/sgraaf/dominion-setup/compare/2026.2.0...2026.3.0) - 2026-10-17

This release gives you more control over your Kingdom. You can now require certain effects (such as +Buy, Trashing or an Attack), force cards in or ban them with `--include` and `--exclude`, and draw only from the Promos you own. A config file can store your collection, bans and default requirements. Every setup now comes with a seed you can use to replay or share it, and `--format json` and `--format names` make the output easy to use in scripts, bots and chats. Setups are also more complete: give a player count and you get the size of each pile, Black Market comes with its own deck, and Shelters and Heirlooms come with a clear list of each player's starting cards.

### Added

- Kingdom requirements: `generate_game(requirements=...)` takes `KingdomRequirement`s (+Action(s), +Card(s), +Buy(s), Attack, Reaction, Trashing), each making sure at least one of the 10 Kingdom cards provides that effect. In the CLI: `--require-actions`, `--require-cards`, `--require-buys`, `--require-attack`, `--require-reaction` and `--require-trashing`.
- Included and excluded cards: `generate_game(include=..., exclude=...)` and the repeatable `--include CARD` and `--exclude CARD` options. Included Kingdom cards and Landscapes (from any set) are always used; excluded ones are never drawn.
- Promo cards: the repeatable `--promo CARD` option draws from the given Promos only (as Promos are bought one by one), while `--set promo` still draws from all of them.
- Seeds: `generate_game(rng=...)` takes a `random.Random` to draw with. `dominion-setup generate` prints the seed of every setup, and `--seed` replays it.
- Output formats: `--format json` prints the game (and its seed) as JSON, for scripts, bots and front ends; `--format names` prints the Kingdom cards, Landscapes, Ally and Prophecy on one comma-separated line, to paste into a chat or a client like dominion.games.
- Pile sizes: `generate_game(players=...)` and `--players` (2 to 6) work out how many cards go in each pile, into the new `Game.players` and `Pile.size` (`None` without a player count). The CLI prints them in a Size column, and `--format json` as `players` and each pile's `size`. Landmarks that start with VP per player (Arena, Basilica, …) give the total in their setup instructions, e.g. "Put 24 VP here (6 VP per player)."
- Black Market deck: when Black Market is in use, a deck of unused Kingdom cards is dealt into the new `Game.black_market_deck`, along with the setup those cards need (e.g. a Bane for Young Witch, Heirlooms, materials). Its size is set by `generate_game(black_market_size=...)` and `--black-market-size` (default 15).
- Starting decks: when Shelters or Heirlooms are in use, a "Starting decks: …" setup instruction lists each player's starting cards, e.g. "Each player starts with 6 Coppers, Pouch, Hovel, Necropolis, Overgrown Estate."
- Config file: `dominion-setup generate` reads its option defaults from `~/.config/dominion-setup/config.toml` (or `$XDG_CONFIG_HOME/dominion-setup/config.toml`), or from `--config-file FILE`, keyed by their long names (e.g. `set`, `exclude`, `require-buys`). Use it to store your collection, bans and default requirements.
- `Game.to_dict` and `Pile.to_dict`, which return the JSON that `--format json` prints (without the seed), for front ends that use the library directly. Each card in it also includes its `image` (the wiki's file name) and `instructions`.
- `CardCost.to_dict`, the inverse of `CardCost.from_dict`. Like the card data, it leaves out fields with default values.
- `KingdomSortOrder.sort_key`, the key that sorts cards in that order.
- Support for Python 3.15.

### Changed

- `generate_game` no longer uses or changes the global `random` state, so `random.seed()` no longer reproduces a game. Pass `rng=random.Random(seed)` instead.
- `CardCost.coins` is now `None` (the new default) for a cost without coins, such as Engineer's 4D, or a Landmark, which has no cost at all; it used to be 0. As a result, `CardCost()` no longer equals `CardCost(coins=0)`, and `list-cards --cost 0` no longer lists cards that only cost Potion or Debt. Costs still sort as if a cost without coins were \$0.
- The "Starting decks: …" setup instruction replaces the "Heirlooms: Each player replaces … starting Coppers with …" instruction and Shelters' own "Shelters: …" instruction.
- `DEFAULT_BASIC_CARD_NAMES` and `SELECTABLE_LANDSCAPE_TYPES` moved from `dominion_setup.models` to `dominion_setup.generator`, alongside the other setup rules.

### Removed

- The `dominion_setup.utils` module. Use `KingdomSortOrder.sort_key` instead of `card_sort_key`; `parse_raw_set_edition` was only used by the CLI.

### Fixed

- Landscapes without a cost (Landmarks, Ways, Traits, Allies, Prophecies) no longer show a cost of \$0.

## [2026.2.0](https://github.com/sgraaf/dominion-setup/compare/2026.1.0...2026.2.0) - 2026-09-13

### Added

- `SetupGenerationError` (a `ValueError` subclass), raised when the selected sets cannot produce a valid setup. The CLI only reports these as usage errors; other errors are no longer disguised as usage errors.
- `Card`, `CardCost`, `CardSetEdition`, `CardType` and `Material` are exported from the top-level package.

### Changed

- For a given `random` seed, `generate_game` now produces the same setup in every process (previously it depended on string hash randomization).
- Cards set aside for Ferryman, Way of the Mouse and Riverboat now trigger all setup (components, Heirlooms, materials, setup instructions), not only name-based setup.
- `load_card_database` accepts any `Traversable` and reads the bundled data without requiring it to be on the file system.
- Releases are only published after linting, type checking and tests pass.

### Fixed

- A Young Witch chosen as an extra pile (by Ferryman or Approaching Army) now gets a Bane pile, and a Ferryman set aside by Riverboat now gets its extra pile.
- The Coffers / Villagers mat is now included for cards giving a single Villager (e.g. Academy, Patron, Silk Merchant).
- Coin tokens are now included for Pirate Ship and Trade Route.

## [2026.1.0](https://github.com/sgraaf/dominion-setup/tree/2026.1.0) - 2026-04-24

- Initial release.
