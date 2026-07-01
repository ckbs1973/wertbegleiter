#!/usr/bin/env python3
"""Keep local update feeds and freshness status current.

This service watches the imported ChatGPT Trading project export plus optional
extra updates, rebuilds the frontend feed, and writes a chat_context heartbeat.
It never fetches private chats by itself, never creates trade signals, and never
executes orders.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
import sys
import time
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tools"))

from build_chatgpt_update_feed import EXTRAS_PATH, OUT_PATH, RAW_PATH, write_feed
from build_live_adapter_config_status import DEFAULT_OUTPUT_PATH as DEFAULT_CONFIG_STATUS_PATH
from build_live_adapter_config_status import write_config_status
from trading_freaks.live_collector import ingest_source_heartbeat, utc_now


DEFAULT_SOURCE_PATH = ROOT / "frontend" / "public" / "data" / "live_source_snapshots.json"
DEFAULT_STATUS_PATH = ROOT / "frontend" / "public" / "data" / "live_feed_status.json"
DEFAULT_ENV_PATH = ROOT / ".env"
DEFAULT_WATCH_PATHS = (RAW_PATH, EXTRAS_PATH)


def file_fingerprint(paths: Iterable[Path]) -> tuple[tuple[str, bool, int, int], ...]:
    values = []
    for path in paths:
        if not path.exists():
            values.append((str(path), False, 0, 0))
            continue
        stat = path.stat()
        values.append((str(path), True, stat.st_mtime_ns, stat.st_size))
    return tuple(values)


def _latest_required_chat_date(feed: dict[str, Any]) -> str:
    values = [
        str(item.get("latest_timestamp") or item.get("latest_sort_key") or "")
        for item in feed.get("chat_coverage", ())
        if item.get("required")
    ]
    return max(values) if values else ""


def chat_context_snapshot(
    feed: dict[str, Any],
    *,
    now: datetime | None = None,
    stale_after_seconds: int = 15,
) -> dict[str, Any]:
    current = now or utc_now()
    covered = int(feed.get("covered_required_chat_count") or 0)
    required = int(feed.get("required_chat_count") or 0)
    missing = [str(item) for item in feed.get("missing_required_chats", ())]
    connection_state = "connected" if required and covered == required and not missing else "error"
    latest_required = _latest_required_chat_date(feed) or "unbekannt"
    details = [
        f"Pflicht-Update-Chats {covered}/{required}",
        f"Coverage {feed.get('coverage_status', 'unbekannt')}",
        f"Updates {feed.get('update_count', 0)}, Extras {feed.get('extra_update_count', 0)}",
        f"Neuester Pflicht-Chat {latest_required}",
        "Lokaler ChatGPT-Export wird beobachtet; kein Scraping, keine Orderausfuehrung.",
    ]
    if missing:
        details.append(f"Fehlende Pflicht-Chats: {', '.join(missing)}")
    return {
        "source_name": "ChatGPT Update Feed",
        "category": "chat_context",
        "connection_state": connection_state,
        "observed_at": current.isoformat(),
        "source_timestamp": current.isoformat(),
        "stale_after_seconds": stale_after_seconds,
        "item_count": int(feed.get("update_count") or 0),
        "details": details,
    }


def write_once(
    *,
    chat_output: Path = OUT_PATH,
    live_source_file: Path = DEFAULT_SOURCE_PATH,
    live_status_file: Path = DEFAULT_STATUS_PATH,
    env_file: Path = DEFAULT_ENV_PATH,
    config_status_file: Path = DEFAULT_CONFIG_STATUS_PATH,
    stale_after_seconds: int = 15,
) -> tuple[dict[str, Any], str]:
    feed = write_feed(chat_output)
    write_config_status(env_file, config_status_file)
    line = write_chat_context_heartbeat(
        feed,
        live_source_file=live_source_file,
        live_status_file=live_status_file,
        stale_after_seconds=stale_after_seconds,
    )
    return feed, line


def write_chat_context_heartbeat(
    feed: dict[str, Any],
    *,
    live_source_file: Path = DEFAULT_SOURCE_PATH,
    live_status_file: Path = DEFAULT_STATUS_PATH,
    stale_after_seconds: int = 15,
) -> str:
    current = utc_now()
    snapshot = chat_context_snapshot(feed, now=current, stale_after_seconds=stale_after_seconds)
    _sources_payload, live_status = ingest_source_heartbeat(
        live_source_file,
        live_status_file,
        snapshot,
        now=current,
    )
    line = (
        f"{current.isoformat()} chat_updates={feed.get('update_count', 0)} "
        f"coverage={feed.get('covered_required_chat_count', 0)}/{feed.get('required_chat_count', 0)} "
        f"live_status={live_status.overall_status}"
    )
    return line


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--chat-output", type=Path, default=OUT_PATH)
    parser.add_argument("--live-source-file", type=Path, default=DEFAULT_SOURCE_PATH)
    parser.add_argument("--live-status-file", type=Path, default=DEFAULT_STATUS_PATH)
    parser.add_argument("--env-file", type=Path, default=DEFAULT_ENV_PATH)
    parser.add_argument("--config-status-file", type=Path, default=DEFAULT_CONFIG_STATUS_PATH)
    parser.add_argument("--interval-seconds", type=float, default=5.0)
    parser.add_argument("--stale-after-seconds", type=int, default=15)
    parser.add_argument("--force-rebuild-every-seconds", type=float, default=60.0)
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()

    if args.once:
        _feed, line = write_once(
            chat_output=args.chat_output,
            live_source_file=args.live_source_file,
            live_status_file=args.live_status_file,
            env_file=args.env_file,
            config_status_file=args.config_status_file,
            stale_after_seconds=args.stale_after_seconds,
        )
        print(line)
        return 0

    print(
        "Realtime update service watching ChatGPT exports; "
        "information only, no order execution.",
        flush=True,
    )
    last_fingerprint = None
    last_rebuild = 0.0
    feed: dict[str, Any] | None = None
    while True:
        current_fingerprint = file_fingerprint(DEFAULT_WATCH_PATHS)
        current_time = time.monotonic()
        should_rebuild = (
            feed is None
            or current_fingerprint != last_fingerprint
            or current_time - last_rebuild >= max(args.force_rebuild_every_seconds, args.interval_seconds)
        )
        if should_rebuild:
            feed = write_feed(args.chat_output)
            write_config_status(args.env_file, args.config_status_file)
            last_fingerprint = current_fingerprint
            last_rebuild = current_time
        if feed is not None:
            line = write_chat_context_heartbeat(
                feed,
                live_source_file=args.live_source_file,
                live_status_file=args.live_status_file,
                stale_after_seconds=args.stale_after_seconds,
            )
            print(line, flush=True)
        time.sleep(max(1.0, args.interval_seconds))


if __name__ == "__main__":
    raise SystemExit(main())
