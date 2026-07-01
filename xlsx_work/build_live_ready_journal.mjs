import fs from "node:fs/promises";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const outputDir = "../outputs/trading_journal_tf";
const outputPath = `${outputDir}/TradingFreaks_Live_Ready_Journal_Codex.xlsx`;
const backtestPath = "../reports/backtest_trade_history_2025-08_to_2026-05.json";
const monthlyTradesPath = "../reports/gbe_monthly_closed_trades.csv";
const orderHistoryPath = "../reports/trade_history_gbe_2026-05-20_reconstructed_trades.csv";

const liveRows = 1000;
const liveStart = 8;
const liveEnd = liveStart + liveRows - 1;
const importRows = 1600;
const importStart = 5;

const workbook = Workbook.create();
const cockpit = workbook.worksheets.add("Live_Cockpit");
const tradePlan = workbook.worksheets.add("Trade_Plan");
const liveJournal = workbook.worksheets.add("Live_Journal");
const riskSettings = workbook.worksheets.add("Risk_Settings");
const psychology = workbook.worksheets.add("Psychologie");
const weekly = workbook.worksheets.add("Wochenreview");
const monthly = workbook.worksheets.add("Monatsauswertung");
const insights = workbook.worksheets.add("Backtest_Insights");
const importReview = workbook.worksheets.add("Import_Review");
const setups = workbook.worksheets.add("Setup_Regeln");
const lists = workbook.worksheets.add("Listen");

function setValues(sheet, range, values) {
  sheet.getRange(range).values = values;
}

function setFormulas(sheet, range, formulas) {
  sheet.getRange(range).formulas = formulas;
}

function title(range) {
  range.format.fill.color = "#173d35";
  range.format.font.color = "#ffffff";
  range.format.font.bold = true;
  range.format.font.size = 16;
}

function header(range) {
  range.format.fill.color = "#2f5d50";
  range.format.font.color = "#ffffff";
  range.format.font.bold = true;
}

function input(range) {
  range.format.fill.color = "#fff7d8";
}

function locked(range) {
  range.format.fill.color = "#edf3ef";
}

function warn(range) {
  range.format.fill.color = "#f7e3db";
}

function parseCsv(text) {
  const lines = text.trim().split(/\r?\n/);
  const headers = lines.shift().split(",");
  return lines.map((line) => {
    const values = [];
    let current = "";
    let quoted = false;
    for (let index = 0; index < line.length; index += 1) {
      const char = line[index];
      if (char === '"') {
        quoted = !quoted;
      } else if (char === "," && !quoted) {
        values.push(current);
        current = "";
      } else {
        current += char;
      }
    }
    values.push(current);
    const row = {};
    headers.forEach((key, index) => {
      row[key] = values[index] ?? "";
    });
    return row;
  });
}

function num(value) {
  if (value === "" || value == null) return null;
  const parsed = Number(String(value).replace(" ", ""));
  return Number.isFinite(parsed) ? parsed : null;
}

function dateOnly(value) {
  return value ? value.slice(0, 10) : "";
}

function timeOnly(value) {
  return value ? value.slice(11, 16) : "";
}

function marketFor(symbol) {
  const normalized = (symbol ?? "").toUpperCase();
  if (normalized.endsWith(".OQ") || normalized.endsWith(".N") || ["NVDA", "AAPL", "MSFT", "TSLA"].includes(normalized)) return "US-Aktie";
  if (["DE40", "DE40.C", "USTEC", "DJ30", "DAX", "US500", "US500.C", "JP225", "F40.C"].includes(normalized)) return "Index";
  if (["XAGUSD", "XAUUSD", "XAUEUR", "XPTUSD", "UKOIL"].includes(normalized)) return "Rohstoff";
  if (["BTCUSD", "BTCEUR", "BCHUSD", "ETHUSD"].includes(normalized)) return "Krypto";
  if (/^[A-Z]{6}$/.test(normalized)) return "Forex";
  return "Sonstige";
}

function pct(value) {
  return value == null ? "" : value;
}

const backtest = JSON.parse(await fs.readFile(backtestPath, "utf8"));

// Listen
setValues(lists, "A1:H1", [["Setup", "Richtung", "Stil", "JaNein", "Modus", "Markt", "Emotion", "Zeiteinheit"]]);
setValues(lists, "A2:A13", [
  ["US Newstrade Breakout"],
  ["US Newstrade Reversal"],
  ["Reversal ohne News"],
  ["Rectangle"],
  ["Vorbörsliches Hoch/Tief"],
  ["Forex Wirtschaftsdaten"],
  ["FX Trendlinien"],
  ["DAX Abpraller"],
  ["SR Reversal"],
  ["52-Wochen Hoch"],
  ["IPO"],
  ["Review offen"],
]);
setValues(lists, "B2:B3", [["Long"], ["Short"]]);
setValues(lists, "C2:C4", [["Scalping"], ["Daytrading"], ["Swingtrading"]]);
setValues(lists, "D2:D3", [["Ja"], ["Nein"]]);
setValues(lists, "E2:E3", [["Paper"], ["Echtgeld"]]);
setValues(lists, "F2:F7", [["US-Aktie"], ["Forex"], ["Index"], ["Rohstoff"], ["Krypto"], ["Sonstige"]]);
setValues(lists, "G2:G11", [["ruhig"], ["fokussiert"], ["gestresst"], ["FOMO"], ["frustriert"], ["euphorisch"], ["müde"], ["unsicher"], ["diszipliniert"], ["neutral"]]);
setValues(lists, "H2:H8", [["M1"], ["M5"], ["M15"], ["H1"], ["H4"], ["D1"], ["W1"]]);

