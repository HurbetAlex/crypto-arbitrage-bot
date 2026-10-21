"""Symbol normalisation and market intersection."""

from __future__ import annotations

import re
from collections.abc import Iterable

QUOTE = "USDT"
_SEPARATORS = re.compile(r"[-_ ]")


def normalize_symbol(raw: str) -> str | None:
    """Return 'BASE/USDT' for any common spelling, or None if not a USDT pair.

    Handles 'btc/usdt', 'BTC-USDT', 'BTCUSDT', and ccxt swap symbols like 'BTC/USDT:USDT'.
    """
    if not raw:
        return None
    text = raw.strip().upper()
    text = text.split(":", 1)[0]  # drop the settle currency of derivatives
    text = _SEPARATORS.sub("/", text)
    if "/" in text:
        base, _, quote = text.partition("/")
    elif text.endswith(QUOTE) and len(text) > len(QUOTE):
        base, quote = text[: -len(QUOTE)], QUOTE
    else:
        return None
    if quote != QUOTE or not base or not base.isalnum():
        return None
    return f"{base}/{QUOTE}"


def common_usdt_symbols(symbol_sets: Iterable[Iterable[str]]) -> list[str]:
    """Sorted USDT pairs listed on every venue (after normalisation)."""
    normalized: list[set[str]] = []
    for symbols in symbol_sets:
        normalized.append({s for s in map(normalize_symbol, symbols) if s})
    if not normalized:
        return []
    return sorted(set.intersection(*normalized))
