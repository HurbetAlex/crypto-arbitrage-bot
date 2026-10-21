from arbitrage_monitor.config import Settings
from arbitrage_monitor.filters import SignalFilter
from arbitrage_monitor.models import Quote
from arbitrage_monitor.monitor import Monitor
from tests.conftest import make_quote


class FakeSource:
    def __init__(self, name, symbols, quotes):
        self.name, self._symbols, self._quotes = name, symbols, quotes

    async def load_symbols(self):
        return self._symbols

    async def fetch_quote(self, symbol):
        return self._quotes.get(symbol)


class FakeNotifier:
    def __init__(self, ok=True):
        self.messages, self.ok = [], ok

    async def send(self, text):
        self.messages.append(text)
        return self.ok


def build(sources, notifier=None, dex=None, **settings):
    s = Settings(
        _env_file=None, default_fee_rate=0.0, max_cycles=1, poll_interval_seconds=0, **settings
    )
    notifier = notifier or FakeNotifier()
    f = SignalFilter(
        s.min_profit_pct, s.max_profit_pct, s.min_volume_usdt, s.alert_cooldown_seconds
    )
    return Monitor(s, sources, notifier, f, dex), notifier


def two_sources(ask_b=110.0):
    a = FakeSource(
        "a", ["BTC/USDT", "ETH/USDT"], {"BTC/USDT": make_quote("a", "BTC/USDT", 99, 100)}
    )
    b = FakeSource(
        "b", ["BTC/USDT:USDT"], {"BTC/USDT": make_quote("b", "BTC/USDT", ask_b, ask_b + 1)}
    )
    return [a, b]


async def test_load_symbols_is_intersection():
    monitor, _ = build(two_sources())
    assert await monitor.load_symbols() == ["BTC/USDT"]


async def test_cycle_sends_alert_for_profitable_route():
    monitor, notifier = build(two_sources())
    await monitor.load_symbols()
    sent = await monitor.run_cycle()
    assert len(sent) == 1 and len(notifier.messages) == 1
    assert "BTC/USDT" in notifier.messages[0]


async def test_cycle_deduplicates_across_cycles():
    monitor, notifier = build(two_sources())
    await monitor.load_symbols()
    await monitor.run_cycle()
    await monitor.run_cycle()
    assert len(notifier.messages) == 1


async def test_small_spread_is_filtered_out():
    monitor, notifier = build(two_sources(ask_b=100.5))
    await monitor.load_symbols()
    assert await monitor.run_cycle() == []
    assert notifier.messages == []


async def test_failed_send_is_not_counted():
    monitor, _ = build(two_sources(), notifier=FakeNotifier(ok=False))
    await monitor.load_symbols()
    assert await monitor.run_cycle() == []


async def test_dex_quote_participates():
    a = FakeSource("a", ["BTC/USDT"], {"BTC/USDT": make_quote("a", "BTC/USDT", 99, 100)})
    b = FakeSource("b", ["BTC/USDT"], {})

    async def dex():
        return {"BTC/USDT": Quote("dex", "BTC/USDT", 120, 120, 120, 5000)}

    monitor, notifier = build([a, b], dex=dex)
    await monitor.load_symbols()
    await monitor.run_cycle()
    assert "dex" in notifier.messages[0]


async def test_run_stops_after_max_cycles():
    monitor, notifier = build(two_sources())
    await monitor.run()
    assert len(notifier.messages) == 1
