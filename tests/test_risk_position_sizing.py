import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from trading_freaks.models import Direction
from trading_freaks.risk.position_sizing import calculate_risk_plan


class RiskPositionSizingTests(unittest.TestCase):
    def test_calculates_valid_long_risk_plan(self):
        plan = calculate_risk_plan(
            account_equity=10_000,
            risk_percent=1.0,
            direction=Direction.LONG,
            entry=101.0,
            stop_loss=100.0,
            take_profit=102.0,
        )

        self.assertTrue(plan.is_valid)
        self.assertEqual(plan.errors, ())
        self.assertAlmostEqual(plan.risk_amount, 100.0)
        self.assertAlmostEqual(plan.risk_per_unit, 1.0)
        self.assertAlmostEqual(plan.position_size, 100.0)
        self.assertAlmostEqual(plan.crv, 1.0)

    def test_warns_above_default_one_percent_risk(self):
        plan = calculate_risk_plan(
            account_equity=10_000,
            risk_percent=2.0,
            direction=Direction.SHORT,
            entry=100.0,
            stop_loss=101.0,
            take_profit=99.0,
        )

        self.assertTrue(plan.is_valid)
        self.assertIn("risk_percent above 1%; protective review required", plan.warnings)

    def test_blocks_missing_stop_loss(self):
        plan = calculate_risk_plan(
            account_equity=10_000,
            risk_percent=1.0,
            direction=Direction.LONG,
            entry=101.0,
            stop_loss=None,
            take_profit=102.0,
        )

        self.assertFalse(plan.is_valid)
        self.assertIn("stop_loss is required and must be positive", plan.errors)
        self.assertEqual(plan.position_size, 0.0)

    def test_blocks_wrong_stop_side(self):
        plan = calculate_risk_plan(
            account_equity=10_000,
            risk_percent=1.0,
            direction=Direction.LONG,
            entry=101.0,
            stop_loss=102.0,
            take_profit=103.0,
        )

        self.assertFalse(plan.is_valid)
        self.assertIn("long stop_loss must be below entry", plan.errors)

    def test_blocks_missing_exit_plan(self):
        plan = calculate_risk_plan(
            account_equity=10_000,
            risk_percent=1.0,
            direction=Direction.LONG,
            entry=101.0,
            stop_loss=100.0,
        )

        self.assertFalse(plan.is_valid)
        self.assertIn("take_profit or explicit exit_rule is required", plan.errors)

    def test_blocks_crv_below_minimum(self):
        plan = calculate_risk_plan(
            account_equity=10_000,
            risk_percent=1.0,
            direction=Direction.LONG,
            entry=101.0,
            stop_loss=100.0,
            take_profit=101.5,
        )

        self.assertFalse(plan.is_valid)
        self.assertIn("planned CRV must be at least 1.0:1", plan.errors)


if __name__ == "__main__":
    unittest.main()

