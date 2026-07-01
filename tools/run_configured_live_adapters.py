#!/usr/bin/env python3
"""Run configured live adapters into the local bridge.

Supported sources are JSON files/endpoints for price, order and calendar data,
plus JSON or RSS/Atom news feeds. The tool is information-only and never sends
orders.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import time
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from trading_freaks.live_adapters import AdapterSource, configured_sources_from_env, read_adapter_payload
from trading_freaks.live_bridge import ingest_bridge_payload
from trading_freaks.live_config import load_env_file as load_config_env_file


DEFAULT_ENV_PATH = ROOT / ".env"
DEFAULT_SOURCE_PATH = ROOT / "frontend" / "public" / "data" / "live_source_snapshots.json"
DEFAULT_STATUS_PATH = ROOT / "frontend" / "public" / "data" / "live_feed_status.json"


def load_env_file(path: Path) -> dict[str, str]:
    return load_config_env_file(path)


def collect_once(
    sources: tuple[AdapterSource, ...],
    *,
    source_path: Path = DEFAULT_SOURCE_PATH,
    status_path: Path = DEFAULT_STATUS_PATH,
) -> list[dict[str, Any]]:
    results = []
    for source in sources:
        try:
            payload = read_adapter_payload(source)
            ingest_results = ingest_bridge_payload(payload, source_path=source_path, status_path=status_path)
            results.append(
                {
                    "source": source.name,
                    "bridge_type": source.bridge_type,
                    "location": source.location,
                    "status": "processed",
                    "results": [item.__dict__ for item in ingest_results],
                }
            )
        except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
            results.append(
                {
                    "source": source.name,
                    "bridge_type": source.bridge_type,
                    "location": source.location,
                    "status": "error",
                    "error": str(exc),
                }
            )
    return results


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--env-file", type=Path, default=DEFAULT_ENV_PATH)
    parser.add_argument("--source-file", type=Path, default=DEFAULT_SOURCE_PATH)
    parser.add_argument("--status-file", type=Path, default=DEFAULT_STATUS_PATH)
    parser.add_argument("--interval-seconds", type=float, default=5.0)
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()

    sources = configured_sources_from_env(load_env_file(args.env_file))
    if not sources:
        print(
            "No live adapters configured. Set LIVE_PRICE_JSON_PATH, LIVE_ORDER_JSON_PATH, "
            "LIVE_CALENDAR_JSON_PATH or LIVE_NEWS_FEED_URL in .env.",
            flush=True,
        )
        return 0

    def run_once() -> None:
        for result in collect_once(sources, source_path=args.source_file, status_path=args.status_file):
            print(json.dumps(result, ensure_ascii=False), flush=True)

    if args.once:
        run_once()
        return 0

    print("Configured live adapters running; information only, no order execution.", flush=True)
    while True:
        run_once()
        time.sleep(max(1.0, args.interval_seconds))


if __name__ == "__main__":
    raise SystemExit(main())
