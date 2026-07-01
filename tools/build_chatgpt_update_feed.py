#!/usr/bin/env python3
"""Build a frontend update feed from imported ChatGPT Trading project chats.

The output is information-only. It preserves the imported chat context as
session/update evidence, but it does not create trading signals or order
recommendations.
"""

from __future__ import annotations

import json
import re
import unicodedata
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RAW_PATH = ROOT / "docs" / "imported_chatgpt_project" / "trading_project_chats_raw.json"
OUT_PATH = ROOT / "frontend" / "public" / "data" / "chatgpt_trading_updates.json"
EXTRAS_PATH = ROOT / "frontend" / "public" / "data" / "chatgpt_trading_update_extras.json"

FOCUS_ASSETS = (
    "DE40",
    "US500",
    "USTEC",
    "EURUSD",
    "USDJPY",
    "GBPUSD",
    "EURGBP",
    "XAUUSD",
    "XAUEUR",
    "XAGUSD",
    "UKOIL",
    "WTI",
    "BRENT",
    "NVDA",
    "MSFT",
    "AAPL",
    "GOOG",
    "AMZN",
    "TSLA",
    "AMD",
)

REQUIRED_UPDATE_CHATS = (
    (
        "Trading Update Daily",
        ("trading update daily", "daily update"),
    ),
    (
        "Taegliches Marktupdate und Trading-Setups",
        ("tagliches marktupdate", "taegliches marktupdate", "marktupdate und trading-setups"),
    ),
    (
        "US open update and trade scenarios",
        ("us open update and trade scenarios", "us-open update", "us open"),
    ),
    (
        "Europe session update and trade scenarios",
        ("europe session update and trade scenarios", "europe session"),
    ),
)

OPTIONAL_UPDATE_CHATS = (
    (
        "Breaking news update: oil, yen, tech insights",
        ("breaking news update", "oil, yen, tech"),
    ),
)

SESSION_PATTERNS = (
    ("Breaking News", ("BREAKING NEWS", "HIGH-IMPACT", "Breaking")),
    ("US Open", ("US-Open", "US Open", "15:25", "15:30", "Opening")),
    ("Europe Session", ("Europe Session", "10:00 Uhr Berlin", "10:00 Uhr", "DE40")),
    ("Daily Update", ("DAILY MARKET UPDATE", "Daily Update", "08:00", "Marktupdate")),
)

THEME_PATTERNS = (
    ("Risk-On/Risk-Off", ("risk-on", "risk off", "risk-off", "risk on")),
    ("Oel/Geopolitik", ("oel", "oil", "brent", "wti", "hormuz", "iran", "geopolit")),
    ("USD/Yields", ("usd", "yield", "rendite", "fed", "zins")),
    ("JPY/Yen", ("jpy", "yen", "intervention", "usdjpy")),
    ("Tech/AI/Semis", ("tech", "ai", "semi", "nasdaq", "ustec", "nvda", "micron")),
    ("Metalle", ("gold", "silber", "xau", "xag", "gold/silber")),
    ("Kalender/Event", ("kalender", "event", "daten", "cpi", "nfp", "ifo", "fed-speaker")),
)

CHECK_PATTERNS = (
    ("Keine erste News-/Open-Kerze handeln", ("erste", "kerze", "nicht in", "no trade")),
    ("5-15 Minuten warten und Struktur verlangen", ("5-15", "warten", "retest", "pullback")),
    ("USD/Yields querpruefen", ("usd", "yield", "rendite")),
    ("Oel/Geopolitik als Risiko-Filter pruefen", ("oel", "oil", "brent", "wti", "hormuz", "iran")),
    ("JPY-Interventionsrisiko pruefen", ("yen", "jpy", "intervention")),
    ("Tech/AI/Semi-Sentiment pruefen", ("tech", "ai", "semi", "nasdaq", "nvda", "micron")),
    ("XAGUSD immer mit Gold, USD/Yields und China-Kontext pruefen", ("xagusd", "silber", "gold/silber")),
)

BLOCKER_PATTERNS = (
    ("Unklare oder gemischte Datenlage", ("gemischt", "unklar", "mixed")),
    ("Kein Einstieg vor Top-Event", ("vor top", "vor event", "nicht vor", "keine positionierung vor")),
    ("Kein Chase in Momentum-Spike", ("chase", "spike", "nicht in den ersten spike")),
    ("Kein Trade ohne Retest/Pullback", ("ohne retest", "ohne pullback", "erst reaktion")),
    ("Korrelierte Ueberladung vermeiden", ("korreliert", "doppelte", "ueberladung", "parallel")),
)


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def _normalize(text: str) -> str:
    ascii_text = unicodedata.normalize("NFKD", text or "").encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", " ", ascii_text.lower()).strip()


