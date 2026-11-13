#!/usr/bin/env python3
"""Decide whether today or yesterday carries a scheduled macro release.

Why this exists: macro indicators are only re-fetched in full on Monday. If a
CPI print lands on Wednesday, the naive "Tue-Fri only check the calendar"
rule leaves it out of the dashboard until the following Monday — up to five
trading days of lag on a number the countdown bar was pointing at.

This script turns "should we re-fetch now" into a deterministic answer, so the
agent does not have to judge it by feel. It only reads local files; it never
calls an MCP server.

Usage:
    python scripts/macro_release_due.py --root <instance> [--date YYYY-MM-DD]

Output: JSON on stdout. Empty `due` means "nothing to do, follow the weekly
cadence". Exit code is always 0 — a failed judgement must not break the whole
automation run, it just reports `due: []` with a note.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

from common import (
    add_root_arg,
    instance_paths,
    latest_snapshot_with,
    load_json,
    load_yaml,
    require_root,
    resolve_root,
)

# Calendar events carry Chinese region names, indicator config uses CN/US.
REGION_ALIAS = {
    "CN": ("中国",),
    "US": ("美国",),
    "HK": ("中国香港", "香港"),
}


def build_report(root: Path, today: date) -> dict:
    out = {
        "checked_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "base_date": today.isoformat(),
        "window": [],
        "snapshot": None,
        "due": [],
        "matched_events": [],
        "note": "",
    }

    P = instance_paths(root)
    cfg_path = P["config"] / "macro.yaml"
    if not cfg_path.exists():
        out["note"] = "config/macro.yaml not present — optional module disabled"
        return out

    cfg = load_yaml(cfg_path) or {}
    rr = cfg.get("release_refresh") or {}
    keywords = rr.get("keywords") or {}
    skip_words = rr.get("skip_keywords") or []
    try:
        window_days = int(rr.get("window_days", 1))
    except (TypeError, ValueError):
        window_days = 1

    snap = latest_snapshot_with(root, "macro.json")
    if snap is None:
        out["note"] = "no macro.json snapshot yet — nothing to compare against"
        return out
    out["snapshot"] = snap.name

    macro = load_json(snap / "macro.json") or {}

    # Indicator region comes from config: snapshots do not carry list_code,
    # and the config is the single source of truth for what each key means.
    ind_region, ind_list_code = {}, {}
    for ind in cfg.get("indicators") or []:
        ind = ind or {}
        key = ind.get("key")
        if key:
            ind_region[key] = ind.get("region") or "CN"
            ind_list_code[key] = ind.get("list_code")
    for ind in macro.get("indicators") or []:
        ind = ind or {}
        key = ind.get("key")
        if key and key not in ind_region:
            ind_region[key] = ind.get("region") or "CN"

    cal = macro.get("calendar") or {}
    events = list(cal.get("events") or []) + list(cal.get("decision_events") or [])

    window = [(today - timedelta(days=d)).isoformat() for d in range(0, window_days + 1)]
    out["window"] = window

    due: dict = {}
    for ev in events:
        ev = ev or {}
        ev_date = str(ev.get("date") or "")[:10]
        if ev_date not in window:
            continue
        text = str(ev.get("event") or "")
        if ev.get("kind") == "speech":
            continue
        if any(str(w) in text for w in skip_words):
            continue

        ev_region = str(ev.get("region") or "")
        hit = []
        for key, words in keywords.items():
            if not any(str(w) in text for w in (words or [])):
                continue
            alias = REGION_ALIAS.get(ind_region.get(key, "CN"), ())
            # Region isolation: a China CPI event must not refetch US CPI.
            if ev_region and ev_region not in alias:
                continue
            hit.append(key)
            due.setdefault(key, []).append(text)

        if hit:
            out["matched_events"].append(
                {"date": ev_date, "region": ev_region, "event": text, "keys": hit}
            )

    out["due"] = [
        {
            "key": k,
            "list_code": ind_list_code.get(k),
            "region": ind_region.get(k),
            "triggered_by": v[:2],
        }
        for k, v in sorted(due.items())
    ]
    out["note"] = (
        "release inside the window — refetch only these indicators, then merge "
        "into today's snapshot; do not wait for Monday and do not run a full pull"
        if out["due"]
        else "no whitelisted release in the window — keep the weekly cadence"
    )
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="Check whether a macro release is due")
    add_root_arg(ap, required=False)
    ap.add_argument("--date", default=None, help="base date YYYY-MM-DD, defaults to today")
    ap.add_argument("--json-lines", action="store_true", help="also print KEY=VALUE lines")
    args = ap.parse_args()
    require_root(ap, args)

    root = resolve_root(args)
    try:
        today = date.fromisoformat(args.date) if args.date else date.today()
    except ValueError:
        print(json.dumps({"error": f"bad --date: {args.date}"}, ensure_ascii=False))
        return 0

    try:
        out = build_report(root, today)
    except Exception as exc:  # judgement failure must not break the run
        out = {
            "checked_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "due": [],
            "note": f"judgement failed, treat as uncovered: {type(exc).__name__}: {exc}",
        }

    if args.json_lines:
        print("DUE_KEYS=" + ",".join(d["key"] for d in out.get("due", [])))
        print("DUE_CODES=" + ",".join(str(d.get("list_code") or "") for d in out.get("due", [])))
        print("DUE_COUNT=" + str(len(out.get("due", []))))
    print(json.dumps(out, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
