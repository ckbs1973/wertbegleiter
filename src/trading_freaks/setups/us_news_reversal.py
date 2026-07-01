"""US stocks news reversal checklist."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from trading_freaks.models import Direction, MarketType, RiskPlan, SetupValidationResult, Timeframe
from trading_freaks.setups.base import attach_risk_plan, condition, warning_text


@dataclass(frozen=True)
class USNewsReversalInput:
    symbol: str
    direction: Direction
    daily_volume: float
    has_news_or_data: bool
    gap_percent: float
    m1_chart_available: bool
    initial_move_against_news_or_extreme_mixed_move: bool
    far_from_vwap: bool
    bottom_or_top_formed: bool
    entry_signal_present: bool
    target_is_vwap_or_technical_level: bool
    room_to_target_for_min_crv: bool
    movement_is_orderly_enough: bool
    entry_not_based_on_hope: bool
    close_by_end_of_day_planned: bool

    def __post_init__(self) -> None:
        if not self.symbol.strip():
            raise ValueError("symbol is required")
        if self.daily_volume < 0:
            raise ValueError("daily_volume must not be negative")


def evaluate_us_news_reversal(
    candidate: USNewsReversalInput,
    *,
    risk_plan: Optional[RiskPlan],
) -> SetupValidationResult:
    checks = [
        condition("Liquide US-Aktie", candidate.daily_volume > 1_000_000),
        condition("News oder Daten vorhanden", candidate.has_news_or_data),
        condition("Vor-/Nachboersenbewegung mindestens 3 Prozent", abs(candidate.gap_percent) >= 3),
        condition("M1-Chart verfuegbar", candidate.m1_chart_available),
        condition("Initialer Lauf gegen News oder extreme Mixed-News-Bewegung", candidate.initial_move_against_news_or_extreme_mixed_move),
        condition("Deutlicher Abstand zum VWAP", candidate.far_from_vwap),
        condition("Boden- oder Topbildung erkennbar", candidate.bottom_or_top_formed),
        condition("Entry-Signal vorhanden", candidate.entry_signal_present),
        condition("Ziel ist VWAP oder technisches Level", candidate.target_is_vwap_or_technical_level),
        condition("Platz zum Ziel fuer CRV >= 1:1", candidate.room_to_target_for_min_crv),
        condition("Bewegung nicht weiter ungeordnet", candidate.movement_is_orderly_enough),
        condition("Entry nicht aus Hoffnung", candidate.entry_not_based_on_hope),
        condition("Intraday-Schliessung ist geplant", candidate.close_by_end_of_day_planned),
    ]
    risk_warnings = attach_risk_plan(checks, risk_plan)

    return SetupValidationResult.from_conditions(
        setup_name="US-Aktien Newstrade Reversal",
        market=MarketType.US_STOCK,
        timeframe_context=Timeframe.M1,
        timeframe_entry=Timeframe.M1,
        direction=candidate.direction,
        conditions=checks,
        entry_logic="Reversal in Richtung News oder Rueckkehr zum VWAP nach Boden-/Topbildung.",
        stop_loss_logic="SL an lokaler Struktur ausserhalb der Boden-/Topbildung.",
        take_profit_logic="VWAP oder naheliegendes technisches Level, nur bei CRV >= 1:1.",
        risk_logic="Positionsgroesse aus RiskPlan; kein Trade ohne gueltigen SL und Exit.",
        invalidation_logic="Nicht handeln ohne Boden/Top, bei ungeordneter Bewegung oder Hoffnungseinstieg.",
        journal_fields=("news_context", "vwap_distance", "reversal_signal", "target_level"),
        warnings=warning_text(risk_warnings),
    )

