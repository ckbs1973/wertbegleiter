# WertBegleiter® Kapitalmarkt

Dieses Repository ist ein sicherer, testbarer Startpunkt fuer WertBegleiter® Kapitalmarkt: ein TradingFreaks-konformes Trading-System. Es fuehrt keine Broker-Orders aus und gibt keine Anlageberatung. Alle Ausgaben sind als Information, Analyse oder Checklistenunterstuetzung zu verstehen.

## Aktueller Umfang

- Basis-Datenmodelle fuer Kerzen, Trades, Setup-Validierung, Risikoplaene, Journal, News, Wirtschaftsdaten und Sentiment.
- Risiko-Engine mit Stop-Loss-Pflicht, CRV-Pruefung, Positionsgroessenberechnung und Schutzwarnungen.
- Setup-Checklisten fuer Wirtschaftsdaten-FX, US-News-Breakout, US-News-Reversal, Reversal ohne News, Rectangle, vorboersliches Hoch/Tief, FX-Trendlinien und DAX-Abpraller.
- Journal-Review mit Trefferquote, Durchschnitts-R, Erwartungswert, Profit Factor, Drawdown, Verlustserie und Regelverstoessen.
- Journal-Validierung fuer Emotionen, Regelverstoesse und Screenshots.
- Daily-Trading-Update fuer scalping-fokussierte Tagesplanung mit 2-5-Trade-Qualitaetskorridor, Uhrzeit, CRV, Positionsgroesse, Tageslimit und Psychologie-Gates.
- Backtesting-Grundgeruest mit history-only Strategieaufruf, Entscheidungslog, Spread, Slippage und konservativer Bracket-Simulation.
- Framework-neutrales Python-Backend unter `src/trading_freaks/api`.
- React/Vite-Frontend unter `frontend` mit Focus Desk, Session-Fahrplan, Kandidatenboard, RiskPlan, 5 TradingFreaks-Pre-Checks, Journal-Cockpit, Review-Ansicht und Backtest-Kostenmodell.
- Unit-Tests fuer Risikoregeln, Setup-Validierung, Journal und Backtesting.
- Architektur-Gap-Analyse in `docs/architecture_gap_analysis.md`.

## Sicherheitsgrundsaetze

- Kein Live-Trading.
- Keine Broker-Integration.
- Keine Kauf- oder Verkaufsempfehlungen.
- Kein Trade ohne Stop Loss.
- Kein Setup-Freigabe-Status ohne RiskPlan, Stop Loss und Exit-Plan.
- `trade_allowed=True` bedeutet nur: Die hinterlegten Regelkriterien sind fuer eine manuelle Pruefung erfuellt. Es ist keine Handlungsaufforderung.

## Daily Trading Update

Das Daily Board ist fuer den taeglichen Workflow vor und waehrend der US-Session gedacht. Es erzwingt keine Trades. Der Bereich `2-5 Trades` ist ein Qualitaetskorridor und kein Tagesziel.

