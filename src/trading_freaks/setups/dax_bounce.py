"""DAX support/resistance bounce checklist."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from trading_freaks.models import Direction, MarketType, RiskPlan, SetupValidationResult, Timeframe
from trading_freaks.setups.base import attach_risk_plan, condition, warning_text


@dataclass(frozen=True)
class DAXBounceInput:
    symbol: str
    direction: Direction
    is_dax_or_supported_index_commodity: bool
    purely_technical_no_news: bool
    h4_d1_w1_zones_identified: bool
    zone_strength_confirmed: bool
    economic_calendar_checked: bool
    no_nearby_risk_event: bool
    order_10_to_15_points_before_zone: bool
    limit_order_allowed_by_plan: bool
    target_points_planned: float
    crv_minimum_possible: bool
    screenshots_planned: bool

    def __post_init__(self) -> None:
        if not self.symbol.strip():
            raise ValueError("symbol is required")
        if self.target_points_planned < 0:
            raise ValueError("target_points_planned must not be negative")


def evaluate_dax_bounce(
    candidate: DAXBounceInput,
    *,
    risk_plan: Optional[RiskPlan],
) -> SetupValidationResult:
    checks = [
        condition("DAX oder unterstuetzter Index/Rohstoff", candidate.is_dax_or_supported_index_commodity),
        condition("Rein technisches Setup ohne News", candidate.purely_technical_no_news),
        condition("H4/D1/W1-Zonen identifiziert", candidate.h4_d1_w1_zones_identified),
        condition("Zone ist stark genug", candidate.zone_strength_confirmed),
        condition("Wirtschaftskalender geprueft", candidate.economic_calendar_checked),
        condition("Kein Risikoevent in direkter Naehe", candidate.no_nearby_risk_event),
        condition("Order 10-15 Punkte vor Zone geplant", candidate.order_10_to_15_points_before_zone),
        condition("Limit-Order ist im Plan erlaubt", candidate.limit_order_allowed_by_plan),
        condition("Zielpunkte geplant", candidate.target_points_planned >= 50),
        condition("CRV mindestens 1:1 moeglich", candidate.crv_minimum_possible),
        condition("Screenshots fuer Journal geplant", candidate.screenshots_planned),
    ]
    risk_warnings = attach_risk_plan(checks, risk_plan)

    return SetupValidationResult.from_conditions(
        setup_name="DAX Abpraller",
        market=MarketType.INDEX,
        timeframe_context=Timeframe.H4,
        timeframe_entry=Timeframe.M5,
        direction=candidate.direction,
        conditions=checks,
        entry_logic="Limit 10-15 Punkte vor starker Unterstuetzung oder Widerstand.",
        stop_loss_logic="SL ausserhalb der Zone mit vorher berechnetem Risiko.",
        take_profit_logic="Scalper ca. 50 Punkte, Daytrader ca. 100 Punkte, Swing >300 Punkte; mindestens CRV 1:1.",
        risk_logic="Mindestens 50-100 Tests vor Fazit; keine Aussage aus Einzeltrade ableiten.",
        invalidation_logic="Nicht handeln bei News-/Risikoeventnaehe, schwacher Zone oder fehlendem CRV.",
        journal_fields=("zone_timeframe", "zone_strength", "calendar_check", "target_points", "screenshots"),
        warnings=warning_text(risk_warnings),
    )

