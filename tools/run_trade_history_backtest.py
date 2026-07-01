from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from statistics import mean, median


ROOT = Path(__file__).resolve().parents[1]
MONTHLY_TRADES = ROOT / "reports" / "gbe_monthly_closed_trades.csv"
ORDER_HISTORY_TRADES = ROOT / "reports" / "trade_history_gbe_2026-05-20_reconstructed_trades.csv"
OUTPUT_JSON = ROOT / "reports" / "backtest_trade_history_2025-08_to_2026-05.json"
OUTPUT_MD = ROOT / "reports" / "backtest_trade_history_2025-08_to_2026-05.md"


@dataclass(frozen=True)
class TradeRecord:
    source: str
    source_file: str
    order_id: str
    symbol: str
    market: str
    direction: str
    entry_time: datetime | None
    exit_time: datetime
    qty: float
    entry: float | None
    exit: float | None
    gross_profit: float
    costs: float
    net_profit: float
    planned_crv: float | None
    risk_cash: float | None
    realized_r: float | None
    documented_sl: bool
    documented_tp: bool
    rule_compliant: bool
    rule_gaps: tuple[str, ...]


def parse_float(value: str | None) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(str(value).replace(" ", ""))
    except ValueError:
        return None


def parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            pass
    return None


def market_for(symbol: str) -> str:
    normalized = symbol.upper()
    if normalized.endswith(".OQ") or normalized.endswith(".N") or normalized in {"NVDA", "AAPL", "MSFT", "TSLA"}:
        return "US-Aktie"
    if normalized in {"DE40", "DE40.C", "USTEC", "DJ30", "DAX", "US500", "JP225"}:
        return "Index"
    if normalized in {"XAGUSD", "XAUUSD", "XAUEUR", "XPTUSD", "UKOIL"}:
        return "Rohstoff"
    if normalized in {"BTCUSD", "BCHUSD", "ETHUSD"}:
        return "Krypto"
    if len(normalized) == 6 and normalized.isalpha():
        return "Forex"
    return "Sonstige"


def load_monthly_trades() -> list[TradeRecord]:
    trades: list[TradeRecord] = []
    with MONTHLY_TRADES.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            exit_time = parse_dt(row["exit_time"])
            if exit_time is None:
                continue
            gross = parse_float(row["gross_profit"]) or 0.0
            net = parse_float(row["net_profit"]) or gross
            # Broker statements sometimes carry positive net > gross due positive swap; model costs only when net is lower.
            costs = max(0.0, gross - net)
            note = (row.get("source_note") or "").lower()
            documented_sl = "[sl" in note
            documented_tp = "[tp" in note
            gaps = ["Setup-Kriterien nicht dokumentiert", "Screenshots fehlen", "Emotionen fehlen"]
            if not documented_sl:
                gaps.append("Stop Loss nicht dokumentiert")
            if not documented_tp:
                gaps.append("Take Profit nicht dokumentiert")
            trades.append(
                TradeRecord(
                    source="GBE Monatsbericht",
                    source_file=row["source_file"],
                    order_id=row["order_id"],
                    symbol=row["symbol"],
                    market=market_for(row["symbol"]),
                    direction=row["direction"],
                    entry_time=parse_dt(row["entry_time"]),
                    exit_time=exit_time,
                    qty=parse_float(row["qty"]) or 0.0,
                    entry=parse_float(row["entry"]),
                    exit=parse_float(row["exit"]),
                    gross_profit=gross,
                    costs=costs,
                    net_profit=net,
                    planned_crv=None,
                    risk_cash=None,
                    realized_r=None,
                    documented_sl=documented_sl,
                    documented_tp=documented_tp,
                    rule_compliant=False,
                    rule_gaps=tuple(gaps),
                )
            )
    return trades


def load_order_history_trades() -> list[TradeRecord]:
    trades: list[TradeRecord] = []
    with ORDER_HISTORY_TRADES.open(newline="", encoding="utf-8") as handle:
        for index, row in enumerate(csv.DictReader(handle), start=1):
            entry_time = parse_dt(row["entry_time"])
            exit_time = parse_dt(row["exit_time"]) or entry_time
            if exit_time is None:
                continue
            entry = parse_float(row["entry"])
            stop = parse_float(row["recorded_sl"])
            target = parse_float(row["recorded_tp"])
            exit_price = parse_float(row["exit"])
            qty = parse_float(row["qty"]) or 0.0
            gross = parse_float(row["gross_profit"]) or 0.0
            commission = parse_float(row.get("commission")) or 0.0
            swap = parse_float(row.get("swap")) or 0.0
            costs = abs(commission + swap)
            net = gross - costs
            # Do not infer R from price distance * quantity for CFDs.
            # A valid R calculation needs tick/pip/point value and currency conversion.
            risk_cash = None
            realized_r = None
            planned_crv = parse_float(row.get("recorded_crv"))
            documented_sl = stop is not None
            documented_tp = target is not None
            gaps = ["Setup-Kriterien nicht dokumentiert", "Screenshots fehlen", "Emotionen fehlen"]
            if not documented_sl:
                gaps.append("Stop Loss nicht dokumentiert")
            if not documented_tp:
                gaps.append("Take Profit nicht dokumentiert")
            if planned_crv is None or planned_crv < 1.0:
                gaps.append("CRV < 1:1 oder nicht dokumentiert")
            trades.append(
                TradeRecord(
                    source="TradingView/GBE Orderverlauf",
                    source_file=ORDER_HISTORY_TRADES.name,
                    order_id=f"order-history-{index}",
                    symbol=row["symbol"],
                    market=market_for(row["symbol"]),
                    direction=row["direction"],
                    entry_time=entry_time,
                    exit_time=exit_time,
                    qty=qty,
                    entry=entry,
                    exit=exit_price,
                    gross_profit=gross,
                    costs=costs,
                    net_profit=net,
                    planned_crv=planned_crv,
                    risk_cash=risk_cash,
                    realized_r=realized_r,
                    documented_sl=documented_sl,
                    documented_tp=documented_tp,
                    rule_compliant=False,
                    rule_gaps=tuple(gaps),
                )
            )
    return trades


