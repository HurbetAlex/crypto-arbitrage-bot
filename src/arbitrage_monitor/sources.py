"""Price sources: ccxt exchanges (REST) and DexScreener."""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Protocol

import httpx

from .models import Quote
from .symbols import normalize_symbol

log = logging.getLogger(__name__)

DEXSCREENER_URL = "https://api.dexscreener.com/latest/dex/search?q=USDT"


class ExchangeLike(Protocol):
    """The subset of the ccxt API used here (sync, as in ccxt's REST classes)."""

    def load_markets(self) -> dict[str, Any]: ...
    def fetch_ticker(self, symbol: str) -> dict[str, Any]: ...


def ticker_to_quote(venue: str, symbol: str, ticker: dict[str, Any]) -> Quote | None:
    """Convert a ccxt ticker to a Quote, or None when bid/ask are missing."""
    bid, ask = ticker.get("bid"), ticker.get("ask")
    if bid is None or ask is None:
        return None
    return Quote(
        venue=venue,
        symbol=symbol,
        bid=float(bid),
        ask=float(ask),
        last=ticker.get("last"),
        volume_usdt=float(ticker.get("quoteVolume") or 0.0),
    )


class ExchangeSource:
    """One ccxt exchange instance for one market type. Blocking calls run in a thread."""

    def __init__(self, name: str, exchange: ExchangeLike) -> None:
        self.name = name
        self._ex = exchange
        self._market_keys: dict[str, str] = {}

    async def load_symbols(self) -> list[str]:
        markets = await asyncio.to_thread(self._ex.load_markets)
        self._market_keys = {}
        for key in markets:
            norm = normalize_symbol(key)
            # Prefer the plain spot-style key when both 'BTC/USDT' and 'BTC/USDT:USDT' exist.
            if norm and (norm not in self._market_keys or key == norm):
                self._market_keys[norm] = key
        return list(self._market_keys)

    async def fetch_quote(self, symbol: str) -> Quote | None:
        key = self._market_keys.get(symbol, symbol)
        try:
            ticker = await asyncio.to_thread(self._ex.fetch_ticker, key)
        except Exception as exc:  # ccxt raises many exchange-specific subclasses
            log.warning("%s: ticker for %s failed: %s", self.name, symbol, type(exc).__name__)
            return None
        return ticker_to_quote(self.name, symbol, ticker)


def parse_dex_pairs(payload: dict[str, Any]) -> dict[str, Quote]:
    """Quotes from a DexScreener search response. Highest-volume pool wins per symbol."""
    best: dict[str, Quote] = {}
    for pair in payload.get("pairs") or []:
        try:
            if str(pair["quoteToken"]["symbol"]).upper() != "USDT":
                continue
            symbol = normalize_symbol(f"{pair['baseToken']['symbol']}/USDT")
            price = float(pair["priceUsd"])
        except (KeyError, TypeError, ValueError):
            continue
        if not symbol or price <= 0:
            continue
        volume = float((pair.get("volume") or {}).get("h24") or 0.0)
        current = best.get(symbol)
        if current is None or volume > current.volume_usdt:
            best[symbol] = Quote("dex", symbol, price, price, price, volume)
    return best


async def fetch_dex_quotes(client: httpx.AsyncClient) -> dict[str, Quote]:
    try:
        response = await client.get(DEXSCREENER_URL, timeout=10)
        response.raise_for_status()
        return parse_dex_pairs(response.json())
    except (httpx.HTTPError, ValueError) as exc:
        log.error("DexScreener request failed: %s", type(exc).__name__)
        return {}
