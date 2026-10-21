import pytest

from arbitrage_monitor.symbols import common_usdt_symbols, normalize_symbol


@pytest.mark.parametrize(
    "raw",
    [
        "BTC/USDT",
        "btc/usdt",
        "BTC-USDT",
        "BTC_USDT",
        "BTCUSDT",
        "btcusdt",
        "BTC/USDT:USDT",
        " BTC/USDT ",
    ],
)
def test_normalize_common_spellings(raw):
    assert normalize_symbol(raw) == "BTC/USDT"


@pytest.mark.parametrize(
    "raw", ["", "BTC/USD", "BTC/USDC", "USDT", "BTC", "/USDT", "BT$C/USDT", "ETHBTC"]
)
def test_normalize_rejects_non_usdt_or_malformed(raw):
    assert normalize_symbol(raw) is None


def test_normalize_keeps_numeric_base():
    assert normalize_symbol("1000SHIB/USDT:USDT") == "1000SHIB/USDT"


def test_common_symbols_intersection_and_sorted():
    venue_a = ["ETH/USDT", "BTC/USDT", "XRP/USDT", "BTC/EUR"]
    venue_b = ["BTC/USDT:USDT", "ETH/USDT:USDT", "DOGE/USDT:USDT"]
    assert common_usdt_symbols([venue_a, venue_b]) == ["BTC/USDT", "ETH/USDT"]


def test_common_symbols_empty_input():
    assert common_usdt_symbols([]) == []


def test_common_symbols_disjoint():
    assert common_usdt_symbols([["BTC/USDT"], ["ETH/USDT"]]) == []
