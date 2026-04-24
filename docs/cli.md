# CLI Reference

The `dominion-setup` command-line interface (CLI) provides for setting up a game of Dominion via the command-line. This page lists the `--help` for `dominion-setup`.

<!-- [[[cog
import cog
from click.testing import CliRunner

from dominion_setup.cli import cli

def help_output(args):
    result = CliRunner().invoke(cli, args, env={"NO_COLOR": "1"})
    output = result.output.replace("Usage: cli ", "Usage: dominion-setup ")
    # Strip trailing whitespace from Rich output to avoid conflict with trailing-whitespace hook
    output = "\n".join(line.rstrip() for line in output.splitlines())
    cog.out(f"\nRunning `dominion-setup {' '.join(args)}` or `python -m dominion-setup {' '.join(args)}` shows a list of all of the available options and arguments:\n")
    cog.out(f"\n```sh\n$ dominion-setup {' '.join(args)}\n{output}\n```\n\n")
cog.outl()
]]] -->

<!-- [[[end]]] -->

## dominion-setup

<!-- [[[cog
help_output(["--help"])
]]] -->

Running `dominion-setup --help` or `python -m dominion-setup --help` shows a list of all of the available options and arguments:

```sh
$ dominion-setup --help

 Usage: dominion-setup [OPTIONS] COMMAND [ARGS]...

 Dominion game setup generator.

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --version  -V  Show the version and exit.                                    │
│ --help     -h  Show this message and exit.                                   │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Commands ───────────────────────────────────────────────────────────────────╮
│ generate       Generate a random Dominion game setup.                        │
│ list-cards     List available kingdom cards with optional filters.           │
│ list-sets      List available sets and their kingdom card counts.            │
╰──────────────────────────────────────────────────────────────────────────────╯
```

<!-- [[[end]]] -->

## dominion-setup generate

<!-- [[[cog
help_output(["generate", "--help"])
]]] -->

Running `dominion-setup generate --help` or `python -m dominion-setup generate --help` shows a list of all of the available options and arguments:

```sh
$ dominion-setup generate --help

 Usage: dominion-setup generate [OPTIONS]

 Generate a random Dominion game setup.

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --set                    -s  [base_1e|base_2e|intri  Set(s) to include       │
│                              gue_1e|intrigue_2e|sea  (repeatable). [default: │
│                              side_1e|seaside_2e|alc  base_2e]                │
│                              hemy|prosperity_1e|pro                          │
│                              sperity_2e|cornucopia_                          │
│                              guilds_1e|cornucopia_g                          │
│                              uilds_2e|hinterlands_1                          │
│                              e|hinterlands_2e|dark_                          │
│                              ages|adventures|empire                          │
│                              s|nocturne|renaissance                          │
│                              |menagerie|allies|plun                          │
│                              der|rising_sun|promo]                           │
│ --sort                       [name|cost|set]         Sort order for kingdom  │
│                                                      cards. [default: cost]  │
│ --colony/--no-colony                                 Force Platinum/Colony   │
│                                                      on or off.              │
│ --shelters/--no-shelter                              Force Shelters on or    │
│ s                                                    off.                    │
│ --max-landscapes             INTEGER RANGE [x>=0]    Maximum number of       │
│                                                      landscapes to include.  │
│                                                      [default: 2]            │
│ --help                   -h                          Show this message and   │
│                                                      exit.                   │
╰──────────────────────────────────────────────────────────────────────────────╯
```

<!-- [[[end]]] -->

## dominion-setup list-cards

<!-- [[[cog
help_output(["list-cards", "--help"])
]]] -->

Running `dominion-setup list-cards --help` or `python -m dominion-setup list-cards --help` shows a list of all of the available options and arguments:

```sh
$ dominion-setup list-cards --help

 Usage: dominion-setup list-cards [OPTIONS]

 List available kingdom cards with optional filters.

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --set   -s  [base_1e|base_2e|intrigue_1e|i  Filter by set (repeatable).      │
│             ntrigue_2e|seaside_1e|seaside_                                   │
│             2e|alchemy|prosperity_1e|prosp                                   │
│             erity_2e|cornucopia_guilds_1e|                                   │
│             cornucopia_guilds_2e|hinterlan                                   │
│             ds_1e|hinterlands_2e|dark_ages                                   │
│             |adventures|empires|nocturne|r                                   │
│             enaissance|menagerie|allies|pl                                   │
│             under|rising_sun|promo]                                          │
│ --type  -t  [action|attack|curse|reaction|  Filter by card type (repeatable; │
│             treasure|victory|duration|priz  all must match).                 │
│             e|reward|command|knight|looter                                   │
│             |ruins|shelter|event|reserve|t                                   │
│             raveller|castle|gathering|land                                   │
│             mark|boon|doom|fate|heirloom|h                                   │
│             ex|night|spirit|state|zombie|a                                   │
│             rtifact|project|way|ally|augur                                   │
│             |clash|fort|liaison|odyssey|to                                   │
│             wnsfolk|wizard|loot|trait|omen                                   │
│             |prophecy|shadow]                                                │
│ --cost      INTEGER                         Filter by exact coin cost.       │
│ --sort      [name|cost|set]                 Sort order for kingdom cards.    │
│                                             [default: cost]                  │
│ --help  -h                                  Show this message and exit.      │
╰──────────────────────────────────────────────────────────────────────────────╯
```

<!-- [[[end]]] -->

## dominion-setup list-sets

<!-- [[[cog
help_output(["list-sets", "--help"])
]]] -->

Running `dominion-setup list-sets --help` or `python -m dominion-setup list-sets --help` shows a list of all of the available options and arguments:

```sh
$ dominion-setup list-sets --help

 Usage: dominion-setup list-sets [OPTIONS]

 List available sets and their kingdom card counts.

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --help  -h  Show this message and exit.                                      │
╰──────────────────────────────────────────────────────────────────────────────╯
```

<!-- [[[end]]] -->
