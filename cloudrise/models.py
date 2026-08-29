from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date, datetime
from typing import Any


@dataclass(frozen=True)
class Bar:
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float


@dataclass(frozen=True)
class Vote:
    agent: str
    score: float
    label: str
    evidence: str


@dataclass(frozen=True)
class Thesis:
    symbol: str
    direction: str
    score: float
    confidence: float
    agreement: float
    spot: float
    realized_volatility: float
    rsi: float
    votes: tuple[Vote, ...] = field(default_factory=tuple)
    summary: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ContractQuote:
    symbol: str
    expiration: date
    option_type: str
    strike: float
    bid: float
    ask: float
    delta: float | None = None
    implied_volatility: float | None = None

    @property
    def midpoint(self) -> float:
        return round((self.bid + self.ask) / 2, 4)

    @property
    def spread_pct(self) -> float:
        return (self.ask - self.bid) / max(self.midpoint, 0.01)


@dataclass(frozen=True)
class SpreadPlan:
    underlying: str
    direction: str
    strategy: str
    expiration: date
    long_leg: ContractQuote
    short_leg: ContractQuote
    limit_debit: float
    width: float
    max_loss_per_contract: float
    max_profit_per_contract: float
    reward_risk: float
    liquidity_score: float

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["expiration"] = self.expiration.isoformat()
        result["long_leg"]["expiration"] = self.long_leg.expiration.isoformat()
        result["short_leg"]["expiration"] = self.short_leg.expiration.isoformat()
        return result


@dataclass(frozen=True)
class RiskDecision:
    approved: bool
    quantity: int
    risk_dollars: float
    portfolio_risk_after: float
    gates: tuple[dict[str, Any], ...]
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

