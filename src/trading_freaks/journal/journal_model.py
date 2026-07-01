"""Journal validation focused on process quality."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePath
from typing import Sequence, Tuple

from trading_freaks.models import JournalEntry


SCREENSHOT_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}


@dataclass(frozen=True)
class JournalValidationIssue:
    field: str
    message: str
    severity: str = "error"


@dataclass(frozen=True)
class JournalValidationResult:
    is_complete: bool
    issues: Tuple[JournalValidationIssue, ...]
    information_only: bool = True


def _is_blank(value: str) -> bool:
    return not value or not value.strip()


def _screenshot_issue(field: str, value: str) -> JournalValidationIssue:
    suffix = PurePath(value).suffix.lower()
    if suffix not in SCREENSHOT_EXTENSIONS:
        return JournalValidationIssue(
            field=field,
            message="Screenshot muss png, jpg, jpeg oder webp sein",
        )
    return JournalValidationIssue(field="", message="", severity="ok")


def validate_journal_entry(entry: JournalEntry) -> JournalValidationResult:
    """Validate journal completeness after a trade review.

    This is about documentation quality, not trade approval.
    """

    issues = []
    required_text_fields = {
        "entry_reason": entry.entry_reason,
        "emotion_before": entry.emotion_before,
        "emotion_during": entry.emotion_during,
        "emotion_after": entry.emotion_after,
        "review": entry.review,
        "improvement_next_trade": entry.improvement_next_trade,
    }
    for field, value in required_text_fields.items():
        if _is_blank(value):
            issues.append(JournalValidationIssue(field=field, message="Pflichtfeld fuer Review fehlt"))

    if not entry.criteria_met and not entry.criteria_failed:
        issues.append(
            JournalValidationIssue(
                field="criteria",
                message="Erfuellte oder fehlende Setup-Kriterien muessen dokumentiert sein",
            )
        )
    if entry.screenshot_before is None:
        issues.append(JournalValidationIssue(field="screenshot_before", message="Screenshot vor Trade fehlt"))
    else:
        issue = _screenshot_issue("screenshot_before", entry.screenshot_before)
        if issue.severity != "ok":
            issues.append(issue)
    if entry.screenshot_after is None:
        issues.append(JournalValidationIssue(field="screenshot_after", message="Screenshot nach Trade fehlt"))
    else:
        issue = _screenshot_issue("screenshot_after", entry.screenshot_after)
        if issue.severity != "ok":
            issues.append(issue)
    if not entry.rule_compliant and _is_blank(entry.violated_rule or ""):
        issues.append(JournalValidationIssue(field="violated_rule", message="Regelverstoss muss benannt werden"))
    if entry.realized_r is None:
        issues.append(JournalValidationIssue(field="realized_r", message="Ergebnis in R fehlt"))

    return JournalValidationResult(is_complete=not issues, issues=tuple(issues))


def validate_journal_entries(entries: Sequence[JournalEntry]) -> Tuple[JournalValidationResult, ...]:
    return tuple(validate_journal_entry(entry) for entry in entries)

