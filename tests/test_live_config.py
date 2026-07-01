import tempfile
import unittest
from pathlib import Path

from trading_freaks.live_config import (
    adapter_config_status,
    adapter_config_status_from_env_file,
    masked_location,
)


class LiveConfigTests(unittest.TestCase):
    def test_missing_env_marks_all_required_adapters_missing(self):
        status = adapter_config_status({}, env_file_exists=False)

        self.assertFalse(status["env_file"]["exists"])
        self.assertEqual(status["configured_count"], 0)
        self.assertEqual(status["missing_count"], 4)
        self.assertTrue(all(item["status"] == "missing_config" for item in status["adapters"]))
        self.assertTrue(status["information_only"])

    def test_configured_local_file_reports_file_existence_without_full_secret_dump(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            price = root / "price.json"
            price.write_text('{"bridge_type":"price","symbol":"BTCUSD","last":1}', encoding="utf-8")
            env_file = root / ".env"
            env_file.write_text(f"LIVE_PRICE_JSON_PATH={price}\n", encoding="utf-8")

            status = adapter_config_status_from_env_file(env_file)

        price_adapter = next(item for item in status["adapters"] if item["env_key"] == "LIVE_PRICE_JSON_PATH")
        self.assertTrue(status["env_file"]["exists"])
        self.assertEqual(price_adapter["status"], "configured")
        self.assertTrue(price_adapter["file_exists"])
        self.assertEqual(price_adapter["location_masked"], ".../price.json")
        self.assertNotIn(str(price.parent), price_adapter["location_masked"])

    def test_relative_env_paths_are_resolved_from_env_file_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source_dir = root / "sources"
            source_dir.mkdir()
            price = source_dir / "price.json"
            price.write_text('{"bridge_type":"price","symbol":"BTCUSD","last":1}', encoding="utf-8")
            env_file = root / ".env"
            env_file.write_text("LIVE_PRICE_JSON_PATH=sources/price.json\n", encoding="utf-8")

            status = adapter_config_status_from_env_file(env_file)

        price_adapter = next(item for item in status["adapters"] if item["env_key"] == "LIVE_PRICE_JSON_PATH")
        self.assertEqual(price_adapter["status"], "configured")
        self.assertTrue(price_adapter["file_exists"])
        self.assertEqual(price_adapter["location_masked"], ".../price.json")

    def test_provider_specific_news_fallback_marks_news_configured(self):
        status = adapter_config_status(
            {"FOREXLIVE_RSS_URL": "https://investinglive.com/feed/"},
            env_file_exists=True,
        )

        news_adapter = next(item for item in status["adapters"] if item["env_key"] == "LIVE_NEWS_FEED_URL")
        self.assertEqual(news_adapter["status"], "configured")
        self.assertEqual(news_adapter["configured_env_key"], "FOREXLIVE_RSS_URL")
        self.assertIn("FOREXLIVE_RSS_URL", news_adapter["env_keys"])
        self.assertEqual(news_adapter["location_kind"], "url")
        self.assertEqual(news_adapter["location_masked"], "https://investinglive.com/feed/")

    def test_worker_bridge_marks_price_and_order_configured(self):
        status = adapter_config_status(
            {"CLOUDFLARE_WORKER_BRIDGE_EVENTS_URL": "https://worker.example/tv/token/events"},
            env_file_exists=True,
        )

        price_adapter = next(item for item in status["adapters"] if item["env_key"] == "LIVE_PRICE_JSON_PATH")
        order_adapter = next(item for item in status["adapters"] if item["env_key"] == "LIVE_ORDER_JSON_PATH")
        self.assertEqual(price_adapter["status"], "configured")
        self.assertEqual(order_adapter["status"], "configured")
        self.assertEqual(price_adapter["configured_env_key"], "CLOUDFLARE_WORKER_BRIDGE_EVENTS_URL")
        self.assertEqual(order_adapter["configured_env_key"], "CLOUDFLARE_WORKER_BRIDGE_EVENTS_URL")
        self.assertEqual(status["missing_count"], 2)

    def test_url_masking_removes_query_string(self):
        masked = masked_location("https://example.test/feed.xml?token=secret")

        self.assertEqual(masked, "https://example.test/feed.xml")
        self.assertNotIn("secret", masked)

    def test_url_masking_hides_tradingview_gateway_token(self):
        masked = masked_location("https://example.test/tv/abcdefghijklmnopqrstuvwxyz123456/price")

        self.assertEqual(masked, "https://example.test/tv/.../price")
        self.assertNotIn("abcdefghijklmnopqrstuvwxyz123456", masked)


if __name__ == "__main__":
    unittest.main()
