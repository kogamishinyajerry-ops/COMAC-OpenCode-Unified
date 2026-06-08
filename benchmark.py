#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
benchmark.py - Performance benchmark for COMAC AgentOS
Stdlib only. Sends 5 short prompts to each enabled provider, measures:
  - First-token latency (ms, streaming-aware)
  - Average tokens/s (approximate, ~4 chars/token heuristic)

If a provider fails, it's reported in the table but the script continues.
"""
import json
import socket
import sys
import time
import urllib.request
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROV_FILE = SCRIPT_DIR / "providers.json"

ROUNDS = 5
PROMPT = "Reply with one short sentence: 'Hello from COMAC benchmark.'"
MAX_TOKENS = 30
TIMEOUT = 30


def approx_tokens(text):
    """Rough token estimate: ~4 chars per token (English)."""
    return max(1, len(text) // 4)


def stream_request(base_url, api_key, model, timeout):
    """Stream chat completion, return (first_token_seconds, total_seconds, chars, error)."""
    url = base_url.rstrip("/") + "/chat/completions"
    body = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": PROMPT}],
        "max_tokens": MAX_TOKENS,
        "stream": True,
        "temperature": 0.0,
    }).encode("utf-8")

    req = urllib.request.Request(
        url, data=body, method="POST",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
    )

    first_token_t = None
    start = time.time()
    chars = 0
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            for line in resp:
                if not line:
                    continue
                ls = line.decode("utf-8", errors="ignore").strip()
                if not ls.startswith("data:"):
                    continue
                payload = ls[5:].strip()
                if payload == "[DONE]":
                    break
                try:
                    obj = json.loads(payload)
                except json.JSONDecodeError:
                    continue
                choices = obj.get("choices", [])
                if not choices:
                    continue
                delta = choices[0].get("delta", {})
                content = delta.get("content", "")
                if content:
                    if first_token_t is None:
                        first_token_t = time.time() - start
                    chars += len(content)
    except Exception as e:
        return None, None, 0, str(e)

    total_t = time.time() - start
    return first_token_t, total_t, chars, None


def benchmark_provider(p):
    pid = p.get("id", "?")
    base = p.get("baseURL", "")
    api_key = p.get("apiKey", "")
    model = p.get("model", "")
    enabled = p.get("enabled", True)
    ptype = p.get("type", "?")

    if not enabled:
        return {"id": pid, "skipped": True, "reason": "disabled"}
    if not base or not model:
        return {"id": pid, "skipped": True, "reason": "missing baseURL/model"}

    # Port precheck (local providers)
    host = p.get("host")
    port = p.get("port")
    if host and port:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(2)
            try:
                s.connect((host, int(port)))
            except Exception as e:
                return {"id": pid, "skipped": True, "reason": f"port {port} not open: {e}"}

    first_tokens = []
    tps_list = []
    errors = []

    for r in range(ROUNDS):
        ft, tt, chars, err = stream_request(base, api_key, model, TIMEOUT)
        if err:
            errors.append(f"r{r+1}:{err}")
            continue
        if ft is None or tt is None or chars == 0:
            errors.append(f"r{r+1}:empty")
            continue
        first_tokens.append(ft * 1000)
        tps = approx_tokens(str(chars)) / tt if tt > 0 else 0
        tps_list.append(tps)

    if not first_tokens:
        return {"id": pid, "skipped": True, "reason": f"all failed ({'; '.join(errors[:2])})"}

    return {
        "id": pid,
        "display": p.get("display", pid),
        "type": ptype,
        "first_token_ms": sum(first_tokens) / len(first_tokens),
        "tokens_per_sec": sum(tps_list) / len(tps_list),
        "rounds_ok": len(first_tokens),
        "rounds_total": ROUNDS,
    }


def main():
    if not PROV_FILE.exists():
        print(f"[FATAL] {PROV_FILE} not found")
        return 3
    try:
        cfg = json.loads(PROV_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(f"[FATAL] providers.json parse error: {e}")
        return 2

    providers = cfg.get("providers", [])
    if not providers:
        print("[FATAL] No providers configured")
        return 2

    print()
    print("=" * 70)
    print(f"  COMAC AgentOS - Benchmark ({ROUNDS} rounds per provider)")
    print("=" * 70)
    print(f"  Prompt: {PROMPT[:60]}...")
    print()

    results = []
    for p in providers:
        pid = p.get("id", "?")
        print(f"  Testing {p.get('display', pid)}...", end="", flush=True)
        r = benchmark_provider(p)
        if r.get("skipped"):
            print(f" SKIPPED ({r.get('reason')})")
        else:
            print(f" done")
        results.append(r)

    print()
    print("=" * 70)
    print("  Results")
    print("=" * 70)
    print(f"  {'Provider':<34} {'First-tok':<13} {'Tok/s':<9} {'Rounds':<8}")
    print(f"  {'-'*34} {'-'*13} {'-'*9} {'-'*8}")
    for r in results:
        if r.get("skipped"):
            print(f"  {r['id'][:34]:<34} {'SKIPPED':<13} {'-':<9} {'-':<8}")
        else:
            print(
                f"  {r['display'][:34]:<34} "
                f"{r['first_token_ms']:>8.0f} ms  "
                f"{r['tokens_per_sec']:>6.2f}    "
                f"{r['rounds_ok']}/{r['rounds_total']}"
            )
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
