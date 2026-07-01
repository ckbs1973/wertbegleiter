import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from build_chatgpt_update_feed import build_feed


class ChatGptUpdateFeedTests(unittest.TestCase):
    def test_required_update_chats_are_explicitly_covered(self):
        feed = build_feed()

        self.assertEqual(feed["required_chat_count"], 4)
        self.assertEqual(feed["covered_required_chat_count"], 4)
        self.assertEqual(feed["coverage_status"], "vollstaendig")
        self.assertEqual(feed["missing_required_chats"], [])
        self.assertIn("keine Anlageberatung", feed["disclaimer"])

        required_titles = {
            item["canonical_title"]
            for item in feed["chat_coverage"]
            if item["required"]
        }
        self.assertEqual(
            required_titles,
            {
                "Trading Update Daily",
                "Taegliches Marktupdate und Trading-Setups",
                "US open update and trade scenarios",
                "Europe session update and trade scenarios",
            },
        )

    def test_optional_breaking_news_context_is_not_counted_as_required(self):
        feed = build_feed()
        optional_titles = {
            item["canonical_title"]
            for item in feed["chat_coverage"]
            if not item["required"]
        }

        self.assertIn("Breaking news update: oil, yen, tech insights", optional_titles)
        self.assertNotIn("Breaking news update: oil, yen, tech insights", feed["required_update_chats"])


if __name__ == "__main__":
    unittest.main()
