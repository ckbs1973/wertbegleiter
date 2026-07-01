#!/usr/bin/env python3
"""Watch a local inbox for live bridge JSON payloads.

External adapters can drop JSON files into reports/live_bridge_inbox. This tool
turns those files into source freshness heartbeats for the frontend. It does not
delete files, does not place orders, and does not create trade recommendations.
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

from trading_freaks.live_bridge import ingest_bridge_payload
from trading_freaks.live_collector import utc_now


DEFAULT_INBOX = ROOT / "reports" / "live_bridge_inbox"
DEFAULT_STATE_FILE = ROOT / "reports" / "live_bridge_inbox_state.json"
DEFAULT_SOURCE_PATH = ROOT / "frontend" / "public" / "data" / "live_source_snapshots.json"
DEFAULT_STATUS_PATH = ROOT / "frontend" / "public" / "data" / "live_feed_status.json"


def file_fingerprint(path: Path) -> str:
    stat = path.stat()
    return f"{stat.st_mtime_ns}:{stat.st_size}"


def read_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"files": {}}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"files": {}}
    return payload if isinstance(payload, dict) else {"files": {}}


def write_state(path: Path, state: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def process_inbox_once(
    *,
    inbox: Path = DEFAULT_INBOX,
    state_file: Path = DEFAULT_STATE_FILE,
    source_path: Path = DEFAULT_SOURCE_PATH,
    status_path: Path = DEFAULT_STATUS_PATH,
) -> list[dict[str, Any]]:
    inbox.mkdir(parents=True, exist_ok=True)
    state = read_state(state_file)
    processed_files = state.setdefault("files", {})
    results: list[dict[str, Any]] = []

    for path in sorted(inbox.glob("*.json")):
        fingerprint = file_fingerprint(path)
        state_key = str(path)
        if processed_files.get(state_key, {}).get("fingerprint") == fingerprint:
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            ingest_results = ingest_bridge_payload(payload, source_path=source_path, status_path=status_path)
            result = {
                "file": str(path),
                "status": "processed",
                "fingerprint": fingerprint,
                "processed_at": utc_now().isoformat(),
                "results": [item.__dict__ for item in ingest_results],
            }
        except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
            result = {
                "file": str(path),
                "status": "error",
                "fingerprint": fingerprint,
                "processed_at": utc_now().isoformat(),
                "error": str(exc),
            }
        processed_files[state_key] = result
        results.append(result)

    if results:
        state["updated_at"] = utc_now().isoformat()
        write_state(state_file, state)
    return results


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--inbox", type=Path, default=DEFAULT_INBOX)
    parser.add_argument("--state-file", type=Path, default=DEFAULT_STATE_FILE)
    parser.add_argument("--source-file", type=Path, default=DEFAULT_SOURCE_PATH)
    parser.add_argument("--status-file", type=Path, default=DEFAULT_STATUS_PATH)
    parser.add_argument("--interval-seconds", type=float, default=1.0)
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()

    def run_once() -> None:
        results = process_inbox_once(
            inbox=args.inbox,
            state_file=args.state_file,
            source_path=args.source_file,
            status_path=args.status_file,
        )
        for result in results:
            print(json.dumps(result, ensure_ascii=False), flush=True)

    if args.once:
        run_once()
        return 0

    print(
        f"Live bridge inbox watching {args.inbox}; information only, no order execution.",
        flush=True,
    )
    while True:
        run_once()
        time.sleep(max(0.25, args.interval_seconds))


if __name__ == "__main__":
    raise SystemExit(main())
