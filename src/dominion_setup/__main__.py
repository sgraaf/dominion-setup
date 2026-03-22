"""dominion-setup as a module entry point.

This allows dominion-setup to be executable from a git checkout or zip archive.
"""

from .cli import cli

if __name__ == "__main__":
    cli()
