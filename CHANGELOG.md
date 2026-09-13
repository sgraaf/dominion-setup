# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and this project adheres to [Calendar Versioning](https://calver.org/).

The **first number** of the version is the year.
The **second number** is incremented with each release, starting at 1 for each year.
The **third number** is for emergencies when we need to start branches for older releases.

## [Unreleased](https://github.com/sgraaf/dominion-setup/compare/2026.2.0...HEAD)

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
