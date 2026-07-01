"""US stocks premarket high/low breakout checklist."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from trading_freaks.models import Direction, MarketType, RiskPlan, SetupValidationResult, Timeframe
from trading_freaks.setups.base import attach_risk_plan, condition, warning_text


@dataclass(frozen=True)
class PremarketHighLowInput:
    symbol: str
    direction: Direction
    has_news_catalyst: bool
    premarket_trend_in_breakout_direction: bool
    gap_percent: float
    strong_opening_drive: bool
    high_liquidity: bool
    m1_clean_after_1430: bool
    premarket_level_formed_by_1525: bool
    consolidation_after_level: bool
    no_premarket_trade_taken: bool
    entry_near_breakout_level: bool
    optional_hold_check_passed: bool
    close_intraday_planned: bool

    def __post_init__(self) -> None:
        if not self.symbol.strip():
            raise ValueError("symbol is required")


def evaluate_premarket_high_low(
    candidate: PremarketHighLowInput,
    *,
    risk_plan: Optional[RiskPlan],
) -> SetupValidationResult:
    level_name = "vorboersliches Hoch" if candidate.direction is Direction.LONG else "vorboersliches Tief"
    checks = [
        condition("News-Katalysator vorhanden", candidate.has_news_catalyst),
        condition("Vorboerse trendet in Ausbruchsrichtung", candidate.premarket_trend_in_breakout_direction),
        condition("Bewegung mindestens 3 Prozent zum Vortagesschluss", abs(candidate.gap_percent) >= 3),
        condition("Starker Opening Drive", candidate.strong_opening_drive),
        condition("Hohe Liquiditaet", candidate.high_liquidity),
        condition("M1 nach ca. 14:30 ohne grosse Gaps", candidate.m1_clean_after_1430),
        condition(f"{level_name} bis 15:25 entstanden", candidate.premarket_level_formed_by_1525),
        condition("Konsolidierung nach dem vorboerslichen Level", candidate.consolidation_after_level),
        condition("Keine Vorboersen-Position eroeffnet", candidate.no_premarket_trade_taken),
        condition("Entry nahe am Ausbruchslevel", candidate.entry_near_breakout_level),
        condition("Optionaler 5-10 Sekunden Halt-Check bestanden", candidate.optional_hold_check_passed),
        condition("Intraday-Schliessung geplant", candidate.close_intraday_planned),
    ]
    risk_warnings = attach_risk_plan(checks, risk_plan)

    return SetupValidationResult.from_conditions(
        setup_name="Vorboersliches Hoch/Tief Breakout",
        market=MarketType.US_STOCK,
        timeframe_context=Timeframe.M1,
        timeframe_entry=Timeframe.M1,
        direction=candidate.direction,
        conditions=checks,
        entry_logic=f"Ausbruch durch {level_name}; kein M1-Schlusskurs zwingend.",
        stop_loss_logic="SL an lokaler Struktur auf der Gegenseite.",
        take_profit_logic="Vorab geplanter Exit, typischerweise CRV ca. 1:1.",
        risk_logic="Nur mit gueltigem RiskPlan; Vorboerse dient nur als Indikator.",
        invalidation_logic="Nicht handeln ohne News, Opening Drive, sauberes Level oder Entry-Naehe.",
        journal_fields=("premarket_level", "opening_drive", "entry_distance", "hold_check"),
        warnings=warning_text(risk_warnings),
    )

