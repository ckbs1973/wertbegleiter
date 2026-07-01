"""Daily trading update gatekeeper for manual decision support.

The module plans a trading day around process gates, risk sizing and journal
readiness. It does not produce broker instructions or investment advice.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import time
from typing import Sequence, Tuple

from trading_freaks.models import (
    ChecklistCondition,
    Direction,
    MarketType,
    RiskPlan,
    TradingStyle,
)
from trading_freaks.risk.position_sizing import calculate_risk_plan
from trading_freaks.session_playbook import imported_rule_summary_lines


US_MAIN_OPEN = time(15, 30)
US_FIRST_CANDLE_DONE = time(15, 35)
US_SCALP_CUTOFF = time(20, 0)
US_INTRADAY_CLOSE = time(21, 59)


def _as_tuple(values: Sequence[str]) -> Tuple[str, ...]:
    return tuple(values)


@dataclass(frozen=True)
class DailyTradingContext:
    account_equity: float
    trades_taken_today: int = 0
    max_trades_per_day: int = 5
    target_min_trades: int = 2
    target_max_trades: int = 5
    default_risk_percent: float = 1.0
    psychology_ready: bool = True
    daily_loss_limit_reached: bool = False
    weekly_loss_limit_reached: bool = False
    loss_streak: int = 0
    correlated_exposure_warning: bool = False

    def __post_init__(self) -> None:
        if self.account_equity <= 0:
            raise ValueError("account_equity must be positive")
        if self.trades_taken_today < 0:
            raise ValueError("trades_taken_today must not be negative")
        if self.max_trades_per_day <= 0:
            raise ValueError("max_trades_per_day must be positive")
        if self.target_min_trades < 0 or self.target_max_trades < self.target_min_trades:
            raise ValueError("target trade corridor is invalid")
        if self.default_risk_percent <= 0:
            raise ValueError("default_risk_percent must be positive")
        if self.loss_streak < 0:
            raise ValueError("loss_streak must not be negative")


@dataclass(frozen=True)
class DailyTradeCandidate:
    candidate_id: str
    symbol: str
    setup_name: str
    market: MarketType
    direction: Direction
    style: TradingStyle
    planned_time: time
    entry: float
    stop_loss: float
    take_profit: float
    unit_value: float = 1.0
    risk_percent: float | None = None
    required_conditions: Tuple[ChecklistCondition, ...] = field(default_factory=tuple)
    notes: Tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not self.candidate_id.strip():
            raise ValueError("candidate_id is required")
        if not self.symbol.strip():
            raise ValueError("symbol is required")
        if not self.setup_name.strip():
            raise ValueError("setup_name is required")
        if self.entry <= 0 or self.stop_loss <= 0 or self.take_profit <= 0:
            raise ValueError("entry, stop_loss and take_profit must be positive")
        if self.unit_value <= 0:
            raise ValueError("unit_value must be positive")
        object.__setattr__(self, "required_conditions", tuple(self.required_conditions))
        object.__setattr__(self, "notes", _as_tuple(self.notes))


@dataclass(frozen=True)
class DailyCandidateEvaluation:
    candidate_id: str
    symbol: str
    setup_name: str
    planned_time: str
    status: str
    decision_text: str
    failed_conditions: Tuple[str, ...]
    passed_conditions: Tuple[str, ...]
    warnings: Tuple[str, ...]
    risk_plan: RiskPlan
    completion_score: float
    information_only: bool = True

    def __post_init__(self) -> None:
        object.__setattr__(self, "failed_conditions", _as_tuple(self.failed_conditions))
        object.__setattr__(self, "passed_conditions", _as_tuple(self.passed_conditions))
        object.__setattr__(self, "warnings", _as_tuple(self.warnings))
        if self.status != "nicht_handeln" and self.failed_conditions:
            raise ValueError("candidate with failed conditions must be blocked")
        if not self.information_only:
            raise ValueError("daily update must remain information-only")


@dataclass(frozen=True)
class DailyTradingUpdate:
    status: str
    trade_slots_remaining: int
    target_trade_corridor: str
    warnings: Tuple[str, ...]
    notes: Tuple[str, ...]
    candidates: Tuple[DailyCandidateEvaluation, ...]
    information_only: bool = True

    def __post_init__(self) -> None:
        object.__setattr__(self, "warnings", _as_tuple(self.warnings))
        object.__setattr__(self, "notes", _as_tuple(self.notes))
        object.__setattr__(self, "candidates", tuple(self.candidates))
        if not self.information_only:
            raise ValueError("daily update must remain information-only")


def _time_label(value: time) -> str:
    return value.strftime("%H:%M")


def _candidate_time_warnings(candidate: DailyTradeCandidate) -> list[str]:
    warnings: list[str] = []
    if candidate.market is MarketType.US_STOCK and candidate.style is TradingStyle.SCALPING:
        if candidate.planned_time < US_MAIN_OPEN:
            warnings.append("US-Aktien-Scalping erst ab Hauptsession 15:30 pruefen")
        elif candidate.planned_time < US_FIRST_CANDLE_DONE:
            warnings.append("Keine erste 5-Minuten-Kerze im US-Open handeln")
        if candidate.planned_time > US_SCALP_CUTOFF:
            warnings.append("Kein neuer US-Aktien-Scalp nach 20:00 planen")
        if candidate.planned_time > US_INTRADAY_CLOSE:
            warnings.append("Intraday-Positionen muessen vor 21:59 geschlossen sein")
    return warnings


def _context_blockers(context: DailyTradingContext) -> list[str]:
    blockers: list[str] = []
    if context.trades_taken_today >= context.max_trades_per_day:
        blockers.append("Tageslimit fuer Trades erreicht")
    if not context.psychology_ready:
        blockers.append("Psychologie-Check blockiert den Tradingtag")
    if context.daily_loss_limit_reached:
        blockers.append("Maximalverlust pro Tag erreicht")
    if context.weekly_loss_limit_reached:
        blockers.append("Maximalverlust pro Woche erreicht")
    if context.loss_streak >= 3:
        blockers.append("Verlustserie >= 3: Pause und Review erforderlich")
    return blockers


def _completion_score(conditions: Sequence[ChecklistCondition], risk_plan: RiskPlan) -> float:
    required = [condition for condition in conditions if condition.required]
    if not required:
        condition_score = 100.0
    else:
        passed = [condition for condition in required if condition.passed]
        condition_score = (len(passed) / len(required)) * 100
    if not risk_plan.is_valid:
        condition_score = min(condition_score, 60.0)
    return round(condition_score, 2)


def evaluate_daily_trading_update(
    *,
    context: DailyTradingContext,
    candidates: Sequence[DailyTradeCandidate],
) -> DailyTradingUpdate:
    """Evaluate daily candidates under conservative TradingFreaks gates."""

    notes = [
        "2-5 Trades sind ein Qualitaetskorridor, kein monetaeres Tagesziel.",
        "Scalping ist die fuehrende Strategie; jede Idee braucht SL, TP oder Exit-Regel und CRV >= 1:1.",
        "Alle Kandidaten bleiben Information und Checklistenunterstuetzung, keine Orderfreigabe.",
    ]
    notes.extend(imported_rule_summary_lines())
    warnings: list[str] = []
    if context.correlated_exposure_warning:
        warnings.append("Mehrere korrelierte Ideen erkannt: Long-/Short- und Asset-Cluster pruefen")
    if context.default_risk_percent > 1.0:
        warnings.append("Default-Risiko ueber 1%; Schutzmodus pruefen")

    context_blockers = _context_blockers(context)
    warnings.extend(context_blockers)
    remaining_slots = max(0, context.max_trades_per_day - context.trades_taken_today)

    evaluations = []
    for candidate in candidates:
        risk_plan = calculate_risk_plan(
            account_equity=context.account_equity,
            risk_percent=candidate.risk_percent or context.default_risk_percent,
            direction=candidate.direction,
            entry=candidate.entry,
            stop_loss=candidate.stop_loss,
            take_profit=candidate.take_profit,
            unit_value=candidate.unit_value,
        )
        required_failed = [
            condition.name
            for condition in candidate.required_conditions
            if condition.required and not condition.passed
        ]
        passed = [condition.name for condition in candidate.required_conditions if condition.passed]
        candidate_warnings = _candidate_time_warnings(candidate)
        candidate_warnings.extend(risk_plan.warnings)

        failed = list(required_failed)
        failed.extend(risk_plan.errors)
        failed.extend(context_blockers)
        failed.extend(candidate_warnings)

        status = "trade_erlaubt_zur_manuellen_pruefung"
        decision_text = "Alle Pflichtkriterien erfuellt; nur manuelle Pruefung, keine Orderfreigabe."
        if failed:
            status = "nicht_handeln"
            decision_text = "Nicht handeln: " + "; ".join(failed)

        evaluations.append(
            DailyCandidateEvaluation(
                candidate_id=candidate.candidate_id,
                symbol=candidate.symbol,
                setup_name=candidate.setup_name,
                planned_time=_time_label(candidate.planned_time),
                status=status,
                decision_text=decision_text,
                failed_conditions=tuple(failed),
                passed_conditions=tuple(passed),
                warnings=tuple(candidate_warnings),
                risk_plan=risk_plan,
                completion_score=_completion_score(candidate.required_conditions, risk_plan),
            )
        )

    valid_count = len([candidate for candidate in evaluations if candidate.status != "nicht_handeln"])
    if valid_count > remaining_slots:
        warnings.append("Mehr gueltige Kandidaten als freie Tages-Slots; nur die besten Setups manuell priorisieren")

    status = "arbeitsbereit"
    if context_blockers:
        status = "trading_pause_empfohlen"
    elif not evaluations:
        status = "nur_beobachten"

    return DailyTradingUpdate(
        status=status,
        trade_slots_remaining=remaining_slots,
        target_trade_corridor=f"{context.target_min_trades}-{context.target_max_trades}",
        warnings=tuple(warnings),
        notes=tuple(notes),
        candidates=tuple(evaluations),
    )
