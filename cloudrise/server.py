from __future__ import annotations

import json
import mimetypes
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from .agent import CloudRiseAgent
from .config import Settings
from .demo import demo_dashboard


PROJECT_ROOT = Path(__file__).resolve().parent.parent
WEB_ROOT = PROJECT_ROOT / "web"
RUNTIME_ROOT = PROJECT_ROOT / "runtime"


def paper_dashboard(agent: CloudRiseAgent) -> dict[str, Any]:
    """Use the complete demo-shaped view, then replace verified account fields."""
    dashboard = demo_dashboard()
    dashboard["mode"] = "paper"
    dashboard["mode_label"] = "ALPACA PAPER · AUTONOMOUS"
    dashboard["ledger"] = [
        {
            "time": str(item.get("timestamp", ""))[11:19],
            "event": str(item.get("event", "")).replace("_", " ").upper(),
            "symbol": str(item.get("payload", {}).get("symbol", "AGENT")),
            "title": str(item.get("payload", {}).get("reason", item.get("event", "Agent event"))),
            "detail": json.dumps(item.get("payload", {}), default=str)[:180],
            "tone": "info",
        }
        for item in reversed(agent.ledger.recent(12))
    ] or dashboard["ledger"]
    try:
        account = agent.cli.account().data
        clock = agent.cli.clock().data
        if isinstance(account, dict):
            equity = float(account.get("equity", account.get("portfolio_value", 100000)) or 100000)
            last_equity = float(account.get("last_equity", equity) or equity)
            dashboard["account"].update(
                {
                    "equity": equity,
                    "day_pnl": equity - last_equity,
                    "day_return": (equity - last_equity) / max(last_equity, 1),
                    "total_return": equity / 100000 - 1,
                    "buying_power": float(account.get("buying_power", 0) or 0),
                    "account_id": str(account.get("id", "PAPER"))[-10:],
                }
            )
        if isinstance(clock, dict):
            dashboard["market"]["is_open"] = bool(clock.get("is_open", False))
            dashboard["market"]["next_event"] = "Market open" if clock.get("is_open") else "Market closed · agent paused"
    except Exception as exc:  # Dashboard must stay up even if the broker is temporarily unavailable.
        dashboard["mode_label"] = "PAPER · CONNECTION NEEDS ATTENTION"
        dashboard["last_action"] = {"status": "blocked", "title": "Broker sync unavailable", "detail": str(exc)[:240]}
    return dashboard


def make_handler(agent: CloudRiseAgent) -> type[BaseHTTPRequestHandler]:
    class CloudRiseHandler(BaseHTTPRequestHandler):
        server_version = "CloudRise/1.0"

        def log_message(self, format: str, *args: Any) -> None:
            # Keep ordinary dashboard refreshes quiet; errors still return JSON.
            return

        def _json(self, payload: Any, status: HTTPStatus = HTTPStatus.OK) -> None:
            data = json.dumps(payload, default=str).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy", "default-src 'self'; style-src 'self'; script-src 'self'; img-src 'self' data:; connect-src 'self'")
            self.end_headers()
            self.wfile.write(data)

        def _static(self, request_path: str) -> None:
            relative = "index.html" if request_path in {"", "/"} else request_path.lstrip("/")
            candidate = (WEB_ROOT / relative).resolve()
            if WEB_ROOT.resolve() not in candidate.parents and candidate != WEB_ROOT.resolve():
                self._json({"error": "not found"}, HTTPStatus.NOT_FOUND)
                return
            if not candidate.is_file():
                self._json({"error": "not found"}, HTTPStatus.NOT_FOUND)
                return
            data = candidate.read_bytes()
            content_type = mimetypes.guess_type(candidate.name)[0] or "application/octet-stream"
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", content_type + ("; charset=utf-8" if content_type.startswith(("text/", "application/javascript")) else ""))
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-cache")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self) -> None:
            path = urlparse(self.path).path
            if path == "/health":
                self._json({"status": "ok", "service": "cloudrise", "mode": agent.settings.execution_mode})
            elif path == "/api/dashboard":
                self._json(demo_dashboard() if agent.settings.execution_mode == "demo" else paper_dashboard(agent))
            elif path == "/api/preflight":
                self._json(agent.preflight())
            elif path.startswith("/api/"):
                self._json({"error": "not found"}, HTTPStatus.NOT_FOUND)
            else:
                self._static(path)

        def do_POST(self) -> None:
            path = urlparse(self.path).path
            content_length = int(self.headers.get("Content-Length", "0") or 0)
            if content_length > 4096:
                self._json({"error": "request too large"}, HTTPStatus.REQUEST_ENTITY_TOO_LARGE)
                return
            if content_length:
                self.rfile.read(content_length)
            if path == "/api/cycle":
                self._json(agent.run_cycle())
            else:
                self._json({"error": "not found"}, HTTPStatus.NOT_FOUND)

    return CloudRiseHandler


def serve(settings: Settings, host: str = "127.0.0.1", port: int = 8787) -> None:
    if host not in {"127.0.0.1", "localhost"} and settings.execution_mode != "demo":
        raise ValueError("Public binding is allowed only in zero-credential demo mode")
    agent = CloudRiseAgent(settings, RUNTIME_ROOT)
    server = ThreadingHTTPServer((host, port), make_handler(agent))
    print(f"CloudRise ready at http://{host}:{port} · {settings.execution_mode.upper()} mode · paper only")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
