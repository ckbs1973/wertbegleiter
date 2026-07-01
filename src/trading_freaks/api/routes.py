"""Backend route functions without broker execution.

These functions are deliberately framework-neutral so they can be used by a
stdlib HTTP server, FastAPI later, or unit tests without network dependencies.
"""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
from enum import Enum
from datetime import date, datetime, time
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

from trading_freaks.daily_update import (
    DailyTradeCandidate,
    DailyTradingContext,
    evaluate_daily_trading_update,
)
from trading_freaks.live_data import (
    default_required_sources,
    evaluate_live_feed_status,
    source_from_payload,
)
from trading_freaks.live_bridge import ingest_bridge_payload
from trading_freaks.live_collector import ingest_source_heartbeat, utc_now
from trading_freaks.morning_brief import create_morning_brief, summarize_brief
from trading_freaks.models import Direction, RiskPlan, SetupValidationResult
from trading_freaks.models import ChecklistCondition, MarketType, TradingStyle
from trading_freaks.news_deck import create_news_deck
from trading_freaks.journal.trade_event_capture import (
    journal_action_from_trade_event,
    parse_external_trade_event,
)
from trading_freaks.journal.persistence import (
    default_journal_store_path,
    read_journal_store,
    write_journal_store,
)
from trading_freaks.risk.position_sizing import calculate_risk_plan
from trading_freaks.setups.us_news_breakout_checklist import (
    USNewsBreakoutInput,
    evaluate_us_news_breakout,
)


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_LIVE_SOURCE_PATH = PROJECT_ROOT / "frontend" / "public" / "data" / "live_source_snapshots.json"
DEFAULT_LIVE_STATUS_PATH = PROJECT_ROOT / "frontend" / "public" / "data" / "live_feed_status.json"
DEFAULT_JOURNAL_STORE_PATH = default_journal_store_path(PROJECT_ROOT)


def _json_safe(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if is_dataclass(value):
        return {key: _json_safe(item) for key, item in asdict(value).items()}
    if isinstance(value, tuple):
        return [_json_safe(item) for item in value]
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items()}
    return value


def _missing_fields(payload: Dict[str, Any], fields: Iterable[str]) -> list:
    return [field for field in fields if field not in payload]


def _risk_plan_from_payload(payload: Optional[Dict[str, Any]], direction: Direction) -> Optional[RiskPlan]:
    if not payload:
        return None
    return calculate_risk_plan(
        account_equity=float(payload["account_equity"]),
        risk_percent=float(payload.get("risk_percent", 1.0)),
        direction=direction,
        entry=float(payload["entry"]),
        stop_loss=float(payload["stop_loss"]) if payload.get("stop_loss") is not None else None,
        take_profit=float(payload["take_profit"]) if payload.get("take_profit") is not None else None,
        exit_rule=payload.get("exit_rule"),
        unit_value=float(payload.get("unit_value", 1.0)),
        product_leverage=(
            float(payload["product_leverage"])
            if payload.get("product_leverage") is not None
            else None
        ),
    )


def _parse_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "ja", "y"}
    return bool(value)


def _parse_time(value: Any, field_name: str) -> time:
    if isinstance(value, time):
        return value
    if not isinstance(value, str) or ":" not in value:
        raise ValueError(f"{field_name} must be HH:MM")
    hour_text, minute_text = value.split(":", 1)
    return time(int(hour_text), int(minute_text))


def _parse_conditions(values: Any) -> tuple[ChecklistCondition, ...]:
    if not values:
        return ()
    conditions = []
    for item in values:
        if isinstance(item, str):
            conditions.append(ChecklistCondition(name=item, passed=False))
            continue
        conditions.append(
            ChecklistCondition(
                name=str(item["name"]),
                passed=_parse_bool(item.get("passed", False)),
                required=_parse_bool(item.get("required", True)),
                evidence=str(item.get("evidence", "")),
            )
        )
    return tuple(conditions)


