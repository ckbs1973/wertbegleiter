# Dauerhafter TradingView-Webhook-Tunnel

Stand: 2026-07-01

Der Quick-Tunnel von `trycloudflare.com` ist nur fuer Tests geeignet. Fuer
Daily Use braucht das Portal eine feste HTTPS-Adresse, damit TradingView Alerts
nicht jeden Tag neu konfiguriert werden muessen.

Dieses Portal bleibt ein Entscheidungs- und Journal-System. Der Tunnel nimmt
nur Marktdaten- und Trade-Event-Fakten entgegen. Es gibt keine Anlageberatung,
keine Orderfreigabe und keine Broker-Orderausfuehrung.

## Zielarchitektur

```text
TradingView Alert
  -> https://trading-webhooks.wertbegleiter.eu/tv/<token>/price
  -> Cloudflare Named Tunnel
  -> http://127.0.0.1:8787
  -> TradingView Webhook Gateway
  -> lokale API /api/live-bridge/ingest
```

Trade-Events laufen analog ueber:

```text
https://trading-webhooks.wertbegleiter.eu/tv/<token>/trade
```

## Aktueller Stand

- Cloudflare-Zone: `wertbegleiter.eu`
- Plan: Free
- Named Tunnel: `wertbegleiter-trading`
- Tunnel-ID: `6daabb6d-4a86-4906-8d84-9da4e4d51020`
- Tunnel-Config im Projekt: `config/cloudflare/wertbegleiter-trading.yml`
- Public Webhook Base URL: `https://trading-webhooks.wertbegleiter.eu`
- Public Webhook URLs sind in `.env` token-geschuetzt registriert.

Offen bleibt die Domain-Aktivierung beim Registrar/DNS-Anbieter. Aktuell sind
im Internet noch die alten Nameserver aktiv:

```text
ns5.kasserver.com
ns6.kasserver.com
```

Cloudflare erwartet stattdessen:

```text
cortney.ns.cloudflare.com
glen.ns.cloudflare.com
```

Solange diese Umstellung nicht erfolgt ist, ist die Cloudflare-Zone intern
vorbereitet, aber die oeffentliche Subdomain kann noch auf den alten Anbieter
zeigen oder ein falsches Zertifikat liefern.

## Einmalige Einrichtung

Voraussetzung: Im Cloudflare Account muss mindestens eine Website/Domain als
Zone vorhanden sein. Wenn die Seite `Authorize Cloudflare Tunnel` keine Zone
auflistet, muss zuerst eine Domain mit `Connect your website or app` verbunden
werden. Ohne Zone kann `cloudflared tunnel login` nicht abgeschlossen werden.

1. Cloudflare Login fuer Named Tunnels:

```bash
tools/bin/cloudflared tunnel login
```

2. Named Tunnel erstellen:

```bash
tools/bin/cloudflared tunnel create wertbegleiter-trading
```

3. DNS-Route auf eine eigene Subdomain setzen:

```bash
tools/bin/cloudflared tunnel route dns wertbegleiter-trading trading-webhooks.wertbegleiter.eu
```

4. Lokale Config anlegen, z. B. `config/cloudflare/wertbegleiter-trading.yml`:

```yaml
tunnel: <tunnel-id>
credentials-file: /Users/<user>/.cloudflared/<tunnel-id>.json

ingress:
  - hostname: trading-webhooks.wertbegleiter.eu
    service: http://127.0.0.1:8787
  - service: http_status:404
```

5. Named Tunnel starten:

```bash
tools/bin/cloudflared tunnel --config config/cloudflare/wertbegleiter-trading.yml run wertbegleiter-trading
```

6. Public Base URL registrieren:

```bash
python3 tools/register_tradingview_public_webhooks.py --base-url https://trading-webhooks.wertbegleiter.eu
```

7. TradingView Alerts mit den URLs aus `.env` anlegen.

## Laufender Tagesstart

```bash
PYTHONPATH=src python3 -m trading_freaks.api.server
python3 tools/run_tradingview_webhook_gateway.py
tools/bin/cloudflared tunnel --config config/cloudflare/wertbegleiter-trading.yml run wertbegleiter-trading
python3 tools/run_configured_live_adapters.py --interval-seconds 5
python3 tools/run_realtime_update_service.py --interval-seconds 5 --force-rebuild-every-seconds 60
```

## Readiness pruefen

```bash
python3 tools/check_infrastructure_readiness.py --check-public-health
python3 tools/check_tradingview_webhook_setup.py
```

Erwartung:

- `tradingview_webhooks.status = ready_for_tradingview`
- `cloudflare.status = authenticated`
- `git.remote_ready = true`
- `LIVE_TRADING_ENABLED=false`

Wenn `--check-public-health` nicht `ok` liefert, ist die oeffentliche Adresse
noch nicht produktiv erreichbar. Bei `wertbegleiter.eu` ist der erwartete
naechste Schritt die Nameserver-Umstellung beim Domain-Anbieter von
`ns5.kasserver.com`/`ns6.kasserver.com` auf die beiden Cloudflare-Nameserver.

## Offene harte Grenze

Auch mit dauerhaftem Tunnel ist das System erst dann wirklich
sekundenaktuell, wenn TradingView Alerts echte Kurs-/Orderdaten senden und der
Wirtschaftskalender live angebunden ist.

## Alternativen ohne eigene Cloudflare-Domain

- Weiterhin temporaerer Quick-Tunnel fuer Tests, aber keine stabile URL fuer
  TradingView.
- ALL-INKL/KAS Webhook Bridge ueber `deploy/kas_webhook_bridge`, wenn die
  Domain bei KAS bleiben soll und keine Nameserver-Umstellung gewuenscht ist.
  Setup: `docs/kas_webhook_bridge_setup.md`.
- Bezahlter/registrierter Tunnel-Anbieter mit reservierter Domain, z. B. ngrok
  Reserved Domain.
- Eigener kleiner HTTPS-Bridge-Server, der nur `/tv/<token>/price` und
  `/tv/<token>/trade` an die lokale Instanz oder eine gehostete API weiterleitet.
