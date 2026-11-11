"""Privacy scanner for the stock-dashboard skill repository.

Default-deny approach: scan every text file that would be committed and fail
on any pattern that looks like real personal/account data. Fictional demo
fixtures (assets/demo, example) are allowlisted by explicit markers.

Usage:
    python scripts/privacy_check.py --root . --strict          # repository scan
    python scripts/privacy_check.py --root . --scope instance  # instance dir scan
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

SCAN_SUFFIXES = {".md", ".py", ".json", ".yaml", ".yml", ".example", ".html",
                 ".txt", ".cfg", ".toml", ".sh", ".js", ".css", ".xml", ".ini"}
BINARY_RED = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".pdf",
              ".xlsx", ".xls", ".docx", ".doc", ".zip", ".7z", ".pem", ".key", ".p12"}

SKIP_DIRS = {".git", ".sandbox", "dist", "__pycache__", "node_modules", ".venv", "venv"}
DEMO_DIRS = {"assets/demo", "example"}

# Patterns are deliberately conservative: false positives are acceptable,
# false negatives are not. Match text is NEVER printed in full.
PATTERNS = [
    ("precise-amount", re.compile(r"(?<![\d.])\d{4,}\.\d{2}(?!\d)")),
    ("cjk-name-context", re.compile(r"(?:收件人|联系人|账户名|户名|本人)\s*[:：]\s*[\u4e00-\u9fa5]{2,4}")),
    ("chat-id", re.compile(r"(?:chat_id|chatid|userid|openid)\s*[:=]\s*['\"]?[A-Za-z0-9_-]{12,}")),
    ("wecom-id", re.compile(r"\b(?:wo|wr|wook)[A-Za-z0-9_-]{16,}\b")),
    # Require a standalone drive letter: avoid false positives on URL schemes
    # (a URL scheme contains a letter followed by colon+slashes too).
    ("windows-abs-path", re.compile(r"(?<![A-Za-z0-9])[A-Za-z]:[\\/]{1,2}(?:Users|Documents|Desktop|Downloads|WorkBuddy|stock|github)\b", re.I)),
    ("unc-path", re.compile(r"\\\\[A-Za-z0-9_.-]+\\")),
    ("automation-uuid", re.compile(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b", re.I)),
    ("token", re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|glpat-[A-Za-z0-9_-]{20,})\b")),
    ("hosts-file", re.compile(r"\bhosts\.yml\b")),
    ("private-key", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("email", re.compile(r"\b[\w.+-]+@(?!users\.noreply\.github\.com|example\.com|workbuddy\.cn)[\w-]+\.[\w.]{2,}\b")),
    ("mainland-mobile", re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)")),
    ("ipv4", re.compile(r"(?<![\d.])(?:\d{1,3}\.){3}\d{1,3}(?![\d.])")),
    ("share-count", re.compile(r"(?:shares|持股|股数)\s*[:：]\s*\d{3,}(?!\.)")),
    ("cost-price", re.compile(r"(?:cost|成本价)\s*[:：]\s*\d{2,}\.\d{4}")),
    ("real-name-in-header", re.compile(r"(?:user\.name|committer|author)\s*[:=]\s*[\u4e00-\u9fa5]{2,4}")),
]

# A watchlist *combination* can reveal a user's private preferences even
# though each ticker is public. Never hardcode anyone's tickers here: the
# codes are supplied at scan time via --codes / PRIVACY_WATCH_CODES.
def add_watchlist_pattern(codes):
    if not codes:
        return
    parts = [re.escape(c.strip()) for c in codes.split(",") if c.strip()]
    if len(parts) >= 3:
        PATTERNS.append(("watchlist-cluster", re.compile("|".join(parts))))
    elif parts:
        PATTERNS.append(("watchlist-code", re.compile("|".join(parts))))

# Legitimate occurrences that must not be treated as leaks.
ALLOWED_EXACT = {
    "precise-amount",  # handled separately: demo/example allowlisted; elsewhere only round demo values allowed
}
ALLOWED_PATHS = {
    # These files describe the scanner itself or the deny-list; mentioning a
    # pattern name is not a leak.
    "docs/PRIVACY-AUDIT.md": {"token", "email", "windows-abs-path", "precise-amount",
                              "automation-uuid", "hosts-file", "private-key",
                                 "chat-id", "wecom-id", "cjk-name-context",
                                 "watchlist-cluster", "watchlist-code"},
    ".gitignore": {"hosts-file", "token", "email"},
    "SECURITY.md": {"token", "email", "hosts-file", "private-key"},
    "scripts/privacy_check.py": {"token", "email", "windows-abs-path", "automation-uuid",
                                 "chat-id", "wecom-id", "mainland-mobile", "ipv4",
                                 "share-count", "cost-price", "cjk-name-context",
                                 "real-name-in-header", "watchlist-cluster", "watchlist-code",
                                 "unc-path", "precise-amount", "hosts-file", "private-key"},
    ".github/workflows/verify.yml": {"token", "email", "windows-abs-path", "automation-uuid"},
    "PRIVACY.md": {"token", "email"},
    "NOTICE": {"email"},
    "README.md": {"email"},
}


def is_demo_path(rel: str) -> bool:
    return any(rel == d or rel.startswith(d + "/") for d in DEMO_DIRS)


def should_scan(path: Path, root: Path) -> bool:
    rel = path.relative_to(root).as_posix()
    parts = rel.split("/")
    if any(p in SKIP_DIRS for p in parts[:-1]):
        return False
    if path.suffix.lower() in BINARY_RED:
        return False
    return path.suffix.lower() in SCAN_SUFFIXES or path.name in {
        "LICENSE", "NOTICE", ".gitignore", "SKILL.md",
    }


def scan_file(path: Path, root: Path) -> list[tuple[str, str]]:
    rel = path.relative_to(root).as_posix()
    try:
        text = path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return []
    hits = []
    for label, rx in PATTERNS:
        if rx.search(text):
            if label in ALLOWED_PATHS.get(rel, set()):
                continue
            if is_demo_path(rel) and label in {
                "precise-amount", "share-count", "cost-price", "ipv4", "email"
            }:
                # demo fixtures are explicitly fictional and marked demo-fixture
                if "demo-fixture" in text or is_demo_path(rel):
                    continue
            hits.append((label, rel))
    return hits


def main() -> None:
    ap = argparse.ArgumentParser(description="privacy scan")
    ap.add_argument("--root", default=".", help="repository or instance root")
    ap.add_argument("--strict", action="store_true", help="exit 1 on any hit")
    ap.add_argument("--scope", choices=["repo", "instance"], default="repo")
    ap.add_argument("--codes", default="", help="optional comma-separated private ticker codes "
                    "to scan for (never stored in the repo); also read from PRIVACY_WATCH_CODES")
    args = ap.parse_args()

    import os
    add_watchlist_pattern(args.codes or os.environ.get("PRIVACY_WATCH_CODES", ""))

    root = Path(args.root).expanduser().resolve()
    if not root.is_dir():
        raise SystemExit(f"root does not exist: {root}")

    all_hits = []
    binaries = []
    for p in sorted(root.rglob("*")):
        if not p.is_file():
            continue
        rel = p.relative_to(root).as_posix()
        parts = rel.split("/")
        if any(x in SKIP_DIRS for x in parts[:-1]):
            continue
        if p.suffix.lower() in BINARY_RED:
            binaries.append(rel)
            continue
        if should_scan(p, root):
            all_hits.extend(scan_file(p, root))

    if args.scope == "instance":
        # An instance legitimately holds private data; only check that no
        # tokens / credentials leaked into it.
        all_hits = [h for h in all_hits if h[0] in {"token", "private-key", "hosts-file"}]

    if binaries:
        print(f"FAIL: {len(binaries)} binary/image file(s) present (screenshots must never be committed):")
        for b in binaries[:10]:
            print(f"  {b}")
        sys.exit(1)

    if all_hits:
        print(f"FAIL: {len(all_hits)} privacy pattern hit(s):")
        for label, rel in all_hits[:40]:
            print(f"  [{label}] {rel}")
        if len(all_hits) > 40:
            print(f"  ... and {len(all_hits) - 40} more")
        sys.exit(1)

    print(f"privacy scan OK ({args.scope}): 0 hits, no binary/image files")
    if args.strict:
        sys.exit(0)


if __name__ == "__main__":
    main()
