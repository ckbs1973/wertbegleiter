"""Minimal backtest runner that prevents strategy lookahead by construction."""

from __future__ import annotations

from typing import Callable, Optional, Sequence, Tuple

from trading_freaks.backtesting.metrics import calculate_backtest_metrics
from trading_freaks.backtesting.trade_simulator import simulate_bracket_trade
from trading_freaks.models import BacktestDecision, BacktestResult, Candle, SimulatedTrade


StrategyDecision = Callable[[Tuple[Candle, ...]], Optional[BacktestDecision]]


class BacktestEngine:
    """Run a strategy callback with history-only candle slices.

    The strategy receives `candles[:i + 1]`, never future candles. Any resulting
    trade is simulated from `candles[i + 1:]`.
    """

    def __init__(
        self,
        *,
        max_holding_bars: Optional[int] = None,
        fees: float = 0.0,
        spread_per_unit: float = 0.0,
        slippage_per_unit: float = 0.0,
    ) -> None:
        if max_holding_bars is not None and max_holding_bars <= 0:
            raise ValueError("max_holding_bars must be positive")
        if fees < 0 or spread_per_unit < 0 or slippage_per_unit < 0:
            raise ValueError("fees, spread_per_unit and slippage_per_unit must not be negative")
        self.max_holding_bars = max_holding_bars
        self.fees = fees
        self.spread_per_unit = spread_per_unit
        self.slippage_per_unit = slippage_per_unit

    def run(
        self,
        *,
        candles: Sequence[Candle],
        strategy: StrategyDecision,
        symbol: str,
        setup_name: str,
    ) -> BacktestResult:
        candles = tuple(candles)
        self._validate_candles(candles)
        decisions = []
        trades = []
        warnings = []

        for index, _candle in enumerate(candles):
            history = candles[: index + 1]
            decision = strategy(history)
            if decision is None:
                continue
            decisions.append(decision)

            risk_plan = decision.risk_plan
            if not decision.validation.trade_allowed:
                continue
            if risk_plan is None or not risk_plan.is_valid:
                warnings.append("Allowed setup ignored because RiskPlan is missing or invalid")
                continue
            if risk_plan.take_profit is None:
                warnings.append("Allowed setup ignored because take_profit is missing")
                continue
            future = candles[index + 1 :]
            if self.max_holding_bars is not None:
                future = future[: self.max_holding_bars]
            if not future:
                warnings.append("Allowed setup ignored because no future candles are available")
                continue

            trades.append(
                simulate_bracket_trade(
                    symbol=symbol,
                    setup_name=setup_name,
                    direction=decision.validation.direction,
                    entry=risk_plan.entry,
                    stop_loss=risk_plan.stop_loss,
                    take_profit=risk_plan.take_profit,
                    position_size=risk_plan.position_size,
                    future_candles=future,
                    fees=self.fees,
                    spread_per_unit=self.spread_per_unit,
                    slippage_per_unit=self.slippage_per_unit,
                )
            )

        return BacktestResult(
            symbol=symbol,
            setup_name=setup_name,
            started_at=candles[0].timestamp,
            ended_at=candles[-1].timestamp,
            decisions=tuple(decisions),
            trades=tuple(trades),
            metrics=calculate_backtest_metrics(tuple(trades)),
            warnings=tuple(warnings),
        )

    @staticmethod
    def _validate_candles(candles: Sequence[Candle]) -> None:
        if not candles:
            raise ValueError("candles are required")
        previous = candles[0].timestamp
        for candle in candles[1:]:
            if candle.timestamp <= previous:
                raise ValueError("candles must be strictly increasing by timestamp")
            previous = candle.timestamp
