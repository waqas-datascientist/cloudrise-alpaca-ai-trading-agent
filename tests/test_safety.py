from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from cloudrise.alpaca_cli import AlpacaCLI
from cloudrise.config import Settings
from cloudrise.server import serve


class SafetyTests(unittest.TestCase):
    def test_cli_child_environment_forces_paper(self) -> None:
        cli = AlpacaCLI("key", "secret")
        environment = cli._environment()
        self.assertEqual("false", environment["ALPACA_LIVE_TRADE"])
        self.assertEqual("json", environment["ALPACA_OUTPUT"])

    def test_live_environment_is_rejected(self) -> None:
        with patch.dict(os.environ, {"ALPACA_LIVE_TRADE": "true"}, clear=False):
            with self.assertRaisesRegex(ValueError, "paper-only"):
                Settings.from_env()

    def test_invalid_mode_is_rejected(self) -> None:
        with patch.dict(os.environ, {"CLOUDRISE_MODE": "live", "ALPACA_LIVE_TRADE": ""}, clear=False):
            with self.assertRaisesRegex(ValueError, "demo.*paper"):
                Settings.from_env()

    def test_paper_dashboard_cannot_bind_publicly(self) -> None:
        with self.assertRaisesRegex(ValueError, "demo mode"):
            serve(Settings(execution_mode="paper"), "0.0.0.0", 8787)


if __name__ == "__main__":
    unittest.main()
