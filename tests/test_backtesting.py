import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from trading_freaks.backtesting.backtest_engine import BacktestEngine
from trading_freaks.backtesting.trade_simulator import simulate_bracket_trade
from trading_freaks.models import (
    BacktestDecision,
    Candle,
    ChecklistCondition,
    Direction,
    MarketType,
    SetupValidationResult,
    Timeframe,
)
from trading_freaks.risk.position_sizing import calculate_risk_plan


def candle(index, open_=100.0, high=101.0, low=99.0, close=100.5):
    return Candle(
        timestamp=datetime(2026, 5, 20, 15, 30, tzinfo=timezone.utc) + timedelta(minutes=index),
        open=open_,
        high=high,
        low=low,
        close=close,
        volume=1000,
        symbol="EXAMPLE",
    )


def allowed_validation():
    return SetupValidationResult.from_conditions(
        setup_name="Test Setup",
        market=MarketType.US_STOCK,
        timeframe_context=Timeframe.M1,
        timeframe_entry=Timeframe.M1,
        direction=Direction.LONG,
        conditions=[ChecklistCondition("Rule", True)],
        entry_logic="",
        stop_loss_logic="",
        take_profit_logic="",
        risk_logic="",
        invalidation_logic="",
        journal_fields=(),
    )


class BacktestingTests(unittest.TestCase):
    def test_same_bar_stop_and_target_uses_conservative_stop(self):
        trade = simulate_bracket_trade(
            symbol="EXAMPLE",
            setup_name="Test Setup",
            direction=Direction.LONG,
            entry=100.0,
            stop_loss=99.0,
            take_profit=101.0,
            position_size=100.0,
            future_candles=[candle(1, high=101.5, low=98.5)],
        )

        self.assertEqual(trade.exit_reason, "stop_loss_conservative_same_bar")
        self.assertAlmostEqual(trade.result_r, -1.0)

    def test_spread_and_slippage_reduce_realized_result(self):
        trade = simulate_bracket_trade(
            symbol="EXAMPLE",
            setup_name="Test Setup",
            direction=Direction.LONG,
            entry=100.0,
            stop_loss=99.0,
            take_profit=101.0,
            position_size=100.0,
            future_candles=[candle(1, high=101.5, low=100.0)],
            spread_per_unit=0.10,
            slippage_per_unit=0.05,
        )

        self.assertEqual(trade.exit_reason, "take_profit")
        self.assertAlmostEqual(trade.entry, 100.10)
        self.assertAlmostEqual(trade.exit_price, 100.90)
        self.assertLess(trade.result_r, 1.0)

    def test_engine_passes_history_only_and_simulates_allowed_decision(self):
        candles = [
            candle(0, high=100.5, low=99.5, close=100.0),
            candle(1, high=100.7, low=99.8, close=100.2),
            candle(2, open_=100.2, high=101.2, low=100.1, close=101.0),
        ]
        seen_lengths = []

        def strategy(history):
            seen_lengths.append(len(history))
            if len(history) != 2:
                return None
            risk = calculate_risk_plan(
                account_equity=10_000,
                risk_percent=1.0,
                direction=Direction.LONG,
                entry=100.0,
                stop_loss=99.0,
                take_profit=101.0,
            )
            return BacktestDecision(
                timestamp=history[-1].timestamp,
                symbol="EXAMPLE",
                setup_name="Test Setup",
                validation=allowed_validation(),
                risk_plan=risk,
            )

        result = BacktestEngine().run(
            candles=candles,
            strategy=strategy,
            symbol="EXAMPLE",
            setup_name="Test Setup",
        )

        self.assertEqual(seen_lengths, [1, 2, 3])
        self.assertEqual(len(result.decisions), 1)
        self.assertEqual(len(result.trades), 1)
        self.assertAlmostEqual(result.metrics["win_rate"], 1.0)


if __name__ == "__main__":
    unittest.main()
