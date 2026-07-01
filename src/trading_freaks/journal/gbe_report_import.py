"""GBE broker report import helpers for journal enrichment.

The importer translates broker statements into objective journal facts. It does
not infer setup quality, trade approval or investment advice.
"""

from __future__ import annotations

import csv
import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Iterable, Sequence
from zoneinfo import ZoneInfo


ORDER_ID_RE = re.compile(r"^W\d+$")
NUMBER_RE = re.compile(r"^-?\d+(?:\.\d+)?$")
BERLIN = ZoneInfo("Europe/Berlin")
UTC = ZoneInfo("UTC")


@dataclass(frozen=True)
class GBEClosedTrade:
    source_file: str
    order_id: str
    symbol: str
    volume: Decimal
    direction: str
    entry_time_utc: datetime
    entry_time_berlin: datetime
    entry: Decimal
    exit_time_utc: datetime
    exit_time_berlin: datetime
    exit: Decimal
    commission: Decimal
    swap: Decimal
    gross_profit: Decimal
    net_profit: Decimal
    holding_minutes: Decimal
    market: str
    setup_candidate: str
    review_flags: tuple[str, ...]


@dataclass(frozen=True)
class GBEAccountSummary:
    source_file: str
    account_no: str
    account_name: str
    snapshot_utc: datetime | None
    currency: str
    closed_trade_pl: Decimal
    net_floating_pl: Decimal
    equity: Decimal
    balance: Decimal
    commissions: Decimal
    swap: Decimal
    inferred_start_balance: Decimal | None


@dataclass(frozen=True)
class GBEReport:
    source_file: str
    trades: tuple[GBEClosedTrade, ...]
    summary: GBEAccountSummary
    information_only: bool = True


def parse_decimal(value: str) -> Decimal:
    clean = value.strip().replace(" ", "")
    if not NUMBER_RE.match(clean):
        raise ValueError(f"Not a numeric value: {value!r}")
    return Decimal(clean)


def decimal_string(value: Decimal | None) -> str:
    if value is None:
        return ""
    return f"{value:.2f}"


def read_pdf_lines(path: Path) -> list[str]:
    from pypdf import PdfReader

    reader = PdfReader(str(path))
    text = "\n".join(page.extract_text() or "" for page in reader.pages)
    return [line.strip() for line in text.splitlines() if line.strip()]


def _value_after_label(lines: Sequence[str], label: str, default: str = "") -> str:
    try:
        index = lines.index(label)
    except ValueError:
        return default
    return lines[index + 1] if index + 1 < len(lines) else default


def _parse_snapshot(value: str) -> datetime | None:
    if not value:
        return None
    normalized = value.replace(" UTC +0", "")
    return datetime.strptime(normalized, "%d/%m/%Y %H:%M:%S").replace(tzinfo=UTC)


def _parse_utc_datetime(value: str) -> datetime:
    return datetime.strptime(value, "%Y-%m-%d %H:%M:%S").replace(tzinfo=UTC)


def _market_and_setup(symbol: str) -> tuple[str, str]:
    upper = symbol.upper()
    if upper in {"DE40", "DAX", "GER40"}:
        return "index", "DAX Abpraller / ORB/SR manuell pruefen"
    if upper in {"US500", "USTEC", "DJ30"}:
        return "index", "SR Reversal / Index-Kontext manuell pruefen"
    if upper in {"XAGUSD", "XAUUSD", "XAUEUR"}:
        return "commodity", "SR Reversal / Metallblock manuell pruefen"
    if upper in {"UKOIL", "USOIL", "WTI", "BRENT"}:
        return "commodity", "SR Reversal / Oel-Kontext manuell pruefen"
    if upper.endswith("USD") and len(upper) == 6:
        return "forex", "FX Setup manuell pruefen"
    return "watchlist", "Setup manuell klassifizieren"