def _chat_config(title: str) -> tuple[str, bool] | None:
    normalized = _normalize(title)
    for canonical, aliases in REQUIRED_UPDATE_CHATS:
        if any(alias in normalized for alias in aliases):
            return canonical, True
    for canonical, aliases in OPTIONAL_UPDATE_CHATS:
        if any(alias in normalized for alias in aliases):
            return canonical, False
    return None


def _sort_key(timestamp: str, fallback: str) -> str:
    for pattern, date_format in (
        (r"^(\d{2}\.\d{2}\.\d{4})\s+(\d{1,2}:\d{2})", "%d.%m.%Y %H:%M"),
        (r"^(\d{4}-\d{2}-\d{2})\s+(\d{1,2}:\d{2})", "%Y-%m-%d %H:%M"),
    ):
        match = re.search(pattern, timestamp)
        if not match:
            continue
        try:
            parsed = datetime.strptime(" ".join(match.groups()), date_format)
            return parsed.isoformat(timespec="minutes")
        except ValueError:
            continue
    return fallback


def _extract_timestamp(text: str, fallback: str) -> tuple[str, str, str]:
    patterns = (
        r"(\d{2}\.\d{2}\.\d{4}),?\s*(\d{1,2}:\d{2})\s*(?:Uhr)?\s*(?:Europe/Berlin|Berlin|CET)?",
        r"(\d{2}\.\d{2}\.\d{4}).{0,25}?(\d{1,2}:\d{2})\s*(?:Uhr)?",
        r"(\d{4}-\d{2}-\d{2}).{0,25}?(\d{1,2}:\d{2})",
    )
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            date, time_value = match.groups()
            timestamp = f"{date} {time_value}"
            return timestamp, _sort_key(timestamp, fallback), "chat_text"
    return fallback, fallback, "export_timestamp"


def _classify_session(title: str, text: str) -> str:
    haystack = f"{title} {text}"
    for session, needles in SESSION_PATTERNS:
        if any(needle.lower() in haystack.lower() for needle in needles):
            return session
    return "Trading Update"


def _matches(patterns: tuple[tuple[str, tuple[str, ...]], ...], text: str) -> list[str]:
    lower = text.lower()
    values = []
    for label, needles in patterns:
        if any(needle.lower() in lower for needle in needles):
            values.append(label)
    return values


def _assets(text: str) -> list[str]:
    lower = text.lower()
    found = []
    for asset in FOCUS_ASSETS:
        if asset.lower() in lower:
            found.append(asset)
    return found


def _summary(text: str) -> str:
    cleaned = _clean(text)
    if len(cleaned) <= 420:
        return cleaned
    cut = cleaned[:420].rsplit(" ", 1)[0]
    return f"{cut}..."


def _load_extra_updates() -> list[dict]:
    if not EXTRAS_PATH.exists():
        return []
    payload = json.loads(EXTRAS_PATH.read_text(encoding="utf-8"))
    values = payload.get("updates", payload if isinstance(payload, list) else [])
    if not isinstance(values, list):
        raise ValueError("chatgpt update extras must be a list or contain an updates list")
    extras = []
    for item in values:
        if not isinstance(item, dict):
            continue
        update = dict(item)
        update.setdefault("canonical_chat_title", update.get("chat_title", "Lokaler Zusatzkontext"))
        update.setdefault("required_chat_source", False)
        update.setdefault("timestamp_source", "external_context")
        update.setdefault("information_only", True)
        update["external_context"] = True
        extras.append(update)
    return extras


