#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
recall.py - OpenCode skill: search persistent agent memory

Reads:
  - agent-memory/identity.md
  - agent-memory/FACTS.json
  - agent-memory/sessions/*.md

Stdlib only. Read-only.
"""
import argparse
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = SCRIPT_DIR.parent.parent
MEM_DIR = ROOT / "agent-memory"
IDENTITY = MEM_DIR / "identity.md"
FACTS = MEM_DIR / "FACTS.json"
SESSIONS = MEM_DIR / "sessions"


def _read_identity():
    if not IDENTITY.exists():
        return None
    try:
        text = IDENTITY.read_text(encoding="utf-8").strip()
        # Truncate to first 8 non-empty lines
        lines = [ln for ln in text.splitlines() if ln.strip()][:8]
        return "\n".join(lines)
    except Exception:
        return None


def _read_facts():
    if not FACTS.exists():
        return []
    try:
        data = json.loads(FACTS.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    # Unwrap the {"created": ..., "facts": {...}} envelope used by memory.bat
    # so callers only see the actual key/value records.
    if isinstance(data, dict) and isinstance(data.get("facts"), dict):
        data = data["facts"]
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        out = []
        for k, v in data.items():
            if isinstance(v, dict):
                out.append({
                    "key": k,
                    "value": v.get("value", ""),
                    "category": v.get("category", "general"),
                    "updatedAt": v.get("updatedAt", ""),
                })
            else:
                out.append({"key": k, "value": str(v), "category": "general", "updatedAt": ""})
        return out
    return []


def _list_sessions(limit=20):
    if not SESSIONS.exists():
        return []
    files = sorted(SESSIONS.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True)
    return files[:limit]


def _search_facts(facts, query):
    if not query:
        return facts
    q = query.lower()
    out = []
    for f in facts:
        blob = " ".join(str(f.get(k, "")) for k in ("key", "value", "category")).lower()
        if q in blob:
            out.append(f)
    return out


def _search_sessions(files, query, snippet_chars=200):
    out = []
    for f in files:
        try:
            text = f.read_text(encoding="utf-8")
        except Exception:
            continue
        if query and query.lower() not in text.lower():
            continue
        # Extract first non-empty line as title, plus snippet
        lines = [ln for ln in text.splitlines() if ln.strip()]
        title = lines[0][:80] if lines else f.name
        snippet_idx = text.lower().find(query.lower()) if query else 0
        if snippet_idx < 0:
            snippet_idx = 0
        start = max(0, snippet_idx - 60)
        snippet = text[start:start + snippet_chars].replace("\n", " ")
        out.append({
            "file": f.name,
            "title": title,
            "snippet": snippet.strip(),
        })
    return out


def main():
    ap = argparse.ArgumentParser(description="Recall COMAC agent memory")
    ap.add_argument("--query", "-q", default="", help="substring search")
    ap.add_argument("--limit", "-n", type=int, default=20, help="max sessions to scan")
    ap.add_argument("--json", action="store_true", help="JSON output")
    args = ap.parse_args()

    if not MEM_DIR.exists():
        print(f"[FATAL] {MEM_DIR} missing", file=sys.stderr)
        return 2

    identity = _read_identity()
    facts_all = _read_facts()
    if facts_all is None:
        print(f"[FATAL] {FACTS} parse error", file=sys.stderr)
        return 3
    facts_matched = _search_facts(facts_all, args.query)
    session_files = _list_sessions(args.limit)
    sessions_matched = _search_sessions(session_files, args.query)

    if args.json:
        print(json.dumps({
            "identity": identity,
            "facts": facts_matched,
            "sessions": sessions_matched,
            "counts": {
                "facts_total": len(facts_all),
                "facts_matched": len(facts_matched),
                "sessions_scanned": len(session_files),
                "sessions_matched": len(sessions_matched),
            },
        }, ensure_ascii=False, indent=2))
    else:
        print("=" * 60)
        print("  COMAC AgentOS - Memory Recall")
        print("=" * 60)
        if identity:
            print()
            print("Identity:")
            for ln in identity.splitlines():
                print(f"  {ln}")
        print()
        print(f"Facts ({len(facts_matched)} of {len(facts_all)}):")
        if not facts_matched:
            print("  (none)")
        for f in facts_matched:
            print(f"  - [{f.get('category','?')}] {f.get('key','?')}: {f.get('value','')}")
        print()
        print(f"Sessions ({len(sessions_matched)} of {len(session_files)} scanned):")
        if not sessions_matched:
            print("  (none)")
        for s in sessions_matched:
            print(f"  - {s['file']}: {s['title']}")
        print()

    if args.query and not facts_matched and not sessions_matched:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