def _validation_to_response(
    validation: SetupValidationResult,
    risk_plan: Optional[RiskPlan],
) -> Dict[str, Any]:
    return {
        "status": "trade_erlaubt_zur_manuellen_pruefung" if validation.trade_allowed else "nicht_handeln",
        "disclaimer": "Information und Checklistenunterstuetzung, keine Anlageberatung oder Orderfreigabe.",
        "validation": _json_safe(validation),
        "risk_plan": _json_safe(risk_plan) if risk_plan is not None else None,
    }


def evaluate_daily_update_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Evaluate a daily scalping-focused trading update from JSON-like input."""

    context_payload = dict(payload.get("context", {}))
    candidate_payloads = list(payload.get("candidates", []))
    if not candidate_payloads:
        return {
            "status": "nur_beobachten",
            "errors": ["Keine Setup-Kandidaten uebergeben"],
            "disclaimer": "Ohne Kandidaten gibt es nur Beobachtung, keine Trade-Planung.",
        }

    try:
        context = DailyTradingContext(
            account_equity=float(context_payload["account_equity"]),
            trades_taken_today=int(context_payload.get("trades_taken_today", 0)),
            max_trades_per_day=int(context_payload.get("max_trades_per_day", 5)),
            target_min_trades=int(context_payload.get("target_min_trades", 2)),
            target_max_trades=int(context_payload.get("target_max_trades", 5)),
            default_risk_percent=float(context_payload.get("default_risk_percent", 1.0)),
            psychology_ready=_parse_bool(context_payload.get("psychology_ready", True)),
            daily_loss_limit_reached=_parse_bool(
                context_payload.get("daily_loss_limit_reached", False)
            ),
            weekly_loss_limit_reached=_parse_bool(
                context_payload.get("weekly_loss_limit_reached", False)
            ),
            loss_streak=int(context_payload.get("loss_streak", 0)),
            correlated_exposure_warning=_parse_bool(
                context_payload.get("correlated_exposure_warning", False)
            ),
        )
        candidates = [
            DailyTradeCandidate(
                candidate_id=str(item.get("candidate_id", f"candidate-{index + 1}")),
                symbol=str(item["symbol"]),
                setup_name=str(item["setup_name"]),
                market=MarketType(item.get("market", MarketType.US_STOCK.value)),
                direction=Direction(item["direction"]),
                style=TradingStyle(item.get("style", TradingStyle.SCALPING.value)),
                planned_time=_parse_time(item["planned_time"], "planned_time"),
                entry=float(item["entry"]),
                stop_loss=float(item["stop_loss"]),
                take_profit=float(item["take_profit"]),
                unit_value=float(item.get("unit_value", 1.0)),
                risk_percent=(
                    float(item["risk_percent"])
                    if item.get("risk_percent") is not None
                    else None
                ),
                required_conditions=_parse_conditions(item.get("required_conditions", ())),
                notes=tuple(str(note) for note in item.get("notes", ())),
            )
            for index, item in enumerate(candidate_payloads)
        ]
    except (KeyError, TypeError, ValueError) as exc:
        return {
            "status": "nicht_handeln",
            "errors": [f"Daily Update konnte nicht berechnet werden: {exc}"],
            "disclaimer": "Fehlerhafte Eingaben blockieren die Tagesplanung.",
        }

    update = evaluate_daily_trading_update(context=context, candidates=candidates)
    return {
        "status": update.status,
        "disclaimer": "Information und Checklistenunterstuetzung, keine Anlageberatung oder Orderfreigabe.",
        "daily_update": _json_safe(update),
    }


def evaluate_morning_brief_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Build a conservative morning setup brief from a watchlist."""

    watchlist_text = str(payload.get("watchlist_text", "")).strip()
    if not watchlist_text:
        return {
            "status": "nicht_handeln",
            "errors": ["watchlist_text fehlt"],
            "disclaimer": "Ohne Watchlist gibt es nur Beobachtung.",
        }
    try:
        brief = create_morning_brief(
            watchlist_text,
            generated_for=str(payload.get("generated_for", "naechster Handelstag")),
            max_candidates=int(payload.get("max_candidates", 5)),
        )
    except (TypeError, ValueError) as exc:
        return {
            "status": "nicht_handeln",
            "errors": [f"Morning Brief konnte nicht berechnet werden: {exc}"],
            "disclaimer": "Fehlerhafte Eingaben blockieren die Tagesplanung.",
        }

    return {
        "status": "morning_brief_erstellt",
        "disclaimer": "Information und Checklistenunterstuetzung, keine Anlageberatung oder Orderfreigabe.",
        "brief": _json_safe(brief),
        "summary": summarize_brief(brief),
    }


