"""Conservative bracket-order trade simulation."""

from __future__ import annotations

from typing import Sequence

from trading_freaks.models import Candle, Direction, SimulatedTrade


def _entry_price(
    direction: Direction,
    raw_price: float,
    half_spread: float,
    slippage_per_unit: float,
) -> float:
    if direction is Direction.LONG:
        return raw_price + half_spread + slippage_per_unit
    return raw_price - half_spread - slippage_per_unit


def _exit_price(direction: Direction, raw_price: float, slippage_per_unit: float) -> float:
    if direction is Direction.LONG:
        return raw_price - slippage_per_unit
    return raw_price + slippage_per_unit


def _result_amount(
    *,
    direction: Direction,
    entry: float,
    exit_price: float,
    position_size: float,
    fees: float,
) -> float:
    if direction is Direction.LONG:
        gross = (exit_price - entry) * position_size
    else:
        gross = (entry - exit_price) * position_size
    return gross - fees


def simulate_bracket_trade(
    *,
    symbol: str,
    setup_name: str,
    direction: Direction,
    entry: float,
    stop_loss: float,
    take_profit: float,
    position_size: float,
    future_candles: Sequence[Candle],
    fees: float = 0.0,
    spread_per_unit: float = 0.0,
    slippage_per_unit: float = 0.0,
) -> SimulatedTrade:
    """Simulate a trade from future candles only.

    If stop and target are both touched within the same candle, the simulator
    chooses the stop. Without intrabar data this is the conservative outcome.
    """

    if not future_candles:
        raise ValueError("future_candles are required")
    if entry <= 0 or stop_loss <= 0 or take_profit <= 0:
        raise ValueError("entry, stop_loss and take_profit must be positive")
    if position_size <= 0:
        raise ValueError("position_size must be positive")
    if fees < 0 or spread_per_unit < 0 or slippage_per_unit < 0:
        raise ValueError("fees, spread_per_unit and slippage_per_unit must not be negative")
    if direction is Direction.LONG:
        if stop_loss >= entry or take_profit <= entry:
            raise ValueError("long bracket requires stop below entry and target above entry")
    else:
        if stop_loss <= entry or take_profit >= entry:
            raise ValueError("short bracket requires stop above entry and target below entry")

    opened_at = future_candles[0].timestamp
    exit_level = future_candles[-1].close
    exit_time = future_candles[-1].timestamp
    exit_reason = "time_exit"

    for candle in future_candles:
        if direction is Direction.LONG:
            stop_hit = candle.low <= stop_loss
            target_hit = candle.high >= take_profit
        else:
            stop_hit = candle.high >= stop_loss
            target_hit = candle.low <= take_profit

        if stop_hit:
            exit_level = stop_loss
            exit_time = candle.timestamp
            exit_reason = "stop_loss_conservative_same_bar" if target_hit else "stop_loss"
            break
        if target_hit:
            exit_level = take_profit
            exit_time = candle.timestamp
            exit_reason = "take_profit"
            break

    half_spread = spread_per_unit / 2
    actual_entry_price = _entry_price(direction, entry, half_spread, slippage_per_unit)
    actual_exit_price = _exit_price(direction, exit_level, half_spread + slippage_per_unit)
    amount = _result_amount(
        direction=direction,
        entry=actual_entry_price,
        exit_price=actual_exit_price,
        position_size=position_size,
        fees=fees,
    )
    initial_risk = abs(actual_entry_price - stop_loss) * position_size
    result_r = amount / initial_risk if initial_risk else 0.0
    return SimulatedTrade(
        symbol=symbol,
        setup_name=setup_name,
        direction=direction,
        opened_at=opened_at,
        closed_at=exit_time,
        entry=actual_entry_price,
        stop_loss=stop_loss,
        take_profit=take_profit,
        position_size=position_size,
        exit_price=actual_exit_price,
        result_amount=amount,
        result_r=result_r,
        exit_reason=exit_reason,
        fees=fees,
        slippage=slippage_per_unit + spread_per_unit,
    )
