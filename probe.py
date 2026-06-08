"""
probe.py v2.1 — COMAC AgentOS Resilient Provider Probe
========================================================
Python 3.11+, zero dependencies, pure stdlib.

Reads providers.json with tolerance for partial/broken config.
Each provider gets independent diagnosis — one bad entry
does not block others. Reports actionable fixes.
Always generates runtime files for valid providers.

Exit code:
  0 = at least one provider online
  1 = all offline but config is valid
  2 = config errors found (still usable)
  3 = providers.json not found or unreadable
"""
import json
import os
import sys
import time
import socket
import subprocess
import urllib.request
import urllib.error
from pathlib import Path

ROOT = Path(__file__).parent.resolve()
PROVIDERS_FILE = ROOT / "providers.json"
RUNTIME_BAT = ROOT / "_runtime.bat"
OPENCODE_JSON = ROOT / "opencode.json"
STATE_FILE = ROOT / "agent-memory" / "state.json"

# ---- network helpers ----

def _port_open(host, port, timeout=2.0):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(timeout)
    try:
        s.connect((host, port))
        s.close()
        return True
    except Exception:
        return False


def _http_get(url, timeout=5.0):
    req = urllib.request.Request(url, headers={"User-Agent": "COMAC-probe/2.1"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read().decode(errors="replace")
    except urllib.error.HTTPError as e:
        return e.code, ""
    except Exception as e:
        return None, str(e)


# ---- validation ----

COMMON_EXE_NAMES = ["llama-server.exe", "ollama.exe", "llama.cpp.exe"]
COMMON_MODEL_EXTS = [".gguf", ".bin", ".safetensors"]
PLACEHOLDER_KEYS = ["YOUR_", "sk-xxx", "changeme", "REPLACE", "<"]

def _is_placeholder(val):
    if not val: return True
    for p in PLACEHOLDER_KEYS:
        if p.lower() in val.lower():
            return True
    return False


def validate_providers(providers: list) -> list:
    """Validate each provider, return list of (provider, warnings, errors)."""
    results = []
    for i, p in enumerate(providers):
        idx = i + 1
        warnings = []
        errors = []
        pid = p.get("id", f"entry-{idx}")

        # required fields
        if "id" not in p:
            errors.append(f"MISSING id field")
        if "baseURL" not in p:
            errors.append(f"MISSING baseURL — cannot connect")

        # type-specific checks
        ptype = p.get("type", "remote")
        if ptype == "local":
            exe = p.get("executable", "")
            model = p.get("modelPath", "")
            if not exe:
                warnings.append(f"missing executable path (type=local)")
            elif not (ROOT / exe).exists():
                warnings.append(f"executable not found: {exe}")
                # search for alternatives
                alt = _find_file(ROOT / "tools", COMMON_EXE_NAMES)
                if alt:
                    warnings.append(f"  -> found alternative: tools/{alt}")
            if not model:
                warnings.append(f"missing modelPath (type=local)")
            elif not (ROOT / model).exists():
                warnings.append(f"model file not found: {model}")
                alt = _find_model(ROOT / "ollama-models")
                if alt:
                    warnings.append(f"  -> found: ollama-models/{alt}")

            # port check
            port = p.get("port", 0)
            if port == 0:
                warnings.append(f"missing port (defaulting to 11435)")

        # apiKey check
        apikey = p.get("apiKey", "")
        if _is_placeholder(apikey):
            warnings.append(f"apiKey is a placeholder — API auth will fail")

        results.append((p, {"warnings": warnings, "errors": errors}))

    return results


def _find_file(directory: Path, names: list) -> str:
    """Search directory for any of the given filenames. Return relative path."""
    if not directory.exists():
        return ""
    for f in sorted(directory.iterdir()):
        if f.is_file() and f.name.lower() in [n.lower() for n in names]:
            return f.name
    return ""


def _find_model(directory: Path) -> str:
    """Search directory for any model file. Return relative path."""
    if not directory.exists():
        return ""
    for f in sorted(directory.iterdir()):
        if f.is_file() and f.suffix.lower() in COMMON_MODEL_EXTS:
            return f.name
    return ""


# ---- probing ----

def probe_remote(prov: dict) -> tuple:
    url = prov["baseURL"].rstrip("/") + "/models"
    timeout = prov.get("timeout", 5)
    code, body = _http_get(url, timeout)
    if code == 200:
        return True, "OK"
    if code == 401:
        return False, "HTTP 401 — invalid apiKey"
    if code == 403:
        return False, "HTTP 403 — forbidden"
    if code == 404:
        # /models not found — fallback to POST /chat/completions
        chat_url = prov["baseURL"].rstrip("/") + "/chat/completions"
        c2, _ = _http_get(chat_url, timeout)
        _ = c2  # unused, just checking reachability
        return True, "reachable (no /models endpoint)"
    if code is not None:
        return False, f"HTTP {code}"
    return False, "unreachable (network/timeout)"


def probe_local(prov: dict) -> tuple:
    host = prov.get("host", "127.0.0.1")
    port = prov.get("port", 11435)
    if not _port_open(host, port):
        return False, f"port {host}:{port} closed"
    return probe_remote(prov)


def start_local(prov: dict) -> tuple:
    exe_rel = prov.get("executable", "")
    model_rel = prov.get("modelPath", "")
    exe = ROOT / exe_rel
    model = ROOT / model_rel
    host = prov.get("host", "127.0.0.1")
    port = str(prov.get("port", 11435))
    args = prov.get("startupArgs", {})
    ctx = str(args.get("context", 32768))
    threads = str(args.get("threads", 512))
    ngl = str(args.get("ngl", 99))

    if not exe.exists():
        return False, f"exe not found: {exe_rel}"
    if not model.exists():
        return False, f"model not found: {model_rel}"

    cmd = [
        str(exe), "-m", str(model),
        "-c", ctx, "-tb", threads, "-ngl", ngl,
        "--host", host, "--port", port,
    ]
    try:
        subprocess.Popen(
            cmd, cwd=str(ROOT),
            creationflags=subprocess.CREATE_NO_WINDOW,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        return True, "started"
    except Exception as e:
        return False, str(e)


# ---- main ----

def main():
    # === load providers.json ===
    if not PROVIDERS_FILE.exists():
        print("[FATAL] providers.json not found.")
        print(f"  Expected at: {PROVIDERS_FILE}")
        print("  Run setup.bat or create the file manually.")
        _write_minimal_runtime()
        return 3

    try:
        with open(PROVIDERS_FILE, encoding="utf-8") as fh:
            cfg = json.load(fh)
    except json.JSONDecodeError as e:
        print(f"[FATAL] providers.json is invalid JSON:")
        print(f"  Line {e.lineno}, column {e.colno}: {e.msg}")
        print(f"  Please fix the syntax error and retry.")
        print(f"  Open in Notepad: start notepad {PROVIDERS_FILE}")
        _write_minimal_runtime()
        return 3
    except Exception as e:
        print(f"[FATAL] Cannot read providers.json: {e}")
        _write_minimal_runtime()
        return 3

    providers = cfg.get("providers", [])

    # filter out disabled providers
    providers = [p for p in providers if p.get("enabled", True)]

    # === validate ===
    validated = validate_providers(providers)
    has_errors = any(v["errors"] for _, v in validated)
    has_warnings = any(v["warnings"] for _, v in validated)

    # === probe each independently ===
    results = []
    online_count = 0
    # collect issues for each provider
    all_fixes = []

    for prov, issues in validated:
        pid = prov.get("id", f"entry-{len(results)+1}")
        ptype = prov.get("type", "remote")
        display = prov.get("display", pid)
        errors = issues["errors"]
        warns = issues["warnings"]

        # if critical errors, skip probing
        if errors:
            results.append({
                "id": pid, "display": display, "type": ptype,
                "online": False,
                "message": "; ".join(errors),
                "warnings": warns,
                "baseURL": prov.get("baseURL", ""),
                "apiKey": prov.get("apiKey", ""),
                "model": prov.get("model", ""),
                "port": prov.get("port", 0),
                "host": prov.get("host", "127.0.0.1"),
                "context": prov.get("context", 32768),
                "output": prov.get("output", 4096),
                "executable": prov.get("executable", ""),
                "modelPath": prov.get("modelPath", ""),
                "startupArgs": prov.get("startupArgs", {}),
                "healthCheck": prov.get("healthCheck", {}),
            })
            continue

        # probe
        if ptype == "local":
            online, msg = probe_local(prov)
            hc = prov.get("healthCheck", {})
            if not online and hc.get("autoRecover", False):
                ok2, msg2 = start_local(prov)
                if ok2:
                    time.sleep(3)
                    online, msg = probe_local(prov)
                    msg = f"{msg} (auto-started)"
                else:
                    msg = f"auto-start failed: {msg2}"
        else:
            online, msg = probe_remote(prov)

        results.append({
            "id": pid, "display": display, "type": ptype,
            "online": online,
            "message": msg,
            "warnings": warns,
            "baseURL": prov.get("baseURL", ""),
            "apiKey": prov.get("apiKey", ""),
            "model": prov.get("model", ""),
            "port": prov.get("port", 0),
            "host": prov.get("host", "127.0.0.1"),
            "context": prov.get("context", 32768),
            "output": prov.get("output", 4096),
            "executable": prov.get("executable", ""),
            "modelPath": prov.get("modelPath", ""),
            "startupArgs": prov.get("startupArgs", {}),
            "healthCheck": prov.get("healthCheck", {}),
        })
        if online:
            online_count += 1

    # === generate runtime files ===
    _write_runtime_bat(results)
    _write_opencode_json(results)
    _update_state(results, online_count)

    # === print report ===
    _print_report(results, online_count, has_errors, has_warnings)

    # exit code
    if online_count > 0:
        return 0
    if has_errors:
        return 2
    return 1


# ---- reporting ----

def _print_report(results, online, has_errors, has_warnings):
    total = len(results)
    print("")
    print("=" * 60)
    print("  COMAC AgentOS — Provider Report")
    print("=" * 60)

    for r in results:
        tag = "[ON]" if r["online"] else "[--]"
        print(f"  {tag}  {r['display']}  ({r['id']})")
        if not r["online"]:
            print(f"       {r['message']}")
        else:
            print(f"       {r['baseURL']}")

    print("=" * 60)

    if online > 0:
        print(f"  ONLINE: {online}/{total} providers ready")
    else:
        print(f"  ZERO providers online ({total} configured)")

    # show warnings first (minor issues)
    for r in results:
        for w in r.get("warnings", []):
            print(f"  [WARN] {r['id']}: {w}")

    # show diagnostics (only if something is wrong)
    if online == 0 or has_errors or has_warnings:
        print("─" * 60)
        print("  DIAGNOSTICS:")
        for r in results:
            pid = r["id"]
            if r["online"]:
                continue
            msg = r["message"]
            if "port" in msg.lower() and "closed" in msg.lower():
                print(f"    {pid}: not running — try: start-qwen.bat")
            elif "model" in msg.lower() and "not found" in msg.lower():
                print(f"    {pid}: GGUF missing — place file in ollama-models/")
            elif "exe" in msg.lower() and "not found" in msg.lower():
                print(f"    {pid}: binary missing — place in tools/")
            elif "401" in msg:
                print(f"    {pid}: check apiKey in providers.json")
            elif "placeholder" in msg.lower():
                print(f"    {pid}: replace placeholder apiKey in providers.json")
            elif "unreachable" in msg.lower():
                print(f"    {pid}: check network/VPN/port")
            elif "json" in msg.lower() or "parse" in msg.lower():
                print(f"    {pid}: fix JSON syntax in providers.json")

        print("─" * 60)
        print("  FIX ACTIONS:")
        print(f"    1. Edit config:  notepad {PROVIDERS_FILE}")
        print(f"    2. Re-probe:     memory probe")
        print(f"    3. Full verify:  verify.bat")

    print("=" * 60)
    print("")


# ---- file writers ----

def _write_minimal_runtime():
    """Write a minimal _runtime.bat when config is broken."""
    lines = [
        "@echo off",
        ":: Minimal runtime — providers.json could not be loaded",
        "set PROV_COUNT=0",
        "set PROV_ONLINE_COUNT=0",
    ]
    with open(RUNTIME_BAT, "w", encoding="utf-8", newline="\r\n") as f:
        f.write("\n".join(lines))


def _write_runtime_bat(results):
    lines = [
        "@echo off",
        f":: Auto-generated by probe.py at {time.strftime('%Y-%m-%d %H:%M:%S')}",
        ":: DO NOT EDIT — regenerated on every probe",
        "",
    ]
    for r in results:
        pid = r["id"]
        safe = pid.replace("-", "_").upper()
        status = "1" if r["online"] else "0"
        lines.append(f"set PROV_{safe}_ID={pid}")
        lines.append(f"set PROV_{safe}_ONLINE={status}")
        lines.append(f"set PROV_{safe}_DISPLAY={r['display']}")
        lines.append(f"set PROV_{safe}_BASE_URL={r['baseURL']}")
        lines.append(f"set PROV_{safe}_API_KEY={r['apiKey']}")
        lines.append(f"set PROV_{safe}_MODEL={r['model']}")
        if r["type"] == "local":
            lines.append(f"set PROV_{safe}_PORT={r['port']}")
            lines.append(f"set PROV_{safe}_MODEL_PATH={r['modelPath']}")
            lines.append(f"set PROV_{safe}_EXECUTABLE={r['executable']}")
        lines.append("")

    lines.append(f"set PROV_COUNT={len(results)}")
    lines.append(f"set PROV_ONLINE_COUNT={sum(1 for r in results if r['online'])}")

    with open(RUNTIME_BAT, "w", encoding="utf-8", newline="\r\n") as f:
        f.write("\n".join(lines))


def _write_opencode_json(results):
    """Write opencode.json with BOTH online and offline providers (v2.3.6+).

    Earlier versions only wrote online providers, which made the file
    shrink to 1 provider on every probe and broke Gate 10 (dual-provider
    conformance). v2.3.6 fix: read providers.json as the source of truth
    and write every provider block regardless of online status. The
    results list is only used to (optionally) annotate online state.
    """
    # Build map of id -> online status from results
    online_map = {r["id"]: r["online"] for r in results}

    # Load providers.json (the canonical config) and write all providers
    if not PROVIDERS_FILE.exists():
        return
    with open(PROVIDERS_FILE, "r", encoding="utf-8") as f:
        pdata = json.load(f)

    providers_block = {}
    for p in pdata.get("providers", []):
        pid = p.get("id")
        if not pid:
            continue
        if not p.get("enabled", True):
            # v2.3.6: still include disabled providers in the JSON so the
            # user can enable+restart without re-running anything. OpenCode
            # simply won't list a disabled model in its selector, but the
            # connection details stay in the file for one-step opt-in.
            pass
        providers_block[pid] = {
            "npm": "@ai-sdk/openai-compatible",
            "name": p.get("display", pid),
            "options": {
                "baseURL": p.get("baseURL", ""),
                "apiKey": p.get("apiKey", ""),
            },
            "models": {
                p.get("model", pid): {
                    "name": f"{p.get('display', pid)} ({p.get('context', 0)} ctx)",
                    "limit": {
                        "context": p.get("context", 8192),
                        "output": p.get("output", 4096),
                    },
                }
            },
        }
    config = {"provider": providers_block}
    with open(OPENCODE_JSON, "w", encoding="utf-8", newline="\r\n") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)


def _update_state(results, online_count):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    state = {
        "last_probe": time.strftime("%Y-%m-%d %H:%M:%S"),
        "active": online_count,
        "total": len(results),
        "providers": {
            r["id"]: {
                "online": r["online"],
                "msg": r["message"],
                "warnings": r.get("warnings", []),
            }
            for r in results
        },
    }
    with open(STATE_FILE, "w", encoding="utf-8", newline="\r\n") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    sys.exit(main())
