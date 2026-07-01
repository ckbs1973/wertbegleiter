"""US stocks news breakout checklist.

This module evaluates whether a candidate matches the documented checklist.
It does not create recommendations or broker orders.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from trading_freaks.models import (
    Direction,
    MarketType,
    RiskPlan,
    SetupValidationResult,
    Timeframe,
)
from trading_freaks.setups.base import condition, risk_plan_conditions, warning_text


ALLOWED_CONSOLIDATION_PATTERNS = {"flag", "triangle", "range", "sideways"}


@dataclass(frozen=True)
class USNewsBreakoutInput:
    symbol: str
    direction: Direction
    daily_volume: float
    is_penny_stock: bool
    has_news_catalyst: bool
    news_is_mixed: bool
    gap_percent: float
    main_session_started: bool
    momentum_in_news_direction_by_1545: bool
    price_on_correct_vwap_side: bool
    consolidation_minutes: float
    consolidation_is_tight: bool
    correction_fraction_of_momentum: float
    pattern_type: str
    rvol: Optional[float]
    rvol_anticipated: bool
    entry_is_near_breakout: bool
    movement_is_momentum_not_volatility: bool
    close_by_end_of_day_planned: bool
    m1_is_liquid_without_large_gaps: bool = True

    def __post_init__(self) -> None:
        if not self.symbol.strip():
            raise ValueError("symbol is required")
        if self.daily_volume < 0:
            raise ValueError("daily_volume must not be negative")
        if self.consolidation_minutes < 0:
            raise ValueError("consolidation_minutes must not be negative")
        if self.correction_fraction_of_momentum < 0:
            raise ValueError("correction_fraction_of_momentum must not be negative")
        if self.rvol is not None and self.rvol < 0:
            raise ValueError("rvol must not be negative")


def evaluate_us_news_breakout(
    candidate: USNewsBreakoutInput,
    *,
    risk_plan: Optional[RiskPlan],
) -> SetupValidationResult:
    """Evaluate the US news breakout checklist.

    `trade_allowed=True` means only that all encoded checklist rules passed for
    manual review. It is not a buy/sell recommendation.
    """

    pattern = candidate.pattern_type.strip().lower()
    rvol_ok = candidate.rvol is not None and candidate.rvol > 1.5
    rvol_or_anticipation_ok = rvol_ok or candidate.rvol_anticipated

    checks = [
        condition(
            "Liquide US-Aktie mit Tagesvolumen > 1 Mio.",
            candidate.daily_volume > 1_000_000,
            evidence=f"daily_volume={candidate.daily_volume}",
        ),
        condition(
            "Kein Penny Stock",
            not candidate.is_penny_stock,
        ),
        condition(
            "M1-Chart ausreichend liquide ohne grosse Gaps",
            candidate.m1_is_liquid_without_large_gaps,
        ),
        condition(
            "Echter News-Katalysator vorhanden",
            candidate.has_news_catalyst,
        ),
        condition(
            "News sind nicht mixed",
            not candidate.news_is_mixed,
        ),
        condition(
            "Vor-/Nachboersenbewegung mindestens 3 Prozent",
            abs(candidate.gap_percent) >= 3.0,
            evidence=f"gap_percent={candidate.gap_percent}",
        ),
        condition(
            "US-Hauptsession hat begonnen",
            candidate.main_session_started,
        ),
        condition(
            "Momentum bis ca. 15:45 Uhr in News-Richtung",
            candidate.momentum_in_news_direction_by_1545,
        ),
        condition(
            "Momentum statt blosser Volatilitaet",
            candidate.movement_is_momentum_not_volatility,
        ),
        condition(
            "Kurs auf korrekter VWAP-Seite",
            candidate.price_on_correct_vwap_side,
            evidence="Long oberhalb VWAP, Short unterhalb VWAP",
        ),
        condition(
            "Enge Konsolidierung mindestens 5 Minuten",
            candidate.consolidation_minutes >= 5 and candidate.consolidation_is_tight,
            evidence=f"minutes={candidate.consolidation_minutes}",
        ),
        condition(
            "Korrektur maximal ein Drittel der Momentumstrecke",
            candidate.correction_fraction_of_momentum <= (1 / 3),
            evidence=f"fraction={candidate.correction_fraction_of_momentum:.3f}",
        ),
        condition(
            "Erlaubtes Konsolidierungsmuster",
            pattern in ALLOWED_CONSOLIDATION_PATTERNS,
            evidence=pattern or "missing",
        ),
        condition(
            "Ausbruch mit RVOL > 1.5 oder plausibler Antizipation",
            rvol_or_anticipation_ok,
            evidence=f"rvol={candidate.rvol}, anticipated={candidate.rvol_anticipated}",
        ),
        condition(
            "Entry nahe am Ausbruchslevel",
            candidate.entry_is_near_breakout,
        ),
        condition(
            "Intraday-Schliessung ist geplant",
            candidate.close_by_end_of_day_planned,
        ),
    ]

    warnings = []
    if candidate.rvol_anticipated and not rvol_ok:
        warnings.append("RVOL wurde antizipiert; nach Kerzenschluss nachpruefen")

    if risk_plan is None:
        checks.extend(
            [
                condition("RiskPlan ist vorhanden", False, evidence="missing"),
                condition("Stop Loss ist vorhanden", False, evidence="missing"),
                condition("Exit-Plan ist vorhanden", False, evidence="missing"),
            ]
        )
    else:
        checks.extend(risk_plan_conditions(risk_plan))
        warnings = warning_text(warnings, risk_plan.warnings)

    return SetupValidationResult.from_conditions(
        setup_name="US-Aktien Newstrade Breakout",
        market=MarketType.US_STOCK,
        timeframe_context=Timeframe.M1,
        timeframe_entry=Timeframe.M1,
        direction=candidate.direction,
        conditions=checks,
        entry_logic="Ausbruch aus enger Konsolidierung in News-Richtung nahe Breakout-Level.",
        stop_loss_logic="Stop Loss an lokaler Struktur; Long unter Entry, Short ueber Entry.",
        take_profit_logic="Vorab geplanter TP oder Exit-Regel, mindestens CRV 1:1.",
        risk_logic="Positionsgroesse aus Kontostand, Risiko-Prozent, Entry, Stop und Unit Value.",
        invalidation_logic=(
            "Kein Setup bei mixed News, fehlendem Momentum, tiefer Korrektur, fehlendem RVOL "
            "oder Entry weit weg vom Ausbruch."
        ),
        journal_fields=(
            "news_catalyst",
            "gap_percent",
            "vwap_side",
            "consolidation_minutes",
            "correction_fraction_of_momentum",
            "rvol",
            "entry_distance_to_breakout",
            "planned_risk",
            "screenshots_before_after",
        ),
        warnings=warnings,
    )

