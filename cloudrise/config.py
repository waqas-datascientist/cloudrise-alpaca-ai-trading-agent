from __future__ import annotations

import os
from dataclasses import dataclass


def _float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except ValueError as exc:
        raise ValueError(f"{name} must be a number") from exc


def _int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer") from exc


@dataclass(frozen=True)
class Settings:
    """Runtime settings. CloudRise deliberately has no live-money mode."""

    execution_mode: str = "demo"
    api_key: str = ""
    secret_key: str = ""
    trading_base_url: str = "https://paper-api.alpaca.markets"
    data_base_url: str = "https://data.alpaca.markets"
    universe: tuple[str, ...] = ("SPY", "QQQ", "IWM")
    max_daily_loss_pct: float = 0.015
    max_risk_per_trade_pct: float = 0.006
    max_portfolio_risk_pct: float = 0.025
    min_confidence: float = 0.62
    max_open_spreads: int = 3
    min_dte: int = 7
    max_dte: int = 21
    scan_interval_minutes: int = 15
    competition_starting_balance: float = 100_000.0

    @property
    def has_credentials(self) -> bool:
        return bool(self.api_key and self.secret_key)

    @classmethod
    def from_env(cls) -> "Settings":
        mode = os.getenv("CLOUDRISE_MODE", "demo").strip().lower()
        if mode not in {"demo", "paper"}:
            raise ValueError("CLOUDRISE_MODE must be 'demo' or 'paper'")
        if os.getenv("ALPACA_LIVE_TRADE", "").strip().lower() in {"1", "true", "yes"}:
            raise ValueError("CloudRise is paper-only; unset ALPACA_LIVE_TRADE")
        universe = tuple(
            symbol.strip().upper()
            for symbol in os.getenv("CLOUDRISE_UNIVERSE", "SPY,QQQ,IWM").split(",")
            if symbol.strip()
        )
        return cls(
            execution_mode=mode,
            api_key=os.getenv("ALPACA_API_KEY", "").strip(),
            secret_key=os.getenv("ALPACA_SECRET_KEY", "").strip(),
            universe=universe or ("SPY", "QQQ", "IWM"),
            max_daily_loss_pct=_float("MAX_DAILY_LOSS_PCT", 0.015),
            max_risk_per_trade_pct=_float("MAX_RISK_PER_TRADE_PCT", 0.006),
            max_portfolio_risk_pct=_float("MAX_PORTFOLIO_RISK_PCT", 0.025),
            min_confidence=_float("MIN_CONFIDENCE", 0.62),
            max_open_spreads=_int("MAX_OPEN_SPREADS", 3),
            min_dte=_int("MIN_DTE", 7),
            max_dte=_int("MAX_DTE", 21),
            scan_interval_minutes=_int("SCAN_INTERVAL_MINUTES", 15),
        )

