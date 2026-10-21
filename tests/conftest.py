from __future__ import annotations

import pytest

from arbitrage_monitor.models import Opportunity, Quote


def make_quote(venue="a", symbol="BTC/USDT", bid=100.0, ask=100.1, volume=1_000_000.0) -> Quote:
    return Quote(venue=venue, symbol=symbol, bid=bid, ask=ask, last=bid, volume_usdt=volume)


def make_opp(**overrides) -> Opportunity:
    base = dict(
        symbol="BTC/USDT",
        buy_venue="binance:spot",
        sell_venue="bybit:spot",
        buy_ask=100.0,
        sell_bid=105.0,
        buy_price_with_fee=100.1,
        sell_price_with_fee=104.895,
        profit_pct=4.78,
        amount=9.99,
        profit_usdt=47.8,
        buy_volume_usdt=500_000.0,
        sell_volume_usdt=250_000.0,
    )
    base.update(overrides)
    return Opportunity(**base)


class FakeClock:
    def __init__(self, now: float = 0.0) -> None:
        self.now = now

    def __call__(self) -> float:
        return self.now


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock()
