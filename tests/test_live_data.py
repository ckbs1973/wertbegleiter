from datetime import datetime, timedelta, timezone
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from trading_freaks.api.routes import evaluate_live_status_payload
from trading_freaks.live_data import (
    LiveFeedStatus,
    LiveSourceSnapshot,
    evaluate_live_feed_status,
)


class LiveDataFreshnessTests(unittest.TestCase):
    def test_all_sources_inside_freshness_window_are_second_fresh(self):
        now = datetime(2026, 6, 29, 18, 0, 5, tzinfo=timezone.utc)
        sources = [
            LiveSourceSnapshot(
                source_name="TradingView prices",
                category="price",
                observed_at=now,
                source_timestamp=now - timedelta(seconds=2),
                stale_after_seconds=5,
                connection_state="connected",
                item_count=12,
            ),
            LiveSourceSnapshot(
                source_name="Squawk",
                category="news",
                observed_at=now,
                source_timestamp=now - timedelta(seconds=20),
                stale_after_seconds=60,
                connection_state="connected",
                item_count=3,
            ),
        ]

        status = evaluate_live_feed_status(sources, now=now)

        self.assertEqual(status.overall_status, "second_fresh")
        self.assertEqual(status.live_source_count, 2)
        self.assertEqual(status.missing_source_count, 0)
        self.assertTrue(all(item.status == "live" for item in status.evaluations))

    def test_stale_price_feed_blocks_second_fresh_status(self):
        now = datetime(2026, 6, 29, 18, 0, 10, tzinfo=timezone.utc)
        source = LiveSourceSnapshot(
            source_name="TradingView prices",
            category="price",
            observed_at=now,
            source_timestamp=now - timedelta(seconds=8),
            stale_after_seconds=5,
            connection_state="connected",
        )

        status = evaluate_live_feed_status([source], now=now)

        self.assertEqual(status.overall_status, "not_live")
        self.assertEqual(status.stale_source_count, 1)
        self.assertEqual(status.evaluations[0].status, "stale")
        self.assertIn("Frischegrenze", " ".join(status.warnings))

    def test_missing_required_sources_are_not_live(self):
        response = evaluate_live_status_payload({})

        self.assertEqual(response["status"], "not_live")
        live_status = response["live_status"]
        self.assertGreaterEqual(live_status["missing_source_count"], 1)
        self.assertIn("keine Anlageberatung", response["disclaimer"])

    def test_information_only_cannot_be_disabled(self):
        now = datetime(2026, 6, 29, 18, 0, tzinfo=timezone.utc)

        with self.assertRaises(ValueError):
            LiveFeedStatus(
                generated_at=now,
                overall_status="second_fresh",
                live_source_count=1,
                stale_source_count=0,
                missing_source_count=0,
                max_age_seconds=1,
                evaluations=(),
                warnings=(),
                information_only=False,
            )


if __name__ == "__main__":
    unittest.main()
