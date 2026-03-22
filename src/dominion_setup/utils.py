"""Utility functions for Dominion game setup."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol, TypeAlias, TypeVar, runtime_checkable

from .models import CARD_SET_ORDER, Card, CardSet, CardSetEdition, KingdomSortOrder

if TYPE_CHECKING:
    from collections.abc import Callable


@runtime_checkable
class SupportsBool(Protocol):
    """An ABC with one abstract method ``__bool__``."""

    def __bool__(self) -> bool: ...


_T_contra = TypeVar("_T_contra", contravariant=True)


@runtime_checkable
class SupportsDunderLT(Protocol[_T_contra]):
    """An ABC with one abstract method ``__lt__``."""

    def __lt__(self, other: _T_contra, /) -> SupportsBool: ...


@runtime_checkable
class SupportsDunderGT(Protocol[_T_contra]):
    """An ABC with one abstract method ``__gt__``."""

    def __gt__(self, other: _T_contra, /) -> SupportsBool: ...


SupportsRichComparison: TypeAlias = SupportsDunderLT[Any] | SupportsDunderGT[Any]


def card_sort_key(
    sort_order: KingdomSortOrder,
) -> Callable[[Card], SupportsRichComparison]:
    """Return a sort-key function for the given kingdom sort order."""
    if sort_order == KingdomSortOrder.NAME:
        return lambda card: card.name
    if sort_order == KingdomSortOrder.SET:
        return lambda card: (
            CARD_SET_ORDER[card.set],
            card.cost,
            card.name,
        )
    # default: sort by cost ascending, then name
    return lambda card: (card.cost, card.name)


def parse_raw_set_edition(raw_set_edition: str) -> tuple[CardSet, CardSetEdition]:
    """Parse a raw Set-Edition string (e.g., "base_2e") into a (``CardSet``, ``CardSetEdition``) 2-tuple.

    Handles multi-word expansion names like ``cornucopia_guilds_2e``
    by stripping the known edition suffix first.
    """
    if raw_set_edition.endswith("_2e"):
        return CardSet[raw_set_edition[:-3].upper()], CardSetEdition.SECOND_EDITION
    if raw_set_edition.endswith("_1e"):
        return CardSet[raw_set_edition[:-3].upper()], CardSetEdition.FIRST_EDITION
    return CardSet[raw_set_edition.upper()], CardSetEdition.FIRST_EDITION
