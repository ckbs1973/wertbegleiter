# Provider-Anschluesse

Stand: 2026-07-01

Dieses Portal bleibt ein Entscheidungs- und Journal-System. Es gibt keine
Anlageberatung, keine Kauf-/Verkaufsempfehlung und keine Orderausfuehrung.

## Aktuell verbunden

| Kategorie | Status | Quelle | Konfiguration |
|---|---|---|---|
| News | live | ForexLive/InvestingLive RSS | `LIVE_NEWS_FEED_URL=https://investinglive.com/feed/` |
| Kurse | blocked | lokaler Placeholder | `LIVE_PRICE_JSON_PATH=reports/live_sources/tradingview_price.json` |
| Orders | blocked | lokaler Placeholder | `LIVE_ORDER_JSON_PATH=reports/live_sources/tradingview_orders.json` |
| Kalender | blocked | lokaler Placeholder | `LIVE_CALENDAR_JSON_PATH=reports/live_sources/economic_calendar.json` |

Der Gesamtstatus bleibt deshalb `partly_live`, nicht `second_fresh`.

## Provider-Slots

| Pflichtquelle | Primaerer Slot | Provider-Fallbacks |
|---|---|---|
| Kurse | `LIVE_PRICE_JSON_PATH` | `TRADINGVIEW_BRIDGE_URL`, `KAS_WEBHOOK_BRIDGE_EVENTS_URL`, `CLOUDFLARE_WORKER_BRIDGE_EVENTS_URL` |
| Orders | `LIVE_ORDER_JSON_PATH` | `BROKER_EVENT_STREAM_URL`, `KAS_WEBHOOK_BRIDGE_EVENTS_URL`, `CLOUDFLARE_WORKER_BRIDGE_EVENTS_URL` |
| Kalender | `LIVE_CALENDAR_JSON_PATH` | `ECONOMIC_CALENDAR_API_URL` |
| News | `LIVE_NEWS_FEED_URL` | `NEWSQUAWK_API_URL`, `X_PRO_LIST_URL`, `FOREXLIVE_RSS_URL`, `SEEKING_ALPHA_NEWS_URL` |

## TradingView-Webhooks

TradingView-Webhooks senden Alert-Daten per HTTP POST an eine URL. Laut
TradingView werden nur Ports 80 und 443 akzeptiert; lokale URLs wie
`http://127.0.0.1:8000/...` sind deshalb nicht direkt geeignet.

Quelle: https://www.tradingview.com/support/solutions/43000529348-how-to-configure-webhook-alerts/

Praktischer Weg:

1. Lokalen API-Server starten.
2. Das schmale TradingView-Gateway starten. Es akzeptiert nur zwei
   token-geschuetzte POST-Routen und leitet intern an die lokale API weiter.
3. Einen HTTPS-Tunnel oder Reverse Proxy ausschliesslich auf
   `http://127.0.0.1:8787` zeigen lassen.
4. Public-URLs in `.env` setzen. Der Pfad muss auf
   `/tv/<token>/price` beziehungsweise `/tv/<token>/trade` zeigen:

```env
TRADINGVIEW_WEBHOOK_PUBLIC_PRICE_URL=https://dein-tunnel.example/tv/<token>/price
TRADINGVIEW_WEBHOOK_PUBLIC_TRADE_URL=https://dein-tunnel.example/tv/<token>/trade
```

5. TradingView Alert-Webhooks nur mit Marktdaten senden, keine Login-Daten und
   keine Secrets.

Wenn keine eigene Domain oder kein ALL-INKL-SSL genutzt werden soll, ist die
Cloudflare Worker Bridge der einfachste feste HTTPS-Weg:

```bash
python3 tools/register_tradingview_public_webhooks.py \
  --base-url https://wertbegleiter-trading-bridge.wertbegleiter.workers.dev \
  --worker-bridge
python3 tools/pull_cloudflare_worker_bridge.py --interval-seconds 3
```

Details: `docs/cloudflare_worker_bridge_setup.md`.

Lokale Ziele sind bereits angelegt:

