from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta, timezone
from typing import Any

from .config import Settings
from .models import Bar


class AlpacaDataError(RuntimeError):
    pass


class AlpacaDataClient:
    """Dependency-free client for Alpaca market data; trading stays in the CLI."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def _get(self, path: str, params: dict[str, Any]) -> dict[str, Any]:
        if not self.settings.has_credentials:
            raise AlpacaDataError("ALPACA_API_KEY and ALPACA_SECRET_KEY are required in paper mode")
        query = urllib.parse.urlencode({key: value for key, value in params.items() if value is not None})
        request = urllib.request.Request(
            f"{self.settings.data_base_url}{path}?{query}",
            headers={
                "APCA-API-KEY-ID": self.settings.api_key,
                "APCA-API-SECRET-KEY": self.settings.secret_key,
                "Accept": "application/json",
                "User-Agent": "CloudRise/1.0",
            },
        )
        for attempt in range(3):
            try:
                with urllib.request.urlopen(request, timeout=20) as response:
                    return json.loads(response.read().decode("utf-8"))
            except urllib.error.HTTPError as exc:
                safe_message = exc.read().decode("utf-8", errors="replace")[:500]
                if exc.code == 429 or exc.code >= 500:
                    time.sleep(0.5 * (2**attempt))
                    continue
                raise AlpacaDataError(f"Alpaca data request failed ({exc.code}): {safe_message}") from exc
            except (urllib.error.URLError, TimeoutError) as exc:
                if attempt == 2:
                    raise AlpacaDataError(f"Alpaca data request unavailable: {exc.reason if hasattr(exc, 'reason') else exc}") from exc
                time.sleep(0.5 * (2**attempt))
        raise AlpacaDataError("Alpaca data request failed after retries")

    def bars(self, symbol: str) -> list[Bar]:
        start = datetime.now(timezone.utc) - timedelta(days=12)
        payload = self._get(
            f"/v2/stocks/{urllib.parse.quote(symbol)}/bars",
            {
                "timeframe": "15Min",
                "start": start.isoformat().replace("+00:00", "Z"),
                "limit": 500,
                "adjustment": "all",
                "feed": "iex",
                "sort": "asc",
            },
        )
        result: list[Bar] = []
        for item in payload.get("bars", []):
            try:
                result.append(
                    Bar(
                        timestamp=datetime.fromisoformat(str(item["t"]).replace("Z", "+00:00")),
                        open=float(item["o"]),
                        high=float(item["h"]),
                        low=float(item["l"]),
                        close=float(item["c"]),
                        volume=float(item["v"]),
                    )
                )
            except (KeyError, TypeError, ValueError):
                continue
        return result

    def option_chain(self, symbol: str, spot: float) -> dict[str, dict[str, Any]]:
        today = date.today()
        payload = self._get(
            f"/v1beta1/options/snapshots/{urllib.parse.quote(symbol)}",
            {
                "feed": "indicative",
                "limit": 1000,
                "expiration_date_gte": (today + timedelta(days=self.settings.min_dte)).isoformat(),
                "expiration_date_lte": (today + timedelta(days=self.settings.max_dte)).isoformat(),
                "strike_price_gte": round(spot * 0.90, 2),
                "strike_price_lte": round(spot * 1.10, 2),
            },
        )
        snapshots = payload.get("snapshots", {})
        return snapshots if isinstance(snapshots, dict) else {}

