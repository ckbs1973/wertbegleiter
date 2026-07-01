"""KAS/ALL-INKL webhook bridge processing.

The bridge receives already-observed TradingView facts on a public KAS endpoint
and lets the local portal pull them. It never sends orders and never creates
trading recommendations.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from trading_freaks.journal.persistence import read_journal_store, write_journal_store
from trading_freaks.journal.trade_event_capture import (
    TradeEventType,
    journal_action_from_trade_event,
    parse_external_trade_event,
)
from trading_freaks.live_bridge import BridgeIngestResult, ingest_bridge_payload


@dataclass(frozen=True)
class KasBridgeEvent:
    sequence: int
    kind: str
    received_at: str
    payload: dict[str, Any]
    source: str = "kas_webhook_bridge"

    def __post_init__(self) -> None:
        if self.sequence <= 0:
            raise ValueError("KAS bridge sequence must be positive")
        if self.kind not in {"price", "trade"}:
            raise ValueError("KAS bridge kind must be price or trade")
        if not isinstance(self.payload, dict):
            raise ValueError("KAS bridge payload must be an object")


@dataclass(frozen=True)
class KasBridgeProcessResult:
    sequence: int
    kind: str
    status: str
    live_results: tuple[BridgeIngestResult, ...] = ()
    journal_action: dict[str, Any] | None = None
    information_only: bool = True


def kas_event_from_payload(record: Mapping[str, Any]) -> KasBridgeEvent:
    payload = record.get("payload")
    if not isinstance(payload, dict):
        raise ValueError("KAS bridge record payload must be an object")
    return KasBridgeEvent(
        sequence=int(record["sequence"]),
        kind=str(record["kind"]),
        received_at=str(record.get("received_at", "")),
        payload=dict(payload),
        source=str(record.get("source", "kas_webhook_bridge")),
    )


def _draft_matches_trade_id(draft: Mapping[str, Any], trade_id: str) -> bool:
    return trade_id in {
        str(draft.get("external_trade_id", "")),
        str(draft.get("trade_id", "")),
        str(draft.get("draft_id", "")),
    }


def _find_draft(drafts: list[dict[str, Any]], trade_id: str) -> tuple[int | None, dict[str, Any] | None]:
    for index, draft in enumerate(drafts):
        if _draft_matches_trade_id(draft, trade_id):
            return index, draft
    return None, None


def _close_reason(event_type: TradeEventType) -> str:
    if event_type is TradeEventType.CLOSED_STOP_LOSS:
        return "Stop Loss"
    if event_type is TradeEventType.CLOSED_TAKE_PROFIT:
        return "Take Profit"
    return "Manuell geschlossen"


def _apply_action_patch(
    *,
    drafts: list[dict[str, Any]],
    active_id: str,
    event_payload: Mapping[str, Any],
    action: dict[str, Any],
) -> tuple[list[dict[str, Any]], str]:
    trade_id = str(action["trade_id"])
    index, existing = _find_draft(drafts, trade_id)
    patch = dict(action.get("journal_patch", {}))
    draft = dict(existing or {})
    draft.update(patch)
    draft.update(
        {
            "draft_id": str(draft.get("draft_id") or trade_id),
            "external_trade_id": trade_id,
            "trade_id": trade_id,
            "status": action["status"],
            "lifecycle_status": action.get("lifecycle_status", draft.get("lifecycle_status", "closed")),
            "account_mode": str(event_payload.get("account_mode") or draft.get("account_mode") or "live"),
            "information_only": True,
        }
    )

    if index is None:
        drafts.append(draft)
    else:
        drafts[index] = draft

    if draft["lifecycle_status"] == "open":
        active_id = draft["draft_id"]
    elif active_id == draft["draft_id"]:
        open_drafts = [item for item in drafts if item.get("lifecycle_status") == "open"]
        active_id = str(open_drafts[-1].get("draft_id", "")) if open_drafts else ""
    return drafts, active_id


def apply_trade_event_to_journal_store(
    event_payload: Mapping[str, Any],
    *,
    store_path: Path,
) -> dict[str, Any]:
    """Apply a KAS trade event to the local journal store."""

    event = parse_external_trade_event(dict(event_payload))
    store = read_journal_store(store_path)
    drafts = [dict(item) for item in store.get("journal_drafts", []) if isinstance(item, dict)]
    active_id = str(store.get("active_journal_draft_id", ""))
    _index, open_trade = _find_draft(drafts, event.trade_id)
    action = journal_action_from_trade_event(event, open_trade=open_trade)

    if action["action"] == "cannot_close_without_open_trade":
        action = {
            "action": "close_event_without_open_draft",
            "trade_id": event.trade_id,
            "status": "Review offen",
            "lifecycle_status": "closed",
            "journal_patch": {
                "external_trade_id": event.trade_id,
                "source": event.source,
                "symbol": event.symbol,
                "market": event.market.value,
                "closed_at": event.timestamp.isoformat(),
                "exit_price": event.exit_price,
                "exit_reason": _close_reason(event.event_type),
                "realized_r": None,
                "fees": event.fees,
                "slippage": event.slippage,
                "screenshot_after": event.screenshot_path,
                "review": "Close-Event ohne offenen Journal-Entwurf importiert. Manuell pruefen.",
            },
            "required_next_steps": (
                "Passenden Open-Trade zuordnen",
                "Entry, Stop Loss und Setup-Kontext ergaenzen",
                "Ergebnis in R nachtragen oder neu berechnen",
            ),
            "information_only": True,
        }

    drafts, active_id = _apply_action_patch(
        drafts=drafts,
        active_id=active_id,
        event_payload=event_payload,
        action=action,
    )
    write_journal_store(
        store_path,
        {
            "source": "kas_webhook_bridge_pull",
            "active_journal_draft_id": active_id,
            "journal_drafts": drafts,
        },
    )
    return action


def process_kas_bridge_events(
    records: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...],
    *,
    source_path: Path,
    status_path: Path,
    journal_store_path: Path,
) -> tuple[KasBridgeProcessResult, ...]:
    results: list[KasBridgeProcessResult] = []
    for raw_record in records:
        event = kas_event_from_payload(raw_record)
        if event.kind == "price":
            live_results = ingest_bridge_payload(event.payload, source_path=source_path, status_path=status_path)
            results.append(
                KasBridgeProcessResult(
                    sequence=event.sequence,
                    kind=event.kind,
                    status="live_status_updated",
                    live_results=live_results,
                )
            )
            continue

        order_payload = {
            "bridge_type": "order",
            "event": event.payload,
            "timestamp": event.payload.get("timestamp") or event.received_at,
            "source_name": "TradingView/Broker Orders",
            "information_only": True,
        }
        live_results = ingest_bridge_payload(order_payload, source_path=source_path, status_path=status_path)
        journal_action = apply_trade_event_to_journal_store(event.payload, store_path=journal_store_path)
        results.append(
            KasBridgeProcessResult(
                sequence=event.sequence,
                kind=event.kind,
                status="journal_updated",
                live_results=live_results,
                journal_action=journal_action,
            )
        )
    return tuple(results)
