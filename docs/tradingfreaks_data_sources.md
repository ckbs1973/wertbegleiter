# TradingFreaks Datenquellen

Diese Datei dokumentiert die Datenquellen, die im Morning Setup Brief genutzt werden sollen. Die Quellen stammen aus den lokalen TradingFreaks-Schulungsunterlagen und wurden mit aktuellen offiziellen URLs ergaenzt.

## Quellen

| Bereich | Quelle | Zweck | TF-Bezug |
|---|---|---|---|
| Watchlist/Charts | TradingView / Broker Watchlist | Basisuniversum, Charts, Levels, VWAP, Intraday-Kontext | `4.6-Newstrade-Breakout.pdf` |
| Wirtschaftskalender | Investing.com Economic Calendar | CPI, Arbeitsmarkt, Zinsentscheide, Zentralbanktermine, Risikoevents | `3.2-FX-Newsquellen.pdf`, `Wirtschaftsdaten-Setup.pdf` |
| FX/Makro-News | ForexLive | Ad-hoc FX-News, Notenbank-Kommentare, Sentiment | `3.2-FX-Newsquellen.pdf` |
| Squawk/Headlines | Newsquawk | schnelle Headlines, Kalender, Marktaudio, Makro-/Aktien-Kontext | `3.2-FX-Newsquellen.pdf` |
| Social News | X Pro, ehemals TweetDeck | Listen/Streams fuer schnelle Unternehmens- und Markt-Headlines | `4.4_die_marktrelevanten_nachrichten.pdf` |
| Aktien-News | Seeking Alpha Market News | Earnings, Guidance, Up-/Downgrades, Unternehmensmeldungen | `4.4_die_marktrelevanten_nachrichten.pdf` |

## News Deck / X Pro

TweetDeck heisst inzwischen X Pro. Das Tool bildet die Arbeitsweise intern als News Deck nach:

- Spalte `US Stock Catalysts`: X-Suche fuer Watchlist-Aktien plus Earnings, Guidance, Up-/Downgrades, Uebernahmen, Buybacks und Short Reports.
- Spalte `Stock News Confirmation`: Seeking Alpha Market News als zweite Quelle fuer Aktienmeldungen.
- Spalte `FX Macro Pulse`: X-/ForexLive-Kontext fuer CPI, NFP, Zentralbanken, PMIs und Zinskommentare.
- Spalte `Risk Event Calendar`: Investing.com Kalender fuer Event-Blocker.
- Spalte `Index Risk Tone`: DAX/Index-Kontext, Futures, Renditen und Risk-On/Risk-Off.

Das News Deck liest keine privaten X-Daten, speichert keine Zugangsdaten und erzeugt keine Handelssignale. Jede Headline ist nur ein Hinweis und muss durch Kursreaktion, VWAP/Level, Momentum, Volumen, Stop Loss, Take Profit und CRV-Pruefung bestaetigt werden.

## Morning-Brief-Regel

Um 08:00 Uhr darf das System aus diesen Quellen nur Screening-Kandidaten erzeugen. Eine Richtung ist eine These, keine Empfehlung:

- US-Aktien: Richtung erst nach News-/Gap- und Opening-Drive-Bestaetigung.
- FX: Richtung erst nach stark-gegen-schwach, Sentiment und Kalenderpruefung.
- DAX/Indizes: Richtung nur an vorbereiteten H4/D1/W1-Zonen und ohne nahes Risikoevent.
- Rohstoffe/Krypto-CFDs: zunaechst nur beobachten, bis Spread, Volatilitaet und Setup sauber klassifiziert sind.

Kein Output darf eine Orderfreigabe, Anlageberatung oder Gewinnversprechen enthalten.
