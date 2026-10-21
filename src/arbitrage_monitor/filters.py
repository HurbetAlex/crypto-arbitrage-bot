"""Signal filter: profit window, liquidity floor and alert de-duplication."""

from __future__ import annotations

import time
from collections.abc import Callable

from .models import Opportunity


class SignalFilter:
    """Decides whether an opportunity is worth an alert.

    Profit must be inside (min_profit_pct, max_profit_pct): the upper bound drops
    obvious data errors such as a delisted token quoting a stale price. A pair that
    was already alerted for the same buy/sell route is muted for `cooldown` seconds.
    """

    def __init__(
        self,
        min_profit_pct: float,
        max_profit_pct: float,
        min_volume_usdt: float = 0.0,
        cooldown: float = 900.0,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.min_profit_pct = min_profit_pct
        self.max_profit_pct = max_profit_pct
        self.min_volume_usdt = min_volume_usdt
        self.cooldown = cooldown
        self._clock = clock
        self._last_alert: dict[tuple[str, str, str], float] = {}

    def passes(self, opp: Opportunity) -> bool:
        """Stateless checks only (no dedup)."""
        if not (self.min_profit_pct < opp.profit_pct < self.max_profit_pct):
            return False
        if min(opp.buy_volume_usdt, opp.sell_volume_usdt) < self.min_volume_usdt:
            return False
        return True

    def should_alert(self, opp: Opportunity) -> bool:
        """Full decision. Records the alert when it returns True."""
        if not self.passes(opp):
            return False
        key = (opp.symbol, opp.buy_venue, opp.sell_venue)
        now = self._clock()
        last = self._last_alert.get(key)
        if last is not None and now - last < self.cooldown:
            return False
        self._last_alert[key] = now
        return True

    def forget_expired(self) -> int:
        """Drop dedup entries older than the cooldown. Returns how many were removed."""
        now = self._clock()
        stale = [k for k, t in self._last_alert.items() if now - t >= self.cooldown]
        for key in stale:
            del self._last_alert[key]
        return len(stale)