// Risk settings
setValues(riskSettings, "A1:D1", [Array(4).fill("Risk_Settings")]);
riskSettings.getRange("A1:D1").merge();
title(riskSettings.getRange("A1:D1"));
setValues(riskSettings, "A3:D3", [["Parameter", "Wert", "Status", "Hinweis"]]);
header(riskSettings.getRange("A3:D3"));
setValues(riskSettings, "A4:D15", [
  ["Startkapital", 10000, "Input", "Vor Live-Wechsel mit Echtgeldkonto abgleichen"],
  ["Aktuelles Kapital", "", "Formel", "Startkapital plus Live_Journal Netto"],
  ["Default Risiko pro Trade", 0.01, "Input", "TradingFreaks Default: 1 %"],
  ["Warnschwelle Risiko", 0.01, "Input", "Warnung ab > 1 %"],
  ["Block-Schwelle Risiko", 0.05, "Input", "Kein Trade oberhalb 5 %"],
  ["Max Tagesverlust", 0.02, "Input", "Bei Erreichen Pause"],
  ["Max Wochenverlust", 0.04, "Input", "Bei Erreichen Wochenreview/Pause"],
  ["Max Verlustserie", 3, "Input", "Nach 3 Verlusten Psychologie-Check"],
  ["Anfänger max. Positionshebel", 10, "Input", "Warnung bei > 1:10"],
  ["Handelsmodus", "Paper", "Input", "Live-Trading bleibt extern und manuell"],
  ["Screenshots Pflicht", "Ja", "Input", "Vor und nach dem Trade"],
  ["Journal-Pflicht", "Ja", "Input", "Kein Echtgeld ohne vollständige Dokumentation"],
]);
setFormulas(riskSettings, "B5:B5", [[`=B4+SUM(Live_Journal!Z${liveStart}:Z${liveEnd})`]]);
input(riskSettings.getRange("B4:B4"));
input(riskSettings.getRange("B6:B15"));
locked(riskSettings.getRange("B5:B5"));
riskSettings.getRange("B6:B10").format.numberFormat = "0.00%";
riskSettings.getRange("A:A").format.columnWidthPx = 230;
riskSettings.getRange("B:B").format.columnWidthPx = 130;
riskSettings.getRange("D:D").format.columnWidthPx = 420;

