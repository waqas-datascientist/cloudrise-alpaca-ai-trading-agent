from __future__ import annotations

import re
from collections import defaultdict
from datetime import date, datetime
from typing import Any

from .indicators import average_true_range, clamp, ema, realized_volatility, rsi
from .models import Bar, ContractQuote, SpreadPlan, Thesis, Vote


OCC_PATTERN = re.compile(r"^([A-Z]{1,6})(\d{6})([CP])(\d{8})$")


class ResearchCommittee:
    """An explainable ensemble of specialist agents.

    Each specialist produces an independent normalized vote. No LLM or paid API
    is required, so the exact same inputs always produce the same decision.
    """

    def analyze(self, symbol: str, bars: list[Bar]) -> Thesis:
        if len(bars) < 40:
            raise ValueError(f"{symbol} needs at least 40 bars; received {len(bars)}")

        closes = [bar.close for bar in bars]
        highs = [bar.high for bar in bars]
        lows = [bar.low for bar in bars]
        spot = closes[-1]
        fast = ema(closes, 8)
        slow = ema(closes, 21)
        ema_gap = (fast[-1] - slow[-1]) / spot
        momentum = (spot / closes[-13]) - 1.0
        recent_high = max(highs[-21:-1])
        recent_low = min(lows[-21:-1])
        channel = max(recent_high - recent_low, spot * 0.002)
        breakout = clamp(((spot - (recent_high + recent_low) / 2.0) / channel) * 1.5)
        current_rsi = rsi(closes)
        current_vol = realized_volatility(closes)
        atr_pct = average_true_range(highs, lows, closes) / spot

        trend_score = clamp(ema_gap / 0.006)
        momentum_score = clamp(momentum / 0.012)
        reversion_score = clamp((50.0 - current_rsi) / 40.0)
        # Mean reversion is a veto-sized vote, not the primary direction engine.
        reversion_score *= 0.55

        votes = (
            Vote("Regime", trend_score, self._label(trend_score), f"8/21 EMA gap {ema_gap:+.2%}"),
            Vote("Momentum", momentum_score, self._label(momentum_score), f"12-bar return {momentum:+.2%}"),
            Vote("Breakout", breakout, self._label(breakout), f"20-bar channel location {breakout:+.2f}"),
            Vote("Reversion", reversion_score, self._label(reversion_score), f"RSI(14) {current_rsi:.1f}"),
        )
        score = (
            0.38 * trend_score
            + 0.30 * momentum_score
            + 0.22 * breakout
            + 0.10 * reversion_score
        )
        score = clamp(score)
        directional = [vote.score for vote in votes if abs(vote.score) >= 0.12]
        if score >= 0.24:
            direction = "bullish"
            agreement = sum(value > 0 for value in directional) / max(len(directional), 1)
        elif score <= -0.24:
            direction = "bearish"
            agreement = sum(value < 0 for value in directional) / max(len(directional), 1)
        else:
            direction = "neutral"
            agreement = 1.0 - abs(score)

        volatility_quality = 1.0 - clamp(abs(current_vol - 0.24) / 0.35, 0.0, 0.55)
        noise_penalty = clamp((atr_pct - 0.018) / 0.025, 0.0, 0.25)
        confidence = clamp(0.42 + abs(score) * 0.40 + agreement * 0.20 + volatility_quality * 0.08 - noise_penalty, 0.0, 0.96)
        summary = (
            f"{len([v for v in votes if v.label != 'flat'])}/4 specialists see a {direction} regime; "
            f"signal {score:+.2f}, agreement {agreement:.0%}, volatility {current_vol:.1%}."
        )
        return Thesis(
            symbol=symbol,
            direction=direction,
            score=round(score, 4),
            confidence=round(confidence, 4),
            agreement=round(agreement, 4),
            spot=round(spot, 4),
            realized_volatility=round(current_vol, 4),
            rsi=round(current_rsi, 2),
            votes=votes,
            summary=summary,
        )

    @staticmethod
    def _label(score: float) -> str:
        if score > 0.12:
            return "bullish"
        if score < -0.12:
            return "bearish"
        return "flat"


def parse_option_snapshot(symbol: str, snapshot: dict[str, Any]) -> ContractQuote | None:
    match = OCC_PATTERN.match(symbol)
    if not match:
        return None
    _, expiry_code, type_code, strike_code = match.groups()
    quote = snapshot.get("latestQuote") or snapshot.get("latest_quote") or {}
    greeks = snapshot.get("greeks") or {}
    try:
        expiration = datetime.strptime(expiry_code, "%y%m%d").date()
        strike = int(strike_code) / 1000.0
        bid = float(quote.get("bp", quote.get("bid_price", 0)) or 0)
        ask = float(quote.get("ap", quote.get("ask_price", 0)) or 0)
        delta_raw = greeks.get("delta")
        iv_raw = snapshot.get("impliedVolatility", snapshot.get("implied_volatility"))
        if bid < 0 or ask <= bid:
            return None
        return ContractQuote(
            symbol=symbol,
            expiration=expiration,
            option_type="call" if type_code == "C" else "put",
            strike=strike,
            bid=bid,
            ask=ask,
            delta=float(delta_raw) if delta_raw is not None else None,
            implied_volatility=float(iv_raw) if iv_raw is not None else None,
        )
    except (TypeError, ValueError):
        return None


