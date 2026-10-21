"""Spread calculation: best ask vs best bid across venues, net of fees."""

from __future__ import annotations

from collections.abc import Callable, Mapping

from .models import Opportunity, Quote


def find_opportunity(
    quotes: Mapping[str, Quote],
    fee_for: Callable[[str], float],
    trade_volume_usdt: float,
) -> Opportunity | None:
    """Best cross-venue trade for one symbol, or None if there is no positive net spread.

    Needs quotes from at least two venues. Fees are applied as a fraction on each leg:
    the buy price is raised by the buy fee, the sell price lowered by the sell fee.
    """
    usable = {
        name: q
        for name, q in quotes.items()
        if q.bid is not None and q.ask is not None and q.bid > 0 and q.ask > 0
    }
    if len(usable) < 2:
        return None

    buy_venue = min(usable, key=lambda n: usable[n].ask)
    sell_venue = max(usable, key=lambda n: usable[n].bid)
    if buy_venue == sell_venue:
        return None

    buy, sell = usable[buy_venue], usable[sell_venue]
    buy_price = buy.ask * (1 + fee_for(buy_venue))
    sell_price = sell.bid * (1 - fee_for(sell_venue))
    if sell_price <= buy_price:
        return None

    amount = trade_volume_usdt / buy_price
    return Opportunity(
        symbol=buy.symbol,
        buy_venue=buy_venue,
        sell_venue=sell_venue,
        buy_ask=buy.ask,
        sell_bid=sell.bid,
        buy_price_with_fee=buy_price,
        sell_price_with_fee=sell_price,
        profit_pct=(sell_price - buy_price) / buy_price * 100,
        amount=amount,
        profit_usdt=(sell_price - buy_price) * amount,
        buy_volume_usdt=buy.volume_usdt,
        sell_volume_usdt=sell.volume_usdt,
    )
