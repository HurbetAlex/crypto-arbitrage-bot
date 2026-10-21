"""Runtime configuration, read from environment variables or a .env file."""

from __future__ import annotations

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

SUPPORTED_MARKETS = {"spot", "future"}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    telegram_bot_token: str = ""
    telegram_chat_id: str = ""

    venues: str = "binance:spot,binance:future,bybit:spot,bybit:future,kucoin:spot,kucoin:future"
    enable_dex: bool = False

    trade_volume_usdt: float = Field(1000.0, gt=0)
    min_profit_pct: float = Field(2.0, ge=0)
    max_profit_pct: float = Field(200.0, gt=0)
    min_volume_usdt: float = Field(0.0, ge=0)
    alert_cooldown_seconds: float = Field(900.0, ge=0)

    default_fee_rate: float = Field(0.001, ge=0, lt=1)
    dex_fee_rate: float = Field(0.003, ge=0, lt=1)
    fee_overrides: dict[str, float] = Field(default_factory=dict)

    poll_interval_seconds: float = Field(10.0, ge=0)
    request_timeout_ms: int = Field(10_000, gt=0)
    max_cycles: int = Field(0, ge=0)
    dry_run: bool = True

    @field_validator("venues")
    @classmethod
    def _check_venues(cls, value: str) -> str:
        for venue in parse_venues(value):
            if venue[1] not in SUPPORTED_MARKETS:
                raise ValueError(f"unsupported market type in venue {venue[0]}:{venue[1]}")
        return value

    @property
    def venue_list(self) -> list[tuple[str, str]]:
        return parse_venues(self.venues)

    def fee_for(self, venue_name: str) -> float:
        """Fee fraction charged on one leg at the given venue."""
        if venue_name in self.fee_overrides:
            return self.fee_overrides[venue_name]
        if venue_name == "dex":
            return self.dex_fee_rate
        return self.default_fee_rate

    @property
    def telegram_configured(self) -> bool:
        return bool(self.telegram_bot_token and self.telegram_chat_id)


def parse_venues(raw: str) -> list[tuple[str, str]]:
    """Parse 'binance:spot,bybit:future' into [('binance', 'spot'), ('bybit', 'future')]."""
    venues: list[tuple[str, str]] = []
    for item in raw.split(","):
        item = item.strip().lower()
        if not item:
            continue
        exchange, _, market = item.partition(":")
        venues.append((exchange, market or "spot"))
    return venues


def venue_name(exchange: str, market: str) -> str:
    return f"{exchange}:{market}"
