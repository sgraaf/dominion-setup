#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["click", "lxml", "playwright", "rich", "rich-click"]
# ///
"""Scrape the Dominion Strategy Wiki card list and generate JSON data files.

Navigates past the anti-bot challenge using a real Chromium browser via
Playwright, extracts the cards table from the "List of cards" page, and writes
per-set JSON files into src/dominion_setup/data/cards/.

Usage:
    uv run bin/scrape_cards_list.py [--headed] [--dry-run]

Requires Playwright's Chromium browser.  On first run, the script installs
it automatically via ``playwright install chromium``.
"""

from __future__ import annotations

import gzip
import html
import json
import re
import subprocess
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path
from typing import Literal, NotRequired, TypedDict
from urllib.parse import urlencode

import rich_click as click
from lxml.html import fromstring
from playwright.sync_api import sync_playwright
from rich.console import Console


class Cost(TypedDict):
    """Card cost, supporting coins, Potion and Debt."""

    coins: NotRequired[int]
    potion: NotRequired[bool]
    debt: NotRequired[int]
    extra: NotRequired[Literal["+", "*"]]


class Card(TypedDict):
    """A single card definition."""

    name: str
    types: list[str]
    purpose: str
    cost: Cost
    set: str
    editions: list[int]
    quantity: int
    image: str
    instructions: str


WIKI_INDEX_URL = "https://wiki.dominionstrategy.com/index.php"
WIKI_PARAMS = {
    "title": "Special:CargoExport",
    "tables": "Components",
    "limit": "max",
    "offset": 0,
    "fields": "_rowID,_pageID,_pageName,_pageTitle,Name,Expansion,Edition,Purpose,Types,Quantity,Cost_Coin,Cost_Potion,Cost_Debt,Cost_Extra,Illustrator,Art,Image,Instructions,Release_Date",
    "format": "json",
    "formatversion": 2,
}
WIKI_JSON_URL = f"{WIKI_INDEX_URL}?{urlencode(WIKI_PARAMS)}"

CARDS_DIR = (
    Path(__file__).resolve().parents[1] / "src" / "dominion_setup" / "data" / "cards"
)

# set name -> output JSON filename (without .json extension)
SET_TO_FILENAME: dict[str, str] = {
    "Base": "base",
    "Intrigue": "intrigue",
    "Seaside": "seaside",
    "Alchemy": "alchemy",
    "Prosperity": "prosperity",
    "Cornucopia & Guilds": "cornucopia_guilds",
    "Hinterlands": "hinterlands",
    "Dark Ages": "dark_ages",
    "Adventures": "adventures",
    "Empires": "empires",
    "Nocturne": "nocturne",
    "Renaissance": "renaissance",
    "Menagerie": "menagerie",
    "Allies": "allies",
    "Plunder": "plunder",
    "Rising Sun": "rising_sun",
    "Promo": "promo",
}

INSTRUCTIONS_PATTERNS_REPLS: list[tuple[str, str]] = [
    (r"\[\[File:Coin\d*\.png\|\d+px\|link=\|alt=(\$\d*)\]\](?=\$\d*)", r""),
    (r"\[\[File:Coin\d*\.png\|\d+px\|link=\|alt=(\$\d*)\]\]", r"\1"),
    (r"\[\[File:Potion\.png\|\d+px\|link=Potion\|alt=(P)\]\](?=P)", r""),
    (r"\[\[File:Potion\.png\|\d+px\|link=Potion\|alt=(P)\]\]", r"\1"),
    (r"\[\[File:Debt\d*\.png\|\d+px\|link=Debt\|alt=(\d*D)\]\](?=\d*D)", r""),
    (r"\[\[File:Debt\d*\.png\|\d+px\|link=Debt\|alt=(\d*D)\]\]", r"\1"),
    (
        r"\[\[File:VP\.png\s*\|\s*\d+px\s*\|\s*(?:bottom)?\s*\|\s*link=Victory point\s*\|\s*alt=(VP)\]\]",
        r"\1",
    ),
    (r"\[\[File:Sun\.png\|\d+px\|link=\|alt=(Sun)\]\](?=Sun)", r""),
    (r"\[\[File:Sun\.png\|\d+px\|link=\|alt=(Sun)\]\]", r"\1"),
    (r"\n{2,}", r"\n"),
    (r" {2,}", r" "),
]

# single shared console for all status output.
console = Console()


