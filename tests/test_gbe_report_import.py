import sys
import unittest
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from trading_freaks.journal.gbe_report_import import journal_rows_from_report, parse_gbe_report_lines


SAMPLE_LINES = [
    "A/C No:",
    "16291",
    "Name:",
    "Christian Koronna",
    "Snapshot:",
    "24/06/2026 22:00:00 UTC +0",
    "Closed Trades:",
    "Order ID",
    "Instrument",
    "Volume",
    "Side",
    "Open Time",
    "Avg Open Price",
    "Close Time",
    "Close Price",
    "Commission",
    "Swap",
    "Net Profit",
    "Profit",
    "W174864985026500",
    "XAGUSD",
    "1.9",
    "BUY",
    "2026-06-24 06:08:14",
    "62.205",
    "2026-06-24 10:56:46",
    "60.544",
    "-10.03",
    "0.00",
    "-13915.88",
    "-13925.91",
    "W174864985031697",
    "DE40",
    "10",
    "SELL",
    "2026-06-24 12:56:46",
    "24618.29",
    "2026-06-24 13:51:16",
    "24670.41",
    "0.00",
    "0.00",
    "-521.20",
    "-521.20",
    "Summary",
    "-10.03",
    "0.00",
    "-14437.08",
    "-14447.11",
    "A/C Summary:",
    "Currency:",
    "EUR",
    "Closed Trade P/L:",
    "-14447.11",
    "Equity:",
    "12456.39",
    "Margin Requirement:",
    "0.00",
    "Commissions(-ve):",
    "-10.03",
    "Net Floating P/L:",
    "0.00",
    "Balance:",
    "12456.39",
    "Swap:",
    "0.00",
]


class GBEReportImportTests(unittest.TestCase):
    def test_parse_gbe_eod_report_lines(self):
        report = parse_gbe_report_lines(SAMPLE_LINES, "End of Day Report 16291 .pdf")

        self.assertEqual(report.summary.account_no, "16291")
        self.assertEqual(report.summary.currency, "EUR")
        self.assertEqual(report.summary.balance, Decimal("12456.39"))
        self.assertEqual(report.summary.inferred_start_balance, Decimal("26903.50"))
        self.assertEqual(len(report.trades), 2)
        self.assertEqual(report.trades[0].symbol, "XAGUSD")
        self.assertEqual(report.trades[0].direction, "Long")
        self.assertEqual(report.trades[0].market, "commodity")
        self.assertEqual(report.trades[0].entry_time_berlin.hour, 8)
        self.assertIn("Metall-Exposure", " ".join(report.trades[0].review_flags))
        self.assertEqual(report.trades[1].symbol, "DE40")
        self.assertEqual(report.trades[1].direction, "Short")
        self.assertEqual(report.trades[1].market, "index")

    def test_journal_rows_mark_missing_plan_data(self):
        report = parse_gbe_report_lines(SAMPLE_LINES, "End of Day Report 16291 .pdf")
        rows = journal_rows_from_report(report)

        self.assertEqual(rows[0]["symbol"], "XAGUSD")
        self.assertEqual(rows[0]["stop_loss"], "")
        self.assertEqual(rows[0]["take_profit"], "")
        self.assertEqual(rows[0]["rule_compliant"], "unklar")
        self.assertIn("Brokerreport enthaelt keine Setup-Kriterien", rows[0]["criteria_failed"])
        self.assertIn("SL/TP/CRV", rows[0]["review"])
        self.assertEqual(rows[1]["setup"], "DAX Abpraller / ORB/SR manuell pruefen")


if __name__ == "__main__":
    unittest.main()
