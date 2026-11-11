"""Layout / output compliance check for an instance directory.

Verifies that generated files stayed inside the whitelisted directories,
that no temporary artifacts were left behind, and that every HTML page is
self-contained (no external stylesheet/script references).
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from common import resolve_root, add_root_arg

ALLOWED_TOP = {"agent.md", "config", "state", "data", "reports", "dashboard",
               "tmp", "logs", "archive", ".workbuddy"}
EXTERNAL = re.compile(r'<link\s+rel=["\']stylesheet["\']|<script\s+src=', re.I)


def main() -> None:
    ap = argparse.ArgumentParser(description="check instance output layout")
    add_root_arg(ap)
    ap.add_argument("--strict", action="store_true")
    args = ap.parse_args()

    root = resolve_root(args)
    problems = []

    # 1) top-level discipline
    for p in root.iterdir():
        if p.name.startswith(".") and p.name == ".workbuddy":
            continue  # host-managed memory, exempt
        if p.name not in ALLOWED_TOP:
            problems.append(f"unexpected top-level entry: {p.name}")

    # 2) no loose HTML/JSON/CSV at root
    for p in root.iterdir():
        if p.is_file() and p.suffix.lower() in {".html", ".json", ".csv", ".log", ".jpg", ".png", ".pdf"}:
            problems.append(f"loose output file at root: {p.name}")

    # 3) tmp hygiene (task-scoped subdirs only, no leftovers reported as warning)
    tmp = root / "tmp"
    if tmp.is_dir():
        leftovers = [p.name for p in tmp.iterdir()]
        if leftovers:
            problems.append(f"tmp/ not empty: {', '.join(leftovers[:5])}")

    # 4) HTML self-containment + links resolve
    dash = root / "dashboard"
    pages = [dash / "index.html"] + sorted((dash / "stocks").glob("*.html")) if dash.is_dir() else []
    if not (dash / "index.html").is_file():
        problems.append("missing dashboard/index.html")
    for page in pages:
        if not page.is_file():
            continue
        text = page.read_text(encoding="utf-8")
        if EXTERNAL.search(text):
            problems.append(f"external resource reference in {page.name}")
        if "<style>" not in text:
            problems.append(f"missing inline CSS in {page.name}")
        if "免责声明" not in text:
            problems.append(f"missing disclaimer in {page.name}")
        for href in re.findall(r'href="(stocks/[^"]+\.html)"', text):
            if not (dash / href).is_file():
                problems.append(f"broken link in {page.name}: {href}")

    # 5) every watchlist code has a detail page
    try:
        from common import load_yaml
        wl = load_yaml(root / "config" / "watchlist.yaml")
        codes = wl.get("codes") or []
        if isinstance(codes, list):
            for c in codes:
                if isinstance(c, dict) and c.get("primary"):
                    f = dash / "stocks" / f'{c["primary"]}.html'
                    if not f.is_file():
                        problems.append(f"missing stock page: {f.name}")
    except Exception as e:
        problems.append(f"could not read watchlist: {type(e).__name__}")

    if problems:
        print(f"FAIL: {len(problems)} layout issue(s):")
        for p in problems[:30]:
            print(f"  - {p}")
        sys.exit(1)

    print(f"layout check OK: {len(pages)} HTML page(s), all self-contained, links resolve, tmp clean")


if __name__ == "__main__":
    main()
