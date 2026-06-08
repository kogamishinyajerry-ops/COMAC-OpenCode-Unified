#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
archive.py - One-click archive the COMAC AgentOS directory
Stdlib only. Uses zipfile to create a portable .zip on the user's Desktop.

Excluded by default (large/redistributed separately):
  - bin/         (OpenCode is redistributed via setup.bat)
  - tools/       (llama-server is huge, restored separately)
  - ollama-models/  (GGUF models can be 4+ GB)
  - downloads/   (original OpenCode zip)
  - __pycache__/
  - *.tmp

Included:
  - all .bat, .py, .json, .md, .txt
  - agent-memory/ (full, including sessions)
  - watchdog / runtime state
"""
import os
import sys
import zipfile
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
EXCLUDE_DIRS = {"bin", "tools", "ollama-models", "downloads", "__pycache__", ".git"}
EXCLUDE_FILES = {".DS_Store", "Thumbs.db"}
EXCLUDE_SUFFIX = {".tmp", ".pyc", ".pyo"}


def _desktop():
    """Best-effort Desktop path. Falls back to home dir."""
    userprofile = os.environ.get("USERPROFILE") or str(Path.home())
    # Try Windows known folders via registry first; fall back to ~/Desktop
    if sys.platform == "win32":
        try:
            import ctypes
            from ctypes import wintypes
            buf = ctypes.create_unicode_buffer(260)
            # CSIDL_DESKTOP = 0, but SHGetFolderPath is deprecated.
            # Try SHGetKnownFolderPath via ole32.
            class GUID(ctypes.Structure):
                _fields_ = [("Data1", ctypes.c_ulong),
                            ("Data2", ctypes.c_ushort),
                            ("Data3", ctypes.c_ushort),
                            ("Data4", ctypes.c_ubyte * 8)]
            FOLDERID_Desktop = GUID(
                0xB4BFCC3A, 0xDB2C, 0x424C, (ctypes.c_ubyte * 8)(0xB0, 0x29, 0xD7, 0x19, 0x7D, 0x36, 0xE0, 0xC3)
            )
            ole32 = ctypes.windll.ole32
            ole32.CoTaskMemFree.restype = None
            ptr = ctypes.c_wchar_p()
            if ole32.SHGetKnownFolderPath(ctypes.byref(FOLDERID_Desktop), 0, None, ctypes.byref(ptr)) == 0:
                desktop = ptr.value
                ole32.CoTaskMemFree(ptr)
                if desktop and Path(desktop).exists():
                    return Path(desktop)
        except Exception:
            pass
    desktop = Path(userprofile) / "Desktop"
    return desktop if desktop.exists() else Path(userprofile)


def main():
    desktop = _desktop()
    date_str = datetime.now().strftime("%Y%m%d-%H%M")
    out_name = f"COMAC-AgentOS-{date_str}.zip"
    out_path = desktop / out_name

    print()
    print("=" * 70)
    print("  COMAC AgentOS - Archive Builder")
    print("=" * 70)
    print(f"  Source: {SCRIPT_DIR}")
    print(f"  Output: {out_path}")
    print()
    print("  Excluding: " + ", ".join(sorted(EXCLUDE_DIRS)))
    print()

    files_added = 0
    bytes_added = 0

    try:
        with zipfile.ZipFile(out_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
            for path in sorted(SCRIPT_DIR.rglob("*")):
                if not path.is_file():
                    continue
                rel = path.relative_to(SCRIPT_DIR)
                parts = rel.parts
                if any(p in EXCLUDE_DIRS for p in parts):
                    continue
                if path.name in EXCLUDE_FILES:
                    continue
                if path.suffix in EXCLUDE_SUFFIX:
                    continue
                # arcname preserves relative path
                zf.write(path, arcname=str(Path("COMAC-OpenCode-Unified") / rel))
                files_added += 1
                bytes_added += path.stat().st_size
                if files_added % 25 == 0:
                    print(f"  ... {files_added} files, {bytes_added / 1024:.0f} KB")
    except OSError as e:
        print(f"[FATAL] zip write failed: {e}")
        return 2

    size_mb = out_path.stat().st_size / (1024 * 1024)
    print()
    print("=" * 70)
    print(f"  [OK] Archive created: {out_path}")
    print(f"  Files: {files_added}  |  Raw: {bytes_added / 1024:.0f} KB  |  Zip: {size_mb:.2f} MB")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    sys.exit(main())
