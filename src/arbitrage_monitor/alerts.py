"""Alert formatting and Telegram delivery."""

from __future__ import annotations

import html
import logging

import httpx

from .models import Opportunity

log = logging.getLogger(__name__)


def format_alert(opp: Opportunity, trade_volume_usdt: float) -> str:
    """Telegram HTML message for one opportunity."""
    esc = html.escape
    return (
        "<b>Arbitrage spread found</b>\n"
        f"Pair: <b>{esc(opp.symbol)}</b>\n"
        f"Buy on <b>{esc(opp.buy_venue)}</b> at <b>{opp.buy_ask:.4f}</b> "
        f"(with fee: {opp.buy_price_with_fee:.4f})\n"
        f"Sell on <b>{esc(opp.sell_venue)}</b> at <b>{opp.sell_bid:.4f}</b> "
        f"(with fee: {opp.sell_price_with_fee:.4f})\n"
        f"Net spread: <b>{opp.profit_pct:.2f}%</b>\n"
        f"Size: <b>{trade_volume_usdt:g} USDT</b> -> <b>{opp.profit_usdt:.2f} USDT</b>\n"
        f"Coins: <b>{opp.amount:.6f}</b>\n"
        "24h volume:\n"
        f" - {esc(opp.buy_venue)}: <b>{opp.buy_volume_usdt:,.2f} USDT</b>\n"
        f" - {esc(opp.sell_venue)}: <b>{opp.sell_volume_usdt:,.2f} USDT</b>\n"
        "<i>Informational only. Check depth and transfer time before acting.</i>"
    )


def strip_html(message: str) -> str:
    """Plain-text version for console output."""
    out, inside = [], False
    for ch in message:
        if ch == "<":
            inside = True
        elif ch == ">":
            inside = False
        elif not inside:
            out.append(ch)
    return html.unescape("".join(out))


class TelegramNotifier:
    def __init__(self, token: str, chat_id: str, client: httpx.AsyncClient | None = None) -> None:
        self._url = f"https://api.telegram.org/bot{token}/sendMessage"
        self._chat_id = chat_id
        self._client = client or httpx.AsyncClient(timeout=10)

    async def send(self, text: str) -> bool:
        payload = {"chat_id": self._chat_id, "text": text, "parse_mode": "HTML"}
        try:
            response = await self._client.post(self._url, data=payload)
        except httpx.HTTPError as exc:
            log.error("Telegram request failed: %s", type(exc).__name__)
            return False
        if response.status_code != 200:
            log.error("Telegram rejected message: HTTP %s", response.status_code)
            return False
        return True

    async def aclose(self) -> None:
        await self._client.aclose()


class ConsoleNotifier:
    """Dry-run notifier: prints instead of sending."""

    async def send(self, text: str) -> bool:
        print(strip_html(text))
        print("-" * 40)
        return True

    async def aclose(self) -> None:
        return None