// Trade Plan
setValues(tradePlan, "A1:D1", [Array(4).fill("Trade_Plan Gatekeeper")]);
tradePlan.getRange("A1:D1").merge();
title(tradePlan.getRange("A1:D1"));
setValues(tradePlan, "A3:D3", [["Feld", "Eingabe", "Status", "Regel"]]);
header(tradePlan.getRange("A3:D3"));
setValues(tradePlan, "A4:D30", [
  ["Modus", "Paper", "", "Echtgeld erst nach stabiler Paper-Phase"],
  ["Datum", "", "", "Dokumentation vor Entry"],
  ["Symbol", "", "", "Nur liquider, passender Markt"],
  ["Markt", "", "", "US-Aktie / Forex / Index / Rohstoff"],
  ["Setup", "", "", "Nur vorab definiertes Setup"],
  ["Richtung", "", "", "Long oder Short"],
  ["Trading-Stil", "", "", "Scalping / Daytrading / Swingtrading"],
  ["Zeiteinheit Kontext", "", "", "Höhere Zeiteinheit prüfen"],
  ["Zeiteinheit Entry", "", "", "Entry-Zeiteinheit dokumentieren"],
  ["Entry", "", "", "Vor Tradebeginn planen"],
  ["Stop Loss", "", "", "Pflicht, sonst nicht handeln"],
  ["Take Profit / Exit", "", "", "TP oder Exit-Regel Pflicht"],
  ["Tick-/Punktwert", 1, "", "Für Positionsgröße erforderlich"],
  ["Risiko %", "", "", "Default aus Risk_Settings"],
  ["Positionsgröße", "", "", "Formel aus Risiko / Stop-Abstand"],
  ["Risiko EUR", "", "", "Formel"],
  ["CRV geplant", "", "", "Minimum 1:1"],
  ["Pflichtkriterien vollständig", "Nein", "", "Alle Setup-Kriterien müssen erfüllt sein"],
  ["News/Event geprüft", "Nein", "", "Keine Trades direkt vor Risikoevent"],
  ["Psychologie ok", "Nein", "", "Kein Revenge, FOMO, Stress-Trade"],
  ["Verlust akzeptiert", "Nein", "", "SL mental akzeptiert"],
  ["Screenshots bereit", "Nein", "", "Vorher/Nachher dokumentieren"],
  ["Tages-/Wochenlimit frei", "Ja", "", "Keine Limits überschreiten"],
  ["Kein Revenge/FOMO", "Ja", "", "Disziplin-Gate"],
  ["Trade Gate", "", "", "Nur Checklistenunterstützung, keine Empfehlung"],
  ["Notiz", "", "", "These kurz und prüfbar formulieren"],
  ["Nächster Schritt", "", "", "Bei Block: nicht handeln / nur beobachten"],
]);
setFormulas(tradePlan, "B5:B5", [["=TODAY()"]]);
setFormulas(tradePlan, "B17:B20", [[
  "=Risk_Settings!B6",
], [
  '=IF(OR(B13="",B14="",B15="",B16="",B17=""),"",ROUND((Risk_Settings!B5*B17)/(ABS(B13-B14)*B16),2))',
], [
  '=IF(OR(B13="",B14="",B16="",B18=""),"",ABS(B13-B14)*B16*B18)',
], [
  '=IFERROR(IF(B9="Long",(B15-B13)/(B13-B14),IF(B9="Short",(B13-B15)/(B14-B13),"")),"")',
]]);
setFormulas(tradePlan, "C4:C30", [
  ['=IF(B4="Echtgeld","Warnung","OK")'],
  ['=IF(B5="","Block","OK")'],
  ['=IF(B6="","Block","OK")'],
  ['=IF(B7="","Block","OK")'],
  ['=IF(B8="","Block","OK")'],
  ['=IF(OR(B9="Long",B9="Short"),"OK","Block")'],
  ['=IF(B10="","Block","OK")'],
  ['=IF(B11="","Block","OK")'],
  ['=IF(B12="","Block","OK")'],
  ['=IF(B13="","Block","OK")'],
  ['=IF(OR(B14="",AND(B9="Long",B14>=B13),AND(B9="Short",B14<=B13)),"Block","OK")'],
  ['=IF(B15="","Block","OK")'],
  ['=IF(B16>0,"OK","Block")'],
  ['=IF(OR(B17="",B17<=0,B17>Risk_Settings!B8),"Block",IF(B17>Risk_Settings!B7,"Warnung","OK"))'],
  ['=IF(B18="","Block","OK")'],
  ['=IF(B19="","Block","OK")'],
  ['=IF(OR(B20="",B20<1),"Block","OK")'],
  ['=IF(B21="Ja","OK","Block")'],
  ['=IF(B22="Ja","OK","Block")'],
  ['=IF(B23="Ja","OK","Block")'],
  ['=IF(B24="Ja","OK","Block")'],
  ['=IF(B25="Ja","OK","Block")'],
  ['=IF(B26="Ja","OK","Block")'],
  ['=IF(B27="Ja","OK","Block")'],
  ['=IF(COUNTIF(C4:C27,"Block")>0,"NICHT HANDELN",IF(COUNTIF(C4:C27,"Warnung")>0,"NUR REVIEW / RISIKO REDUZIEREN","CHECKLISTE ERFÜLLT"))'],
  ['=IF(B29="","Review offen","OK")'],
  ['=IF(C28="NICHT HANDELN","Nicht handeln / nur beobachten","Manuell journalisieren; keine automatische Order")'],
]);
input(tradePlan.getRange("B4:B16"));
input(tradePlan.getRange("B21:B29"));
locked(tradePlan.getRange("B17:B20"));
locked(tradePlan.getRange("C4:C30"));
warn(tradePlan.getRange("A28:D30"));
tradePlan.getRange("B17:B17").format.numberFormat = "0.00%";
tradePlan.getRange("B19:B20").format.numberFormat = "#,##0.00";
tradePlan.getRange("A:A").format.columnWidthPx = 230;
tradePlan.getRange("B:B").format.columnWidthPx = 170;
tradePlan.getRange("C:C").format.columnWidthPx = 210;
tradePlan.getRange("D:D").format.columnWidthPx = 420;

