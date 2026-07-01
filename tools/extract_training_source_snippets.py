#!/usr/bin/env python3
"""Print short keyword snippets from TradingFreaks PDF training material."""

from __future__ import annotations

from pathlib import Path

from pypdf import PdfReader


BASE = Path("/Volumes/NAS-Koronna/Chris/WertBegleiter/TradingFreaks/Schulungsunterlagen")
FILES = [
    "3.2-FX-Newsquellen.pdf",
    "4.1-Aktien-Start.pdf",
    "4.4_die_marktrelevanten_nachrichten.pdf",
    "4.6-Newstrade-Breakout.pdf",
    "Wirtschaftsdaten-Setup.pdf",
    "Vorboersliches-Hoch.pdf",
    "2.5-Sentiment.pdf",
    "DAX-Trading-Abpraller.pdf",
]
KEYWORDS = [
    "quelle",
    "quellen",
    "webseite",
    "seite",
    "kalender",
    "news",
    "nachrichten",
    "finviz",
    "tradingview",
    "forexfactory",
    "investing",
    "fxstreet",
    "marketwatch",
    "yahoo",
    "benzinga",
    "earnings",
    "calendar",
    "reuters",
    "bloomberg",
    "guidance",
    "sentiment",
]


def snippets_for(path: Path) -> list[tuple[int, str, str]]:
    reader = PdfReader(str(path))
    hits = []
    for page_number, page in enumerate(reader.pages, 1):
        text = (page.extract_text() or "").replace("\n", " ")
        lower = text.lower()
        for keyword in KEYWORDS:
            position = lower.find(keyword)
            if position == -1:
                continue
            snippet = " ".join(text[max(0, position - 180) : position + 320].split())
            hits.append((page_number, keyword, snippet))
            break
    return hits


def main() -> int:
    for filename in FILES:
        path = BASE / filename
        print(f"\n### {filename}")
        hits = snippets_for(path)
        for page_number, keyword, snippet in hits[:14]:
            print(f"page {page_number} [{keyword}]: {snippet[:760]}")
        print(f"hits {len(hits)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
