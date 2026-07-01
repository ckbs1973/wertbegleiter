"""Rule-based morning setup brief for watchlist-driven preparation.

The brief selects assets for manual screening. It never issues a trade
recommendation, broker instruction, or live-trading decision.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Sequence, Tuple

from trading_freaks.data_sources import MORNING_BRIEF_SOURCES, TradingDataSource


PREFERRED_US_STOCKS = ("NVDA", "TSLA", "AAPL", "MSFT", "AMZN", "GOOG", "NKE", "PYPL")
PREFERRED_FX = ("EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD")
PREFERRED_INDEX = ("DE40", "US500", "USTEC", "DJ30")


def _as_tuple(values: Sequence[str]) -> Tuple[str, ...]:
    return tuple(values)


@dataclass(frozen=True)
class WatchlistAsset:
    symbol: str
    group: str
    source: str = ""

    def __post_init__(self) -> None:
        if not self.symbol.strip():
            raise ValueError("symbol is required")


@dataclass(frozen=True)
class MorningBriefCandidate:
    symbol: str
    group: str
    market: str
    primary_setup: str
    direction_thesis: str
    earliest_review_time: str
    decision_window: str
    required_confirmations: Tuple[str, ...]
    blockers: Tuple[str, ...]
    status: str = "nur_beobachten"
    information_only: bool = True

    def __post_init__(self) -> None:
        object.__setattr__(self, "required_confirmations", _as_tuple(self.required_confirmations))
        object.__setattr__(self, "blockers", _as_tuple(self.blockers))
        if not self.information_only:
            raise ValueError("morning brief must remain information-only")


@dataclass(frozen=True)
class MorningBrief:
    title: str
    generated_for: str
    candidates: Tuple[MorningBriefCandidate, ...]
    data_sources: Tuple[TradingDataSource, ...] = field(default_factory=lambda: MORNING_BRIEF_SOURCES)
    rejected_assets: Tuple[str, ...] = field(default_factory=tuple)
    process_notes: Tuple[str, ...] = field(default_factory=tuple)
    information_only: bool = True

    def __post_init__(self) -> None:
        object.__setattr__(self, "candidates", tuple(self.candidates))
        object.__setattr__(self, "data_sources", tuple(self.data_sources))
        object.__setattr__(self, "rejected_assets", _as_tuple(self.rejected_assets))
        object.__setattr__(self, "process_notes", _as_tuple(self.process_notes))
        if not self.information_only:
            raise ValueError("morning brief must remain information-only")


def parse_tradingview_watchlist(text: str) -> Tuple[WatchlistAsset, ...]:
    """Parse TradingView export text with optional ### group markers."""

    assets = []
    current_group = "Watchlist"
    for token in [part.strip() for part in text.split(",") if part.strip()]:
        if token.startswith("###"):
            current_group = token.replace("#", "").strip() or "Watchlist"
            continue
        source, symbol = (token.split(":", 1) if ":" in token else ("", token))
        clean_symbol = "".join(char for char in symbol.upper() if char.isalnum() or char in "._-")
        if clean_symbol:
            assets.append(WatchlistAsset(symbol=clean_symbol, group=current_group, source=source))
    return tuple(assets)


def _market_for(asset: WatchlistAsset) -> str:
    group = asset.group.upper()
    symbol = asset.symbol.upper()
    if "STOCK" in group:
        return "us_stock"
    if "FOREX" in group:
        return "forex"
    if "INDEX" in group or symbol in PREFERRED_INDEX:
        return "index"
    if "COMMODITY" in group or symbol in {"XAGUSD", "XAUUSD", "UKOIL"}:
        return "commodity"
    if "KRYPTO" in group or "CRYPTO" in group:
        return "crypto_cfd"
    return "unknown"


def _priority(asset: WatchlistAsset) -> tuple[int, int, str]:
    market = _market_for(asset)
    symbol = asset.symbol.upper()
    if market == "us_stock":
        order = PREFERRED_US_STOCKS
        return (0, order.index(symbol) if symbol in order else 99, symbol)
    if market == "index":
        order = PREFERRED_INDEX
        return (1, order.index(symbol) if symbol in order else 99, symbol)
    if market == "forex":
        order = PREFERRED_FX
        return (2, order.index(symbol) if symbol in order else 99, symbol)
    return (3, 99, symbol)


