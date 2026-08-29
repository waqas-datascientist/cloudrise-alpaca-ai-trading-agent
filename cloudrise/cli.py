from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path

from .agent import CloudRiseAgent
from .config import Settings
from .server import RUNTIME_ROOT, serve


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="CloudRise autonomous Alpaca options agent")
    subparsers = parser.add_subparsers(dest="command", required=True)
    server = subparsers.add_parser("serve", help="start the local decision dashboard")
    server.add_argument("--host", default=os.getenv("CLOUDRISE_HOST", "127.0.0.1"))
    server.add_argument("--port", default=int(os.getenv("PORT", "8787")), type=int)
    subparsers.add_parser("preflight", help="verify paper account, CLI and safety invariants")
    subparsers.add_parser("cycle", help="run one autonomous observe→debate→govern→execute cycle")
    watch = subparsers.add_parser("watch", help="run autonomous cycles at the configured interval")
    watch.add_argument("--interval", type=int, default=None, help="override interval in minutes")
    return parser


def main() -> None:
    arguments = build_parser().parse_args()
    settings = Settings.from_env()
    if arguments.command == "serve":
        serve(settings, arguments.host, arguments.port)
        return
    agent = CloudRiseAgent(settings, Path(RUNTIME_ROOT))
    if arguments.command == "watch":
        interval = max(1, arguments.interval or settings.scan_interval_minutes)
        print(f"CloudRise autonomous loop started · every {interval}m · {settings.execution_mode.upper()} · paper only")
        try:
            while True:
                print(json.dumps(agent.run_cycle(), indent=2, default=str))
                time.sleep(interval * 60)
        except KeyboardInterrupt:
            print("CloudRise loop stopped safely.")
        return
    payload = agent.preflight() if arguments.command == "preflight" else agent.run_cycle()
    print(json.dumps(payload, indent=2, default=str))


if __name__ == "__main__":
    main()
