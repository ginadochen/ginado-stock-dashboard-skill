"""Data-source health self-check.

Probes ONLY reachability (TCP + a lightweight HTTPS request); does not fetch
market data or talk to MCP. Writes state/source-health.json under --root.
Always exits 0 so an unavailable source never aborts a scheduled task.
"""

from __future__ import annotations

import argparse
import json
import socket
import ssl
import urllib.request
from pathlib import Path

from common import (
    add_root_arg, resolve_root, instance_paths, load_yaml, load_json,
    write_json, now_iso,
)

TIMEOUT = 2.5
CONTROL_URL = "https://www.baidu.com"  # control site to distinguish local/network failure
HISTORY_LIMIT = 20


def probe_tcp(host: str, port: int = 443) -> tuple[bool, str]:
    try:
        with socket.create_connection((host, port), timeout=TIMEOUT):
            return True, "ok"
    except Exception as e:
        return False, type(e).__name__


def probe_http(url: str) -> tuple[int | None, str]:
    ctx = ssl.create_default_context()
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "stock-dashboard-health/0.1"})
        with urllib.request.urlopen(req, timeout=TIMEOUT, context=ctx) as r:
            return r.status, "ok"
    except Exception as e:
        return None, type(e).__name__


def main() -> None:
    ap = argparse.ArgumentParser(description="check data source reachability")
    add_root_arg(ap)
    ap.add_argument("--strict", action="store_true", help="exit non-zero if any source is down")
    args = ap.parse_args()

    root = resolve_root(args)
    P = instance_paths(root)
    inst = load_yaml(P["config"] / "instance.yaml")
    ar = load_yaml(P["config"] / "alert-rules.yaml")
    (P["state"]).mkdir(parents=True, exist_ok=True)

    # Targets come from instance config; the skill itself ships no endpoints.
    raw_targets = as_dict(load_yaml(P["config"] / "sources.yaml").get("targets"))
    targets = {}
    for name, spec in raw_targets.items():
        if isinstance(spec, dict) and spec.get("host"):
            targets[name] = {"host": str(spec["host"]), "url": str(spec.get("url") or "https://" + str(spec["host"]) + "/")}
    if not targets:
        targets = {
            "primary": {"status": "unconfigured"},
            "calibration": {"status": "unconfigured"},
        }

    result = {}
    for name, spec in targets.items():
        if spec.get("status") == "unconfigured":
            result[name] = {"status": "unconfigured", "tcp_reachable": None,
                            "http_status": None, "note": "no endpoint configured (demo/offline mode)"}
            continue
        tcp_ok, tcp_note = probe_tcp(spec["host"])
        http_status, http_note = probe_http(spec["url"]) if tcp_ok else (None, "skipped")
        status = "up" if (tcp_ok and http_status and http_status < 500) else "down"
        result[name] = {
            "status": status, "tcp_reachable": tcp_ok, "tcp_error": tcp_note,
            "http_status": http_status, "http_error": http_note,
        }

    ctl_status, ctl_note = probe_http(CONTROL_URL)
    control_ok = bool(ctl_status and ctl_status < 500)

    state_path = P["state"] / "source-health.json"
    prev = load_json(state_path)
    history = list(prev.get("history") or [])
    history.append({"as_of": now_iso(), "sources": {k: v.get("status") for k, v in result.items()},
                    "control_ok": control_ok})
    history = history[-HISTORY_LIMIT:]

    write_json(state_path, {
        "source": "check_sources.py", "as_of": now_iso(),
        "control": {"url": CONTROL_URL, "http_status": ctl_status, "error": ctl_note,
                    "ok": control_ok},
        "sources": result, "history": history,
        "policy": "unavailable => skip all calls to that source, no retry, no reconnect; "
                  "on recovery backfill percentiles and rebuild pages",
    })

    # Append a one-line, de-identified log (never contains account data).
    (P["logs"]).mkdir(parents=True, exist_ok=True)
    log = P["logs"] / f"{now_iso()[:7]}.log"
    line = (f"{now_iso()} | source-health | " +
            ", ".join(f"{k}={v.get('status')}" for k, v in result.items()) +
            f" | control_ok={control_ok}\n")
    with open(log, "a", encoding="utf-8") as f:
        f.write(line)

    for k, v in result.items():
        print(f"{k}: {v.get('status')} (tcp={v.get('tcp_reachable')}, http={v.get('http_status')})")
    print(f"control: {'ok' if control_ok else 'unreachable'}")

    if args.strict and any(v.get("status") == "down" for v in result.values()):
        raise SystemExit(1)


def as_dict(v):
    return v if isinstance(v, dict) else {}


if __name__ == "__main__":
    main()
