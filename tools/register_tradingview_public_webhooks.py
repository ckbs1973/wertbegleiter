#!/usr/bin/env python3
"""Register public TradingView webhook URLs in .env.

This helper only writes endpoint configuration. It does not start tunnels,
does not fetch market data, does not create advice and never enables live
trading or broker execution.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from urllib.parse import urlsplit, urlunsplit


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "src"))

from check_tradingview_webhook_setup import public_webhook_url_check
from run_tradingview_webhook_gateway import gateway_path_for, load_gateway_config
from trading_freaks.live_config import masked_location


DEFAULT_ENV_PATH = ROOT / ".env"


def endpoint_from_base(base_url: str, path: str) -> str:
    parsed = urlsplit(base_url.strip())
    if parsed.scheme != "https" or not parsed.netloc:
        raise ValueError("base-url must be a public https URL")
    base_path = parsed.path.rstrip("/")
    endpoint_path = path if not base_path else f"{base_path}{path}"
    return urlunsplit((parsed.scheme, parsed.netloc, endpoint_path, "", ""))


def gateway_endpoints_from_base(base_url: str, token: str) -> tuple[str, str]:
    return (
        endpoint_from_base(base_url, gateway_path_for("price", token)),
        endpoint_from_base(base_url, gateway_path_for("trade", token)),
    )


def kas_events_endpoint_from_base(base_url: str, token: str) -> str:
    price_path = gateway_path_for("price", token)
    return endpoint_from_base(base_url, f"{price_path.rsplit('/', 1)[0]}/events")


def update_env_text(text: str, updates: dict[str, str]) -> str:
    seen: set[str] = set()
    lines = []
    for raw_line in text.splitlines():
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            lines.append(raw_line)
            continue
        key, _value = raw_line.split("=", 1)
        clean_key = key.strip()
        if clean_key in updates:
            lines.append(f"{clean_key}={updates[clean_key]}")
            seen.add(clean_key)
        else:
            lines.append(raw_line)

    missing_updates = [key for key in updates if key not in seen]
    if missing_updates and lines and lines[-1].strip():
        lines.append("")
    for key in missing_updates:
        lines.append(f"{key}={updates[key]}")
    return "\n".join(lines).rstrip() + "\n"


def register_public_webhooks(
    *,
    env_file: Path,
    price_url: str,
    trade_url: str,
    kas_events_url: str = "",
    dry_run: bool = False,
) -> dict[str, object]:
    price_ok, price_message = public_webhook_url_check(price_url)
    trade_ok, trade_message = public_webhook_url_check(trade_url)
    if not price_ok or not trade_ok:
        return {
            "status": "ungueltig",
            "errors": [
                message
                for ok, message in ((price_ok, price_message), (trade_ok, trade_message))
                if not ok
            ],
            "information_only": True,
        }

    original = env_file.read_text(encoding="utf-8") if env_file.exists() else ""
    updates = {
        "TRADINGVIEW_WEBHOOK_PUBLIC_PRICE_URL": price_url,
        "TRADINGVIEW_WEBHOOK_PUBLIC_TRADE_URL": trade_url,
    }
    if kas_events_url:
        updates["KAS_WEBHOOK_BRIDGE_EVENTS_URL"] = kas_events_url
    new_text = update_env_text(original, updates)
    if not dry_run:
        env_file.write_text(new_text, encoding="utf-8")

    return {
        "status": "registriert" if not dry_run else "dry_run",
        "env_file": str(env_file),
        "public_endpoints": {
            "price": masked_location(price_url),
            "trade": masked_location(trade_url),
            "kas_events": masked_location(kas_events_url) if kas_events_url else "",
        },
        "next_step": "python3 tools/check_tradingview_webhook_setup.py ausfuehren und TradingView Alerts testen.",
        "disclaimer": "Konfiguration-only, keine Anlageberatung und keine Orderausfuehrung.",
        "information_only": True,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--env-file", type=Path, default=DEFAULT_ENV_PATH)
    parser.add_argument("--base-url", default="", help="Public HTTPS base URL, e.g. https://example.trycloudflare.com")
    parser.add_argument("--token", default="", help="Webhook token; defaults to TRADINGVIEW_WEBHOOK_TOKEN from .env")
    parser.add_argument("--price-url", default="")
    parser.add_argument("--trade-url", default="")
    parser.add_argument("--kas-bridge", action="store_true", help="Also register KAS_WEBHOOK_BRIDGE_EVENTS_URL at /tv/<token>/events")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if args.base_url:
        token = args.token.strip() or str(load_gateway_config(args.env_file).get("token", "")).strip()
        try:
            price_url, trade_url = gateway_endpoints_from_base(args.base_url, token)
        except ValueError as exc:
            payload = {"status": "ungueltig", "errors": [str(exc)], "information_only": True}
            print(json.dumps(payload, indent=2, ensure_ascii=False))
            return 2
    else:
        price_url = args.price_url.strip()
        trade_url = args.trade_url.strip()
        token = args.token.strip() or str(load_gateway_config(args.env_file).get("token", "")).strip()
    kas_events_url = kas_events_endpoint_from_base(args.base_url, token) if args.kas_bridge and args.base_url else ""

    payload = register_public_webhooks(
        env_file=args.env_file,
        price_url=price_url,
        trade_url=trade_url,
        kas_events_url=kas_events_url,
        dry_run=args.dry_run,
    )
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0 if payload["status"] in {"registriert", "dry_run"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
