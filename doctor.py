#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
doctor.py - One-click health check for COMAC AgentOS
Stdlib only. Reads providers.json. Reports Python, paths, ports, providers,
disk, memory, watchdog. ANSI colors (works on Win10+ with chcp 65001).

Exit codes:
  0 = all green
  1 = warnings present (not blocking)
  2 = errors present (deployment affected)
"""
import json
import os
import shutil
import socket
import subprocess
import sys
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROV_FILE = SCRIPT_DIR / "providers.json"

G = "\033[92m"
Y = "\033[93m"
R = "\033[91m"
B = "\033[94m"
C = "\033[96m"
N = "\033[0m"
BOLD = "\033[1m"


def enable_ansi_on_windows():
    """Enable ANSI on Windows 10+ (no-op on non-Windows)."""
    if sys.platform == "win32":
        try:
            import ctypes

            kernel32 = ctypes.windll.kernel32
            handle = kernel32.GetStdHandle(-11)  # STD_OUTPUT_HANDLE
            mode = ctypes.c_uint32()
            if kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
                mode.value |= 0x4  # ENABLE_VIRTUAL_TERMINAL_PROCESSING
                kernel32.SetConsoleMode(handle, mode)
        except Exception:
            pass


def ok(msg):
    print(f"  {G}[OK]{N}    {msg}")


def warn(msg):
    print(f"  {Y}[WARN]{N}  {msg}")


def err(msg):
    print(f"  {R}[FAIL]{N}  {msg}")


def info(msg):
    print(f"  {C}[INFO]{N}  {msg}")


def header(msg):
    print()
    print(f"{BOLD}{B}{'=' * 60}{N}")
    print(f"{BOLD}{B}  {msg}{N}")
    print(f"{BOLD}{B}{'=' * 60}{N}")


def check_python():
    header("1. Python Environment")
    v = sys.version_info
    info(f"Version:  {v.major}.{v.minor}.{v.micro}")
    info(f"Path:     {sys.executable}")
    info(f"Platform: {sys.platform}")
    if (v.major, v.minor) >= (3, 11):
        ok(f"Python {v.major}.{v.minor} >= 3.11 (compatible)")
        return 0
    err(f"Python {v.major}.{v.minor} < 3.11 (required)")
    return 2


def check_paths():
    header("2. Critical Files & Directories")
    rc = 0
    must_exist = [
        ("providers.json", SCRIPT_DIR / "providers.json"),
        ("messages/zh.txt", SCRIPT_DIR / "messages" / "zh.txt"),
        ("probe.py", SCRIPT_DIR / "probe.py"),
        ("run.bat", SCRIPT_DIR / "run.bat"),
        ("agent-memory/", SCRIPT_DIR / "agent-memory"),
    ]
    for name, p in must_exist:
        if p.exists():
            ok(name)
        else:
            err(f"{name} MISSING")
            rc = 2

    opencode = SCRIPT_DIR / "bin" / "opencode.exe"
    if opencode.exists():
        ok("bin/opencode.exe (deployed)")
    else:
        warn("bin/opencode.exe missing - run setup.bat to extract")
        rc = max(rc, 1)

    return rc


def check_providers():
    header("3. Provider Registry")
    if not PROV_FILE.exists():
        err("providers.json not found")
        return 2
    try:
        cfg = json.loads(PROV_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        err(f"providers.json JSON parse error: {e}")
        return 2

    providers = cfg.get("providers", [])
    info(f"Total configured: {len(providers)}")
    enabled_count = sum(1 for p in providers if p.get("enabled", True))
    info(f"Enabled: {enabled_count}")

    rc = 0
    for p in providers:
        pid = p.get("id", "?")
        ptype = p.get("type", "?")
        display = p.get("display", pid)
        enabled = p.get("enabled", True)
        if enabled:
            ok(f"{display} [{ptype}]")
        else:
            warn(f"{display} [{ptype}] [DISABLED]")
    return rc


def check_provider_runtime():
    """Quick port+HTTP probe for enabled providers."""
    header("4. Provider Runtime (Quick Probe)")
    if not PROV_FILE.exists():
        warn("providers.json missing - skipped")
        return 1
    try:
        cfg = json.loads(PROV_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return 1

    rc = 0
    for p in cfg.get("providers", []):
        if not p.get("enabled", True):
            continue
        pid = p.get("id", "?")
        host = p.get("host", "127.0.0.1")
        port = p.get("port")
        base = p.get("baseURL", "")

        if port:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(1.5)
                try:
                    s.connect((host, int(port)))
                    ok(f"{pid}:{port} is listening")
                except (socket.timeout, ConnectionRefusedError, OSError):
                    warn(f"{pid}:{port} NOT listening (provider offline)")
                    rc = max(rc, 1)
        elif base:
            from urllib.request import urlopen
            from urllib.error import URLError
            try:
                urlopen(base.rstrip("/") + "/models", timeout=2).read()
                ok(f"{pid}: {base} reachable")
            except (URLError, Exception) as e:
                warn(f"{pid}: {base} unreachable ({e})")
                rc = max(rc, 1)
        else:
            info(f"{pid}: no port/baseURL to probe")
    return rc


def check_disk():
    header("5. Disk Space")
    try:
        total, used, free = shutil.disk_usage(SCRIPT_DIR)
    except Exception as e:
        warn(f"disk_usage failed: {e}")
        return 1
    free_gb = free / (1024 ** 3)
    total_gb = total / (1024 ** 3)
    used_pct = (used / total) * 100 if total else 0
    info(f"Total: {total_gb:.1f} GB  |  Free: {free_gb:.1f} GB  |  Used: {used_pct:.1f}%")
    if free_gb < 1:
        err(f"Free space < 1 GB ({free_gb:.2f} GB) - too low")
        return 2
    if free_gb < 5:
        warn(f"Free space < 5 GB ({free_gb:.2f} GB) - recommend cleanup")
        return 1
    ok(f"Free space {free_gb:.1f} GB is sufficient")
    return 0


def check_watchdog():
    header("6. Watchdog Process")
    if sys.platform != "win32":
        info("Non-Windows - skipped")
        return 0
    try:
        out = subprocess.run(
            ["tasklist", "/fi", "WINDOWTITLE eq COMAC-Watchdog"],
            capture_output=True, encoding="utf-8", errors="replace", timeout=3,
        ).stdout or ""
        if "cmd.exe" in out:
            ok("COMAC-Watchdog is running")
            return 0
        warn("COMAC-Watchdog NOT running (start with run.bat)")
        return 1
    except Exception as e:
        info(f"tasklist check failed: {e}")
        return 0


def check_memory_info():
    header("7. Memory (systeminfo)")
    if sys.platform != "win32":
        info("Non-Windows - skipped")
        return 0
    try:
        out = subprocess.run(
            ["systeminfo"], capture_output=True,
            encoding="utf-8", errors="replace", timeout=10,
        ).stdout or ""
        for line in out.splitlines():
            if "Total Physical Memory" in line or "Available Physical Memory" in line:
                info(line.strip())
        return 0
    except Exception as e:
        info(f"systeminfo failed: {e}")
        return 0


def check_memory_state():
    """Inspect agent-memory state.json."""
    header("8. Agent Memory State")
    state = SCRIPT_DIR / "agent-memory" / "state.json"
    if not state.exists():
        info("state.json not found (first run?)")
        return 0
    try:
        s = json.loads(state.read_text(encoding="utf-8"))
        # state.json actually uses snake_case (last_probe), but accept camelCase
        # as a fallback for forward compatibility.
        info(f"Last probe: {s.get('last_probe', s.get('lastProbe', 'never'))}")
        info(f"Online count: {s.get('online_count', s.get('onlineCount', 0))}")
        for pid, st in s.get("providers", {}).items():
            online_str = "online" if st.get("online") else "offline"
            print(f"  - {pid}: {online_str} (last seen {st.get('lastSeen', st.get('last_seen', '?'))})")
        ok("state.json readable")
        return 0
    except Exception as e:
        warn(f"state.json parse error: {e}")
        return 1


def main():
    enable_ansi_on_windows()
    print(f"{BOLD}{C}COMAC AgentOS - Doctor v1.0{N}")
    print(f"{C}Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{N}")
    print(f"{C}Path: {SCRIPT_DIR}{N}")

    results = []
    results.append(check_python())
    results.append(check_paths())
    results.append(check_providers())
    results.append(check_provider_runtime())
    results.append(check_disk())
    results.append(check_watchdog())
    results.append(check_memory_info())
    results.append(check_memory_state())

    header("Summary")
    rc = max(results) if results else 0
    if rc == 0:
        print(f"  {G}{BOLD}ALL CHECKS PASSED - system healthy{N}")
    elif rc == 1:
        print(f"  {Y}{BOLD}WARNINGS - operational but suboptimal{N}")
    else:
        print(f"  {R}{BOLD}ERRORS - run REPAIR MODE in run.bat{N}")
    return rc


if __name__ == "__main__":
    sys.exit(main())
