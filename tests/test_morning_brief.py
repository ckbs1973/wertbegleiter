import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from trading_freaks.api.routes import evaluate_morning_brief_payload
from trading_freaks.data_sources import MORNING_BRIEF_SOURCES, sources_by_category
from trading_freaks.morning_brief import (
    assets_by_group,
    create_morning_brief,
    parse_tradingview_watchlist,
)


WATCHLIST = (
    "###INDEX CFD,GBEBROKERS:DE40,GBEBROKERS:US500,"
    "###STOCK CFD,GBEBROKERS:AAPL,GBEBROKERS:NVDA,GBEBROKERS:TSLA,"
    "###Forex,GBEBROKERS:EURUSD,GBEBROKERS:GBPUSD,"
    "###COMMODITY CFD,GBEBROKERS:XAGUSD"
)


class MorningBriefTests(unittest.TestCase):
    def test_parse_tradingview_watchlist_groups_assets(self):
        assets = parse_tradingview_watchlist(WATCHLIST)

        self.assertEqual(len(assets), 8)
        self.assertEqual(assets[0].symbol, "DE40")
        self.assertEqual(assets[0].group, "INDEX CFD")
        self.assertEqual(assets_by_group(assets)["STOCK CFD"], 3)

    def test_brief_prioritizes_liquid_us_stock_screening(self):
        brief = create_morning_brief(WATCHLIST, generated_for="2026-05-22", max_candidates=3)

        symbols = [candidate.symbol for candidate in brief.candidates]
        self.assertEqual(symbols, ["NVDA", "TSLA", "AAPL"])
        self.assertTrue(all(candidate.status == "nur_beobachten" for candidate in brief.candidates))
        self.assertIn("keine Anlageberatung", " ".join(brief.process_notes))
        self.assertIn("XAGUSD", " ".join(brief.process_notes))
        self.assertIn("Long bei positiver News", brief.candidates[0].direction_thesis)
        self.assertTrue(any(source.name == "Investing.com Economic Calendar" for source in brief.data_sources))

    def test_api_returns_summary_without_trade_recommendation(self):
        response = evaluate_morning_brief_payload(
            {
                "watchlist_text": WATCHLIST,
                "generated_for": "2026-05-22",
                "max_candidates": 5,
            }
        )

        self.assertEqual(response["status"], "morning_brief_erstellt")
        self.assertIn("keine Anlageberatung", response["disclaimer"])
        self.assertIn("TradingFreaks Morning Setup Brief", response["summary"])
        self.assertIn("Datenquellen-Check", response["summary"])
        self.assertEqual(response["brief"]["candidates"][0]["symbol"], "NVDA")

    def test_api_blocks_missing_watchlist(self):
        response = evaluate_morning_brief_payload({"watchlist_text": ""})

        self.assertEqual(response["status"], "nicht_handeln")
        self.assertIn("watchlist_text fehlt", response["errors"])

    def test_source_registry_contains_tf_sources(self):
        names = [source.name for source in MORNING_BRIEF_SOURCES]

        self.assertIn("ForexLive", names)
        self.assertIn("Newsquawk", names)
        self.assertIn("X Pro", names)
        self.assertEqual(sources_by_category("economic_calendar")[0].name, "Investing.com Economic Calendar")


if __name__ == "__main__":
    unittest.main()