// Live Journal
const liveHeaders = [
  "Trade-No.", "Datum", "Uhrzeit", "Modus", "Markt", "Symbol", "Setup", "Richtung", "Stil",
  "TF Kontext", "TF Entry", "News", "Event", "Sentiment", "Entry", "SL", "TP", "Exit",
  "Tick-/Punktwert", "Positionsgröße", "Risiko EUR", "Risiko %", "CRV geplant", "Brutto",
  "Kosten", "Netto", "Ergebnis R", "Regelkonform", "Verletzte Regel", "Pflichtkriterien erfüllt",
  "Psychologie ok", "Screenshot vor", "Screenshot nach", "Emotion vorher", "Emotion während",
  "Emotion nachher", "Review", "Verbesserung", "Journal vollständig", "Trade Gate", "Notiz/Quelle",
];
setValues(liveJournal, "A1:F1", [Array(6).fill("Live_Journal")]);
liveJournal.getRange("A1:F1").merge();
title(liveJournal.getRange("A1:F1"));
setValues(liveJournal, "A3:H3", [["Trades", "Gewinntrades", "Verlusttrades", "Trefferquote", "Netto", "Profit Factor", "Regelkonform", "Journal vollständig"]]);
header(liveJournal.getRange("A3:H3"));
setFormulas(liveJournal, "A4:H4", [[
  `=COUNTA(B${liveStart}:B${liveEnd})`,
  `=COUNTIF(Z${liveStart}:Z${liveEnd},">0")`,
  `=COUNTIF(Z${liveStart}:Z${liveEnd},"<0")`,
  '=IF(A4=0,"",B4/A4)',
  `=SUM(Z${liveStart}:Z${liveEnd})`,
  `=IFERROR(SUMIF(Z${liveStart}:Z${liveEnd},">0",Z${liveStart}:Z${liveEnd})/ABS(SUMIF(Z${liveStart}:Z${liveEnd},"<0",Z${liveStart}:Z${liveEnd})),"")`,
  `=COUNTIF(AB${liveStart}:AB${liveEnd},"Ja")`,
  `=COUNTIF(AM${liveStart}:AM${liveEnd},"Ja")`,
]]);
locked(liveJournal.getRange("A4:H4"));
setValues(liveJournal, `A7:AO7`, [liveHeaders]);
header(liveJournal.getRange("A7:AO7"));
setFormulas(liveJournal, `A${liveStart}:A${liveEnd}`, Array.from({ length: liveRows }, (_, index) => {
  const row = liveStart + index;
  return [`=IF(B${row}="","",ROW()-7)`];
}));
setFormulas(liveJournal, `U${liveStart}:W${liveEnd}`, Array.from({ length: liveRows }, (_, index) => {
  const row = liveStart + index;
  return [
    `=IF(OR(O${row}="",P${row}="",S${row}="",T${row}=""),"",ABS(O${row}-P${row})*S${row}*T${row})`,
    `=IF(U${row}="","",IFERROR(U${row}/Risk_Settings!B5,""))`,
    `=IFERROR(IF(H${row}="Long",(Q${row}-O${row})/(O${row}-P${row}),IF(H${row}="Short",(O${row}-Q${row})/(P${row}-O${row}),"")),"")`,
  ];
}));
setFormulas(liveJournal, `Z${liveStart}:AA${liveEnd}`, Array.from({ length: liveRows }, (_, index) => {
  const row = liveStart + index;
  return [
    `=IF(AND(X${row}="",Y${row}=""),"",X${row}-Y${row})`,
    `=IFERROR(Z${row}/U${row},"")`,
  ];
}));
setFormulas(liveJournal, `AM${liveStart}:AN${liveEnd}`, Array.from({ length: liveRows }, (_, index) => {
  const row = liveStart + index;
  return [
    `=IF(B${row}="","",IF(AND(AB${row}<>"",AD${row}<>"",AE${row}<>"",AF${row}<>"",AG${row}<>"",AH${row}<>"",AI${row}<>"",AJ${row}<>"",AK${row}<>"",AL${row}<>""),"Ja","Nein"))`,
    `=IF(B${row}="","",IF(OR(P${row}="",Q${row}="",W${row}<1,V${row}>Risk_Settings!B8,AD${row}<>"Ja",AE${row}<>"Ja"),"NICHT HANDELN/REVIEW","OK dokumentiert"))`,
  ];
}));
input(liveJournal.getRange(`B${liveStart}:T${liveEnd}`));
input(liveJournal.getRange(`X${liveStart}:Y${liveEnd}`));
input(liveJournal.getRange(`AB${liveStart}:AL${liveEnd}`));
input(liveJournal.getRange(`AO${liveStart}:AO${liveEnd}`));
locked(liveJournal.getRange(`A${liveStart}:A${liveEnd}`));
locked(liveJournal.getRange(`U${liveStart}:W${liveEnd}`));
locked(liveJournal.getRange(`Z${liveStart}:AA${liveEnd}`));
locked(liveJournal.getRange(`AM${liveStart}:AN${liveEnd}`));
liveJournal.getRange(`B${liveStart}:B${liveEnd}`).format.numberFormat = "yyyy-mm-dd";
liveJournal.getRange(`C${liveStart}:C${liveEnd}`).format.numberFormat = "hh:mm";
liveJournal.getRange(`O${liveStart}:Z${liveEnd}`).format.numberFormat = "#,##0.00";
liveJournal.getRange(`V${liveStart}:V${liveEnd}`).format.numberFormat = "0.00%";
liveJournal.getRange(`W${liveStart}:W${liveEnd}`).format.numberFormat = "0.00";
liveJournal.getRange(`AA${liveStart}:AA${liveEnd}`).format.numberFormat = "0.00";
liveJournal.getRange("A:C").format.columnWidthPx = 105;
liveJournal.getRange("D:N").format.columnWidthPx = 125;
liveJournal.getRange("O:AA").format.columnWidthPx = 105;
liveJournal.getRange("AB:AO").format.columnWidthPx = 170;

