---
name: comac-switch-provider
description: Switch the active LLM provider (GLM <-> local Qwen) for COMAC AgentOS
---

# COMAC Provider Switcher

Use this skill when the user wants to:

- Switch the active LLM provider mid-session
- Use local Qwen instead of remote GLM (or vice versa)
- Change which model powers the next `run.bat` invocation

## How it works

- Reads `providers.json` in the project root
- Toggles the `enabled` field for each provider (only the chosen one becomes `true`)
- Preserves all other fields (apiKey, baseURL, modelPath, executable, port, etc.)
- Atomic write via `.tmp` + `Path.replace()` (no partial writes on crash)

## How to invoke

```
python skills/switch-provider/switch_provider.py
```

The wrapper invokes the root-level `switch.py` interactive menu. There is
no `--id` flag on the skill itself; the root `switch.py` only supports the
menu. (Future: programmatic `--id` would be a thin refactor of `switch.py`.)

## Exit codes

- `0` = switched (or cancelled)
- `1` = invalid input
- `2` = providers.json parse/write error
- `3` = providers.json missing

## Important

- This skill **does not** restart the watchdog or kill running llama-server.
- After switching, **recommend the user re-run `run.bat`** to apply the change.
- **Never** auto-switch without explicit user consent.

## v2.3.5 — Default provider count (locked to 2)

Out of the box, `providers.json` ships with **exactly 2 providers**:
1 enabled by default (`llamacpp` = Qwen2.5-Coder-3B local) and 1 opt-in
(`newapi` = GLM-5.1-AWQ-4bit remote, `enabled=false` by default).

The previous `qwen-fast` 1.5B fallback has been **removed** in v2.3.5.
This is intentional — the 1.5B model was an experimental vGPU escape
hatch that ended up slower than the 3B on the actual deploy target
(8-10 tok/s vs 12-18 tok/s headline numbers from 2024 didn't pan out
on the 2018-era CPU). Two real providers beats three theoretical ones.

- `newapi` requires a reachable intranet endpoint + valid API key; on
  airgapped deploy targets it will always probe offline. Disabling it
  avoids REPAIR_MODE loops.
- `llamacpp` requires `ollama-models\qwen2.5-coder-3b-instruct-q4_k_m.gguf`
  (~1.9 GB, user must place manually — see `ollama-models/README.md`).

To enable GLM-5.1: edit `providers.json`, set `newapi.enabled=true`,
replace `YOUR_NEWAPI_KEY_HERE` with a real key, confirm `baseURL` is
reachable, then run `memory probe` (or `python probe.py`) to refresh
`_runtime.bat`.