- Tageskontrolle: Kontostand, Default-Risiko, bisherige Trades, Verlustserie, Psychologie und Verlustlimits.
- Start/Tagesmodus: fuehrt durch Tagesstatus, Asset/Setup, Richtung, RiskPlan, 5 Pre-Checks, Entscheidung, Journal und Review. Der erste offene Schritt ist die naechste Aktion.
- Setup-Kandidaten: Symbol, Setup, Richtung, Uhrzeit, Entry, Stop Loss, Take Profit, Tick-/Punktwert und Pflichtkriterien.
- Ergebnis: `Nicht handeln`, sobald ein Pflichtkriterium fehlt, das Tageslimit erreicht ist, der Psychologie-Check blockiert, Stop/TP ungueltig sind oder das CRV unter 1:1 liegt.
- Ausgabe: Positionsgroesse, Risiko-Betrag, Risiko je Einheit, CRV, Warnungen und konkrete Blockadegruende.
- 5 Pre-Checks aus den TradingFreaks-Unterlagen: Trading Setup, Beste Gelegenheit, Trade Management, Ueberzeugung/Disziplin und Journal vorbereitet. Ergebnis und Review bleiben im Nach-Trade-Journal.
- Setup-Karte im Focus Desk: Fokus, Entry-Logik, Exit/Risiko, benoetigte Bestaetigungen und Blocker werden pro aktivem Setup verdichtet angezeigt.
- Updates-Ansicht: lokal importierte ChatGPT-Trading-Projektchats werden als News-/Session-Feed mit Zeitstempel, Session, Assetbezug, Themen, Pflichtchecks und Blockern angezeigt. Die vier Pflicht-Update-Chats sind `Trading Update Daily`, `Taegliches Marktupdate und Trading-Setups`, `US open update and trade scenarios` und `Europe session update and trade scenarios`; Breaking News und Webchecks laufen als Zusatzkontext. Neue lokale Chat-Exporte koennen mit `python3 tools/build_chatgpt_update_feed.py` nach `frontend/public/data/chatgpt_trading_updates.json` ueberfuehrt werden.
- Live-Status: Sekundenaktualitaet wird separat ueber `frontend/public/data/live_feed_status.json` geprueft. Das Portal zeigt nur dann `Sekundenfrisch`, wenn alle Pflichtquellen innerhalb ihrer Frischegrenze liegen. Ohne echte Kurs-, Order-, Kalender- und News-Streams bleibt der Status bewusst `Nicht live`.
- Chat-basierte Pruefkandidaten: Der Focus Desk leitet aus den importierten Updates priorisierte potentielle Trade-Pruefungen ab. Das Ranking nutzt Aktualitaet, Session-Relevanz, Assetbezug, Themen, Pflichtchecks und Blocker. Diese Kandidaten sind keine Signale; sie bleiben `Bedingt`, bis aktuelle Kurse, Richtung, Entry, Stop Loss, Take Profit, CRV und die 5 Pre-Checks manuell bestaetigt wurden.
- Journal-Cockpit: Vor-Trade-Emotion, Ueberzeugung, Stress, Screenshots per Copy/Paste, Drag & Drop oder Datei, Ergebnis in R/Geld, Gebuehren, Slippage, Regelverstoesse und Review in einem eigenen Arbeitsbereich.
- Daily Journal: gefuehrter Tagesabschluss mit Plan, Vorher-Bild, Ergebnis, Nachher-Bild und Review als klare Arbeitsschritte.
- Trades-Ansicht: lange Journalhistorie aller geladenen Broker-Imports und Tagesentwuerfe mit technischer Review-Einstufung (`Technisch offen`, `Risiko auffaellig`, `Regelabweichung`, `Dokumentiert`) sowie Filter nach Woche, Monat, Quartal, Jahr und Assetklasse.
- Echtjournal-Bereinigung: Die Trades-Seite bietet einen Backup-Export und kann lokale Live-Drafts verlustfrei als Paper/Test archivieren, damit das Echtgeld-Journal sauber starten kann.
- Lokaler Journal-Dateisync: Wenn das Backend laeuft, kann die Trades-Seite Journal-Drafts nach `reports/journal_live_store.json` speichern und daraus laden. Das ersetzt Browser-LocalStorage als alleinige Quelle.
- Sandbox-Testmodus: Ueber die Go-Live-/Trades-Kacheln kann ein isolierter Testmodus gestartet werden (`?sandbox=1`). Er nutzt einen getrennten Browser-Speicher und schuetzt das normale Journal vor UI-Testaktionen.
- Review-Ansicht: importierte Brokerdaten plus Entwuerfe, offene Nacharbeit, Dokumentationsluecken, schwache Symbole, haeufige Blocker, Durchschnitts-R, bekannte Regelquote und Trefferquote als Prozessmetriken.
- Anleitung: kurze Bedienlogik fuer Focus Desk, Journal, Trades und Review direkt in der App.
- GBE-End-of-Day-Reports koennen mit `tools/import_gbe_eod_report.py` in journalfaehige CSV/JSON-Dateien umgewandelt werden. Brokerreports liefern objektive Ausfuehrungsdaten; SL, TP, CRV, Setup-Kriterien, Screenshots und Emotionen bleiben manuelle Journal-Nacharbeit.
- Trade-Event-Capture: Externe Paper-/Demo-/Broker-/TradingView-Events koennen ueber `/api/trade-events/capture` in Journal-Lifecycle-Aktionen uebersetzt werden (`opened`, `closed_stop_loss`, `closed_take_profit`, `closed_manual`). Die Route fuehrt keine Orders aus, sondern startet oder schliesst nur Journal-Entwuerfe auf Basis bekannter Trade-Fakten.
- Frontend-Event-Import: Im Journal koennen dieselben TradingView-/Broker-Eventdaten als JSON eingefuegt werden. `opened` erstellt oder aktualisiert einen laufenden Trade, `closed_*` schliesst ihn ueber dieselbe `trade_id`, berechnet soweit moeglich das realisierte R und verschiebt ihn in die Review-Warteschlange. Mehrere parallele Trades werden ueber eindeutige `trade_id`s getrennt.
- TradingView-macOS-Capture: `tools/capture_tradingview_event.py` aktiviert die lokale TradingView-App, erstellt optional einen Screenshot des sichtbaren Charts und erzeugt ein Journal-Event-JSON fuer den Frontend-Import. Das Tool liest keine Orders aus TradingView und fuehrt keine Orders aus.
- TradingView-Webhook-Setup: `tools/check_tradingview_webhook_setup.py` prueft lokale Webhook-Ziele, Public-/Tunnel-URLs, Tunnel-Tool und JSON-valide Alert-Templates. TradingView braucht fuer echte Zustellung eine oeffentliche HTTPS-URL auf Port 443.
- TradingView-Gateway: `tools/run_tradingview_webhook_gateway.py` stellt nur zwei token-geschuetzte POST-Routen bereit: `/tv/<token>/price` und `/tv/<token>/trade`. Das Gateway leitet intern an die lokale API weiter und fuehrt keine Orders aus.
- ALL-INKL/KAS-Webhook-Bridge: `deploy/kas_webhook_bridge` kann ohne Cloudflare auf dem KAS-Webspace laufen. `tools/pull_kas_webhook_bridge.py` holt gespeicherte Events lokal ab, aktualisiert Live-Status und schreibt Trade-Events in `reports/journal_live_store.json`.
- TradingView-Public-URL registrieren: `tools/register_tradingview_public_webhooks.py --base-url https://dein-tunnel.example` schreibt die token-geschuetzten Preis- und Trade-Webhook-Ziele sicher in `.env`, ohne Live-Trading zu aktivieren.
- Das Frontend laedt lokale Testimporte aus `frontend/public/data/`: rekonstruierte TradingView/GBE-Trades, GBE-Monatsberichte und den letzten EOD-Report. Diese Eintraege sind als `Review offen` markiert, bis die TradingFreaks-Pflichtfelder manuell ergaenzt wurden.

