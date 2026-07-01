import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from trading_freaks.api.routes import (
    capture_live_source_heartbeat_payload,
    capture_trade_event_payload,
    evaluate_us_news_breakout_payload,
    ingest_live_bridge_payload,
    read_journal_store_payload,
    save_journal_store_payload,
    validate_journal_capture_payload,
)


def valid_payload():
    return {
        "candidate": {
            "symbol": "EXAMPLE",
            "direction": "long",
            "daily_volume": 2_000_000,
            "is_penny_stock": False,
            "has_news_catalyst": True,
            "news_is_mixed": False,
            "gap_percent": 4.0,
            "main_session_started": True,
            "momentum_in_news_direction_by_1545": True,
            "price_on_correct_vwap_side": True,
            "consolidation_minutes": 6,
            "consolidation_is_tight": True,
            "correction_fraction_of_momentum": 0.25,
            "pattern_type": "flag",
            "rvol": 1.8,
            "rvol_anticipated": False,
            "entry_is_near_breakout": True,
            "movement_is_momentum_not_volatility": True,
            "close_by_end_of_day_planned": True,
        },
        "risk": {
            "account_equity": 10_000,
            "risk_percent": 1.0,
            "entry": 101.0,
            "stop_loss": 100.0,
            "take_profit": 102.0,
            "unit_value": 1.0,
        },
    }