def _summary_from_lines(lines: Sequence[str], source_file: str) -> GBEAccountSummary:
    closed_pl = parse_decimal(_value_after_label(lines, "Closed Trade P/L:", "0.00"))
    balance = parse_decimal(_value_after_label(lines, "Balance:", "0.00"))
    net_floating = parse_decimal(_value_after_label(lines, "Net Floating P/L:", "0.00"))
    inferred_start_balance = balance - closed_pl if balance else None
    return GBEAccountSummary(
        source_file=source_file,
        account_no=_value_after_label(lines, "A/C No:", ""),
        account_name=_value_after_label(lines, "Name:", ""),
        snapshot_utc=_parse_snapshot(_value_after_label(lines, "Snapshot:", "")),
        currency=_value_after_label(lines, "Currency:", ""),
        closed_trade_pl=closed_pl,
        net_floating_pl=net_floating,
        equity=parse_decimal(_value_after_label(lines, "Equity:", "0.00")),
        balance=balance,
        commissions=parse_decimal(_value_after_label(lines, "Commissions(-ve):", "0.00")),
        swap=parse_decimal(_value_after_label(lines, "Swap:", "0.00")),
        inferred_start_balance=inferred_start_balance,
    )


def _review_flags(symbol: str, net_profit: Decimal, summary: GBEAccountSummary) -> tuple[str, ...]:
    flags = [
        "Brokerreport enthaelt kein SL/TP/CRV; Plan, Setup-Kriterien und Screenshots manuell ergaenzen",
    ]
    if summary.inferred_start_balance and summary.inferred_start_balance > 0:
        pnl_percent = abs(net_profit / summary.inferred_start_balance * Decimal("100"))
        if net_profit < 0 and pnl_percent > Decimal("1"):
            flags.append("Verlust groesser als 1 Prozent des abgeleiteten Tagesstartkapitals")
        if symbol.upper() in {"XAGUSD", "XAUUSD", "XAUEUR"} and pnl_percent > Decimal("10"):
            flags.append("Metall-Exposure und Positionsgroesse zwingend reviewen")
    return tuple(flags)


def parse_gbe_report_lines(lines: Sequence[str], source_file: str) -> GBEReport:
    if "Closed Trades:" not in lines:
        raise ValueError("Report format unsupported: missing 'Closed Trades:'")

    summary = _summary_from_lines(lines, source_file)
    header_index = lines.index("Profit", lines.index("Closed Trades:"))
    summary_index = lines.index("Summary", header_index)
    trade_lines = list(lines[header_index + 1 : summary_index])
    order_positions = [index for index, line in enumerate(trade_lines) if ORDER_ID_RE.match(line)]
    trades: list[GBEClosedTrade] = []

    for index, start in enumerate(order_positions):
        end = order_positions[index + 1] if index + 1 < len(order_positions) else len(trade_lines)
        chunk = trade_lines[start:end]
        if len(chunk) != 12:
            raise ValueError(f"Expected 12 trade fields for {chunk[0]}, got {len(chunk)}: {chunk}")

        order_id, symbol, volume, side, open_time, open_price, close_time, close_price, commission, swap, gross, net = chunk
        entry_utc = _parse_utc_datetime(open_time)
        exit_utc = _parse_utc_datetime(close_time)
        market, setup_candidate = _market_and_setup(symbol)
        net_profit = parse_decimal(net)
        trades.append(
            GBEClosedTrade(
                source_file=source_file,
                order_id=order_id,
                symbol=symbol,
                volume=parse_decimal(volume),
                direction="Long" if side.upper() == "BUY" else "Short",
                entry_time_utc=entry_utc,
                entry_time_berlin=entry_utc.astimezone(BERLIN),
                entry=parse_decimal(open_price),
                exit_time_utc=exit_utc,
                exit_time_berlin=exit_utc.astimezone(BERLIN),
                exit=parse_decimal(close_price),
                commission=parse_decimal(commission),
                swap=parse_decimal(swap),
                gross_profit=parse_decimal(gross),
                net_profit=net_profit,
                holding_minutes=Decimal(str(round((exit_utc - entry_utc).total_seconds() / 60, 2))),
                market=market,
                setup_candidate=setup_candidate,
                review_flags=_review_flags(symbol, net_profit, summary),
            )
        )

    return GBEReport(source_file=source_file, trades=tuple(trades), summary=summary)