def ensure_browser() -> None:
    """Install Chromium for Playwright if not already cached."""
    subprocess.run(
        [sys.executable, "-m", "playwright", "install", "chromium"],
        check=True,
    )


def scrape_card_table(*, headless: bool = True) -> list[Card]:
    """Load the wiki page in Chromium, and extract and parse the cards table.

    The wiki uses an anti-bot challenge that requires a real browser engine to
    solve. After the challenge resolves, the actual page may still stream in
    -- so we poll the table row row_count until it stabilises.
    """
    # first, fetch the page's HTML content
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=headless)
        page = browser.new_page()

        console.print(f"Navigating to {WIKI_INDEX_URL} ...")
        page.goto(WIKI_INDEX_URL, timeout=10_000, wait_until="domcontentloaded")

        # wait for the anti-bot challenge to resolve: the real page has an
        # <h1> containing the page title and a large <table>. This sets a
        # session cookie `anubis-cookie-auth`
        console.print("Waiting for anti-bot challenge to resolve ...")
        page.wait_for_selector("h1#firstHeading", timeout=10_000)
        console.print("[green]Challenge passed![/green]")

        # fetch raw cards data
        console.print(f"Navigating to {WIKI_JSON_URL} ...")
        with page.expect_response(WIKI_JSON_URL) as response_info:
            page.goto(WIKI_JSON_URL, timeout=10_000, wait_until="domcontentloaded")
        raw_cards = response_info.value.json()

    # parse raw cards data
    cards: list[Card] = [
        {
            "name": "Ruins",
            "types": ["Action", "Ruins"],
            "purpose": "Basic",
            "cost": {"coins": 0},
            "set": "Dark Ages",
            "editions": [1],
            "quantity": 0,
            "image": "Survivors.jpg",
            "instructions": "Setup: Shuffle the Ruins cards, then count out 10 per player after the first: 10 for two players, 20 for three players, 30 for four players, 40 for five players, or 50 for six players.",
        },
        {
            "name": "Shelters",
            "types": ["Shelter"],
            "purpose": "Basic",
            "cost": {"coins": 1},
            "set": "Dark Ages",
            "editions": [1],
            "quantity": 0,
            "image": "Hovel.jpg",
            "instructions": "Setup: If only Kingdom cards from Dark Ages are being used this game, the Shelter cards replace starting Estates - each player's starting deck is seven Coppers, a Hovel, a Necropolis, and an Overgrown Estate. If a mix of Kingdom cards from Dark Ages and other sets is being used, then the use of Shelters should be determined randomly, based on the proportion of Dark Ages cards in use.",
        },
        {
            "name": "Boons",
            "types": ["Boon"],
            "purpose": "Status",
            "cost": {},
            "set": "Nocturne",
            "editions": [1],
            "quantity": 0,
            "image": "Boon-back.jpg",
            "instructions": "Setup: If any Kingdom cards being used have the Fate type, shuffle the Boons and put them near the Supply, and put the Will-o'-Wisp pile near the Supply also.",
        },
        {
            "name": "Hexes",
            "types": ["Hex"],
            "purpose": "Status",
            "cost": {},
            "set": "Nocturne",
            "editions": [1],
            "quantity": 0,
            "image": "Hex-back.jpg",
            "instructions": "Setup: If any Kingdom cards being used have the Doom type, shuffle the Hexes and put them near the Supply, and put Deluded/Envious and Miserable/Twice Miserable near the Supply also.",
        },
        {
            "name": "Loot",
            "types": ["Treasure", "Loot"],
            "purpose": "Non-Supply",
            "cost": {
                "coins": 7,
                "extra": "*",
            },
            "set": "Plunder",
            "editions": [1],
            "quantity": 0,
            "image": "Amphora.jpg",
            "instructions": "Setup: If any Kingdom cards give Loot, shuffle the Loot cards and set them out near the Supply.",
        },
    ]
    for raw_card in raw_cards:
        cost: Cost = {}
        if coins := raw_card["Cost Coin"]:
            cost["coins"] = coins
        if potion := raw_card["Cost Potion"]:
            cost["potion"] = bool(potion)
        if debt := raw_card["Cost Debt"]:
            cost["debt"] = debt
        if extra := raw_card["Cost Extra"]:
            cost["extra"] = extra

        if not cost and coins is not None:  # card with zero cost
            cost["coins"] = coins

        name = (
            html.unescape(raw_card["Name"]) if raw_card["Name"] != "Farm" else "Harem"
        )

        types = [type_.strip() for type_ in raw_card["Types"]]

        purpose = raw_card["Purpose"]
        if {"Ruins", "Shelter", "Boon", "Hex", "Loot"} & set(types):
            purpose = "Mixed Pile Card"

        set_ = (
            raw_card["Expansion"].replace("&amp;", "&")
            if raw_card["Expansion"] != "Dominion"
            else "Base"
        )

        quantity = raw_card["Quantity"]

        instructions = (
            fromstring(
                unicodedata.normalize(
                    "NFKD", html.unescape(html.unescape(raw_card["Instructions"]))
                )
                .replace("'''", "")  # bold
                .replace("''", "")  # italic
                .replace("<p>", "\n")
                .replace("</p>", "\n")
                .replace("<br>", "\n")
                .replace(
                    '<hr style="width:66%;margin-left:17%;text-align:center;" />',
                    "\n-----\n",
                )
                .replace(
                    '<hr style="width:50%;margin-left:25%;text-align:center;" />',
                    "\n-----\n",
                )
                .replace("\u2013", "-")
                .replace("\u2019", "'")
            )
            .text_content()
            .strip()
        )
        for pattern, repl in INSTRUCTIONS_PATTERNS_REPLS:
            instructions = re.sub(pattern, repl, instructions)

        # prepend "Setup: " to mixed pile cards
        if quantity == 0 and purpose == "Kingdom Pile":
            instructions = f"Setup: {instructions}"

        card: Card = {
            "name": name,
            "types": types,
            "purpose": purpose,
            "cost": cost,
            "set": set_,
            "editions": [
                edition
                if isinstance(edition, int)
                else int(edition.removeprefix("amp;"))
                for edition in raw_card["Edition"]
            ],
            "quantity": quantity,
            "image": html.unescape(raw_card["Image"]),
            "instructions": instructions,
        }
        cards.append(card)

    console.print(f"Extracted [bold]{len(cards)}[/bold] cards from the wiki table.")
    return cards


