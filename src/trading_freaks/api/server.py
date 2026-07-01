"""Small stdlib JSON server for local decision-support workflows."""

from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Callable, Dict
from urllib.parse import urlparse

from trading_freaks.api.routes import (
    capture_live_source_heartbeat_payload,
    capture_trade_event_payload,
    evaluate_daily_update_payload,
    evaluate_live_status_payload,
    evaluate_morning_brief_payload,
    evaluate_news_deck_payload,
    evaluate_us_news_breakout_payload,
    ingest_live_bridge_payload,
    read_journal_store_payload,
    save_journal_store_payload,
    validate_journal_capture_payload,
)


ROUTES: Dict[str, Callable[[dict], dict]] = {
    "/api/daily-update/evaluate": evaluate_daily_update_payload,
    "/api/live-status/evaluate": evaluate_live_status_payload,
    "/api/live-bridge/ingest": ingest_live_bridge_payload,
    "/api/live-sources/heartbeat": capture_live_source_heartbeat_payload,
    "/api/morning-brief/evaluate": evaluate_morning_brief_payload,
    "/api/news-deck/evaluate": evaluate_news_deck_payload,
    "/api/us-news-breakout/evaluate": evaluate_us_news_breakout_payload,
    "/api/journal/validate": validate_journal_capture_payload,
    "/api/journal/store": save_journal_store_payload,
    "/api/trade-events/capture": capture_trade_event_payload,
}

GET_ROUTES: Dict[str, Callable[[dict], dict]] = {
    "/api/journal/store": read_journal_store_payload,
}


class TradingFreaksHandler(BaseHTTPRequestHandler):
    def do_OPTIONS(self) -> None:
        self._send_json({"status": "ok"})

    def do_GET(self) -> None:
        route_path = urlparse(self.path).path
        if route_path == "/api/health":
            self._send_json({"status": "ok", "live_trading_enabled": False})
            return
        handler = GET_ROUTES.get(route_path)
        if handler is not None:
            self._send_json(handler({}))
            return
        self._send_json({"error": "not_found"}, status=404)

    def do_POST(self) -> None:
        route_path = urlparse(self.path).path
        handler = ROUTES.get(route_path)
        if handler is None:
            self._send_json({"error": "not_found"}, status=404)
            return
        try:
            length = int(self.headers.get("content-length", "0"))
            payload = json.loads(self.rfile.read(length).decode("utf-8") or "{}")
            response = handler(payload)
            self._send_json(response)
        except Exception as exc:  # pragma: no cover - defensive boundary for local server
            self._send_json({"status": "nicht_handeln", "error": str(exc)}, status=400)

    def _send_json(self, payload: dict, status: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("content-type", "application/json; charset=utf-8")
        self.send_header("access-control-allow-origin", "*")
        self.send_header("access-control-allow-methods", "GET, POST, OPTIONS")
        self.send_header("access-control-allow-headers", "content-type")
        self.send_header("content-length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def run(host: str = "127.0.0.1", port: int = 8000) -> None:
    server = ThreadingHTTPServer((host, port), TradingFreaksHandler)
    print(f"TradingFreaks backend listening on http://{host}:{port}")
    server.serve_forever()


if __name__ == "__main__":
    run()
