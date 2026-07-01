"""US stocks technical reversal without news checklist."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import time
from typing import Optional

from trading_freaks.models import Direction, MarketType, RiskPlan, SetupValidationResult, Timeframe
from trading_freaks.setups.base import attach_risk_plan, condition, warning_text


@dataclass(frozen=True)
class USReversalWithoutNewsInput:
    symbol: str
    direction: Direction
    current_time: time
    daily_volume: float
    has_relevant_news: bool
    has_strong_volume_news_hint: bool
    traded_once_today: bool
    far_from_vwap: bool
    fibonacci_drawn: bool
    vwap_beyond_50_retracement: bool
    ema9_signal_close: bool
    follow_through_candle: bool
    room_to_382_retracement: bool
    take_profit_at_50_or_vwap: bool
    close_by_2159_planned: bool
    long_short_balance_ok: bool

    def __post_init__(self) -> None:
        if not self.symbol.strip():
            raise ValueError("symbol is required")
        if self.daily_volume < 0:
            raise ValueError("daily_volume must not be negative")


def evaluate_us_reversal_without_news(
    candidate: USReversalWithoutNewsInput,
    *,
    risk_plan: Optional[RiskPlan],
) -> SetupValidationResult:
    within_window = time(16, 0) <= candidate.current_time <= time(20, 0)
    checks = [
        condition("Liquide US-Aktie mit Tagesvolumen > 1 Mio.", candidate.daily_volume > 1_000_000),
        condition("Keine relevanten News", not candidate.has_relevant_news),
        condition("Kein starkes Volumen als News-Indiz", not candidate.has_strong_volume_news_hint),
        condition("Suchfenster 16:00 bis 20:00", within_window),
        condition("Aktie heute noch nicht gehandelt", not candidate.traded_once_today),
        condition("Stark vom VWAP entfernt", candidate.far_from_vwap),
        condition("Fibonacci vom Tageshoch/-tief gezogen", candidate.fibonacci_drawn),
        condition("VWAP liegt jenseits des 50er Retracements", candidate.vwap_beyond_50_retracement),
        condition("M1-Schluss ueber/unter EMA9 als Signal", candidate.ema9_signal_close),
        condition("Folgekerze bestaetigt Signal", candidate.follow_through_candle),
        condition("Mindestens Platz bis 38,2 Prozent Retracement", candidate.room_to_382_retracement),
        condition("TP am 50er Retracement oder VWAP geplant", candidate.take_profit_at_50_or_vwap),
        condition("Schliessung spaetestens 21:59 geplant", candidate.close_by_2159_planned),
        condition("Long-/Short-Verhaeltnis im Schutzmodus ok", candidate.long_short_balance_ok),
    ]
    risk_warnings = attach_risk_plan(checks, risk_plan)

    return SetupValidationResult.from_conditions(
        setup_name="Aktien Reversal ohne News",
        market=MarketType.US_STOCK,
        timeframe_context=Timeframe.M1,
        timeframe_entry=Timeframe.M1,
        direction=candidate.direction,
        conditions=checks,
        entry_logic="Technisches Mean-Reversion-Signal nach EMA9-Bestaetigung und Folgekerze.",
        stop_loss_logic="SL unter lokalem Tief bei Long bzw. ueber lokalem Hoch bei Short.",
        take_profit_logic="Naehere Marke aus 50er Retracement oder VWAP.",
        risk_logic="Nur bei CRV > 1:1 und gueltigem RiskPlan.",
        invalidation_logic="Nicht handeln bei News, starkem Volumenhinweis, falschem Zeitfenster oder Zweittrade.",
        journal_fields=("vwap_distance", "fib_382", "fib_50", "ema9_signal", "long_short_balance"),
        warnings=warning_text(risk_warnings),
    )