class ApiRouteTests(unittest.TestCase):
    def test_us_news_breakout_route_returns_manual_review_status(self):
        response = evaluate_us_news_breakout_payload(valid_payload())

        self.assertEqual(response["status"], "trade_erlaubt_zur_manuellen_pruefung")
        self.assertTrue(response["validation"]["trade_allowed"])
        self.assertIn("keine Anlageberatung", response["disclaimer"])

    def test_us_news_breakout_route_blocks_missing_fields(self):
        payload = valid_payload()
        del payload["candidate"]["has_news_catalyst"]

        response = evaluate_us_news_breakout_payload(payload)

        self.assertEqual(response["status"], "nicht_handeln")
        self.assertIn("Pflichtfeld fehlt: has_news_catalyst", response["errors"])

    def test_journal_capture_route_requires_emotions_and_screenshots(self):
        response = validate_journal_capture_payload(
            {
                "emotion_before": "",
                "emotion_during": "focused",
                "emotion_after": "calm",
                "criteria_met": ["News"],
                "criteria_failed": [],
                "screenshot_before": "before.bmp",
                "screenshot_after": "",
                "rule_compliant": False,
                "violated_rule": "",
                "realized_r": None,
                "review": "",
            }
        )

        self.assertEqual(response["status"], "journal_unvollstaendig")
        fields = [issue["field"] for issue in response["issues"]]
        self.assertIn("emotion_before", fields)
        self.assertIn("screenshot_before", fields)
        self.assertIn("screenshot_after", fields)
        self.assertIn("violated_rule", fields)
        self.assertIn("realized_r", fields)

    def test_trade_event_open_starts_journal_draft(self):
        response = capture_trade_event_payload(
            {
                "event_type": "opened",
                "source": "tradingview_webhook",
                "trade_id": "btc-paper-1",
                "symbol": "BTCUSD",
                "market": "crypto",
                "timestamp": "2026-06-27T10:15:00+02:00",
                "direction": "long",
                "entry": 60000,
                "stop_loss": 59500,
                "take_profit": 61000,
                "size": 0.1,
                "screenshot_path": "screenshots/btc-before.png",
            }
        )

        self.assertEqual(response["status"], "trade_event_verarbeitet")
        action = response["event_action"]
        self.assertEqual(action["action"], "start_journal_draft")
        self.assertEqual(action["journal_patch"]["symbol"], "BTCUSD")
        self.assertEqual(action["journal_patch"]["screenshot_before"], "screenshots/btc-before.png")
        self.assertTrue(action["information_only"])

    def test_trade_event_close_updates_existing_journal_draft(self):
        response = capture_trade_event_payload(
            {
                "event": {
                    "event_type": "closed_take_profit",
                    "source": "broker_webhook",
                    "trade_id": "btc-paper-1",
                    "symbol": "BTCUSD",
                    "market": "crypto",
                    "timestamp": "2026-06-27T11:05:00+02:00",
                    "exit_price": 61000,
                    "fees": 2.5,
                    "slippage": 1.0,
                    "screenshot_path": "screenshots/btc-after.png",
                },
                "open_trade": {
                    "entry": 60000,
                    "stop_loss": 59500,
                    "direction": "long",
                },
            }
        )

        self.assertEqual(response["status"], "trade_event_verarbeitet")
        action = response["event_action"]
        self.assertEqual(action["action"], "close_journal_draft")
        self.assertEqual(action["journal_patch"]["exit_reason"], "Take Profit")
        self.assertEqual(action["journal_patch"]["realized_r"], 2.0)
        self.assertEqual(action["journal_patch"]["screenshot_after"], "screenshots/btc-after.png")

    def test_live_source_heartbeat_route_writes_status_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            source_path = Path(tmp) / "live_source_snapshots.json"
            status_path = Path(tmp) / "live_feed_status.json"
            response = capture_live_source_heartbeat_payload(
                {
                    "source_name": "News/Squawk/X Pro",
                    "category": "news",
                    "connection_state": "connected",
                    "item_count": 3,
                    "details": ["News heartbeat"],
                },
                source_path=source_path,
                status_path=status_path,
            )

        self.assertEqual(response["status"], "live_source_aktualisiert")
        self.assertEqual(response["source_count"], 1)
        self.assertEqual(response["live_status"]["overall_status"], "partly_live")
        self.assertIn("keine Anlageberatung", response["disclaimer"])

    def test_live_source_heartbeat_route_blocks_missing_fields(self):
        response = capture_live_source_heartbeat_payload({"source_name": "Unvollstaendig"})

        self.assertEqual(response["status"], "nicht_live")
        self.assertIn("Pflichtfeld fehlt: category", response["errors"])

    def test_live_bridge_route_accepts_simple_price_payload(self):
        with tempfile.TemporaryDirectory() as tmp:
            source_path = Path(tmp) / "live_source_snapshots.json"
            status_path = Path(tmp) / "live_feed_status.json"
            response = ingest_live_bridge_payload(
                {
                    "bridge_type": "price",
                    "symbol": "BTCUSD",
                    "last": 60447.98,
                },
                source_path=source_path,
                status_path=status_path,
            )

        self.assertEqual(response["status"], "live_bridge_aktualisiert")
        self.assertEqual(response["processed"][0]["category"], "price")
        self.assertIn("keine Anlageberatung", response["disclaimer"])

    def test_journal_store_roundtrip_persists_live_drafts_without_orders(self):
        with tempfile.TemporaryDirectory() as tmp:
            store_path = Path(tmp) / "journal_live_store.json"
            save_response = save_journal_store_payload(
                {
                    "active_journal_draft_id": "draft-1",
                    "journal_drafts": [
                        {
                            "draft_id": "draft-1",
                            "symbol": "btcusd",
                            "account_mode": "live",
                            "lifecycle_status": "open",
                            "entry": "60000",
                            "stop_loss": "59500",
                            "take_profit": "61000",
                        }
                    ],
                },
                store_path=store_path,
            )
            read_response = read_journal_store_payload(store_path=store_path)

        self.assertEqual(save_response["status"], "journal_store_gespeichert")
        self.assertEqual(read_response["status"], "journal_store_geladen")
        self.assertEqual(read_response["draft_count"], 1)
        draft = read_response["journal_store"]["journal_drafts"][0]
        self.assertEqual(draft["symbol"], "BTCUSD")
        self.assertEqual(draft["account_mode"], "live")
        self.assertTrue(draft["information_only"])
        self.assertIn("keine Orderausfuehrung", read_response["disclaimer"])

    def test_journal_store_write_creates_backup_on_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            store_path = Path(tmp) / "journal_live_store.json"
            first = save_journal_store_payload(
                {"journal_drafts": [{"draft_id": "draft-1", "symbol": "NVDA"}]},
                store_path=store_path,
            )
            second = save_journal_store_payload(
                {"journal_drafts": [{"draft_id": "draft-2", "symbol": "TSLA"}]},
                store_path=store_path,
            )
            backups = list(Path(tmp).glob("journal_live_store.*.bak.json"))

        self.assertEqual(first["status"], "journal_store_gespeichert")
        self.assertEqual(second["status"], "journal_store_gespeichert")
        self.assertEqual(second["draft_count"], 1)
        self.assertEqual(len(backups), 1)


if __name__ == "__main__":
    unittest.main()