def categorize_cards(cards: list[Card]) -> dict[str, list[Card]]:
    """Split cards into per-set buckets."""
    set_to_cards: dict[str, list[Card]] = defaultdict(list)

    for card in cards:
        set_ = card["set"]

        if set_ not in SET_TO_FILENAME:
            console.print(
                f"[yellow]WARNING:[/yellow] unknown set {set_!r}"
                f" for card {card['name']!r}"
            )
            continue

        set_to_cards[set_].append(card)

    return set_to_cards


def write_cards_json(
    cards: list[Card], name: str, *, encoding: str = "utf-8", compress: bool = False
) -> None:
    """Write a JSON array to *path* and print a summary line."""
    if compress:
        with gzip.open(CARDS_DIR / f"{name}.gz", "wt", encoding=encoding) as fh:
            json.dump(cards, fh)
    else:
        with CARDS_DIR.joinpath(name).open("w", encoding=encoding) as fh:
            json.dump(cards, fh, indent=2, ensure_ascii=False)
            fh.write("\n")
    console.print(f"  [bold]{name}[/bold]: {len(cards)} cards")


@click.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.option(
    "--headed",
    is_flag=True,
    default=False,
    help="Run browser in headed (visible) mode.",
)
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Parse and categorise cards without writing any files.",
)
@click.option(
    "-c",
    "--compress",
    is_flag=True,
    default=False,
    help="Compress the JSON card data files.",
)
def main(*, headed: bool, dry_run: bool, compress: bool) -> None:
    """Scrape the Dominion Strategy Wiki and write per-set JSON card data files."""
    console.print("Ensuring Chromium browser is installed (for Playwright) ...")
    ensure_browser()

    cards = scrape_card_table(headless=not headed)
    set_to_cards = categorize_cards(cards)

    total_cards = sum(map(len, set_to_cards.values()))
    total_files = len(set_to_cards)

    if dry_run:
        console.print(
            f"[yellow]dry-run[/yellow] Would write {total_cards} cards across {total_files} files."
        )
        return

    # write categorised card data to JSON files
    CARDS_DIR.mkdir(parents=True, exist_ok=True)
    console.print(f"Writing JSON files to [bold]{CARDS_DIR}/[/bold]")

    for set_, set_cards in set_to_cards.items():
        write_cards_json(
            sorted(set_cards, key=lambda card: card["name"]),
            f"{SET_TO_FILENAME[set_]}.json",
            compress=compress,
        )

    console.print(
        f"\n[green]Done[/green] — {total_cards} cards across {total_files} files."
    )


if __name__ == "__main__":
    main()