## Sekundenaktuelle Daten

Das Portal unterscheidet zwischen `aktualisiert geladen` und `sekundenfrisch`.

- `chatgpt_trading_updates.json`: strukturierter Kontext aus Chat-/News-/Tagesupdate-Importen. Dieser Feed kann automatisch neu geladen werden, ist aber nur so aktuell wie seine erzeugte Datei.
- `chatgpt_trading_update_extras.json`: optionaler Zusatzkontext, z. B. tagesaktuelle Webchecks. Diese Extras bleiben beim Neuaufbau des ChatGPT-Feeds erhalten.
- `live_feed_status.json`: technische Frischepruefung fuer Pflichtquellen. Preis- und Orderdaten gelten standardmaessig nach 5 Sekunden als stale, News nach 60 Sekunden, Kalenderdaten nach 15 Minuten.
- `tools/build_live_feed_status.py`: erzeugt eine lokale Statusdatei. Ohne echte API-/WebSocket-Verbindungen markiert sie die Pflichtquellen korrekt als `missing` bzw. `Nicht live`.
- `tools/run_live_feed_collector.py`: schreibt `live_feed_status.json` fortlaufend, standardmaessig jede Sekunde. Wenn der Collector stoppt, markiert das Frontend die Statusdatei nach wenigen Sekunden als stale.
- `tools/run_realtime_update_service.py`: baut den ChatGPT-Update-Feed laufend neu, bewahrt Zusatz-Webchecks und schreibt einen `chat_context`-Heartbeat in den Live-Status. Aenderungen an lokalen ChatGPT-Exporten werden dadurch automatisch im Portal sichtbar.
- `tools/ingest_live_source.py`: Bridge-Einstieg fuer externe Prozesse. TradingView-/Broker-/News-Skripte koennen damit pro Quelle einen frischen Zeitstempel in `live_source_snapshots.json` schreiben.
- `tools/run_live_bridge_inbox.py`: beobachtet `reports/live_bridge_inbox` auf lokale JSON-Dateien von TradingView-/Broker-, Kalender- oder News-Adaptern. Neue oder geaenderte Dateien werden in Heartbeats uebersetzt; Dateien werden nicht geloescht und es werden keine Orders ausgefuehrt.
- `tools/run_configured_live_adapters.py`: liest in `.env` konfigurierte lokale JSON-Dateien, JSON-Endpunkte oder RSS/Atom-Newsfeeds und schreibt sie in dieselbe Live-Bridge. Das ist der Einstieg fuer echte Preis-, Order-, Kalender- und Newsadapter.
- `/api/live-sources/heartbeat`: lokaler HTTP-Einstieg fuer dieselben Heartbeats. Die Route aktualisiert `live_source_snapshots.json` und baut `live_feed_status.json` sofort neu. Sie speichert nur Quellenfrische, keine Orders und keine Trade-Empfehlungen.
- `/api/live-bridge/ingest`: einfacherer lokaler HTTP-Einstieg fuer Bridge-Payloads wie `{"bridge_type":"price","symbol":"BTCUSD","last":60447.98}`. Die Route normalisiert die Daten in Heartbeats und fuehrt keine Orders aus.
- Lokale Pflichtanschluesse sind in `.env` vorbereitet: `reports/live_sources/tradingview_price.json`, `tradingview_orders.json`, `economic_calendar.json` und `LIVE_NEWS_FEED_URL=https://investinglive.com/feed/`. Kurse, Orders und Kalender sind als `blocked` markiert, bis echte Provider diese Dateien laufend aktualisieren oder echte URLs gesetzt werden; News ist per RSS-Fallback live angebunden.
- Fuer echte Sekundenaktualitaet muessen Live-Quellen in `.env` konfiguriert werden, z. B. TradingView-/Broker-Bridge, Order-Eventstream, Wirtschaftskalender-API und News-/Squawk-/X-Pro-Quelle.
- Auch bei `Sekundenfrisch` bleibt jeder Output Information und Checklistenunterstuetzung. Es gibt keine Orderfreigabe und keine Kauf-/Verkaufsempfehlung.
- Finales Betriebs-Runbook fuer Start, Tagesprozess, Journal-Sicherung und Go-Live-Grenze: [`docs/operations_runbook.md`](docs/operations_runbook.md).
- Provider-Anschlussstatus und Payload-Beispiele: [`docs/provider_connections.md`](docs/provider_connections.md).
- Kompakter Anschlussplan fuer den Echtgeldbetrieb: [`docs/live_source_setup.md`](docs/live_source_setup.md).
- Dauerhafter TradingView-Webhooks-Tunnel: [`docs/permanent_tunnel_setup.md`](docs/permanent_tunnel_setup.md).
- Cloudflare-freie ALL-INKL/KAS-Webhook-Bridge: [`docs/kas_webhook_bridge_setup.md`](docs/kas_webhook_bridge_setup.md).
- Git-/Remote-Setup: [`docs/git_setup.md`](docs/git_setup.md).
- Aktueller Go-Live-Audit mit Funktionsstatus, Blockern und Erweiterungen: [`docs/functionality_audit_2026-07-01.md`](docs/functionality_audit_2026-07-01.md).

