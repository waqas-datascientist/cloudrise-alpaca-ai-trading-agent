from __future__ import annotations

import unittest
from datetime import date, datetime, timedelta, timezone

from cloudrise.models import Bar
from cloudrise.strategy import ResearchCommittee, SpreadConstructor, build_mleg_order


def trending_bars(up: bool = True) -> list[Bar]:
    start = datetime(2026, 8, 20, 13, 30, tzinfo=timezone.utc)
    bars = []
    for index in range(80):
        drift = index * (0.42 if up else -0.42)
        wave = (index % 5 - 2) * 0.06
        close = 620 + drift + wave
        bars.append(Bar(start + timedelta(minutes=15 * index), close - 0.2, close + 0.6, close - 0.7, close, 1_000_000 + index))
    return bars


def snapshot(bid: float, ask: float, delta: float) -> dict:
    return {"latestQuote": {"bp": bid, "ap": ask}, "greeks": {"delta": delta}, "impliedVolatility": 0.22}


class StrategyTests(unittest.TestCase):
    def test_committee_detects_bullish_and_bearish_regimes(self) -> None:
        committee = ResearchCommittee()
        bullish = committee.analyze("SPY", trending_bars(True))
        bearish = committee.analyze("SPY", trending_bars(False))
        self.assertEqual("bullish", bullish.direction)
        self.assertEqual("bearish", bearish.direction)
        self.assertGreater(bullish.confidence, 0.62)
        self.assertGreater(bearish.confidence, 0.62)

    def test_constructs_atomic_bull_call_spread(self) -> None:
        thesis = ResearchCommittee().analyze("SPY", trending_bars(True))
        snapshots = {
            "SPY260911C00645000": snapshot(9.20, 9.35, 0.62),
            "SPY260911C00650000": snapshot(6.10, 6.25, 0.54),
            "SPY260911C00655000": snapshot(3.50, 3.65, 0.31),
            "SPY260911C00660000": snapshot(1.80, 1.95, 0.19),
        }
        plan = SpreadConstructor(7, 21).construct(thesis, snapshots, today=date(2026, 8, 28))
        self.assertIsNotNone(plan)
        assert plan is not None
        self.assertLess(plan.long_leg.strike, plan.short_leg.strike)
        self.assertGreater(plan.max_loss_per_contract, 0)
        payload = build_mleg_order(plan, 2, "cloudrise-test")
        self.assertEqual("mleg", payload["order_class"])
        self.assertEqual("2", payload["qty"])
        self.assertEqual("buy_to_open", payload["legs"][0]["position_intent"])
        self.assertEqual("sell_to_open", payload["legs"][1]["position_intent"])


if __name__ == "__main__":
    unittest.main()

