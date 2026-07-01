"""Backtest metrics for informational analysis."""

from __future__ import annotations

from math import inf
from typing import Dict, Sequence

from trading_freaks.models import SimulatedTrade


def _average(values: Sequence[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _max_drawdown(rs: Sequence[float]) -> float:
    equity = 0.0
    peak = 0.0
    max_drawdown = 0.0
    for result in rs:
        equity += result
        peak = max(peak, equity)
        max_drawdown = min(max_drawdown, equity - peak)
    return abs(max_drawdown)


def _largest_loss_streak(rs: Sequence[float]) -> int:
    longest = 0
    current = 0
    for result in rs:
        if result < 0:
            current += 1
            longest = max(longest, current)
        else:
            current = 0
    return longest


def calculate_backtest_metrics(trades: Sequence[SimulatedTrade]) -> Dict[str, float]:
    rs = [trade.result_r for trade in trades]
    wins = [result for result in rs if result > 0]
    losses = [result for result in rs if result < 0]
    gross_profit = sum(trade.result_amount for trade in trades if trade.result_amount > 0)
    gross_loss = abs(sum(trade.result_amount for trade in trades if trade.result_amount < 0))
    profit_factor = inf if gross_profit > 0 and gross_loss == 0 else 0.0
    if gross_loss > 0:
        profit_factor = gross_profit / gross_loss
    return {
        "trades": float(len(trades)),
        "win_rate": len(wins) / len(rs) if rs else 0.0,
        "average_r": _average(rs),
        "expectancy_r": _average(rs),
        "average_win_r": _average(wins),
        "average_loss_r": _average(losses),
        "profit_factor": profit_factor,
        "max_drawdown_r": _max_drawdown(rs),
        "largest_loss_streak": float(_largest_loss_streak(rs)),
        "total_result_amount": sum(trade.result_amount for trade in trades),
    }

