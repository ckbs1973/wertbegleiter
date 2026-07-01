"""File-backed journal persistence for local decision support.

The store keeps journal drafts outside browser localStorage. It never executes
orders and deliberately stores only the payload handed in by the local tool.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable


DISCLAIMER = (
    "Lokale Journal-Persistenz. Information und Dokumentation, keine Anlageberatung, "
    "keine Kauf-/Verkaufsempfehlung und keine Orderausfuehrung."
)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def default_journal_store_path(project_root: Path) -> Path:
    return project_root / "reports" / "journal_live_store.json"


def _safe_text(value: Any, max_length: int = 200_000) -> str:
    text = str(value or "")
    return text[:max_length]


def _normalize_draft(draft: Dict[str, Any], index: int) -> Dict[str, Any]:
    draft_id = _safe_text(draft.get("draft_id") or draft.get("id") or f"draft-{index + 1}", 160)
    symbol = _safe_text(draft.get("symbol") or "UNDEFINED", 80).upper()
    account_mode = _safe_text(draft.get("account_mode") or draft.get("mode") or "live", 40).lower()
    if account_mode not in {"live", "paper", "import"}:
        account_mode = "live"
    lifecycle_status = _safe_text(draft.get("lifecycle_status") or "closed", 40).lower()
    if lifecycle_status not in {"open", "closed"}:
        lifecycle_status = "closed"
    normalized = dict(draft)
    normalized.update(
        {
            "draft_id": draft_id,
            "symbol": symbol,
            "account_mode": account_mode,
            "lifecycle_status": lifecycle_status,
            "information_only": True,
        }
    )
    return normalized


def _normalize_drafts(values: Iterable[Any]) -> list[Dict[str, Any]]:
    drafts: list[Dict[str, Any]] = []
    seen: set[str] = set()
    for index, item in enumerate(values):
        if not isinstance(item, dict):
            continue
        draft = _normalize_draft(item, index)
        if draft["draft_id"] in seen:
            continue
        seen.add(draft["draft_id"])
        drafts.append(draft)
    return drafts


def normalize_journal_store_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    drafts = _normalize_drafts(payload.get("journal_drafts") or payload.get("drafts") or [])
    active_id = _safe_text(payload.get("active_journal_draft_id") or payload.get("activeJournalDraftId"), 160)
    if active_id and active_id not in {draft["draft_id"] for draft in drafts}:
        active_id = ""
    return {
        "schema_version": 1,
        "updated_at": utc_now_iso(),
        "disclaimer": DISCLAIMER,
        "journal_drafts": drafts,
        "active_journal_draft_id": active_id,
        "source": _safe_text(payload.get("source") or "wertbegleiter_portal", 120),
        "information_only": True,
    }


def read_journal_store(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {
            "schema_version": 1,
            "updated_at": "",
            "disclaimer": DISCLAIMER,
            "journal_drafts": [],
            "active_journal_draft_id": "",
            "source": "empty_store",
            "information_only": True,
        }
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Journal store must contain a JSON object")
    return normalize_journal_store_payload(payload)


def write_journal_store(path: Path, payload: Dict[str, Any]) -> Dict[str, Any]:
    normalized = normalize_journal_store_payload(payload)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        backup = path.with_name(f"{path.stem}.{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.bak{path.suffix}")
        backup.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
    tmp_path = path.with_suffix(f"{path.suffix}.tmp")
    tmp_path.write_text(json.dumps(normalized, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp_path.replace(path)
    return normalized
