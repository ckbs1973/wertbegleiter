# ALL-INKL/KAS Webhook Bridge

Stand: 2026-07-01

Diese Bridge ist die Cloudflare-freie Variante fuer TradingView Webhooks. Sie
nimmt auf dem ALL-INKL/KAS-Webspace nur Fakten entgegen und speichert sie
zwischen. Das lokale Portal holt diese Fakten danach ab und aktualisiert
Live-Status und Journal. Es gibt keine Anlageberatung, keine Orderfreigabe und
keine Broker-Orderausfuehrung.

## Zielarchitektur

```text
TradingView Alert
  -> https://wertbegleiter.eu/wb-bridge/tv/<token>/price
  -> ALL-INKL/KAS PHP Bridge
  -> storage/events.ndjson
  -> lokaler Puller
  -> Live-Status und Journal-Store
```

Trade-Events laufen analog ueber:

```text
https://wertbegleiter.eu/wb-bridge/tv/<token>/trade
```

Der lokale Puller liest:

```text
https://wertbegleiter.eu/wb-bridge/tv/<token>/events
```

## Deployment auf KAS

Voraussetzung: Fuer den Bridge-Ordner PHP 7.4 oder neuer nutzen.

1. Ordner `deploy/kas_webhook_bridge` auf den Webspace kopieren, z. B. nach
   `/www/htdocs/.../wertbegleiter.eu/wb-bridge/`.
2. Auf dem Server `config.example.php` nach `config.php` kopieren.
3. In `config.php` den echten langen Token setzen. Der Token muss mit
   `TRADINGVIEW_WEBHOOK_TOKEN` in der lokalen `.env` uebereinstimmen.
4. Falls moeglich sicherstellen, dass `.htaccess` aktiv ist. Die Bridge liefert
   selbst eine `.htaccess`, die `config.php`, `storage/` und Directory Listings
   schuetzt.
5. Healthcheck im Browser testen:

```text
https://wertbegleiter.eu/wb-bridge/health
```

Erwartung: `{"status":"ok", ...}`.

## Lokale .env

```env
TRADINGVIEW_WEBHOOK_PUBLIC_PRICE_URL=https://wertbegleiter.eu/wb-bridge/tv/<token>/price
TRADINGVIEW_WEBHOOK_PUBLIC_TRADE_URL=https://wertbegleiter.eu/wb-bridge/tv/<token>/trade
KAS_WEBHOOK_BRIDGE_EVENTS_URL=https://wertbegleiter.eu/wb-bridge/tv/<token>/events
KAS_WEBHOOK_BRIDGE_CURSOR_PATH=reports/live_sources/kas_webhook_bridge_cursor.json
KAS_WEBHOOK_BRIDGE_POLL_INTERVAL_SECONDS=3
```

Den Token nicht in Git committen.

Die URLs koennen lokal auch automatisch gesetzt werden:

```bash
python3 tools/register_tradingview_public_webhooks.py \
  --base-url https://wertbegleiter.eu/wb-bridge \
  --kas-bridge
```

## Tagesstart lokal

```bash
PYTHONPATH=src python3 -m trading_freaks.api.server
python3 tools/pull_kas_webhook_bridge.py --interval-seconds 3
python3 tools/run_configured_live_adapters.py --interval-seconds 5
python3 tools/run_realtime_update_service.py --interval-seconds 5 --force-rebuild-every-seconds 60
```

Der Puller:

- schreibt Preis-Events in den Live-Status,
- schreibt Order-/Trade-Events in den Live-Status,
- legt `opened`-Events als offene Journal-Drafts an,
- schliesst `closed_stop_loss`, `closed_take_profit` und `closed_manual` ueber
  dieselbe `trade_id`,
- berechnet `realized_r`, wenn Entry und Stop Loss aus dem Open-Event bekannt
  sind,
- erhaelt Close-Events ohne passenden Open-Trade als `Review offen`, damit
  nichts unsichtbar verloren geht.

## Readiness pruefen

```bash
python3 tools/check_tradingview_webhook_setup.py
python3 tools/check_infrastructure_readiness.py --check-public-health
```

Stand 2026-07-01: Die Bridge-Dateien liegen auf dem KAS-Webspace unter
`/wertbegleiter.eu/wb-bridge/`. Der HTTP-Healthcheck liefert `status=ok`.
HTTPS liefert jedoch das ALL-INKL-Standardzertifikat `*.kasserver.com`, weil
der aktuelle Tarif im KAS unter `SSL-Schutz` die Meldung `Ressourcenlimit
erreicht` zeigt. Fuer TradingView-Daily-Use bleibt deshalb HTTPS ein harter
Blocker, bis entweder SSL bei ALL-INKL freigeschaltet wird oder die
Cloudflare-Nameserver/DNS-Route fuer den Named Tunnel aktiv sind.

Bei aktiver KAS Bridge ist Cloudflare nicht mehr Pflicht. Der Healthcheck nutzt
die oeffentliche Webhook-Domain. Wenn KAS erreichbar ist, aber noch keine
TradingView Alerts gesendet wurden, bleibt der Live-Status bewusst teilweise
oder nicht live.

## TradingView Alert Payloads

Die vorhandenen Templates liegen unter:

```text
reports/live_sources/tradingview_webhooks/
```

Wichtig: TradingView muss beim Open-Event Entry, Stop Loss, Richtung, Symbol,
Trade-ID und Size liefern, wenn das Journal den Trade automatisch als laufend
und spaeter mit R-Ergebnis fuehren soll. Fehlen Stop Loss oder Exit-Regel,
blockiert die Trade-Bewertung weiterhin regelkonform.

## Grenzen

- KAS ersetzt nur die feste HTTPS-Bruecke.
- Wirtschaftskalender, schnelle News/Squawk und Broker-spezifische Orderdetails
  brauchen weiterhin eigene Provider oder Exporte.
- Die Bridge liest keine Orders aktiv aus TradingView aus. Sie verarbeitet nur
  Alerts, die TradingView sendet.
