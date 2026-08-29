from __future__ import annotations

import re
from collections import defaultdict
from datetime import date, datetime
from typing import Any


OCC_POSITION = re.compile(r"^([A-Z]{1,6})(\d{6})([CP])(\d{8})$")


def option_underlying(symbol: str) -> str | None:
    match = OCC_POSITION.match(str(symbol).upper())
    return match.group(1) if match else None


def order_underlyings(order: dict[str, Any]) -> set[str]:
    """Extract option roots from a nested MLeg order without trusting its label."""
    roots = {
        root
        for leg in order.get("legs", []) or []
        if isinstance(leg, dict)
        for root in [option_underlying(str(leg.get("symbol", "")))]
        if root
    }
    if roots:
        return roots
    client_order_id = str(order.get("client_order_id", "")).lower()
    match = re.match(r"^cloudrise-(?:exit-)?\d{14}-([a-z]{1,6})$", client_order_id)
    return {match.group(1).upper()} if match else set()


def is_closing_order(order: dict[str, Any]) -> bool:
    client_order_id = str(order.get("client_order_id", "")).lower()
    if client_order_id.startswith("cloudrise-exit-"):
        return True
    return any(
        str(leg.get("position_intent", "")).lower().endswith("_to_close")
        for leg in order.get("legs", []) or []
        if isinstance(leg, dict)
    )


def group_option_positions(positions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Group the legs of each active vertical by underlying and expiration."""
    groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for position in positions:
        symbol = str(position.get("symbol", "")).upper()
        match = OCC_POSITION.match(symbol)
        if not match:
            continue
        root, expiry_code, _, _ = match.groups()
        groups[(root, expiry_code)].append(position)

    result = []
    for (root, expiry_code), legs in groups.items():
        if len(legs) < 2 or len(legs) > 4:
            continue
        expiration = datetime.strptime(expiry_code, "%y%m%d").date()
        cost_basis = sum(float(leg.get("cost_basis", 0) or 0) for leg in legs)
        unrealized_pl = sum(float(leg.get("unrealized_pl", 0) or 0) for leg in legs)
        result.append(
            {
                "underlying": root,
                "expiration": expiration,
                "legs": legs,
                "net_cost_basis": cost_basis,
                "unrealized_pl": unrealized_pl,
                "return_on_risk": unrealized_pl / max(abs(cost_basis), 100.0),
            }
        )
    return result


def exit_reason(group: dict[str, Any], today: date | None = None) -> str | None:
    today = today or date.today()
    dte = (group["expiration"] - today).days
    return_on_risk = float(group.get("return_on_risk", 0) or 0)
    if dte <= 3:
        return "expiry window ≤3 DTE"
    if return_on_risk >= 0.35:
        return "profit target ≥35% of defined risk"
    if return_on_risk <= -0.45:
        return "loss limit ≤−45% of defined risk"
    return None


def build_exit_mleg_order(group: dict[str, Any], client_order_id: str) -> dict[str, Any]:
    quantities = [abs(float(leg.get("qty", 0) or 0)) for leg in group["legs"]]
    quantity = int(min(quantities)) if quantities else 0
    if quantity < 1:
        raise ValueError("Cannot close an option group with zero quantity")
    legs = []
    for position in group["legs"]:
        signed_quantity = float(position.get("qty", 0) or 0)
        if signed_quantity > 0:
            side, intent = "sell", "sell_to_close"
        elif signed_quantity < 0:
            side, intent = "buy", "buy_to_close"
        else:
            raise ValueError("Cannot close a zero-quantity leg")
        legs.append(
            {
                "symbol": str(position["symbol"]),
                "ratio_qty": str(max(1, int(abs(signed_quantity) / quantity))),
                "side": side,
                "position_intent": intent,
            }
        )
    return {
        "order_class": "mleg",
        "qty": str(quantity),
        "type": "market",
        "time_in_force": "day",
        "client_order_id": client_order_id[:128],
        "legs": legs,
    }
