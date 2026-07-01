"""Normalize external trade events into journal lifecycle actions.

This module is intentionally not a broker connector. It accepts already-known
trade facts from TradingView alerts, broker exports, demo/paper webhooks, or a
future browser capture and turns them into journal instructions.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional

from trading_freaks.models import Direction, MarketType


class TradeEventType(str, Enum):
    OPENED = "opened"
    CLOSED_STOP_LOSS = "closed_stop_loss"
    CLOSED_TAKE_PROFIT = "closed_take_profit"
    CLOSED_MANUAL = "closed_manual"


@dataclass(frozen=True)
class ExternalTradeEvent:
    event_id: str
    source: str
    event_type: TradeEventType
    trade_id: str
    symbol: str
    market: MarketType
    timestamp: datetime
    direction: Optional[Direction] = None
    entry: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    size: Optional[float] = None
    exit_price: Optional[float] = None
    fees: float = 0.0
    slippage: float = 0.0
    screenshot_path: str = ""
    note: str = ""

    def __post_init__(self) -> None:
        if self.timestamp.tzinfo is None or self.timestamp.utcoffset() is None:
            raise ValueError("timestamp must be timezone-aware")
        for field_name in ("event_id", "source", "trade_id", "symbol"):
            if not str(getattr(self, field_name)).strip():
                raise ValueError(f"{field_name} is required")
        if self.fees < 0 or self.slippage < 0:
            raise ValueError("fees and slippage must not be negative")
        if self.event_type is TradeEventType.OPENED:
            if self.direction is None:
                raise ValueError("direction is required for opened events")
            for field_name in ("entry", "stop_loss", "size"):
                value = getattr(self, field_name)
                if value is None or value <= 0:
                    raise ValueError(f"{field_name} must be positive for opened events")
            if self.direction is Direction.LONG and self.stop_loss >= self.entry:
                raise ValueError("long stop_loss must be below entry")
            if self.direction is Direction.SHORT and self.stop_loss <= self.entry:
                raise ValueError("short stop_loss must be above entry")
        else:
            if self.exit_price is None or self.exit_price <= 0:
                raise ValueError("exit_price must be positive for close events")


def _to_float(value: Any, field_name: str, required: bool = False) -> Optional[float]:
    if value in (None, ""):
        if required:
            raise ValueError(f"{field_name} is required")
        return None
    parsed = float(value)
    return parsed


def _parse_timestamp(value: Any) -> datetime:
    if isinstance(value, datetime):
        timestamp = value
    else:
        text = str(value or "").strip()
        if not text:
            raise ValueError("timestamp is required")
        timestamp = datetime.fromisoformat(text.replace("Z", "+00:00"))
    if timestamp.tzinfo is None or timestamp.utcoffset() is None:
        raise ValueError("timestamp must be timezone-aware")
    return timestamp


def parse_external_trade_event(payload: Dict[str, Any]) -> ExternalTradeEvent:
    """Parse a JSON-like trade event from TradingView/broker/paper sources."""

    event_type = TradeEventType(str(payload["event_type"]))
    direction = Direction(str(payload["direction"])) if payload.get("direction") else None
    return ExternalTradeEvent(
        event_id=str(payload.get("event_id") or f"{payload.get('source', 'event')}-{payload.get('trade_id', '')}-{event_type.value}"),
        source=str(payload.get("source", "external")),
        event_type=event_type,
        trade_id=str(payload["trade_id"]),
        symbol=str(payload["symbol"]).upper(),
        market=MarketType(str(payload.get("market", MarketType.US_STOCK.value))),
        timestamp=_parse_timestamp(payload.get("timestamp")),
        direction=direction,
        entry=_to_float(payload.get("entry"), "entry"),
        stop_loss=_to_float(payload.get("stop_loss"), "stop_loss"),
        take_profit=_to_float(payload.get("take_profit"), "take_profit"),
        size=_to_float(payload.get("size"), "size"),
        exit_price=_to_float(payload.get("exit_price"), "exit_price"),
        fees=_to_float(payload.get("fees", 0), "fees") or 0.0,
        slippage=_to_float(payload.get("slippage", 0), "slippage") or 0.0,
        screenshot_path=str(payload.get("screenshot_path", "")),
        note=str(payload.get("note", "")),
    )


def _realized_r(event: ExternalTradeEvent, open_trade: Dict[str, Any]) -> Optional[float]:
    entry = _to_float(open_trade.get("entry"), "entry")
    stop_loss = _to_float(open_trade.get("stop_loss"), "stop_loss")
    exit_price = event.exit_price
    direction = open_trade.get("direction")
    if entry is None or stop_loss is None or exit_price is None:
        return None
    risk_per_unit = abs(entry - stop_loss)
    if risk_per_unit <= 0:
        return None
    if direction == Direction.SHORT.value or direction is Direction.SHORT:
        return (entry - exit_price) / risk_per_unit
    return (exit_price - entry) / risk_per_unit


def journal_action_from_trade_event(
    event: ExternalTradeEvent,
    open_trade: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Return a journal lifecycle action for an external trade event."""

    if event.event_type is TradeEventType.OPENED:
        return {
            "action": "start_journal_draft",
            "trade_id": event.trade_id,
            "status": "Trade laeuft",
            "lifecycle_status": "open",
            "journal_patch": {
                "external_trade_id": event.trade_id,
                "source": event.source,
                "symbol": event.symbol,
                "market": event.market.value,
                "direction": event.direction.value if event.direction else "",
                "entry": event.entry,
                "stop_loss": event.stop_loss,
                "take_profit": event.take_profit,
                "position_size": event.size,
                "started_at": event.timestamp.isoformat(),
                "screenshot_before": event.screenshot_path,
                "review": event.note,
            },
            "required_next_steps": (
                "Screenshot vor Trade pruefen",
                "Setup-Kriterien und 5 Pre-Checks manuell bestaetigen",
                "Trade nach Exit mit Ergebnis, Nachher-Screenshot und Review abschliessen",
            ),
            "information_only": True,
        }

    if not open_trade:
        return {
            "action": "cannot_close_without_open_trade",
            "trade_id": event.trade_id,
            "status": "nicht_verarbeitbar",
            "errors": ["Kein passender offener Journal-Entwurf fuer trade_id gefunden"],
            "information_only": True,
        }

    close_reason = {
        TradeEventType.CLOSED_STOP_LOSS: "Stop Loss",
        TradeEventType.CLOSED_TAKE_PROFIT: "Take Profit",
        TradeEventType.CLOSED_MANUAL: "Manuell geschlossen",
    }[event.event_type]
    realized = _realized_r(event, open_trade)
    return {
        "action": "close_journal_draft",
        "trade_id": event.trade_id,
        "status": "Review offen",
        "lifecycle_status": "closed",
        "journal_patch": {
            "external_trade_id": event.trade_id,
            "closed_at": event.timestamp.isoformat(),
            "exit_price": event.exit_price,
            "exit_reason": close_reason,
            "realized_r": round(realized, 4) if realized is not None else None,
            "fees": event.fees,
            "slippage": event.slippage,
            "screenshot_after": event.screenshot_path,
            "review": event.note,
        },
        "required_next_steps": (
            "Regelkonformitaet pruefen",
            "Emotion nach Trade dokumentieren",
            "Verbesserung fuer naechsten Trade erfassen",
        ),
        "information_only": True,
    }
