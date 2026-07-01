import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

from run_configured_live_adapters import collect_once, load_env_file
from trading_freaks.live_adapters import (
    AdapterSource,
    configured_sources_from_env,
    payload_from_adapter_text,
    read_adapter_payload,
)


RSS_SAMPLE = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Market News</title>
    <item>
      <title>Fed speaker headline</title>
      <link>https://example.test/fed</link>
      <pubDate>Mon, 29 Jun 2026 18:00:00 GMT</pubDate>
    </item>
  </channel>
</rss>
"""


class LiveAdaptersTests(unittest.TestCase):
    def test_rss_feed_becomes_news_payload(self):
        source = AdapterSource(name="News/Squawk/X Pro", bridge_type="news", location="memory://rss")

        payload = payload_from_adapter_text(source, RSS_SAMPLE)

        self.assertEqual(payload["bridge_type"], "news")
        self.assertEqual(payload["source_name"], "News/Squawk/X Pro")
        self.assertEqual(payload["item_count"], 1)
        self.assertEqual(payload["items"][0]["headline"], "Fed speaker headline")

    def test_json_file_payload_preserves_bridge_type(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "calendar.json"
            path.write_text(json.dumps({"events": [{"title": "US PCE"}]}), encoding="utf-8")
            source = AdapterSource(name="Wirtschaftskalender", bridge_type="calendar", location=str(path))

            payload = read_adapter_payload(source)

        self.assertEqual(payload["bridge_type"], "calendar")
        self.assertEqual(payload["source_name"], "Wirtschaftskalender")
        self.assertEqual(payload["events"][0]["title"], "US PCE")

    def test_env_file_configures_sources_and_collects_once(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            price = root / "price.json"
            price.write_text(json.dumps({"symbol": "BTCUSD", "last": 60447.98}), encoding="utf-8")
            env_file = root / ".env"
            env_file.write_text(f"LIVE_PRICE_JSON_PATH={price}\n", encoding="utf-8")
            sources = configured_sources_from_env(load_env_file(env_file))

            results = collect_once(
                sources,
                source_path=root / "live_source_snapshots.json",
                status_path=root / "live_feed_status.json",
            )

        self.assertEqual(len(sources), 1)
        self.assertEqual(results[0]["status"], "processed")
        self.assertEqual(results[0]["bridge_type"], "price")

    def test_provider_specific_news_fallback_configures_adapter(self):
        sources = configured_sources_from_env(
            {
                "FOREXLIVE_RSS_URL": "https://investinglive.com/feed/",
                "LIVE_ADAPTER_TIMEOUT_SECONDS": "5",
            }
        )

        self.assertEqual(len(sources), 1)
        self.assertEqual(sources[0].bridge_type, "news")
        self.assertEqual(sources[0].name, "ForexLive/InvestingLive RSS")
        self.assertEqual(sources[0].location, "https://investinglive.com/feed/")

    def test_generic_live_news_slot_wins_over_provider_fallback(self):
        sources = configured_sources_from_env(
            {
                "LIVE_NEWS_FEED_URL": "https://primary.example/feed.xml",
                "FOREXLIVE_RSS_URL": "https://investinglive.com/feed/",
            }
        )

        self.assertEqual(len(sources), 1)
        self.assertEqual(sources[0].name, "News/Squawk/X Pro")
        self.assertEqual(sources[0].location, "https://primary.example/feed.xml")

    def test_relative_env_file_paths_collect_once(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source_dir = root / "sources"
            source_dir.mkdir()
            price = source_dir / "price.json"
            price.write_text(json.dumps({"symbol": "BTCUSD", "last": 60447.98}), encoding="utf-8")
            env_file = root / ".env"
            env_file.write_text("LIVE_PRICE_JSON_PATH=sources/price.json\n", encoding="utf-8")
            sources = configured_sources_from_env(load_env_file(env_file))

            results = collect_once(
                sources,
                source_path=root / "live_source_snapshots.json",
                status_path=root / "live_feed_status.json",
            )

        self.assertEqual(len(sources), 1)
        self.assertEqual(results[0]["status"], "processed")
        self.assertTrue(Path(sources[0].location).is_absolute())

    def test_blocked_demo_sources_do_not_create_second_fresh_status(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name, bridge_type in (
                ("price.json", "price"),
                ("orders.json", "order"),
                ("calendar.json", "calendar"),
                ("news.json", "news"),
            ):
                (root / name).write_text(
                    json.dumps(
                        {
                            "bridge_type": bridge_type,
                            "connection_state": "blocked",
                            "item_count": 0,
                        }
                    ),
                    encoding="utf-8",
                )
            env_file = root / ".env"
            env_file.write_text(
                "\n".join(
                    [
                        "LIVE_PRICE_JSON_PATH=price.json",
                        "LIVE_ORDER_JSON_PATH=orders.json",
                        "LIVE_CALENDAR_JSON_PATH=calendar.json",
                        "LIVE_NEWS_FEED_URL=news.json",
                    ]
                ),
                encoding="utf-8",
            )
            sources = configured_sources_from_env(load_env_file(env_file))

            collect_once(
                sources,
                source_path=root / "live_source_snapshots.json",
                status_path=root / "live_feed_status.json",
            )
            status = json.loads((root / "live_feed_status.json").read_text(encoding="utf-8"))

        self.assertEqual(len(sources), 4)
        self.assertEqual(status["live_status"]["overall_status"], "not_live")
        self.assertEqual(status["live_status"]["live_source_count"], 0)
        self.assertEqual(status["live_status"]["missing_source_count"], 4)
        self.assertTrue(all(item["item_count"] == 0 for item in status["live_status"]["evaluations"]))


if __name__ == "__main__":
    unittest.main()
