"""Backtesting helpers with explicit no-lookahead boundaries."""

from trading_freaks.backtesting.backtest_engine import BacktestEngine, StrategyDecision
from trading_freaks.backtesting.metrics import calculate_backtest_metrics
from trading_freaks.backtesting.trade_simulator import simulate_bracket_trade

__all__ = [
    "BacktestEngine",
    "StrategyDecision",
    "calculate_backtest_metrics",
    "simulate_bracket_trade",
]

