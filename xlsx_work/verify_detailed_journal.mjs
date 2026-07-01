import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";

const path = "../outputs/trading_journal_tf/TradingFreaks_Detailed_Journal_Codex.xlsx";
const input = await FileBlob.load(path);
const workbook = await SpreadsheetFile.importXlsx(input);

for (const range of [
  "Kontoübersicht!A1:M17",
  "Journal!A1:AQ12",
  "Monatsauswertung!A1:J12",
  "Wochenreview!A1:H8",
  "Psychologie!A1:I8",
  "Setups!A1:H10",
]) {
  const inspected = await workbook.inspect({
    kind: "table",
    range,
    include: "values,formulas",
    tableMaxRows: 20,
    tableMaxCols: 50,
  });
  console.log(`\n--- ${range} ---`);
  console.log(inspected.ndjson);
}

const errors = await workbook.inspect({
  kind: "match",
  searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A",
  options: { useRegex: true, maxResults: 300 },
  summary: "formula error scan",
});
console.log("\n--- ERRORS ---");
console.log(errors.ndjson);

for (const [sheetName, range] of [
  ["Kontoübersicht", "A1:M20"],
  ["Journal", "A1:AQ18"],
  ["Monatsauswertung", "A1:J13"],
  ["Wochenreview", "A1:H15"],
  ["Psychologie", "A1:I15"],
  ["Setups", "A1:H15"],
]) {
  const image = await workbook.render({ sheetName, range, scale: 1 });
  console.log(`rendered ${sheetName}: ${image.size ?? "ok"}`);
}
