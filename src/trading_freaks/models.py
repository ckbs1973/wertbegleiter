"""Core domain models for rule-based trading decision support.

These models express process quality and rule conformance. They do not
represent investment advice, predictions, or broker execution instructions.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, time
from enum import Enum
from typing import Dict, Optional, Sequence, Tuple


class Direction(str, Enum):
    LONG = "long"
    SHORT = "short"


class MarketType(str, Enum):
    US_STOCK = "us_stock"
    FOREX = "forex"
    INDEX = "index"
    COMMODITY = "commodity"
    CRYPTO = "crypto"


class Timeframe(str, Enum):
    M1 = "M1"
    M5 = "M5"
    M15 = "M15"
    H1 = "H1"
    H4 = "H4"
    D1 = "D1"
    W1 = "W1"


class TradingStyle(str, Enum):
    SCALPING = "scalping"
    DAYTRADING = "daytrading"
    SWINGTRADING = "swingtrading"


class OrderType(str, Enum):
    MARKET = "market"
    BUY_STOP = "buy_stop"
    SELL_STOP = "sell_stop"
    BUY_LIMIT = "buy_limit"
    SELL_LIMIT = "sell_limit"
    STOP_LOSS = "stop_loss"
    TAKE_PROFIT = "take_profit"
    TRAILING_STOP = "trailing_stop"


def _ensure_aware_timestamp(value: datetime, field_name: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must be timezone-aware")


def _as_tuple(values: Sequence[str]) -> Tuple[str, ...]:
    return tuple(values)


@dataclass(frozen=True)
class Candle:
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    symbol: Optional[str] = None

    def __post_init__(self) -> None:
        _ensure_aware_timestamp(self.timestamp, "timestamp")
        prices = (self.open, self.high, self.low, self.close)
        if any(price <= 0 for price in prices):
            raise ValueError("OHLC prices must be positive")
        if self.high < max(self.open, self.close):
            raise ValueError("high must be at least open and close")
        if self.low > min(self.open, self.close):
            raise ValueError("low must be at most open and close")
        if self.low > self.high:
            raise ValueError("low must not exceed high")
        if self.volume < 0:
            raise ValueError("volume must not be negative")


@dataclass(frozen=True)
class ChecklistCondition:
    name: str
    passed: bool
    required: bool = True
    evidence: str = ""

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("condition name is required")


@dataclass(frozen=True)
class RiskPlan:
    account_equity: float
    risk_percent: float
    risk_amount: float
    direction: Direction
    entry: float
    stop_loss: float
    take_profit: Optional[float]
    exit_rule: Optional[str]
    risk_per_unit: float
    position_size: float
    planned_reward: Optional[float]
    crv: Optional[float]
    position_leverage: Optional[float]
    product_leverage: Optional[float]
    margin_required: Optional[float]
    is_valid: bool
    warnings: Tuple[str, ...] = field(default_factory=tuple)
    errors: Tuple[str, ...] = field(default_factory=tuple)
    information_only: bool = True

    def __post_init__(self) -> None:
        object.__setattr__(self, "warnings", _as_tuple(self.warnings))
        object.__setattr__(self, "errors", _as_tuple(self.errors))


@dataclass(frozen=True)
class SetupValidationResult:
    setup_name: str
    market: MarketType
    timeframe_context: Timeframe
    timeframe_entry: Timeframe
    direction: Direction
    required_conditions: Tuple[str, ...]
    passed_conditions: Tuple[str, ...]
    failed_conditions: Tuple[str, ...]
    entry_logic: str
    stop_loss_logic: str
    take_profit_logic: str
    risk_logic: str
    invalidation_logic: str
    journal_fields: Tuple[str, ...]
    confidence_score: float
    trade_allowed: bool
    reason_if_not_allowed: str
    warnings: Tuple[str, ...] = field(default_factory=tuple)
    information_only: bool = True

    def __post_init__(self) -> None:
        if not 0 <= self.confidence_score <= 100:
            raise ValueError("confidence_score must be between 0 and 100")
        object.__setattr__(self, "required_conditions", _as_tuple(self.required_conditions))
        object.__setattr__(self, "passed_conditions", _as_tuple(self.passed_conditions))
        object.__setattr__(self, "failed_conditions", _as_tuple(self.failed_conditions))
        object.__setattr__(self, "journal_fields", _as_tuple(self.journal_fields))
        object.__setattr__(self, "warnings", _as_tuple(self.warnings))
        if self.trade_allowed and self.failed_conditions:
            raise ValueError("trade_allowed cannot be true when required conditions failed")
        if self.trade_allowed and not self.information_only:
            raise ValueError("setup validation must remain information-only")

    @classmethod
    def from_conditions(
        cls,
        *,
        setup_name: str,
        market: MarketType,
        timeframe_context: Timeframe,
        timeframe_entry: Timeframe,
        direction: Direction,
        conditions: Sequence[ChecklistCondition],
        entry_logic: str,
        stop_loss_logic: str,
        take_profit_logic: str,
        risk_logic: str,
        invalidation_logic: str,
        journal_fields: Sequence[str],
        warnings: Sequence[str] = (),
    ) -> "SetupValidationResult":
        required = [condition.name for condition in conditions if condition.required]
        passed = [condition.name for condition in conditions if condition.passed]
        failed = [
            condition.name
            for condition in conditions
            if condition.required and not condition.passed
        ]
        required_passed = len([name for name in required if name in passed])
        confidence = 100.0 if not required else round((required_passed / len(required)) * 100, 2)
        trade_allowed = not failed
        reason = ""
        if failed:
            reason = "Kein gueltiges Setup: " + "; ".join(failed)
        return cls(
            setup_name=setup_name,
            market=market,
            timeframe_context=timeframe_context,
            timeframe_entry=timeframe_entry,
            direction=direction,
            required_conditions=required,
            passed_conditions=passed,
            failed_conditions=failed,
            entry_logic=entry_logic,
            stop_loss_logic=stop_loss_logic,
            take_profit_logic=take_profit_logic,
            risk_logic=risk_logic,
            invalidation_logic=invalidation_logic,
            journal_fields=journal_fields,
            confidence_score=confidence,
            trade_allowed=trade_allowed,
            reason_if_not_allowed=reason,
            warnings=warnings,
        )


@dataclass(frozen=True)
class SetupSignal:
    setup_name: str
    symbol: str
    generated_at: datetime
    validation: SetupValidationResult
    risk_plan: Optional[RiskPlan] = None

    def __post_init__(self) -> None:
        _ensure_aware_timestamp(self.generated_at, "generated_at")


@dataclass(frozen=True)
class Trade:
    trade_id: str
    market: MarketType
    symbol: str
    setup_name: str
    direction: Direction
    style: TradingStyle
    opened_at: datetime
    entry: float
    stop_loss: float
    size: float
    take_profit: Optional[float] = None
    closed_at: Optional[datetime] = None
    exit_price: Optional[float] = None
    fees: float = 0.0
    slippage: float = 0.0
    tags: Tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        _ensure_aware_timestamp(self.opened_at, "opened_at")
        if self.closed_at is not None:
            _ensure_aware_timestamp(self.closed_at, "closed_at")
        if not self.trade_id.strip():
            raise ValueError("trade_id is required")
        if not self.symbol.strip():
            raise ValueError("symbol is required")
        if self.entry <= 0 or self.stop_loss <= 0:
            raise ValueError("entry and stop_loss must be positive")
        if self.size <= 0:
            raise ValueError("size must be positive")
        if self.direction is Direction.LONG and self.stop_loss >= self.entry:
            raise ValueError("long stop_loss must be below entry")
        if self.direction is Direction.SHORT and self.stop_loss <= self.entry:
            raise ValueError("short stop_loss must be above entry")
        if self.take_profit is not None:
            if self.direction is Direction.LONG and self.take_profit <= self.entry:
                raise ValueError("long take_profit must be above entry")
            if self.direction is Direction.SHORT and self.take_profit >= self.entry:
                raise ValueError("short take_profit must be below entry")
        if self.fees < 0 or self.slippage < 0:
            raise ValueError("fees and slippage must not be negative")
        object.__setattr__(self, "tags", _as_tuple(self.tags))


@dataclass(frozen=True)
class BacktestDecision:
    timestamp: datetime
    symbol: str
    setup_name: str
    validation: SetupValidationResult
    risk_plan: Optional[RiskPlan]
    notes: Tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        _ensure_aware_timestamp(self.timestamp, "timestamp")
        if not self.symbol.strip():
            raise ValueError("symbol is required")
        object.__setattr__(self, "notes", _as_tuple(self.notes))


@dataclass(frozen=True)
class SimulatedTrade:
    symbol: str
    setup_name: str
    direction: Direction
    opened_at: datetime
    closed_at: datetime
    entry: float
    stop_loss: float
    take_profit: float
    position_size: float
    exit_price: float
    result_amount: float
    result_r: float
    exit_reason: str
    fees: float = 0.0
    slippage: float = 0.0

    def __post_init__(self) -> None:
        _ensure_aware_timestamp(self.opened_at, "opened_at")
        _ensure_aware_timestamp(self.closed_at, "closed_at")
        if self.closed_at < self.opened_at:
            raise ValueError("closed_at must not be before opened_at")
        if self.entry <= 0 or self.stop_loss <= 0 or self.take_profit <= 0:
            raise ValueError("entry, stop_loss and take_profit must be positive")
        if self.position_size <= 0:
            raise ValueError("position_size must be positive")
        if self.direction is Direction.LONG and self.stop_loss >= self.entry:
            raise ValueError("long stop_loss must be below entry")
        if self.direction is Direction.SHORT and self.stop_loss <= self.entry:
            raise ValueError("short stop_loss must be above entry")
        if self.direction is Direction.LONG and self.take_profit <= self.entry:
            raise ValueError("long take_profit must be above entry")
        if self.direction is Direction.SHORT and self.take_profit >= self.entry:
            raise ValueError("short take_profit must be below entry")
        if self.fees < 0 or self.slippage < 0:
            raise ValueError("fees and slippage must not be negative")


@dataclass(frozen=True)
class BacktestResult:
    symbol: str
    setup_name: str
    started_at: datetime
    ended_at: datetime
    decisions: Tuple[BacktestDecision, ...]
    trades: Tuple[SimulatedTrade, ...]
    metrics: Dict[str, float]
    warnings: Tuple[str, ...] = field(default_factory=tuple)
    information_only: bool = True

    def __post_init__(self) -> None:
        _ensure_aware_timestamp(self.started_at, "started_at")
        _ensure_aware_timestamp(self.ended_at, "ended_at")
        if self.ended_at < self.started_at:
            raise ValueError("ended_at must not be before started_at")
        if not self.symbol.strip():
            raise ValueError("symbol is required")
        object.__setattr__(self, "decisions", tuple(self.decisions))
        object.__setattr__(self, "trades", tuple(self.trades))
        object.__setattr__(self, "warnings", _as_tuple(self.warnings))


@dataclass(frozen=True)
class NewsEvent:
    symbol: str
    published_at: datetime
    category: str
    headline: str
    source: str
    sentiment: str = "unknown"
    guidance_relevance: Optional[str] = None
    surprise_level: Optional[str] = None

    def __post_init__(self) -> None:
        _ensure_aware_timestamp(self.published_at, "published_at")
        if not self.symbol.strip():
            raise ValueError("symbol is required")
        if not self.headline.strip():
            raise ValueError("headline is required")


@dataclass(frozen=True)
class EconomicEvent:
    currency: str
    release_at: datetime
    event_name: str
    impact: str
    actual: Optional[float] = None
    forecast: Optional[float] = None
    previous: Optional[float] = None
    interpretation: str = "unknown"

    def __post_init__(self) -> None:
        _ensure_aware_timestamp(self.release_at, "release_at")
        if not self.currency.strip():
            raise ValueError("currency is required")
        if not self.event_name.strip():
            raise ValueError("event_name is required")


@dataclass(frozen=True)
class SentimentSnapshot:
    captured_at: datetime
    currency_strength: Dict[str, float] = field(default_factory=dict)
    risk_regime: str = "unknown"
    safe_haven_flow: str = "unknown"
    notes: Tuple[str, ...] = field(default_factory=tuple)
    conflicts: Tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        _ensure_aware_timestamp(self.captured_at, "captured_at")
        object.__setattr__(self, "notes", _as_tuple(self.notes))
        object.__setattr__(self, "conflicts", _as_tuple(self.conflicts))


@dataclass(frozen=True)
class JournalEntry:
    trade_date: date
    trade_time: time
    market: MarketType
    symbol: str
    setup: str
    direction: Direction
    trading_style: TradingStyle
    timeframe_context: Timeframe
    timeframe_entry: Timeframe
    news_catalyst: bool
    economic_event: bool
    sentiment: str
    entry: float
    stop_loss: float
    take_profit: Optional[float]
    position_size: float
    risk_amount: float
    risk_percent: float
    planned_crv: Optional[float]
    entry_reason: str
    criteria_met: Tuple[str, ...] = field(default_factory=tuple)
    criteria_failed: Tuple[str, ...] = field(default_factory=tuple)
    screenshot_before: Optional[str] = None
    screenshot_after: Optional[str] = None
    realized_r: Optional[float] = None
    result_amount: Optional[float] = None
    fees_spread: float = 0.0
    slippage: float = 0.0
    rule_compliant: bool = True
    violated_rule: Optional[str] = None
    conviction_level: Optional[int] = None
    emotion_before: str = ""
    emotion_during: str = ""
    emotion_after: str = ""
    review: str = ""
    improvement_next_trade: str = ""

    def __post_init__(self) -> None:
        if not self.symbol.strip():
            raise ValueError("symbol is required")
        if self.entry <= 0 or self.stop_loss <= 0:
            raise ValueError("entry and stop_loss must be positive")
        if self.position_size <= 0:
            raise ValueError("position_size must be positive")
        if self.risk_amount <= 0 or self.risk_percent <= 0:
            raise ValueError("risk_amount and risk_percent must be positive")
        if self.direction is Direction.LONG and self.stop_loss >= self.entry:
            raise ValueError("long stop_loss must be below entry")
        if self.direction is Direction.SHORT and self.stop_loss <= self.entry:
            raise ValueError("short stop_loss must be above entry")
        if self.conviction_level is not None and not 1 <= self.conviction_level <= 10:
            raise ValueError("conviction_level must be between 1 and 10")
        if not self.rule_compliant and not self.violated_rule:
            raise ValueError("violated_rule is required when rule_compliant is false")
        object.__setattr__(self, "criteria_met", _as_tuple(self.criteria_met))
        object.__setattr__(self, "criteria_failed", _as_tuple(self.criteria_failed))
