# Betriebs-Runbook 2026-07-01

Dieses Portal ist ein Entscheidungs- und Journal-System. Es gibt keine Anlageberatung, keine Kauf-/Verkaufsempfehlung und keine Orderfreigabe. Live-Trading ist standardmaessig deaktiviert.

## Lokaler Start

Backend starten:

```bash
PYTHONPATH=src python3 -m trading_freaks.api.server
```

Frontend starten:

```bash
npm --prefix frontend run dev -- --host 127.0.0.1 --port 5173
```

Portal oeffnen:

```text
http://127.0.0.1:5173/
```

API-Healthcheck:

```text
http://127.0.0.1:8000/api/health
```

Erwartung: `live_trading_enabled` bleibt `false`.

## Aktualitaet und Quellen

ChatGPT-/Update-Feed fortlaufend neu bauen:

```bash
python3 tools/run_realtime_update_service.py --interval-seconds 5 --force-rebuild-every-seconds 60
```

Live-Adapter aus `.env` starten:

```bash
python3 tools/run_configured_live_adapters.py --interval-seconds 5
```

TradingView-Webhooks vorbereiten oder pruefen:

```bash
python3 tools/check_tradingview_webhook_setup.py
python3 tools/check_infrastructure_readiness.py --check-public-health
```

Sicheres TradingView-Gateway starten:

```bash
python3 tools/run_tradingview_webhook_gateway.py
```

HTTPS-Tunnel nur auf das Gateway, nicht auf die komplette API, zeigen lassen:

```bash
tools/bin/cloudflared tunnel --url http://127.0.0.1:8787 --no-autoupdate
```

Dieser Quick-Tunnel ist nur temporaer. Fuer Daily Use ist ein Cloudflare Named
Tunnel oder eine andere feste HTTPS-Bridge noetig. Ablauf:
[`docs/permanent_tunnel_setup.md`](permanent_tunnel_setup.md).

Empfohlene feste HTTPS-Bridge ohne Nameserver-Umstellung:

```bash
python3 tools/register_tradingview_public_webhooks.py \
  --base-url https://wertbegleiter-trading-bridge.wertbegleiter.workers.dev \
  --worker-bridge
python3 tools/pull_cloudflare_worker_bridge.py --interval-seconds 3
```

Setup: [`docs/cloudflare_worker_bridge_setup.md`](cloudflare_worker_bridge_setup.md).

Wenn der Tunnel eine Public-Base-URL liefert:

```bash
python3 tools/register_tradingview_public_webhooks.py --base-url https://dein-tunnel.example
```

Das schreibt token-geschuetzte URLs nach `.env`:

```text
https://dein-tunnel.example/tv/<token>/price
https://dein-tunnel.example/tv/<token>/trade
```

Die vier Pflichtslots sind lokal angelegt:

- `reports/live_sources/tradingview_price.json`
- `reports/live_sources/tradingview_orders.json`
- `reports/live_sources/economic_calendar.json`
- `LIVE_NEWS_FEED_URL=https://investinglive.com/feed/`

Kurse, Orders und Kalender sind als `blocked` markiert, bis echte Provider
diese Dateien laufend aktualisieren oder echte Feed-/API-Pfade in `.env`
gesetzt werden. Der News-Slot ist per ForexLive/InvestingLive RSS-Fallback
angebunden.

Sekundenaktuelle Pruefung ist erst erlaubt, wenn alle Pflichtquellen frisch sind:

- TradingView/Broker-Kurse
- TradingView/Broker-Orders
- Wirtschaftskalender
- News/Squawk/X Pro
- ChatGPT Update Feed als Kontext, nicht als Live-Marktdatenersatz

Wenn eine Pflichtquelle `missing` oder `stale` ist, bleibt der Tagesstatus konservativ. Dann sind Kandidaten nur Screening- oder Beobachtungskandidaten.

## Tagesprozess

1. Startseite oeffnen und `Go-Live Status` pruefen.
2. `Live & News` oeffnen und Quellenstatus, Update-Feed, Blocker und Anschlussplan pruefen.
3. `Heute` fuer Tagesfahrplan, Session-Fenster und Fokus-Kandidaten nutzen.
4. `Pruefen` fuer konkrete Setup-Validierung nutzen.
5. Kein Trade ohne Stop Loss, Take Profit oder Exit-Regel, Risiko, Positionsgroesse und CRV-Pruefung.
6. Wenn ein Pflichtkriterium fehlt: Status bleibt `nicht handeln` oder `nur beobachten`.
7. Trade im `Journal` starten, Vorher-Bild einfuegen und Pflichtcheck speichern.
8. Laufenden Trade im `Journal` oder unter `Trades` weiterbearbeiten.
9. Trade abschliessen, Ergebnis eintragen, Nachher-Bild und Review ergaenzen.
10. Unter `Trades` regelmaessig `Datei speichern` nutzen.

## Journal und Datensicherung

Lokaler Dateispeicher:

```text
reports/journal_live_store.json
```

Das Backend legt beim Ueberschreiben eine Backup-Datei an. Vor dem Echtgeldbetrieb sollte das alte Paper-/Testjournal zusaetzlich exportiert werden.

Empfohlener Ablauf:

1. `Trades` oeffnen.
2. `Backup exportieren` nutzen.
3. `Echtjournal leer starten` nur nach bewusstem Backup nutzen.
4. Nach echten Eintraegen `Datei speichern` nutzen.
5. Vor groesseren Tests `Sandbox testen` nutzen, damit Live-/Echtjournal nicht verschmutzt wird.

## Review-Prozess

Ein Trade ist erst fertig, wenn folgende Punkte erledigt sind:

- Plan dokumentiert
- Vorher-Bild vorhanden
- Ergebnis in R oder Geld erfasst
- Nachher-Bild vorhanden
- Regelcheck beantwortet
- Abweichungen und Emotionen erfasst
- Review gespeichert

Offene Reviews sind keine Fehler, sondern Arbeitsposten. Sie muessen aus der Review-Liste geoeffnet, ergaenzt und abgeschlossen werden.

## Go-Live-Grenze

Lokal produktionsnah nutzbar:

- Setup-Pruefung
- Risiko-/Positionsgroessenrechnung
- Journal-Lifecycle
- Review
- lokale ChatGPT-Update-Integration
- Datei-Backup fuer das Journal

Noch nicht voll live-betriebsbereit:

- echte TradingView/Broker-Kursbridge
- echte TradingView/Broker-Orderbridge
- echte Wirtschaftskalender-API
- echte News-/Squawk-/X-Pro-Quelle

Bis diese Quellen angebunden sind, darf das Portal keine sekundengenaue Trade-Freigabe behaupten.
