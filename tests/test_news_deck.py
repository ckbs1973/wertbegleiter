import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from trading_freaks.api.routes import evaluate_news_deck_payload
from trading_freaks.news_deck import create_news_deck


WATCHLIST = (
    "###INDEX CFD,GBEBROKERS:DE40,GBEBROKERS:US500,"
    "###STOCK CFD,GBEBROKERS:AAPL,GBEBROKERS:NVDA,GBEBROKERS:TSLA,"
    "###Forex,GBEBROKERS:EURUSD,GBEBROKERS:GBPUSD"
)


class NewsDeckTests(unittest.TestCase):
    def test_creates_tweetdeck_style_columns_from_watchlist(self):
        deck = create_news_deck(WATCHLIST)

        self.assertEqual(deck.status, "news_deck_vorbereitet")
        self.assertEqual(len(deck.columns), 5)
        first = deck.columns[0]
        self.assertEqual(first.source, "X Pro / TweetDeck")
        self.assertIn("$NVDA", first.query)
        self.assertIn("filter:replies", first.query)
        self.assertTrue(first.url.startswith("https://x.com/search?"))
        self.assertIn("keine Anlageberatung", deck.disclaimer)

    def test_api_blocks_missing_watchlist(self):
        response = evaluate_news_deck_payload({"watchlist_text": ""})

        self.assertEqual(response["status"], "nicht_handeln")
        self.assertIn("watchlist_text fehlt", response["errors"])

    def test_api_returns_deck_without_trade_signal(self):
        response = evaluate_news_deck_payload({"watchlist_text": WATCHLIST})

        self.assertEqual(response["status"], "news_deck_vorbereitet")
        self.assertIn("keine Anlageberatung", response["disclaimer"])
        self.assertIn("X-Zugangsdaten", response["source_note"])
        self.assertEqual(response["deck"]["columns"][2]["title"], "FX Macro Pulse")


if __name__ == "__main__":
    unittest.main()
