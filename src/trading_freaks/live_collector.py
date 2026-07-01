"""Local live-source collector utilities.

The collector converts external source heartbeats into a freshness status file
for the frontend. It never creates trade signals or broker orders.
"""

from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Mapping, Sequence

from trading_freaks.live_data import (
    DEFAULT_STALE_AFTER_SECONDS,
    LiveFeedStatus,
    LiveSourceSnapshot,
    default_required_sources,
    evaluate_live_feed_status,
    parse_timestamp,
    source_from_payload,
)


REQUIRED_CATEGORIES = ("price", "order", "calendar", "news")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def json_safe(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value):
        return {key: json_safe(item) for key, item in asdict(value).items()}
    if isinstance(value, tuple):
        return [json_safe(item) for item in value]
    if isinstance(value, list):
        return [json_safe(item) for item in value]
    if isinstance(value, dict):
        return {key: json_safe(item) for key, item in value.items()}
    return value


def status_payload(status: LiveFeedStatus) -> dict[str, Any]:
    return {
        "generated_at": status.generated_at.isoformat(),
        "disclaimer": (
            "Information und Quellenfrische-Pruefung, keine Anlageberatung, "
            "keine Kauf-/Verkaufsempfehlung und keine Orderfreigabe."
        ),
        "live_status": json_safe(status),
        "next_step": (
            "Sekundenaktuelle Daten erfordern live verbundene Kurs-, Order-, "
            "Kalender- und Newsquellen."
        ),
    }


def snapshots_from_payload(payload: Mapping[str, Any], *, observed_at: datetime | None = None) -> tuple[LiveSourceSnapshot, ...]:
    values = payload.get("sources", payload if isinstance(payload, list) else [])
    if not isinstance(values, list):
        raise ValueError("live source payload must contain a sources list")
    return tuple(source_from_payload(item, observed_at=observed_at) for item in values)


def read_source_snapshots(path: Path, *, now: datetime | None = None) -> tuple[LiveSourceSnapshot, ...]:
    if not path.exists():
        return ()
    payload = json.loads(path.read_text(encoding="utf-8"))
    return snapshots_from_payload(payload, observed_at=now or utc_now())


def ensure_required_categories(
    sources: Sequence[LiveSourceSnapshot],
    *,
    now: datetime | None = None,
) -> tuple[LiveSourceSnapshot, ...]:
    current = now or utc_now()
    represented = {source.category for source in sources}
    missing_defaults = [
        source
        for source in default_required_sources(generated_at=current)
        if source.category in REQUIRED_CATEGORIES and source.category not in represented
    ]
    return tuple(sources) + tuple(missing_defaults)


def evaluate_sources(
    sources: Sequence[LiveSourceSnapshot],
    *,
    now: datetime | None = None,
) -> LiveFeedStatus:
    current = now or utc_now()
    return evaluate_live_feed_status(ensure_required_categories(sources, now=current), now=current)


def write_live_status_file(
    output_path: Path,
    sources: Sequence[LiveSourceSnapshot],
    *,
    now: datetime | None = None,
) -> LiveFeedStatus:
    current = now or utc_now()
    status = evaluate_sources(sources, now=current)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(status_payload(status), ensure_ascii=False, indent=2), encoding="utf-8")
    return status


def ingest_source_heartbeat(
    source_path: Path,
    output_path: Path,
    snapshot: Mapping[str, Any],
    *,
    now: datetime | None = None,
) -> tuple[dict[str, Any], LiveFeedStatus]:
    """Persist one source heartbeat and rebuild the frontend live status."""

    current = now or utc_now()
    existing: Mapping[str, Any] = {}
    if source_path.exists():
        existing = json.loads(source_path.read_text(encoding="utf-8"))
    payload = upsert_snapshot_payload(existing, snapshot, now=current)

    source_path.parent.mkdir(parents=True, exist_ok=True)
    source_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    sources = snapshots_from_payload(payload, observed_at=current)
    status = write_live_status_file(output_path, sources, now=current)
    return payload, status


def upsert_snapshot_payload(
    existing: Mapping[str, Any] | None,
    snapshot: Mapping[str, Any],
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    current = now or utc_now()
    source_name = str(snapshot["source_name"])
    category = str(snapshot.get("category", "news"))
    normalized = {
        "source_name": source_name,
        "category": category,
        "observed_at": (parse_timestamp(snapshot.get("observed_at")) or current).isoformat(),
        "source_timestamp": (parse_timestamp(snapshot.get("source_timestamp")) or current).isoformat(),
        "stale_after_seconds": int(snapshot.get("stale_after_seconds") or DEFAULT_STALE_AFTER_SECONDS.get(category, 60)),
        "connection_state": str(snapshot.get("connection_state", "connected")),
        "item_count": int(snapshot.get("item_count", 0)),
        "details": [str(item) for item in snapshot.get("details", ())],
    }
    payload = {"sources": []}
    if existing and isinstance(existing.get("sources"), list):
        payload["sources"] = [item for item in existing["sources"] if item.get("source_name") != source_name]
    payload["sources"].append(normalized)
    payload["sources"].sort(key=lambda item: (item.get("category", ""), item.get("source_name", "")))
    return payload
