from arbitrage_monitor.filters import SignalFilter
from tests.conftest import make_opp


def make_filter(clock, **kw):
    params = dict(min_profit_pct=2.0, max_profit_pct=200.0, min_volume_usdt=0.0, cooldown=900.0)
    params.update(kw)
    return SignalFilter(clock=clock, **params)


def test_passes_inside_window(clock):
    assert make_filter(clock).passes(make_opp(profit_pct=5))


def test_rejects_below_min(clock):
    assert not make_filter(clock).passes(make_opp(profit_pct=1.5))


def test_min_bound_is_exclusive(clock):
    assert not make_filter(clock).passes(make_opp(profit_pct=2.0))


def test_rejects_above_max_as_data_error(clock):
    assert not make_filter(clock).passes(make_opp(profit_pct=350))


def test_max_bound_is_exclusive(clock):
    assert not make_filter(clock).passes(make_opp(profit_pct=200.0))


def test_volume_floor_checks_the_thinner_side(clock):
    f = make_filter(clock, min_volume_usdt=100_000)
    assert f.passes(make_opp(buy_volume_usdt=500_000, sell_volume_usdt=150_000))
    assert not f.passes(make_opp(buy_volume_usdt=500_000, sell_volume_usdt=50_000))
    assert not f.passes(make_opp(buy_volume_usdt=50_000, sell_volume_usdt=500_000))


def test_zero_volume_floor_accepts_zero_volume(clock):
    assert make_filter(clock).passes(make_opp(buy_volume_usdt=0, sell_volume_usdt=0))


def test_first_alert_goes_through(clock):
    assert make_filter(clock).should_alert(make_opp())


def test_duplicate_within_cooldown_is_muted(clock):
    f = make_filter(clock)
    assert f.should_alert(make_opp())
    clock.now = 899
    assert not f.should_alert(make_opp())


def test_alert_again_after_cooldown(clock):
    f = make_filter(clock)
    assert f.should_alert(make_opp())
    clock.now = 900
    assert f.should_alert(make_opp())


def test_different_route_is_not_deduplicated(clock):
    f = make_filter(clock)
    assert f.should_alert(make_opp())
    assert f.should_alert(make_opp(sell_venue="kucoin:spot"))
    assert f.should_alert(make_opp(symbol="ETH/USDT"))


def test_reversed_route_is_a_different_key(clock):
    f = make_filter(clock)
    assert f.should_alert(make_opp(buy_venue="a", sell_venue="b"))
    assert f.should_alert(make_opp(buy_venue="b", sell_venue="a"))


def test_rejected_opportunity_does_not_start_cooldown(clock):
    f = make_filter(clock)
    assert not f.should_alert(make_opp(profit_pct=0.5))
    assert f.should_alert(make_opp(profit_pct=5))


def test_forget_expired_removes_only_stale_entries(clock):
    f = make_filter(clock)
    f.should_alert(make_opp(symbol="OLD/USDT"))
    clock.now = 600
    f.should_alert(make_opp(symbol="NEW/USDT"))
    clock.now = 950
    assert f.forget_expired() == 1
    assert not f.should_alert(make_opp(symbol="NEW/USDT"))
    assert f.should_alert(make_opp(symbol="OLD/USDT"))


def test_zero_cooldown_never_mutes(clock):
    f = make_filter(clock, cooldown=0)
    assert f.should_alert(make_opp())
    assert f.should_alert(make_opp())