def max_drawdown(equity: list[float]) -> float:
    peak = equity[0] if equity else 0.0
    drawdown = 0.0
    for value in equity:
        peak = max(peak, value)
        drawdown = max(drawdown, peak - value)
    return drawdown


def largest_loss_streak(trades: list[TradeRecord]) -> int:
    longest = 0
    current = 0
    for trade in trades:
        if trade.net_profit < 0:
            current += 1
            longest = max(longest, current)
        elif trade.net_profit > 0:
            current = 0
    return longest


def grouped_metrics(trades: list[TradeRecord], key_fn) -> list[dict[str, object]]:
    groups: dict[str, list[TradeRecord]] = defaultdict(list)
    for trade in trades:
        groups[key_fn(trade)].append(trade)
    rows = []
    for key, values in groups.items():
        rows.append({"name": key, **metrics(values)})
    return sorted(rows, key=lambda row: (float(row["net_profit"]), int(row["trades"])))


def metrics(trades: list[TradeRecord]) -> dict[str, object]:
    count = len(trades)
    wins = [trade.net_profit for trade in trades if trade.net_profit > 0]
    losses = [trade.net_profit for trade in trades if trade.net_profit < 0]
    flat = [trade.net_profit for trade in trades if trade.net_profit == 0]
    gross_wins = sum(wins)
    gross_losses = abs(sum(losses))
    net = sum(trade.net_profit for trade in trades)
    equity = []
    running = 0.0
    for trade in trades:
        running += trade.net_profit
        equity.append(running)
    r_values = [trade.realized_r for trade in trades if trade.realized_r is not None]
    return {
        "trades": count,
        "wins": len(wins),
        "losses": len(losses),
        "flat": len(flat),
        "win_rate": len(wins) / count if count else 0.0,
        "gross_profit": gross_wins,
        "gross_loss": gross_losses,
        "net_profit": net,
        "average_trade": net / count if count else 0.0,
        "median_trade": median([trade.net_profit for trade in trades]) if trades else 0.0,
        "average_win": mean(wins) if wins else 0.0,
        "average_loss": mean(losses) if losses else 0.0,
        "profit_factor": gross_wins / gross_losses if gross_losses else None,
        "max_drawdown": max_drawdown(equity),
        "largest_loss_streak": largest_loss_streak(trades),
        "expectancy_cash": net / count if count else 0.0,
        "average_realized_r": mean(r_values) if r_values else None,
        "r_sample_size": len(r_values),
        "rule_compliant_trades": sum(1 for trade in trades if trade.rule_compliant),
    }


def fmt_money(value: object) -> str:
    if value is None:
        return "n/a"
    return f"{float(value):,.2f}"


def fmt_pct(value: object) -> str:
    if value is None:
        return "n/a"
    return f"{float(value) * 100:.2f}%"


def top_rows(rows: list[dict[str, object]], n: int = 10) -> list[dict[str, object]]:
    return rows[:n]


