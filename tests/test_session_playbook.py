import sys
import unittest
from datetime import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from trading_freaks.session_playbook import (
    IMPORTED_TRADING_PROJECT_RULES,
    imported_rule_summary_lines,
    session_for_time,
)


class SessionPlaybookTests(unittest.TestCase):
    def test_imported_rules_include_all_project_chats(self):
        rules = IMPORTED_TRADING_PROJECT_RULES

        self.assertIn("Trading Update Daily", rules.source_chats)
        self.assertIn("Breaking news update: oil, yen, tech insights", rules.source_chats)
        self.assertIn("US open update and trade scenarios", rules.source_chats)
        self.assertTrue(rules.information_only)

    def test_session_windows_match_daily_chat_playbook(self):
        self.assertEqual(session_for_time(time(10, 30)).name, "Europe Session ORB")
        self.assertEqual(session_for_time(time(15, 25)).name, "US Open Preparation")
        self.assertEqual(session_for_time(time(16, 45)).name, "US Momentum Window")
        self.assertIsNone(session_for_time(time(21, 0)))

    def test_news_playbook_requires_timestamp_and_no_order_language(self):
        news = IMPORTED_TRADING_PROJECT_RULES.news_playbook

        self.assertIn("Europe/Berlin", news.required_timestamp_format)
        self.assertIn("Datum und Uhrzeit", " ".join(news.mandatory_filters))
        self.assertIn("keine Orderfreigabe", news.forbidden_behaviors)
        self.assertIn("keine Kauf-/Verkaufsempfehlung", news.forbidden_behaviors)

    def test_xagusd_and_metals_rules_are_mandatory(self):
        rules = IMPORTED_TRADING_PROJECT_RULES

        self.assertIn("XAGUSD", rules.focus_assets)
        self.assertTrue(any("XAGUSD" in rule for rule in rules.metals_rules))
        self.assertTrue(any("doppelte Metall-Exposure" in rule for rule in rules.metals_rules))

    def test_risk_rules_encode_wait_and_quality_constraints(self):
        risk_text = " ".join(IMPORTED_TRADING_PROJECT_RULES.risk_rules)
        summary = " ".join(imported_rule_summary_lines())

        self.assertIn("maximal ein Haupttrade", risk_text)
        self.assertIn("<= 0,8", risk_text)
        self.assertIn("5-15 Minuten", summary)
        self.assertIn("keine erste Kerze", summary)


if __name__ == "__main__":
    unittest.main()
