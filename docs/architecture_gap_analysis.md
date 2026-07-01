# Bestandsaufnahme und Implementierungsplan

## 1. Bestandsaufnahme

Das Arbeitsverzeichnis war beim Start leer:

- Keine vorhandene Codebasis.
- Kein Git-Repository.
- Keine Tests.
- Keine README oder Konfiguration.
- Verfuegbare lokale Python-Version: Python 3.9.6.

Technologieannahme fuer den ersten Schritt:

- Python-Paket unter `src/trading_freaks`.
- Keine externen Abhaengigkeiten im Python-Kern.
- React/Vite-Frontend unter `frontend`; Dependency-Installation ist separat.
- Unit-Tests mit `unittest`.
- Fokus auf sichere Entscheidungsunterstuetzung statt Broker-Automation.

Ergaenzter Chat-Kontext:

- Chat 1: Trading-App mit Setup-Checklisten, Fokus US-Aktien-Newstrade-Breakout, React Frontend und Python Backend.
- Chat 2: Journal mit Emotionen, Regelverstoessen und Screenshots.
- Chat 3: Backtesting ohne Lookahead-Bias, Spread und Slippage.
- ChatGPT-Projektchats: Daily Update, Breaking News zu Oel/Yen/Tech, taegliches Marktupdate, US Open Szenarien und Europe Session Szenarien wurden importiert und in `src/trading_freaks/session_playbook.py` als testbare Prozessregeln modelliert.

## 2. Fehlende Module gegenueber Zielsystem

Noch nicht vorhanden oder nur als Struktur vorbereitet:

- Datenloader fuer OHLCV, News und Wirtschaftskalender.
- Indikatoren: EMA, SMA, VWAP, ATR, Fibonacci, RVOL.
- Erweiterte Risiko-Engine: Margin-Modelle, Korrelation, Tages-/Wochenverlustlimits, Verlustserien-State.
- Setup-Module sind als Checklisten fuer die wichtigsten genannten Setups vorhanden; es fehlen noch datengetriebene Erkennung, SR-Reversal und feinere Varianten je Trading-Stil.
- Fundamentales FX-Sentiment-Modul.
- Psychologie- und Disziplinmodul mit Tageswerten.
- Journal-Persistenz auf Datei-/Datenbankebene; Export und Review-Kennzahlen sind als Kernfunktionen vorhanden.
- Backtesting-Engine ist als sicherer Grundkern vorhanden; es fehlen Datenloader, Kalender-/News-Zeitstempel, Spread-Zeitreihen, Kommissionstabellen und Setup-spezifische historische Signalbildung.
- API/UI sind als erster US-Newstrade-Breakout-Flow vorhanden; Watchlist, Persistenz und tiefe Journal-Views fehlen noch.
- Datenvalidierung fuer Screenshots und Handelszeiten.
- Dokumentierte Beispielkonfigurationen je Setup.

## 3. Priorisierter Implementierungsplan

1. Kernmodelle und sichere Validierungsobjekte definieren.
2. Risiko- und Positionsgroessenlogik so kapseln, dass Stop Loss, CRV und Exit-Plan nicht umgangen werden.
3. Erste Setup-Checkliste als Referenzmodul implementieren.
4. Journal-Modell und erste Wochenreview-Metriken ergaenzen.
5. Indikatoren als reine, testbare Funktionen implementieren.
6. Weitere Setup-Module einzeln nachziehen und gegen Fixtures testen.
7. Backtesting-Grundgeruest mit Entscheidungslogs und Lookahead-Schutz bauen.
8. Persistenz fuer Journal, Backtests und Reports hinzufuegen.
9. UI/API erst aufsetzen, wenn Kernlogik stabil ist.
10. TradingView/Pine-Script-Export oder Alert-Helfer nur als Analyse- und Checklistenunterstuetzung, ohne Live-Order-Automation.

## 4. Erster implementierter Schritt

Der erste Schritt liefert:

- `Candle`, `Trade`, `SetupSignal`, `SetupValidationResult`, `RiskPlan`, `JournalEntry`, `NewsEvent`, `EconomicEvent`, `SentimentSnapshot`.
- `calculate_risk_plan` fuer Standard-Risikoplanung.
- `USNewsBreakoutInput` und `evaluate_us_news_breakout` als Beispiel-Setup-Checkliste.
- Unit-Tests fuer valide und blockierte Szenarien.

## 5. Zweiter implementierter Schritt

- Setup-Checklisten fuer:
  - Wirtschaftsdaten-FX
  - US-News-Reversal
  - Reversal ohne News
  - Rectangle
  - Vorboersliches Hoch/Tief
  - FX-Trendlinien
  - DAX-Abpraller
- Journal-Review-Engine mit Performance- und Prozesskennzahlen.
- JSON-/CSV-Export fuer JournalEntries.
- Backtesting-Kern mit history-only Strategieaufruf, Spread, Slippage und konservativer Bracket-Simulation.
- Erweiterte Tests fuer neue Module.

## 6. Dritter implementierter Schritt

- Python-Backend-Route fuer US-Aktien-Newstrade-Breakout.
- Python-Backend-Route fuer Journal-Capture-Validierung.
- React/Vite-Frontend fuer den Hauptflow aus Chat 1.
- Journal-Validierung fuer Emotionen, Regelverstoesse und Screenshots aus Chat 2.
- Backtesting-Kostenmodell mit Spread und Slippage aus Chat 3.

## 7. Sicherheitsentscheidung

`trade_allowed=True` ist technisch als "Regelcheck bestanden" modelliert. Es ist keine Kauf-/Verkaufsempfehlung und keine Orderfreigabe. Live-Trading ist nicht implementiert.

## 8. Importierte Session-Regeln aus ChatGPT Trading

- ORB-Playbook: Europe `10:00-12:00`, US Momentum `16:30-18:00`.
- US Open: keine erste 5-Minuten-Kerze handeln.
- News/Event: 5-15 Minuten nach Event/Open/Repricing warten; keine Positionierung vor Top-Terminen.
- Fokusfilter: Oel/Hormuz, USD/Yields, JPY-Interventionsrisiko, Tech/AI/Semis, DE40, EURUSD, USDJPY, XAU/XAG.
- XAGUSD ist fester Bestandteil des Metallblocks und wird nicht isoliert von Gold, USD/Yields, Gold/Silber-Ratio und China-/Industriekontext bewertet.
- Breaking-News-Updates muessen Datum/Uhrzeit am Anfang fuehren und duerfen nur bedingte Szenarien liefern.
