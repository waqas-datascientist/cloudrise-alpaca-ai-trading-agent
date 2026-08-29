from __future__ import annotations

import unittest
from datetime import date

from cloudrise.positions import (
    build_exit_mleg_order,
    exit_reason,
    group_option_positions,
    is_closing_order,
    order_underlyings,
)


class PositionManagementTests(unittest.TestCase):
    def setUp(self) -> None:
        self.positions = [
            {"symbol": "SPY260911C00650000", "qty": "2", "cost_basis": "600", "unrealized_pl": "180"},
            {"symbol": "SPY260911C00655000", "qty": "-2", "cost_basis": "-200", "unrealized_pl": "-20"},
        ]

    def test_groups_vertical_and_triggers_profit_target(self) -> None:
        groups = group_option_positions(self.positions)
        self.assertEqual(1, len(groups))
        self.assertEqual("SPY", groups[0]["underlying"])
        self.assertEqual(0.40, groups[0]["return_on_risk"])
        self.assertIn("profit target", exit_reason(groups[0], today=date(2026, 8, 29)))

    def test_builds_atomic_closing_order(self) -> None:
        group = group_option_positions(self.positions)[0]
        payload = build_exit_mleg_order(group, "cloudrise-exit-test")
        self.assertEqual("mleg", payload["order_class"])
        self.assertEqual("market", payload["type"])
        self.assertEqual("2", payload["qty"])
        self.assertEqual("sell_to_close", payload["legs"][0]["position_intent"])
        self.assertEqual("buy_to_close", payload["legs"][1]["position_intent"])

    def test_near_expiry_exit_precedes_profit_logic(self) -> None:
        group = group_option_positions(self.positions)[0]
        self.assertIn("expiry", exit_reason(group, today=date(2026, 9, 9)))

    def test_detects_pending_exit_and_its_underlying(self) -> None:
        order = {
            "order_class": "mleg",
            "client_order_id": "cloudrise-exit-20260829153000-spy",
            "legs": [
                {"symbol": "SPY260911C00650000", "position_intent": "sell_to_close"},
                {"symbol": "SPY260911C00655000", "position_intent": "buy_to_close"},
            ],
        }
        self.assertTrue(is_closing_order(order))
        self.assertEqual({"SPY"}, order_underlyings(order))

    def test_client_id_fallback_preserves_idempotency(self) -> None:
        order = {"client_order_id": "cloudrise-exit-20260829153000-qqq", "legs": []}
        self.assertEqual({"QQQ"}, order_underlyings(order))


if __name__ == "__main__":
    unittest.main()
