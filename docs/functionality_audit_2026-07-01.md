# Funktionaler Go-Live-Audit 2026-07-01

Kontext: WertBegleiter Kapitalmarkt ist ein Trading-Management- und Entscheidungsunterstuetzungs-Tool. Es gibt keine Anlageberatung, keine Kauf-/Verkaufsempfehlung, keine Orderfreigabe und keine Broker-Orderausfuehrung.

## Executive Summary

Der lokal testbare Kern des Portals funktioniert: Frontend erreichbar, Navigation oeffnet alle Hauptseiten, Tests laufen durch, Build ist erfolgreich, keine sichtbaren `NaN`-/`undefined`-Fehler im Browser-Smoke-Test.

Das Tool ist fuer echten Live-Betrieb noch nicht voll produktionsbereit, weil drei externe Pflichtquellen noch nicht live angebunden sind:

- TradingView/Broker Kurse: `blocked`
- TradingView/Broker Orders: `blocked`
- Wirtschaftskalender: `blocked`
- News/Squawk/X Pro: `live` per ForexLive/InvestingLive RSS-Fallback
- `.env`: vorhanden
- konfigurierte Live-Adapter: 4/4

Das ist kein kosmetischer Fehler, sondern ein korrekter Sicherheitsblocker. Ohne echte Kurs-, Order- und Kalenderquelle darf das Tool keine sekundengenaue Trade-Pruefung behaupten.

## Verifizierter Ist-Zustand

| Bereich | Ergebnis | Nachweis |
| --- | --- | --- |
| Frontend | Laeuft | `http://127.0.0.1:5173/` liefert HTTP 200; Vite-Prozess hoert auf Port 5173. |
| Backend/API | Laeuft | `http://127.0.0.1:8000/api/health` liefert `{"status":"ok","live_trading_enabled":false}`. |
| Realtime-Update-Service | Laeuft | `tools/run_realtime_update_service.py` schreibt Feed und Live-Status laufend neu. |
| Unit-/Integrationstests | Bestanden | `PYTHONPATH=src python3 -m pytest`: 112 passed. |
| Frontend-Lint | Bestanden | `npm run lint`: Frontend structure OK. |
| Frontend-Build | Bestanden | `npm run build`: Vite Build erfolgreich. |
| Browser-Navigation | Bestanden | Heute, Pruefen, Live & News, Journal, Trades, Review, Hilfe oeffnen. |
| Browser-Fehlersymptome | Keine gefunden | Keine sichtbaren `NaN` oder `undefined` in den geprueften Seiten. |
| Go-Live Panel | Bestanden | Startseite zeigt Live-Quellen, Update-Stand, Echtjournal und Testmodus als harte Statuskacheln. |
| Live-Anschlusspfad | Bestanden | Button `Anschlussplan` oeffnet Live & News, klappt Details auf und springt zum Anschlussplan fuer Live-Quellen. |
| TradingView-Webhooks | Formal bereit, HTTPS extern blockiert | Lokale Endpunkte, token-geschuetztes Gateway und JSON-Templates sind aktiv; der externe KAS-HTTPS-Healthcheck scheitert am Zertifikat fuer `wertbegleiter.eu`. |
| Cloudflare Worker Bridge | Deployt und getestet | `https://wertbegleiter-trading-bridge.wertbegleiter.workers.dev/health` liefert `status=ok`; Smoke-Test-Heartbeat wurde gespeichert und lokal verarbeitet. |
| Journal-Bereinigung | Vorhanden | Trades-Seite bietet Backup-Export, Echtjournal-Start und Sandbox-Testmodus. Bereinigung archiviert statt zu loeschen. |
| Journal-Dateisync | Vorhanden | Mit laufendem Backend kann das Portal Journal-Drafts nach `reports/journal_live_store.json` speichern und daraus laden. |
| Betriebs-Runbook | Vorhanden | `docs/operations_runbook.md` beschreibt Start, Tagesprozess, Journal-Sicherung, Review und Go-Live-Grenze. |
| Sandbox-Testmodus | Bestanden | Separater Speicher via `?sandbox=1`; Testmodus kann gestartet und wieder beendet werden. |
| Live-Status | Teilweise live | News per RSS-Fallback live; Kurse, Orders und Kalender noch blockiert. |
| ChatGPT Update Feed | Technisch eingebunden | 4/4 Pflicht-Chats, 110 Updates. |
| Tagesaktualitaet ChatGPT | Nicht ausreichend | Neuester Pflicht-Chat: 24.06.2026; neuester Zusatzkontext: 30.06.2026. Heute ist 01.07.2026. |
| Journal/Trades | Grundfunktion sichtbar | 0 laufende Trades, 2 aktive Reviews im sichtbaren Echtjournal. |

