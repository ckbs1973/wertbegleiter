"""Journal review metrics for process feedback loops."""

from __future__ import annotations

from dataclasses import dataclass
from math import inf
from typing import Dict, Iterable, List, Sequence

from trading_freaks.models import JournalEntry


@dataclass(frozen=True)
class PerformanceSlice:
    key: str
    trades: int
    win_rate: float
    average_r: float
    expectancy_r: float
    rule_violations: int


@dataclass(frozen=True)
class JournalMetrics:
    total_trades: int
    win_rate: float
    average_r: float
    expectancy_r: float
    profit_factor: float
    max_drawdown_r: float
    average_win_r: float
    average_loss_r: float
    largest_loss_streak: int
    rule_compliant_trades: int
    rule_violation_trades: int
    by_setup: Dict[str, PerformanceSlice]
    by_symbol: Dict[str, PerformanceSlice]
    by_weekday: Dict[str, PerformanceSlice]
    by_emotion_before: Dict[str, PerformanceSlice]
    frequent_violations: Dict[str, int]


def _realized_rs(entries: Iterable[JournalEntry]) -> List[float]:
    return [entry.realized_r for entry in entries if entry.realized_r is not None]


def _win_rate(rs: Sequence[float]) -> float:
    if not rs:
        return 0.0
    return len([result for result in rs if result > 0]) / len(rs)


def _average(values: Sequence[float]) -> float:
    if not values:
        return 0.0
    return sum(values) / len(values)


def _profit_factor(rs: Sequence[float]) -> float:
    wins = sum(result for result in rs if result > 0)
    losses = abs(sum(result for result in rs if result < 0))
    if losses == 0:
        return inf if wins > 0 else 0.0
    return wins / losses


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


def _slice(entries: Sequence[JournalEntry], key: str) -> PerformanceSlice:
    rs = _realized_rs(entries)
    return PerformanceSlice(
        key=key,
        trades=len(entries),
        win_rate=_win_rate(rs),
        average_r=_average(rs),
        expectancy_r=_average(rs),
        rule_violations=len([entry for entry in entries if not entry.rule_compliant]),
    )


def _group(entries: Sequence[JournalEntry], attr: str) -> Dict[str, PerformanceSlice]:
    grouped: Dict[str, List[JournalEntry]] = {}
    for entry in entries:
        value = getattr(entry, attr)
        key = str(value.value if hasattr(value, "value") else value or "unknown")
        grouped.setdefault(key, []).append(entry)
    return {key: _slice(values, key) for key, values in grouped.items()}


def _group_by_weekday(entries: Sequence[JournalEntry]) -> Dict[str, PerformanceSlice]:
    grouped: Dict[str, List[JournalEntry]] = {}
    for entry in entries:
        key = entry.trade_date.strftime("%A")
        grouped.setdefault(key, []).append(entry)
    return {key: _slice(values, key) for key, values in grouped.items()}


def _frequent_violations(entries: Sequence[JournalEntry]) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for entry in entries:
        if not entry.rule_compliant and entry.violated_rule:
            counts[entry.violated_rule] = counts.get(entry.violated_rule, 0) + 1
    return dict(sorted(counts.items(), key=lambda item: item[1], reverse=True))


def review_journal(entries: Sequence[JournalEntry]) -> JournalMetrics:
    """Calculate journal metrics for review, not performance promises."""

    entries = tuple(entries)
    rs = _realized_rs(entries)
    wins = [result for result in rs if result > 0]
    losses = [result for result in rs if result < 0]
    rule_compliant = len([entry for entry in entries if entry.rule_compliant])
    violations = len(entries) - rule_compliant
    return JournalMetrics(
        total_trades=len(entries),
        win_rate=_win_rate(rs),
        average_r=_average(rs),
        expectancy_r=_average(rs),
        profit_factor=_profit_factor(rs),
        max_drawdown_r=_max_drawdown(rs),
        average_win_r=_average(wins),
        average_loss_r=_average(losses),
        largest_loss_streak=_largest_loss_streak(rs),
        rule_compliant_trades=rule_compliant,
        rule_violation_trades=violations,
        by_setup=_group(entries, "setup"),
        by_symbol=_group(entries, "symbol"),
        by_weekday=_group_by_weekday(entries),
        by_emotion_before=_group(entries, "emotion_before"),
        frequent_violations=_frequent_violations(entries),
    )

