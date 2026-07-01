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

Aktueller Stand:

- Lokales Repository: vorhanden
- Branch: `main`
- Initiale Commits: vorhanden
- Remote `origin`: noch nicht gesetzt
- `gh` CLI: auf diesem Mac aktuell nicht installiert

Wenn bereits ein GitHub-Repository existiert, reicht die HTTPS- oder SSH-URL,
z. B.:

```bash
git remote add origin git@github.com:<owner>/<repo>.git
git push -u origin main
```

Wenn noch kein Repository existiert, zuerst in GitHub ein privates Repository
anlegen, z. B. `wertbegleiter-kapitalmarkt`, und danach die Remote-URL setzen.

Vor einem Push muss geprueft werden, dass `.env`, Brokerdaten, Reports,
Screenshots und lokale TradingView-Tunnel-Token nicht im Commit enthalten sind.

## Sicherheitsregel

Git dokumentiert nur den Werkzeugbau. Es ist keine Trading-Freigabe, keine
Anlageberatung und kein Broker-Automatismus.