// Live Cockpit
setValues(cockpit, "A1:H1", [Array(8).fill("Live_Cockpit")]);
cockpit.getRange("A1:H1").merge();
title(cockpit.getRange("A1:H1"));
setValues(cockpit, "A3:H3", [["Kennzahl", "Wert", "Status", "Prozessregel", "Kennzahl", "Wert", "Status", "Prozessregel"]]);
header(cockpit.getRange("A3:H3"));
setValues(cockpit, "A4:D11", [
  ["Handelsmodus", "", "", "Echtgeld bleibt manuell und extern"],
  ["Aktuelles Kapital", "", "", "Aus Risk_Settings und Live_Journal"],
  ["Default Risiko", "", "", "Standard 1 %"],
  ["Heute Netto", "", "", "Bei Tageslimit: Pause"],
  ["Diese Woche Netto", "", "", "Bei Wochenlimit: Review"],
  ["Live-Trades", "", "", "Nur vollständig dokumentierte Trades zählen"],
  ["Regelkonformität", "", "", "Ziel: 100 % Prozessqualität"],
  ["Journal vollständig", "", "", "Ziel: 100 % Dokumentation"],
]);
setValues(cockpit, "E4:H11", [
  ["Backtest Trades", backtest.overall.trades, "Info", "Historie nur als Warnsystem"],
  ["Backtest Profit Factor", backtest.overall.profit_factor, "Info", "Unter 1: Setup-/Risikoreview nötig"],
  ["Backtest Max DD", backtest.overall.max_drawdown, "Info", "Drawdown-Schutz ernst nehmen"],
  ["Backtest Verlustserie", backtest.overall.largest_loss_streak, "Info", "Nach 3 Verlusten Pause/Check"],
  ["Haupt-Risikocluster", "Rohstoffe/XAGUSD", "Warnung", "Vor Echtgeld nur mit getesteter Regel"],
  ["Setup-Gate", "Alle Pflichtfelder", "Pflicht", "Fehlt ein Kriterium: nicht handeln"],
  ["SL/TP Gate", "Pflicht", "Pflicht", "Kein Trade ohne Stop Loss"],
  ["Psychologie-Gate", "Pflicht", "Pflicht", "Kein Revenge/FOMO"],
]);
setFormulas(cockpit, "B4:B11", [
  ["=Risk_Settings!B13"],
  ["=Risk_Settings!B5"],
  ["=Risk_Settings!B6"],
  [`=SUMIFS(Live_Journal!Z${liveStart}:Z${liveEnd},Live_Journal!B${liveStart}:B${liveEnd},TODAY())`],
  [`=SUMIFS(Live_Journal!Z${liveStart}:Z${liveEnd},Live_Journal!B${liveStart}:B${liveEnd},">="&TODAY()-WEEKDAY(TODAY(),2)+1,Live_Journal!B${liveStart}:B${liveEnd},"<="&TODAY())`],
  ["=Live_Journal!A4"],
  ['=IF(Live_Journal!A4=0,"",Live_Journal!G4/Live_Journal!A4)'],
  ['=IF(Live_Journal!A4=0,"",Live_Journal!H4/Live_Journal!A4)'],
]);
setFormulas(cockpit, "C4:C11", [
  ['=IF(B4="Echtgeld","Warnung","OK")'],
  ['=IF(B5>0,"OK","Block")'],
  ['=IF(B6<=Risk_Settings!B7,"OK","Warnung")'],
  ['=IF(B7<=-Risk_Settings!B5*Risk_Settings!B9,"Pause","OK")'],
  ['=IF(B8<=-Risk_Settings!B5*Risk_Settings!B10,"Pause","OK")'],
  ['=IF(B9=0,"Noch keine Live-Trades","Info")'],
  ['=IF(B10="","Noch keine Live-Trades",IF(B10=1,"OK","Warnung"))'],
  ['=IF(B11="","Noch keine Live-Trades",IF(B11=1,"OK","Warnung"))'],
]);
locked(cockpit.getRange("B4:C11"));
locked(cockpit.getRange("E4:H11"));
cockpit.getRange("B5:B8").format.numberFormat = "#,##0.00";
cockpit.getRange("B6:B6").format.numberFormat = "0.00%";
cockpit.getRange("B10:B11").format.numberFormat = "0.00%";
cockpit.getRange("F5:F6").format.numberFormat = "#,##0.00";
cockpit.getRange("A:A").format.columnWidthPx = 170;
cockpit.getRange("D:D").format.columnWidthPx = 330;
cockpit.getRange("E:E").format.columnWidthPx = 185;
cockpit.getRange("H:H").format.columnWidthPx = 330;

// Psychology
setValues(psychology, "A1:J1", [Array(10).fill("Psychologie")]);
psychology.getRange("A1:J1").merge();
title(psychology.getRange("A1:J1"));
setValues(psychology, "A3:J3", [["Datum", "Glücklich", "Gestresst", "Wach", "Entmutigt", "Nervös/Frustriert", "Balance/Kontrolle", "Impulsivität", "Trading Pause empfohlen", "Notiz"]]);
header(psychology.getRange("A3:J3"));
input(psychology.getRange("A4:H370"));
input(psychology.getRange("J4:J370"));
setFormulas(psychology, "I4:I370", Array.from({ length: 367 }, (_, index) => {
  const row = 4 + index;
  return [`=IF(A${row}="","",IF(OR(C${row}>=4,E${row}>=4,F${row}>=4,H${row}>=4,G${row}<=2),"Ja","Nein"))`];
}));
locked(psychology.getRange("I4:I370"));
psychology.getRange("A:A").format.columnWidthPx = 110;
psychology.getRange("B:I").format.columnWidthPx = 120;
psychology.getRange("J:J").format.columnWidthPx = 320;

