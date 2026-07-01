"""Curated data-source registry for TradingFreaks-style preparation.

The registry captures sources named in the local TradingFreaks material plus
the current canonical URLs where practical. It is used for process checklists,
not for automatic trade recommendations.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple


@dataclass(frozen=True)
class TradingDataSource:
    name: str
    category: str
    url: str
    usage: str
    training_reference: str
    priority: int
    paid: bool = False
    caution: str = ""


MORNING_BRIEF_SOURCES: Tuple[TradingDataSource, ...] = (
    TradingDataSource(
        name="TradingView / Broker Watchlist",
        category="watchlist",
        url="local import",
        usage="Basisuniversum, Symbole, Marktgruppen und Charts fuer Levels/VWAP/Intraday-Kontext.",
        training_reference="4.6-Newstrade-Breakout.pdf; Watchlist beim Broker oder TradingView parken.",
        priority=1,
        caution="Watchlist ist nur ein Universum, kein Signal.",
    ),
    TradingDataSource(
        name="Investing.com Economic Calendar",
        category="economic_calendar",
        url="https://www.investing.com/economic-calendar-",
        usage="Wirtschaftsdaten, Inflationsdaten, Arbeitsmarkt, Zentralbanktermine und Risikoevents.",
        training_reference="3.2-FX-Newsquellen.pdf; Wirtschaftsdaten-Setup.pdf.",
        priority=2,
        caution="Events blockieren Setups, wenn Zeitpunkt oder Ueberraschung unklar sind.",
    ),
    TradingDataSource(
        name="ForexLive",
        category="fx_news",
        url="https://www.forexlive.com/",
        usage="Ad-hoc FX-/Makro-News, Zentralbank-Kommentare und Sentiment-Hinweise.",
        training_reference="3.2-FX-Newsquellen.pdf.",
        priority=3,
        caution="News muessen mit Kursmomentum und Kalenderkontext bestaetigt werden.",
    ),
    TradingDataSource(
        name="Newsquawk",
        category="squawk",
        url="https://www.newsquawk.com/",
        usage="Schnelle Headlines, Kalender, Marktaudio und Aktien-/Makro-Kontext.",
        training_reference="3.2-FX-Newsquellen.pdf.",
        priority=4,
        paid=True,
        caution="Kostenpflichtig; ohne Zugriff nur als optionale Quelle markieren.",
    ),
    TradingDataSource(
        name="X Pro",
        category="social_news",
        url="https://help.x.com/en/using-x/x-pro",
        usage="Listen/Streams fuer schnelle Unternehmens- und Markt-Headlines.",
        training_reference="4.4_die_marktrelevanten_nachrichten.pdf nennt TweetDeck.",
        priority=5,
        paid=True,
        caution="TweetDeck heisst heute X Pro; Social-News brauchen Verifikation durch Preisreaktion.",
    ),
    TradingDataSource(
        name="Seeking Alpha Market News",
        category="stock_news",
        url="https://seekingalpha.com/market-news/top-news",
        usage="Aktien-News, Earnings, Guidance, Up-/Downgrades und Unternehmensmeldungen.",
        training_reference="4.4_die_marktrelevanten_nachrichten.pdf.",
        priority=6,
        caution="Nicht jede Meldung ist marktrelevant; Kursreaktion und Volumen muessen bestaetigen.",
    ),
)


def sources_by_category(category: str) -> Tuple[TradingDataSource, ...]:
    return tuple(source for source in MORNING_BRIEF_SOURCES if source.category == category)


def source_checklist_lines() -> Tuple[str, ...]:
    return tuple(
        f"{source.name}: {source.usage} ({'paid' if source.paid else 'free/local'})"
        for source in sorted(MORNING_BRIEF_SOURCES, key=lambda item: item.priority)
    )
