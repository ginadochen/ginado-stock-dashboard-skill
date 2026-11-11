"""Write one daily NAV snapshot under --root.

All account values are supplied on the command line by the Agent, which reads
them from config/portfolio.yaml. Values are NEVER logged and NEVER appear in
notifications. This script does not call MCP.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from common import add_root_arg, resolve_root, write_json, now_iso


def parse_benchmarks(items):
    out = {}
    for item in items or []:
        key, sep, val = item.partition("=")
        if not sep:
            raise SystemExit(f"invalid --benchmark, expected CODE=VALUE, got: {item}")
        try:
            out[key.strip()] = float(val)
        except ValueError:
            raise SystemExit(f"benchmark value must be numeric: {item}")
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description="write daily NAV snapshot")
    add_root_arg(ap)
    ap.add_argument("--date", required=True, help="YYYY-MM-DD (trading day)")
    ap.add_argument("--total-assets", type=float, required=True)
    ap.add_argument("--cash", type=float, required=True)
    ap.add_argument("--position-value", type=float, required=True)
    ap.add_argument("--day-pnl", type=float, default=0.0)
    ap.add_argument("--benchmark", action="append", default=[], help="CODE=VALUE, repeatable")
    ap.add_argument("--currency", default="CNY")
    ap.add_argument("--source", default="manual")
    ap.add_argument("--demo", action="store_true", help="mark snapshot as fictional demo data")
    args = ap.parse_args()

    if len(args.date) != 10 or args.date[4] != "-" or args.date[7] != "-":
        raise SystemExit("--date must be YYYY-MM-DD")

    root = resolve_root(args)
    snap = root / "data" / args.date[:7] / args.date
    snap.mkdir(parents=True, exist_ok=True)
    target = snap / "nav.json"
    existing = {}
    if target.exists():
        import json
        existing = json.loads(target.read_text(encoding="utf-8"))

    payload = {
        "source": "demo-fixture" if args.demo else args.source,
        "as_of": args.date,
        "currency": args.currency,
        "date": args.date,
        "total_assets_cny": args.total_assets,
        "cash_cny": args.cash,
        "position_value_cny": args.position_value,
        "day_pnl_cny": args.day_pnl,
        "benchmarks": parse_benchmarks(args.benchmark),
        "method_note": "简单收益口径；TWR/MWR 未计算，净值曲线需 ≥10 个交易日",
        "first_written_at": existing.get("first_written_at", now_iso()),
        "updated_at": now_iso(),
    }
    write_json(target, payload)
    print(f"wrote {target}")


if __name__ == "__main__":
    main()
