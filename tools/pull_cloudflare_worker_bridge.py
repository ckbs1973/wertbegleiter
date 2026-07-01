#!/usr/bin/env python3
"""Pull Cloudflare Worker TradingView webhook events into the local portal.

The Worker endpoint stores already-observed TradingView facts. This local
puller updates source freshness and journal drafts. It does not execute orders.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import time


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tools"))

from pull_kas_webhook_bridge import (  # noqa: E402
    DEFAULT_ENV_PATH,
    events_url_from_price_or_trade_url,
    pull_once,
)
from trading_freaks.api.routes import (  # noqa: E402
    DEFAULT_JOURNAL_STORE_PATH,
    DEFAULT_LIVE_SOURCE_PATH,
    DEFAULT_LIVE_STATUS_PATH,
)
from trading_freaks.live_config import load_env_file  # noqa: E402


DEFAULT_CURSOR_PATH = ROOT / "reports" / "live_sources" / "cloudflare_worker_bridge_cursor.json"


def configured_events_url(env: dict[str, str]) -> str:
    direct = env.get("CLOUDFLARE_WORKER_BRIDGE_EVENTS_URL", "").strip()
    if direct:
        return direct
    for key in ("TRADINGVIEW_WEBHOOK_PUBLIC_PRICE_URL", "TRADINGVIEW_WEBHOOK_PUBLIC_TRADE_URL"):
        value = env.get(key, "").strip()
        if value:
            return events_url_from_price_or_trade_url(value)
    raise ValueError("Set CLOUDFLARE_WORKER_BRIDGE_EVENTS_URL or TradingView public webhook URLs in .env")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--env-file", type=Path, default=DEFAULT_ENV_PATH)
    parser.add_argument("--events-url", default="")
    parser.add_argument("--cursor-path", type=Path, default=None)
    parser.add_argument("--source-file", type=Path, default=DEFAULT_LIVE_SOURCE_PATH)
    parser.add_argument("--status-file", type=Path, default=DEFAULT_LIVE_STATUS_PATH)
    parser.add_argument("--journal-store", type=Path, default=DEFAULT_JOURNAL_STORE_PATH)
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--timeout-seconds", type=float, default=5.0)
    parser.add_argument("--interval-seconds", type=float, default=3.0)
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()

    env = load_env_file(args.env_file)
    events_url = args.events_url.strip() or configured_events_url(env)
    cursor_path = args.cursor_path or Path(env.get("CLOUDFLARE_WORKER_BRIDGE_CURSOR_PATH", "") or DEFAULT_CURSOR_PATH)

    def run() -> None:
        print(
            json.dumps(
                pull_once(
                    events_url=events_url,
                    cursor_path=cursor_path,
                    source_path=args.source_file,
                    status_path=args.status_file,
                    journal_store_path=args.journal_store,
                    limit=args.limit,
                    timeout_seconds=args.timeout_seconds,
                    bridge_name="Cloudflare Worker Bridge Pull",
                    cursor_source="cloudflare_worker_bridge",
                ),
                ensure_ascii=False,
            ),
            flush=True,
        )

    if args.once:
        run()
        return 0

    print("Cloudflare Worker bridge puller running; information only, no order execution.", flush=True)
    while True:
        run()
        time.sleep(max(1.0, args.interval_seconds))


if __name__ == "__main__":
    raise SystemExit(main())