def evaluate_news_deck_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Build a TweetDeck/X-Pro style news workflow from a watchlist."""

    watchlist_text = str(payload.get("watchlist_text", "")).strip()
    if not watchlist_text:
        return {
            "status": "nicht_handeln",
            "errors": ["watchlist_text fehlt"],
            "disclaimer": "Ohne Watchlist kann kein News-Deck vorbereitet werden.",
        }

    try:
        deck = create_news_deck(watchlist_text)
    except (TypeError, ValueError) as exc:
        return {
            "status": "nicht_handeln",
            "errors": [f"News-Deck konnte nicht vorbereitet werden: {exc}"],
            "disclaimer": "Fehlerhafte Eingaben blockieren die News-Vorbereitung.",
        }

    return {
        "status": deck.status,
        "disclaimer": deck.disclaimer,
        "source_note": deck.source_note,
        "deck": _json_safe(deck),
    }


def evaluate_live_status_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Evaluate whether market/news sources are fresh enough for live use."""

    try:
        source_payloads = payload.get("sources", [])
        sources = (
            tuple(source_from_payload(item) for item in source_payloads)
            if source_payloads
            else default_required_sources()
        )
        status = evaluate_live_feed_status(sources)
    except (KeyError, TypeError, ValueError) as exc:
        return {
            "status": "nicht_live",
            "errors": [f"Live-Status konnte nicht berechnet werden: {exc}"],
            "disclaimer": "Fehlerhafte oder fehlende Live-Daten blockieren sekundenaktuelle Pruefung.",
        }

    return {
        "status": status.overall_status,
        "disclaimer": "Information und Quellenfrische-Pruefung, keine Anlageberatung oder Orderfreigabe.",
        "live_status": _json_safe(status),
    }


def capture_live_source_heartbeat_payload(
    payload: Dict[str, Any],
    *,
    source_path: Path | None = None,
    status_path: Path | None = None,
) -> Dict[str, Any]:
    """Persist one live-source heartbeat for the local freshness monitor."""

    snapshot_payload = dict(payload.get("source", payload))
    missing = _missing_fields(snapshot_payload, ("source_name", "category"))
    if missing:
        return {
            "status": "nicht_live",
            "errors": [f"Pflichtfeld fehlt: {field}" for field in missing],
            "disclaimer": "Ohne belastbare Quellen-Heartbeats bleibt das Portal nicht sekundenfrisch.",
        }

    try:
        current = utc_now()
        sources_payload, status = ingest_source_heartbeat(
            source_path or DEFAULT_LIVE_SOURCE_PATH,
            status_path or DEFAULT_LIVE_STATUS_PATH,
            snapshot_payload,
            now=current,
        )
    except (KeyError, TypeError, ValueError, OSError) as exc:
        return {
            "status": "nicht_live",
            "errors": [f"Live-Quelle konnte nicht gespeichert werden: {exc}"],
            "disclaimer": "Fehlerhafte oder nicht schreibbare Live-Daten blockieren sekundenaktuelle Pruefung.",
        }

    return {
        "status": "live_source_aktualisiert",
        "disclaimer": "Information und Quellenfrische-Pruefung, keine Anlageberatung oder Orderfreigabe.",
        "source_count": len(sources_payload.get("sources", [])),
        "live_status": _json_safe(status),
    }


