from __future__ import annotations

import csv
import json
import re
from decimal import Decimal
from pathlib import Path

from pypdf import PdfReader


SOURCE_DIR = Path("/Volumes/NAS-Koronna/Chris/WertBegleiter/GBE Brokers/Monatsberichte")
OUTPUT_CSV = Path("../reports/gbe_monthly_closed_trades.csv")
SUMMARY_JSON = Path("../reports/gbe_monthly_closed_trades_summary.json")

ORDER_ID_RE = re.compile(r"^W\d+$")
NUMBER_RE = re.compile(r"^-?\d+(?:\.\d+)?$")
OLD_DEAL_RE = re.compile(
    r"^(?P<time>\d{4}\.\d{2}\.\d{2} \d{2}:\d{2}:\d{2})"
    r"(?P<ticket>\d+)"
    r"(?P<side>buy|sell)\s*"
    r"(?P<size>\d+(?:\.\d+)?K?)"
    r"(?P<body>.*)$"
)
OLD_ORDER_ID_RE = re.compile(r"^\d{4}\.\d{2}\.\d{2} \d{2}:\d{2}:\d{2}(?P<order>\d+)(?=buy|sell)")
OLD_MONEY_RE = re.compile(r"-?\d+(?: \d{3})*\.\d{2}")


def clean_lines(path: Path) -> list[str]:
    reader = PdfReader(str(path))
    text = "\n".join(page.extract_text() or "" for page in reader.pages)
    return [line.strip() for line in text.splitlines() if line.strip()]


def parse_number(value: str) -> Decimal:
    value = value.replace(" ", "")
    if not NUMBER_RE.match(value):
        raise ValueError(f"Not a numeric value: {value!r}")
    return Decimal(value)


def decimal_string(value: Decimal) -> str:
    return f"{value:.2f}"


def parse_size(value: str) -> Decimal:
    if value.endswith("K"):
        return parse_number(value[:-1]) * Decimal("1000")
    return parse_number(value)


def old_datetime(value: str) -> str:
    return value.replace(".", "-", 2)


def find_old_order_ids(lines: list[str]) -> list[str]:
    order_ids: list[str] = []
    for line in lines:
        match = OLD_ORDER_ID_RE.match(line)
        if match:
            order_ids.append(match.group("order"))
    return sorted(set(order_ids), key=len, reverse=True)


def split_old_body(body: str, order_ids: list[str]) -> tuple[str, str, str, str]:
    for order_id in order_ids:
        pos = body.find(order_id)
        if pos > 0:
            prefix = body[:pos]
            tail = body[pos + len(order_id) :]
            match = re.match(r"^(?P<symbol>[A-Za-z0-9.]+?)(?P<price>-?\d+(?:\.\d{2,5}))$", prefix)
            if not match:
                raise ValueError(f"Could not split symbol/price in old deal body: {body!r}")
            return match.group("symbol"), match.group("price"), order_id, tail
    raise ValueError(f"Could not find order id in old deal body: {body!r}")


def parse_old_money_tail(tail: str) -> tuple[Decimal, Decimal, Decimal, Decimal]:
    values = [parse_number(match.group(0)) for match in OLD_MONEY_RE.finditer(tail)]
    if len(values) < 4:
        raise ValueError(f"Expected four money values in old deal tail: {tail!r}")
    return tuple(values[-4:])  # type: ignore[return-value]


def parse_old_closed_pl(lines: list[str]) -> Decimal | None:
    for line in lines:
        if line.startswith("Closed P/L:"):
            return parse_number(line.split(":", 1)[1])
    return None


