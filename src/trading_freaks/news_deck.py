"""TweetDeck/X-Pro style news desk planning without live scraping.

The module creates column definitions, queries, and validation prompts that can
be opened in X Pro or used beside other news sources. It deliberately does not
authenticate to X, scrape timelines, or treat social posts as trade signals.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Tuple
from urllib.parse import quote_plus

from trading_freaks.morning_brief import WatchlistAsset, parse_tradingview_watchlist


@dataclass(frozen=True)
class NewsDeckColumn:
    column_id: str
    title: str
    source: str
    category: str
    query: str
    url: str
    symbols: Tuple[str, ...]
    required_checks: Tuple[str, ...]
    blocking_rules: Tuple[str, ...]
    journal_hints: Tuple[str, ...]


@dataclass(frozen=True)
class NewsDeckPlan:
    status: str
    disclaimer: str
    source_note: str
    columns: Tuple[NewsDeckColumn, ...]
    workflow: Tuple[str, ...]


US_STOCK_NEWS_TERMS = (
    "earnings",
    "guidance",
    "upgrade",
    "downgrade",
    "acquisition",
    "takeover",
    "buyback",
    "short report",
)

FX_MACRO_TERMS = (
    "CPI",
    "NFP",
    "Fed",
    "ECB",
    "BoE",
    "BoJ",
    "SNB",
    "PMI",
    "rates",
)


def _symbols_by_group(assets: Iterable[WatchlistAsset], group_keyword: str) -> Tuple[str, ...]:
    keyword = group_keyword.upper()
    return tuple(asset.symbol for asset in assets if keyword in asset.group.upper())


def _x_search_url(query: str) -> str:
    return f"https://x.com/search?q={quote_plus(query)}&src=typed_query&f=live"


def _or_query(symbols: Iterable[str], prefix_cash_tag: bool = False) -> str:
    values = []
    for symbol in symbols:
        clean = symbol.strip().upper()
        if not clean:
            continue
        values.append(f"${clean}" if prefix_cash_tag else clean)
    return " OR ".join(values)


def _stock_query(symbols: Tuple[str, ...]) -> str:
    if not symbols:
        return "(" + " OR ".join(US_STOCK_NEWS_TERMS) + ")"
    symbol_query = _or_query(symbols[:10], prefix_cash_tag=True)
    term_query = " OR ".join(f'"{term}"' if " " in term else term for term in US_STOCK_NEWS_TERMS)
    return f"({symbol_query}) ({term_query}) -filter:replies"


def _fx_query(symbols: Tuple[str, ...]) -> str:
    pair_query = _or_query(symbols[:12])
    term_query = " OR ".join(FX_MACRO_TERMS)
    return f"({pair_query}) ({term_query}) -filter:replies" if pair_query else f"({term_query}) -filter:replies"


def _index_query(symbols: Tuple[str, ...]) -> str:
    index_symbols = _or_query(symbols[:10])
    terms = "DAX OR Nasdaq OR S&P OR futures OR yield OR risk-off OR risk-on"
    return f"({index_symbols}) ({terms}) -filter:replies" if index_symbols else f"({terms}) -filter:replies"


def create_news_deck(watchlist_text: str) -> NewsDeckPlan:
    """Create a TweetDeck-like column plan from a TradingView watchlist."""

    assets = parse_tradingview_watchlist(watchlist_text)
    stock_symbols = _symbols_by_group(assets, "STOCK")
    fx_symbols = _symbols_by_group(assets, "FOREX")
    index_symbols = _symbols_by_group(assets, "INDEX")

    stock_query = _stock_query(stock_symbols)
    fx_query = _fx_query(fx_symbols)
    index_query = _index_query(index_symbols)

    columns = (
        NewsDeckColumn(
            column_id="x-us-stock-catalysts",
            title="US Stock Catalysts",
            source="X Pro / TweetDeck",
            category="social_news",
            query=stock_query,
            url=_x_search_url(stock_query),
            symbols=stock_symbols[:10],
            required_checks=(
                "News-Katalysator muss eindeutig sein",
                "Gap > 3% oder starke relative Bewegung pruefen",
                "Opening Drive ab 15:30 und VWAP-Seite bestaetigen",
                "RVOL > 1,5 nur fuer News-Breakout werten",
            ),
            blocking_rules=(
                "Mixed News ohne klare Richtung",
                "Post ohne bestaetigende Kursreaktion",
                "Nur Volatilitaet statt Momentum",
            ),
            journal_hints=(
                "Quelle, Uhrzeit und Headline notieren",
                "Screenshot vor Trade und nach Trade sichern",
            ),
        ),
        NewsDeckColumn(
            column_id="seeking-alpha-confirmation",
            title="Stock News Confirmation",
            source="Seeking Alpha Market News",
            category="stock_news",
            query="Earnings, Guidance, Up-/Downgrades, Uebernahmen, Short-Attacken",
            url="https://seekingalpha.com/market-news/top-news",
            symbols=stock_symbols[:10],
            required_checks=(
                "Headline gegen zweite Quelle verifizieren",
                "Guidance hoeher gewichten als Vergangenheitszahlen",
                "Kursreaktion und Volumen muessen die Relevanz zeigen",
            ),
            blocking_rules=(
                "Keine marktrelevante Meldung",
                "Meldung bereits voll eingepreist",
                "Unklare Interpretation",
            ),
            journal_hints=("News-Kategorie und Interpretation dokumentieren",),
        ),
        NewsDeckColumn(
            column_id="x-fx-macro",
            title="FX Macro Pulse",
            source="X Pro / TweetDeck",
            category="fx_news",
            query=fx_query,
            url=_x_search_url(fx_query),
            symbols=fx_symbols[:12],
            required_checks=(
                "Stark gegen schwach nur mit Sentiment-Kontext markieren",
                "Wirtschaftskalender vor Setup pruefen",
                "Nach Event: Ueberraschung, einheitliche Daten, Momentum",
            ),
            blocking_rules=(
                "Risikoevent steht direkt bevor",
                "Daten gemischt",
                "Sentiment laeuft klar gegen die technische Idee",
            ),
            journal_hints=("Eventzeit, Datenabweichung und erste M1/M5-Reaktion erfassen",),
        ),
        NewsDeckColumn(
            column_id="calendar-risk-events",
            title="Risk Event Calendar",
            source="Investing.com Economic Calendar",
            category="economic_calendar",
            query="CPI, Arbeitsmarkt, Zentralbanken, PMIs, Wachstum",
            url="https://www.investing.com/economic-calendar-",
            symbols=fx_symbols,
            required_checks=(
                "High-impact Events fuer betroffene Waehrungen markieren",
                "Keine Position vor dem Event im Wirtschaftsdaten-Setup",
                "FX/Index-Limits bei nahen Events blockieren",
            ),
            blocking_rules=(
                "Eventzeit unklar",
                "Spread/Slippage-Risiko nicht kalkulierbar",
                "News vor Preisreaktion interpretiert",
            ),
            journal_hints=("Kalender-Screenshot oder Event-Name im Journal festhalten",),
        ),
        NewsDeckColumn(
            column_id="x-index-risk",
            title="Index Risk Tone",
            source="X Pro / TweetDeck",
            category="index_news",
            query=index_query,
            url=_x_search_url(index_query),
            symbols=index_symbols[:10],
            required_checks=(
                "DAX/Index-Zonen nur aus H4/D1/W1 ableiten",
                "Risk-On/Risk-Off gegen US-Futures und Renditen pruefen",
                "Limit-Idee nur mit SL, TP und CRV >= 1:1 vorbereiten",
            ),
            blocking_rules=(
                "Risikoevent in direkter Naehe",
                "Zone nicht stark genug",
                "Abstand zur Zone zu gross",
            ),
            journal_hints=("Zone, Zeiteinheit und Ablehnungsgrund dokumentieren",),
        ),
    )

    return NewsDeckPlan(
        status="news_deck_vorbereitet",
        disclaimer="Information und Checklistenunterstuetzung, keine Anlageberatung oder Orderfreigabe.",
        source_note=(
            "X Pro kann als externe Spaltenoberflaeche genutzt werden; dieses System "
            "speichert keine X-Zugangsdaten und wertet Posts nur als zu verifizierende Hinweise."
        ),
        columns=columns,
        workflow=(
            "08:00 Quellen und Kalender pruefen",
            "US-Aktien erst nach News, Gap und Opening Drive klassifizieren",
            "FX nur nach Sentiment, Kalender und Momentum pruefen",
            "Jede Headline mit Kursreaktion, VWAP/Level und Volumen bestaetigen",
            "Ohne Stop Loss, Take Profit und CRV >= 1:1 bleibt der Status Nicht handeln",
        ),
    )
