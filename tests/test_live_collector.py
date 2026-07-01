from datetime import datetime, timedelta, timezone
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from trading_freaks.live_collector import (
    ensure_required_categories,
    evaluate_sources,
    ingest_source_heartbeat,
    upsert_snapshot_payload,
    write_live_status_file,
)
from trading_freaks.live_data import LiveSourceSnapshot


class LiveCollectorTests(unittest.TestCase):
    def test_required_categories_are_added_when_bridge_only_sends_prices(self):
        now = datetime(2026, 6, 29, 18, 0, tzinfo=timezone.utc)
        price = LiveSourceSnapshot(
            source_name="TradingView/Broker Kurse",
            category="price",
            observed_at=now,
            source_timestamp=now,
            connection_state="connected",
        )

        sources = ensure_required_categories([price], now=now)

        self.assertEqual({source.category for source in sources}, {"price", "order", "calendar", "news"})
        self.assertEqual(len([source for source in sources if source.category == "price"]), 1)

    def test_partial_live_status_when_only_one_required_source_is_connected(self):
        now = datetime(2026, 6, 29, 18, 0, tzinfo=timezone.utc)
        price = LiveSourceSnapshot(
            source_name="TradingView/Broker Kurse",
            category="price",
            observed_at=now,
            source_timestamp=now - timedelta(seconds=1),
            connection_state="connected",
        )

        status = evaluate_sources([price], now=now)

        self.assertEqual(status.overall_status, "partly_live")
        self.assertEqual(status.live_source_count, 1)
        self.assertEqual(status.missing_source_count, 3)

    def test_upsert_snapshot_replaces_same_source(self):
        now = datetime(2026, 6, 29, 18, 0, tzinfo=timezone.utc)
        payload = upsert_snapshot_payload(
            None,
            {"source_name": "Squawk", "category": "news", "item_count": 1},
            now=now,
        )
        payload = upsert_snapshot_payload(
            payload,
            {"source_name": "Squawk", "category": "news", "item_count": 2, "details": ["new"]},
            now=now + timedelta(seconds=1),
        )

        self.assertEqual(len(payload["sources"]), 1)
        self.assertEqual(payload["sources"][0]["item_count"], 2)
        self.assertEqual(payload["sources"][0]["details"], ["new"])

    def test_write_live_status_file_is_json_serializable(self):
        now = datetime(2026, 6, 29, 18, 0, tzinfo=timezone.utc)
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "live_feed_status.json"
            status = write_live_status_file(output, (), now=now)
            payload = json.loads(output.read_text(encoding="utf-8"))

        self.assertEqual(status.overall_status, "not_live")
        self.assertEqual(payload["live_status"]["overall_status"], "not_live")
        self.assertIn("keine Anlageberatung", payload["disclaimer"])

    def test_ingest_source_heartbeat_updates_sources_and_status(self):
        now = datetime(2026, 6, 29, 18, 0, tzinfo=timezone.utc)
        with tempfile.TemporaryDirectory() as tmp:
            source_file = Path(tmp) / "live_source_snapshots.json"
            status_file = Path(tmp) / "live_feed_status.json"
            sources_payload, status = ingest_source_heartbeat(
                source_file,
                status_file,
                {
                    "source_name": "TradingView/Broker Kurse",
                    "category": "price",
                    "connection_state": "connected",
                    "item_count": 1,
                    "details": ["Bridge-Heartbeat"],
                },
                now=now,
            )
            status_payload = json.loads(status_file.read_text(encoding="utf-8"))
            source_file_exists = source_file.exists()

        self.assertTrue(source_file_exists)
        self.assertEqual(sources_payload["sources"][0]["category"], "price")
        self.assertEqual(status.overall_status, "partly_live")
        self.assertEqual(status_payload["live_status"]["live_source_count"], 1)
        self.assertEqual(status_payload["live_status"]["missing_source_count"], 3)


if __name__ == "__main__":
    unittest.main()