def parse_old_statement(path: Path) -> tuple[list[dict[str, str]], dict[str, str]]:
    lines = clean_lines(path)
    deals_index = lines.index("Deals:")
    positions_index = lines.index("Positions:")
    deal_lines = lines[deals_index + 2 : positions_index]
    order_ids = find_old_order_ids(lines[:deals_index])

    open_positions: dict[tuple[str, str], list[dict[str, object]]] = {}
    records: list[dict[str, str]] = []
    commission_total = Decimal("0")
    fee_total = Decimal("0")
    swap_total = Decimal("0")
    gross_total = Decimal("0")
    net_total = Decimal("0")

    for line in deal_lines:
        match = OLD_DEAL_RE.match(line)
        if not match:
            continue

        symbol, price_text, order_id, tail = split_old_body(match.group("body"), order_ids)
        entry_match = re.search(r"(in|out)", tail)
        if not entry_match:
            continue
        entry_type = entry_match.group(1)
        comment = tail[: entry_match.start()].strip()
        money_tail = tail[entry_match.end() :]
        commission, fee, swap, profit = parse_old_money_tail(money_tail)
        net_profit = commission + fee + swap + profit

        side = match.group("side").lower()
        size = parse_size(match.group("size"))
        price = parse_number(price_text)
        event_time = old_datetime(match.group("time"))

        if entry_type == "in":
            open_positions.setdefault((symbol, side), []).append({
                "time": event_time,
                "price": price,
                "size": size,
                "order_id": order_id,
            })
            continue

        commission_total += commission
        fee_total += fee
        swap_total += swap
        gross_total += profit
        net_total += net_profit

        opening_side = "buy" if side == "sell" else "sell"
        queue = open_positions.get((symbol, opening_side), [])
        matched = queue[0] if queue else None
        if matched:
            remaining = matched["size"] - size  # type: ignore[operator]
            if remaining <= 0:
                queue.pop(0)
            else:
                matched["size"] = remaining

        records.append(
            {
                "source_file": path.name,
                "order_id": order_id,
                "symbol": symbol,
                "qty": decimal_string(size),
                "direction": "Long" if opening_side == "buy" else "Short",
                "entry_time": str(matched["time"]) if matched else "",
                "entry": decimal_string(matched["price"]) if matched else "",
                "exit_time": event_time,
                "exit": decimal_string(price),
                "commission": decimal_string(commission + fee),
                "swap": decimal_string(swap),
                "gross_profit": decimal_string(profit),
                "net_profit": decimal_string(net_profit),
                "source_note": comment,
            }
        )

    closed_pl = parse_old_closed_pl(lines)
    summary = {
        "source_file": path.name,
        "closed_trades": str(len(records)),
        "summary_commission": decimal_string(commission_total + fee_total),
        "summary_swap": decimal_string(swap_total),
        "summary_gross_profit": decimal_string(gross_total),
        "summary_net_profit": decimal_string(closed_pl) if closed_pl is not None else decimal_string(net_total),
        "calculated_commission": decimal_string(commission_total + fee_total),
        "calculated_swap": decimal_string(swap_total),
        "calculated_gross_profit": decimal_string(gross_total),
        "calculated_net_profit": decimal_string(net_total),
    }
    return records, summary


def parse_closed_trades(path: Path) -> tuple[list[dict[str, str]], dict[str, str]]:
    lines = clean_lines(path)
    if "Closed Trades:" not in lines:
        return parse_old_statement(path)

    closed_index = lines.index("Closed Trades:")
    header_index = lines.index("Order ID", closed_index)
    profit_header_index = lines.index("Profit", header_index)
    summary_index = lines.index("Summary", profit_header_index)
    trade_lines = lines[profit_header_index + 1 : summary_index]
    summary_values = lines[summary_index + 1 : summary_index + 5]

    records: list[dict[str, str]] = []
    order_positions = [i for i, line in enumerate(trade_lines) if ORDER_ID_RE.match(line)]

    for index, start in enumerate(order_positions):
        end = order_positions[index + 1] if index + 1 < len(order_positions) else len(trade_lines)
        chunk = trade_lines[start:end]
        if len(chunk) != 12:
            raise ValueError(f"{path.name}: expected 12 fields for {chunk[0]}, got {len(chunk)}: {chunk}")

        order_id, instrument, volume, side, open_time, open_price, close_time, close_price, commission, swap, gross_profit, net_profit = chunk
        records.append(
            {
                "source_file": path.name,
                "order_id": order_id,
                "symbol": instrument,
                "qty": volume,
                "direction": "Long" if side.upper() == "BUY" else "Short",
                "entry_time": open_time,
                "entry": open_price,
                "exit_time": close_time,
                "exit": close_price,
                "commission": commission,
                "swap": swap,
                "gross_profit": gross_profit,
                "net_profit": net_profit,
                "source_note": "",
            }
        )

    summary = {
        "source_file": path.name,
        "closed_trades": str(len(records)),
        "summary_commission": summary_values[0],
        "summary_swap": summary_values[1],
        "summary_gross_profit": summary_values[2],
        "summary_net_profit": summary_values[3],
        "calculated_commission": str(sum(parse_number(row["commission"]) for row in records)),
        "calculated_swap": str(sum(parse_number(row["swap"]) for row in records)),
        "calculated_gross_profit": str(sum(parse_number(row["gross_profit"]) for row in records)),
        "calculated_net_profit": str(sum(parse_number(row["net_profit"]) for row in records)),
    }
    return records, summary


def main() -> None:
    all_records: list[dict[str, str]] = []
    summaries: list[dict[str, str]] = []

    for path in sorted(SOURCE_DIR.glob("GBE Monthly Statement *.pdf")):
        records, summary = parse_closed_trades(path)
        all_records.extend(records)
        summaries.append(summary)

    all_records.sort(key=lambda row: (row["entry_time"] or row["exit_time"], row["exit_time"], row["order_id"]))

    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_CSV.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=[
            "source_file",
            "order_id",
            "symbol",
            "qty",
            "direction",
            "entry_time",
            "entry",
            "exit_time",
            "exit",
            "commission",
            "swap",
            "gross_profit",
            "net_profit",
            "source_note",
        ])
        writer.writeheader()
        writer.writerows(all_records)

    SUMMARY_JSON.write_text(json.dumps({
        "files": summaries,
        "total_closed_trades": len(all_records),
        "total_gross_profit": str(sum(parse_number(row["gross_profit"]) for row in all_records)),
        "total_net_profit": str(sum(parse_number(row["net_profit"]) for row in all_records)),
    }, indent=2), encoding="utf-8")

    print(f"{len(all_records)} closed trades -> {OUTPUT_CSV}")


if __name__ == "__main__":
    main()