def build_feed() -> dict:
    chats = json.loads(RAW_PATH.read_text(encoding="utf-8"))
    updates = []
    raw_chats = []
    for chat_index, chat in enumerate(chats):
        title = chat.get("sourceTitle") or chat.get("pageTitle") or f"Chat {chat_index + 1}"
        exported_at = chat.get("extractedAt") or datetime.now(timezone.utc).isoformat()
        config = _chat_config(title)
        canonical_title = config[0] if config else title
        required_source = config[1] if config else False
        raw_chats.append(
            {
                "canonical_title": canonical_title,
                "title": title,
                "url": chat.get("sourceUrl") or chat.get("url") or "",
                "exported_at": exported_at,
                "required": required_source,
            }
        )
        for message in chat.get("messages", []):
            if message.get("role") != "assistant":
                continue
            text = _clean(message.get("text", ""))
            if len(text) < 80:
                continue
            timestamp, sort_key, timestamp_source = _extract_timestamp(text, exported_at)
            session = _classify_session(title, text)
            themes = _matches(THEME_PATTERNS, text)
            assets = _assets(text)
            checks = _matches(CHECK_PATTERNS, text)
            blockers = _matches(BLOCKER_PATTERNS, text)
            if not (themes or assets or checks or blockers or session != "Trading Update"):
                continue
            updates.append(
                {
                    "id": f"chat-{chat_index + 1}-message-{message.get('index', len(updates))}",
                    "chat_title": title,
                    "canonical_chat_title": canonical_title,
                    "required_chat_source": required_source,
                    "chat_url": chat.get("sourceUrl") or chat.get("url") or "",
                    "message_index": message.get("index"),
                    "timestamp": timestamp,
                    "sort_key": sort_key,
                    "timestamp_source": timestamp_source,
                    "exported_at": exported_at,
                    "session": session,
                    "assets": assets,
                    "themes": themes,
                    "required_checks": checks,
                    "blockers": blockers,
                    "summary": _summary(text),
                    "full_text": text,
                    "information_only": True,
                }
            )
    extra_updates = _load_extra_updates()
    known_ids = {item["id"] for item in updates}
    updates.extend(item for item in extra_updates if item.get("id") not in known_ids)
    updates.sort(key=lambda item: (item["sort_key"], item["exported_at"], item["id"]), reverse=True)
    coverage = _build_chat_coverage(raw_chats, updates)
    required_coverage = [item for item in coverage if item["required"]]
    missing_required = [item["canonical_title"] for item in required_coverage if item["status"] == "missing"]
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": str(RAW_PATH.relative_to(ROOT)),
        "disclaimer": "Information und Checklistenunterstuetzung, keine Anlageberatung, keine Kauf-/Verkaufsempfehlung und keine Orderfreigabe.",
        "chat_count": len(chats),
        "update_count": len(updates),
        "extra_update_count": len(extra_updates),
        "required_update_chats": [item[0] for item in REQUIRED_UPDATE_CHATS],
        "optional_update_chats": [item[0] for item in OPTIONAL_UPDATE_CHATS],
        "covered_required_chat_count": len(required_coverage) - len(missing_required),
        "required_chat_count": len(REQUIRED_UPDATE_CHATS),
        "missing_required_chats": missing_required,
        "chat_coverage": coverage,
        "coverage_status": "vollstaendig" if not missing_required else "unvollstaendig",
        "updates": updates,
    }


def _build_chat_coverage(raw_chats: list[dict], updates: list[dict]) -> list[dict]:
    coverage: dict[str, dict] = {}
    for canonical, _aliases in REQUIRED_UPDATE_CHATS:
        coverage[canonical] = {
            "canonical_title": canonical,
            "title": canonical,
            "url": "",
            "required": True,
            "status": "missing",
            "exported_at": "",
            "latest_timestamp": "",
            "latest_sort_key": "",
            "update_count": 0,
            "sessions": [],
            "assets": [],
            "themes": [],
        }
    for canonical, _aliases in OPTIONAL_UPDATE_CHATS:
        coverage[canonical] = {
            "canonical_title": canonical,
            "title": canonical,
            "url": "",
            "required": False,
            "status": "missing",
            "exported_at": "",
            "latest_timestamp": "",
            "latest_sort_key": "",
            "update_count": 0,
            "sessions": [],
            "assets": [],
            "themes": [],
        }

    for chat in raw_chats:
        item = coverage.setdefault(
            chat["canonical_title"],
            {
                "canonical_title": chat["canonical_title"],
                "title": chat["title"],
                "url": "",
                "required": chat["required"],
                "status": "missing",
                "exported_at": "",
                "latest_timestamp": "",
                "latest_sort_key": "",
                "update_count": 0,
                "sessions": [],
                "assets": [],
                "themes": [],
            },
        )
        item["title"] = chat["title"]
        item["url"] = chat["url"]
        item["required"] = chat["required"]
        item["status"] = "imported"
        item["exported_at"] = chat["exported_at"]

    for update in updates:
        canonical = update.get("canonical_chat_title") or update.get("chat_title")
        item = coverage.setdefault(
            canonical,
            {
                "canonical_title": canonical,
                "title": update.get("chat_title", canonical),
                "url": update.get("chat_url", ""),
                "required": bool(update.get("required_chat_source")),
                "status": "imported",
                "exported_at": update.get("exported_at", ""),
                "latest_timestamp": "",
                "latest_sort_key": "",
                "update_count": 0,
                "sessions": [],
                "assets": [],
                "themes": [],
            },
        )
        item["update_count"] += 1
        if not item["latest_sort_key"] or update.get("sort_key", "") > item["latest_sort_key"]:
            item["latest_sort_key"] = update.get("sort_key", "")
            item["latest_timestamp"] = update.get("timestamp", "")
        item["sessions"] = sorted(set(item["sessions"]) | {update.get("session", "")} - {""})
        item["assets"] = sorted(set(item["assets"]) | set(update.get("assets", [])))
        item["themes"] = sorted(set(item["themes"]) | set(update.get("themes", [])))

    return sorted(
        coverage.values(),
        key=lambda item: (
            not item["required"],
            item["canonical_title"].lower(),
        ),
    )


def main() -> None:
    write_feed(OUT_PATH)
    print(f"wrote {OUT_PATH}")


def write_feed(output_path: Path = OUT_PATH) -> dict:
    feed = build_feed()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(feed, ensure_ascii=False, indent=2), encoding="utf-8")
    return feed


if __name__ == "__main__":
    main()
