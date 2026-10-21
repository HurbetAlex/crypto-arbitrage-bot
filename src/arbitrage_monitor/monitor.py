"""Polling loop: fetch quotes, compute spreads, filter, alert."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable, Sequence
from typing import Protocol

from .alerts import format_alert
from .config import Settings
from .filters import SignalFilter
from .models import Opportunity, Quote
from .spread import find_opportunity
from .symbols import common_usdt_symbols

log = logging.getLogger(__name__)


class QuoteSource(Protocol):
    name: str

    async def load_symbols(self) -> list[str]: ...
    async def fetch_quote(self, symbol: str) -> Quote | None: ...


class Notifier(Protocol):
    async def send(self, text: str) -> bool: ...


DexFetcher = Callable[[], Awaitable[dict[str, Quote]]]


class Monitor:
    def __init__(
        self,
        settings: Settings,
        sources: Sequence[QuoteSource],
        notifier: Notifier,
        signal_filter: SignalFilter,
        dex_fetcher: DexFetcher | None = None,
    ) -> None:
        self.settings = settings
        self.sources = list(sources)
        self.notifier = notifier
        self.filter = signal_filter
        self.dex_fetcher = dex_fetcher
        self.symbols: list[str] = []

    async def load_symbols(self) -> list[str]:
        sets = await asyncio.gather(*(s.load_symbols() for s in self.sources))
        self.symbols = common_usdt_symbols(sets)
        log.info("%d symbols common to %d venues", len(self.symbols), len(self.sources))
        return self.symbols

    async def scan_symbol(
        self, symbol: str, dex_quotes: dict[str, Quote] | None = None
    ) -> Opportunity | None:
        results = await asyncio.gather(*(s.fetch_quote(symbol) for s in self.sources))
        quotes = {q.venue: q for q in results if q is not None}
        if dex_quotes and symbol in dex_quotes:
            quotes["dex"] = dex_quotes[symbol]
        return find_opportunity(quotes, self.settings.fee_for, self.settings.trade_volume_usdt)

    async def run_cycle(self) -> list[Opportunity]:
        dex_quotes = await self.dex_fetcher() if self.dex_fetcher else None
        sent: list[Opportunity] = []
        for symbol in self.symbols:
            opp = await self.scan_symbol(symbol, dex_quotes)
            if opp and self.filter.should_alert(opp):
                message = format_alert(opp, self.settings.trade_volume_usdt)
                if await self.notifier.send(message):
                    sent.append(opp)
        self.filter.forget_expired()
        return sent

    async def run(self) -> None:
        await self.load_symbols()
        cycle = 0
        while True:
            cycle += 1
            await self.run_cycle()
            if self.settings.max_cycles and cycle >= self.settings.max_cycles:
                return
            await asyncio.sleep(self.settings.poll_interval_seconds)
