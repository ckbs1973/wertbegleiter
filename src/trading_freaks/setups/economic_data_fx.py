"""FX economic data event checklist."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from trading_freaks.models import Direction, MarketType, RiskPlan, SetupValidationResult, Timeframe
from trading_freaks.setups.base import attach_risk_plan, condition, warning_text


RELEVANT_EVENTS = {
    "inflation",
    "labor_market",
    "central_bank",
    "growth",
    "nfp",
    "cpi",
    "rates",
}


@dataclass(frozen=True)
class EconomicDataFXInput:
    pair: str
    direction: Direction
    event_type: str
    weekly_calendar_checked: bool
    is_g8_g10_pair: bool
    no_position_before_event: bool
    pairs_selected_15m_before: bool
    support_resistance_marked: bool
    data_checked_after_release: bool
    surprise_is_large: bool
    data_is_unified: bool
    momentum_pips: float
    no_simultaneous_buy_sell_stops: bool
    current_spread_pips: float
    planned_target_pips: float

    def __post_init__(self) -> None:
        if not self.pair.strip():
            raise ValueError("pair is required")
        if self.momentum_pips < 0 or self.current_spread_pips < 0 or self.planned_target_pips < 0:
            raise ValueError("pip values must not be negative")


def evaluate_economic_data_fx(
    candidate: EconomicDataFXInput,
    *,
    risk_plan: Optional[RiskPlan],
) -> SetupValidationResult:
    event = candidate.event_type.strip().lower()
    checks = [
        condition("G8/G10-Paar", candidate.is_g8_g10_pair),
        condition("Wirtschaftskalender wurde wochenweise geprueft", candidate.weekly_calendar_checked),
        condition("Relevantes Risikoevent", event in RELEVANT_EVENTS, evidence=event),
        condition("Keine Position vor Eventeroeffnung", candidate.no_position_before_event),
        condition("Zwei passende Paare ca. 15 Minuten vorher ausgewaehlt", candidate.pairs_selected_15m_before),
        condition("Unterstuetzung und Widerstand markiert", candidate.support_resistance_marked),
        condition("Daten nach Veroeffentlichung geprueft", candidate.data_checked_after_release),
        condition("Grosse Abweichung zur Erwartung", candidate.surprise_is_large),
        condition("Daten eindeutig interpretierbar", candidate.data_is_unified),
        condition("Momentum groesser 20 Pips", candidate.momentum_pips > 20, evidence=f"{candidate.momentum_pips} pips"),
        condition("Keine gleichzeitigen Buy- und Sell-Stops", candidate.no_simultaneous_buy_sell_stops),
        condition(
            "Spread im Verhaeltnis zum Ziel vertretbar",
            candidate.planned_target_pips > 0 and candidate.current_spread_pips <= candidate.planned_target_pips * 0.15,
            evidence=f"spread={candidate.current_spread_pips}, target={candidate.planned_target_pips}",
        ),
    ]
    risk_warnings = attach_risk_plan(checks, risk_plan)

    return SetupValidationResult.from_conditions(
        setup_name="Wirtschaftsdaten-Setup FX",
        market=MarketType.FOREX,
        timeframe_context=Timeframe.M5,
        timeframe_entry=Timeframe.M1,
        direction=candidate.direction,
        conditions=checks,
        entry_logic="Nach Datenpruefung Momentum oder Ruecklauf der initialen Bewegung abwarten.",
        stop_loss_logic="SL vor Tradebeginn planen; je nach Stil typischerweise 20 bis 50+ Pips.",
        take_profit_logic="TP oder Exit-Regel vor Tradebeginn; CRV ca. 1:1.",
        risk_logic="Default 1 Prozent Risiko, keine Martingale-Erhoehung nach Verlust.",
        invalidation_logic="Nicht handeln bei gemischten Daten, fehlender Ueberraschung oder fehlendem Momentum.",
        journal_fields=("event_type", "surprise", "data_interpretation", "momentum_pips", "spread_pips"),
        warnings=warning_text(risk_warnings),
    )