def parse_gbe_report_pdf(path: Path) -> GBEReport:
    return parse_gbe_report_lines(read_pdf_lines(path), path.name)


def journal_rows_from_report(report: GBEReport) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    start_balance = report.summary.inferred_start_balance
    for trade in report.trades:
        result_percent_of_inferred_day_start = ""
        if start_balance and start_balance > 0:
            result_percent_of_inferred_day_start = decimal_string(trade.net_profit / start_balance * Decimal("100"))

        rows.append(
            {
                "source_file": trade.source_file,
                "account_no": report.summary.account_no,
                "currency": report.summary.currency,
                "report_snapshot_utc": report.summary.snapshot_utc.isoformat() if report.summary.snapshot_utc else "",
                "trade_date_berlin": trade.entry_time_berlin.date().isoformat(),
                "trade_time_berlin": trade.entry_time_berlin.time().isoformat(timespec="seconds"),
                "entry_time_utc": trade.entry_time_utc.isoformat(),
                "exit_time_utc": trade.exit_time_utc.isoformat(),
                "entry_time_berlin": trade.entry_time_berlin.isoformat(),
                "exit_time_berlin": trade.exit_time_berlin.isoformat(),
                "holding_minutes": decimal_string(trade.holding_minutes),
                "market": trade.market,
                "symbol": trade.symbol,
                "setup": trade.setup_candidate,
                "direction": trade.direction,
                "trading_style": "manuell nachtragen",
                "timeframe_context": "manuell nachtragen",
                "timeframe_entry": "manuell nachtragen",
                "news_catalyst": "manuell pruefen",
                "economic_event": "manuell pruefen",
                "sentiment": "manuell nachtragen",
                "entry": str(trade.entry),
                "stop_loss": "",
                "take_profit": "",
                "position_size": str(trade.volume),
                "risk_amount": "",
                "result_percent_inferred_from_day_start": result_percent_of_inferred_day_start,
                "planned_crv": "",
                "realized_r": "",
                "result_money": decimal_string(trade.net_profit),
                "gross_profit": decimal_string(trade.gross_profit),
                "commission": decimal_string(trade.commission),
                "swap": decimal_string(trade.swap),
                "slippage": "",
                "rule_compliant": "unklar",
                "violated_rule": "offen: SL/TP/CRV/Setup/Screenshots aus TradingView/Journalkontext nachtragen",
                "criteria_met": "",
                "criteria_failed": "Brokerreport enthaelt keine Setup-Kriterien",
                "screenshot_before": "",
                "screenshot_after": "",
                "emotion_before": "",
                "emotion_during": "",
                "emotion_after": "",
                "confidence_level": "",
                "review": " | ".join(trade.review_flags),
                "improvement_next_trade": "Tradeplan, Risiko, SL/TP, Setup-Kriterien und Screenshots nachtragen; danach erst Prozessqualitaet bewerten.",
                "information_only": "true",
            }
        )
    return rows


def report_to_dict(report: GBEReport) -> dict[str, object]:
    def convert(value: object) -> object:
        if isinstance(value, Decimal):
            return str(value)
        if isinstance(value, datetime):
            return value.isoformat()
        if isinstance(value, tuple):
            return [convert(item) for item in value]
        if isinstance(value, dict):
            return {key: convert(item) for key, item in value.items()}
        return value

    return convert(asdict(report))  # type: ignore[return-value]


def write_journal_import_files(report: GBEReport, output_prefix: Path) -> tuple[Path, Path]:
    rows = journal_rows_from_report(report)
    csv_path = output_prefix.with_suffix(".csv")
    json_path = output_prefix.with_suffix(".json")
    csv_path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = list(rows[0].keys()) if rows else []
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    json_path.write_text(
        json.dumps(
            {
                "disclaimer": "Information und Journal-Unterstuetzung, keine Anlageberatung oder Orderfreigabe.",
                "report": report_to_dict(report),
                "journal_rows": rows,
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return csv_path, json_path


def net_profit_total(trades: Iterable[GBEClosedTrade]) -> Decimal:
    total = Decimal("0")
    for trade in trades:
        total += trade.net_profit
    return total
