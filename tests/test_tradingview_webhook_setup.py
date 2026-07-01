import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

from check_tradingview_webhook_setup import public_webhook_url_check, readiness_payload, template_checks
from register_tradingview_public_webhooks import (
    endpoint_from_base,
    gateway_endpoints_from_base,
    kas_events_endpoint_from_base,
    register_public_webhooks,
    update_env_text,
    worker_events_endpoint_from_base,
)
from run_tradingview_webhook_gateway import gateway_path_for, route_kind_from_path, target_url_for


TOKEN = "abcdefghijklmnopqrstuvwxyz123456"

PRICE_TEMPLATE = {
    "bridge_type": "price",
    "source_name": "TradingView Webhook",
    "symbol": "{{ticker}}",
    "last": "{{close}}",
}

OPEN_TEMPLATE = {
    "event_type": "opened",
    "trade_id": "{{ticker}}-{{timenow}}",
    "symbol": "{{ticker}}",
    "timestamp": "{{timenow}}",
}

CLOSE_TEMPLATE = {
    "event_type": "closed_manual",
    "trade_id": "{{ticker}}-OPEN_TRADE_ID_ERSETZEN",
    "symbol": "{{ticker}}",
    "timestamp": "{{timenow}}",
}


class TradingViewWebhookSetupTests(unittest.TestCase):
    def test_templates_must_exist_and_be_valid_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "price_heartbeat_alert_message.json").write_text(json.dumps(PRICE_TEMPLATE), encoding="utf-8")
            (root / "trade_opened_alert_message.json").write_text(json.dumps(OPEN_TEMPLATE), encoding="utf-8")
            (root / "trade_closed_manual_alert_message.json").write_text(json.dumps(CLOSE_TEMPLATE), encoding="utf-8")

            checks = template_checks(root)

        self.assertEqual({item["status"] for item in checks}, {"ok"})

    def test_readiness_is_local_ready_but_public_missing_without_tunnel_url(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            template_dir = root / "templates"
            template_dir.mkdir()
            (template_dir / "price_heartbeat_alert_message.json").write_text(json.dumps(PRICE_TEMPLATE), encoding="utf-8")
            (template_dir / "trade_opened_alert_message.json").write_text(json.dumps(OPEN_TEMPLATE), encoding="utf-8")
            (template_dir / "trade_closed_manual_alert_message.json").write_text(json.dumps(CLOSE_TEMPLATE), encoding="utf-8")
            env_file = root / ".env"
            env_file.write_text(
                "\n".join(
                    [
                        "TRADINGVIEW_WEBHOOK_LOCAL_PRICE_URL=http://127.0.0.1:8000/api/live-bridge/ingest",
                        "TRADINGVIEW_WEBHOOK_LOCAL_TRADE_URL=http://127.0.0.1:8000/api/trade-events/capture",
                    ]
                ),
                encoding="utf-8",
            )

            payload = readiness_payload(env_file, template_dir)

        self.assertEqual(payload["status"], "local_ready_public_missing")
        self.assertTrue(payload["local_endpoints"]["ready"])
        self.assertFalse(payload["public_endpoints"]["ready"])
        self.assertIn("oeffentliche HTTPS-URL", " ".join(payload["blockers"]))
        self.assertTrue(payload["information_only"])

    def test_public_webhook_url_validation_blocks_localhost(self):
        ok, message = public_webhook_url_check("http://127.0.0.1:8000/api/live-bridge/ingest")

        self.assertFalse(ok)
        self.assertIn("HTTPS", message)

    def test_public_webhook_url_validation_requires_gateway_route(self):
        direct_ok, direct_message = public_webhook_url_check("https://example.test/api/live-bridge/ingest")
        gateway_ok, gateway_message = public_webhook_url_check(f"https://example.test/tv/{TOKEN}/price")

        self.assertFalse(direct_ok)
        self.assertIn("Gateway", direct_message)
        self.assertTrue(gateway_ok)
        self.assertIn("geeignet", gateway_message)

    def test_endpoint_from_base_builds_tradingview_public_paths(self):
        self.assertEqual(
            endpoint_from_base("https://example.trycloudflare.com", "/api/live-bridge/ingest"),
            "https://example.trycloudflare.com/api/live-bridge/ingest",
        )
        self.assertEqual(
            endpoint_from_base("https://example.trycloudflare.com/tv", "/api/trade-events/capture"),
            "https://example.trycloudflare.com/tv/api/trade-events/capture",
        )

    def test_gateway_paths_are_token_protected_and_narrow(self):
        self.assertEqual(gateway_path_for("price", TOKEN), f"/tv/{TOKEN}/price")
        self.assertEqual(gateway_path_for("trade", TOKEN), f"/tv/{TOKEN}/trade")
        self.assertEqual(route_kind_from_path(f"/tv/{TOKEN}/price", TOKEN), "price")
        self.assertEqual(route_kind_from_path("/tv/wrong/price", TOKEN), "")
        self.assertIsNone(route_kind_from_path(f"/api/live-bridge/ingest", TOKEN))
        self.assertEqual(target_url_for("price"), "http://127.0.0.1:8000/api/live-bridge/ingest")

    def test_gateway_endpoints_from_base_use_token_routes(self):
        price, trade = gateway_endpoints_from_base("https://example.trycloudflare.com", TOKEN)

        self.assertEqual(price, f"https://example.trycloudflare.com/tv/{TOKEN}/price")
        self.assertEqual(trade, f"https://example.trycloudflare.com/tv/{TOKEN}/trade")
        self.assertEqual(
            kas_events_endpoint_from_base("https://example.test/wb-bridge", TOKEN),
            f"https://example.test/wb-bridge/tv/{TOKEN}/events",
        )
        self.assertEqual(
            worker_events_endpoint_from_base("https://example.worker.dev", TOKEN),
            f"https://example.worker.dev/tv/{TOKEN}/events",
        )

    def test_update_env_text_replaces_existing_keys_and_appends_missing(self):
        result = update_env_text(
            "A=1\nTRADINGVIEW_WEBHOOK_PUBLIC_PRICE_URL=\n",
            {
                "TRADINGVIEW_WEBHOOK_PUBLIC_PRICE_URL": f"https://example.test/tv/{TOKEN}/price",
                "TRADINGVIEW_WEBHOOK_PUBLIC_TRADE_URL": f"https://example.test/tv/{TOKEN}/trade",
            },
        )

        self.assertIn(f"TRADINGVIEW_WEBHOOK_PUBLIC_PRICE_URL=https://example.test/tv/{TOKEN}/price", result)
        self.assertIn(f"TRADINGVIEW_WEBHOOK_PUBLIC_TRADE_URL=https://example.test/tv/{TOKEN}/trade", result)
        self.assertIn("A=1", result)

    def test_register_public_webhooks_writes_env_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            env_file = Path(tmp) / ".env"
            env_file.write_text("LIVE_TRADING_ENABLED=false\n", encoding="utf-8")

            payload = register_public_webhooks(
                env_file=env_file,
                price_url=f"https://example.test/tv/{TOKEN}/price",
                trade_url=f"https://example.test/tv/{TOKEN}/trade",
                kas_events_url=f"https://example.test/tv/{TOKEN}/events",
                worker_events_url=f"https://worker.example/tv/{TOKEN}/events",
            )
            text = env_file.read_text(encoding="utf-8")

        self.assertEqual(payload["status"], "registriert")
        self.assertIn(f"TRADINGVIEW_WEBHOOK_PUBLIC_PRICE_URL=https://example.test/tv/{TOKEN}/price", text)
        self.assertIn(f"TRADINGVIEW_WEBHOOK_PUBLIC_TRADE_URL=https://example.test/tv/{TOKEN}/trade", text)
        self.assertIn(f"KAS_WEBHOOK_BRIDGE_EVENTS_URL=https://example.test/tv/{TOKEN}/events", text)
        self.assertIn(f"CLOUDFLARE_WORKER_BRIDGE_EVENTS_URL=https://worker.example/tv/{TOKEN}/events", text)
        self.assertEqual(payload["public_endpoints"]["price"], "https://example.test/tv/.../price")
        self.assertEqual(payload["public_endpoints"]["trade"], "https://example.test/tv/.../trade")
        self.assertEqual(payload["public_endpoints"]["kas_events"], "https://example.test/tv/.../events")
        self.assertEqual(payload["public_endpoints"]["cloudflare_worker_events"], "https://worker.example/tv/.../events")
        self.assertIn("keine Orderausfuehrung", payload["disclaimer"])


if __name__ == "__main__":
    unittest.main()
