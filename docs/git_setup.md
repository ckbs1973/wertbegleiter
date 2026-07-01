# Git-Setup

Stand: 2026-07-01

Dieses Projekt ist lokal als Git-Repository vorbereitet. Git dient hier der
Nachvollziehbarkeit von Code-, Doku- und Konfigurationsaenderungen. Es speichert
keine Secrets, keine Broker-Zugangsdaten und keine lokalen Live-Reports.

## Versioniert

- `src/`
- `tests/`
- `tools/`
- `frontend/src/`
- `frontend/package.json`
- `frontend/package-lock.json`
- `docs/`
- `.env.example`
- `.gitignore`
- `README.md`

## Nicht versioniert

- `.env`
- `reports/`
- `outputs/`
- `frontend/node_modules/`
- `frontend/dist/`
- `tools/bin/`
- Python-/Vite-/Test-Caches

## Remote-Anbindung

Ein lokales Git-Repository ist noch keine Cloud-Sicherung. Fuer GitHub oder
einen anderen Remote braucht es einmalig eine Remote-URL:

```bash
git remote add origin <repo-url>
git push -u origin main
```

Vor einem Push muss geprueft werden, dass `.env`, Brokerdaten, Reports,
Screenshots und lokale TradingView-Tunnel-Token nicht im Commit enthalten sind.

## Sicherheitsregel

Git dokumentiert nur den Werkzeugbau. Es ist keine Trading-Freigabe, keine
Anlageberatung und kein Broker-Automatismus.
