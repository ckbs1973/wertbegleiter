"""Shared setup helpers."""

from __future__ import annotations

from typing import Iterable, List, Optional, Sequence

from trading_freaks.models import ChecklistCondition, RiskPlan


def condition(name: str, passed: bool, evidence: str = "", required: bool = True) -> ChecklistCondition:
    return ChecklistCondition(name=name, passed=passed, evidence=evidence, required=required)


def risk_plan_conditions(risk_plan: RiskPlan) -> List[ChecklistCondition]:
    checks = [
        condition(
            "RiskPlan ist gueltig",
            risk_plan.is_valid,
            evidence="; ".join(risk_plan.errors) if risk_plan.errors else "OK",
        ),
        condition(
            "Stop Loss ist vorhanden",
            risk_plan.stop_loss > 0,
            evidence=f"SL={risk_plan.stop_loss}",
        ),
        condition(
            "Exit-Plan ist vorhanden",
            risk_plan.take_profit is not None or bool(risk_plan.exit_rule),
            evidence=risk_plan.exit_rule or f"TP={risk_plan.take_profit}",
        ),
    ]
    if risk_plan.crv is not None:
        checks.append(
            condition(
                "CRV mindestens 1:1",
                risk_plan.crv >= 1.0,
                evidence=f"CRV={risk_plan.crv:.2f}",
            )
        )
    return checks


def attach_risk_plan(
    checks: List[ChecklistCondition],
    risk_plan: Optional[RiskPlan],
) -> List[str]:
    if risk_plan is None:
        checks.extend(
            [
                condition("RiskPlan ist vorhanden", False, evidence="missing"),
                condition("Stop Loss ist vorhanden", False, evidence="missing"),
                condition("Exit-Plan ist vorhanden", False, evidence="missing"),
            ]
        )
        return []

    checks.extend(risk_plan_conditions(risk_plan))
    return list(risk_plan.warnings)


def no_reasons(reasons: Sequence[bool]) -> bool:
    return not any(reasons)


def warning_text(*groups: Iterable[str]) -> List[str]:
    warnings: List[str] = []
    for group in groups:
        warnings.extend(str(item) for item in group if str(item))
    return warnings