// Weekly review
setValues(weekly, "A1:I1", [Array(9).fill("Wochenreview")]);
weekly.getRange("A1:I1").merge();
title(weekly.getRange("A1:I1"));
setValues(weekly, "A3:I3", [["Woche ab", "Trades", "Netto", "Trefferquote", "Regelkonform", "Journal vollständig", "Hauptfehler", "Fokus nächste Woche", "Live-ready?"]]);
header(weekly.getRange("A3:I3"));
input(weekly.getRange("A4:A55"));
input(weekly.getRange("G4:H55"));
setFormulas(weekly, "B4:F55", Array.from({ length: 52 }, (_, index) => {
  const row = 4 + index;
  return [
    `=IF(A${row}="","",COUNTIFS(Live_Journal!B:B,">="&A${row},Live_Journal!B:B,"<"&A${row}+7))`,
    `=IF(A${row}="","",SUMIFS(Live_Journal!Z:Z,Live_Journal!B:B,">="&A${row},Live_Journal!B:B,"<"&A${row}+7))`,
    `=IF(B${row}=0,"",COUNTIFS(Live_Journal!B:B,">="&A${row},Live_Journal!B:B,"<"&A${row}+7,Live_Journal!Z:Z,">0")/B${row})`,
    `=IF(B${row}=0,"",COUNTIFS(Live_Journal!B:B,">="&A${row},Live_Journal!B:B,"<"&A${row}+7,Live_Journal!AB:AB,"Ja")/B${row})`,
    `=IF(B${row}=0,"",COUNTIFS(Live_Journal!B:B,">="&A${row},Live_Journal!B:B,"<"&A${row}+7,Live_Journal!AM:AM,"Ja")/B${row})`,
  ];
}));
setFormulas(weekly, "I4:I55", Array.from({ length: 52 }, (_, index) => {
  const row = 4 + index;
  return [`=IF(B${row}=0,"",IF(AND(E${row}=1,F${row}=1),"Ja","Nein"))`];
}));
locked(weekly.getRange("B4:F55"));
locked(weekly.getRange("I4:I55"));
weekly.getRange("C:C").format.numberFormat = "#,##0.00";
weekly.getRange("D:F").format.numberFormat = "0.00%";
weekly.getRange("A:I").format.columnWidthPx = 130;
weekly.getRange("G:H").format.columnWidthPx = 280;

// Monthly summary
setValues(monthly, "A1:I1", [Array(9).fill("Monatsauswertung")]);
monthly.getRange("A1:I1").merge();
title(monthly.getRange("A1:I1"));
setValues(monthly, "A3:I3", [["Monat", "Trades", "Gewinntrades", "Verlusttrades", "Trefferquote", "Netto", "Profit Factor", "Regelkonform", "Journal vollständig"]]);
header(monthly.getRange("A3:I3"));
const monthRows = Array.from({ length: 24 }, (_, index) => {
  const year = 2026 + Math.floor(index / 12);
  const month = (index % 12) + 1;
  return [`${year}-${String(month).padStart(2, "0")}`];
});
setValues(monthly, "A4:A27", monthRows);
setFormulas(monthly, "B4:I27", monthRows.map((rowValue, index) => {
  const row = 4 + index;
  const period = rowValue[0];
  const [year, month] = period.split("-").map(Number);
  const nextYear = month === 12 ? year + 1 : year;
  const nextMonth = month === 12 ? 1 : month + 1;
  const startDate = `${period}-01`;
  const endDate = `${nextYear}-${String(nextMonth).padStart(2, "0")}-01`;
  const criteria = `Live_Journal!B$${liveStart}:B$${liveEnd},">=${startDate}",Live_Journal!B$${liveStart}:B$${liveEnd},"<${endDate}"`;
  return [
    `=COUNTIFS(${criteria})`,
    `=COUNTIFS(${criteria},Live_Journal!Z$${liveStart}:Z$${liveEnd},">0")`,
    `=COUNTIFS(${criteria},Live_Journal!Z$${liveStart}:Z$${liveEnd},"<0")`,
    `=IF(B${row}=0,"",C${row}/B${row})`,
    `=SUMIFS(Live_Journal!Z$${liveStart}:Z$${liveEnd},${criteria})`,
    `=IFERROR(SUMIFS(Live_Journal!Z$${liveStart}:Z$${liveEnd},${criteria},Live_Journal!Z$${liveStart}:Z$${liveEnd},">0")/ABS(SUMIFS(Live_Journal!Z$${liveStart}:Z$${liveEnd},${criteria},Live_Journal!Z$${liveStart}:Z$${liveEnd},"<0")),"")`,
    `=IF(B${row}=0,"",COUNTIFS(${criteria},Live_Journal!AB$${liveStart}:AB$${liveEnd},"Ja")/B${row})`,
    `=IF(B${row}=0,"",COUNTIFS(${criteria},Live_Journal!AM$${liveStart}:AM$${liveEnd},"Ja")/B${row})`,
  ];
}));
locked(monthly.getRange("B4:I27"));
monthly.getRange("E:E").format.numberFormat = "0.00%";
monthly.getRange("F:F").format.numberFormat = "#,##0.00";
monthly.getRange("G:I").format.numberFormat = "0.00";
monthly.getRange("H:I").format.numberFormat = "0.00%";
monthly.getRange("A:I").format.columnWidthPx = 130;