Immer-aktuell-Dienst lokal starten:

```bash
python3 tools/run_realtime_update_service.py --interval-seconds 5
```

Dieser Dienst haelt ChatGPT-Exporte und Zusatzkontext im Portal aktuell. Er ersetzt keine echten Kurs-, Order-, Kalender- oder News-Streams. Ohne diese Quellen bleibt der Gesamtstatus konservativ `Teilweise live` oder `Nicht live`.

Nur den Live-Collector lokal starten:

```bash
python3 tools/run_live_feed_collector.py --interval-seconds 1
```

Lokale Bridge-Inbox fuer echte Adapter starten:

```bash
python3 tools/run_live_bridge_inbox.py --interval-seconds 1
```

Adapter koennen dann JSON-Dateien nach `reports/live_bridge_inbox/` schreiben. Beispiele:

```json
{"bridge_type":"price","symbol":"BTCUSD","last":60447.98}
```

```json
{"bridge_type":"order","event_type":"opened","trade_id":"paper-1","symbol":"BTCUSD"}
```

```json
{"bridge_type":"calendar","events":[{"title":"US PCE","impact":"high"}]}
```

```json
{"bridge_type":"news","items":[{"headline":"Squawk heartbeat"}]}
```

Erst wenn `price`, `order`, `calendar` und `news` frisch sind, wechselt der Live-Status auf `Sekundenfrisch`. Ein frischer ChatGPT-Feed allein reicht bewusst nicht fuer sekundenaktuelle Trade-Pruefung.

