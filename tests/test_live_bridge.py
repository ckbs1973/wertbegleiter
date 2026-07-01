from datetime import datetime, timezone
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

from run_live_bridge_inbox import process_inbox_once
from trading_freaks.live_bridge import bridge_payload_to_snapshot, ingest_bridge_payload


class LiveBridgeTests(unittest.TestCase):
    def test_price_payload_becomes_canonical_price_heartbeat(self):
        now = datetime(2026, 6, 29, 18, 0, tzinfo=timezone.utc)

        snapshot = bridge_payload_to_snapshot(
            {
                "bridge_type": "price",
                "symbol": "btcusd",
                "last": 60447.98,
                "timestamp": "2026-06-29T18:00:00+00:00",
            },
            now=now,
        )

        self.assertEqual(snapshot["source_name"], "TradingView/Broker Kurse")
        self.assertEqual(snapshot["category"], "price")
        self.assertEqual(snapshot["connection_state"], "connected")
        self.assertEqual(snapshot["item_count"], 1)
        self.assertIn("Symbol BTCUSD", snapshot["details"])
        self.assertIn("keine Orderausfuehrung", " ".join(snapshot["details"]))

    def test_all_required_bridge_categories_can_be_second_fresh(self):
        now = datetime(2026, 6, 29, 18, 0, tzinfo=timezone.utc)
        payload = {
            "payloads": [
                {"bridge_type": "price", "symbol": "BTCUSD", "last": 60447.98, "timestamp": now.isoformat()},
                {"bridge_type": "order", "event_type": "opened", "trade_id": "paper-1", "symbol": "BTCUSD", "timestamp": now.isoformat()},
                {"bridge_type": "calendar", "events": [{"title": "US PCE", "impact": "high"}], "timestamp": now.isoformat()},
                {"bridge_type": "news", "items": [{"headline": "Squawk heartbeat"}], "timestamp": now.isoformat()},
            ]
        }

        with tempfile.TemporaryDirectory() as tmp:
            source_path = Path(tmp) / "live_source_snapshots.json"
            status_path = Path(tmp) / "live_feed_status.json"
            results = ingest_bridge_payload(payload, source_path=source_path, status_path=status_path, now=now)
            status_payload = json.loads(status_path.read_text(encoding="utf-8"))

        self.assertEqual(len(results), 4)
        self.assertEqual(status_payload["live_status"]["overall_status"], "second_fresh")
        self.assertEqual(status_payload["live_status"]["live_source_count"], 4)
        self.assertEqual(status_payload["live_status"]["missing_source_count"], 0)

    def test_inbox_runner_processes_changed_files_once(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            inbox = root / "inbox"
            state = root / "state.json"
            source_path = root / "live_source_snapshots.json"
            status_path = root / "live_feed_status.json"
            inbox.mkdir()
            payload_file = inbox / "price.json"
            payload_file.write_text(
                json.dumps({"bridge_type": "price", "symbol": "BTCUSD", "last": 60447.98}),
                encoding="utf-8",
            )

            first = process_inbox_once(
                inbox=inbox,
                state_file=state,
                source_path=source_path,
                status_path=status_path,
            )
            second = process_inbox_once(
                inbox=inbox,
                state_file=state,
                source_path=source_path,
                status_path=status_path,
            )

        self.assertEqual(len(first), 1)
        self.assertEqual(first[0]["status"], "processed")
        self.assertEqual(second, [])


if __name__ == "__main__":
    unittest.main()
