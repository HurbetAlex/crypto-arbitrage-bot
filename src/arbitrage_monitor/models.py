from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Quote:
    """Top-of-book prices for one symbol on one venue."""

    venue: str
    symbol: str
    bid: float
    ask: float
    last: float | None = None
    volume_usdt: float = 0.0


@dataclass(frozen=True)
class Opportunity:
    """Buy at the best ask on one venue, sell at the best bid on another."""

    symbol: str
    buy_venue: str
    sell_venue: str
    buy_ask: float
    sell_bid: float
    buy_price_with_fee: float
    sell_price_with_fee: float
    profit_pct: float
    amount: float
    profit_usdt: float
    buy_volume_usdt: float
    sell_volume_usdt: float
