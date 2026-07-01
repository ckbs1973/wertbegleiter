from datetime import datetime, timezone
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from run_realtime_update_service import chat_context_snapshot


class RealtimeUpdateServiceTests(unittest.TestCase):
    def test_chat_context_snapshot_marks_complete_feed_connected(self):
        now = datetime(2026, 6, 29, 20, 0, tzinfo=timezone.utc)
        snapshot = chat_context_snapshot(
            {
                "covered_required_chat_count": 4,
                "required_chat_count": 4,
                "missing_required_chats": [],
                "coverage_status": "vollstaendig",
                "update_count": 109,
                "extra_update_count": 1,
                "chat_coverage": [
                    {"required": True, "latest_timestamp": "29.06.2026 20:36"},
                ],
            },
            now=now,
            stale_after_seconds=15,
        )

        self.assertEqual(snapshot["source_name"], "ChatGPT Update Feed")
        self.assertEqual(snapshot["category"], "chat_context")
        self.assertEqual(snapshot["connection_state"], "connected")
        self.assertEqual(snapshot["item_count"], 109)
        self.assertIn("Pflicht-Update-Chats 4/4", snapshot["details"])
        self.assertIn("keine Orderausfuehrung", " ".join(snapshot["details"]))

    def test_chat_context_snapshot_marks_missing_required_chats_error(self):
        snapshot = chat_context_snapshot(
            {
                "covered_required_chat_count": 3,
                "required_chat_count": 4,
                "missing_required_chats": ["US open update and trade scenarios"],
                "coverage_status": "unvollstaendig",
                "update_count": 80,
            },
            now=datetime(2026, 6, 29, 20, 0, tzinfo=timezone.utc),
        )

        self.assertEqual(snapshot["connection_state"], "error")
        self.assertTrue(any("Fehlende Pflicht-Chats" in item for item in snapshot["details"]))


if __name__ == "__main__":
    unittest.main()