class SpreadConstructor:
    """Selects liquid 7-21 DTE vertical debit spreads from Alpaca snapshots."""

    def __init__(self, min_dte: int = 7, max_dte: int = 21) -> None:
        self.min_dte = min_dte
        self.max_dte = max_dte

    def construct(
        self,
        thesis: Thesis,
        snapshots: dict[str, dict[str, Any]],
        today: date | None = None,
    ) -> SpreadPlan | None:
        if thesis.direction not in {"bullish", "bearish"}:
            return None
        today = today or date.today()
        desired_type = "call" if thesis.direction == "bullish" else "put"
        by_expiry: dict[date, list[ContractQuote]] = defaultdict(list)
        for symbol, snapshot in snapshots.items():
            contract = parse_option_snapshot(symbol, snapshot)
            if not contract or contract.option_type != desired_type:
                continue
            dte = (contract.expiration - today).days
            if self.min_dte <= dte <= self.max_dte and contract.spread_pct <= 0.55:
                by_expiry[contract.expiration].append(contract)
        if not by_expiry:
            return None

        expiration = min(by_expiry, key=lambda item: abs((item - today).days - 12))
        contracts = sorted(by_expiry[expiration], key=lambda item: item.strike)
        if len(contracts) < 2:
            return None

        if thesis.direction == "bullish":
            long_leg = self._nearest_delta_or_moneyness(contracts, 0.55, thesis.spot, 0.995)
            higher = [item for item in contracts if item.strike > long_leg.strike]
            if not higher:
                return None
            short_leg = self._nearest_delta_or_moneyness(higher, 0.30, thesis.spot, 1.025)
            width = short_leg.strike - long_leg.strike
            strategy = "bull call debit spread"
        else:
            long_leg = self._nearest_delta_or_moneyness(contracts, -0.55, thesis.spot, 1.005)
            lower = [item for item in contracts if item.strike < long_leg.strike]
            if not lower:
                return None
            short_leg = self._nearest_delta_or_moneyness(lower, -0.30, thesis.spot, 0.975)
            width = long_leg.strike - short_leg.strike
            strategy = "bear put debit spread"

        conservative_debit = round(long_leg.ask - short_leg.bid, 2)
        if conservative_debit <= 0 or conservative_debit >= width:
            return None
        max_loss = round(conservative_debit * 100.0, 2)
        max_profit = round((width - conservative_debit) * 100.0, 2)
        reward_risk = round(max_profit / max_loss, 2)
        liquidity = clamp(1.0 - (long_leg.spread_pct + short_leg.spread_pct) / 1.10, 0.0, 1.0)
        return SpreadPlan(
            underlying=thesis.symbol,
            direction=thesis.direction,
            strategy=strategy,
            expiration=expiration,
            long_leg=long_leg,
            short_leg=short_leg,
            limit_debit=conservative_debit,
            width=round(width, 2),
            max_loss_per_contract=max_loss,
            max_profit_per_contract=max_profit,
            reward_risk=reward_risk,
            liquidity_score=round(liquidity, 3),
        )

    @staticmethod
    def _nearest_delta_or_moneyness(
        contracts: list[ContractQuote], target_delta: float, spot: float, target_moneyness: float
    ) -> ContractQuote:
        with_delta = [item for item in contracts if item.delta is not None]
        if with_delta:
            return min(with_delta, key=lambda item: abs(float(item.delta) - target_delta))
        target_strike = spot * target_moneyness
        return min(contracts, key=lambda item: abs(item.strike - target_strike))


def build_mleg_order(plan: SpreadPlan, quantity: int, client_order_id: str) -> dict[str, Any]:
    """Build the official Alpaca MLeg order shape for a defined-risk debit spread."""
    return {
        "order_class": "mleg",
        "qty": str(quantity),
        "type": "limit",
        "limit_price": f"{plan.limit_debit:.2f}",
        "time_in_force": "day",
        "client_order_id": client_order_id[:128],
        "legs": [
            {
                "symbol": plan.long_leg.symbol,
                "ratio_qty": "1",
                "side": "buy",
                "position_intent": "buy_to_open",
            },
            {
                "symbol": plan.short_leg.symbol,
                "ratio_qty": "1",
                "side": "sell",
                "position_intent": "sell_to_open",
            },
        ],
    }

