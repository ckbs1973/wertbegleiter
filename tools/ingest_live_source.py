#!/usr/bin/env python3
"""Upsert one live source heartbeat for the local collector.

This is a bridge target for TradingView/Broker/News scripts. It does not
execute orders and does not create trading recommendations.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from trading_freaks.live_collector import upsert_snapshot_payload, utc_now


DEFAULT_SOURCE_PATH = ROOT / "frontend" / "public" / "data" / "live_source_snapshots.json"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-file", type=Path, default=DEFAULT_SOURCE_PATH)
    parser.add_argument("--source-name", required=True)
    parser.add_argument("--category", required=True, choices=("price", "order", "news", "calendar", "chat_context", "journal"))
    parser.add_argument("--connection-state", default="connected", choices=("connected", "missing", "blocked", "error"))
    parser.add_argument("--source-timestamp", default="")
    parser.add_argument("--stale-after-seconds", type=int, default=None)
    parser.add_argument("--item-count", type=int, default=1)
    parser.add_argument("--detail", action="append", default=[])
    args = parser.parse_args()

    now = utc_now()
    existing = {}
    if args.source_file.exists():
        existing = json.loads(args.source_file.read_text(encoding="utf-8"))
    payload = upsert_snapshot_payload(
        existing,
        {
            "source_name": args.source_name,
            "category": args.category,
            "connection_state": args.connection_state,
            "source_timestamp": args.source_timestamp or now.isoformat(),
            "observed_at": now.isoformat(),
            "stale_after_seconds": args.stale_after_seconds,
            "item_count": args.item_count,
            "details": args.detail,
        },
        now=now,
    )
    args.source_file.parent.mkdir(parents=True, exist_ok=True)
    args.source_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"updated {args.source_file}: {args.source_name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
