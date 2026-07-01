import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from trading_freaks.models import Direction
from trading_freaks.risk.position_sizing import calculate_risk_plan
from trading_freaks.setups.us_news_breakout_checklist import (
    USNewsBreakoutInput,
    evaluate_us_news_breakout,
)


def valid_candidate(**overrides):
    payload = {
        "symbol": "EXAMPLE",
        "direction": Direction.LONG,
        "daily_volume": 2_000_000,
        "is_penny_stock": False,
        "has_news_catalyst": True,
        "news_is_mixed": False,
        "gap_percent": 4.2,
        "main_session_started": True,
        "momentum_in_news_direction_by_1545": True,
        "price_on_correct_vwap_side": True,
        "consolidation_minutes": 7,
        "consolidation_is_tight": True,
        "correction_fraction_of_momentum": 0.25,
        "pattern_type": "flag",
        "rvol": 1.8,
        "rvol_anticipated": False,
        "entry_is_near_breakout": True,
        "movement_is_momentum_not_volatility": True,
        "close_by_end_of_day_planned": True,
    }
    payload.update(overrides)
    return USNewsBreakoutInput(**payload)


def valid_risk_plan():
    return calculate_risk_plan(
        account_equity=10_000,
        risk_percent=1.0,
        direction=Direction.LONG,
        entry=101.0,
        stop_loss=100.0,
        take_profit=102.0,
    )


class USNewsBreakoutChecklistTests(unittest.TestCase):
    def test_valid_candidate_passes_as_information_only_rule_check(self):
        result = evaluate_us_news_breakout(valid_candidate(), risk_plan=valid_risk_plan())

        self.assertTrue(result.trade_allowed)
        self.assertTrue(result.information_only)
        self.assertEqual(result.failed_conditions, ())
        self.assertEqual(result.confidence_score, 100.0)

    def test_missing_risk_plan_blocks_setup(self):
        result = evaluate_us_news_breakout(valid_candidate(), risk_plan=None)

        self.assertFalse(result.trade_allowed)
        self.assertIn("RiskPlan ist vorhanden", result.failed_conditions)
        self.assertIn("Kein gueltiges Setup", result.reason_if_not_allowed)

    def test_mixed_news_blocks_breakout_setup(self):
        result = evaluate_us_news_breakout(
            valid_candidate(news_is_mixed=True),
            risk_plan=valid_risk_plan(),
        )

        self.assertFalse(result.trade_allowed)
        self.assertIn("News sind nicht mixed", result.failed_conditions)

    def test_volatility_without_momentum_blocks_setup(self):
        result = evaluate_us_news_breakout(
            valid_candidate(movement_is_momentum_not_volatility=False),
            risk_plan=valid_risk_plan(),
        )

        self.assertFalse(result.trade_allowed)
        self.assertIn("Momentum statt blosser Volatilitaet", result.failed_conditions)

    def test_rvol_anticipation_warns_but_can_pass(self):
        result = evaluate_us_news_breakout(
            valid_candidate(rvol=1.1, rvol_anticipated=True),
            risk_plan=valid_risk_plan(),
        )

        self.assertTrue(result.trade_allowed)
        self.assertIn("RVOL wurde antizipiert; nach Kerzenschluss nachpruefen", result.warnings)

    def test_invalid_risk_plan_blocks_setup(self):
        invalid_risk = calculate_risk_plan(
            account_equity=10_000,
            risk_percent=1.0,
            direction=Direction.LONG,
            entry=101.0,
            stop_loss=102.0,
            take_profit=103.0,
        )

        result = evaluate_us_news_breakout(valid_candidate(), risk_plan=invalid_risk)

        self.assertFalse(result.trade_allowed)
        self.assertIn("RiskPlan ist gueltig", result.failed_conditions)


if __name__ == "__main__":
    unittest.main()

