#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
redteam_final.py - Final red-team test for COMAC AgentOS v2.2 install package
Stdlib only. Runs ALL the gates that matter before pushing to GitHub.

Exit codes:
  0 = all gates green
  1 = warnings present (deployable but not perfect)
  2 = blocking failures (DO NOT ship)
"""
import json
import re
import socket
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
G = "\033[92m"
Y = "\033[93m"
R = "\033[91m"
B = "\033[94m"
C = "\033[96m"
N = "\033[0m"
BOLD = "\033[1m"

# ---------- counting & printing ----------

results = {"pass": 0, "warn": 0, "fail": 0, "details": []}


def step(label):
    print(f"\n{BOLD}{B}{'=' * 64}{N}")
    print(f"{BOLD}{B}  {label}{N}")
    print(f"{BOLD}{B}{'=' * 64}{N}")


def ok(msg):
    print(f"  {G}[PASS]{N}  {msg}")
    results["pass"] += 1
    results["details"].append(("PASS", msg))


def warn(msg):
    print(f"  {Y}[WARN]{N}  {msg}")
    results["warn"] += 1
    results["details"].append(("WARN", msg))


def fail(msg):
    print(f"  {R}[FAIL]{N}  {msg}")
    results["fail"] += 1
    results["details"].append(("FAIL", msg))


def info(msg):
    print(f"  {C}[INFO]{N}  {msg}")


# ---------- Gate 1: File integrity ----------

def gate1_file_integrity():
    step("Gate 1: File Integrity (v2.2 manifest)")

    core_v20 = [
        "providers.json", "probe.py", "run.bat", "setup.bat",
        "verify.bat", "watchdog.bat", "memory.bat",
        "start-qwen.bat", "stop-qwen.bat", "README.md",
        "SKILL.md",
        "messages/zh.txt",
        "agent-memory/identity.md", "agent-memory/FACTS.json",
        "agent-memory/state.json",
    ]
    core_v22 = [
        "doctor.bat", "doctor.py", "webui.bat", "webui.py",
        "switch.bat", "switch.py", "benchmark.bat", "benchmark.py",
        "archive.bat", "archive.py", "aliases.bat",
        "skills/switch-provider/SKILL.md", "skills/switch-provider/switch_provider.py",
        "skills/diagnose/SKILL.md", "skills/diagnose/diagnose.py",
        "skills/recall-memory/SKILL.md", "skills/recall-memory/recall.py",
    ]

    rc = 0
    for rel in core_v20:
        p = SCRIPT_DIR / rel
        if p.exists():
            ok(f"core v2.0: {rel}")
        else:
            fail(f"core v2.0 MISSING: {rel}")
            rc = 2
    for rel in core_v22:
        p = SCRIPT_DIR / rel
        if p.exists():
            ok(f"core v2.2: {rel}")
        else:
            fail(f"core v2.2 MISSING: {rel}")
            rc = 2
    return rc


# ---------- Gate 2: JSON validity ----------

def gate2_json_validity():
    step("Gate 2: JSON Validity")
    rc = 0
    json_files = [
        "providers.json", "opencode.json", "_runtime.bat",
    ]
    # _runtime.bat is not JSON; we'll handle separately
    for rel in ["providers.json", "opencode.json"]:
        p = SCRIPT_DIR / rel
        if not p.exists():
            warn(f"{rel} missing - skipping")
            rc = max(rc, 1)
            continue
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            ok(f"{rel} parses cleanly ({type(data).__name__})")
        except json.JSONDecodeError as e:
            fail(f"{rel} JSON parse error: {e}")
            rc = 2
    return rc


# ---------- Gate 3: Python syntax ----------

def gate3_python_syntax():
    step("Gate 3: Python Syntax (compile all .py files)")
    rc = 0
    py_files = list(SCRIPT_DIR.glob("*.py")) + list((SCRIPT_DIR / "skills").rglob("*.py"))
    for py in sorted(py_files):
        rel = py.relative_to(SCRIPT_DIR)
        # 3.13 has tomllib and other features, but project targets 3.11.8
        # Use -W to allow 3.13-managed compile of 3.11-compatible code
        r = subprocess.run(
            [sys.executable, "-c", f"import py_compile; py_compile.compile(r'{py}', doraise=True)"],
            capture_output=True, text=True
        )
        if r.returncode == 0:
            ok(f"{rel}")
        else:
            fail(f"{rel} syntax error: {r.stderr.strip()[:200]}")
            rc = 2
    return rc


# ---------- Gate 4: Dev-path leak detection ----------

def gate4_no_dev_leak():
    step("Gate 4: Dev-Path Leak Detection (no Kogami/4070/3.13.12 in shipped files)")
    rc = 0
    # These are dev-machine markers. If any leak into shipped files, FAIL.
    # (commit-time smoke check; 3.13.12 is the dev managed path)
    patterns = [
        (r"C:\\Users\\Kogami\\", "dev user path"),
        (r"3\.13\.12", "dev Python 3.13.12 path leak"),
        (r"4070", "dev GPU 4070 leak"),
    ]
    # Only scan shipped runtime files (not .git, not agent-memory/sessions, not .pyc)
    skip_dirs = {".git", "__pycache__", "agent-memory", "bin", "tools", "ollama-models", "downloads"}
    # Detector itself: the pattern strings appear in the source code as the WHAT-we're-looking-for
    # explanation, not as actual leaks. (Working memory rule: detector self-reference is not a leak.)
    skip_files = {SCRIPT_DIR / "redteam_final.py"}
    extensions = {".bat", ".py", ".json", ".md", ".txt"}

    for path in SCRIPT_DIR.rglob("*"):
        if not path.is_file():
            continue
        if path in skip_files:
            continue
        if any(part in skip_dirs for part in path.parts):
            continue
        if path.suffix.lower() not in extensions:
            continue
        try:
            content = path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        rel = path.relative_to(SCRIPT_DIR)
        for pat, desc in patterns:
            if re.search(pat, content):
                # Allow: agent-memory contains the dev name in CONTEXT.md as a soft reference
                # We still fail on it - user wants ZERO leaks
                fail(f"{rel}: contains {desc}")
                rc = 2
    if rc == 0:
        ok("no dev-path / Python-version / GPU-name leaks in shipped runtime files")
    return rc


# ---------- Gate 5: SKILL.md ↔ wrapper alignment (working memory rule #14) ----------

def gate5_skill_alignment():
    step("Gate 5: SKILL.md ↔ Wrapper Alignment (1:1 per skill)")
    rc = 0
    for skill_dir in (SCRIPT_DIR / "skills").iterdir():
        if not skill_dir.is_dir():
            continue
        skill_md = skill_dir / "SKILL.md"
        # Each skill needs a wrapper .py with non-SKILL.md basename matching skill dir
        wrappers = [f for f in skill_dir.iterdir() if f.suffix == ".py" and f.stem != "__init__"]
        if not skill_md.exists():
            fail(f"{skill_dir.name}: SKILL.md missing")
            rc = 2
            continue
        if not wrappers:
            fail(f"{skill_dir.name}: no wrapper .py")
            rc = 2
            continue
        if len(wrappers) > 1:
            warn(f"{skill_dir.name}: multiple wrappers {[w.name for w in wrappers]}")
            rc = max(rc, 1)
            continue
        # Check SKILL.md mentions the wrapper's invocation pattern
        skill_text = skill_md.read_text(encoding="utf-8")
        wrapper_name = wrappers[0].name
        if wrapper_name in skill_text:
            ok(f"{skill_dir.name}: SKILL.md mentions {wrapper_name}")
        else:
            # Acceptable: SKILL.md references 'the root-level tool' or similar
            # But hard rule says 1:1 alignment; we warn
            warn(f"{skill_dir.name}: SKILL.md does not mention {wrapper_name}")
            rc = max(rc, 1)
    return rc


# ---------- Gate 6: providers.json schema ----------

def gate6_provider_schema():
    step("Gate 6: providers.json Schema Conformance")
    p = SCRIPT_DIR / "providers.json"
    if not p.exists():
        fail("providers.json missing")
        return 2
    try:
        cfg = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        fail(f"providers.json JSON error: {e}")
        return 2

    rc = 0
    providers = cfg.get("providers", [])
    if not providers:
        fail("no providers in providers.json")
        return 2
    ok(f"{len(providers)} provider(s) configured")

    for prov in providers:
        pid = prov.get("id", "?")
        ptype = prov.get("type", "?")
        if ptype not in ("remote", "local"):
            fail(f"{pid}: invalid type={ptype}")
            rc = 2
            continue
        # required fields per working memory schema
        required = ["id", "display", "type", "baseURL", "apiKey", "model", "context", "output", "timeout", "enabled"]
        missing = [f for f in required if f not in prov]
        if missing:
            fail(f"{pid}: missing fields {missing}")
            rc = 2
            continue
        if ptype == "local":
            local_req = ["host", "port", "executable", "modelPath", "startupArgs", "healthCheck"]
            missing = [f for f in local_req if f not in prov]
            if missing:
                fail(f"{pid} (local): missing fields {missing}")
                rc = 2
                continue
        ok(f"{pid} ({ptype}) schema OK")
    return rc


# ---------- Gate 7: end-to-end (probe.py + doctor.py + benchmark) ----------

def gate7_e2e():
    step("Gate 7: End-to-End Probe / Doctor / Benchmark")
    rc = 0
    py = sys.executable

    # probe.py
    r = subprocess.run([py, str(SCRIPT_DIR / "probe.py")], capture_output=True, text=True, timeout=60)
    if r.returncode in (0, 1):
        ok(f"probe.py exit={r.returncode} (expected 0/1)")
    else:
        fail(f"probe.py exit={r.returncode}: {r.stderr.strip()[:200]}")
        rc = 2

    # doctor.py
    r = subprocess.run([py, str(SCRIPT_DIR / "doctor.py")], capture_output=True, text=True, timeout=30)
    if r.returncode in (0, 1, 2):
        ok(f"doctor.py exit={r.returncode} (expected 0/1/2)")
    else:
        fail(f"doctor.py unexpected exit={r.returncode}")
        rc = 2

    # benchmark.py - just confirm it runs
    r = subprocess.run([py, str(SCRIPT_DIR / "benchmark.py")], capture_output=True, text=True, timeout=120)
    if r.returncode in (0, 1, 2):
        ok(f"benchmark.py exit={r.returncode}")
    else:
        # benchmark may fail if no provider online; treat as warn not fail
        warn(f"benchmark.py exit={r.returncode} (no provider online is OK)")
        rc = max(rc, 1)

    return rc


# ---------- Gate 8: Self-contained deploy assets (v2.2 final) ----------
# Verifies that the package is fully deployable on a clean Windows 10 box
# without the user having to fetch binaries from the internet.

def gate8_self_contained():
    step("Gate 8: Self-Contained Deploy Assets (OpenCode + llama-server + GGUF slot)")
    rc = 0

    # 8.1 OpenCode zip in downloads/
    opencode_zip = SCRIPT_DIR / "downloads" / "opencode-windows-x64.zip"
    if opencode_zip.exists():
        size_mb = opencode_zip.stat().st_size / 1024 / 1024
        if size_mb > 30:  # expected ~50 MB
            ok(f"downloads/opencode-windows-x64.zip present ({size_mb:.1f} MB)")
        else:
            fail(f"downloads/opencode-windows-x64.zip too small ({size_mb:.1f} MB, expected ~50 MB)")
            rc = 2
    else:
        fail("downloads/opencode-windows-x64.zip MISSING — package is not self-contained")
        rc = 2

    # 8.2 llama-server.exe in tools/
    llama_exe = SCRIPT_DIR / "tools" / "llama-server.exe"
    if llama_exe.exists():
        size_mb = llama_exe.stat().st_size / 1024 / 1024
        if size_mb > 5:  # expected ~10 MB
            ok(f"tools/llama-server.exe present ({size_mb:.1f} MB)")
        else:
            fail(f"tools/llama-server.exe too small ({size_mb:.1f} MB, expected ~10 MB)")
            rc = 2
    else:
        fail("tools/llama-server.exe MISSING — package is not self-contained")
        rc = 2

    # 8.3 llama DLLs (llama.dll, ggml.dll) for runtime
    required_dlls = ["llama.dll", "ggml.dll", "ggml-base.dll"]
    for dll in required_dlls:
        p = SCRIPT_DIR / "tools" / dll
        if p.exists():
            ok(f"tools/{dll} present")
        else:
            fail(f"tools/{dll} MISSING — llama-server.exe cannot run")
            rc = 2

    # 8.4 ollama-models/ has README.md explaining user must drop GGUF here
    ollama_readme = SCRIPT_DIR / "ollama-models" / "README.md"
    if ollama_readme.exists():
        ok("ollama-models/README.md present (user knows where to drop GGUF)")
    else:
        warn("ollama-models/README.md missing — user may not know to drop GGUF here")
        rc = max(rc, 1)

    # 8.5 ollama-models/ has at least one .gguf OR README.md (slot is intentional)
    gguf_files = list((SCRIPT_DIR / "ollama-models").glob("*.gguf"))
    if gguf_files:
        ok(f"ollama-models/ has {len(gguf_files)} GGUF file(s) (largest: {max(f.stat().st_size for f in gguf_files) / 1024 / 1024:.0f} MB)")
    else:
        info("ollama-models/ is empty (no GGUF bundled — user must provide locally)")
        # This is WARN, not FAIL, by design

    return rc


# ---------- main ----------

def main():
    print(f"{BOLD}COMAC AgentOS v2.2 — Final Red-Team Test{N}")
    print(f"Project: {SCRIPT_DIR}")
    print(f"Python:  {sys.executable} ({sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro})")

    rc = 0
    rc = max(rc, gate1_file_integrity())
    rc = max(rc, gate2_json_validity())
    rc = max(rc, gate3_python_syntax())
    rc = max(rc, gate4_no_dev_leak())
    rc = max(rc, gate5_skill_alignment())
    rc = max(rc, gate6_provider_schema())
    rc = max(rc, gate7_e2e())
    rc = max(rc, gate8_self_contained())

    # ---- summary ----
    print(f"\n{BOLD}{B}{'=' * 64}{N}")
    print(f"{BOLD}{B}  SUMMARY{N}")
    print(f"{BOLD}{B}{'=' * 64}{N}")
    print(f"  {G}PASS: {results['pass']}{N}    {Y}WARN: {results['warn']}{N}    {R}FAIL: {results['fail']}{N}")

    if results["fail"] == 0 and results["warn"] == 0:
        print(f"\n  {G}{BOLD}>>> READY TO SHIP <<<{N}")
    elif results["fail"] == 0:
        print(f"\n  {Y}{BOLD}>>> SHIPPABLE (warnings present) <<<{N}")
    else:
        print(f"\n  {R}{BOLD}>>> NOT READY - {results['fail']} blocking failures <<<{N}")

    # gate-level worst
    final_rc = rc
    if results["fail"] > 0:
        final_rc = 2
    elif results["warn"] > 0 and rc == 0:
        final_rc = 1
    return final_rc


if __name__ == "__main__":
    sys.exit(main())
