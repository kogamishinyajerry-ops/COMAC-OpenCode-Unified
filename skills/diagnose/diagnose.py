#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
diagnose.py - OpenCode skill: run a focused health check

This script reimplements the most useful checks from the root-level
doctor.py in a smaller, JSON-friendly form. Output is a sequence of
{check, status, detail} records. Final summary printed at end.

Stdlib only.
"""
import json
import os
import shutil
import socket
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = SCRIPT_DIR.parent.parent
PROV_FILE = ROOT / "providers.json"
STATE_FILE = ROOT / "agent-memory" / "state.json"


def _check_python():
    v = sys.version_info
    ok = (v.major, v.minor) >= (3, 11)
    return ("python", "ok" if ok else "error",
            f"{v.major}.{v.minor}.{v.micro}")


def _check_providers_json():
    if not PROV_FILE.exists():
        return ("providers.json", "error", "missing")
    try:
        cfg = json.loads(PROV_FILE.read_text(encoding="utf-8"))
        n = len(cfg.get("providers", []))
        return ("providers.json", "ok", f"{n} providers")
    except json.JSONDecodeError as e:
        return ("providers.json", "error", f"parse: {e}")


def _check_provider_ports():
    if not PROV_FILE.exists():
        return ("provider-ports", "warn", "providers.json missing")
    try:
        cfg = json.loads(PROV_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return ("provider-ports", "error", "providers.json invalid")

    results = []
    worst = "ok"
    for p in cfg.get("providers", []):
        if not p.get("enabled", True):
            continue
        pid = p.get("id", "?")
        host = p.get("host", "127.0.0.1")
        port = p.get("port")
        if not port:
            continue
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(1.5)
            try:
                s.connect((host, int(port)))
                results.append(f"{pid}=UP")
            except Exception:
                results.append(f"{pid}=DOWN")
                worst = "warn"
    if not results:
        return ("provider-ports", "ok", "no port providers")
    return ("provider-ports", worst, ", ".join(results))


def _check_disk():
    try:
        total, used, free = shutil.disk_usage(ROOT)
        free_gb = free / (1024 ** 3)
    except Exception as e:
        return ("disk", "warn", f"check failed: {e}")
    if free_gb < 1:
        return ("disk", "error", f"{free_gb:.2f} GB free")
    if free_gb < 5:
        return ("disk", "warn", f"{free_gb:.2f} GB free")
    return ("disk", "ok", f"{free_gb:.1f} GB free")


def _check_watchdog():
    if sys.platform != "win32":
        return ("watchdog", "ok", "non-Windows")
    try:
        out = subprocess.run(
            ["tasklist", "/fi", "WINDOWTITLE eq COMAC-Watchdog"],
            capture_output=True, encoding="utf-8", errors="replace", timeout=3,
        ).stdout or ""
        if "cmd.exe" in out:
            return ("watchdog", "ok", "running")
        return ("watchdog", "warn", "not running")
    except Exception as e:
        return ("watchdog", "warn", f"check failed: {e}")


def _check_state():
    if not STATE_FILE.exists():
        return ("state.json", "warn", "missing (first run?)")
    try:
        s = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        # state.json actually uses snake_case (last_probe); accept camelCase too.
        last = s.get("last_probe", s.get("lastProbe", "never"))
        return ("state.json", "ok", f"last probe: {last}")
    except Exception as e:
        return ("state.json", "warn", f"parse: {e}")


CHECKS = [_check_python, _check_providers_json, _check_provider_ports,
          _check_disk, _check_watchdog, _check_state]

STATUS_RANK = {"ok": 0, "warn": 1, "error": 2}


def main():
    json_mode = "--json" in sys.argv
    records = []
    for chk in CHECKS:
        records.append(chk())

    if json_mode:
        for name, status, detail in records:
            print(json.dumps({"check": name, "status": status, "detail": detail}, ensure_ascii=False))
    else:
        print(f"COMAC AgentOS - Diagnose")
        print(f"{'='*60}")
        for name, status, detail in records:
            sym = {"ok": "[OK]   ", "warn": "[WARN] ", "error": "[FAIL] "}.get(status, "[?]    ")
            print(f"  {sym}{name:<20} {detail}")
        print(f"{'='*60}")

    worst = max(STATUS_RANK.get(s, 0) for _, s, _ in records)
    return worst


if __name__ == "__main__":
    sys.exit(main())
