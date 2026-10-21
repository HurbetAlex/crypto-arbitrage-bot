import pytest

from arbitrage_monitor.spread import find_opportunity
from tests.conftest import make_quote


def no_fee(_):
    return 0.0


def test_needs_two_venues():
    assert find_opportunity({"a": make_quote("a")}, no_fee, 1000) is None


def test_no_opportunity_when_spread_negative():
    quotes = {"a": make_quote("a", bid=99, ask=100), "b": make_quote("b", bid=99.5, ask=100.5)}
    assert find_opportunity(quotes, no_fee, 1000) is None


def test_picks_lowest_ask_and_highest_bid():
    quotes = {
        "a": make_quote("a", bid=100, ask=101),
        "b": make_quote("b", bid=110, ask=111),
        "c": make_quote("c", bid=99, ask=100),
    }
    opp = find_opportunity(quotes, no_fee, 1000)
    assert opp.buy_venue == "c"
    assert opp.sell_venue == "b"
    assert opp.buy_ask == 100 and opp.sell_bid == 110


def test_profit_pct_without_fees():
    quotes = {"a": make_quote("a", bid=99, ask=100), "b": make_quote("b", bid=105, ask=106)}
    opp = find_opportunity(quotes, no_fee, 1000)
    assert opp.profit_pct == pytest.approx(5.0)
    assert opp.amount == pytest.approx(10.0)
    assert opp.profit_usdt == pytest.approx(50.0)


def test_fees_reduce_profit():
    quotes = {"a": make_quote("a", bid=99, ask=100), "b": make_quote("b", bid=105, ask=106)}
    opp = find_opportunity(quotes, lambda _: 0.01, 1000)
    assert opp.buy_price_with_fee == pytest.approx(101.0)
    assert opp.sell_price_with_fee == pytest.approx(103.95)
    assert opp.profit_pct == pytest.approx((103.95 - 101.0) / 101.0 * 100)


def test_fees_can_erase_the_spread():
    quotes = {"a": make_quote("a", bid=99, ask=100), "b": make_quote("b", bid=100.5, ask=101)}
    assert find_opportunity(quotes, no_fee, 1000) is not None
    assert find_opportunity(quotes, lambda _: 0.01, 1000) is None


def test_per_venue_fees_are_applied_to_the_right_leg():
    fees = {"a": 0.0, "b": 0.02}
    quotes = {"a": make_quote("a", bid=99, ask=100), "b": make_quote("b", bid=110, ask=111)}
    opp = find_opportunity(quotes, fees.__getitem__, 1000)
    assert opp.buy_price_with_fee == pytest.approx(100.0)
    assert opp.sell_price_with_fee == pytest.approx(110 * 0.98)


def test_same_venue_best_on_both_sides_is_ignored():
    quotes = {"a": make_quote("a", bid=100, ask=99), "b": make_quote("b", bid=98, ask=101)}
    assert find_opportunity(quotes, no_fee, 1000) is None


def test_non_positive_prices_are_dropped():
    quotes = {"a": make_quote("a", bid=0, ask=0), "b": make_quote("b", bid=105, ask=106)}
    assert find_opportunity(quotes, no_fee, 1000) is None


def test_volumes_are_carried_over():
    quotes = {
        "a": make_quote("a", bid=99, ask=100, volume=111.0),
        "b": make_quote("b", bid=105, ask=106, volume=222.0),
    }
    opp = find_opportunity(quotes, no_fee, 1000)
    assert (opp.buy_volume_usdt, opp.sell_volume_usdt) == (111.0, 222.0)


def test_trade_volume_scales_profit_not_pct():
    quotes = {"a": make_quote("a", bid=99, ask=100), "b": make_quote("b", bid=105, ask=106)}
    small = find_opportunity(quotes, no_fee, 1000)
    big = find_opportunity(quotes, no_fee, 5000)
    assert big.profit_pct == pytest.approx(small.profit_pct)
    assert big.profit_usdt == pytest.approx(small.profit_usdt * 5)
