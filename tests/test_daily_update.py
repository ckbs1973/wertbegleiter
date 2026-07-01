import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from trading_freaks.api.routes import evaluate_daily_update_payload


def valid_daily_payload():
    return {
        "context": {
            "account_equity": 10_000,
            "trades_taken_today": 1,
            "max_trades_per_day": 5,
            "target_min_trades": 2,
            "target_max_trades": 5,
            "default_risk_percent": 1,
            "psychology_ready": True,
            "loss_streak": 0,
        },
        "candidates": [
            {
                "candidate_id": "nvda-breakout",
                "symbol": "NVDA",
                "setup_name": "US Newstrade Breakout",
                "market": "us_stock",
                "direction": "long",
                "style": "scalping",
                "planned_time": "15:45",
                "entry": 101,
                "stop_loss": 100,
                "take_profit": 102,
                "unit_value": 1,
                "required_conditions": [
                    {"name": "News-Katalysator", "passed": True},
                    {"name": "Momentum statt Volatilitaet", "passed": True},
                    {"name": "Entry nahe Ausbruchslevel", "passed": True},
                ],
            }
        ],
    }


class DailyUpdateTests(unittest.TestCase):
    def test_valid_candidate_gets_manual_review_status(self):
        response = evaluate_daily_update_payload(valid_daily_payload())

        self.assertEqual(response["status"], "arbeitsbereit")
        candidate = response["daily_update"]["candidates"][0]
        self.assertEqual(candidate["status"], "trade_erlaubt_zur_manuellen_pruefung")
        self.assertEqual(candidate["risk_plan"]["risk_amount"], 100)
        self.assertEqual(candidate["risk_plan"]["position_size"], 100)
        self.assertEqual(candidate["risk_plan"]["crv"], 1)

    def test_missing_required_condition_blocks_candidate(self):
        payload = valid_daily_payload()
        payload["candidates"][0]["required_conditions"][1]["passed"] = False

        response = evaluate_daily_update_payload(payload)

        candidate = response["daily_update"]["candidates"][0]
        self.assertEqual(candidate["status"], "nicht_handeln")
        self.assertIn("Momentum statt Volatilitaet", candidate["failed_conditions"])

    def test_daily_trade_limit_blocks_candidate(self):
        payload = valid_daily_payload()
        payload["context"]["trades_taken_today"] = 5

        response = evaluate_daily_update_payload(payload)

        self.assertEqual(response["status"], "trading_pause_empfohlen")
        candidate = response["daily_update"]["candidates"][0]
        self.assertEqual(candidate["status"], "nicht_handeln")
        self.assertIn("Tageslimit fuer Trades erreicht", candidate["failed_conditions"])

    def test_crv_below_one_blocks_candidate(self):
        payload = valid_daily_payload()
        payload["candidates"][0]["take_profit"] = 101.5

        response = evaluate_daily_update_payload(payload)

        candidate = response["daily_update"]["candidates"][0]
        self.assertEqual(candidate["status"], "nicht_handeln")
        self.assertIn("planned CRV must be at least 1.0:1", candidate["failed_conditions"])

    def test_us_open_first_five_minute_candle_blocks_scalp(self):
        payload = valid_daily_payload()
        payload["candidates"][0]["planned_time"] = "15:32"

        response = evaluate_daily_update_payload(payload)

        candidate = response["daily_update"]["candidates"][0]
        self.assertEqual(candidate["status"], "nicht_handeln")
        self.assertIn("Keine erste 5-Minuten-Kerze im US-Open handeln", candidate["failed_conditions"])

    def test_imported_project_notes_are_included(self):
        response = evaluate_daily_update_payload(valid_daily_payload())

        notes = " ".join(response["daily_update"]["notes"])
        self.assertIn("ORB 10:00-12:00", notes)
        self.assertIn("XAGUSD", notes)


if __name__ == "__main__":
    unittest.main()
