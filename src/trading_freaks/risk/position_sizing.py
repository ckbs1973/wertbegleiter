"""Position sizing with conservative TradingFreaks-style guardrails."""

from __future__ import annotations

from typing import Optional

from trading_freaks.models import Direction, RiskPlan


def calculate_risk_plan(
    *,
    account_equity: float,
    risk_percent: float,
    direction: Direction,
    entry: float,
    stop_loss: Optional[float],
    take_profit: Optional[float] = None,
    exit_rule: Optional[str] = None,
    unit_value: float = 1.0,
    product_leverage: Optional[float] = None,
    max_risk_percent: float = 5.0,
    warn_risk_percent: float = 1.0,
    warn_position_leverage: float = 10.0,
    min_crv: float = 1.0,
) -> RiskPlan:
    """Calculate a RiskPlan without producing an execution recommendation.

    `unit_value` represents the currency value of one price-unit move per one
    position unit. For US stocks it is usually 1. For FX/indices it should be
    provided by the instrument adapter once implemented.
    """

    errors = []
    warnings = []

    if account_equity <= 0:
        errors.append("account_equity must be positive")
    if risk_percent <= 0:
        errors.append("risk_percent must be positive")
    if risk_percent > max_risk_percent:
        errors.append(f"risk_percent must not exceed {max_risk_percent}%")
    elif risk_percent > warn_risk_percent:
        warnings.append("risk_percent above 1%; protective review required")
    if entry <= 0:
        errors.append("entry must be positive")
    if stop_loss is None or stop_loss <= 0:
        errors.append("stop_loss is required and must be positive")
        stop_loss_value = 0.0
    else:
        stop_loss_value = stop_loss
    if unit_value <= 0:
        errors.append("unit_value must be positive")
    if take_profit is None and not exit_rule:
        errors.append("take_profit or explicit exit_rule is required")
    if product_leverage is not None and product_leverage <= 0:
        errors.append("product_leverage must be positive when provided")

    if stop_loss is not None and stop_loss > 0 and entry > 0:
        if direction is Direction.LONG and stop_loss >= entry:
            errors.append("long stop_loss must be below entry")
        if direction is Direction.SHORT and stop_loss <= entry:
            errors.append("short stop_loss must be above entry")

    if take_profit is not None and entry > 0:
        if direction is Direction.LONG and take_profit <= entry:
            errors.append("long take_profit must be above entry")
        if direction is Direction.SHORT and take_profit >= entry:
            errors.append("short take_profit must be below entry")

    risk_amount = account_equity * (risk_percent / 100) if account_equity > 0 else 0.0
    risk_per_unit = abs(entry - stop_loss_value) * unit_value if entry > 0 else 0.0
    position_size = risk_amount / risk_per_unit if risk_per_unit > 0 and not errors else 0.0

    planned_reward = None
    crv = None
    if take_profit is not None and entry > 0 and unit_value > 0:
        planned_reward = abs(take_profit - entry) * unit_value * position_size
        crv = planned_reward / risk_amount if risk_amount > 0 else None
        if crv is not None and crv < min_crv:
            errors.append(f"planned CRV must be at least {min_crv}:1")

    notional = abs(position_size * entry) if position_size else 0.0
    position_leverage = notional / account_equity if account_equity > 0 and notional else None
    margin_required = None
    if product_leverage and notional:
        margin_required = notional / product_leverage
        if margin_required > account_equity:
            warnings.append("margin_required exceeds account equity")

    if position_leverage is not None and position_leverage > warn_position_leverage:
        warnings.append("position_leverage above 1:10 protective threshold")

    is_valid = not errors
    return RiskPlan(
        account_equity=account_equity,
        risk_percent=risk_percent,
        risk_amount=risk_amount,
        direction=direction,
        entry=entry,
        stop_loss=stop_loss_value,
        take_profit=take_profit,
        exit_rule=exit_rule,
        risk_per_unit=risk_per_unit,
        position_size=position_size,
        planned_reward=planned_reward,
        crv=crv,
        position_leverage=position_leverage,
        product_leverage=product_leverage,
        margin_required=margin_required,
        is_valid=is_valid,
        warnings=tuple(warnings),
        errors=tuple(errors),
    )

