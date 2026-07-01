#!/usr/bin/env python3
"""Continuously build the frontend live-feed status file."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
import time


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from trading_freaks.live_collector import read_source_snapshots, utc_now, write_live_status_file


DEFAULT_SOURCE_PATH = ROOT / "frontend" / "public" / "data" / "live_source_snapshots.json"
DEFAULT_OUTPUT_PATH = ROOT / "frontend" / "public" / "data" / "live_feed_status.json"


def write_once(source_path: Path, output_path: Path) -> str:
    current = utc_now()
    sources = read_source_snapshots(source_path, now=current)
    status = write_live_status_file(output_path, sources, now=current)
    return (
        f"{status.generated_at.isoformat()} "
        f"{status.overall_status} live={status.live_source_count} "
        f"stale={status.stale_source_count} missing={status.missing_source_count}"
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-file", type=Path, default=DEFAULT_SOURCE_PATH)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH)
    parser.add_argument("--interval-seconds", type=float, default=1.0)
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()

    if args.once:
        print(write_once(args.source_file, args.output))
        return 0

    print(f"Live feed collector writing {args.output} every {args.interval_seconds:.2f}s")
    while True:
        print(write_once(args.source_file, args.output), flush=True)
        time.sleep(max(0.25, args.interval_seconds))


if __name__ == "__main__":
    raise SystemExit(main())
