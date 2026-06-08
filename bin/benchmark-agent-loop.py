#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
benchmark-agent-loop.py - COMAC AgentOS v2.3
5-step OpenCode agent loop benchmark. Stdlib only. 3.11.8 deploy-machine compatible.

Mimics the real OpenCode agent pattern:
  1. plan         - "describe your plan in 1-2 sentences"
  2. tool_call    - "read the file" (forces tool_choice=auto, validates tool calling)
  3. tool_result  - "given this tool result, decide next step"
  4. code_fix     - "write the minimal fix"
  5. final        - "confirm completion"

Each step is a separate /v1/chat/completions call (no streaming) so cold-start
amortization and end-to-end latency match real OpenCode usage.

Exit codes:
  0 = pass  (< 180s wall clock -> fluid for OpenCode)
  1 = warn  (180-300s -> marginal, agent loops will feel slow)
  2 = fail  (> 300s OR any step errored -> do not ship this model)
  3 = providers.json missing / no enabled local provider / port unreachable
"""
import json
import socket
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROV_FILE = SCRIPT_DIR.parent / "providers.json"

WARMUP_PROMPT = "Reply with exactly: OK"
TOOL_DEF = {
    "type": "function",
    "function": {
        "name": "read_file",
        "description": "Read a file from disk and return its contents",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Absolute file path"}
            },
            "required": ["path"]
        }
    }
}

# 5-step OpenCode agent loop
STEPS = [
    {
        "name": "step1_plan",
        "max_tokens": 120,
        "system": "You are an OpenCode-style coding agent. Be terse, no preamble.",
        "user": "User asks: 'Fix the bug in compute_sum.py where it returns 0 for empty lists.' Describe your plan in 1-2 sentences.",
    },
    {
        "name": "step2_tool_call",
        "max_tokens": 80,
        "system": "You are an OpenCode-style coding agent. Use the read_file tool when you need source code.",
        "user": "Read the file C:/work/compute_sum.py to see the current code.",
        "tools": [TOOL_DEF],
    },
    {
        "name": "step3_tool_result",
        "max_tokens": 200,
        "system": "You are an OpenCode-style coding agent. The user gave you a tool result. Continue the task.",
        "user": "Tool result from read_file returned:\n\ndef compute_sum(nums):\n    total = 0\n    for n in nums:\n        total = total + n\n    return total\n\nDecide what to do next in 1-2 sentences.",
    },
    {
        "name": "step4_code_fix",
        "max_tokens": 250,
        "system": "You are an OpenCode-style coding agent. Write the minimal fix. Output code only.",
        "user": "Write the fixed compute_sum function. Output only the function definition.",
    },
    {
        "name": "step5_final",
        "max_tokens": 80,
        "system": "You are an OpenCode-style coding agent. Be terse, no preamble.",
        "user": "Confirm completion in one short sentence.",
    },
]

PASS_THRESHOLD = 180.0
WARN_THRESHOLD = 300.0
REQUEST_TIMEOUT = 60


def approx_tokens(n_chars):
    """Rough token estimate: ~4 chars per token (English / code). 0 -> 0."""
    if n_chars <= 0:
        return 0
    return n_chars // 4


def find_local_provider(cfg):
    """First enabled local provider (CPU-tuned 3B expected on v2.3)."""
    for prov in cfg.get("providers", []):
        if not prov.get("enabled", True):
            continue
        if prov.get("type") != "local":
            continue
        if prov.get("host") and prov.get("port"):
            return prov
    return None


def port_open(host, port, timeout=2):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(timeout)
            s.connect((host, int(port)))
        return True
    except Exception:
        return False


def chat_request(p, prompt_pack):
    """One non-streaming /v1/chat/completions call. Returns (elapsed_s, out_chars, err)."""
    url = p["baseURL"].rstrip("/") + "/chat/completions"
    body = {
        "model": p["model"],
        "messages": [
            {"role": "system", "content": prompt_pack["system"]},
            {"role": "user", "content": prompt_pack["user"]},
        ],
        "max_tokens": prompt_pack["max_tokens"],
        "temperature": 0.0,
    }
    if prompt_pack.get("tools"):
        body["tools"] = prompt_pack["tools"]
        body["tool_choice"] = "auto"

    raw = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        url, data=raw, method="POST",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {p['apiKey']}",
        },
    )
    start = time.time()
    try:
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
            data = resp.read()
        elapsed = time.time() - start
    except (urllib.error.URLError, urllib.error.HTTPError, socket.timeout, OSError) as e:
        return 0.0, 0, str(e)

    try:
        obj = json.loads(data)
    except json.JSONDecodeError as e:
        return elapsed, 0, f"json parse: {e}"

    try:
        msg = obj["choices"][0]["message"]
        content = msg.get("content", "") or ""
    except (KeyError, IndexError, TypeError) as e:
        return elapsed, 0, f"choices missing: {e}"

    return elapsed, len(content), None


def main():
    if not PROV_FILE.exists():
        print(f"[FATAL] {PROV_FILE} not found")
        return 3
    try:
        cfg = json.loads(PROV_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(f"[FATAL] providers.json parse error: {e}")
        return 2

    p = find_local_provider(cfg)
    if not p:
        print("[FATAL] no enabled local provider found in providers.json")
        return 3

    if not port_open(p["host"], p["port"]):
        print(f"[FATAL] {p['host']}:{p['port']} not reachable.")
        print(f"        Start llama-server first: start-qwen.bat")
        return 3

    print()
    print("=" * 70)
    print(f"  COMAC AgentOS v2.3 - 5-Step Agent Loop Benchmark")
    print("=" * 70)
    print(f"  Provider: {p.get('display', p.get('id'))}")
    print(f"  Model:    {p.get('model')}")
    print(f"  Endpoint: {p.get('baseURL')}")
    print(f"  Steps:    1 warmup + {len(STEPS)} agent-loop")
    print()

    # Warmup (cold start amortization; first 3B call is always slow on CPU)
    print(f"  [{'warmup':<14}] sending... ", end="", flush=True)
    w_t, w_chars, w_err = chat_request(p, {
        "system": "You are a coding agent.",
        "user": WARMUP_PROMPT,
        "max_tokens": 8,
    })
    if w_err:
        print(f"FAIL: {w_err}")
        return 2
    w_tps = approx_tokens(w_chars) / w_t if w_t > 0 else 0
    print(f"done   {w_t:>5.2f}s  ~{w_tps:>5.2f} tok/s  (warm)")

    # 5-step agent loop
    step_results = []
    step_start = time.time()
    for s in STEPS:
        t, chars, err = chat_request(p, s)
        if err:
            print(f"  [{s['name']:<18}] FAIL: {err}")
            return 2
        tps = approx_tokens(chars) / t if t > 0 else 0
        step_results.append((s["name"], t, chars, tps))
        print(f"  [{s['name']:<18}] {t:>6.2f}s  ~{tps:>5.2f} tok/s  ({chars} chars)")

    wall = time.time() - step_start
    total_chars = sum(r[2] for r in step_results)
    avg_tps = sum(r[3] for r in step_results) / len(step_results) if step_results else 0.0

    print()
    print("=" * 70)
    print(f"  RESULT")
    print("=" * 70)
    print(f"  Steps completed:    {len(STEPS)}/{len(STEPS)}")
    print(f"  Wall clock:         {wall:>6.2f}s  (urllib overhead included)")
    print(f"  Total output:       {total_chars} chars  (~{approx_tokens(total_chars)} tokens)")
    print(f"  Avg tok/s (output): {avg_tps:>6.2f}")
    print()
    if wall < PASS_THRESHOLD:
        print(f"  [PASS]  wall {wall:.0f}s < {PASS_THRESHOLD:.0f}s  ->  FLUID for OpenCode agent loops")
        return 0
    elif wall < WARN_THRESHOLD:
        print(f"  [WARN]  wall {wall:.0f}s in [{PASS_THRESHOLD:.0f}, {WARN_THRESHOLD:.0f})  ->  MARGINAL, agent loops will feel slow")
        return 1
    else:
        print(f"  [FAIL]  wall {wall:.0f}s >= {WARN_THRESHOLD:.0f}s  ->  TOO SLOW, switch to 1.5B or accept GPU offload")
        return 2


if __name__ == "__main__":
    sys.exit(main())
