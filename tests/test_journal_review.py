import json
import sys
import unittest
from datetime import date, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from trading_freaks.journal.journal_export import journal_entries_to_csv_rows, journal_entries_to_json
from trading_freaks.journal.journal_model import validate_journal_entry
from trading_freaks.journal.review_engine import review_journal
from trading_freaks.models import Direction, JournalEntry, MarketType, Timeframe, TradingStyle


def entry(
    result_r,
    *,
    symbol="EXAMPLE",
    setup="Setup",
    compliant=True,
    violation=None,
    emotion="calm",
    screenshot_before="before.png",
):
    return JournalEntry(
        trade_date=date(2026, 5, 20),
        trade_time=time(15, 45),
        market=MarketType.US_STOCK,
        symbol=symbol,
        setup=setup,
        direction=Direction.LONG,
        trading_style=TradingStyle.SCALPING,
        timeframe_context=Timeframe.M1,
        timeframe_entry=Timeframe.M1,
        news_catalyst=True,
        economic_event=False,
        sentiment="positive",
        entry=101.0,
        stop_loss=100.0,
        take_profit=102.0,
        position_size=100.0,
        risk_amount=100.0,
        risk_percent=1.0,
        planned_crv=1.0,
        entry_reason="Checklist",
        realized_r=result_r,
        rule_compliant=compliant,
        violated_rule=violation,
        emotion_before=emotion,
        emotion_during="focused",
        emotion_after="calm",
        review="Plan followed",
        improvement_next_trade="Keep same process",
        criteria_met=("News", "VWAP", "RVOL"),
        screenshot_before=screenshot_before,
        screenshot_after="after.png",
    )


class JournalReviewTests(unittest.TestCase):
    def test_review_metrics(self):
        metrics = review_journal(
            [
                entry(1.0, setup="A"),
                entry(-1.0, setup="A", compliant=False, violation="FOMO", emotion="nervous"),
                entry(2.0, setup="B"),
                entry(-0.5, setup="B"),
            ]
        )

        self.assertEqual(metrics.total_trades, 4)
        self.assertAlmostEqual(metrics.win_rate, 0.5)
        self.assertAlmostEqual(metrics.average_r, 0.375)
        self.assertAlmostEqual(metrics.profit_factor, 2.0)
        self.assertEqual(metrics.largest_loss_streak, 1)
        self.assertEqual(metrics.rule_violation_trades, 1)
        self.assertEqual(metrics.frequent_violations["FOMO"], 1)
        self.assertIn("A", metrics.by_setup)
        self.assertIn("nervous", metrics.by_emotion_before)

    def test_exports_json_and_csv(self):
        entries = [entry(1.0)]
        parsed = json.loads(journal_entries_to_json(entries))
        csv_text = journal_entries_to_csv_rows(entries)

        self.assertEqual(parsed[0]["symbol"], "EXAMPLE")
        self.assertIn("symbol", csv_text.splitlines()[0])
        self.assertIn("EXAMPLE", csv_text)

    def test_journal_validation_requires_emotions_rule_context_and_screenshots(self):
        valid = validate_journal_entry(entry(1.0))
        incomplete = validate_journal_entry(
            entry(
                -1.0,
                emotion="",
                screenshot_before="before.bmp",
            )
        )

        self.assertTrue(valid.is_complete)
        self.assertFalse(incomplete.is_complete)
        self.assertIn("emotion_before", [issue.field for issue in incomplete.issues])
        self.assertIn("screenshot_before", [issue.field for issue in incomplete.issues])


if __name__ == "__main__":
    unittest.main()
