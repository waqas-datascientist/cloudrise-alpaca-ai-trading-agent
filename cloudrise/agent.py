from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .alpaca_cli import AlpacaCLI, AlpacaCLIError, cli_preflight
from .alpaca_data import AlpacaDataClient, AlpacaDataError
from .config import Settings
from .demo import demo_dashboard
from .ledger import DecisionLedger
from .positions import (
    build_exit_mleg_order,
    exit_reason,
    group_option_positions,
    is_closing_order,
    order_underlyings,
)
from .risk import RiskGovernor
from .strategy import ResearchCommittee, SpreadConstructor, build_mleg_order


class CloudRiseAgent:
    def __init__(self, settings: Settings, runtime_dir: Path) -> None:
        self.settings = settings
        self.cli = AlpacaCLI(settings.api_key, settings.secret_key)
        self.data = AlpacaDataClient(settings)
        self.committee = ResearchCommittee()
        self.constructor = SpreadConstructor(settings.min_dte, settings.max_dte)
        self.governor = RiskGovernor(settings)
        self.ledger = DecisionLedger(runtime_dir / "decision-ledger.jsonl")

    def preflight(self) -> dict[str, Any]:
        if self.settings.execution_mode == "demo":
            return {
                "ready": True,
                "mode": "demo",
                "checks": [
                    {"name": "Demo replay", "passed": True, "detail": "no credentials or credits required"},
                    {"name": "Order transmission", "passed": True, "detail": "disabled"},
                    {"name": "Paper-only invariant", "passed": True, "detail": "enforced in code"},
                ],
            }
        checks = [
            {
                "name": "API credentials",
                "passed": self.settings.has_credentials,
                "detail": "present in environment" if self.settings.has_credentials else "missing",
            },
            {"name": "Paper endpoint", "passed": self.settings.trading_base_url.startswith("https://paper-api."), "detail": self.settings.trading_base_url},
        ]
        cli_report = cli_preflight(self.cli, require_account=self.settings.has_credentials)
        checks.extend(cli_report["checks"])
        checks.append(
            {
                "name": "$100k fresh competition account",
                "passed": True,
                "detail": "manual submission check — verify in Alpaca dashboard",
            }
        )
        return {"ready": all(item["passed"] for item in checks), "mode": "paper", "checks": checks}

    def run_cycle(self) -> dict[str, Any]:
        if self.settings.execution_mode == "demo":
            record = self.ledger.append("demo_cycle", {"transmitted": False, "result": "previewed"})
            result = demo_dashboard()
            result["cycle_record"] = record
            return result

        report = self.preflight()
        if not report["ready"]:
            return {"status": "blocked", "reason": "Preflight failed", "preflight": report}

        try:
            account_result = self.cli.account()
            clock_result = self.cli.clock()
            positions_result = self.cli.positions()
            orders_result = self.cli.orders()
            account = account_result.data if isinstance(account_result.data, dict) else {}
            clock = clock_result.data if isinstance(clock_result.data, dict) else {}
            positions = positions_result.data if isinstance(positions_result.data, list) else []
            orders = orders_result.data if isinstance(orders_result.data, list) else []
            self.ledger.append(
                "cli_sync",
                {"commands": [account_result.command, clock_result.command, positions_result.command, orders_result.command]},
            )

            position_groups = group_option_positions(positions)
            open_orders = [
                item
                for item in orders
                if str(item.get("status", "")).lower()
                in {"new", "accepted", "pending_new", "partially_filled", "pending_replace"}
            ]
            pending_closing_orders = [item for item in open_orders if is_closing_order(item)]
            pending_exit_underlyings = {
                underlying
                for item in pending_closing_orders
                for underlying in order_underlyings(item)
            }
            if bool(clock.get("is_open", False)):
                for group in position_groups:
                    if group["underlying"] in pending_exit_underlyings:
                        record = self.ledger.append(
                            "exit_pending",
                            {
                                "underlying": group["underlying"],
                                "detail": "existing closing MLeg is still open; no new risk considered",
                            },
                        )
                        return {
                            "status": "exit_pending",
                            "paper_only": True,
                            "underlying": group["underlying"],
                            "reason": "Existing closing MLeg is still open",
                            "ledger": record,
                        }
                    reason = exit_reason(group)
                    if not reason:
                        continue
                    exit_id = f"cloudrise-exit-{datetime.now(timezone.utc):%Y%m%d%H%M%S}-{group['underlying'].lower()}"
                    exit_payload = build_exit_mleg_order(group, exit_id)
                    exit_result = self.cli.submit_mleg(exit_payload)
                    record = self.ledger.append(
                        "exit_submitted",
                        {
                            "underlying": group["underlying"],
                            "reason": reason,
                            "return_on_risk": round(float(group["return_on_risk"]), 4),
                            "order": exit_payload,
                            "response": exit_result.data,
                            "command": exit_result.command,
                        },
                    )
                    return {
                        "status": "exit_submitted",
                        "paper_only": True,
                        "underlying": group["underlying"],
                        "reason": reason,
                        "order": exit_result.data,
                        "ledger": record,
                    }

            theses = []
            for symbol in self.settings.universe:
                bars = self.data.bars(symbol)
                if len(bars) >= 40:
                    thesis = self.committee.analyze(symbol, bars)
                    theses.append(thesis)
                    self.ledger.append("thesis", thesis.to_dict())
            directional = [item for item in theses if item.direction != "neutral"]
            if not directional:
                return self._no_trade("No candidate achieved directional consensus", theses)
            best = max(directional, key=lambda item: (item.confidence, abs(item.score)))
            snapshots = self.data.option_chain(best.symbol, best.spot)
            plan = self.constructor.construct(best, snapshots)
            if plan is None:
                return self._no_trade("No liquid 7–21 DTE defined-risk spread passed construction", theses)

            equity = float(account.get("equity", account.get("portfolio_value", 0)) or 0)
            last_equity = float(account.get("last_equity", equity) or equity)
            pending_entry_orders = [
                item
                for item in open_orders
                if str(item.get("order_class", "")).lower() == "mleg" and not is_closing_order(item)
            ]
            open_spreads = len(position_groups) + len(pending_entry_orders)
            current_risk = open_spreads * equity * self.settings.max_risk_per_trade_pct
            active_underlyings = {str(group["underlying"]) for group in position_groups}
            active_underlyings.update(
                underlying
                for item in pending_entry_orders
                for underlying in order_underlyings(item)
            )
            risk = self.governor.evaluate(
                best,
                plan,
                equity=equity,
                last_equity=last_equity,
                current_defined_risk=current_risk,
                open_spreads=open_spreads,
                market_open=bool(clock.get("is_open", False)),
                duplicate_underlying=best.symbol in active_underlyings,
            )
            self.ledger.append("risk_decision", {"thesis": best.to_dict(), "plan": plan.to_dict(), "risk": risk.to_dict()})
            if not risk.approved:
                return {"status": "blocked", "reason": risk.reason, "theses": [item.to_dict() for item in theses], "plan": plan.to_dict(), "risk": risk.to_dict()}

            client_order_id = f"cloudrise-{datetime.now(timezone.utc):%Y%m%d%H%M%S}-{best.symbol.lower()}"
            payload = build_mleg_order(plan, risk.quantity, client_order_id)
            order_result = self.cli.submit_mleg(payload)
            # Store only the non-secret order payload and Alpaca response.
            record = self.ledger.append("order_submitted", {"order": payload, "response": order_result.data, "command": order_result.command})
            return {
                "status": "submitted",
                "paper_only": True,
                "thesis": best.to_dict(),
                "plan": plan.to_dict(),
                "risk": risk.to_dict(),
                "order": order_result.data,
                "ledger": record,
            }
        except (AlpacaCLIError, AlpacaDataError, ValueError) as exc:
            record = self.ledger.append("cycle_error", {"type": type(exc).__name__, "message": str(exc)[:500]})
            return {"status": "error", "reason": str(exc), "ledger": record}

    def _no_trade(self, reason: str, theses: list[Any]) -> dict[str, Any]:
        record = self.ledger.append("no_trade", {"reason": reason})
        return {"status": "no_trade", "reason": reason, "theses": [item.to_dict() for item in theses], "ledger": record}
