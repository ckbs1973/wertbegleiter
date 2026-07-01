import fs from "node:fs/promises";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const outputDir = "../outputs/trading_journal_tf";
const outputPath = `${outputDir}/TradingFreaks_Detailed_Journal_Codex.xlsx`;
const reconstructedTradesPath = "../reports/trade_history_gbe_2026-05-20_reconstructed_trades.csv";
const monthlyTradesPath = "../reports/gbe_monthly_closed_trades.csv";
const maxJournalRow = 1807;

const months = [
  "Januar", "Februar", "Maerz", "April", "Mai", "Juni",
  "Juli", "August", "September", "Oktober", "November", "Dezember",
];

const monthlyPeriods = [
  "2025-08", "2025-09", "2025-10", "2025-11",
  "2026-01", "2026-02", "2026-04", "2026-05",
];

const setups = [
  "Forex Wirtschaftsdaten",
  "Trendlinien Scalping",
  "Trendlinien Swingtrading",
  "Aktien Newstrading",
  "Vorbörsliches Hoch/Tief",
  "Rectangle",
  "Aktien Reversal mit News",
  "Reversal ohne News",
  "DAX Abpraller",
  "SR Reversal",
  "52-Wochen Hoch",
  "IPO",
];

const headers = [
  "Trade-No.", "Datum", "Uhrzeit Einstieg", "Uhrzeit Ausstieg", "Strategie", "Symbol",
  "Markt", "Long/Short", "Trading-Stil", "Zeiteinheit Kontext", "Zeiteinheit Entry",
  "News-Katalysator", "Wirtschaftsevent", "Sentiment", "Positionsgröße/Lot",
  "Einstieg", "SL", "TP", "Ausstieg", "Risiko", "Risiko [%]", "Tradeergebnis",
  "Gebühren/Spread", "Nettoergebnis", "Ergebnis [%]", "CRV geplant", "CRV realisiert",
  "Sternebewertung", "Regelkonform", "Verletzte Regel", "Setup-Kriterien erfüllt",
  "Setup-Kriterien nicht erfüllt", "Entry-Grund", "Emotion vorher", "Emotion während",
  "Emotion nachher", "Überzeugung 1-10", "Screenshot vor Trade", "Screenshot nach Trade",
  "Review", "Verbesserung nächster Trade", "Kapitalentwicklung", "Journal vollständig",
];

const workbook = Workbook.create();
const overview = workbook.worksheets.add("Kontoübersicht");
const journal = workbook.worksheets.add("Journal");
const monthly = workbook.worksheets.add("Monatsauswertung");
const review = workbook.worksheets.add("Wochenreview");
const psyche = workbook.worksheets.add("Psychologie");
const setupSheet = workbook.worksheets.add("Setups");
const helper = workbook.worksheets.add("Listen");

function setValues(sheet, range, values) {
  sheet.getRange(range).values = values;
}

function setFormulas(sheet, range, formulas) {
  sheet.getRange(range).formulas = formulas;
}

function styleTitle(range) {
  range.format.fill.color = "#1f3b33";
  range.format.font.color = "#ffffff";
  range.format.font.bold = true;
  range.format.font.size = 16;
}

function styleHeader(range) {
  range.format.fill.color = "#2f5d50";
  range.format.font.color = "#ffffff";
  range.format.font.bold = true;
}

function styleInput(range) {
  range.format.fill.color = "#fff8df";
}

function styleLocked(range) {
  range.format.fill.color = "#eef3ef";
}

function parseCsv(text) {
  const lines = text.trim().split(/\r?\n/);
  const header = lines.shift().split(",");
  return lines.map((line) => {
    const parts = line.split(",");
    const row = {};
    header.forEach((key, index) => {
      row[key] = parts[index] ?? "";
    });
    return row;
  });
}

function dateOnly(value) {
  if (!value) return "";
  return value.slice(0, 10);
}

function timeOnly(value) {
  if (!value) return "";
  return value.slice(11, 16);
}

function marketFor(symbol) {
  const normalized = (symbol ?? "").toUpperCase();
  if (normalized.endsWith(".OQ") || normalized.endsWith(".N") || ["NVDA", "AAPL", "MSFT", "TSLA"].includes(normalized)) return "US-Aktie";
  if (["DE40", "DE40.C", "USTEC", "DJ30", "DAX", "US500", "JP225"].includes(normalized)) return "Index";
  if (["XAGUSD", "XAUUSD", "XAUEUR", "XPTUSD", "UKOIL"].includes(normalized)) return "Rohstoff";
  if (["BTCUSD", "BCHUSD", "ETHUSD"].includes(normalized)) return "Krypto";
  if (/^[A-Z]{6}$/.test(normalized)) return "Forex";
  return "";
}