Konfigurierte Live-Adapter ueber `.env` starten:

```bash
python3 tools/run_configured_live_adapters.py --interval-seconds 5
```

Unterstuetzte Variablen:

```env
LIVE_PRICE_JSON_PATH=/lokaler/pfad/price.json
LIVE_ORDER_JSON_PATH=/lokaler/pfad/orders.json
LIVE_CALENDAR_JSON_PATH=/lokaler/pfad/calendar.json
LIVE_NEWS_FEED_URL=https://example.test/feed.xml
```

`LIVE_NEWS_FEED_URL` darf JSON, RSS oder Atom liefern. Preis-, Order- und Kalenderquellen sollten JSON liefern. Ohne gesetzte Variablen beendet sich der Adapter-Runner ohne Fehler und veraendert keinen Status.

Sicherer TradingView-Webhook-Pfad:

```bash
PYTHONPATH=src python3 -m trading_freaks.api.server
python3 tools/run_tradingview_webhook_gateway.py
tools/bin/cloudflared tunnel --config config/cloudflare/wertbegleiter-trading.yml run wertbegleiter-trading
python3 tools/register_tradingview_public_webhooks.py --base-url https://trading-webhooks.wertbegleiter.eu
```

TradingView bekommt danach nur die beiden Gateway-URLs `/tv/<token>/price`
und `/tv/<token>/trade`. Die komplette lokale API wird nicht als Public-URL
registriert.

Cloudflare-freier KAS-Pfad:

```bash
python3 tools/register_tradingview_public_webhooks.py \
  --base-url https://wertbegleiter.eu/wb-bridge \
  --kas-bridge
python3 tools/pull_kas_webhook_bridge.py --interval-seconds 3
```

Voraussetzung ist, dass `deploy/kas_webhook_bridge` auf dem KAS-Webspace
deployt und `KAS_WEBHOOK_BRIDGE_EVENTS_URL` in `.env` gesetzt ist. Der Puller
holt gespeicherte TradingView-Events ab, schreibt Preis-/Order-Heartbeats und
uebernimmt Trade-Open/-Close-Events in den lokalen Journal-Store.

Infrastruktur-Readiness pruefen:

```bash
python3 tools/check_infrastructure_readiness.py --check-public-health
```

Fuer Daily Use muss ein Git Remote gesetzt sein und der temporaere
`trycloudflare.com`-Tunnel durch einen Named Tunnel oder eine andere feste
HTTPS-Bridge ersetzt werden.

