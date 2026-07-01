#!/usr/bin/env python3
"""Create a TradingFreaks morning brief from a TradingView watchlist file."""

from __future__ import annotations

import argparse
from pathlib import Path

from trading_freaks.morning_brief import create_morning_brief, summarize_brief


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("watchlist", type=Path)
    parser.add_argument("--date", default="naechster Handelstag")
    parser.add_argument("--max-candidates", type=int, default=5)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    brief = create_morning_brief(
        args.watchlist.read_text(encoding="utf-8"),
        generated_for=args.date,
        max_candidates=args.max_candidates,
    )
    summary = summarize_brief(brief)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(summary, encoding="utf-8")
    print(summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
