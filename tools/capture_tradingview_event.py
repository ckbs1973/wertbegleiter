#!/usr/bin/env python3
"""Create journal event JSON from the local TradingView macOS app.

The tool does not read orders from TradingView and does not execute trades.
It activates the TradingView app, captures the visible screen when requested,
and writes a structured event that the frontend Journal can process.
"""

from __future__ import annotations

import argparse
import json
import platform
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional


EVENT_TYPES = ("opened", "closed_stop_loss", "closed_take_profit", "closed_manual")
DEFAULT_OUTPUT_DIR = Path("reports/tradingview_captures")


def slug(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_.-]+", "-", value.strip())
    return cleaned.strip("-") or "trade"


def iso_now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def event_filename(symbol: str, trade_id: str, event_type: str, suffix: str) -> str:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return f"{stamp}-{slug(symbol)}-{slug(trade_id)}-{slug(event_type)}.{suffix}"


def optional_float(value: Optional[str]) -> Optional[float]:
    if value in (None, ""):
        return None
    parsed = float(str(value).replace(",", "."))
    return parsed


def activate_app(app_name: str) -> None:
    if platform.system() != "Darwin":
        raise RuntimeError("TradingView-App-Capture ist nur auf macOS verfuegbar.")
    subprocess.run(
        ["osascript", "-e", f'tell application "{app_name}" to activate'],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    time.sleep(0.6)


def capture_screen(output_path: Path, app_name: str = "TradingView") -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    activate_app(app_name)
    subprocess.run(
        ["screencapture", "-x", str(output_path)],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return output_path


def build_event_payload(args: argparse.Namespace, screenshot_path: str = "") -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "event_type": args.event_type,
        "source": "tradingview_macos_app",
        "trade_id": args.trade_id,
        "symbol": args.symbol.upper(),
        "timestamp": args.timestamp or iso_now(),
        "screenshot_path": screenshot_path,
        "note": args.note or "Aus TradingView macOS App fuer Journal-Capture erzeugt.",
    }

    if args.market:
        payload["market"] = args.market

    if args.event_type == "opened":
        payload.update(
            {
                "direction": args.direction,
                "entry": optional_float(args.entry),
                "stop_loss": optional_float(args.stop_loss),
                "take_profit": optional_float(args.take_profit),
                "size": optional_float(args.size),
            }
        )
    else:
        payload.update(
            {
                "exit_price": optional_float(args.exit_price),
                "fees": optional_float(args.fees),
                "slippage": optional_float(args.slippage),
            }
        )

    return {key: value for key, value in payload.items() if value not in (None, "")}


def write_json(path: Path, payload: Dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def copy_to_clipboard(payload: Dict[str, Any]) -> None:
    subprocess.run(
        ["pbcopy"],
        input=json.dumps(payload, indent=2, ensure_ascii=False),
        check=True,
        text=True,
    )


def parser() -> argparse.ArgumentParser:
    argument_parser = argparse.ArgumentParser(
        description="TradingView macOS Screenshot erfassen und Journal-Event-JSON erzeugen.",
    )
    argument_parser.add_argument("--event-type", choices=EVENT_TYPES, required=True)
    argument_parser.add_argument("--trade-id", required=True, help="Eindeutige ID fuer parallele Trades.")
    argument_parser.add_argument("--symbol", required=True)
    argument_parser.add_argument("--market", default="")
    argument_parser.add_argument("--timestamp", default="")
    argument_parser.add_argument("--direction", choices=("long", "short", "conditional"), default="long")
    argument_parser.add_argument("--entry", default="")
    argument_parser.add_argument("--stop-loss", default="")
    argument_parser.add_argument("--take-profit", default="")
    argument_parser.add_argument("--size", default="")
    argument_parser.add_argument("--exit-price", default="")
    argument_parser.add_argument("--fees", default="")
    argument_parser.add_argument("--slippage", default="")
    argument_parser.add_argument("--note", default="")
    argument_parser.add_argument("--app-name", default="TradingView")
    argument_parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    argument_parser.add_argument("--no-screenshot", action="store_true")
    argument_parser.add_argument("--copy", action="store_true", help="Event-JSON in die Zwischenablage legen.")
    return argument_parser


def main(argv: Optional[list[str]] = None) -> int:
    args = parser().parse_args(argv)
    output_dir = Path(args.output_dir)
    screenshot_path = ""

    if not args.no_screenshot:
        screenshot_file = output_dir / "screenshots" / event_filename(args.symbol, args.trade_id, args.event_type, "png")
        try:
            screenshot_path = str(capture_screen(screenshot_file, args.app_name))
        except (RuntimeError, subprocess.CalledProcessError) as error:
            print(f"Screenshot nicht erstellt: {error}", file=sys.stderr)
            print("Hinweis: macOS benoetigt ggf. Bildschirmaufnahme-Rechte fuer Terminal/Codex.", file=sys.stderr)

    payload = build_event_payload(args, screenshot_path=screenshot_path)
    json_file = output_dir / "events" / event_filename(args.symbol, args.trade_id, args.event_type, "json")
    write_json(json_file, payload)

    if args.copy:
        copy_to_clipboard(payload)

    print(json.dumps({"event_file": str(json_file), "event": payload}, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
