# Importierte Regeln aus dem ChatGPT-Projekt Trading

Quelle: `docs/imported_chatgpt_project/trading_project_chats_raw.json`

Importierte Chats:

1. `Trading Update Daily Update?`
2. `Breaking news update: oil, yen, tech insights Update?`
3. `Taegliches Marktupdate und Trading-Setups Update?`
4. `US open update and trade scenarios`
5. `Europe session update and trade scenarios`

## Kernstruktur Daily Update

Jedes Daily Update folgt einer wiederkehrenden Struktur:

1. Stimmung / Marktregime
2. Termine / News-Filter
3. Zeitfenster-Plan
4. bedingte Trade-Ideen, ausdruecklich keine Signale
5. Fazit mit Pflichtbestaetigungen und Blockern

Alle Breaking-News-Meldungen sollen mit Datum und Uhrzeit beginnen, z. B. `24.06.2026, 15:27 Uhr Europe/Berlin`.

## Session-Playbook

`08:00-10:00 Daily Market Update`

- Wochenausblick, Wirtschaftskalender und Top-Events pruefen.
- Risk-On/Risk-Off, USD, US-Renditen, Oel, Gold/Silber, Tech/AI und JPY einordnen.
- No-Trade-Zonen fuer Top-Events markieren.

`10:00-12:00 Europe Session / ORB`

- DE40 ist haeufig Primaermarkt.
- EURUSD, USDJPY, Gold/Silber und Oel dienen als Kontext- und Korrelationsfilter.
- Kein Einstieg in den ersten Spike.
- Bevorzugt: ORB Break + Retest, Failed Breakout, Reversal an sauberem Level.

`15:25 US Open Update`

- US-Futures, US500/USTEC, Tech/AI, Semis, NVDA und aktuelle Earnings-/Newsrisiken pruefen.
- Keine aggressive Vorpositionierung in den Open.

`15:30-15:35 US Open`

- Erste 5-Minuten-Kerze nur beobachten.
- Keine FOMO-Entries.

`16:30-18:00 US Momentum Window`

- Bestes Momentumfenster fuer US-ORB und Post-Event-Setups.
- 5-15 Minuten nach Open/Event/Repricing warten.
- Pullback oder Break-and-Retest bevorzugen.
- Oel und Bond-Yields als Pflichtfilter nutzen.

## Asset-Fokus

Feste Fokusmaerkte aus den Chats:

- Indizes: `DE40`, `US500`, `USTEC`
- FX: `EURUSD`, `USDJPY`, teilweise `GBPUSD`, `EURGBP`
- Metalle: `XAUUSD`, `XAUEUR`, `XAGUSD`
- Oel: `UKOIL`, Brent/WTI-Kontext
- Tech/AI-Watchlist: `NVDA`, `MSFT`, `AAPL`, `GOOG`, `AMZN`, `TSLA`

## XAGUSD / Silber

XAGUSD soll immer in Daily Updates beruecksichtigt werden:

- zusammen mit Gold/XAUUSD/XAUEUR
- mit USD- und Rendite-Sensitivitaet
- mit Gold/Silber-Ratio als Zusatzfilter
- mit Industrie-/China-/Konjunkturbezug
- mit Risk-On/Risk-Off-Kontext
- ohne doppelte Metall-Exposure durch parallele Gold- und Silberideen

## News- und Eventfilter

Harte Regeln:

- Keine Positionierung vor Top-Terminen.
- Nach Event zuerst Zahlen, Erwartungsabweichung, Einheitlichkeit und M1/M5-Momentum pruefen.
- Nicht in erste News-, Event- oder Open-Kerze springen.
- 5-15 Minuten nach Event/Open/Repricing warten.
- Nur Struktur handeln: Pullback, Retest, Failed Breakout, klare Fortsetzung.
- Kein Trade bei unklaren Daten, gemischten Signalen oder fehlendem Momentum.

## Breaking-News-Playbook

Breaking-News-Updates sollen enthalten:

- Datum und Uhrzeit zu Beginn.
- Ereignis.
- Betroffene Maerkte.
- Moegliche Richtung nur als bedingte These.
- Relevantes Zeitfenster.
- Playbook-Bewertung.
- Pflichtfilter.
- Blocker / No-Trade-Hinweise.

Spezielle Themen:

- JPY/USDJPY im Interventionsbereich nicht blind long handeln.
- Oel/Hormuz/Geopolitik kann Risk-On/Risk-Off sofort drehen.
- Tech/AI und Micron-/Semi-Earnings sind Filter fuer USTEC/NVDA/Semis.
- USD und US-Renditen sind Pflichtfilter fuer Gold, Silber, EURUSD, USDJPY und Tech.

## Risiko- und Prozessregeln

- 2-5 Trades sind ein Qualitaetskorridor, kein Tagesziel.
- Maximal ein Haupttrade je Session bei hoher Korrelation oder Headline-Risiko.
- Bei Geopolitik/Headline-Spikes Risiko reduzieren, z. B. auf `<= 0,8 %`.
- Mindest-CRV bleibt `>= 1:1`.
- Hochwertige ORB-/Event-Szenarien sollen eher `>= 1:2` anstreben.
- Kein Chase, kein Revenge-Trading, keine erste Kerze.
- Kein Trade ohne Stop Loss und Exit-Plan.
- Kein Trade ist ein valider Trade.

## Produktimplikationen

Im Tool muessen diese Regeln sichtbar werden:

- Morning/Daily Update als Startscreen.
- Europe Session und US Open als getrennte Boards.
- News Deck mit Oel, JPY, Tech/AI, Kalender und Metallen.
- XAGUSD fester Bestandteil des Metallblocks.
- Sessionbezogene Blocker: Top-Event, erste Open-Kerze, fehlender Retest, fehlende Korrelation.
- Journal muss Quelle, Uhrzeit, News-/Event-Kontext, Setup, Kriterien, Emotionen und Regelkonformitaet erfassen.

Alle importierten Regeln bleiben Entscheidungsunterstuetzung. Sie sind keine Anlageberatung, keine Kauf-/Verkaufsempfehlung und keine Orderfreigabe.
