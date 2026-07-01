# Live-Quellen fuer den Echtgeldbetrieb

Dieses Tool gibt keine Anlageberatung und keine Orderfreigabe. Live-Quellen
dienen nur der Quellenfrische, Journal-Automatisierung und manuellen
Setup-Pruefung.

## Pflichtquellen

| Quelle | Variable | Frische | Zweck |
|---|---|---:|---|
| TradingView/Broker Kurse | `LIVE_PRICE_JSON_PATH` | 5s | Kurs-Heartbeat und Marktstatus |
| TradingView/Broker Orders | `LIVE_ORDER_JSON_PATH` | 5s | offene/geschlossene Trades ins Journal uebernehmen |
| Wirtschaftskalender | `LIVE_CALENDAR_JSON_PATH` | 900s | Risikoevents und Blocker |
| News/Squawk/X Pro | `LIVE_NEWS_FEED_URL` | 60s | Headlines, Squawk, X-Pro/RSS/API-Kontext |

Ohne echte Quelle bleibt der Status bewusst `missing`. Das ist kein Fehler,
sondern Schutz vor Schein-Live-Daten.

`KAS_WEBHOOK_BRIDGE_EVENTS_URL` und `CLOUDFLARE_WORKER_BRIDGE_EVENTS_URL`
gelten als Konfigurations-Fallback fuer Kurse und Orders. Live wird die Quelle
aber erst, wenn der jeweilige Puller frische Preis- oder Trade-Events schreibt.

## Aktuell angelegte lokale Anschluesse

Die vier Pflichtanschluesse sind lokal vorbereitet und in `.env` eingetragen:

| Quelle | Lokale Starterdatei | Aktueller Zweck |
|---|---|---|
| TradingView/Broker Kurse | `reports/live_sources/tradingview_price.json` | Platzhalter fuer Preis-Heartbeat |
| TradingView/Broker Orders | `reports/live_sources/tradingview_orders.json` | Platzhalter fuer Order-/Positions-Events |
| Wirtschaftskalender | `reports/live_sources/economic_calendar.json` | Platzhalter fuer Risikoevents |
| News/Squawk/X Pro | `https://investinglive.com/feed/` | verbundener ForexLive/InvestingLive RSS-Fallback |

Die drei lokalen Dateien fuer Kurse, Orders und Kalender sind bewusst mit
`connection_state: "blocked"` markiert. Dadurch zeigt das Portal `4/4 Adapter
konfiguriert`, aber weiterhin keinen sekundenfrischen Gesamtstatus. Der
News-Slot ist per RSS-Fallback live; Kurse, Orders und Kalender brauchen noch
echte Provider.

Technische Pruefung:

```bash
python3 tools/build_live_adapter_config_status.py
python3 tools/run_configured_live_adapters.py --once
```

## Startreihenfolge

1. `.env` pruefen. Die vier Pflichtslots sind bereits angelegt.
2. Demo-/Blockerdateien fuer Kurse, Orders und Kalender durch echte lokale Dateien oder JSON-Endpunkte ersetzen.
3. Adapter starten:

```bash
python3 tools/run_configured_live_adapters.py --interval-seconds 5
```

4. Optional Inbox-Service fuer externe TradingView-/Broker-Events starten:

```bash
python3 tools/run_live_bridge_inbox.py --interval-seconds 1
```

5. Optional feste TradingView-HTTPS-Inbox per Cloudflare Worker starten:

```bash
python3 tools/pull_cloudflare_worker_bridge.py --interval-seconds 3
```

Voraussetzung: Worker nach `docs/cloudflare_worker_bridge_setup.md` deployen
und `CLOUDFLARE_WORKER_BRIDGE_EVENTS_URL` in `.env` setzen.

6. Portal oeffnen:

```text
http://127.0.0.1:5173/
```

## JSON-Kontrakte

Preisquelle:

```json
{"bridge_type":"price","symbol":"BTCUSD","last":60447.98}
```

Orderquelle:

```json
{"bridge_type":"order","event_type":"opened","trade_id":"live-1","symbol":"BTCUSD"}
```

Kalenderquelle:

```json
{"bridge_type":"calendar","events":[{"title":"US PCE","impact":"high"}]}
```

Newsquelle:

```json
{"bridge_type":"news","items":[{"headline":"Headline","url":"https://example.test"}]}
```

RSS/Atom ist fuer `LIVE_NEWS_FEED_URL` ebenfalls erlaubt.