Aktueller Named Tunnel: `wertbegleiter-trading` auf
`trading-webhooks.wertbegleiter.eu`. Cloudflare ist vorbereitet; produktive
Erreichbarkeit setzt voraus, dass die Nameserver von `wertbegleiter.eu` beim
Domain-Anbieter auf `cortney.ns.cloudflare.com` und
`glen.ns.cloudflare.com` umgestellt sind.

Beispiel fuer einen externen Preis-Heartbeat:

```bash
python3 tools/ingest_live_source.py \
  --source-name "TradingView/Broker Kurse" \
  --category price \
  --connection-state connected \
  --item-count 1 \
  --detail "Bridge-Heartbeat, keine Orderausfuehrung"
```

Solange nur Preise verbunden sind, bleibt der Gesamtstatus `Teilweise live`, weil Orders, Kalender und News weiterhin fehlen. `Sekundenfrisch` erscheint erst, wenn alle Pflichtkategorien innerhalb ihrer Frischegrenzen aktualisiert werden.

HTTP-Heartbeat bei laufendem Backend senden:

```bash
curl -X POST http://127.0.0.1:8000/api/live-sources/heartbeat \
  -H 'content-type: application/json' \
  -d '{
    "source_name": "News/Squawk/X Pro",
    "category": "news",
    "connection_state": "connected",
    "item_count": 3,
    "details": ["lokaler News-Bridge-Heartbeat, keine Orderausfuehrung"]
  }'
```

Einfacher Bridge-POST bei laufendem Backend:

```bash
curl -X POST http://127.0.0.1:8000/api/live-bridge/ingest \
  -H 'content-type: application/json' \
  -d '{"bridge_type":"price","symbol":"BTCUSD","last":60447.98}'
```

## Lokale Nutzung

```bash
PYTHONPATH=src python3 -m unittest discover -s tests
python3 -m compileall src tests
npm --prefix frontend run lint
```

Trade-Event-Capture lokal testen:

```bash
PYTHONPATH=src python3 -m trading_freaks.api.server
```

Dann `POST /api/trade-events/capture` mit einem Event wie:

```json
{
  "event_type": "opened",
  "source": "tradingview_webhook",
  "trade_id": "btc-paper-1",
  "symbol": "BTCUSD",
  "market": "crypto",
  "timestamp": "2026-06-27T10:15:00+02:00",
  "direction": "long",
  "entry": 60000,
  "stop_loss": 59500,
  "take_profit": 61000,
  "size": 0.1,
  "screenshot_path": "screenshots/btc-before.png"
}
```

TradingView MacOS App Screenshot plus Journal-Event erzeugen:

```bash
python3 tools/capture_tradingview_event.py \
  --event-type opened \
  --trade-id btc-paper-1 \
  --symbol BTCUSD \
  --market crypto \
  --direction long \
  --entry 60000 \
  --stop-loss 59500 \
  --take-profit 61000 \
  --size 0.1 \
  --copy
```

Beim Schliessen desselben Paper-/Demo-Trades dieselbe `trade-id` verwenden:

```bash
python3 tools/capture_tradingview_event.py \
  --event-type closed_take_profit \
  --trade-id btc-paper-1 \
  --symbol BTCUSD \
  --market crypto \
  --exit-price 61000 \
  --copy
```

Mit `--copy` liegt das Event-JSON direkt in der Zwischenablage und kann im Journal unter `TradingView/Broker Event` eingefuegt und verarbeitet werden. Wenn macOS keinen Screenshot erlaubt, in den Systemeinstellungen `Bildschirmaufnahme` fuer Terminal/Codex freigeben oder `--no-screenshot` nutzen.

Optional, falls Ruff lokal installiert ist:

```bash
python3 -m ruff check src tests
```

Backend lokal starten:

```bash
PYTHONPATH=src python3 -m trading_freaks.api.server
```

Journal-Dateisync pruefen:

```bash
curl http://127.0.0.1:8000/api/journal/store
```

Das Backend speichert Journal-Drafts lokal unter `reports/journal_live_store.json` und legt beim Ueberschreiben eine Backup-Datei an. Es fuehrt keine Orders aus.

