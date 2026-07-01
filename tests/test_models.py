import sys
import unittest
from datetime import date, datetime, time, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from trading_freaks.models import (
    Candle,
    Direction,
    JournalEntry,
    MarketType,
    SetupValidationResult,
    Timeframe,
    TradingStyle,
)


class ModelTests(unittest.TestCase):
    def test_candle_requires_timezone_aware_timestamp(self):
        with self.assertRaises(ValueError):
            Candle(
                timestamp=datetime(2026, 5, 20, 15, 30),
                open=100.0,
                high=101.0,
                low=99.0,
                close=100.5,
                volume=1000,
            )

    def test_candle_accepts_valid_ohlcv(self):
        candle = Candle(
            timestamp=datetime(2026, 5, 20, 15, 30, tzinfo=timezone.utc),
            open=100.0,
            high=101.0,
            low=99.0,
            close=100.5,
            volume=1000,
        )

        self.assertEqual(candle.close, 100.5)

    def test_setup_validation_rejects_allowed_with_failed_conditions(self):
        with self.assertRaises(ValueError):
            SetupValidationResult(
                setup_name="Example",
                market=MarketType.US_STOCK,
                timeframe_context=Timeframe.M1,
                timeframe_entry=Timeframe.M1,
                direction=Direction.LONG,
                required_conditions=("A",),
                passed_conditions=(),
                failed_conditions=("A",),
                entry_logic="",
                stop_loss_logic="",
                take_profit_logic="",
                risk_logic="",
                invalidation_logic="",
                journal_fields=(),
                confidence_score=0.0,
                trade_allowed=True,
                reason_if_not_allowed="",
            )

    def test_journal_entry_requires_violated_rule_when_non_compliant(self):
        with self.assertRaises(ValueError):
            JournalEntry(
                trade_date=date(2026, 5, 20),
                trade_time=time(15, 45),
                market=MarketType.US_STOCK,
                symbol="EXAMPLE",
                setup="US-Aktien Newstrade Breakout",
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
                entry_reason="Breakout checklist passed",
                rule_compliant=False,
            )


if __name__ == "__main__":
    unittest.main()

