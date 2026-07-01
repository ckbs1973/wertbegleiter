"""Session playbook rules imported from the ChatGPT Trading project.

The rules describe how to structure daily updates, Europe-session checks,
US-open checks, and breaking-news checks. They are process guardrails only:
no investment advice, no order recommendation, no broker execution.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import time
from typing import Sequence, Tuple


def _as_tuple(values: Sequence[str]) -> Tuple[str, ...]:
    return tuple(values)


@dataclass(frozen=True)
class SessionWindow:
    name: str
    start: time
    end: time
    focus: str
    required_checks: Tuple[str, ...]
    blockers: Tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "required_checks", _as_tuple(self.required_checks))
        object.__setattr__(self, "blockers", _as_tuple(self.blockers))
        if self.start >= self.end:
            raise ValueError("session start must be before end")


@dataclass(frozen=True)
class NewsPlaybook:
    required_timestamp_format: str
    structure: Tuple[str, ...]
    mandatory_filters: Tuple[str, ...]
    forbidden_behaviors: Tuple[str, ...]
    information_only: bool = True

    def __post_init__(self) -> None:
        object.__setattr__(self, "structure", _as_tuple(self.structure))
        object.__setattr__(self, "mandatory_filters", _as_tuple(self.mandatory_filters))
        object.__setattr__(self, "forbidden_behaviors", _as_tuple(self.forbidden_behaviors))
        if not self.information_only:
            raise ValueError("news playbook must remain information-only")


@dataclass(frozen=True)
class ImportedTradingProjectRules:
    source_chats: Tuple[str, ...]
    session_windows: Tuple[SessionWindow, ...]
    focus_assets: Tuple[str, ...]
    macro_filters: Tuple[str, ...]
    metals_rules: Tuple[str, ...]
    risk_rules: Tuple[str, ...]
    news_playbook: NewsPlaybook
    information_only: bool = True

    def __post_init__(self) -> None:
        object.__setattr__(self, "source_chats", _as_tuple(self.source_chats))
        object.__setattr__(self, "session_windows", tuple(self.session_windows))
        object.__setattr__(self, "focus_assets", _as_tuple(self.focus_assets))
        object.__setattr__(self, "macro_filters", _as_tuple(self.macro_filters))
        object.__setattr__(self, "metals_rules", _as_tuple(self.metals_rules))
        object.__setattr__(self, "risk_rules", _as_tuple(self.risk_rules))
        if not self.information_only:
            raise ValueError("imported trading rules must remain information-only")


IMPORTED_TRADING_PROJECT_RULES = ImportedTradingProjectRules(
    source_chats=(
        "Trading Update Daily",
        "Breaking news update: oil, yen, tech insights",
        "Taegliches Marktupdate und Trading-Setups",
        "US open update and trade scenarios",
        "Europe session update and trade scenarios",
    ),
    session_windows=(
        SessionWindow(
            name="Daily Market Update",
            start=time(8, 0),
            end=time(10, 0),
            focus="Makrobild, Wochenkalender, Top-Events, Watchlist-Kontext, No-Trade-Zonen.",
            required_checks=(
                "Wochenausblick und Wirtschaftskalender pruefen",
                "Risk-On/Risk-Off, USD, Yields, Oel, Gold/Silber und Tech-Sentiment einordnen",
                "Top-Events als harte Blocker vorplanen",
            ),
            blockers=(
                "fehlender Kalendercheck",
                "unklare Datenlage",
                "direkte Positionierung vor Top-Event",
            ),
        ),
        SessionWindow(
            name="Europe Session ORB",
            start=time(10, 0),
            end=time(12, 0),
            focus="DE40, EURUSD, USDJPY, XAU/XAG und eventgetriebene Europa-Setups.",
            required_checks=(
                "Opening Range abwarten",
                "Break und Retest oder Failed-Breakout-Struktur bestaetigen",
                "DE40 nicht gegen klares US-/Tech-Risiko handeln",
                "EURUSD nur mit USD/Yields-Bestaetigung handeln",
            ),
            blockers=(
                "Entry in den ersten Spike",
                "Top-Event unmittelbar vorher/nachher",
                "Chop ohne Follow-through",
            ),
        ),
        SessionWindow(
            name="US Open Preparation",
            start=time(14, 30),
            end=time(16, 30),
            focus="US-Daten, Fed-Speaker, US-Futures, Tech/AI, Micron/Semi-Kontext und US-Open-Plan.",
            required_checks=(
                "15:25 US-Open-Update erstellen",
                "keine erste 5-Minuten-Kerze handeln",
                "Opening Range und Korrelationen abwarten",
                "US500/USTEC, NVDA/Semis, USD/Yields und Oel gegeneinander pruefen",
            ),
            blockers=(
                "FOMO in den US-Open",
                "Daten-/News-Spike ohne Retest",
                "Index-Divergenz US500 gegen USTEC",
            ),
        ),
        SessionWindow(
            name="US Momentum Window",
            start=time(16, 30),
            end=time(18, 0),
            focus="Bestes Momentumfenster fuer US-ORB, Post-Event-Trendfolge und Pullback-Setups.",
            required_checks=(
                "5-15 Minuten nach Event/Open/Repricing warten",
                "Pullback oder Break-and-Retest bevorzugen",
                "Bond-Yields und Oel als Pflichtfilter nutzen",
                "maximal einen Haupttrade je stark korrelierter Session-Idee priorisieren",
            ),
            blockers=(
                "laufender Momentum-Spike ohne Pullback",
                "neues FX/Gold-Setup direkt vor Auktion/Fed-Speaker/Event",
                "korrelierte Ueberladung in gleicher Richtung",
            ),
        ),
    ),
    focus_assets=(
        "DE40",
        "US500",
        "USTEC",
        "EURUSD",
        "USDJPY",
        "XAUUSD",
        "XAUEUR",
        "XAGUSD",
        "UKOIL",
        "NVDA",
        "MSFT",
        "AAPL",
        "GOOG",
        "AMZN",
        "TSLA",
    ),
    macro_filters=(
        "Wirtschaftskalender und Wochenuebersicht vor jeder Session pruefen",
        "keine Positionierung vor Top-Terminen",
        "nach Top-Events zuerst Zahlen, Ueberraschung und M1/M5-Momentum pruefen",
        "Oel/Hormuz/Geopolitik als Risk-On/Risk-Off-Treiber behandeln",
        "USD, US-Renditen und Fed-Kommentare als Filter fuer Gold, EURUSD, USDJPY und Tech nutzen",
        "USDJPY im Interventionsbereich nicht blind long handeln",
        "Micron-/Semi-Earnings als Sentimentfilter fuer USTEC, NVDA und AI-Watchlist beachten",
    ),
    metals_rules=(
        "XAGUSD immer zusammen mit XAUUSD/XAUEUR im Metallblock beruecksichtigen",
        "Silber auf USD-, Rendite-, Gold/Silber-Ratio-, Industrie-, China- und Risk-On/Risk-Off-Sensitivitaet pruefen",
        "keine doppelte Metall-Exposure durch parallel korrelierte Gold- und Silberideen",
        "kein Blind-Long in XAUEUR, wenn XAUUSD klar gegenlaeuft",
    ),
    risk_rules=(
        "2-5 Trades sind ein Qualitaetskorridor, kein Tagesziel",
        "maximal ein Haupttrade je Session bei hoher Korrelation oder Headline-Risiko",
        "bei Geopolitik/Headline-Spikes Risiko reduzieren, z. B. <= 0,8 %",
        "CRV >= 1:1 bleibt hart; hochwertige ORB-/Event-Szenarien sollen eher >= 1:2 anstreben",
        "kein Chase, keine erste Kerze, kein Trade ohne Stop Loss und Exit-Plan",
        "kein Trade ist ein valider Trade",
    ),
    news_playbook=NewsPlaybook(
        required_timestamp_format="DD.MM.YYYY, HH:MM Uhr Europe/Berlin zu Beginn jeder Newsmeldung",
        structure=(
            "Stimmung / Marktregime",
            "Termine / News-Filter",
            "Zeitfenster-Plan",
            "bedingte Trade-Ideen, ausdruecklich keine Signale",
            "Fazit mit Blockern und Pflichtbestaetigungen",
        ),
        mandatory_filters=(
            "Datum und Uhrzeit an den Anfang jeder Breaking-News-Meldung",
            "betroffene Maerkte benennen",
            "moegliche Richtung nur als bedingte These formulieren",
            "relevantes Zeitfenster nennen",
            "Playbook-Bewertung mit Pullback/Retest/No-Trade formulieren",
            "Oel, USD/Yields, JPY/Intervention, Tech/AI und Metalle je nach Relevanz querpruefen",
        ),
        forbidden_behaviors=(
            "keine Orderfreigabe",
            "keine Kauf-/Verkaufsempfehlung",
            "keine Positionierung vor Event",
            "keine erste News- oder Open-Kerze handeln",
            "kein gleichzeitiges Ueberladen korrelierter USD-, Metall- oder Index-Ideen",
        ),
    ),
)


def session_for_time(value: time) -> SessionWindow | None:
    """Return the imported session window active at a given Berlin time."""

    for window in IMPORTED_TRADING_PROJECT_RULES.session_windows:
        if window.start <= value < window.end:
            return window
    return None


def imported_rule_summary_lines() -> Tuple[str, ...]:
    """Return compact lines suitable for UI, reports, and README snippets."""

    rules = IMPORTED_TRADING_PROJECT_RULES
    lines = [
        "ChatGPT-Trading-Projektregeln sind reine Prozessleitplanken.",
        "Kern-Playbook: ORB 10:00-12:00 und 16:30-18:00, strikter News-Filter, keine erste Kerze.",
        "Jede Breaking-News-Meldung startet mit Datum/Uhrzeit in Europe/Berlin.",
        "XAGUSD ist immer im Metallblock neben XAUUSD/XAUEUR enthalten.",
        "Oel, USD/Yields, JPY-Interventionsrisiko und Tech/AI-Sentiment sind Pflicht-Cross-Checks.",
        "Kein Trade vor Top-Events; 5-15 Minuten nach Event/Open/Repricing warten und Struktur verlangen.",
    ]
    return tuple(lines)
