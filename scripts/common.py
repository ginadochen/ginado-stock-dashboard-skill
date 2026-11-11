"""Shared helpers for stock-dashboard scripts.

All scripts take --root explicitly. Nothing here infers an instance directory
from __file__: the skill package is read-only and must never receive outputs.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from datetime import datetime

try:  # PyYAML is optional; demo mode must run with the standard library only.
    import yaml  # type: ignore

    _HAS_YAML = True
except ImportError:  # pragma: no cover
    yaml = None  # type: ignore
    _HAS_YAML = False


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def add_root_arg(parser: argparse.ArgumentParser, help_text: str = "instance root directory",
                 required: bool = True) -> None:
    parser.add_argument("--root", required=required, help=help_text)


def require_root(parser, args) -> None:
    """For scripts with a --self-test mode, enforce --root only for real runs."""
    if not getattr(args, "root", None):
        parser.error("--root is required unless --self-test is used")


def resolve_root(args) -> Path:
    root = Path(args.root).expanduser().resolve()
    if not root.is_dir():
        raise SystemExit(f"instance root does not exist: {root}")
    return root


def instance_paths(root: Path) -> dict:
    return {
        "root": root,
        "config": root / "config",
        "state": root / "state",
        "data": root / "data",
        "dashboard": root / "dashboard",
        "stocks": root / "dashboard" / "stocks",
        "reports": root / "reports",
        "logs": root / "logs",
        "tmp": root / "tmp",
        "archive": root / "archive",
    }


# ---------------------------------------------------------------------------
# Minimal YAML subset parser (standard-library only)
# Supports: comments, nested mappings, sequences, scalars, quoted strings.
# Templates intentionally avoid flow collections, anchors and block scalars.
# ---------------------------------------------------------------------------

def _scalar(text: str):
    t = text.strip()
    if t == "" or t in ("null", "~", "None"):
        return None
    if t.lower() in ("true", "yes", "on"):
        return True
    if t.lower() in ("false", "no", "off"):
        return False
    if (t.startswith('"') and t.endswith('"')) or (t.startswith("'") and t.endswith("'")):
        return t[1:-1]
    if re.fullmatch(r"-?\d+", t):
        return int(t)
    if re.fullmatch(r"-?\d+\.\d+", t):
        return float(t)
    return t


def _strip_comment(line: str) -> str:
    out, quote = [], None
    for ch in line:
        if quote:
            out.append(ch)
            if ch == quote:
                quote = None
        elif ch in ('"', "'"):
            quote = ch
            out.append(ch)
        elif ch == "#":
            break
        else:
            out.append(ch)
    return "".join(out).rstrip()


def _extract_block_scalars(text: str):
    """Pull `key: |` / `key: >` blocks out before parsing.

    The minimal parser only handles flow-free mappings/sequences; block
    scalars contain colons and '#' characters that would otherwise be
    mis-parsed. Blocks are replaced by a quoted sentinel and restored later.
    """
    lines = text.splitlines()
    blocks, out = [], []
    i = 0
    while i < len(lines):
        raw = lines[i]
        stripped = raw.strip()
        m = re.match(r"^(\s*)([^:#]+):\s*([|>])[+-]?\s*$", raw)
        if not m:
            out.append(raw)
            i += 1
            continue
        key_indent, key, style = len(m.group(1)), m.group(2).strip(), m.group(3)
        body, i = [], i + 1
        while i < len(lines):
            nxt = lines[i]
            if nxt.strip() and (len(nxt) - len(nxt.lstrip(" "))) <= key_indent:
                break
            body.append(nxt)
            i += 1
        # strip the common indentation of the block body
        nonblank = [len(x) - len(x.lstrip(" ")) for x in body if x.strip()]
        common = min(nonblank) if nonblank else 0
        value = "\n".join(x[common:] if len(x) >= common else x for x in body)
        if style == ">":
            value = re.sub(r"(?<!\n)\n(?!\n)", " ", value)
        idx = len(blocks)
        blocks.append(value)
        out.append(f"{' ' * key_indent}{key}: \"<<<BLOCK{idx}>>>\"")
    return "\n".join(out), blocks


def _restore_blocks(obj, blocks):
    if isinstance(obj, str):
        m = re.fullmatch(r"<<<BLOCK(\d+)>>>", obj)
        if m:
            return blocks[int(m.group(1))]
        return obj
    if isinstance(obj, list):
        return [_restore_blocks(v, blocks) for v in obj]
    if isinstance(obj, dict):
        return {k: _restore_blocks(v, blocks) for k, v in obj.items()}
    return obj


def mini_yaml_load(text: str):
    text, blocks = _extract_block_scalars(text)
    rows = []
    for raw in text.splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        line = _strip_comment(raw)
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip(" "))
        rows.append((indent, line.strip()))

    def parse(pos: int, indent: int):
        # Decide list vs mapping by the first row at this level.
        is_list = rows[pos][1].startswith("- ") or rows[pos][1] == "-"
        container = [] if is_list else {}
        while pos < len(rows):
            ind, body = rows[pos]
            if ind < indent:
                break
            if ind > indent:
                raise ValueError(f"unexpected indent near: {body}")
            if is_list:
                if not (body.startswith("- ") or body == "-"):
                    break
                item = body[1:].strip()
                pos += 1
                if ":" in item and not item.startswith(("{", "[")):
                    key, _, val = item.partition(":")
                    obj = {key.strip(): _scalar(val)}
                    if pos < len(rows) and rows[pos][0] > indent:
                        sub, pos = parse(pos, rows[pos][0])
                        if isinstance(sub, dict):
                            obj.update(sub)
                    container.append(obj)
                elif item:
                    container.append(_scalar(item))
                else:
                    if pos < len(rows) and rows[pos][0] > indent:
                        sub, pos = parse(pos, rows[pos][0])
                        container.append(sub)
                    else:
                        container.append(None)
            else:
                if body.startswith("- "):
                    break
                key, _, val = body.partition(":")
                key = key.strip()
                pos += 1
                if val.strip():
                    container[key] = _scalar(val)
                else:
                    if pos < len(rows) and rows[pos][0] > indent:
                        sub, pos = parse(pos, rows[pos][0])
                        container[key] = sub
                    else:
                        container[key] = {}
        return container, pos

    if not rows:
        return {}
    result, _ = parse(0, rows[0][0])
    return _restore_blocks(result, blocks)


def load_yaml(path: Path):
    if not path.exists():
        return {}
    text = path.read_text(encoding="utf-8")
    if _HAS_YAML:
        return yaml.safe_load(text) or {}
    return mini_yaml_load(text) or {}


def load_json(path: Path):
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# Snapshot selection
# ---------------------------------------------------------------------------

def latest_snapshot_with(root: Path, filename: str) -> Path | None:
    """Pick the newest dated dir that actually contains `filename`.

    Never pick "the newest directory": same-day dirs often hold only a
    partial snapshot (e.g. only earnings.json, no quotes.json).
    """
    candidates = [
        p for p in (root / "data").glob("*/*")
        if p.is_dir() and (p / filename).is_file()
    ]
    if not candidates:
        return None
    return sorted(candidates, key=lambda p: p.name)[-1]


# ---------------------------------------------------------------------------
# Formatting / escaping
# ---------------------------------------------------------------------------

def esc(s) -> str:
    return (
        str(s if s is not None else "")
        .replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        .replace('"', "&quot;").replace("'", "&#39;")
    )


def num(v, d=2, suffix="") -> str:
    if v is None or v == "":
        return "—"
    try:
        return f"{float(v):,.{d}f}{suffix}"
    except (TypeError, ValueError):
        return esc(v)


def signed(v, d=2) -> str:
    if v is None or v == "":
        return "—"
    try:
        f = float(v)
        return f"{'+' if f > 0 else ''}{f:,.{d}f}"
    except (TypeError, ValueError):
        return esc(v)


def cls(v) -> str:
    """Chinese market convention: up = red, down = green."""
    try:
        f = float(v)
    except (TypeError, ValueError):
        return ""
    return "up" if f > 0 else ("down" if f < 0 else "")


def chg(base, now) -> float | None:
    try:
        b, n = float(base), float(now)
        return None if b == 0 else (n - b) / b * 100
    except (TypeError, ValueError):
        return None


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


DISCLAIMER_SHORT = (
    "免责声明：以上内容仅供参考，不构成投资建议。市场有风险，投资需谨慎。"
)

DISCLAIMER_FULL = (
    "免责声明：以上内容基于公开数据和量化分析，仅供参考，不构成投资建议。"
    "市场有风险，投资需谨慎。任何投资决策应结合个人风险承受能力、资金状况"
    "和投资目标独立判断，必要时咨询持牌专业机构。过往表现不预示未来收益。"
)