function num(value) {
  if (value === "" || value == null) return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function columnName(columnNumber) {
  let name = "";
  let number = columnNumber;
  while (number > 0) {
    const remainder = (number - 1) % 26;
    name = String.fromCharCode(65 + remainder) + name;
    number = Math.floor((number - 1) / 26);
  }
  return name;
}

function monthCriteria(columnNumber) {
  const monthNumber = columnNumber - 1;
  const startDate = `2026-${String(monthNumber).padStart(2, "0")}-01`;
  const nextMonth = monthNumber === 12 ? "2027-01-01" : `2026-${String(monthNumber + 1).padStart(2, "0")}-01`;
  return [
    `Journal!B$8:B$${maxJournalRow},">=${startDate}"`,
    `Journal!B$8:B$${maxJournalRow},"<${nextMonth}"`,
  ].join(",");
}

function nextPeriod(period) {
  const [year, month] = period.split("-").map(Number);
  const nextYear = month === 12 ? year + 1 : year;
  const nextMonth = month === 12 ? 1 : month + 1;
  return `${nextYear}-${String(nextMonth).padStart(2, "0")}`;
}

function applyJournalFormulas() {
  setFormulas(journal, `A${start}:A${end}`, Array.from({ length: rows }, (_, i) => {
    const r = start + i;
    return [`=IF(B${r}="","",ROW()-7)`];
  }));
  setFormulas(journal, `T${start}:T${end}`, Array.from({ length: rows }, (_, i) => {
    const r = start + i;
    return [`=IF(OR(B${r}="",P${r}="",Q${r}="",O${r}=""),"",ABS(P${r}-Q${r})*O${r})`];
  }));
  setFormulas(journal, `U${start}:U${end}`, Array.from({ length: rows }, (_, i) => {
    const r = start + i;
    return [`=IFERROR(T${r}/'Kontoübersicht'!B$4,"")`];
  }));
  setFormulas(journal, `X${start}:X${end}`, Array.from({ length: rows }, (_, i) => {
    const r = start + i;
    return [`=IF(AND(V${r}="",W${r}=""),"",V${r}-W${r})`];
  }));
  setFormulas(journal, `Y${start}:Y${end}`, Array.from({ length: rows }, (_, i) => {
    const r = start + i;
    return [`=IFERROR(X${r}/'Kontoübersicht'!B$4,"")`];
  }));
  setFormulas(journal, `Z${start}:Z${end}`, Array.from({ length: rows }, (_, i) => {
    const r = start + i;
    return [`=IFERROR(ABS(R${r}-P${r})/ABS(P${r}-Q${r}),"")`];
  }));
  setFormulas(journal, `AA${start}:AA${end}`, Array.from({ length: rows }, (_, i) => {
    const r = start + i;
    return [`=IFERROR(ABS(S${r}-P${r})/ABS(P${r}-Q${r}),"")`];
  }));
  setFormulas(journal, `AP${start}:AP${end}`, Array.from({ length: rows }, (_, i) => {
    const r = start + i;
    return [`=IF(B${r}="","",IF(ROW()=8,'Kontoübersicht'!B$4+X${r},AP${r - 1}+X${r}))`];
  }));
  setFormulas(journal, `AQ${start}:AQ${end}`, Array.from({ length: rows }, (_, i) => {
    const r = start + i;
    return [`=IF(B${r}="","",IF(AND(AC${r}<>"",AE${r}<>"",AF${r}<>"",AG${r}<>"",AH${r}<>"",AI${r}<>"",AJ${r}<>"",AK${r}<>"",AL${r}<>"",AM${r}<>""),"Ja","Nein"))`];
  }));
}

// Listen
setValues(helper, "A1:H1", [["Setups", "Richtung", "Trading-Stil", "JaNein", "Regelkonform", "Emotion", "Markt", "Zeiteinheit"]]);
setValues(helper, `A2:A${setups.length + 1}`, setups.map((s) => [s]));
setValues(helper, "B2:B3", [["Long"], ["Short"]]);
setValues(helper, "C2:C4", [["Scalping"], ["Daytrading"], ["Swingtrading"]]);
setValues(helper, "D2:D3", [["Ja"], ["Nein"]]);
setValues(helper, "E2:E3", [["Ja"], ["Nein"]]);
setValues(helper, "F2:F10", [["ruhig"], ["fokussiert"], ["gestresst"], ["FOMO"], ["frustriert"], ["euphorisch"], ["müde"], ["unsicher"], ["diszipliniert"]]);
setValues(helper, "G2:G6", [["US-Aktie"], ["Forex"], ["Index"], ["Rohstoff"], ["Krypto"]]);
setValues(helper, "H2:H8", [["M1"], ["M5"], ["M15"], ["H1"], ["H4"], ["D1"], ["W1"]]);

// Kontoübersicht
setValues(overview, "A1:M1", [["Kontoübersicht"]]);
overview.getRange("A1:M1").merge();
styleTitle(overview.getRange("A1:M1"));
setValues(overview, "A3:M3", [["Monat", ...months]]);
styleHeader(overview.getRange("A3:M3"));
setValues(overview, "A4:A17", [
  ["Startkapital"], ["Ein-/Auszahlungen"], ["Tradeergebnisse"], ["Gebühren/Spread"],
  ["Nettoergebnis"], ["Endkapital"], ["Veränderung %"], ["Anzahl Trades"],
  ["Gewinntrades"], ["Verlusttrades"], ["Trefferquote"], ["Ø CRV geplant"],
  ["Regelverstöße"], ["Journal unvollständig"],
]);
styleHeader(overview.getRange("A4:A17"));
setValues(overview, "B4:M4", [Array(12).fill(10000)]);
setValues(overview, "B5:M5", [Array(12).fill(0)]);
styleInput(overview.getRange("B4:M5"));
setFormulas(overview, "B6:M17", [
  months.map((m, index) => `=SUMIFS(Journal!V$8:V$${maxJournalRow},${monthCriteria(index + 2)})`),
  months.map((m, index) => `=SUMIFS(Journal!W$8:W$${maxJournalRow},${monthCriteria(index + 2)})`),
  months.map((m, index) => {
    const col = columnName(index + 2);
    return `=${col}6-${col}7`;
  }),
  months.map((m, index) => {
    const col = columnName(index + 2);
    return `=${col}4+${col}5+${col}8`;
  }),
  months.map((m, index) => {
    const col = columnName(index + 2);
    return `=IF(${col}4=0,"",${col}8/${col}4)`;
  }),
  months.map((m, index) => `=COUNTIFS(${monthCriteria(index + 2)})`),
  months.map((m, index) => `=COUNTIFS(${monthCriteria(index + 2)},Journal!X$8:X$${maxJournalRow},">0")`),
  months.map((m, index) => `=COUNTIFS(${monthCriteria(index + 2)},Journal!X$8:X$${maxJournalRow},"<0")`),
  months.map((m, index) => {
    const col = columnName(index + 2);
    return `=IF(${col}11=0,"",${col}12/${col}11)`;
  }),
  months.map((m, index) => `=IFERROR(AVERAGEIFS(Journal!Z$8:Z$${maxJournalRow},${monthCriteria(index + 2)}),"")`),
  months.map((m, index) => `=COUNTIFS(${monthCriteria(index + 2)},Journal!AC$8:AC$${maxJournalRow},"Nein")`),
  months.map((m, index) => `=COUNTIFS(${monthCriteria(index + 2)},Journal!AQ$8:AQ$${maxJournalRow},"Nein")`),
]);
styleLocked(overview.getRange("B6:M17"));
overview.getRange("B4:M9").format.numberFormat = "#,##0.00";
overview.getRange("B10:M10").format.numberFormat = "0.00%";
overview.getRange("B11:M13").format.numberFormat = "0";
overview.getRange("B14:M14").format.numberFormat = "0.00%";
overview.getRange("B15:M15").format.numberFormat = "0.00";
overview.getRange("B16:M17").format.numberFormat = "0";
overview.getRange("A:A").format.columnWidthPx = 175;
overview.getRange("B:M").format.columnWidthPx = 105;

// Journal
setValues(journal, "A1:F1", [Array(6).fill("Detailliertes Trading-Journal")]);
journal.getRange("A1:F1").merge();
styleTitle(journal.getRange("A1:F1"));
setValues(journal, "A3:F3", [["Anzahl Trades", "Gewinntrades", "Verlusttrades", "Trefferquote", "Ø CRV geplant", "Profit Factor"]]);
styleHeader(journal.getRange("A3:F3"));
setFormulas(journal, "A4:F4", [[
  `=COUNTA(B8:B${maxJournalRow})`,
  `=COUNTIF(X8:X${maxJournalRow},">0")`,
  `=COUNTIF(X8:X${maxJournalRow},"<0")`,
  '=IF(A4=0,"",B4/A4)',
  `=IFERROR(AVERAGE(Z8:Z${maxJournalRow}),"")`,
  `=IFERROR(SUMIF(X8:X${maxJournalRow},">0",X8:X${maxJournalRow})/ABS(SUMIF(X8:X${maxJournalRow},"<0",X8:X${maxJournalRow})),"")`,
]]);
styleLocked(journal.getRange("A4:F4"));
setValues(journal, `A7:AQ7`, [headers]);
styleHeader(journal.getRange("A7:AQ7"));
const rows = maxJournalRow - 7;
const start = 8;
const end = start + rows - 1;
styleInput(journal.getRange(`B${start}:S${end}`));
styleInput(journal.getRange(`V${start}:W${end}`));
styleInput(journal.getRange(`AB${start}:AO${end}`));
styleLocked(journal.getRange(`A${start}:A${end}`));
styleLocked(journal.getRange(`T${start}:U${end}`));
styleLocked(journal.getRange(`X${start}:AA${end}`));
styleLocked(journal.getRange(`AP${start}:AQ${end}`));
journal.getRange(`B${start}:B${end}`).format.numberFormat = "@";
journal.getRange(`C${start}:D${end}`).format.numberFormat = "hh:mm";
journal.getRange(`O${start}:T${end}`).format.numberFormat = "#,##0.00";
journal.getRange(`U${start}:U${end}`).format.numberFormat = "0.00%";
journal.getRange(`V${start}:X${end}`).format.numberFormat = "#,##0.00";
journal.getRange(`Y${start}:Y${end}`).format.numberFormat = "0.00%";
journal.getRange(`Z${start}:AA${end}`).format.numberFormat = "0.00";
journal.getRange(`AP${start}:AP${end}`).format.numberFormat = "#,##0.00";
journal.getRange("D4:D4").format.numberFormat = "0.00%";
journal.getRange("E4:F4").format.numberFormat = "0.00";
journal.getRange("A:D").format.columnWidthPx = 105;
journal.getRange("E:E").format.columnWidthPx = 160;
journal.getRange("F:H").format.columnWidthPx = 90;
journal.getRange("I:N").format.columnWidthPx = 125;
journal.getRange("O:AA").format.columnWidthPx = 105;
journal.getRange("AB:AM").format.columnWidthPx = 180;
journal.getRange("AN:AO").format.columnWidthPx = 230;
journal.getRange("AP:AQ").format.columnWidthPx = 125;

const importedJournalRows = [];

try {
  const monthlyCsv = await fs.readFile(monthlyTradesPath, "utf8");
  const imported = parseCsv(monthlyCsv);
  for (const trade of imported) {
    const gross = num(trade.gross_profit);
    const net = num(trade.net_profit);
    const feeCost = gross != null && net != null && net <= gross ? gross - net : 0;
    const tradeResult = gross != null && net != null && net > gross ? net : gross;
    const effectiveDateTime = trade.exit_time || trade.entry_time;
    const missing = ["Setup-Kriterien", "SL", "TP", "Screenshots", "Emotionen"];
    if (!trade.entry_time || !trade.entry) missing.push("Entry aus Vorperiode");
    const sourceNote = trade.source_note ? `; Kommentar: ${trade.source_note}` : "";
    importedJournalRows.push({
      sortKey: `${dateOnly(effectiveDateTime)} ${timeOnly(effectiveDateTime)} ${trade.order_id}`,
      values: [
        dateOnly(effectiveDateTime), timeOnly(trade.entry_time), timeOnly(trade.exit_time),
        "GBE Monatsbericht / Review offen", trade.symbol, marketFor(trade.symbol), trade.direction,
        "", "", "", "", "", "", num(trade.qty), num(trade.entry), null,
        null, num(trade.exit), null, null, tradeResult,
        feeCost, null, null, null, null, "", "Nein",
        "SL/TP, Setup, Emotionen, Screenshots und Regelcheck fehlen",
        "Geschlossener Trade aus GBE-Monatsbericht vorhanden",
        `${missing.join(", ")} nicht dokumentiert`,
        `Import aus GBE-Monatsbericht (${trade.source_file}); Entry-Grund nachtragen`,
        "", "", "", "", "", "",
        `Quelle: ${trade.source_file}; Order ${trade.order_id}; Netto laut Bericht ${trade.net_profit}${sourceNote}`,
        "Setup vor Entry dokumentieren und Monatsbericht-Trade reviewen",
      ],
    });
  }
} catch (error) {
  console.log(`No monthly statement import used: ${error.message}`);
}

try {
  const tradeCsv = await fs.readFile(reconstructedTradesPath, "utf8");
  const imported = parseCsv(tradeCsv);
  for (const trade of imported) {
    const commissionAndSwap = Math.abs((num(trade.commission) ?? 0) + (num(trade.swap) ?? 0));
    const plannedCrv = num(trade.recorded_crv);
    importedJournalRows.push({
      sortKey: `${dateOnly(trade.entry_time)} ${timeOnly(trade.entry_time)} ${trade.symbol}`,
      values: [
        dateOnly(trade.entry_time), timeOnly(trade.entry_time), timeOnly(trade.exit_time),
        "TradingView/GBE Orderverlauf / Review offen", trade.symbol, marketFor(trade.symbol), trade.direction,
        "", "", "", "", "", "", num(trade.qty), num(trade.entry), num(trade.recorded_sl),
        num(trade.recorded_tp), num(trade.exit), null, null, num(trade.gross_profit),
        commissionAndSwap, null, null, plannedCrv, null, "", "Nein",
        "Setup, Emotionen, Screenshots und Regelcheck fehlen", "SL/TP im Export vorhanden",
        "Setup-Kriterien nicht dokumentiert", "Import aus TradingView/GBE Orderverlauf; Entry-Grund nachtragen",
        "", "", "", "", "", "", "Bitte Trade nach TradingFreaks-Regeln reviewen",
        "Setup vor Entry dokumentieren",
      ],
    });
  }
} catch (error) {
  console.log(`No reconstructed trade import used: ${error.message}`);
}

importedJournalRows.sort((a, b) => a.sortKey.localeCompare(b.sortKey));
const journalRows = importedJournalRows.slice(0, rows).map((row) => row.values);
if (journalRows.length) {
  setValues(journal, `B${start}:AO${start + journalRows.length - 1}`, journalRows);
}
applyJournalFormulas();
journal.getRange(`B${start}:B${end}`).format.numberFormat = "@";
journal.getRange(`C${start}:D${end}`).format.numberFormat = "hh:mm";
journal.getRange(`O${start}:T${end}`).format.numberFormat = "#,##0.00";
journal.getRange(`U${start}:U${end}`).format.numberFormat = "0.00%";
journal.getRange(`V${start}:X${end}`).format.numberFormat = "#,##0.00";
journal.getRange(`Y${start}:Y${end}`).format.numberFormat = "0.00%";
journal.getRange(`Z${start}:AA${end}`).format.numberFormat = "0.00";
journal.getRange(`AP${start}:AP${end}`).format.numberFormat = "#,##0.00";

// Monatsauswertung
setValues(monthly, "A1:J1", [Array(10).fill("Monatsauswertung")]);
monthly.getRange("A1:J1").merge();
styleTitle(monthly.getRange("A1:J1"));
setValues(monthly, "A3:J3", [["Monat", "Anzahl Trades", "Gewinntrades", "Verlusttrades", "Trefferquote", "Tradeergebnisse", "Gebühren/Spread", "Nettoergebnis", "Regelverstöße", "Journal unvollständig"]]);
styleHeader(monthly.getRange("A3:J3"));
setValues(monthly, `A4:A${monthlyPeriods.length + 3}`, monthlyPeriods.map((period) => [period]));
setFormulas(monthly, `B4:J${monthlyPeriods.length + 3}`, monthlyPeriods.map((period, index) => {
  const row = index + 4;
  const startDate = `${period}-01`;
  const endDate = `${nextPeriod(period)}-01`;
  const criteria = `Journal!B$8:B$${maxJournalRow},">=${startDate}",Journal!B$8:B$${maxJournalRow},"<${endDate}"`;
  return [
    `=COUNTIFS(${criteria})`,
    `=COUNTIFS(${criteria},Journal!X$8:X$${maxJournalRow},">0")`,
    `=COUNTIFS(${criteria},Journal!X$8:X$${maxJournalRow},"<0")`,
    `=IF(B${row}=0,"",C${row}/B${row})`,
    `=SUMIFS(Journal!V$8:V$${maxJournalRow},${criteria})`,
    `=SUMIFS(Journal!W$8:W$${maxJournalRow},${criteria})`,
    `=SUMIFS(Journal!X$8:X$${maxJournalRow},${criteria})`,
    `=COUNTIFS(${criteria},Journal!AC$8:AC$${maxJournalRow},"Nein")`,
    `=COUNTIFS(${criteria},Journal!AQ$8:AQ$${maxJournalRow},"Nein")`,
  ];
}));
styleLocked(monthly.getRange(`B4:J${monthlyPeriods.length + 3}`));
monthly.getRange("A:A").format.columnWidthPx = 105;
monthly.getRange("B:D").format.columnWidthPx = 105;
monthly.getRange("E:E").format.columnWidthPx = 110;
monthly.getRange("F:H").format.columnWidthPx = 130;
monthly.getRange("I:J").format.columnWidthPx = 135;
monthly.getRange(`E4:E${monthlyPeriods.length + 3}`).format.numberFormat = "0.00%";
monthly.getRange(`F4:H${monthlyPeriods.length + 3}`).format.numberFormat = "#,##0.00";

// Wochenreview
setValues(review, "A1:H1", [["Wochenreview"]]);
review.getRange("A1:H1").merge();
styleTitle(review.getRange("A1:H1"));
setValues(review, "A3:H3", [["Woche ab", "Anzahl Trades", "Netto", "Trefferquote", "Regelverstöße", "Journal vollständig", "Hauptfehler", "Fokus nächste Woche"]]);
styleHeader(review.getRange("A3:H3"));
setValues(review, "A4:A15", Array.from({ length: 12 }, () => [""]));
styleInput(review.getRange("A4:A15"));
setFormulas(review, "B4:F15", Array.from({ length: 12 }, (_, i) => {
  const row = i + 4;
  return [
    `=IF(A${row}="","",COUNTIFS(Journal!B:B,">="&A${row},Journal!B:B,"<"&A${row}+7))`,
    `=IF(A${row}="","",SUMIFS(Journal!X:X,Journal!B:B,">="&A${row},Journal!B:B,"<"&A${row}+7))`,
    `=IF(B${row}=0,"",COUNTIFS(Journal!B:B,">="&A${row},Journal!B:B,"<"&A${row}+7,Journal!X:X,">0")/B${row})`,
    `=IF(A${row}="","",COUNTIFS(Journal!B:B,">="&A${row},Journal!B:B,"<"&A${row}+7,Journal!AC:AC,"Nein"))`,
    `=IF(B${row}=0,"",COUNTIFS(Journal!B:B,">="&A${row},Journal!B:B,"<"&A${row}+7,Journal!AQ:AQ,"Ja")/B${row})`,
  ];
}));
styleLocked(review.getRange("B4:F15"));
styleInput(review.getRange("G4:H15"));

// Psychologie
setValues(psyche, "A1:I1", [["Psychologie & Disziplin"]]);
psyche.getRange("A1:I1").merge();
styleTitle(psyche.getRange("A1:I1"));
setValues(psyche, "A3:I3", [["Datum", "Glücklich", "Gestresst", "Wach", "Entmutigt", "Nervös/Frustriert", "Balance/Kontrolle", "Impulsivität", "Trading Pause empfohlen"]]);
styleHeader(psyche.getRange("A3:I3"));
styleInput(psyche.getRange("A4:H370"));
setFormulas(psyche, "I4:I370", Array.from({ length: 367 }, (_, i) => {
  const r = i + 4;
  return [`=IF(A${r}="","",IF(OR(C${r}>=4,E${r}>=4,F${r}>=4,H${r}>=4,G${r}<=2),"Ja","Nein"))`];
}));
styleLocked(psyche.getRange("I4:I370"));

// Setups
setValues(setupSheet, "A1:H1", [["Setup-Regelwerk"]]);
setupSheet.getRange("A1:H1").merge();
styleTitle(setupSheet.getRange("A1:H1"));
setValues(setupSheet, "A3:H3", [["Setup", "Markt", "Pflichtkriterien", "Entry", "SL", "TP/Exit", "Nicht handeln wenn", "Journal-Fokus"]]);
styleHeader(setupSheet.getRange("A3:H3"));
setValues(setupSheet, "A4:H15", [
  ["US Newstrade Breakout", "US-Aktie", "News, >3%, Momentum, VWAP-Seite, enge Konsolidierung, RVOL >1,5", "Breakout nahe Level", "Lokale Struktur", "CRV >= 1:1, intraday schließen", "Mixed News, Volatilität statt Momentum, tiefe Korrektur", "News, RVOL, VWAP, Korrektur, Screenshot"],
  ["US Newstrade Reversal", "US-Aktie", "News, VWAP-Abstand, Boden/Top, Entry-Signal", "Reversal in Richtung VWAP/News", "Lokale Struktur", "VWAP/Level, CRV >= 1:1", "Keine Bodenbildung, Hoffnungseinstieg", "VWAP-Abstand, Signal, Emotion"],
  ["Reversal ohne News", "US-Aktie", "Keine News, VWAP-Abstand, Fib, EMA9, Folgekerze", "Mean-Reversion-Signal", "Lokal tief/hoch", "50er Fib oder VWAP", "News, Volumenhinweis, nach 20:00", "Fib-Level, EMA9, Uhrzeit"],
  ["Rectangle", "US-Aktie", "Momentum, max. 1/3 Korrektur, 6 Kerzen, horizontal", "Stop über/unter Range", "Gegenseite Range", "CRV 1:1 oder Trailing", "Flagge, Dreieck, unklare Range", "Range-Kanten, Touchpoints"],
  ["Vorbörsliches Hoch/Tief", "US-Aktie", "News, >3%, Opening Drive, Level bis 15:25", "Breakout Premarket Level", "Lokale Struktur", "CRV ca. 1:1", "Keine News, kein Drive, Entry weit weg", "Premarket Level, Entry-Nähe"],
  ["Forex Wirtschaftsdaten", "Forex", "Event, klare Überraschung, einheitliche Daten, >20 Pips Momentum", "Momentum oder Pullback", "20-50 Pips", "CRV ca. 1:1", "Gemischte Daten, Vorposition, beide Stopps", "Event, Daten, Momentum"],
  ["FX Trendlinien", "Forex", "H4+, 2 Punkte, dritter Touch, kein Event", "Limit 5-10 Pips vor Linie", "20-50 Pips", "CRV ca. 1:1", "Frische News, Gegensentiment, hohe Kosten", "Trendlinie, Touchcount"],
  ["DAX Abpraller", "Index", "H4/D1/W1 Zone, Kalender ok, technische Idee", "10-15 Punkte vor Zone", "Außerhalb Zone", "50/100/300 Punkte je Stil", "Risikoevent, schwache Zone", "Zone, Screenshot, Tests"],
  ["SR Reversal", "FX/Index", "H4/D1/W1 Zone, 24h kein Event", "Limit vor Zone", "20-50 Pips / 50-200 Punkte", "CRV 1:1", "Event, Zone nicht stark", "Zone, Entfernung, Risiko"],
  ["52-Wochen Hoch", "Aktie", "Starker Kontext, Liquidität, klares Level", "Breakout/Retest", "Struktur", "Plan-Level", "Illiquide, kein Momentum", "Level, Volumen"],
  ["IPO", "Aktie", "Liquidität, News/Story, klare Struktur", "Setup-spezifisch", "Struktur", "Plan-Level", "Volatilität ohne Setup", "Story, Struktur"],
  ["Platzhalter", "-", "-", "-", "-", "-", "-", "-"],
]);
styleInput(setupSheet.getRange("A4:H15"));

// Basic widths and panes
for (const sheet of [overview, journal, monthly, review, psyche, setupSheet, helper]) {
  sheet.getRange("A:AZ").format.font.name = "Aptos";
}
journal.freezePanes.freezeRows(7);
overview.freezePanes.freezeRows(3);
monthly.freezePanes.freezeRows(3);
review.freezePanes.freezeRows(3);
psyche.freezePanes.freezeRows(3);
setupSheet.freezePanes.freezeRows(3);

await fs.mkdir(outputDir, { recursive: true });
const output = await SpreadsheetFile.exportXlsx(workbook);
await output.save(outputPath);
console.log(outputPath);