## Seiten-Audit

| Seite | Auftrag | Status | Bewertung |
| --- | --- | --- | --- |
| Heute | Management-Blick: Tagesstatus, naechste Aktion, Kandidaten, Review, Journal | Funktioniert lokal | Gute Startseite fuer Entscheidungen. Weiterhin nur Status, keine Empfehlung. |
| Pruefen | Setup-Check: Asset, Richtung, Entry, Stop, Ziel, Risiko, CRV, 5 Pre-Checks | Funktioniert lokal | Richtiger Ort fuer manuelle Setup-Freigabe. Alte Updates erzeugen keine heutigen Kandidaten. |
| Live & News | Quellenstatus, ChatGPT-Updates, News-/Session-Kontext, Live-Blocker | Funktioniert teilweise | Prozesspfad ist vorhanden, Details sind einklappbar. Echte News-/Squawk-/X-Pro-Quelle fehlt. |
| Journal | Laufende Trades starten, Abschluss, Bilder, Ergebnis/R, Review | Funktioniert lokal | Aktuell keine laufenden Trades sichtbar; 2 Reviews offen. Automatik braucht Order-Bridge. |
| Trades | Lange Liste, Filter nach Zeitraum und Assetklasse, technische Bewertung | Funktioniert lokal | Default zeigt Echt/Live Journal; Archiv/Paper separat filterbar. |
| Review | Offene Nacharbeit, Muster, Dokumentationsluecken, Wochenreview | Funktioniert lokal | Review-Arbeitsliste ist nutzbar, aber nur so gut wie Journal-Status/Bilder/R-Werte. |
| Hilfe | Bedienlogik | Funktioniert | Kurz und prozessnah. |

## Feld- und Funktionsaudit

| Funktion | Auftrag | Status |
| --- | --- | --- |
| Asset-Auswahl | Symbol eindeutig fuer Kandidat/Trade setzen | Vorhanden. |
| Richtung Long/Short/Bedingt | Keine Richtung ohne Bestaetigung | Vorhanden; Default bleibt konservativ. |
| Entry | Einstieg dokumentieren | Vorhanden. |
| Stop Loss | Pflicht-Risikogrenze | Vorhanden; Prozess blockiert unvollstaendige Trades. |
| Take Profit / Ziel | Exit-Plan fuer CRV | Vorhanden. |
| Risiko % | Default 1 Prozent, Warnung bei hoeherem Risiko | Vorhanden. |
| Positionsgroesse | Risiko- und Stop-basierte Berechnung | Vorhanden; echte Tick-/Punktwerte muessen korrekt gepflegt sein. |
| CRV | Mindestqualitaet 1:1 | Vorhanden. |
| 5 Pre-Checks | TradingFreaks Pflichtpruefung | Vorhanden. |
| Screenshot vorher/nachher | Review-Beweis | Vorhanden fuer manuelle Bilder; automatische TradingView-Mac-App-Erfassung ist noch offen. |
| Ergebnis in R | Vergleichbare Trade-Auswertung | Vorhanden, wenn Risiko/Ergebnisdaten vollstaendig sind. |
| Slippage | Abweichung zwischen Plan und Ausfuehrung | Sinnvoll und vorhanden als Review-Feld. |
| Trade abschliessen | Draft als geschlossen und reviewpflichtig markieren | Funktion lokal vorhanden; End-to-End nur ohne Live-Bridge manuell. |
| TradingView/Broker Event | Orderfakten importieren | Schema vorhanden; echte Orderquelle fehlt. |
| Update-Kandidaten | Kandidaten aus heutigen Updates ableiten | Korrekt blockiert, wenn Updates nicht tagesaktuell sind. |
| Review-Warteschlange | Nur aktive Nacharbeit anzeigen | Sichtbar; aktuell 2 offene Reviews. |