def ingest_live_bridge_payload(
    payload: Dict[str, Any],
    *,
    source_path: Path | None = None,
    status_path: Path | None = None,
) -> Dict[str, Any]:
    """Normalize bridge payloads and persist source freshness heartbeats."""

    try:
        results = ingest_bridge_payload(
            payload.get("payload", payload),
            source_path=source_path or DEFAULT_LIVE_SOURCE_PATH,
            status_path=status_path or DEFAULT_LIVE_STATUS_PATH,
        )
    except (KeyError, TypeError, ValueError, OSError) as exc:
        return {
            "status": "nicht_live",
            "errors": [f"Live-Bridge konnte nicht verarbeitet werden: {exc}"],
            "disclaimer": "Fehlerhafte Bridge-Daten blockieren sekundenaktuelle Pruefung.",
        }

    return {
        "status": "live_bridge_aktualisiert",
        "disclaimer": "Information und Quellenfrische-Pruefung, keine Anlageberatung oder Orderfreigabe.",
        "processed": [_json_safe(item) for item in results],
    }


def evaluate_us_news_breakout_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Evaluate the main US news breakout flow from JSON-like input."""

    candidate_payload = dict(payload.get("candidate", payload))
    risk_payload = payload.get("risk")
    missing = _missing_fields(
        candidate_payload,
        (
            "symbol",
            "direction",
            "daily_volume",
            "is_penny_stock",
            "has_news_catalyst",
            "news_is_mixed",
            "gap_percent",
            "main_session_started",
            "momentum_in_news_direction_by_1545",
            "price_on_correct_vwap_side",
            "consolidation_minutes",
            "consolidation_is_tight",
            "correction_fraction_of_momentum",
            "pattern_type",
            "rvol",
            "rvol_anticipated",
            "entry_is_near_breakout",
            "movement_is_momentum_not_volatility",
            "close_by_end_of_day_planned",
        ),
    )
    if missing:
        return {
            "status": "nicht_handeln",
            "errors": [f"Pflichtfeld fehlt: {field}" for field in missing],
            "disclaimer": "Unvollstaendige Daten blockieren die Setup-Pruefung.",
        }

    direction = Direction(candidate_payload["direction"])
    candidate = USNewsBreakoutInput(
        symbol=str(candidate_payload["symbol"]),
        direction=direction,
        daily_volume=float(candidate_payload["daily_volume"]),
        is_penny_stock=bool(candidate_payload["is_penny_stock"]),
        has_news_catalyst=bool(candidate_payload["has_news_catalyst"]),
        news_is_mixed=bool(candidate_payload["news_is_mixed"]),
        gap_percent=float(candidate_payload["gap_percent"]),
        main_session_started=bool(candidate_payload["main_session_started"]),
        momentum_in_news_direction_by_1545=bool(
            candidate_payload["momentum_in_news_direction_by_1545"]
        ),
        price_on_correct_vwap_side=bool(candidate_payload["price_on_correct_vwap_side"]),
        consolidation_minutes=float(candidate_payload["consolidation_minutes"]),
        consolidation_is_tight=bool(candidate_payload["consolidation_is_tight"]),
        correction_fraction_of_momentum=float(candidate_payload["correction_fraction_of_momentum"]),
        pattern_type=str(candidate_payload["pattern_type"]),
        rvol=float(candidate_payload["rvol"]) if candidate_payload.get("rvol") is not None else None,
        rvol_anticipated=bool(candidate_payload["rvol_anticipated"]),
        entry_is_near_breakout=bool(candidate_payload["entry_is_near_breakout"]),
        movement_is_momentum_not_volatility=bool(
            candidate_payload["movement_is_momentum_not_volatility"]
        ),
        close_by_end_of_day_planned=bool(candidate_payload["close_by_end_of_day_planned"]),
        m1_is_liquid_without_large_gaps=bool(
            candidate_payload.get("m1_is_liquid_without_large_gaps", True)
        ),
    )
    try:
        risk_plan = _risk_plan_from_payload(risk_payload, direction)
    except (KeyError, TypeError, ValueError) as exc:
        return {
            "status": "nicht_handeln",
            "errors": [f"RiskPlan konnte nicht berechnet werden: {exc}"],
            "disclaimer": "Kein Trade ohne berechenbares Risiko, Stop Loss und Exit-Plan.",
        }

    validation = evaluate_us_news_breakout(candidate, risk_plan=risk_plan)
    return _validation_to_response(validation, risk_plan)


def validate_journal_capture_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Validate the journal fields emphasized by the project context."""

    issues = []
    for field in ("emotion_before", "emotion_during", "emotion_after", "review"):
        if not str(payload.get(field, "")).strip():
            issues.append({"field": field, "message": "Pflichtfeld fuer Journal-Review fehlt"})
    if not payload.get("criteria_met") and not payload.get("criteria_failed"):
        issues.append({"field": "criteria", "message": "Setup-Kriterien muessen dokumentiert sein"})
    for field in ("screenshot_before", "screenshot_after"):
        value = str(payload.get(field, "")).strip()
        if not value:
            issues.append({"field": field, "message": "Screenshot fehlt"})
        elif not value.lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
            issues.append({"field": field, "message": "Screenshot-Format muss png, jpg, jpeg oder webp sein"})
    if payload.get("rule_compliant") is False and not str(payload.get("violated_rule", "")).strip():
        issues.append({"field": "violated_rule", "message": "Regelverstoss muss benannt werden"})
    if payload.get("realized_r") is None:
        issues.append({"field": "realized_r", "message": "Ergebnis in R fehlt"})

    return {
        "status": "journal_vollstaendig" if not issues else "journal_unvollstaendig",
        "is_complete": not issues,
        "issues": issues,
        "disclaimer": "Journal prueft Prozessqualitaet, nicht die Guete einer Handelsidee.",
    }