```env
TRADINGVIEW_WEBHOOK_LOCAL_PRICE_URL=http://127.0.0.1:8000/api/live-bridge/ingest
TRADINGVIEW_WEBHOOK_LOCAL_TRADE_URL=http://127.0.0.1:8000/api/trade-events/capture
TRADINGVIEW_GATEWAY_HOST=127.0.0.1
TRADINGVIEW_GATEWAY_PORT=8787
TRADINGVIEW_WEBHOOK_TOKEN=<lokaler_geheimer_token>
```

Aktuelle Templates:

| Zweck | Datei | TradingView Webhook-Ziel |
|---|---|---|
| Kurs-/Heartbeat | `reports/live_sources/tradingview_webhooks/price_heartbeat_alert_message.json` | `TRADINGVIEW_WEBHOOK_PUBLIC_PRICE_URL` |
| Trade gestartet | `reports/live_sources/tradingview_webhooks/trade_opened_alert_message.json` | `TRADINGVIEW_WEBHOOK_PUBLIC_TRADE_URL` |
| Trade geschlossen | `reports/live_sources/tradingview_webhooks/trade_closed_manual_alert_message.json` | `TRADINGVIEW_WEBHOOK_PUBLIC_TRADE_URL` |

Setup pruefen:

```bash
python3 tools/check_tradingview_webhook_setup.py
```

Wenn ein Tunnel oder Reverse Proxy eine Public-Base-URL liefert, registrierst
Du beide TradingView-Ziele mit einem Befehl:

```bash
python3 tools/register_tradingview_public_webhooks.py --base-url https://dein-tunnel.example
```

Gateway lokal starten:

```bash
python3 tools/run_tradingview_webhook_gateway.py
```

Falls `cloudflared` lokal im Projekt liegt, kann der Tunnel auf das Gateway
zeigen:

```bash
tools/bin/cloudflared tunnel --url http://127.0.0.1:8787 --no-autoupdate
```

Solange `TRADINGVIEW_WEBHOOK_PUBLIC_PRICE_URL` und
`TRADINGVIEW_WEBHOOK_PUBLIC_TRADE_URL` leer sind, ist TradingView nur lokal
vorbereitet, aber noch nicht extern erreichbar.

Beispiel fuer Kurs-Heartbeat:

```json
{
  "bridge_type": "price",
  "source_name": "TradingView Webhook",
  "connection_state": "connected",
  "symbol": "BTCUSD",
  "last": 60447.98,
  "timestamp": "2026-07-01T13:30:00+00:00"
}
```

## Broker-/Orderstream

Orders duerfen nur als beobachtete Fakten ins Journal uebernommen werden. Die
Bridge fuehrt keine Order aus.

Beispiel fuer Trade-Start:

```json
{
  "bridge_type": "order",
  "source_name": "Broker Orderstream",
  "connection_state": "connected",
  "event_type": "opened",
  "trade_id": "broker-123",
  "symbol": "BTCUSD",
  "direction": "long",
  "entry": 60447.98,
  "stop_loss": 60359.08,
  "take_profit": 60549.56,
  "size": 0.3,
  "timestamp": "2026-07-01T13:30:00+00:00"
}
```

Beispiel fuer Trade-Ende:

```json
{
  "bridge_type": "order",
  "source_name": "Broker Orderstream",
  "connection_state": "connected",
  "event_type": "closed_stop_loss",
  "trade_id": "broker-123",
  "symbol": "BTCUSD",
  "exit_price": 60359.08,
  "timestamp": "2026-07-01T13:45:00+00:00"
}
```

## Wirtschaftskalender

Kalenderdaten muessen echte Zeitstempel enthalten. Ohne Kalender bleibt jedes
Setup mit News-/Event-Risiko konservativ blockiert.

Beispiel:

```json
{
  "bridge_type": "calendar",
  "source_name": "Economic Calendar API",
  "connection_state": "connected",
  "events": [
    {
      "title": "US CPI",
      "impact": "high",
      "currency": "USD",
      "scheduled_at": "2026-07-01T14:30:00+02:00"
    }
  ],
  "next_high_impact_event": "US CPI 14:30 Europe/Berlin"
}
```

## Smoke-Test

```bash
python3 tools/build_live_adapter_config_status.py
python3 tools/run_configured_live_adapters.py --once
```

Erwartung nach dem aktuellen Anschluss:

- Adapter: `4/4`
- Live-Status: `partly_live`
- News: `live`
- Kurse, Orders, Kalender: `blocked`, bis echte Quellen liefern