def _candidate_for(asset: WatchlistAsset) -> MorningBriefCandidate:
    market = _market_for(asset)
    symbol = asset.symbol.upper()

    if market == "us_stock":
        return MorningBriefCandidate(
            symbol=symbol,
            group=asset.group,
            market=market,
            primary_setup="US Newstrade Breakout / Rectangle Scalping",
            direction_thesis=(
                "Richtung erst nach News- und Opening-Drive-Bestaetigung: "
                "Long bei positiver News plus Momentum ueber VWAP, Short bei negativer News plus Momentum unter VWAP."
            ),
            earliest_review_time="15:30",
            decision_window="15:45-20:00",
            required_confirmations=(
                "marktrelevanter Katalysator oder klares Momentum",
                "M1 liquide ohne grosse Gaps",
                "VWAP-Seite passt zur Richtung",
                "enge Konsolidierung oder klares Rectangle",
                "Entry nahe Level, Stop Loss, Take Profit, CRV >= 1:1",
            ),
            blockers=(
                "keine News und kein sauberes Momentum",
                "nur Volatilitaet ohne Richtung",
                "Entry zu weit vom Level",
                "RVOL fehlt beim News-Breakout",
            ),
        )

    if market == "index":
        setup = "DAX Abpraller" if symbol == "DE40" else "SR Reversal"
        return MorningBriefCandidate(
            symbol=symbol,
            group=asset.group,
            market=market,
            primary_setup=setup,
            direction_thesis="Long nur an bestaetigter Unterstuetzung, Short nur an bestaetigtem Widerstand.",
            earliest_review_time="08:00",
            decision_window="09:00-11:30",
            required_confirmations=(
                "H4/D1/W1 Zone markiert",
                "kein Hochrisiko-Event in direkter Naehe",
                "Limit/Entry vorab geplant",
                "Stop Loss, Take Profit, CRV >= 1:1",
            ),
            blockers=(
                "Zone zu schwach oder frisch gebrochen",
                "Risikoevent direkt bevorstehend",
                "Spread/Kosten zu hoch",
            ),
        )

    if market == "forex":
        return MorningBriefCandidate(
            symbol=symbol,
            group=asset.group,
            market=market,
            primary_setup="FX Trendlinie / SR Reversal",
            direction_thesis="Richtung nur nach stark-gegen-schwach, Sentiment und H4/D1-Level bestimmen.",
            earliest_review_time="08:00",
            decision_window="08:00-11:00",
            required_confirmations=(
                "Sentiment-Konflikte geprueft",
                "keine frischen News oder Hochrisiko-Daten",
                "H4 oder hoeherer Trendlinien-/SR-Kontext",
                "Spread passt zu Ziel und Stop",
            ),
            blockers=(
                "Risikoevent innerhalb von 24 Stunden",
                "Sentiment laeuft extrem gegen die Idee",
                "Trendlinie subjektiv schwach",
            ),
        )

    return MorningBriefCandidate(
        symbol=symbol,
        group=asset.group,
        market=market,
        primary_setup="Nur Beobachtung",
        direction_thesis="Keine Richtung ohne aktuelle Daten und bestaetigtes Setup.",
        earliest_review_time="08:00",
        decision_window="nur nach manuellem Review",
        required_confirmations=(
            "Setup zuerst klassifizieren",
            "Kosten/Spread/Volatilitaet pruefen",
            "Stop Loss, Take Profit, CRV >= 1:1",
        ),
        blockers=("kein definiertes Setup", "keine saubere Datenlage"),
    )


def create_morning_brief(
    watchlist_text: str,
    *,
    generated_for: str = "naechster Handelstag",
    max_candidates: int = 5,
) -> MorningBrief:
    """Create a conservative morning brief from a watchlist export."""

    if max_candidates < 1:
        raise ValueError("max_candidates must be positive")
    assets = parse_tradingview_watchlist(watchlist_text)
    ranked = sorted(assets, key=_priority)
    selected = ranked[:max_candidates]
    rejected = [asset.symbol for asset in ranked[max_candidates:]]
    return MorningBrief(
        title="TradingFreaks Morning Setup Brief",
        generated_for=generated_for,
        candidates=tuple(_candidate_for(asset) for asset in selected),
        data_sources=MORNING_BRIEF_SOURCES,
        rejected_assets=tuple(rejected),
        process_notes=(
            "keine Anlageberatung, keine Kauf-/Verkaufsempfehlung, keine Orderfreigabe.",
            "Wenn aktuelle News-, Kalender- oder Kursdaten fehlen, bleiben alle Assets Screening-Kandidaten.",
            "Kein Trade ohne Stop Loss, Take Profit oder Exit-Regel und CRV >= 1:1.",
            "2-5 Kandidaten sind ein Qualitaetskorridor, kein Tagesziel.",
            "XAGUSD/Silber immer im Metallblock zusammen mit XAUUSD/XAUEUR, USD/Yields und Gold/Silber-Ratio pruefen.",
            "Europe ORB 10:00-12:00 und US Momentum 16:30-18:00 als Sessionfenster beruecksichtigen.",
        ),
    )


def summarize_brief(brief: MorningBrief) -> str:
    """Return a compact markdown-style text summary for notifications."""

    lines = [f"# {brief.title}", "", f"Zeitraum: {brief.generated_for}", ""]
    lines.append("Hinweis: Information und Checklistenunterstuetzung, keine Anlageberatung.")
    lines.append("")
    lines.append("## Datenquellen-Check um 08:00")
    for source in sorted(brief.data_sources, key=lambda item: item.priority):
        access = "kostenpflichtig" if source.paid else "frei/lokal"
        lines.append(f"- {source.name} ({access}): {source.usage}")
    lines.append("")
    for candidate in brief.candidates:
        lines.extend(
            [
                f"## {candidate.symbol} ({candidate.primary_setup})",
                f"- Status: {candidate.status}",
                f"- Zeitfenster: ab {candidate.earliest_review_time}, Entscheidung {candidate.decision_window}",
                f"- Richtungsthese: {candidate.direction_thesis}",
                "- Pflichtbestaetigungen: " + "; ".join(candidate.required_confirmations),
                "- Blocker: " + "; ".join(candidate.blockers),
                "",
            ]
        )
    if brief.rejected_assets:
        lines.append("Weitere Watchlist-Werte nur beobachten: " + ", ".join(brief.rejected_assets))
    return "\n".join(lines)


def assets_by_group(assets: Iterable[WatchlistAsset]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for asset in assets:
        counts[asset.group] = counts.get(asset.group, 0) + 1
    return counts