def read_journal_store_payload(
    payload: Optional[Dict[str, Any]] = None,
    *,
    store_path: Path | None = None,
) -> Dict[str, Any]:
    """Read local persistent journal drafts without broker interaction."""

    try:
        store = read_journal_store(store_path or DEFAULT_JOURNAL_STORE_PATH)
    except (OSError, ValueError, TypeError) as exc:
        return {
            "status": "journal_store_fehler",
            "errors": [f"Journal-Speicher konnte nicht gelesen werden: {exc}"],
            "disclaimer": "Lokale Journal-Persistenz konnte nicht geladen werden. Keine Orderausfuehrung.",
        }

    return {
        "status": "journal_store_geladen",
        "store_path": str(store_path or DEFAULT_JOURNAL_STORE_PATH),
        "draft_count": len(store.get("journal_drafts", [])),
        "journal_store": store,
        "disclaimer": store.get("disclaimer", "Lokale Journal-Persistenz, keine Orderausfuehrung."),
    }


def save_journal_store_payload(
    payload: Dict[str, Any],
    *,
    store_path: Path | None = None,
) -> Dict[str, Any]:
    """Persist local journal drafts outside browser localStorage."""

    try:
        store = write_journal_store(store_path or DEFAULT_JOURNAL_STORE_PATH, payload)
    except (OSError, ValueError, TypeError) as exc:
        return {
            "status": "journal_store_fehler",
            "errors": [f"Journal-Speicher konnte nicht geschrieben werden: {exc}"],
            "disclaimer": "Lokale Journal-Persistenz konnte nicht gespeichert werden. Keine Orderausfuehrung.",
        }

    return {
        "status": "journal_store_gespeichert",
        "store_path": str(store_path or DEFAULT_JOURNAL_STORE_PATH),
        "draft_count": len(store.get("journal_drafts", [])),
        "journal_store": store,
        "disclaimer": store.get("disclaimer", "Lokale Journal-Persistenz, keine Orderausfuehrung."),
    }


def capture_trade_event_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Convert an external trade event into a journal lifecycle action."""

    try:
        event = parse_external_trade_event(dict(payload.get("event", payload)))
        open_trade = payload.get("open_trade")
        action = journal_action_from_trade_event(event, open_trade=open_trade)
    except (KeyError, TypeError, ValueError) as exc:
        return {
            "status": "nicht_verarbeitbar",
            "errors": [f"Trade-Event konnte nicht verarbeitet werden: {exc}"],
            "disclaimer": "Externe Trade-Events ergaenzen nur das Journal. Keine Anlageberatung, keine Orderausfuehrung.",
        }

    return {
        "status": "trade_event_verarbeitet" if action["status"] != "nicht_verarbeitbar" else "nicht_verarbeitbar",
        "disclaimer": "Externe Trade-Events ergaenzen nur das Journal. Keine Anlageberatung, keine Orderausfuehrung.",
        "event_action": action,
    }
