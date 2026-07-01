import argparse
import importlib.util
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "tools" / "capture_tradingview_event.py"
SPEC = importlib.util.spec_from_file_location("capture_tradingview_event", MODULE_PATH)
capture_tool = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(capture_tool)


class TradingViewCaptureToolTests(unittest.TestCase):
    def test_open_event_payload_matches_journal_event_contract(self):
        args = argparse.Namespace(
            event_type="opened",
            trade_id="btc-paper-1",
            symbol="btcusd",
            market="crypto",
            timestamp="2026-06-27T10:15:00+02:00",
            direction="long",
            entry="60000",
            stop_loss="59500",
            take_profit="61000",
            size="0.1",
            exit_price="",
            fees="",
            slippage="",
            note="Test",
        )

        payload = capture_tool.build_event_payload(args, screenshot_path="reports/tv/btc-before.png")

        self.assertEqual(payload["event_type"], "opened")
        self.assertEqual(payload["source"], "tradingview_macos_app")
        self.assertEqual(payload["symbol"], "BTCUSD")
        self.assertEqual(payload["market"], "crypto")
        self.assertEqual(payload["entry"], 60000.0)
        self.assertEqual(payload["stop_loss"], 59500.0)
        self.assertEqual(payload["take_profit"], 61000.0)
        self.assertEqual(payload["screenshot_path"], "reports/tv/btc-before.png")

    def test_close_event_payload_contains_exit_facts_only(self):
        args = argparse.Namespace(
            event_type="closed_take_profit",
            trade_id="btc-paper-1",
            symbol="BTCUSD",
            market="crypto",
            timestamp="2026-06-27T11:15:00+02:00",
            direction="long",
            entry="",
            stop_loss="",
            take_profit="",
            size="",
            exit_price="61000",
            fees="2.5",
            slippage="1",
            note="Review offen",
        )

        payload = capture_tool.build_event_payload(args, screenshot_path="reports/tv/btc-after.png")

        self.assertEqual(payload["event_type"], "closed_take_profit")
        self.assertEqual(payload["exit_price"], 61000.0)
        self.assertEqual(payload["fees"], 2.5)
        self.assertEqual(payload["slippage"], 1.0)
        self.assertNotIn("entry", payload)
        self.assertEqual(payload["screenshot_path"], "reports/tv/btc-after.png")


if __name__ == "__main__":
    unittest.main()
