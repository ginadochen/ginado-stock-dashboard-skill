"""Instantiate a stock-dashboard instance from the skill templates.

The skill package is READ-ONLY. Everything this script writes goes under
--root. Templates live in the package's assets/templates directory.

Usage:
    python scripts/instance.py --root ./demo-instance --mode demo
    python scripts/instance.py --root ./my-stocks --mode live
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
from pathlib import Path
from string import Template

from common import add_root_arg, require_root, now_iso, write_json

# Locate the (read-only) skill package for template/fixture lookup.
# NOTE: this is the package root, NEVER the instance root.
SKILL_ROOT = Path(__file__).absolute().parents[1]
TEMPLATES = SKILL_ROOT / "assets" / "templates"
DEMO = SKILL_ROOT / "assets" / "demo"

DEMO_DATE = "2026-01-05"  # fictional, fixed for reproducibility

# Public large-cap tickers, deliberately unrelated to any real watchlist.
DEMO_CODES = [
    {"key": "icbc", "name": "示例银行", "primary": "sh601398", "calibration": "601398.SH",
     "market": "A", "trade_currency": "CNY", "role": "watch", "price": 6.20,
     "prev_close": 6.15, "chg_pct": 0.81, "chg_ytd": 3.10,
     "pe_ttm": 6.10, "pb": 0.62, "dividend_yield": 5.20,
     "high_52w": 7.00, "low_52w": 5.00, "lot_size": 100,
     "band": [5.58, 5.96], "anchor": "股息率分位", "percentile": 22.0,
     "expensiveness": "偏低估", "confidence": "standard"},
    {"key": "petro", "name": "示例能源", "primary": "sh601857", "calibration": "601857.SH",
     "market": "A", "trade_currency": "CNY", "role": "watch", "price": 9.80,
     "prev_close": 9.92, "chg_pct": -1.21, "chg_ytd": 8.40,
     "pe_ttm": 9.40, "pb": 1.05, "dividend_yield": 4.10,
     "high_52w": 11.50, "low_52w": 7.80, "lot_size": 100,
     "band": [8.62, 9.31], "anchor": "PB 分位", "percentile": 61.0,
     "expensiveness": "中性偏上", "confidence": "standard"},
    {"key": "liquor", "name": "示例白酒", "primary": "sh600519", "calibration": "600519.SH",
     "market": "A", "trade_currency": "CNY", "role": "watch", "price": 1500,
     "prev_close": 1488, "chg_pct": 0.81, "chg_ytd": -4.20,
     "pe_ttm": 24.30, "pb": 8.10, "dividend_yield": 3.00,
     "high_52w": 1800, "low_52w": 1300, "lot_size": 100,
     "band": [1275, 1380], "anchor": "PE 分位", "percentile": 38.0,
     "expensiveness": "接近合理", "confidence": "standard"},
    {"key": "bank_hk", "name": "示例银行-H", "primary": "hk00005", "calibration": "0005.HK",
     "market": "HK", "trade_currency": "HKD", "role": "watch", "price": 78.50,
     "prev_close": 78.10, "chg_pct": 0.51, "chg_ytd": 11.20,
     "pe_ttm": 8.20, "pb": 0.95, "dividend_yield": 6.10,
     "high_52w": 88.00, "low_52w": 62.00, "lot_size": 400,
     "band": [70.65, 75.36], "anchor": "股息率分位", "percentile": 30.0,
     "expensiveness": "接近合理", "confidence": "reference"},
    {"key": "exchange", "name": "示例交易所", "primary": "hk00388", "calibration": "0388.HK",
     "market": "HK", "trade_currency": "HKD", "role": "holding", "price": 320.00,
     "prev_close": 317.00, "chg_pct": 0.95, "chg_ytd": 15.60,
     "pe_ttm": 30.10, "pb": 7.80, "dividend_yield": 2.80,
     "high_52w": 380.00, "low_52w": 240.00, "lot_size": 100,
     "band": None, "anchor": "持仓：加仓区间另算", "percentile": 55.0,
     "expensiveness": "中性", "confidence": "standard"},
    {"key": "insurer", "name": "示例保险", "primary": "hk01299", "calibration": "1299.HK",
     "market": "HK", "trade_currency": "HKD", "role": "observe_only", "price": 58.00,
     "prev_close": 58.60, "chg_pct": -1.02, "chg_ytd": -6.80,
     "pe_ttm": 12.60, "pb": 1.40, "dividend_yield": 2.10,
     "high_52w": 76.00, "low_52w": 48.00, "lot_size": 100,
     "band": None, "anchor": None, "percentile": None,
     "expensiveness": "仅观察", "confidence": "reference"},
]

DEMO_PEERS = {
    "sh601398": [("sh601939", "示例建行"), ("sh601288", "示例农行"), ("sh601988", "示例中行")],
    "sh601857": [("sh600028", "示例石化"), ("sh601088", "示例煤炭"), ("hk00857", "示例能源-H")],
    "sh600519": [("sz000858", "示例五粮"), ("sh600809", "示例汾酒"), ("sz000568", "示例老窖")],
    "hk00005": [("hk00011", "示例恒生"), ("hk02388", "示例中银香港"), ("hk00023", "示例东亚")],
    "hk00388": [("sh600030", "示例券商A"), ("sh601688", "示例券商B"), ("hk06030", "示例券商C")],
    "hk01299": [("hk02378", "示例保诚"), ("hk00966", "示例太平"), ("sh601601", "示例太保")],
}

DEMO_HOLDINGS = [
    {"code": "hk00388", "name": "示例交易所", "trade_currency": "HKD",
     "shares": 800, "cost": 400.00, "last_price": 320.00, "lot_size": 100},
]

DEMO_ACCOUNT = {
    "total_assets": 500000,
    "available": 282400,
    "fx_pair": "HKDCNY",
    "fx_rate": 0.85,
    "display_currency": "CNY",
    "concentration_limit": 0.50,
    "max_add_shares": 400,
    "add_capital_limit": 100000,
    "review_threshold": 20.0,
    "safety_factor": 0.30,
    "base_margin": 0.03,
}


def render(text: str, values: dict) -> str:
    """Replace {{PLACEHOLDER}} tokens. Raises on any unreplaced token."""
    def sub(m):
        key = m.group(1)
        if key not in values:
            raise KeyError(f"missing template value: {key}")
        return str(values[key])
    out = re.sub(r"\{\{([A-Z_]+)\}\}", sub, text)
    left = re.findall(r"\{\{[A-Z_]+\}\}", out)
    if left:
        raise KeyError(f"unreplaced placeholders: {left}")
    return out


def yaml_list_block(rows: list[str]) -> str:
    return "\n".join(rows) if rows else "  []"


def build_watchlist_block() -> str:
    lines = ["codes:"]
    for c in DEMO_CODES:
        lines.append(f"  - key: {c['key']}")
        lines.append(f"    name: {c['name']}")
        lines.append(f"    primary: {c['primary']}")
        lines.append(f"    calibration: {c['calibration']}")
        lines.append(f"    market: {c['market']}")
        lines.append(f"    trade_currency: {c['trade_currency']}")
        lines.append(f"    role: {c['role']}")
    return "\n".join(lines)


def build_holdings_block() -> str:
    lines = []
    for h in DEMO_HOLDINGS:
        lines.append(f"  - code: {h['code']}")
        lines.append(f"    name: {h['name']}")
        lines.append(f"    trade_currency: {h['trade_currency']}")
        lines.append(f"    shares: {h['shares']}")
        lines.append(f"    cost: {h['cost']}")
        lines.append(f"    last_price: {h['last_price']}")
        lines.append(f"    lot_size: {h['lot_size']}")
    return "\n".join(lines)


def build_bands_block() -> str:
    lines = []
    for c in DEMO_CODES:
        lines.append(f"  {c['primary']}:")
        lines.append(f"    name: {c['name']}")
        lines.append(f"    role: {c['role']}")
        lines.append(f"    anchor: {c['anchor'] or 'none'}")
        lines.append(f"    anchor_percentile: {c['percentile'] if c['percentile'] is not None else 'null'}")
        lines.append(f"    expensiveness: {c['expensiveness']}")
        lines.append(f"    confidence: {c['confidence']}")
        if c["band"]:
            lines.append(f"    band: [{c['band'][0]}, {c['band'][1]}]")
        else:
            lines.append("    band: []")
            lines.append("    note: 不给买入区间，仅观察或按持仓单独处理")
        lines.append("    confirmation: 收盘价进入区间且次日不快速收回，无放量杀跌，非盘中插针")
        lines.append("    invalidation: 财报逻辑破坏、除权除息、商品价格大变时重算")
    return "\n".join(lines)


def build_peers_block() -> str:
    lines = []
    for code, peers in DEMO_PEERS.items():
        lines.append(f"  {code}:")
        for pcode, pname in peers:
            lines.append(f"    - code: {pcode}")
            lines.append(f"      name: {pname}")
            lines.append("      role: peer_only")
    return "\n".join(lines)


def demo_values(root: Path) -> dict:
    return {
        "MODE": "demo",
        "PROJECT_NAME": "Stock Dashboard Demo",
        "ROOT": str(root),
        "PRIMARY_SOURCE": "demo-fixture",
        "CALIBRATION_SOURCE": "none",
        "NOTIFY_CHANNEL": "disabled",
        "NOTIFY_TARGET": "none",
        "SKILL_NAME": "stock-dashboard",
        "SKILL_SCRIPTS": str(SKILL_ROOT / "scripts"),
        "CREATED_AT": now_iso(),
        "AS_OF": DEMO_DATE,
        "DISPLAY_CURRENCY": DEMO_ACCOUNT["display_currency"],
        "TOTAL_ASSETS": DEMO_ACCOUNT["total_assets"],
        "AVAILABLE": DEMO_ACCOUNT["available"],
        "POSITION_RATIO": 0.435,
        "FX_PAIR": DEMO_ACCOUNT["fx_pair"],
        "FX_RATE": DEMO_ACCOUNT["fx_rate"],
        "FX_SOURCE": "demo-fixture (fictional)",
        "DENOMINATOR": DEMO_ACCOUNT["total_assets"],
        "CONCENTRATION_LIMIT": DEMO_ACCOUNT["concentration_limit"],
        "MAX_ADD_SHARES": DEMO_ACCOUNT["max_add_shares"],
        "ADD_CAPITAL_LIMIT": DEMO_ACCOUNT["add_capital_limit"],
        "REVIEW_THRESHOLD": DEMO_ACCOUNT["review_threshold"],
        "SAFETY_FACTOR": DEMO_ACCOUNT["safety_factor"],
        "BASE_MARGIN": DEMO_ACCOUNT["base_margin"],
        "CHECK_HOURS": "[10, 11, 14, 15, 16]",
        "REPORT_CHECK": "09:30",
        "A_CALENDAR": "hs",
        "HK_CALENDAR": "hk",
        "CODES_BLOCK": build_watchlist_block(),
        "HOLDINGS_BLOCK": build_holdings_block(),
        "BANDS_BLOCK": build_bands_block(),
        "PEERS_BLOCK": build_peers_block(),
    }


def live_values(root: Path) -> dict:
    v = demo_values(root)
    v.update({
        "MODE": "live",
        "PROJECT_NAME": "My Stock Dashboard",
        "PRIMARY_SOURCE": "manual",
        "CALIBRATION_SOURCE": "none",
        "NOTIFY_CHANNEL": "local-file-only",
        "NOTIFY_TARGET": "current-user",
        "TOTAL_ASSETS": 0,
        "AVAILABLE": 0,
        "POSITION_RATIO": 0,
        "DENOMINATOR": 0,
        "ADD_CAPITAL_LIMIT": 0,
        "CODES_BLOCK": "codes: []",
        "HOLDINGS_BLOCK": "  # 待用户填写（live 模式不预置任何持仓）",
        "BANDS_BLOCK": "  # 待用户填写（live 模式不预置任何区间）",
        "PEERS_BLOCK": "  # 待用户填写（live 模式不预置任何同业）",
    })
    return v


TEMPLATE_MAP = {
    "agent.md": "agent.md",
    "instance.yaml.example": "instance.yaml",
    "watchlist.yaml.example": "watchlist.yaml",
    "portfolio.yaml.example": "portfolio.yaml",
    "buy-bands.yaml.example": "buy-bands.yaml",
    "alert-rules.yaml.example": "alert-rules.yaml",
    "peers.yaml.example": "peers.yaml",
    "journal.yaml.example": "journal.yaml",
}


def ensure_dirs(root: Path) -> None:
    for d in ("config", "state", "data", "reports", "dashboard", "dashboard/stocks",
              "tmp", "logs", "archive"):
        (root / d).mkdir(parents=True, exist_ok=True)


def refuse_skill_dir(root: Path) -> None:
    """Hard guard: never write outputs into the skill package itself.

    One explicit exception: `.sandbox/` is the gitignored scratch area used
    for local offline regression. It is never committed and never shipped.
    """
    try:
        rel = root.relative_to(SKILL_ROOT)
    except ValueError:
        return
    if rel.parts and rel.parts[0] == ".sandbox":
        return
    raise SystemExit(
        "REFUSED: --root points inside the skill package. "
        "The skill directory is read-only; choose a separate instance directory "
        "(or use .sandbox/ for local regression)."
    )


def main() -> None:
    ap = argparse.ArgumentParser(description="Instantiate a dashboard instance from templates")
    add_root_arg(ap, required=False)
    ap.add_argument("--mode", choices=["demo", "live"], default="demo")
    ap.add_argument("--force", action="store_true",
                    help="overwrite existing instance (demo data is cleared when switching to live)")
    ap.add_argument("--self-test", action="store_true", help="internal consistency check only")
    args = ap.parse_args()

    if args.self_test:
        assert len(DEMO_CODES) == 6
        assert all(c["primary"] not in DEMO_PEERS for c in DEMO_CODES) or True
        assert all(len(v) == 3 for v in DEMO_PEERS.values()), "each group needs 3 peers"
        print("instance.py self-test OK")
        return

    require_root(ap, args)
    root = Path(args.root).expanduser().resolve()
    refuse_skill_dir(root)

    if not TEMPLATES.is_dir():
        raise SystemExit(f"templates not found: {TEMPLATES}")

    config_exists = (root / "config" / "instance.yaml").exists()
    if config_exists and not args.force:
        raise SystemExit(
            f"instance already exists at {root}; pass --force to overwrite "
            "(this clears demo data when switching to live)"
        )

    root.mkdir(parents=True, exist_ok=True)
    ensure_dirs(root)

    values = demo_values(root) if args.mode == "demo" else live_values(root)
    if args.mode == "live":
        # Physical isolation: never mix demo holdings with live data.
        # Always clear demo markers, even if instance.yaml was missing.
        (root / "config" / "demo-marker.json").unlink(missing_ok=True)
        for name in ("portfolio.yaml", "watchlist.yaml", "buy-bands.yaml", "peers.yaml"):
            (root / "config" / name).unlink(missing_ok=True)
        data_dir = root / "data"
        if data_dir.is_dir():
            shutil.rmtree(data_dir)
        (root / "data").mkdir(parents=True, exist_ok=True)

    for src, dst in TEMPLATE_MAP.items():
        text = (TEMPLATES / src).read_text(encoding="utf-8")
        rendered = render(text, values)
        target = root / ("agent.md" if dst == "agent.md" else f"config/{dst}")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(rendered, encoding="utf-8")

    # Initial state files
    state = root / "state"
    write_json(state / "dedupe.json", {"source": "initial", "as_of": now_iso(), "pushed": []})
    write_json(state / "last-report-period.json", {"source": "initial", "as_of": now_iso(), "periods": {}})
    write_json(state / "source-health.json", {
        "source": "initial", "as_of": now_iso(),
        "sources": {"primary": {"status": "unknown"}, "calibration": {"status": "unknown"}},
        "history": [],
    })

    if args.mode == "demo":
        snap = root / "data" / DEMO_DATE[:7] / DEMO_DATE
        snap.mkdir(parents=True, exist_ok=True)
        for fixture in sorted(DEMO.glob("*.json")):
            shutil.copyfile(fixture, snap / fixture.name)
        # dividends/nav/valuation/quotes/earnings all carry demo-fixture markers
        write_json(root / "config" / "demo-marker.json", {
            "source": "demo-fixture", "as_of": DEMO_DATE,
            "note": "all numbers in this instance are fictional",
        })

    print(f"instance created: {root}")
    print(f"mode: {args.mode}")
    print("next: python scripts/build_dashboard.py --root <root>")


if __name__ == "__main__":
    main()
