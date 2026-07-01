# Cloudflare Worker Bridge

Die Worker Bridge ist die bevorzugte feste HTTPS-Inbox, wenn ALL-INKL/KAS kein
passendes SSL-Zertifikat liefert oder die Nameserver nicht umgestellt werden
sollen. Sie laeuft auf `workers.dev`, speichert nur TradingView-Fakten und fuehrt
keine Orders aus.

## Funktion

- `POST /tv/<token>/price` nimmt TradingView-Preis-/Heartbeat-Payloads an.
- `POST /tv/<token>/trade` nimmt Trade-Events wie `opened`,
  `closed_stop_loss`, `closed_take_profit` oder `closed_manual` an.
- `GET /tv/<token>/events?since=0&limit=100` liefert gespeicherte Events fuer
  den lokalen Puller.
- `GET /health` prueft nur die Erreichbarkeit.

Alle Events bleiben Information und Journal-Unterstuetzung. Es gibt keine
Anlageberatung, keine Kauf-/Verkaufsempfehlung und keine Orderausfuehrung.

## Cloudflare einrichten

1. Im Ordner `deploy/cloudflare_worker_bridge` die Beispieldatei kopieren:

```bash
cp wrangler.toml.example wrangler.toml
```

2. Bei Cloudflare anmelden und eine KV-Namespace anlegen:

```bash
npx wrangler login
npx wrangler kv namespace create wertbegleiter_trading_events --config deploy/cloudflare_worker_bridge/wrangler.toml
```

3. Die ausgegebene KV-`id` in `deploy/cloudflare_worker_bridge/wrangler.toml`
   bei `id = "..."` eintragen.

4. Den bestehenden lokalen TradingView-Token als Worker-Secret setzen:

```bash
npx wrangler secret put TRADINGVIEW_WEBHOOK_TOKEN --config deploy/cloudflare_worker_bridge/wrangler.toml
```

5. Worker deployen:

```bash
npx wrangler deploy --config deploy/cloudflare_worker_bridge/wrangler.toml
```

Wrangler zeigt danach eine URL wie
`https://wertbegleiter-trading-bridge.<dein-name>.workers.dev`.

Aktueller Projektstand vom 01.07.2026:

```text
https://wertbegleiter-trading-bridge.wertbegleiter.workers.dev
```

Der Public-Healthcheck liefert `status=ok`. Ein Smoke-Test-Preis-Heartbeat
wurde gespeichert und per lokalem Puller verarbeitet.

## Lokale Konfiguration

Die TradingView-Webhook-URLs werden mit der Worker-Basis-URL in `.env`
geschrieben:

```bash
python3 tools/register_tradingview_public_webhooks.py \
  --base-url https://wertbegleiter-trading-bridge.wertbegleiter.workers.dev \
  --worker-bridge
```

Danach holt der lokale Puller gespeicherte Worker-Events ab:

```bash
python3 tools/pull_cloudflare_worker_bridge.py --interval-seconds 3
```

Der Puller schreibt Preis-/Order-Heartbeats in den Live-Status und uebernimmt
Trade-Open/-Close-Events in `reports/journal_live_store.json`.

## TradingView

In TradingView werden nur diese beiden URLs genutzt:

```text
https://wertbegleiter-trading-bridge.wertbegleiter.workers.dev/tv/<token>/price
https://wertbegleiter-trading-bridge.wertbegleiter.workers.dev/tv/<token>/trade
```

Die Alert-Payloads liegen unter
`reports/live_sources/tradingview_webhooks/`.

## Betriebsgrenze

Diese Worker-Bridge ist fuer Alert- und Trade-Fakten gedacht, nicht fuer
hochfrequente Tickdaten. Fuer Sekundenstatus reichen sparsame Heartbeats. Eine
Broker-/TradingView-API mit WebSocket waere die naechste Stufe, wenn echte
Realtime-Kursstreams benoetigt werden.