// Backtest insights
setValues(insights, "A1:H1", [Array(8).fill("Backtest_Insights")]);
insights.getRange("A1:H1").merge();
title(insights.getRange("A1:H1"));
setValues(insights, "A3:D3", [["Kennzahl", "Wert", "Interpretation", "Prozessregel fürs Live-Journal"]]);
header(insights.getRange("A3:D3"));
setValues(insights, "A4:D15", [
  ["Trades historisch", backtest.overall.trades, "Große Stichprobe, aber unvollständig dokumentiert", "Historie nur als Warnsystem nutzen"],
  ["Trefferquote", backtest.overall.win_rate, "Trefferquote allein reicht nicht", "Erwartungswert und Regelkonformität prüfen"],
  ["Nettoergebnis", backtest.overall.net_profit, "Gesamt negativ", "Vor Echtgeld nur mit vollständigem Prozess"],
  ["Profit Factor", backtest.overall.profit_factor, "Unter 1", "Setup-Freigabe erst nach Paper-Review"],
  ["Max Drawdown", backtest.overall.max_drawdown, "Sehr hoher Sequenz-Drawdown", "Tages-/Wochenlimit hart führen"],
  ["Größte Verlustserie", backtest.overall.largest_loss_streak, "11 Verluste am Stück", "Nach 3 Verlusten Pause und Psychologie-Check"],
  ["Rohstoff-Cluster", "XAGUSD/XAUUSD/XAUEUR", "Dominanter Drawdown-Cluster", "Nur mit eigenem getesteten Setup und kleinem Risiko"],
  ["Regelkonform dokumentiert", backtest.overall.rule_compliant_trades, "Aus Quellen nicht nachweisbar", "Ohne Pflichtfelder: nicht handeln"],
  ["SL/TP", "Pflicht", "Ohne SL/TP kein Trade", "Gatekeeper blockiert unvollständige Planung"],
  ["Psychologie", "Pflicht", "Revenge/FOMO sind Risikofaktoren", "Täglicher Psychologie-Check"],
  ["Screenshots", "Pflicht", "Review sonst kaum möglich", "Vorher/Nachher im Journal verlinken"],
  ["Live-Wechsel", "Bedingt", "Nicht an P&L, sondern Prozessqualität koppeln", "Erst nach Wochenreview mit 100 % Dokumentation"],
]);
insights.getRange("B5:B8").format.numberFormat = "#,##0.00";
insights.getRange("B5:B5").format.numberFormat = "0.00%";
insights.getRange("B7:B7").format.numberFormat = "0.00";
insights.getRange("A:A").format.columnWidthPx = 190;
insights.getRange("B:B").format.columnWidthPx = 130;
insights.getRange("C:D").format.columnWidthPx = 330;

setValues(insights, "F3:H3", [["Schwächste Symbole", "Netto", "Prozessnotiz"]]);
header(insights.getRange("F3:H3"));
setValues(insights, "F4:H13", backtest.by_symbol_worst.slice(0, 10).map((row) => [
  row.name,
  row.net_profit,
  "Vor Live nur mit explizitem Setup-Review",
]));
insights.getRange("G4:G13").format.numberFormat = "#,##0.00";

// Import Review
const importHeaders = ["Quelle", "Datum", "Zeit Entry", "Zeit Exit", "Symbol", "Markt", "Richtung", "Entry", "Exit", "Qty", "Brutto", "Kosten", "Netto", "Regelstatus", "Fehlende Pflichtfelder", "Review-Notiz"];
setValues(importReview, "A1:F1", [Array(6).fill("Import_Review")]);
importReview.getRange("A1:F1").merge();
title(importReview.getRange("A1:F1"));
setValues(importReview, "A3:P3", [importHeaders]);
header(importReview.getRange("A3:P3"));
const importRecords = [];
try {
  const monthlyCsv = await fs.readFile(monthlyTradesPath, "utf8");
  for (const trade of parseCsv(monthlyCsv)) {
    const gross = num(trade.gross_profit) ?? 0;
    const net = num(trade.net_profit) ?? gross;
    const costs = Math.max(0, gross - net);
    const note = trade.source_note ? `Kommentar: ${trade.source_note}` : "";
    importRecords.push([
      trade.source_file,
      dateOnly(trade.exit_time),
      timeOnly(trade.entry_time),
      timeOnly(trade.exit_time),
      trade.symbol,
      marketFor(trade.symbol),
      trade.direction,
      num(trade.entry),
      num(trade.exit),
      num(trade.qty),
      gross,
      costs,
      net,
      "Review offen",
      "Setup, SL/TP Planung, Screenshots, Emotionen",
      `Order ${trade.order_id}; ${note}`,
    ]);
  }
} catch (error) {
  console.log(`No monthly import review data: ${error.message}`);
}
try {
  const orderCsv = await fs.readFile(orderHistoryPath, "utf8");
  for (const trade of parseCsv(orderCsv)) {
    const gross = num(trade.gross_profit) ?? 0;
    const costs = Math.abs((num(trade.commission) ?? 0) + (num(trade.swap) ?? 0));
    importRecords.push([
      "TradingView/GBE Orderverlauf",
      dateOnly(trade.exit_time),
      timeOnly(trade.entry_time),
      timeOnly(trade.exit_time),
      trade.symbol,
      marketFor(trade.symbol),
      trade.direction,
      num(trade.entry),
      num(trade.exit),
      num(trade.qty),
      gross,
      costs,
      gross - costs,
      "Review offen",
      "Setup, Screenshots, Emotionen",
      `SL dokumentiert: ${trade.has_recorded_sl}; TP dokumentiert: ${trade.has_recorded_tp}; CRV: ${trade.recorded_crv}`,
    ]);
  }
} catch (error) {
  console.log(`No order import review data: ${error.message}`);
}
if (importRecords.length) {
  setValues(importReview, `A${importStart}:P${importStart + Math.min(importRows, importRecords.length) - 1}`, importRecords.slice(0, importRows));
}
importReview.getRange("A:P").format.columnWidthPx = 130;
importReview.getRange("O:P").format.columnWidthPx = 280;
importReview.getRange(`H${importStart}:M${importStart + importRows}`).format.numberFormat = "#,##0.00";

