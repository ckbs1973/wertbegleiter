#!/usr/bin/env python3
"""Check TradingView webhook readiness without executing orders.

The check is deliberately read-only. It validates local endpoint configuration,
public webhook URL placeholders, tunnel tool availability and JSON alert
templates. It never places broker orders and never creates trade advice.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import sys
from typing import Any
from urllib.parse import urlsplit


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from trading_freaks.live_config import load_env_file, masked_location


DEFAULT_ENV_PATH = ROOT / ".env"
DEFAULT_TEMPLATE_DIR = ROOT / "reports" / "live_sources" / "tradingview_webhooks"

REQUIRED_TEMPLATE_FILES = (
    "price_heartbeat_alert_message.json",
    "trade_opened_alert_message.json",
    "trade_closed_manual_alert_message.json",
)

LOCAL_HOSTS = {"127.0.0.1", "localhost", "::1"}
PUBLIC_GATEWAY_KINDS = {"price", "trade"}


def public_webhook_url_check(value: str) -> tuple[bool, str]:
    url = value.strip()
    if not url:
        return False, "URL fehlt."
    parsed = urlsplit(url)
    if parsed.scheme != "https":
        return False, "TradingView-Webhooks brauchen eine oeffentliche HTTPS-URL."
    if not parsed.netloc:
        return False, "HTTPS-URL hat keinen Host."
    host = parsed.hostname or ""
    if host.lower() in LOCAL_HOSTS:
        return False, "Lokale Hosts sind von TradingView nicht erreichbar."
    if parsed.query or parsed.fragment:
        return False, "Keine Query-Strings oder Fragmente in Webhook-URLs speichern."
    if not _is_token_gateway_path(parsed.path):
        return False, "Public TradingView-URLs muessen auf das token-geschuetzte Gateway /tv/<token>/price oder /tv/<token>/trade zeigen."
    return True, "Public Webhook-URL ist formal geeignet."


def _is_token_gateway_path(path: str) -> bool:
    parts = [part for part in path.split("/") if part]
    for idx, part in enumerate(parts):
        if part == "tv" and idx + 2 < len(parts):
            token = parts[idx + 1]
            route_kind = parts[idx + 2]
            return len(token) >= 24 and route_kind in PUBLIC_GATEWAY_KINDS
    return False


def _load_json_template(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("template must contain a JSON object")
    return payload


def template_checks(template_dir: Path = DEFAULT_TEMPLATE_DIR) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    for filename in REQUIRED_TEMPLATE_FILES:
        path = template_dir / filename
        item: dict[str, Any] = {
            "file": str(path),
            "name": filename,
            "exists": path.exists(),
            "valid_json": False,
            "status": "missing",
            "message": "Template fehlt.",
        }
        if path.exists():
            try:
                payload = _load_json_template(path)
                item.update(
                    {
                        "valid_json": True,
                        "status": "ok",
                        "message": "Template ist JSON-valide.",
                        "keys": sorted(payload.keys()),
                    }
                )
            except (OSError, ValueError, json.JSONDecodeError) as exc:
                item.update({"status": "error", "message": f"Template ungueltig: {exc}"})
        checks.append(item)
    return checks


def _tool_check(tool: str) -> dict[str, str]:
    path = shutil.which(tool) or ""
    return {"tool": tool, "path": path, "status": "installed" if path else "missing"}


def _local_tool_check(tool: str, path: Path) -> dict[str, str]:
    installed = path.exists() and os.access(path, os.X_OK)
    return {"tool": tool, "path": str(path) if installed else "", "status": "installed" if installed else "missing"}


def tunnel_tool_checks() -> list[dict[str, str]]:
    return [
        _tool_check("ngrok"),
        _tool_check("cloudflared"),
        _local_tool_check("cloudflared-local", ROOT / "tools" / "bin" / "cloudflared"),
    ]


def readiness_payload(env_file: Path = DEFAULT_ENV_PATH, template_dir: Path = DEFAULT_TEMPLATE_DIR) -> dict[str, Any]:
    env = load_env_file(env_file)
    templates = template_checks(template_dir)
    tunnel_tools = tunnel_tool_checks()
    public_price = env.get("TRADINGVIEW_WEBHOOK_PUBLIC_PRICE_URL", "").strip()
    public_trade = env.get("TRADINGVIEW_WEBHOOK_PUBLIC_TRADE_URL", "").strip()
    local_price = env.get("TRADINGVIEW_WEBHOOK_LOCAL_PRICE_URL", "").strip()
    local_trade = env.get("TRADINGVIEW_WEBHOOK_LOCAL_TRADE_URL", "").strip()

    local_ready = bool(local_price and local_trade and all(item["status"] == "ok" for item in templates))
    public_price_ok, public_price_message = public_webhook_url_check(public_price)
    public_trade_ok, public_trade_message = public_webhook_url_check(public_trade)
    public_ready = public_price_ok and public_trade_ok
    tunnel_tool_installed = any(item["status"] == "installed" for item in tunnel_tools)

    blockers = []
    if not local_ready:
        blockers.append("Lokale Webhook-Ziele oder Templates fehlen.")
    if not public_ready:
        blockers.append("TradingView braucht eine oeffentliche HTTPS-URL fuer Webhooks.")
        if public_price and not public_price_ok:
            blockers.append(f"Price-Webhook ungueltig: {public_price_message}")
        if public_trade and not public_trade_ok:
            blockers.append(f"Trade-Webhook ungueltig: {public_trade_message}")
    if not public_ready and not tunnel_tool_installed:
        blockers.append("Kein Tunnel-Tool gefunden: ngrok oder cloudflared installieren/konfigurieren.")

    return {
        "status": "ready_for_tradingview" if local_ready and public_ready else "local_ready_public_missing" if local_ready else "not_ready",
        "disclaimer": "Read-only Webhook-Pruefung, keine Anlageberatung, keine Orderausfuehrung.",
        "env_file": {"exists": env_file.exists(), "path": str(env_file)},
        "local_endpoints": {
            "price": local_price,
            "trade": local_trade,
            "ready": local_ready,
        },
        "public_endpoints": {
            "price": masked_location(public_price),
            "trade": masked_location(public_trade),
            "ready": public_ready,
            "price_message": public_price_message,
            "trade_message": public_trade_message,
        },
        "templates": templates,
        "tunnel_tools": tunnel_tools,
        "blockers": blockers,
        "next_step": (
            "TradingView-Gateway starten, HTTPS-Tunnel auf Port 8787 einrichten und PUBLIC-URLs in .env setzen."
            if not public_ready
            else "TradingView Alert-Webhooks mit den Public-URLs und Templates testen."
        ),
        "information_only": True,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--env-file", type=Path, default=DEFAULT_ENV_PATH)
    parser.add_argument("--template-dir", type=Path, default=DEFAULT_TEMPLATE_DIR)
    args = parser.parse_args()

    payload = readiness_payload(args.env_file, args.template_dir)
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
