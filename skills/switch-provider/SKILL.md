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