// Setup rules
setValues(setups, "A1:H1", [Array(8).fill("Setup_Regeln")]);
setups.getRange("A1:H1").merge();
title(setups.getRange("A1:H1"));
setValues(setups, "A3:H3", [["Setup", "Markt", "Pflichtkriterien", "Entry", "SL", "TP/Exit", "Nicht handeln wenn", "Journal-Fokus"]]);
header(setups.getRange("A3:H3"));
setValues(setups, "A4:H14", [
  ["US Newstrade Breakout", "US-Aktie", "News, >3 %, Momentum, VWAP-Seite, enge Konsolidierung, RVOL >1,5", "Breakout nahe Level", "Lokale Struktur", "CRV >= 1:1, intraday schließen", "Mixed News, Volatilität statt Momentum, tiefe Korrektur", "News, RVOL, VWAP, Korrektur, Screenshot"],
  ["US Newstrade Reversal", "US-Aktie", "News, VWAP-Abstand, Boden/Top, Entry-Signal", "Reversal Richtung VWAP/News", "Lokale Struktur", "VWAP/Level, CRV >= 1:1", "Keine Bodenbildung, Hoffnungseinstieg", "VWAP-Abstand, Signal, Emotion"],
  ["Reversal ohne News", "US-Aktie", "Keine News, VWAP-Abstand, Fib, EMA9, Folgekerze", "Mean-Reversion-Signal", "Lokal tief/hoch", "50er Fib oder VWAP", "News, Volumenhinweis, nach 20:00", "Fib-Level, EMA9, Uhrzeit"],
  ["Rectangle", "US-Aktie", "Momentum, max. 1/3 Korrektur, 6 Kerzen, horizontal", "Stop über/unter Range", "Gegenseite Range", "CRV 1:1 oder Trailing", "Flagge, Dreieck, unklare Range", "Range-Kanten, Touchpoints"],
  ["Vorbörsliches Hoch/Tief", "US-Aktie", "News, >3 %, Opening Drive, Level bis 15:25", "Breakout Premarket Level", "Lokale Struktur", "CRV ca. 1:1", "Keine News, kein Drive, Entry weit weg", "Premarket Level, Entry-Nähe"],
  ["Forex Wirtschaftsdaten", "Forex", "Event, klare Überraschung, einheitliche Daten, >20 Pips Momentum", "Momentum oder Pullback", "20-50 Pips", "CRV ca. 1:1", "Gemischte Daten, Vorposition, beide Stopps", "Event, Daten, Momentum"],
  ["FX Trendlinien", "Forex", "H4+, 2 Punkte, dritter Touch, kein Event", "Limit 5-10 Pips vor Linie", "20-50 Pips", "CRV ca. 1:1", "Frische News, Gegensentiment, hohe Kosten", "Trendlinie, Touchcount"],
  ["DAX Abpraller", "Index", "H4/D1/W1 Zone, Kalender ok, technische Idee", "10-15 Punkte vor Zone", "Außerhalb Zone", "50/100/300 Punkte je Stil", "Risikoevent, schwache Zone", "Zone, Screenshot, Tests"],
  ["SR Reversal", "FX/Index", "H4/D1/W1 Zone, 24h kein Event", "Limit vor Zone", "20-50 Pips / 50-200 Punkte", "CRV 1:1", "Event, Zone nicht stark", "Zone, Entfernung, Risiko"],
  ["Live-Schutzregel", "Alle", "Kein Trade ohne vollständige Checkliste", "Manuell", "Pflicht", "Pflicht", "Stress, FOMO, Revenge, Tageslimit", "Prozessqualität vor P&L"],
  ["Paper-zu-Live Review", "Alle", "Erst nach Wochen mit 100 % Dokumentation", "n/a", "n/a", "n/a", "Regelverstöße offen", "Wochenreview entscheidet"],
]);
setups.getRange("A:H").format.columnWidthPx = 180;
setups.getRange("C:H").format.columnWidthPx = 310;

for (const sheet of [cockpit, tradePlan, liveJournal, riskSettings, psychology, weekly, monthly, insights, importReview, setups, lists]) {
  sheet.getRange("A:AO").format.font.name = "Aptos";
}
cockpit.freezePanes.freezeRows(3);
tradePlan.freezePanes.freezeRows(3);
liveJournal.freezePanes.freezeRows(7);
riskSettings.freezePanes.freezeRows(3);
psychology.freezePanes.freezeRows(3);
weekly.freezePanes.freezeRows(3);
monthly.freezePanes.freezeRows(3);
insights.freezePanes.freezeRows(3);
importReview.freezePanes.freezeRows(3);
setups.freezePanes.freezeRows(3);

await fs.mkdir(outputDir, { recursive: true });
const output = await SpreadsheetFile.exportXlsx(workbook);
await output.save(outputPath);
console.log(outputPath);