Frontend starten, sobald die Node-Dependencies installiert sind:

```bash
npm --prefix frontend install
npm --prefix frontend run dev
```

GBE-End-of-Day-Reports werden als Originalquelle unter `reports/source_reports/` abgelegt. Einen Report fuer das Journal importieren:

```bash
python3 tools/import_gbe_eod_report.py "/pfad/zum/End of Day Report.pdf"
```

Falls das System-Python `pypdf` nicht installiert hat, zuerst die Projektabhaengigkeiten installieren oder die gebuendelte Codex-Python-Laufzeit verwenden.

## Beispiel

```python
from trading_freaks.models import Direction
from trading_freaks.risk.position_sizing import calculate_risk_plan
from trading_freaks.setups.us_news_breakout_checklist import (
    USNewsBreakoutInput,
    evaluate_us_news_breakout,
)

risk = calculate_risk_plan(
    account_equity=10_000,
    risk_percent=1.0,
    direction=Direction.LONG,
    entry=101.0,
    stop_loss=100.0,
    take_profit=102.0,
)

result = evaluate_us_news_breakout(
    USNewsBreakoutInput(
        symbol="EXAMPLE",
        direction=Direction.LONG,
        daily_volume=2_000_000,
        is_penny_stock=False,
        has_news_catalyst=True,
        news_is_mixed=False,
        gap_percent=4.2,
        main_session_started=True,
        momentum_in_news_direction_by_1545=True,
        price_on_correct_vwap_side=True,
        consolidation_minutes=7,
        consolidation_is_tight=True,
        correction_fraction_of_momentum=0.25,
        pattern_type="flag",
        rvol=1.8,
        rvol_anticipated=False,
        entry_is_near_breakout=True,
        movement_is_momentum_not_volatility=True,
        close_by_end_of_day_planned=True,
    ),
    risk_plan=risk,
)
```

## Backtesting-Grundsatz

`BacktestEngine` ruft Strategie-Funktionen nur mit `candles[:i + 1]` auf. Die Simulation nutzt erst danach liegende Kerzen. Spread und Slippage werden als schlechtere Entry-/Exit-Preise modelliert. Wenn Stop Loss und Take Profit in derselben Kerze beruehrt werden, wird konservativ der Stop Loss angenommen, weil ohne Intrabar-Daten keine bessere Reihenfolge bekannt ist.

## Chat-Kontext

- Chat 1: Trading-App mit Setup-Checklisten, Fokus US-Aktien-Newstrade-Breakout, React Frontend und Python Backend.
- Chat 2: Journal mit Emotionen, Regelverstoessen und Screenshots.
- Chat 3: Backtesting ohne Lookahead-Bias mit Spread und Slippage.
- ChatGPT-Projektchats lokal importiert: Daily Update, Breaking News zu Oel/Yen/Tech, taegliches Marktupdate, US Open Szenarien und Europe Session Szenarien; siehe `docs/imported_chatgpt_project/trading_project_rules_summary.md`. Es gibt keine automatische Live-Synchronisation mit privaten ChatGPT-Projektchats.

## Importiertes Session-Playbook

- Daily Update ab 08:00 mit Kalender, Wochenplan, Oel, USD/Yields, Tech/AI, JPY und Metallblock.
- Europe Session `10:00-12:00`: DE40/EURUSD/USDJPY/XAU/XAG nur nach ORB, Retest, Level- und Eventcheck.
- US Open Prep um ca. 15:25; erste US-Open-5-Minuten-Kerze ist No-Trade.
- US Momentum Window `16:30-18:00`: 5-15 Minuten nach Event/Open/Repricing warten; Pullback oder Break-and-Retest bevorzugen.
- XAGUSD ist dauerhaft mit XAUUSD/XAUEUR, USD/Yields, Gold/Silber-Ratio, China-/Industriebezug und Metall-Exposure zu pruefen.
- Breaking-News-Updates beginnen mit Datum/Uhrzeit und bleiben bedingte Szenarien, keine Signale.
