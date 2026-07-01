"""Freshness checks for live market/news decision support.

This module does not fetch or recommend trades. It only evaluates whether the
data displayed in the desk is fresh enough to be used as information context.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Mapping, Sequence, Tuple


DEFAULT_STALE_AFTER_SECONDS = {
    "price": 5,
    "order": 5,
    "news": 60,
    "calendar": 900,
    "chat_context": 300,
    "journal": 10,
}


def _as_tuple(values: Sequence[str]) -> Tuple[str, ...]:
    return tuple(values)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _ensure_aware(value: datetime, field_name: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must be timezone-aware")


def parse_timestamp(value: Any) -> datetime | None:
    """Parse ISO-like timestamps into aware datetimes."""

    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        _ensure_aware(value, "timestamp")
        return value
    text = str(value).strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = f"{text[:-1]}+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


@dataclass(frozen=True)
class LiveSourceSnapshot:
    source_name: str
    category: str
    observed_at: datetime
    source_timestamp: datetime | None = None
    stale_after_seconds: int | None = None
    connection_state: str = "missing"
    item_count: int = 0
    details: Tuple[str, ...] = field(default_factory=tuple)
    information_only: bool = True

    def __post_init__(self) -> None:
        if not self.source_name.strip():
            raise ValueError("source_name is required")
        if not self.category.strip():
            raise ValueError("category is required")
        _ensure_aware(self.observed_at, "observed_at")
        if self.source_timestamp is not None:
            _ensure_aware(self.source_timestamp, "source_timestamp")
        object.__setattr__(self, "details", _as_tuple(self.details))
        if self.stale_after_seconds is not None and self.stale_after_seconds <= 0:
            raise ValueError("stale_after_seconds must be positive")
        if not self.information_only:
            raise ValueError("live source snapshots must remain information-only")


@dataclass(frozen=True)
class LiveSourceEvaluation:
    source_name: str
    category: str
    status: str
    age_seconds: float | None
    stale_after_seconds: int
    connection_state: str
    item_count: int
    message: str
    details: Tuple[str, ...] = field(default_factory=tuple)
    information_only: bool = True

    def __post_init__(self) -> None:
        object.__setattr__(self, "details", _as_tuple(self.details))
        if not self.information_only:
            raise ValueError("live evaluations must remain information-only")


@dataclass(frozen=True)
class LiveFeedStatus:
    generated_at: datetime
    overall_status: str
    live_source_count: int
    stale_source_count: int
    missing_source_count: int
    max_age_seconds: float | None
    evaluations: Tuple[LiveSourceEvaluation, ...]
    warnings: Tuple[str, ...]
    information_only: bool = True

    def __post_init__(self) -> None:
        _ensure_aware(self.generated_at, "generated_at")
        object.__setattr__(self, "evaluations", tuple(self.evaluations))
        object.__setattr__(self, "warnings", _as_tuple(self.warnings))
        if not self.information_only:
            raise ValueError("live feed status must remain information-only")


def evaluate_source(snapshot: LiveSourceSnapshot, *, now: datetime | None = None) -> LiveSourceEvaluation:
    current = now or _utc_now()
    _ensure_aware(current, "now")
    stale_after = snapshot.stale_after_seconds or DEFAULT_STALE_AFTER_SECONDS.get(snapshot.category, 60)
    timestamp = snapshot.source_timestamp or snapshot.observed_at
    age = max(0.0, (current - timestamp).total_seconds()) if timestamp else None
    connection_state = snapshot.connection_state

    if connection_state in {"missing", "blocked", "error"}:
        status = connection_state
        message = "Quelle ist nicht live verbunden."
    elif age is None:
        status = "missing"
        message = "Quelle liefert keinen belastbaren Zeitstempel."
    elif age <= stale_after:
        status = "live"
        message = "Quelle ist innerhalb der erlaubten Frischegrenze."
    else:
        status = "stale"
        message = "Quelle ist zu alt fuer sekundenaktuelle Entscheidungsunterstuetzung."

    return LiveSourceEvaluation(
        source_name=snapshot.source_name,
        category=snapshot.category,
        status=status,
        age_seconds=round(age, 3) if age is not None else None,
        stale_after_seconds=stale_after,
        connection_state=connection_state,
        item_count=snapshot.item_count,
        message=message,
        details=snapshot.details,
    )


def evaluate_live_feed_status(
    sources: Sequence[LiveSourceSnapshot],
    *,
    now: datetime | None = None,
) -> LiveFeedStatus:
    current = now or _utc_now()
    _ensure_aware(current, "now")
    evaluations = tuple(evaluate_source(source, now=current) for source in sources)
    live_count = len([item for item in evaluations if item.status == "live"])
    stale_count = len([item for item in evaluations if item.status == "stale"])
    missing_count = len([item for item in evaluations if item.status in {"missing", "blocked", "error"}])
    ages = [item.age_seconds for item in evaluations if item.age_seconds is not None]

    if not evaluations:
        overall = "not_configured"
    elif live_count == len(evaluations):
        overall = "second_fresh"
    elif live_count:
        overall = "partly_live"
    else:
        overall = "not_live"

    warnings = []
    if missing_count:
        warnings.append("Mindestens eine Pflichtquelle ist nicht live verbunden.")
    if stale_count:
        warnings.append("Mindestens eine Quelle ist aelter als ihre Frischegrenze.")
    if overall != "second_fresh":
        warnings.append("Keine sekundengenaue Trade-Pruefung ohne live verbundene Pflichtquellen.")

    return LiveFeedStatus(
        generated_at=current,
        overall_status=overall,
        live_source_count=live_count,
        stale_source_count=stale_count,
        missing_source_count=missing_count,
        max_age_seconds=max(ages) if ages else None,
        evaluations=evaluations,
        warnings=tuple(warnings),
    )


def source_from_payload(payload: Mapping[str, Any], *, observed_at: datetime | None = None) -> LiveSourceSnapshot:
    category = str(payload.get("category", "news"))
    return LiveSourceSnapshot(
        source_name=str(payload["source_name"]),
        category=category,
        observed_at=parse_timestamp(payload.get("observed_at")) or observed_at or _utc_now(),
        source_timestamp=parse_timestamp(payload.get("source_timestamp")),
        stale_after_seconds=(
            int(payload["stale_after_seconds"])
            if payload.get("stale_after_seconds") is not None
            else DEFAULT_STALE_AFTER_SECONDS.get(category, 60)
        ),
        connection_state=str(payload.get("connection_state", "missing")),
        item_count=int(payload.get("item_count", 0)),
        details=tuple(str(item) for item in payload.get("details", ())),
    )


def default_required_sources(*, generated_at: datetime | None = None) -> Tuple[LiveSourceSnapshot, ...]:
    current = generated_at or _utc_now()
    return (
        LiveSourceSnapshot(
            source_name="TradingView/Broker Kurse",
            category="price",
            observed_at=current,
            connection_state="missing",
            details=("Realtime-Kurse brauchen API/WebSocket oder TradingView/Broker-Bridge.",),
        ),
        LiveSourceSnapshot(
            source_name="TradingView/Broker Orders",
            category="order",
            observed_at=current,
            connection_state="missing",
            details=("Offene/geschlossene Trades brauchen Broker- oder TradingView-Eventstream.",),
        ),
        LiveSourceSnapshot(
            source_name="Wirtschaftskalender",
            category="calendar",
            observed_at=current,
            connection_state="missing",
            details=("Kalenderdaten muessen periodisch oder per API aktualisiert werden.",),
        ),
        LiveSourceSnapshot(
            source_name="News/Squawk/X Pro",
            category="news",
            observed_at=current,
            connection_state="missing",
            details=("Sekundenschnelle News brauchen Newsquawk/X-Pro/RSS/API-Quelle.",),
        ),
    )
