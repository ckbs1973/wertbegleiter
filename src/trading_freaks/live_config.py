"""Read-only readiness checks for configured live adapters.

This module never fetches market data and never exposes secrets. It only tells
the UI whether required live adapter variables are present and structurally
usable before the real adapter runner tries to ingest them.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping
from urllib.parse import urlsplit, urlunsplit


PATH_LIKE_ENV_KEYS = frozenset(
    {
        "LIVE_PRICE_JSON_PATH",
        "LIVE_ORDER_JSON_PATH",
        "LIVE_CALENDAR_JSON_PATH",
        "LIVE_NEWS_FEED_URL",
        "TRADINGVIEW_BRIDGE_URL",
        "BROKER_EVENT_STREAM_URL",
        "ECONOMIC_CALENDAR_API_URL",
        "FOREXLIVE_RSS_URL",
        "NEWSQUAWK_API_URL",
        "X_PRO_LIST_URL",
        "SEEKING_ALPHA_NEWS_URL",
    }
)


@dataclass(frozen=True)
class RequiredLiveAdapter:
    env_key: str
    source_name: str
    category: str
    stale_after_seconds: int
    purpose: str
    fallback_env_keys: tuple[str, ...] = ()


REQUIRED_LIVE_ADAPTERS: tuple[RequiredLiveAdapter, ...] = (
    RequiredLiveAdapter(
        env_key="LIVE_PRICE_JSON_PATH",
        source_name="TradingView/Broker Kurse",
        category="price",
        stale_after_seconds=5,
        purpose="Realtime-Kurse oder lokaler Preis-Heartbeat",
        fallback_env_keys=("TRADINGVIEW_BRIDGE_URL",),
    ),
    RequiredLiveAdapter(
        env_key="LIVE_ORDER_JSON_PATH",
        source_name="TradingView/Broker Orders",
        category="order",
        stale_after_seconds=5,
        purpose="Offene und geschlossene Trades fuer den Journal-Lifecycle",
        fallback_env_keys=("BROKER_EVENT_STREAM_URL",),
    ),
    RequiredLiveAdapter(
        env_key="LIVE_CALENDAR_JSON_PATH",
        source_name="Wirtschaftskalender",
        category="calendar",
        stale_after_seconds=900,
        purpose="Risikoevents, Newsblocker und Kalenderkontext",
        fallback_env_keys=("ECONOMIC_CALENDAR_API_URL",),
    ),
    RequiredLiveAdapter(
        env_key="LIVE_NEWS_FEED_URL",
        source_name="News/Squawk/X Pro",
        category="news",
        stale_after_seconds=60,
        purpose="Headlines, Squawk, RSS/Atom oder JSON-Newsfeed",
        fallback_env_keys=("NEWSQUAWK_API_URL", "X_PRO_LIST_URL", "FOREXLIVE_RSS_URL", "SEEKING_ALPHA_NEWS_URL"),
    ),
)


def load_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        clean_key = key.strip()
        clean_value = value.strip().strip('"').strip("'")
        values[clean_key] = _resolve_env_value(clean_key, clean_value, base_dir=path.parent)
    return values


def _utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _is_url(value: str) -> bool:
    return value.startswith("http://") or value.startswith("https://")


def _resolve_env_value(key: str, value: str, *, base_dir: Path) -> str:
    if key not in PATH_LIKE_ENV_KEYS or not value or _is_url(value):
        return value
    candidate = Path(value)
    if candidate.is_absolute():
        return value
    return str((base_dir / candidate).resolve())


def masked_location(value: str) -> str:
    text = value.strip()
    if not text:
        return ""
    if _is_url(text):
        parsed = urlsplit(text)
        safe_path = _mask_sensitive_url_path(parsed.path or "/")
        if len(safe_path) > 48:
            safe_path = f"...{safe_path[-45:]}"
        return urlunsplit((parsed.scheme, parsed.netloc, safe_path, "", ""))
    path = Path(text)
    if path.name:
        return f".../{path.name}"
    return "lokaler Pfad gesetzt"


def _mask_sensitive_url_path(path: str) -> str:
    parts = path.split("/")
    for idx, part in enumerate(parts):
        if part == "tv" and idx + 2 < len(parts):
            parts[idx + 1] = "..."
    return "/".join(parts)


def _adapter_env_keys(adapter: RequiredLiveAdapter) -> tuple[str, ...]:
    return (adapter.env_key,) + tuple(adapter.fallback_env_keys)


def _configured_location(env: Mapping[str, str], adapter: RequiredLiveAdapter) -> tuple[str, str]:
    for key in _adapter_env_keys(adapter):
        value = str(env.get(key, "")).strip()
        if value:
            return key, value
    return adapter.env_key, ""


def adapter_config_status(
    env: Mapping[str, str],
    *,
    env_file_exists: bool,
    env_file_label: str = ".env",
) -> dict[str, object]:
    adapters = []
    for adapter in REQUIRED_LIVE_ADAPTERS:
        configured_env_key, raw_location = _configured_location(env, adapter)
        configured = bool(raw_location)
        is_url = _is_url(raw_location)
        file_exists = None
        if configured and not is_url:
            file_exists = Path(raw_location).exists()
        if not configured:
            status = "missing_config"
            message = f"{adapter.env_key} oder Provider-Fallback ist nicht gesetzt."
            next_step = f"Einen dieser Slots in {env_file_label} mit echter Quelle setzen: {', '.join(_adapter_env_keys(adapter))}."
        elif file_exists is False:
            status = "missing_file"
            message = "Lokaler Pfad ist gesetzt, Datei wurde aber nicht gefunden."
            next_step = "Dateipfad korrigieren oder Bridge-Prozess starten, der diese Datei schreibt."
        else:
            status = "configured"
            message = "Konfiguration ist vorhanden; Live-Status wird erst durch frische Daten gruen."
            next_step = "Adapter-Runner starten und Frische im Live-Status pruefen."

        adapters.append(
            {
                "env_key": adapter.env_key,
                "env_keys": list(_adapter_env_keys(adapter)),
                "configured_env_key": configured_env_key if configured else "",
                "source_name": adapter.source_name,
                "category": adapter.category,
                "stale_after_seconds": adapter.stale_after_seconds,
                "purpose": adapter.purpose,
                "configured": configured,
                "status": status,
                "location_kind": "url" if is_url else "file" if configured else "",
                "location_masked": masked_location(raw_location),
                "file_exists": file_exists,
                "message": message,
                "next_step": next_step,
                "information_only": True,
            }
        )

    configured_count = len([item for item in adapters if item["configured"]])
    missing_count = len(adapters) - configured_count
    warnings = []
    if not env_file_exists:
        warnings.append(f"{env_file_label} fehlt. Live-Adapter sind nicht konfiguriert.")
    if missing_count:
        warnings.append("Mindestens eine Pflichtquelle hat noch keine Adapter-Konfiguration.")
    if any(item["status"] == "missing_file" for item in adapters):
        warnings.append("Mindestens eine konfigurierte lokale Datei existiert nicht.")

    return {
        "generated_at": _utc_iso(),
        "disclaimer": "Konfigurationspruefung, keine Anlageberatung, keine Orderfreigabe und keine Secret-Ausgabe.",
        "env_file": {
            "exists": env_file_exists,
            "label": env_file_label,
        },
        "configured_count": configured_count,
        "missing_count": missing_count,
        "adapters": adapters,
        "warnings": warnings,
        "information_only": True,
    }


def adapter_config_status_from_env_file(path: Path) -> dict[str, object]:
    return adapter_config_status(
        load_env_file(path),
        env_file_exists=path.exists(),
        env_file_label=path.name,
    )
