import pytest
from pydantic import ValidationError

from arbitrage_monitor.config import Settings, parse_venues, venue_name


def test_parse_venues():
    assert parse_venues("Binance:spot, bybit:future,,") == [
        ("binance", "spot"),
        ("bybit", "future"),
    ]


def test_parse_venues_defaults_to_spot():
    assert parse_venues("kucoin") == [("kucoin", "spot")]


def test_venue_name():
    assert venue_name("binance", "spot") == "binance:spot"


def test_defaults_are_safe(monkeypatch):
    monkeypatch.chdir("/")
    s = Settings(_env_file=None)
    assert s.dry_run is True
    assert s.enable_dex is False
    assert s.telegram_configured is False
    assert len(s.venue_list) == 6


def test_reads_environment(monkeypatch):
    monkeypatch.setenv("MIN_PROFIT_PCT", "3.5")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "t")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "c")
    s = Settings(_env_file=None)
    assert s.min_profit_pct == 3.5
    assert s.telegram_configured is True


def test_fee_overrides_from_json_env(monkeypatch):
    monkeypatch.setenv("FEE_OVERRIDES", '{"bybit:spot": 0.0008}')
    s = Settings(_env_file=None)
    assert s.fee_for("bybit:spot") == 0.0008
    assert s.fee_for("binance:spot") == s.default_fee_rate


def test_dex_fee_rate():
    s = Settings(_env_file=None)
    assert s.fee_for("dex") == s.dex_fee_rate


def test_rejects_unknown_market_type():
    with pytest.raises(ValidationError):
        Settings(_env_file=None, venues="binance:margin")


@pytest.mark.parametrize(
    "field,value", [("trade_volume_usdt", 0), ("default_fee_rate", 1.0), ("min_profit_pct", -1)]
)
def test_rejects_out_of_range_values(field, value):
    with pytest.raises(ValidationError):
        Settings(_env_file=None, **{field: value})


def test_telegram_requires_both_values():
    assert Settings(_env_file=None, telegram_bot_token="t").telegram_configured is False
