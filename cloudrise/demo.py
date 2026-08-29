from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta, timezone
from typing import Any


EQUITY_VALUES = [
    100000, 100040, 99970, 100120, 100210, 100180, 100360, 100520, 100455, 100710,
    100830, 100760, 100940, 101080, 101025, 101240, 101410, 101335, 101590, 101720,
    101655, 101842,
]


def demo_dashboard(step: int | None = None) -> dict[str, Any]:
    """A clearly labeled deterministic replay for demos without credentials."""
    step = len(EQUITY_VALUES) - 1 if step is None else max(4, min(step, len(EQUITY_VALUES) - 1))
    start = datetime(2026, 8, 28, 13, 30, tzinfo=timezone.utc)
    equity = [
        {"time": (start + timedelta(minutes=15 * index)).isoformat(), "value": value}
        for index, value in enumerate(EQUITY_VALUES[: step + 1])
    ]
    current = EQUITY_VALUES[step]
    previous = EQUITY_VALUES[max(0, step - 7)]
    dashboard = {
        "mode": "demo",
        "mode_label": "DEMO REPLAY · PAPER ONLY",
        "as_of": equity[-1]["time"],
        "market": {"is_open": True, "next_event": "Close in 2h 18m", "feed": "Alpaca indicative"},
        "account": {
            "equity": current,
            "starting_equity": 100000,
            "day_pnl": current - previous,
            "day_return": (current - previous) / previous,
            "total_return": (current / 100000) - 1,
            "buying_power": 94160,
            "account_id": "PAPER-•••-7K2Q",
        },
        "equity_curve": equity,
        "risk": {
            "used": 1180,
            "budget": 2500,
            "daily_loss_limit": 1500,
            "open_spreads": 2,
            "max_spreads": 3,
            "gates": [
                {"name": "Paper environment", "passed": True, "detail": "locked"},
                {"name": "Daily loss circuit", "passed": True, "detail": "+1.07% today"},
                {"name": "Portfolio risk", "passed": True, "detail": "$1,180 / $2,500"},
                {"name": "Position slots", "passed": True, "detail": "2 / 3"},
                {"name": "Data freshness", "passed": True, "detail": "8s ago"},
            ],
        },
        "candidates": [
            {
                "symbol": "SPY", "direction": "bullish", "score": 0.71, "confidence": 0.84,
                "agreement": 0.75, "spot": 648.42, "rsi": 61.8, "volatility": 0.184,
                "summary": "Trend, momentum and breakout agents agree; reversion remains neutral.",
                "votes": [
                    {"agent": "Regime", "score": 0.82, "label": "bullish"},
                    {"agent": "Momentum", "score": 0.73, "label": "bullish"},
                    {"agent": "Breakout", "score": 0.67, "label": "bullish"},
                    {"agent": "Reversion", "score": -0.08, "label": "flat"},
                ],
            },
            {
                "symbol": "QQQ", "direction": "neutral", "score": 0.16, "confidence": 0.55,
                "agreement": 0.52, "spot": 584.16, "rsi": 54.2, "volatility": 0.231,
                "summary": "Momentum is positive, but the breakout agent has not confirmed.",
                "votes": [],
            },
            {
                "symbol": "IWM", "direction": "bearish", "score": -0.46, "confidence": 0.69,
                "agreement": 0.75, "spot": 238.31, "rsi": 41.7, "volatility": 0.276,
                "summary": "Bearish structure passes consensus; liquidity ranks below SPY.",
                "votes": [],
            },
        ],
        "positions": [
            {
                "symbol": "SPY", "strategy": "647/652 call debit spread", "expiry": "Sep 11",
                "direction": "BULL", "qty": 2, "entry": 1.84, "mark": 2.31, "pnl": 94,
                "pnl_pct": 25.5, "max_risk": 368, "status": "MANAGE",
            },
            {
                "symbol": "IWM", "strategy": "240/235 put debit spread", "expiry": "Sep 11",
                "direction": "BEAR", "qty": 2, "entry": 2.08, "mark": 2.37, "pnl": 58,
                "pnl_pct": 13.9, "max_risk": 416, "status": "HOLD",
            },
        ],
        "ledger": [
            {
                "time": "15:42:08", "event": "RISK APPROVED", "symbol": "SPY",
                "title": "2× SPY 647/652 call spread",
                "detail": "Max loss $368 · reward/risk 1.72× · 11 DTE · all 11 gates passed",
                "tone": "positive",
            },
            {
                "time": "15:41:52", "event": "THESIS FORMED", "symbol": "SPY",
                "title": "Bullish consensus reached at 84% confidence",
                "detail": "Regime +0.82 · momentum +0.73 · breakout +0.67 · RSI veto clear",
                "tone": "info",
            },
            {
                "time": "15:41:26", "event": "CANDIDATE REJECTED", "symbol": "QQQ",
                "title": "No trade: committee confidence below threshold",
                "detail": "55% confidence did not clear the 62% gate; capital preserved",
                "tone": "muted",
            },
            {
                "time": "15:41:03", "event": "CLI SYNC", "symbol": "ALPACA",
                "title": "Account, clock, positions and orders reconciled",
                "detail": "Official Alpaca CLI · structured JSON · paper profile",
                "tone": "info",
            },
        ],
        "agent_stages": [
            {"name": "Observe", "detail": "3 indices · 15m bars", "status": "done"},
            {"name": "Debate", "detail": "4 specialist votes", "status": "done"},
            {"name": "Govern", "detail": "11 hard risk gates", "status": "done"},
            {"name": "Execute", "detail": "Atomic MLeg limit", "status": "active"},
        ],
        "last_action": {
            "status": "approved",
            "title": "SPY bullish spread is the top-ranked opportunity",
            "detail": "A defined-risk MLeg order was previewed at a $1.84 debit. Demo mode never transmits orders.",
        },
    }
    return deepcopy(dashboard)

