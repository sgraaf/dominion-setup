# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and this project adheres to [Calendar Versioning](https://calver.org/).

The **first number** of the version is the year.
The **second number** is incremented with each release, starting at 1 for each year.
The **third number** is for emergencies when we need to start branches for older releases.

## [Unreleased](https://github.com/sgraaf/dominion-setup/compare/2026.1.0...HEAD)

### Added

- `Card`, `CardCost`, `CardSetEdition`, `CardType` and `Material` are exported from the top-level package.

### Changed

- `load_card_database` accepts any `Traversable` and reads the bundled data without requiring it to be on the file system.
- Releases are only published after linting, type checking and tests pass.

### Fixed

- The Coffers / Villagers mat is now included for cards giving a single Villager (e.g. Academy, Patron, Silk Merchant).

## [2026.1.0](https://github.com/sgraaf/dominion-setup/tree/2026.1.0) - 2026-04-24

- Initial release.
