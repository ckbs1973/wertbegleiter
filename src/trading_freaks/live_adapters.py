"""Configured live adapters for files, JSON endpoints and RSS/Atom feeds.

Adapters only convert external facts into bridge payloads. They do not create
trade decisions, do not send orders, and do not hold credentials.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET


PROVIDER_SOURCE_NAMES = {
    "TRADINGVIEW_BRIDGE_URL": "TradingView Webhook/Bridge",
    "BROKER_EVENT_STREAM_URL": "Broker Order/Eventstream",
    "ECONOMIC_CALENDAR_API_URL": "Wirtschaftskalender API",
    "FOREXLIVE_RSS_URL": "ForexLive/InvestingLive RSS",
    "NEWSQUAWK_API_URL": "Newsquawk API",
    "X_PRO_LIST_URL": "X Pro Liste/API",
    "SEEKING_ALPHA_NEWS_URL": "Seeking Alpha News",
}

ADAPTER_ENV_CANDIDATES = (
    ("price", "TradingView/Broker Kurse", ("LIVE_PRICE_JSON_PATH", "TRADINGVIEW_BRIDGE_URL")),
    ("order", "TradingView/Broker Orders", ("LIVE_ORDER_JSON_PATH", "BROKER_EVENT_STREAM_URL")),
    ("calendar", "Wirtschaftskalender", ("LIVE_CALENDAR_JSON_PATH", "ECONOMIC_CALENDAR_API_URL")),
    (
        "news",
        "News/Squawk/X Pro",
        (
            "LIVE_NEWS_FEED_URL",
            "NEWSQUAWK_API_URL",
            "X_PRO_LIST_URL",
            "FOREXLIVE_RSS_URL",
            "SEEKING_ALPHA_NEWS_URL",
        ),
    ),
)


@dataclass(frozen=True)
class AdapterSource:
    name: str
    bridge_type: str
    location: str
    timeout_seconds: float = 5.0

    def __post_init__(self) -> None:
        if self.bridge_type not in {"price", "order", "calendar", "news"}:
            raise ValueError("bridge_type must be price, order, calendar or news")
        if not self.location.strip():
            raise ValueError("adapter location is required")


def is_url(location: str) -> bool:
    return location.startswith("http://") or location.startswith("https://")


def read_adapter_text(source: AdapterSource) -> str:
    if is_url(source.location):
        request = Request(source.location, headers={"User-Agent": "WertBegleiter-Kapitalmarkt/0.1"})
        with urlopen(request, timeout=source.timeout_seconds) as response:  # nosec - user-configured local/live source
            return response.read().decode("utf-8", errors="replace")
    return Path(source.location).read_text(encoding="utf-8")


def _looks_like_json(text: str) -> bool:
    stripped = text.lstrip()
    return stripped.startswith("{") or stripped.startswith("[")


def _rss_items(text: str, *, max_items: int = 20) -> list[dict[str, Any]]:
    root = ET.fromstring(text)
    items = []
    for item in root.findall(".//item"):
        title = item.findtext("title") or ""
        link = item.findtext("link") or ""
        published = item.findtext("pubDate") or item.findtext("published") or ""
        if title.strip():
            items.append({"headline": title.strip(), "url": link.strip(), "published": published.strip()})
    if items:
        return items[:max_items]

    namespaces = {"atom": "http://www.w3.org/2005/Atom"}
    for entry in root.findall(".//atom:entry", namespaces):
        title = entry.findtext("atom:title", default="", namespaces=namespaces)
        updated = entry.findtext("atom:updated", default="", namespaces=namespaces)
        link_el = entry.find("atom:link", namespaces)
        link = link_el.attrib.get("href", "") if link_el is not None else ""
        if title.strip():
            items.append({"headline": title.strip(), "url": link.strip(), "published": updated.strip()})
    return items[:max_items]


def payload_from_adapter_text(source: AdapterSource, text: str) -> dict[str, Any]:
    if _looks_like_json(text):
        payload = json.loads(text)
        if isinstance(payload, list):
            return {"bridge_type": source.bridge_type, "items" if source.bridge_type == "news" else "events": payload}
        if not isinstance(payload, Mapping):
            raise ValueError("JSON adapter payload must be an object or list")
        result = dict(payload)
        result.setdefault("bridge_type", source.bridge_type)
        result.setdefault("source_name", source.name)
        return result

    if source.bridge_type != "news":
        raise ValueError("non-JSON adapter text is only supported for news RSS/Atom feeds")
    items = _rss_items(text)
    return {
        "bridge_type": "news",
        "source_name": source.name,
        "items": items,
        "item_count": len(items),
    }


def read_adapter_payload(source: AdapterSource) -> dict[str, Any]:
    return payload_from_adapter_text(source, read_adapter_text(source))


def configured_sources_from_env(env: Mapping[str, str]) -> tuple[AdapterSource, ...]:
    sources: list[AdapterSource] = []
    timeout = float(env.get("LIVE_ADAPTER_TIMEOUT_SECONDS", "5") or 5)
    for bridge_type, canonical_name, keys in ADAPTER_ENV_CANDIDATES:
        for key in keys:
            location = str(env.get(key, "")).strip()
            if not location:
                continue
            name = PROVIDER_SOURCE_NAMES.get(key, canonical_name)
            sources.append(
                AdapterSource(name=name, bridge_type=bridge_type, location=location, timeout_seconds=timeout)
            )
            break
    return tuple(sources)
