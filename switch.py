#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
switch.py - One-click switch active provider
Reads providers.json, shows menu, swaps the `enabled` flags so user choice
becomes the sole active provider. Only the `enabled` field is touched -
all other fields (apiKey, baseURL, modelPath, executable) are preserved.
Atomic write via .tmp + replace.
"""
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROV_FILE = SCRIPT_DIR / "providers.json"


def load_cfg():
    if not PROV_FILE.exists():
        print(f"[FATAL] {PROV_FILE} not found")
        return None
    try:
        return json.loads(PROV_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(f"[FATAL] providers.json parse error: {e}")
        return None


def main():
    cfg = load_cfg()
    if cfg is None:
        return 3

    providers = cfg.get("providers", [])
    if not providers:
        print("[FATAL] No providers in providers.json")
        return 2

    print()
    print("=" * 60)
    print("  COMAC AgentOS - Provider Switcher")
    print("=" * 60)
    print()
    print("  Current provider status:")
    print()
    for i, p in enumerate(providers, 1):
        pid = p.get("id", "?")
        display = p.get("display", pid)
        enabled = p.get("enabled", True)
        ptype = p.get("type", "?")
        tag = "[ON] " if enabled else "[OFF]"
        print(f"    [{i}] {tag}{display} ({ptype}, id={pid})")
    print()
    print("    [0] Cancel")
    print()

    try:
        choice = input("  Switch to (1-N, 0=cancel): ").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        return 1

    if not choice or choice == "0":
        print("[INFO] Cancelled")
        return 0

    try:
        idx = int(choice) - 1
    except ValueError:
        print(f"[FATAL] Invalid choice: {choice}")
        return 1

    if idx < 0 or idx >= len(providers):
        print(f"[FATAL] Choice out of range: {idx + 1}")
        return 1

    # Apply: enable chosen, disable others
    for i, p in enumerate(providers):
        p["enabled"] = (i == idx)

    # Atomic write
    tmp = PROV_FILE.with_suffix(".json.tmp")
    try:
        tmp.write_text(
            json.dumps(cfg, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        tmp.replace(PROV_FILE)
    except OSError as e:
        print(f"[FATAL] Write failed: {e}")
        return 2

    target = providers[idx]
    print()
    print(f"[OK] Switched to: {target.get('display', target.get('id'))} (id={target.get('id')})")
    print()
    print("  Other providers are now disabled. To re-enable, edit")
    print("  providers.json directly, or run this script again.")
    print()
    print("  Tip: Re-run run.bat to pick up the new config.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
