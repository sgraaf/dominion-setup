# CLI Reference

The `dominion-setup` command-line interface (CLI) provides for setting up a game of Dominion via the command-line. This page lists the `--help` for `dominion-setup`.

<!-- [[[cog
import cog
from click.testing import CliRunner

from dominion_setup.cli import cli

def help_output(args):
    result = CliRunner().invoke(cli, args)
    output = result.output.replace("Usage: cli ", "Usage: dominion-setup ")
    cog.out(f"\nRunning `dominion-setup {' '.join(args)}` or `python -m dominion-setup {' '.join(args)}` shows a list of all of the available options and arguments:\n")
    cog.out(f"\n```sh\n{output}```\n\n")
cog.outl()
]]] -->

<!-- [[[end]]] -->

## dominion-setup

<!-- [[[cog
help_output(["--help"])
]]] -->

Running `dominion-setup --help` or `python -m dominion-setup --help` shows a list of all of the available options and arguments:

```sh
Usage: dominion-setup [OPTIONS] COMMAND [ARGS]...

  Dominion game setup generator.

Options:
  -V, --version  Show the version and exit.
  -h, --help     Show this message and exit.

Commands:
  generate*  Generate a random Dominion game setup.
```

<!-- [[[end]]] -->

## dominion-setup generate

<!-- [[[cog
help_output(["generate", "--help"])
]]] -->

Running `dominion-setup generate --help` or `python -m dominion-setup generate --help` shows a list of all of the available options and arguments:

```sh
Usage: dominion-setup generate [OPTIONS]

  Generate a random Dominion game setup.

Options:
  -h, --help                   Show this message and exit.
```

<!-- [[[end]]] -->