## Harte Go-Live-Blocker

Diese Punkte muessen geloest sein, bevor das Tool als echtes Tages-Trading-System belastbar ist:

1. Echte Live-Adapter fuer die drei offenen Pflichtquellen konfigurieren:
   - `LIVE_PRICE_JSON_PATH` oder `TRADINGVIEW_BRIDGE_URL`
   - `LIVE_ORDER_JSON_PATH` oder `BROKER_EVENT_STREAM_URL`
   - `LIVE_CALENDAR_JSON_PATH` oder `ECONOMIC_CALENDAR_API_URL`
2. Eine oeffentlich erreichbare HTTPS-Bridge aktivieren:
   - bevorzugt: Cloudflare Worker Bridge ueber `workers.dev` - Status: erledigt
   - alternativ: KAS-SSL fuer `wertbegleiter.eu` aktivieren
   - alternativ: Cloudflare Named Tunnel mit aktiver DNS-/Nameserver-Route
3. TradingView Alerts im TradingView UI mit den registrierten Public-Webhook-URLs anlegen:
   - `TRADINGVIEW_WEBHOOK_PUBLIC_PRICE_URL`
   - `TRADINGVIEW_WEBHOOK_PUBLIC_TRADE_URL`
4. TradingView/Broker-Orderquelle live testen, damit offene und geschlossene Trades automatisch in Journal/Review laufen.
5. Wirtschaftskalender anbinden, damit CPI, NFP, Zinsentscheidungen und Hochrisiko-Events nicht manuell uebersehen werden.
6. Optional schnelleren News-/Squawk-/X-Pro-Feed setzen, falls der ForexLive/InvestingLive RSS-Fallback fuer Sekundenhandel nicht ausreicht.
7. Taegliche ChatGPT-Projektupdates exportieren oder durch einen echten Feed ersetzen. Der Pflicht-Chat-Stand 24.06.2026 ist fuer 01.07.2026 nur historischer Kontext.
8. Persistenz klaeren: Browser-LocalStorage reicht fuer Test/Paper nicht als langfristiges Echtgeld-Journal. Status: lokale JSON-Dateispeicherung mit Backup ist vorhanden; DB/Cloud-Backup bleibt optionaler Ausbau.
9. Sandbox-Testmodus ergaenzen, damit Buttons wie Reset, Start, Abschluss, Export und Bild-Upload automatisiert getestet werden koennen, ohne echte Journal-Daten zu veraendern.

Status 01.07.2026: Der Sandbox-Testmodus ist eingebaut. Das lokale `cloudflared`-Binary ist vorhanden, das TradingView-Gateway ist als schmale Schutzschicht umgesetzt und `tools/check_tradingview_webhook_setup.py` meldet formal `ready_for_tradingview`. Der externe `--check-public-health` ist mit der Cloudflare Worker Bridge `ready`; der alte KAS-Pfad bleibt wegen Zertifikats-Mismatch nur historischer Fallback. Vollautomatische Button-End-to-End-Tests fuer Reset, Abschluss, Upload und Export bleiben als naechster Testausbau offen.

## Sinnvolle Erweiterungen

Prioritaet A - direkt fuer Echtgeldstart:

- Live-Quellen-Onboarding im Portal: zeigt `.env`-Status, fehlende Adapter, Beispielpfade und Startbefehle direkt als gefuehrten Prozess.
- Broker-Reconciliation: Orderverlauf gegen Journal abgleichen; offene Trades, fehlende SL/TP, fehlende Reviews und Abweichungen markieren.
- Echtgeld/Paper-Trennung mit Ein-Klick-Bereinigung: Paper/Test archivieren, Echtjournal sauber starten, Archiv bleibt auswertbar.
- Go-Live Statuspanel: umgesetzt; zeigt Live-Quellen, Update-Alter, Echtjournal-Blocker und Testmodus direkt auf der Startseite.
- Journal-Bereinigung: umgesetzt; Backup und verlustfreie Archivierung lokaler Live-Drafts als Paper/Test sind vorhanden.
- Journal-Persistenz: lokale JSON-Datei mit Backup ist umgesetzt; lokale Datenbank oder Cloud-Backup bleiben als Ausbauoption.
- Testmodus fuer UI-Workflows: Grundmodus umgesetzt; vollautomatische Tests fuer Start, Speichern, Abschluss, R-Berechnung, Bilder, Review und Export noch ausbauen.

Prioritaet B - besserer Entscheidungsdesk:

- Benchmarkbereich: SPY/QQQ/DAX/VIX, US10Y, USD, Oel/Gold, Sektorstaerke und Marktphase als Kontext. Das ersetzt keine Live-News, hilft aber beim Management-Blick.
- Live-&-News Detailpfad prominenter machen: Cockpit -> Quelle -> Detail -> Kandidat -> Setup-Pruefung.
- Session-Plan: Europa, US Pre-Market, US Open, Power Hour mit Uhrzeiten und Blockern.
- Watchlist-Scoring: nur regelbasierte Kandidaten, keine Empfehlung.
- Tagesabschluss-Assistent: alle Trades geschlossen, Bilder komplett, R berechnet, Regelcheck, Review.

Prioritaet C - Komfort und Automatisierung:

- TradingView-Mac-App Screenshot-Workflow: manuelle Freigabe, dann Chartbild dem aktiven Trade zuordnen.
- Optionaler Read-only Order-Import aus TradingView/GBE-Exporten.
- PDF-/Brokerreport-Importer als fester Prozess.
- Wochenreview-Dashboard mit Setup-, Uhrzeit-, Symbol-, Emotion- und Regelverstoss-Auswertung.

## Aktueller Betriebsmodus

Das Portal darf aktuell als lokales Entscheidungs- und Journal-Tool verwendet werden:

- Setup manuell pruefen.
- Keine Trades ohne Stop Loss.
- Kein Trade unter CRV 1:1.
- Risiko default 1 Prozent.
- Alle Pflichtkriterien muessen erfuellt sein.
- Unklare oder alte Daten fuehren zu `Nur beobachten` oder `Nicht handeln`.

Das Portal darf aktuell nicht als sekundengenaues Live-Trading-Command-Center betrachtet werden, weil Kurse, Orders, Kalender und News noch nicht live verbunden sind.

## Verwendete Testbefehle

```bash
npm run lint
npm run build
python3 -m pytest
PYTHONPYCACHEPREFIX=/private/tmp/codex_pycache python3 -m compileall src tests tools
npm --prefix deploy/cloudflare_worker_bridge run check
curl -sI http://127.0.0.1:5173/
lsof -nP -iTCP:5173 -sTCP:LISTEN
lsof -nP -iTCP:8000 -sTCP:LISTEN
```

## Naechste empfohlene Umsetzung

1. Live-Quellen-Onboarding im UI prominenter machen.
2. Echtgeld/Paper-Bereinigung fuer Journal einbauen.
3. Persistente Journal-Speicherung ausserhalb von LocalStorage einbauen.
4. Sandbox-Testmodus fuer alle Buttons und Upload-Flows bauen.
5. Benchmarkbereich in Live & News / Heute ergaenzen.
6. TradingView Alerts im TradingView UI auf die Worker-URLs umstellen und mit Preis-/Trade-Events testen.
7. Danach TradingView/Broker-Order-Bridge read-only anbinden.
