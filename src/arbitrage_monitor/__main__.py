"""Entry point: `python -m arbitrage_monitor` or the `arbitrage-monitor` script."""

from __future__ import annotations

import asyncio
import logging

import ccxt
import httpx

from .alerts import ConsoleNotifier, TelegramNotifier
from .config import Settings, venue_name
from .filters import SignalFilter
from .monitor import Monitor
from .sources import ExchangeSource, fetch_dex_quotes


def build_sources(settings: Settings) -> list[ExchangeSource]:
    sources = []
    for exchange_id, market in settings.venue_list:
        cls = getattr(ccxt, exchange_id, None)
        if cls is None:
            raise SystemExit(f"Unknown exchange id: {exchange_id}")
        instance = cls({"options": {"defaultType": market}, "timeout": settings.request_timeout_ms})
        sources.append(ExchangeSource(venue_name(exchange_id, market), instance))
    return sources


async def amain() -> None:
    settings = Settings()
    notifier: ConsoleNotifier | TelegramNotifier
    if settings.dry_run or not settings.telegram_configured:
        if not settings.dry_run:
            logging.warning("Telegram is not configured, falling back to console output")
        notifier = ConsoleNotifier()
    else:
        notifier = TelegramNotifier(settings.telegram_bot_token, settings.telegram_chat_id)

    signal_filter = SignalFilter(
        settings.min_profit_pct,
        settings.max_profit_pct,
        settings.min_volume_usdt,
        settings.alert_cooldown_seconds,
    )
    async with httpx.AsyncClient() as http:
        dex_fetcher = (lambda: fetch_dex_quotes(http)) if settings.enable_dex else None
        monitor = Monitor(settings, build_sources(settings), notifier, signal_filter, dex_fetcher)
        try:
            await monitor.run()
        finally:
            await notifier.aclose()


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    try:
        asyncio.run(amain())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
