import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

from pull_cloudflare_worker_bridge import configured_events_url
from pull_kas_webhook_bridge import events_url_from_price_or_trade_url


class CloudflareWorkerBridgeTests(unittest.TestCase):
    def test_configured_events_url_prefers_worker_bridge_key(self):
        url = configured_events_url(
            {
                "CLOUDFLARE_WORKER_BRIDGE_EVENTS_URL": "https://worker.example/tv/token/events",
                "TRADINGVIEW_WEBHOOK_PUBLIC_PRICE_URL": "https://old.example/tv/token/price",
            }
        )

        self.assertEqual(url, "https://worker.example/tv/token/events")

    def test_configured_events_url_can_derive_from_public_webhook(self):
        url = configured_events_url({"TRADINGVIEW_WEBHOOK_PUBLIC_TRADE_URL": "https://worker.example/tv/token/trade"})

        self.assertEqual(url, "https://worker.example/tv/token/events")

    def test_events_url_derivation_requires_tradingview_route(self):
        with self.assertRaises(ValueError):
            events_url_from_price_or_trade_url("https://worker.example/api/live-bridge/ingest")


if __name__ == "__main__":
    unittest.main()
