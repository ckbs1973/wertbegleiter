"""Journal serialization helpers."""

from __future__ import annotations

import csv
import json
from dataclasses import asdict
from io import StringIO
from typing import Any, Dict, Sequence

from trading_freaks.models import JournalEntry


def _json_safe(value: Any) -> Any:
    if hasattr(value, "value"):
        return value.value
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if isinstance(value, tuple):
        return list(value)
    return value


def journal_entry_to_dict(entry: JournalEntry) -> Dict[str, Any]:
    raw = asdict(entry)
    return {key: _json_safe(value) for key, value in raw.items()}


def journal_entries_to_json(entries: Sequence[JournalEntry]) -> str:
    return json.dumps([journal_entry_to_dict(entry) for entry in entries], indent=2, sort_keys=True)


def journal_entries_to_csv_rows(entries: Sequence[JournalEntry]) -> str:
    if not entries:
        return ""
    rows = [journal_entry_to_dict(entry) for entry in entries]
    output = StringIO()
    writer = csv.DictWriter(output, fieldnames=list(rows[0].keys()))
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue()

