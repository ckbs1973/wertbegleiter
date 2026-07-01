#!/usr/bin/env python3
"""Pull stored KAS/ALL-INKL TradingView webhook events into the local portal.

The public KAS endpoint stores facts only. This local puller updates source
freshness and journal drafts. It does not execute orders.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import time
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from trading_freaks.api.routes import (  # noqa: E402
    DEFAULT_JOURNAL_STORE_PATH,
    DEFAULT_LIVE_SOURCE_PATH,
    DEFAULT_LIVE_STATUS_PATH,
)
from trading_freaks.kas_bridge import process_kas_bridge_events  # noqa: E402
from trading_freaks.live_config import load_env_file, masked_location  # noqa: E402


DEFAULT_ENV_PATH = ROOT / ".env"
DEFAULT_CURSOR_PATH = ROOT / "reports" / "live_sources" / "kas_webhook_bridge_cursor.json"


def events_url_from_price_or_trade_url(value: str) -> str:
    parsed = urlsplit(value.strip())
    if parsed.scheme != "https" or not parsed.netloc:
        raise ValueError("KAS bridge URL must be https")
    parts = [part for part in parsed.path.split("/") if part]
    if len(parts) < 3 or parts[-3] != "tv" or parts[-1] not in {"price", "trade"}:
        raise ValueError("KAS bridge URL must contain /tv/<token>/price or /tv/<token>/trade")
    parts[-1] = "events"
    return urlunsplit((parsed.scheme, parsed.netloc, "/" + "/".join(parts), "", ""))


def events_url_with_cursor(events_url: str, *, since: int, limit: int) -> str:
    parsed = urlsplit(events_url.strip())
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    query.update({"since": str(max(0, since)), "limit": str(max(1, limit))})
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, urlencode(query), ""))


def load_cursor(path: Path) -> int:
    if not path.exists():
        return 0
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        return 0
    return max(0, int(payload.get("last_sequence", 0) or 0))


def save_cursor(path: Path, sequence: int, *, source: str = "kas_webhook_bridge") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "last_sequence": max(0, int(sequence)),
                "source": source,
                "information_only": True,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def fetch_kas_events(events_url: str, *, since: int, limit: int, timeout_seconds: float) -> dict[str, Any]:
    request = Request(
        events_url_with_cursor(events_url, since=since, limit=limit),
        headers={"User-Agent": "WertBegleiter-Kapitalmarkt/0.1"},
    )
    with urlopen(request, timeout=timeout_seconds) as response:  # nosec - user-configured KAS endpoint
        payload = json.loads(response.read().decode("utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("KAS bridge response must be a JSON object")
    return payload


def configured_events_url(env: dict[str, str]) -> str:
    direct = env.get("KAS_WEBHOOK_BRIDGE_EVENTS_URL", "").strip()
    if direct:
        return direct
    for key in ("TRADINGVIEW_WEBHOOK_PUBLIC_PRICE_URL", "TRADINGVIEW_WEBHOOK_PUBLIC_TRADE_URL"):
        value = env.get(key, "").strip()
        if value:
            return events_url_from_price_or_trade_url(value)
    raise ValueError("Set KAS_WEBHOOK_BRIDGE_EVENTS_URL or TradingView public webhook URLs in .env")


def pull_once(
    *,
    events_url: str,
    cursor_path: Path,
    source_path: Path,
    status_path: Path,
    journal_store_path: Path,
    limit: int,
    timeout_seconds: float,
    bridge_name: str = "KAS Bridge Pull",
    cursor_source: str = "kas_webhook_bridge",
) -> dict[str, Any]:
    since = load_cursor(cursor_path)
    payload = fetch_kas_events(events_url, since=since, limit=limit, timeout_seconds=timeout_seconds)
    records = payload.get("events", [])
    if not isinstance(records, list):
        raise ValueError("KAS bridge events must be a list")

    results = process_kas_bridge_events(
        records,
        source_path=source_path,
        status_path=status_path,
        journal_store_path=journal_store_path,
    )
    sequences = [int(record.get("sequence", 0) or 0) for record in records if isinstance(record, dict)]
    if sequences:
        save_cursor(cursor_path, max(sequences), source=cursor_source)

    return {
        "status": "processed",
        "events_url": masked_location(events_url),
        "count": len(records),
        "processed": [
            {
                "sequence": item.sequence,
                "kind": item.kind,
                "status": item.status,
                "journal_action": item.journal_action.get("action") if item.journal_action else "",
                "information_only": True,
            }
            for item in results
        ],
        "disclaimer": f"{bridge_name}, keine Anlageberatung und keine Orderausfuehrung.",
        "information_only": True,
    }


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
    cursor_path = args.cursor_path or Path(env.get("KAS_WEBHOOK_BRIDGE_CURSOR_PATH", "") or DEFAULT_CURSOR_PATH)

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
                ),
                ensure_ascii=False,
            ),
            flush=True,
        )

    if args.once:
        run()
        return 0

    print("KAS webhook bridge puller running; information only, no order execution.", flush=True)
    while True:
        run()
        time.sleep(max(1.0, args.interval_seconds))


if __name__ == "__main__":
    raise SystemExit(main())
