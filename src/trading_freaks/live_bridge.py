"""Local live bridge payload normalization.

The bridge accepts already-observed facts from local adapters and turns them
into source freshness heartbeats. It never fetches private data by itself, never
creates trade recommendations, and never executes orders.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping, Sequence

from trading_freaks.live_collector import ingest_source_heartbeat, utc_now
from trading_freaks.live_data import DEFAULT_STALE_AFTER_SECONDS, parse_timestamp


CANONICAL_SOURCE_NAMES = {
    "price": "TradingView/Broker Kurse",
    "order": "TradingView/Broker Orders",
    "calendar": "Wirtschaftskalender",
    "news": "News/Squawk/X Pro",
}


@dataclass(frozen=True)
class BridgeIngestResult:
    source_name: str
    category: str
    item_count: int
    live_status: str
    information_only: bool = True

    def __post_init__(self) -> None:
        if not self.information_only:
            raise ValueError("bridge ingest results must remain information-only")


def _first_text(values: Sequence[Any], *, limit: int = 3) -> tuple[str, ...]:
    texts = []
    for item in values[:limit]:
        if isinstance(item, Mapping):
            text = str(item.get("title") or item.get("headline") or item.get("event") or item.get("symbol") or item)
        else:
            text = str(item)
        if text.strip():
            texts.append(text.strip())
    return tuple(texts)


def _payload_details(payload: Mapping[str, Any]) -> list[str]:
    details = payload.get("details", [])
    if not isinstance(details, list):
        return []
    return [str(item).strip() for item in details if str(item).strip()]


def _item_count(payload: Mapping[str, Any], default: int) -> int:
    raw_value = payload.get("item_count")
    if raw_value not in (None, ""):
        return int(raw_value)
    return default


def _event_timestamp(payload: Mapping[str, Any], *, now: datetime | None = None) -> str:
    current = now or utc_now()
    timestamp = (
        parse_timestamp(payload.get("source_timestamp"))
        or parse_timestamp(payload.get("timestamp"))
        or parse_timestamp(payload.get("observed_at"))
        or current
    )
    return timestamp.isoformat()


def _source_base(
    payload: Mapping[str, Any],
    *,
    category: str,
    now: datetime | None = None,
) -> dict[str, Any]:
    current = now or utc_now()
    return {
        "source_name": str(payload.get("source_name") or CANONICAL_SOURCE_NAMES[category]),
        "category": category,
        "connection_state": str(payload.get("connection_state", "connected")),
        "observed_at": current.isoformat(),
        "source_timestamp": _event_timestamp(payload, now=current),
        "stale_after_seconds": int(
            payload.get("stale_after_seconds") or DEFAULT_STALE_AFTER_SECONDS.get(category, 60)
        ),
        "information_only": True,
    }


def price_payload_to_snapshot(payload: Mapping[str, Any], *, now: datetime | None = None) -> dict[str, Any]:
    symbol = str(payload.get("symbol", "")).upper()
    details = []
    if symbol:
        details.append(f"Symbol {symbol}")
    for field in ("last", "bid", "ask"):
        if payload.get(field) not in (None, ""):
            details.append(f"{field}={payload.get(field)}")
    details.append("Preis-Heartbeat, keine Orderausfuehrung.")
    details.extend(_payload_details(payload))
    snapshot = _source_base(payload, category="price", now=now)
    snapshot.update(
        {
            "item_count": _item_count(payload, 1 if symbol else 0),
            "details": details,
        }
    )
    return snapshot


def order_payload_to_snapshot(payload: Mapping[str, Any], *, now: datetime | None = None) -> dict[str, Any]:
    event = payload.get("event", payload)
    symbol = str(event.get("symbol", payload.get("symbol", ""))).upper()
    event_type = str(event.get("event_type", payload.get("event_type", "order_update")))
    trade_id = str(event.get("trade_id", payload.get("trade_id", "")))
    details = [f"Event {event_type}"]
    if symbol:
        details.append(f"Symbol {symbol}")
    if trade_id:
        details.append(f"trade_id {trade_id}")
    details.append("Order-/Positions-Heartbeat fuer Journalabgleich, keine Broker-Order.")
    details.extend(_payload_details(payload))
    base_payload = dict(payload)
    base_payload.setdefault("timestamp", event.get("timestamp"))
    snapshot = _source_base(base_payload, category="order", now=now)
    snapshot.update(
        {
            "item_count": _item_count(payload, 1),
            "details": details,
        }
    )
    return snapshot


def calendar_payload_to_snapshot(payload: Mapping[str, Any], *, now: datetime | None = None) -> dict[str, Any]:
    events = payload.get("events", [])
    if not isinstance(events, list):
        events = []
    details = ["Wirtschaftskalender-Heartbeat."]
    details.extend(_first_text(events))
    if payload.get("next_high_impact_event"):
        details.append(f"Naechstes Top-Event: {payload.get('next_high_impact_event')}")
    details.extend(_payload_details(payload))
    snapshot = _source_base(payload, category="calendar", now=now)
    snapshot.update(
        {
            "item_count": _item_count(payload, len(events)),
            "details": details,
        }
    )
    return snapshot


def news_payload_to_snapshot(payload: Mapping[str, Any], *, now: datetime | None = None) -> dict[str, Any]:
    items = payload.get("items", payload.get("headlines", []))
    if not isinstance(items, list):
        items = []
    details = ["News-/Squawk-Heartbeat."]
    details.extend(_first_text(items))
    if payload.get("headline"):
        details.append(str(payload["headline"]))
    details.extend(_payload_details(payload))
    snapshot = _source_base(payload, category="news", now=now)
    snapshot.update(
        {
            "item_count": _item_count(payload, len(items) or (1 if payload.get("headline") else 0)),
            "details": details,
        }
    )
    return snapshot


def bridge_payload_to_snapshot(payload: Mapping[str, Any], *, now: datetime | None = None) -> dict[str, Any]:
    """Normalize one bridge payload into the live-source heartbeat contract."""

    if "source" in payload and isinstance(payload["source"], Mapping):
        return dict(payload["source"])
    category = str(payload.get("category") or payload.get("bridge_type") or payload.get("type") or "").lower()
    if category == "prices":
        category = "price"
    if category == "orders":
        category = "order"
    if category in {"economic_calendar", "events"}:
        category = "calendar"
    if category in {"headline", "headlines"}:
        category = "news"

    if category == "price":
        return price_payload_to_snapshot(payload, now=now)
    if category == "order":
        return order_payload_to_snapshot(payload, now=now)
    if category == "calendar":
        return calendar_payload_to_snapshot(payload, now=now)
    if category == "news":
        return news_payload_to_snapshot(payload, now=now)
    raise ValueError("bridge payload category must be price, order, calendar or news")


def iter_bridge_payloads(payload: Any) -> tuple[Mapping[str, Any], ...]:
    if isinstance(payload, list):
        values = payload
    elif isinstance(payload, Mapping) and isinstance(payload.get("sources"), list):
        values = payload["sources"]
    elif isinstance(payload, Mapping) and isinstance(payload.get("payloads"), list):
        values = payload["payloads"]
    elif isinstance(payload, Mapping):
        values = [payload]
    else:
        raise ValueError("bridge file must contain a JSON object, sources list, payloads list or JSON array")
    if not all(isinstance(item, Mapping) for item in values):
        raise ValueError("bridge payload entries must be JSON objects")
    return tuple(values)


def ingest_bridge_payload(
    payload: Any,
    *,
    source_path: Path,
    status_path: Path,
    now: datetime | None = None,
) -> tuple[BridgeIngestResult, ...]:
    """Persist one or more bridge payloads and rebuild live status."""

    current = now or utc_now()
    results = []
    for item in iter_bridge_payloads(payload):
        snapshot = bridge_payload_to_snapshot(item, now=current)
        _sources_payload, status = ingest_source_heartbeat(source_path, status_path, snapshot, now=current)
        results.append(
            BridgeIngestResult(
                source_name=str(snapshot["source_name"]),
                category=str(snapshot["category"]),
                item_count=int(snapshot.get("item_count", 0)),
                live_status=status.overall_status,
            )
        )
    return tuple(results)
