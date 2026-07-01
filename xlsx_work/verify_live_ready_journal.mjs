import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";

const path = "../outputs/trading_journal_tf/TradingFreaks_Live_Ready_Journal_Codex.xlsx";
const workbook = await SpreadsheetFile.importXlsx(await FileBlob.load(path));

for (const range of [
  "Live_Cockpit!A1:H11",
  "Trade_Plan!A1:D30",
  "Live_Journal!A1:AO12",
  "Risk_Settings!A1:D15",
  "Backtest_Insights!A1:H15",
  "Import_Review!A1:P12",
]) {
  const inspected = await workbook.inspect({
    kind: "table",
    range,
    include: "values,formulas",
    tableMaxRows: 35,
    tableMaxCols: 45,
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
  ["Live_Cockpit", "A1:H14"],
  ["Trade_Plan", "A1:D30"],
  ["Live_Journal", "A1:AO18"],
  ["Backtest_Insights", "A1:H16"],
  ["Import_Review", "A1:P18"],
]) {
  const image = await workbook.render({ sheetName, range, scale: 1 });
  console.log(`rendered ${sheetName}: ${image.size ?? "ok"}`);
}
