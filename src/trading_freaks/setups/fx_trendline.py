"""FX trendline rebound checklist."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from trading_freaks.models import Direction, MarketType, RiskPlan, SetupValidationResult, Timeframe
from trading_freaks.setups.base import attach_risk_plan, condition, warning_text


@dataclass(frozen=True)
class FXTrendlineInput:
    pair: str
    direction: Direction
    daily_g8_g10_screening_done: bool
    timeframe_h4_or_higher: bool
    trendline_touches_before_trade: int
    trade_at_third_touch: bool
    market_is_calm: bool
    sentiment_not_extreme_against_trade: bool
    no_risk_event_today: bool
    no_fresh_currency_news: bool
    order_planned_5_to_10_pips_before_line: bool
    order_type_matches_direction: bool
    spread_cost_ok: bool
    delete_open_limit_before_2300: bool
    daytrade_close_before_day_end: bool

    def __post_init__(self) -> None:
        if not self.pair.strip():
            raise ValueError("pair is required")
        if self.trendline_touches_before_trade < 0:
            raise ValueError("trendline touches must not be negative")


def evaluate_fx_trendline(
    candidate: FXTrendlineInput,
    *,
    risk_plan: Optional[RiskPlan],
) -> SetupValidationResult:
    checks = [
        condition("Taegliches G8/G10-Screening erledigt", candidate.daily_g8_g10_screening_done),
        condition("Trendlinie auf H4 oder hoeher", candidate.timeframe_h4_or_higher),
        condition("Trendlinie hat mindestens zwei vorherige Auflagepunkte", candidate.trendline_touches_before_trade >= 2),
        condition("Trade am dritten Auflagepunkt geplant", candidate.trade_at_third_touch),
        condition("Ruhiger Markt bevorzugt", candidate.market_is_calm),
        condition("Sentiment nicht extrem gegen die Idee", candidate.sentiment_not_extreme_against_trade),
        condition("Kein Risikoevent am selben Tag", candidate.no_risk_event_today),
        condition("Keine frischen News zu einer Waehrung", candidate.no_fresh_currency_news),
        condition("Limit 5-10 Pips vor Trendlinie geplant", candidate.order_planned_5_to_10_pips_before_line),
        condition("Ordertyp passt zur Richtung", candidate.order_type_matches_direction),
        condition("Spread/Kosten im Verhaeltnis zum Ziel ok", candidate.spread_cost_ok),
        condition("Offene Limits vor 23:00 loeschen", candidate.delete_open_limit_before_2300),
        condition("Daytrading-Schliessung vor Tagesende geplant", candidate.daytrade_close_before_day_end),
    ]
    risk_warnings = attach_risk_plan(checks, risk_plan)

    return SetupValidationResult.from_conditions(
        setup_name="FX Trendlinien Setup",
        market=MarketType.FOREX,
        timeframe_context=Timeframe.H4,
        timeframe_entry=Timeframe.H4,
        direction=candidate.direction,
        conditions=checks,
        entry_logic="Buy Limit vor steigender Unterstuetzungslinie oder Sell Limit vor fallender Widerstandslinie.",
        stop_loss_logic="SL vorab geplant, typischerweise 20 bis 50 Pips je nach Stil.",
        take_profit_logic="TP im Bereich 20 bis 50 Pips bzw. CRV ca. 1:1.",
        risk_logic="Orders nur mit SL/TP und gueltigem RiskPlan.",
        invalidation_logic="Nicht handeln bei schwacher Trendlinie, Risikoereignis, frischen News oder extremem Gegensentiment.",
        journal_fields=("trendline_timeframe", "touch_count", "sentiment", "risk_events", "spread_cost"),
        warnings=warning_text(risk_warnings),
    )

