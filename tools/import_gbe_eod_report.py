from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from trading_freaks.journal.gbe_report_import import (  # noqa: E402
    journal_rows_from_report,
    net_profit_total,
    parse_gbe_report_pdf,
    write_journal_import_files,
)


def safe_stem(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", value).strip("_").lower()


def default_output_prefix(pdf_path: Path, report_date: str | None) -> Path:
    date_part = report_date or "unknown-date"
    return ROOT / "reports" / f"gbe_eod_{date_part}_{safe_stem(pdf_path.stem)}_journal_import"


def main() -> None:
    parser = argparse.ArgumentParser(description="Import a GBE End of Day PDF report into journal-ready CSV/JSON files.")
    parser.add_argument("pdf", type=Path, help="Path to the GBE End of Day PDF report")
    parser.add_argument("--output-prefix", type=Path, help="Output path without extension")
    args = parser.parse_args()

    report = parse_gbe_report_pdf(args.pdf)
    rows = journal_rows_from_report(report)
    report_date = rows[0]["trade_date_berlin"] if rows else None
    output_prefix = args.output_prefix or default_output_prefix(args.pdf, report_date)
    csv_path, json_path = write_journal_import_files(report, output_prefix)

    print(f"Imported report: {args.pdf}")
    print(f"Closed trades: {len(report.trades)}")
    print(f"Net P/L: {net_profit_total(report.trades)} {report.summary.currency}")
    print(f"Balance: {report.summary.balance} {report.summary.currency}")
    print(f"CSV: {csv_path}")
    print(f"JSON: {json_path}")
    print("Disclaimer: Information und Journal-Unterstuetzung, keine Anlageberatung oder Orderfreigabe.")


if __name__ == "__main__":
    main()