def make_markdown(summary: dict[str, object]) -> str:
    overall = summary["overall"]
    assert isinstance(overall, dict)
    by_month = summary["by_month"]
    by_symbol_worst = summary["by_symbol_worst"]
    by_symbol_best = summary["by_symbol_best"]
    by_market = summary["by_market"]
    assert isinstance(by_month, list)
    assert isinstance(by_symbol_worst, list)
    assert isinstance(by_symbol_best, list)
    assert isinstance(by_market, list)

    def fmt_profit_factor(value: object) -> str:
        return "n/a" if value is None else f"{float(value):.2f}"

    def table(rows: list[dict[str, object]], name_label: str = "Gruppe") -> str:
        lines = [f"| {name_label} | Trades | Trefferquote | Netto | Profit Factor | Max DD | Verlustserie |", "|---|---:|---:|---:|---:|---:|---:|"]
        for row in rows:
            lines.append(
                f"| {row['name']} | {row['trades']} | {fmt_pct(row['win_rate'])} | {fmt_money(row['net_profit'])} | "
                f"{fmt_profit_factor(row['profit_factor'])} | "
                f"{fmt_money(row['max_drawdown'])} | {row['largest_loss_streak']} |"
            )
        return "\n".join(lines)

    lines = [
        "# Backtest-/Review-Report der Trade-Historie",
        "",
        "Hinweis: Dies ist ein ex-post Backtest der ausgeführten Trades, keine Anlageberatung und kein Signal-Backtest. "
        "Ein echter regelbasierter Setup-Backtest benötigt historische OHLCV-Daten, News-/Event-Zeitstempel und vollständig dokumentierte Setup-Kriterien.",
        "",
        "## Gesamtbild",
        "",
        f"- Zeitraum: {summary['start_date']} bis {summary['end_date']}",
        f"- Trades: {overall['trades']} | Gewinner: {overall['wins']} | Verlierer: {overall['losses']} | Flat: {overall['flat']}",
        f"- Trefferquote: {fmt_pct(overall['win_rate'])}",
        f"- Nettoergebnis: {fmt_money(overall['net_profit'])}",
        f"- Erwartungswert je Trade: {fmt_money(overall['expectancy_cash'])}",
        f"- Durchschnittlicher Gewinn: {fmt_money(overall['average_win'])}",
        f"- Durchschnittlicher Verlust: {fmt_money(overall['average_loss'])}",
        f"- Profit Factor: {fmt_profit_factor(overall['profit_factor'])}",
        f"- Max Drawdown auf Trade-Sequenz: {fmt_money(overall['max_drawdown'])}",
        f"- Größte Verlustserie: {overall['largest_loss_streak']} Trades",
        "- Realized-R: nicht belastbar berechnet, weil Tick-/Punktwerte und Währungsumrechnung nicht vollständig vorliegen.",
        f"- Regelkonform vollständig dokumentiert: {overall['rule_compliant_trades']} Trades",
        "",
        "## Monatsauswertung",
        "",
        table(by_month, "Monat"),
        "",
        "## Marktgruppen",
        "",
        table(by_market, "Markt"),
        "",
        "## Schwächste Symbole",
        "",
        table(top_rows(by_symbol_worst), "Symbol"),
        "",
        "## Stärkste Symbole",
        "",
        table(top_rows(by_symbol_best), "Symbol"),
        "",
        "## TradingFreaks-Regelcheck",
        "",
        "- Kein Trade wurde als vollständig regelkonform gewertet, weil Setup-Checkliste, Emotionen und Screenshots aus den Quellen nicht vollständig vorliegen.",
        "- Monatsberichte enthalten überwiegend keine belastbare SL-/TP-Planung zum Entscheidungszeitpunkt.",
        "- Deshalb ist der korrekte System-Output für die historische Regelvalidierung: `nicht handeln` bzw. `Review offen`, bis Pflichtfelder nachgetragen sind.",
        "- Die Kennzahlen sind Prozess- und Risikoinformation, keine Kauf-/Verkaufsempfehlung und keine Prognose.",
    ]
    return "\n".join(lines) + "\n"


def main() -> None:
    trades = load_monthly_trades() + load_order_history_trades()
    trades.sort(key=lambda trade: (trade.exit_time, trade.order_id))

    by_month = grouped_metrics(trades, lambda trade: trade.exit_time.strftime("%Y-%m"))
    by_market = grouped_metrics(trades, lambda trade: trade.market)
    by_symbol = grouped_metrics(trades, lambda trade: trade.symbol)
    by_symbol_worst = sorted(by_symbol, key=lambda row: float(row["net_profit"]))
    by_symbol_best = sorted(by_symbol, key=lambda row: float(row["net_profit"]), reverse=True)
    gap_counts = Counter(gap for trade in trades for gap in trade.rule_gaps)

    summary: dict[str, object] = {
        "start_date": trades[0].exit_time.isoformat(sep=" ") if trades else "",
        "end_date": trades[-1].exit_time.isoformat(sep=" ") if trades else "",
        "overall": metrics(trades),
        "by_month": by_month,
        "by_market": by_market,
        "by_symbol_worst": top_rows(by_symbol_worst, 15),
        "by_symbol_best": top_rows(by_symbol_best, 15),
        "rule_gap_counts": dict(gap_counts.most_common()),
        "source_files": [MONTHLY_TRADES.name, ORDER_HISTORY_TRADES.name],
        "method": "Executed-trade backtest/review. No lookahead signal generation; no OHLCV or news-driven strategy simulation.",
    }

    OUTPUT_JSON.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    OUTPUT_MD.write_text(make_markdown(summary), encoding="utf-8")
    print(f"{len(trades)} trades analysed")
    print(OUTPUT_MD)
    print(OUTPUT_JSON)


if __name__ == "__main__":
    main()
