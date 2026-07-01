# ChatGPT-Projektkontext Trading

Diese Datei sammelt die aus dem ChatGPT-Projekt `Trading` uebernommenen Inhalte fuer Bewertung, Architekturentscheidungen und Produktlogik.

Direkter Zugriff war erst nach Benutzer-Login im In-App-Browser moeglich. Die sichtbaren Projekt-Chats wurden am 24.06.2026 lokal extrahiert.

Rohimport:

- `docs/imported_chatgpt_project/trading_project_chats_raw.json`
- `docs/imported_chatgpt_project/manifest.json`

Verdichtete Regeln:

- `docs/imported_chatgpt_project/trading_project_rules_summary.md`

## Importierte Projekt-Chats

Folgende Chats aus dem ChatGPT-Projekt `Trading` wurden ausgelesen:

1. `Trading Update Daily Update?`
2. `Breaking news update: oil, yen, tech insights Update?`
3. `Taegliches Marktupdate und Trading-Setups Update?`
4. `US open update and trade scenarios`
5. `Europe session update and trade scenarios`

Hinweis: Der Nutzer sprach von vier Chats, der Screenshot zeigte fuenf sichtbare Eintraege. Fuer die Bewertung werden alle fuenf sichtbaren Projekt-Chats beruecksichtigt.

## Bereits uebernommene Chat-Zusammenfassungen

### Chat 1

- Ziel: Trading-App mit Setup-Checklisten.
- Fokus: US-Aktien Newstrade Breakout.
- Vorgabe: React Frontend, Python Backend.

### Chat 2

- Ziel: Journal verbessern.
- Fokus: Emotionen, Regelverstoesse und Screenshots erfassen.

### Chat 3

- Ziel: Backtesting.
- Fokus: keine Lookahead-Bias, Spread und Slippage beruecksichtigen.

### Projektchats aus ChatGPT

- Daily Updates mit ORB-Playbook `10:00-12:00` und `16:30-18:00`.
- Breaking-News-Checks fuer Oel/Geopolitik, JPY/USDJPY, Tech/AI und Makro.
- Tägliches Marktupdate mit XAGUSD als dauerhaftem Bestandteil.
- US-Open-Szenarien mit erster 5-Minuten-Kerze als No-Trade-Zone.
- Europe-Session-Szenarien mit DE40, EURUSD, USDJPY, Gold/Silber und Oel-Kontext.

## Aus den sichtbaren Titeln ableitbare Produktimplikationen

Diese Punkte sind aus den importierten Chatinhalten validiert:

- Das System braucht ein taegliches Morning-/Daily-Update als ersten Arbeitsbildschirm.
- Breaking-News-Kontext soll explizit Oel, JPY/Yen und Tech-Aktien beruecksichtigen.
- Europa-Session und US-Open sollten als getrennte Update-Phasen modelliert werden.
- Trade-Szenarien sollen als bedingte Prueflogik formuliert werden, nicht als Orderempfehlung.
- Der Focus Desk sollte nach Session, Assetklasse und Setup trennen: Europe, US Open, News/Makro, Watchlist-Kandidaten, Journal.
- Jede Breaking-News-Meldung soll Datum und Uhrzeit zu Beginn nennen.
- XAGUSD/Silber ist dauerhaft im Metallblock zu beruecksichtigen.
- 5-15 Minuten Wartezeit nach Event/Open/Repricing und keine erste US-Open-Kerze handeln.
- Bei Headline-/Geopolitik-Risiko maximal ein Haupttrade je Session und reduziertes Risiko.

## Bewertungsregel

Alle Inhalte aus den Chats werden nur als Prozess-, Analyse- und Checklistenlogik genutzt. Das System bleibt ohne Anlageberatung, ohne Kauf-/Verkaufsempfehlung und ohne Live-Orderausfuehrung.
