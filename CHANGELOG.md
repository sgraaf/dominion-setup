# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and this project adheres to [Calendar Versioning](https://calver.org/).

The **first number** of the version is the year.
The **second number** is incremented with each release, starting at 1 for each year.
The **third number** is for emergencies when we need to start branches for older releases.

## [Unreleased](https://github.com/sgraaf/dominion-setup/compare/2026.2.0...HEAD)

### Added

- Support for Python 3.15.
- `KingdomSortOrder.sort_key`, the key that sorts cards in that order.
- `CardCost.to_dict`, the inverse of `CardCost.from_dict`. Like the card data, it leaves out fields with default values.
- Kingdom requirements: `generate_game(requirements=...)` with `KingdomRequirement` (+Action(s), +Card(s), +Buy(s), Attack, Reaction, Trashing), and the matching `--require-actions`, `--require-cards`, `--require-buys`, `--require-attack`, `--require-reaction` and `--require-trashing` flags of `dominion-setup generate`. Each makes sure at least one of the 10 Kingdom cards provides that effect.
- Seeds: `generate_game(rng=...)` takes a `random.Random` to draw with, and `dominion-setup generate --seed` replays a game. `generate` prints the seed of every setup, so a game can be replayed or shared.
- Included and excluded cards: `generate_game(include=..., exclude=...)` and the repeatable `--include CARD` and `--exclude CARD` options of `dominion-setup generate`. Included Kingdom cards and Landscapes (from any set) are always used; excluded ones are never drawn.
- Output formats: `dominion-setup generate --format json` prints the game (and its seed) as JSON, for scripts, bots and front ends; `--format names` prints the Kingdom cards, Landscapes, Ally and Prophecy on one comma-separated line, to paste into a chat or a client like dominion.games.
- Black Market deck: when Black Market is in use, `generate_game` deals out a Black Market deck of different unused Kingdom cards into the new `Game.black_market_deck`, and runs the setup they need (e.g. a Bane for Young Witch, Heirlooms, materials). Its size is set by `generate_game(black_market_size=...)` and `dominion-setup generate --black-market-size` (default 15).

### Changed

- `CardCost.coins` is now `None` (the new default) for a cost without coins, such as Engineer's 4D or a Landmark, which has no cost; before, it was 0. So `CardCost()` no longer equals `CardCost(coins=0)`, and `list-cards --cost 0` no longer lists cards that only cost Potion or Debt. Costs still sort as if a cost without coins were \$0.
- `generate_game` no longer uses or changes the global `random` state, so `random.seed()` no longer reproduces a game. Pass `rng=random.Random(seed)` instead.
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
