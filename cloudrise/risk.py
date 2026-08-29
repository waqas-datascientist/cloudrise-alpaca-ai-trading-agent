from __future__ import annotations

from typing import Any

from .config import Settings
from .models import RiskDecision, SpreadPlan, Thesis


class RiskGovernor:
    """Non-bypassable portfolio and trade-level risk gates."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def evaluate(
        self,
        thesis: Thesis,
        plan: SpreadPlan,
        *,
        equity: float,
        last_equity: float,
        current_defined_risk: float,
        open_spreads: int,
        market_open: bool,
        duplicate_underlying: bool = False,
    ) -> RiskDecision:
        daily_return = (equity - last_equity) / max(last_equity, 1.0)
        per_trade_budget = equity * self.settings.max_risk_per_trade_pct
        portfolio_budget = equity * self.settings.max_portfolio_risk_pct
        quantity = max(0, int(per_trade_budget // max(plan.max_loss_per_contract, 0.01)))
        quantity = min(quantity, 3)
        proposed_risk = quantity * plan.max_loss_per_contract

        raw_gates: list[tuple[str, bool, str]] = [
            ("Paper only", self.settings.execution_mode in {"demo", "paper"}, self.settings.execution_mode.upper()),
            ("Market open", market_open, "regular session" if market_open else "orders paused"),
            (
                "Daily loss limit",
                daily_return > -self.settings.max_daily_loss_pct,
                f"{daily_return:+.2%} / -{self.settings.max_daily_loss_pct:.2%}",
            ),
            (
                "Committee confidence",
                thesis.confidence >= self.settings.min_confidence,
                f"{thesis.confidence:.0%} / {self.settings.min_confidence:.0%}",
            ),
            ("Directional consensus", thesis.direction != "neutral" and thesis.agreement >= 0.60, f"{thesis.agreement:.0%}"),
            ("Defined-risk sizing", quantity >= 1, f"${proposed_risk:,.0f} proposed"),
            (
                "Portfolio risk",
                current_defined_risk + proposed_risk <= portfolio_budget,
                f"${current_defined_risk + proposed_risk:,.0f} / ${portfolio_budget:,.0f}",
            ),
            ("Position slots", open_spreads < self.settings.max_open_spreads, f"{open_spreads}/{self.settings.max_open_spreads}"),
            ("No duplicate", not duplicate_underlying, thesis.symbol),
            ("Liquidity", plan.liquidity_score >= 0.35, f"{plan.liquidity_score:.0%}"),
            ("Reward / risk", plan.reward_risk >= 0.60, f"{plan.reward_risk:.2f}x"),
        ]
        gates: tuple[dict[str, Any], ...] = tuple(
            {"name": name, "passed": passed, "detail": detail} for name, passed, detail in raw_gates
        )
        failed = [gate[0] for gate in raw_gates if not gate[1]]
        approved = not failed
        return RiskDecision(
            approved=approved,
            quantity=quantity if approved else 0,
            risk_dollars=round(proposed_risk if approved else 0.0, 2),
            portfolio_risk_after=round(current_defined_risk + (proposed_risk if approved else 0.0), 2),
            gates=gates,
            reason="All risk gates passed" if approved else "Blocked: " + ", ".join(failed),
        )

