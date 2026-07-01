import json
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

from pull_kas_webhook_bridge import events_url_from_price_or_trade_url, events_url_with_cursor
from trading_freaks.kas_bridge import process_kas_bridge_events


class KasBridgeTests(unittest.TestCase):
    def test_events_url_can_be_derived_from_public_price_url(self):
        url = events_url_from_price_or_trade_url("https://wertbegleiter.eu/wb/tv/abcdefghijklmnopqrstuvwxyz123456/price")

        self.assertEqual(url, "https://wertbegleiter.eu/wb/tv/abcdefghijklmnopqrstuvwxyz123456/events")
        self.assertEqual(
            events_url_with_cursor(url, since=7, limit=50),
            "https://wertbegleiter.eu/wb/tv/abcdefghijklmnopqrstuvwxyz123456/events?since=7&limit=50",
        )

    def test_kas_price_and_trade_events_update_live_status_and_journal_store(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source_path = root / "live_source_snapshots.json"
            status_path = root / "live_feed_status.json"
            journal_store = root / "journal_live_store.json"
            now = datetime.now(timezone.utc).isoformat()

            results = process_kas_bridge_events(
                [
                    {
                        "sequence": 1,
                        "kind": "price",
                        "received_at": now,
                        "payload": {
                            "bridge_type": "price",
                            "symbol": "BTCUSD",
                            "last": 60447.98,
                            "timestamp": now,
                        },
                    },
                    {
                        "sequence": 2,
                        "kind": "trade",
                        "received_at": now,
                        "payload": {
                            "event_type": "opened",
                            "source": "tradingview_webhook",
                            "trade_id": "btc-test-1",
                            "symbol": "BTCUSD",
                            "market": "crypto",
                            "timestamp": now,
                            "direction": "long",
                            "entry": 60000,
                            "stop_loss": 59500,
                            "take_profit": 61000,
                            "size": 0.1,
                        },
                    },
                    {
                        "sequence": 3,
                        "kind": "trade",
                        "received_at": now,
                        "payload": {
                            "event_type": "closed_take_profit",
                            "source": "tradingview_webhook",
                            "trade_id": "btc-test-1",
                            "symbol": "BTCUSD",
                            "market": "crypto",
                            "timestamp": now,
                            "exit_price": 61000,
                        },
                    },
                ],
                source_path=source_path,
                status_path=status_path,
                journal_store_path=journal_store,
            )
            store = json.loads(journal_store.read_text(encoding="utf-8"))
            status = json.loads(status_path.read_text(encoding="utf-8"))

        self.assertEqual([item.status for item in results], ["live_status_updated", "journal_updated", "journal_updated"])
        self.assertEqual(len(store["journal_drafts"]), 1)
        draft = store["journal_drafts"][0]
        self.assertEqual(draft["symbol"], "BTCUSD")
        self.assertEqual(draft["lifecycle_status"], "closed")
        self.assertEqual(draft["exit_reason"], "Take Profit")
        self.assertEqual(draft["realized_r"], 2.0)
        self.assertTrue(draft["information_only"])
        self.assertEqual(status["live_status"]["live_source_count"], 2)

    def test_close_event_without_open_trade_is_preserved_for_review(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            process_kas_bridge_events(
                [
                    {
                        "sequence": 1,
                        "kind": "trade",
                        "received_at": "2026-07-01T08:20:00+00:00",
                        "payload": {
                            "event_type": "closed_stop_loss",
                            "source": "tradingview_webhook",
                            "trade_id": "missing-open",
                            "symbol": "BTCUSD",
                            "market": "crypto",
                            "timestamp": "2026-07-01T08:20:00+00:00",
                            "exit_price": 59500,
                        },
                    },
                ],
                source_path=root / "sources.json",
                status_path=root / "status.json",
                journal_store_path=root / "journal.json",
            )
            store = json.loads((root / "journal.json").read_text(encoding="utf-8"))

        self.assertEqual(store["journal_drafts"][0]["status"], "Review offen")
        self.assertEqual(store["journal_drafts"][0]["exit_reason"], "Stop Loss")
        self.assertIsNone(store["journal_drafts"][0]["realized_r"])
        self.assertIn("ohne offenen Journal-Entwurf", store["journal_drafts"][0]["review"])


if __name__ == "__main__":
    unittest.main()
