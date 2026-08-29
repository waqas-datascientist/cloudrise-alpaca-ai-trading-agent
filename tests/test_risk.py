from __future__ import annotations

import unittest
from datetime import date

from cloudrise.config import Settings
from cloudrise.models import ContractQuote, RiskDecision, SpreadPlan, Thesis
from cloudrise.risk import RiskGovernor


def fixtures() -> tuple[Thesis, SpreadPlan]:
    thesis = Thesis("SPY", "bullish", 0.7, 0.84, 0.75, 650, 0.22, 61)
    long_leg = ContractQuote("SPY260911C00650000", date(2026, 9, 11), "call", 650, 6.1, 6.25, 0.54)
    short_leg = ContractQuote("SPY260911C00655000", date(2026, 9, 11), "call", 655, 3.5, 3.65, 0.31)
    plan = SpreadPlan("SPY", "bullish", "bull call debit spread", date(2026, 9, 11), long_leg, short_leg, 2.75, 5, 275, 225, 0.82, 0.78)
    return thesis, plan


class RiskTests(unittest.TestCase):
    def test_approves_sized_defined_risk_trade(self) -> None:
        thesis, plan = fixtures()
        result = RiskGovernor(Settings()).evaluate(thesis, plan, equity=100000, last_equity=99800, current_defined_risk=400, open_spreads=1, market_open=True)
        self.assertTrue(result.approved)
        self.assertEqual(2, result.quantity)
        self.assertEqual(550, result.risk_dollars)

    def test_daily_loss_circuit_is_non_bypassable(self) -> None:
        thesis, plan = fixtures()
        result = RiskGovernor(Settings()).evaluate(thesis, plan, equity=98000, last_equity=100000, current_defined_risk=0, open_spreads=0, market_open=True)
        self.assertFalse(result.approved)
        self.assertIn("Daily loss limit", result.reason)
        self.assertEqual(0, result.quantity)

    def test_market_closed_blocks_order(self) -> None:
        thesis, plan = fixtures()
        result = RiskGovernor(Settings()).evaluate(thesis, plan, equity=100000, last_equity=100000, current_defined_risk=0, open_spreads=0, market_open=False)
        self.assertFalse(result.approved)
        self.assertIn("Market open", result.reason)


if __name__ == "__main__":
    unittest.main()

