#!/usr/bin/env python3
"""Run a narrow TradingView webhook gateway.

The gateway exposes only two token-protected POST routes and forwards them to
the local decision-support API. It does not expose the full API, does not place
orders, and does not create trading recommendations.
"""

from __future__ import annotations

import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import sys
from typing import Any
from urllib.error import URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from trading_freaks.live_config import load_env_file


DEFAULT_ENV_PATH = ROOT / ".env"
DEFAULT_API_BASE_URL = "http://127.0.0.1:8000"
ROUTE_TARGETS = {
    "price": "/api/live-bridge/ingest",
    "trade": "/api/trade-events/capture",
}


def load_gateway_config(env_file: Path = DEFAULT_ENV_PATH) -> dict[str, Any]:
    env = load_env_file(env_file)
    return {
        "host": env.get("TRADINGVIEW_GATEWAY_HOST", "127.0.0.1") or "127.0.0.1",
        "port": int(env.get("TRADINGVIEW_GATEWAY_PORT", "8787") or 8787),
        "token": env.get("TRADINGVIEW_WEBHOOK_TOKEN", "").strip(),
        "api_base_url": env.get("TRADINGVIEW_GATEWAY_API_BASE_URL", DEFAULT_API_BASE_URL).rstrip("/"),
    }


def validate_gateway_token(token: str) -> None:
    if len(token.strip()) < 24:
        raise ValueError("TRADINGVIEW_WEBHOOK_TOKEN must be at least 24 characters")
    if "/" in token or "?" in token or "#" in token:
        raise ValueError("TRADINGVIEW_WEBHOOK_TOKEN must be URL path safe")


def gateway_path_for(kind: str, token: str) -> str:
    if kind not in ROUTE_TARGETS:
        raise ValueError("kind must be price or trade")
    validate_gateway_token(token)
    return f"/tv/{token}/{kind}"


def route_kind_from_path(path: str, token: str) -> str | None:
    parsed = urlparse(path)
    parts = [part for part in parsed.path.split("/") if part]
    if len(parts) != 3 or parts[0] != "tv":
        return None
    if parts[1] != token:
        return ""
    return parts[2] if parts[2] in ROUTE_TARGETS else None


def target_url_for(kind: str, api_base_url: str = DEFAULT_API_BASE_URL) -> str:
    if kind not in ROUTE_TARGETS:
        raise ValueError("unknown gateway route")
    return f"{api_base_url.rstrip('/')}{ROUTE_TARGETS[kind]}"


def forward_json_payload(kind: str, payload: dict[str, Any], *, api_base_url: str = DEFAULT_API_BASE_URL) -> dict[str, Any]:
    target = target_url_for(kind, api_base_url)
    request = Request(
        target,
        data=json.dumps(payload).encode("utf-8"),
        headers={"content-type": "application/json; charset=utf-8"},
        method="POST",
    )
    with urlopen(request, timeout=5) as response:  # nosec - forwards to local API configured by user
        return json.loads(response.read().decode("utf-8"))


def make_handler(*, token: str, api_base_url: str) -> type[BaseHTTPRequestHandler]:
    class TradingViewGatewayHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            if urlparse(self.path).path == "/health":
                self._send_json(
                    {
                        "status": "ok",
                        "routes": ["POST /tv/<token>/price", "POST /tv/<token>/trade"],
                        "information_only": True,
                    }
                )
                return
            self._send_json({"error": "not_found"}, status=404)

        def do_POST(self) -> None:
            kind = route_kind_from_path(self.path, token)
            if kind == "":
                self._send_json({"error": "forbidden"}, status=403)
                return
            if kind is None:
                self._send_json({"error": "not_found"}, status=404)
                return
            try:
                length = int(self.headers.get("content-length", "0"))
                raw_body = self.rfile.read(length).decode("utf-8")
                payload = json.loads(raw_body or "{}")
                if not isinstance(payload, dict):
                    raise ValueError("TradingView webhook body must be a JSON object")
                result = forward_json_payload(kind, payload, api_base_url=api_base_url)
                self._send_json(
                    {
                        "status": "forwarded",
                        "kind": kind,
                        "target": ROUTE_TARGETS[kind],
                        "result": result,
                        "disclaimer": "Information only, keine Anlageberatung und keine Orderausfuehrung.",
                    }
                )
            except (ValueError, json.JSONDecodeError) as exc:
                self._send_json({"status": "invalid_payload", "error": str(exc)}, status=400)
            except (OSError, URLError) as exc:
                self._send_json({"status": "api_unreachable", "error": str(exc)}, status=502)

        def _send_json(self, payload: dict[str, Any], status: int = 200) -> None:
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("content-type", "application/json; charset=utf-8")
            self.send_header("content-length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    return TradingViewGatewayHandler


def run(host: str, port: int, token: str, api_base_url: str) -> None:
    validate_gateway_token(token)
    server = ThreadingHTTPServer((host, port), make_handler(token=token, api_base_url=api_base_url))
    print(f"TradingView webhook gateway listening on http://{host}:{port}")
    print("Routes: /tv/<token>/price and /tv/<token>/trade")
    print("Information only, no order execution.")
    server.serve_forever()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--env-file", type=Path, default=DEFAULT_ENV_PATH)
    parser.add_argument("--host", default="")
    parser.add_argument("--port", type=int, default=0)
    parser.add_argument("--token", default="")
    parser.add_argument("--api-base-url", default="")
    args = parser.parse_args()

    config = load_gateway_config(args.env_file)
    run(
        host=args.host or config["host"],
        port=args.port or config["port"],
        token=args.token or config["token"],
        api_base_url=(args.api_base_url or config["api_base_url"]),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

