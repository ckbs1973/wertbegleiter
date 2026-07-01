"""US stocks rectangle continuation checklist."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from trading_freaks.models import Direction, MarketType, RiskPlan, SetupValidationResult, Timeframe
from trading_freaks.setups.base import attach_risk_plan, condition, warning_text


@dataclass(frozen=True)
class RectangleInput:
    symbol: str
    direction: Direction
    daily_volume: float
    is_penny_stock: bool
    has_m1_intraday_gaps: bool
    prior_move_is_momentum: bool
    correction_fraction_of_momentum: float
    correction_candles: int
    is_horizontal_range: bool
    is_flag_or_triangle: bool
    rectangle_clear: bool
    upper_touches: int
    lower_touches: int
    entry_near_rectangle_edge: bool
    exit_at_crv_one_or_trailing_allowed: bool

    def __post_init__(self) -> None:
        if not self.symbol.strip():
            raise ValueError("symbol is required")
        if self.daily_volume < 0 or self.correction_fraction_of_momentum < 0:
            raise ValueError("volume and correction fraction must not be negative")
        if self.correction_candles < 0 or self.upper_touches < 0 or self.lower_touches < 0:
            raise ValueError("counts must not be negative")


def evaluate_rectangle(
    candidate: RectangleInput,
    *,
    risk_plan: Optional[RiskPlan],
) -> SetupValidationResult:
    touches_ok = candidate.upper_touches >= 2 and candidate.lower_touches >= 2
    checks = [
        condition("Liquide US-Aktie mit Tagesvolumen > 1 Mio.", candidate.daily_volume > 1_000_000),
        condition("Kein Penny Stock", not candidate.is_penny_stock),
        condition("Keine grossen M1-Intraday-Gaps", not candidate.has_m1_intraday_gaps),
        condition("Vorheriges Momentum statt Volatilitaet", candidate.prior_move_is_momentum),
        condition("Korrektur maximal ein Drittel der Momentumstrecke", candidate.correction_fraction_of_momentum <= (1 / 3)),
        condition("Korrektur mindestens 6 Kerzen", candidate.correction_candles >= 6),
        condition("Horizontale Seitwaertsphase", candidate.is_horizontal_range),
        condition("Keine Flagge oder Dreieck", not candidate.is_flag_or_triangle),
        condition("Rectangle klar abgrenzbar", candidate.rectangle_clear),
        condition("Mindestens zwei Auflagepunkte oben und unten", touches_ok),
        condition("Entry nahe Rectangle-Kante", candidate.entry_near_rectangle_edge),
        condition("Exit bei CRV 1:1 oder erlaubtem Trailing geplant", candidate.exit_at_crv_one_or_trailing_allowed),
    ]
    risk_warnings = attach_risk_plan(checks, risk_plan)

    return SetupValidationResult.from_conditions(
        setup_name="Rectangle Setup US-Aktien Scalping",
        market=MarketType.US_STOCK,
        timeframe_context=Timeframe.M1,
        timeframe_entry=Timeframe.M1,
        direction=candidate.direction,
        conditions=checks,
        entry_logic="Buy Stop ueber Rectangle-Oberkante oder Sell Stop unter Rectangle-Unterkante.",
        stop_loss_logic="SL knapp auf der Gegenseite des Rectangles.",
        take_profit_logic="Exit bei CRV 1:1 oder setup-konformem Teilverkauf/Trailing.",
        risk_logic="Scalping-Risiko aus gueltigem RiskPlan; kein Volumenfilter erforderlich.",
        invalidation_logic="Nicht handeln bei Volatilitaet ohne Momentum, tiefer Korrektur oder unklarem Rectangle.",
        journal_fields=("momentum_leg", "correction_depth", "range_candles", "upper_touches", "lower_touches"),
        warnings=warning_text(risk_warnings),
    )

