from __future__ import annotations

import json
import os
import shutil
import subprocess
from dataclasses import dataclass
from typing import Any


class AlpacaCLIError(RuntimeError):
    pass


@dataclass(frozen=True)
class CLIResult:
    data: Any
    command: str


class AlpacaCLI:
    """Thin adapter around Alpaca's official agent-oriented CLI.

    It never invokes a shell, never writes credentials to disk, and forces
    paper mode in the child process regardless of the user's global profile.
    """

    def __init__(self, api_key: str = "", secret_key: str = "") -> None:
        self.api_key = api_key
        self.secret_key = secret_key

    @staticmethod
    def available() -> bool:
        return shutil.which("alpaca") is not None

    def _environment(self) -> dict[str, str]:
        environment = os.environ.copy()
        environment["ALPACA_LIVE_TRADE"] = "false"
        environment["ALPACA_OUTPUT"] = "json"
        if self.api_key and self.secret_key:
            environment["ALPACA_API_KEY"] = self.api_key
            environment["ALPACA_SECRET_KEY"] = self.secret_key
        return environment

    def run(self, arguments: list[str], payload: dict[str, Any] | None = None, timeout: int = 35) -> CLIResult:
        if not self.available():
            raise AlpacaCLIError("Alpaca CLI is not installed or is not on PATH")
        process = subprocess.run(
            ["alpaca", *arguments],
            input=json.dumps(payload) if payload is not None else None,
            text=True,
            capture_output=True,
            timeout=timeout,
            env=self._environment(),
            shell=False,
            check=False,
        )
        command_name = "alpaca " + " ".join(arguments)
        if process.returncode != 0:
            message = process.stderr.strip() or process.stdout.strip() or "unknown CLI error"
            raise AlpacaCLIError(f"{command_name} failed: {message[:500]}")
        output = process.stdout.strip()
        if not output:
            return CLIResult({}, command_name)
        try:
            return CLIResult(json.loads(output), command_name)
        except json.JSONDecodeError as exc:
            raise AlpacaCLIError(f"{command_name} returned non-JSON output") from exc

    def version(self) -> CLIResult:
        return self.run(["version"])

    def account(self) -> CLIResult:
        return self.run(["account", "get", "--quiet"])

    def clock(self) -> CLIResult:
        return self.run(["clock", "--quiet"])

    def positions(self) -> CLIResult:
        return self.run(["position", "list", "--quiet"])

    def orders(self) -> CLIResult:
        return self.run(["order", "list", "--status", "all", "--quiet"])

    def submit_mleg(self, payload: dict[str, Any]) -> CLIResult:
        return self.run(["api", "POST", "/v2/orders"], payload=payload)


def cli_preflight(cli: AlpacaCLI, require_account: bool = True) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    if not cli.available():
        return {
            "ready": False,
            "checks": [{"name": "Alpaca CLI", "passed": False, "detail": "not installed"}],
        }
    checks.append({"name": "Alpaca CLI", "passed": True, "detail": "available on PATH"})
    try:
        version = cli.version().data
        checks.append({"name": "CLI version", "passed": True, "detail": str(version)[:120]})
    except AlpacaCLIError as exc:
        checks.append({"name": "CLI version", "passed": False, "detail": str(exc)})
    if require_account:
        try:
            account = cli.account().data
            status = str(account.get("status", "unknown")) if isinstance(account, dict) else "connected"
            checks.append({"name": "Paper account", "passed": True, "detail": status})
        except AlpacaCLIError as exc:
            checks.append({"name": "Paper account", "passed": False, "detail": str(exc)})
    return {"ready": all(check["passed"] for check in checks), "checks": checks}

