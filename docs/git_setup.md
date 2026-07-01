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
- Remote `origin`: `https://github.com/ckbs1973/wertbegleiter.git`
- Upstream/Push: noch nicht abgeschlossen, weil das lokale Terminal noch keine GitHub-Credentials hat
- `gh` CLI: auf diesem Mac aktuell nicht installiert

Das GitHub-Repository existiert und ist erreichbar:

```text
https://github.com/ckbs1973/wertbegleiter
```

Push per HTTPS braucht auf diesem Mac noch eine GitHub-Authentifizierung, z. B.
ueber GitHub Desktop, Git Credential Manager, `gh auth login` oder einen
Personal Access Token im lokalen Credential Store. Der Token gehoert nicht in
`.env`, nicht in Git und nicht in diese Doku.

Alternativ kann ein SSH-Key erstellt und bei GitHub hinterlegt werden. Danach:

```bash
git remote set-url origin git@github.com:ckbs1973/wertbegleiter.git
git push -u origin main
```

Wenn HTTPS genutzt wird, bleibt:

```bash
git push -u origin main
```

Vor einem Push muss geprueft werden, dass `.env`, Brokerdaten, Reports,
Screenshots und lokale TradingView-Tunnel-Token nicht im Commit enthalten sind.

## Sicherheitsregel

Git dokumentiert nur den Werkzeugbau. Es ist keine Trading-Freigabe, keine
Anlageberatung und kein Broker-Automatismus.
