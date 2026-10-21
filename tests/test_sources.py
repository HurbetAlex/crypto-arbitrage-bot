import httpx
import pytest

from arbitrage_monitor.sources import (
    ExchangeSource,
    fetch_dex_quotes,
    parse_dex_pairs,
    ticker_to_quote,
)


def test_ticker_to_quote_basic():
    q = ticker_to_quote("v", "BTC/USDT", {"bid": 1, "ask": 2, "last": 1.5, "quoteVolume": 10})
    assert (q.bid, q.ask, q.last, q.volume_usdt) == (1.0, 2.0, 1.5, 10.0)


@pytest.mark.parametrize("ticker", [{"bid": None, "ask": 1}, {"bid": 1, "ask": None}, {}])
def test_ticker_to_quote_missing_side(ticker):
    assert ticker_to_quote("v", "BTC/USDT", ticker) is None


def test_ticker_to_quote_missing_volume_is_zero():
    assert (
        ticker_to_quote("v", "X/USDT", {"bid": 1, "ask": 2, "quoteVolume": None}).volume_usdt == 0
    )


class FakeExchange:
    def __init__(self, markets, tickers):
        self._markets, self._tickers, self.calls = markets, tickers, []

    def load_markets(self):
        return self._markets

    def fetch_ticker(self, symbol):
        self.calls.append(symbol)
        value = self._tickers[symbol]
        if isinstance(value, Exception):
            raise value
        return value


async def test_load_symbols_normalises_and_prefers_spot_key():
    ex = FakeExchange({"BTC/USDT:USDT": {}, "BTC/USDT": {}, "ETH/USDT:USDT": {}, "BTC/EUR": {}}, {})
    src = ExchangeSource("v", ex)
    assert sorted(await src.load_symbols()) == ["BTC/USDT", "ETH/USDT"]
    assert src._market_keys["BTC/USDT"] == "BTC/USDT"
    assert src._market_keys["ETH/USDT"] == "ETH/USDT:USDT"


async def test_fetch_quote_uses_native_market_key():
    ex = FakeExchange({"ETH/USDT:USDT": {}}, {"ETH/USDT:USDT": {"bid": 1, "ask": 2}})
    src = ExchangeSource("bybit:future", ex)
    await src.load_symbols()
    quote = await src.fetch_quote("ETH/USDT")
    assert ex.calls == ["ETH/USDT:USDT"]
    assert quote.venue == "bybit:future" and quote.symbol == "ETH/USDT"


async def test_fetch_quote_swallows_exchange_errors():
    ex = FakeExchange({"BTC/USDT": {}}, {"BTC/USDT": RuntimeError("rate limit")})
    src = ExchangeSource("v", ex)
    await src.load_symbols()
    assert await src.fetch_quote("BTC/USDT") is None


def pair(base="PEPE", quote="USDT", price="0.5", h24=100):
    return {
        "baseToken": {"symbol": base},
        "quoteToken": {"symbol": quote},
        "priceUsd": price,
        "volume": {"h24": h24},
    }


def test_parse_dex_pairs_basic():
    quotes = parse_dex_pairs({"pairs": [pair()]})
    assert quotes["PEPE/USDT"].bid == quotes["PEPE/USDT"].ask == 0.5
    assert quotes["PEPE/USDT"].venue == "dex"


def test_parse_dex_keeps_highest_volume_pool():
    quotes = parse_dex_pairs({"pairs": [pair(price="1", h24=10), pair(price="2", h24=99)]})
    assert quotes["PEPE/USDT"].bid == 2.0


def test_parse_dex_skips_other_quotes_and_bad_rows():
    payload = {
        "pairs": [pair(quote="WETH"), pair(price="abc"), pair(price="0"), {"x": 1}, pair("OK")]
    }
    assert list(parse_dex_pairs(payload)) == ["OK/USDT"]


@pytest.mark.parametrize("payload", [{}, {"pairs": None}, {"pairs": []}])
def test_parse_dex_empty(payload):
    assert parse_dex_pairs(payload) == {}


async def test_fetch_dex_quotes_ok_and_error():
    ok = httpx.AsyncClient(
        transport=httpx.MockTransport(lambda r: httpx.Response(200, json={"pairs": [pair()]}))
    )
    assert "PEPE/USDT" in await fetch_dex_quotes(ok)
    bad = httpx.AsyncClient(transport=httpx.MockTransport(lambda r: httpx.Response(500)))
    assert await fetch_dex_quotes(bad) == {}
