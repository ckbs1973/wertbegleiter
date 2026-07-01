import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";

const files = [
  "/Volumes/NAS-Koronna/Chris/WertBegleiter/TradingFreaks/Schulungsunterlagen/Trading-Journal-TF-Light-V1.02(1).xlsx",
  "/Volumes/NAS-Koronna/Chris/WertBegleiter/TradingFreaks/Schulungsunterlagen/Trading-Journal-TF-V2.21-rotgruen.xlsx",
];

for (const file of files) {
  console.log(`\n=== ${file} ===`);
  const input = await FileBlob.load(file);
  const workbook = await SpreadsheetFile.importXlsx(input);
  console.log((await workbook.inspect({ kind: "workbook", summary: "workbook summary" })).ndjson);
  for (const sheet of workbook.worksheets.items.slice(0, 12)) {
    console.log(`--- SHEET ${sheet.name} ---`);
    const inspected = await workbook.inspect({
      kind: "table",
      range: `${sheet.name}!A1:Z40`,
      include: "values,formulas",
      tableMaxRows: 40,
      tableMaxCols: 26,
    });
    console.log(inspected.ndjson);
  }
}
