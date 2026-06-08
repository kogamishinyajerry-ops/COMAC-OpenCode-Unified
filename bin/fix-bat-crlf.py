#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fix-bat-crlf.py — COMAC AgentOS CRLF repair tool (v1.0, 2026-06-08)
Stdlib only. Scans root *.bat (and optionally .txt/.cmd) and converts
LF-only line endings to CRLF so Windows CMD can parse them.

Why this exists:
- Git on Windows with core.autocrlf=false or on macOS/Linux checkouts
  rewrites .bat files from CRLF to LF during clone/pull.
- CMD.exe and `call` are sensitive to line endings: LF-only files
  either silently do nothing or report "系统找不到指定的命令".
- This script is idempotent: running it twice is a no-op.

Usage:
  python bin/fix-bat-crlf.py            # auto-detect root from script path
  python bin/fix-bat-crlf.py --root X   # explicit root
  python bin/fix-bat-crlf.py --dry-run  # show what would change, don't write

Exit codes:
  0 = all CRLF (or all successfully converted)
  1 = some files failed
  2 = no .bat files found
"""
import os
import sys
import argparse
from pathlib import Path

# Extensions that MUST be CRLF on Windows for cmd.exe to parse
TARGET_EXTS = {".bat", ".cmd"}

# .txt files called as scripts (e.g. messages/zh.txt via `call`) also need CRLF
TARGET_TXT = True


def has_cr(data: bytes) -> bool:
    return b"\r" in data


def to_crlf(data: bytes) -> bytes:
    """Convert LF-only to CRLF. Idempotent: if already CRLF, returns unchanged."""
    if has_cr(data):
        return data
    # Normalize line endings: replace lone \n with \r\n, leave \r\n alone
    return data.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")


def should_process(path: Path) -> bool:
    ext = path.suffix.lower()
    if ext in TARGET_EXTS:
        return True
    if TARGET_TXT and ext == ".txt":
        return True
    return False


def main() -> int:
    parser = argparse.ArgumentParser(description="Fix CRLF line endings on .bat/.cmd/.txt")
    parser.add_argument("--root", type=Path, default=None,
                        help="Project root (default: parent of bin/)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would change without writing")
    parser.add_argument("--quiet", action="store_true",
                        help="Only print files that changed")
    args = parser.parse_args()

    if args.root is None:
        # bin/fix-bat-crlf.py -> root is parent of bin/
        args.root = Path(__file__).resolve().parent.parent

    root = args.root.resolve()
    if not root.is_dir():
        print(f"[FATAL] root not a directory: {root}", file=sys.stderr)
        return 1

    targets = []
    for p in sorted(root.iterdir()):
        if p.is_file() and should_process(p):
            targets.append(p)

    if not targets:
        print(f"[WARN] no .bat/.cmd/.txt found in {root}")
        return 2

    changed = []
    already_ok = []
    failed = []

    for p in targets:
        try:
            raw = p.read_bytes()
        except OSError as e:
            failed.append((p, str(e)))
            continue

        new = to_crlf(raw)
        if new == raw:
            already_ok.append(p)
            continue

        if not args.dry_run:
            try:
                p.write_bytes(new)
            except OSError as e:
                failed.append((p, str(e)))
                continue
        changed.append(p)

    # Report
    if not args.quiet or args.dry_run:
        print(f"Root: {root}")
        print(f"Scanned: {len(targets)} files")
        print(f"Already CRLF: {len(already_ok)}")
        print(f"Changed: {len(changed)}")
        if args.dry_run:
            print("(dry-run — no files written)")
        for p in changed:
            print(f"  [FIXED] {p.relative_to(root)}")
        for p, err in failed:
            print(f"  [FAIL ] {p.relative_to(root)}: {err}", file=sys.stderr)

    if failed:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
