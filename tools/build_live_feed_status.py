#!/usr/bin/env python3
"""Build a local live-feed freshness status file.

The script intentionally does not fetch broker/news data. It records whether
required live connections are configured and fresh enough. Real providers can
later write the same JSON shape from WebSocket/API clients.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from trading_freaks.live_collector import status_payload, write_live_status_file
from trading_freaks.live_data import default_required_sources


OUT_PATH = ROOT / "frontend" / "public" / "data" / "live_feed_status.json"


def main() -> int:
    generated_at = datetime.now(timezone.utc)
    status = write_live_status_file(
        OUT_PATH,
        default_required_sources(generated_at=generated_at),
        now=generated_at,
    )
    status_payload(status)
    print(f"wrote {OUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
