---
name: comac-diagnose
description: Run a quick health check on the COMAC AgentOS environment and report findings
---

# COMAC Diagnose

Use this skill when:

- The user reports the system is slow, broken, or behaving strangely
- Before/after a configuration change in `providers.json`
- During a `run.bat` REPAIR MODE flow
- The user asks "is everything OK?"

## What it checks

- Python version (must be >= 3.11)
- `providers.json` readability and JSON validity
- Provider port reachability (one socket connect per enabled provider)
- Disk free space (warns below 5 GB, errors below 1 GB)
- COMAC-Watchdog process (via `tasklist /fi "WINDOWTITLE eq COMAC-Watchdog"`)
- `agent-memory/state.json` last probe timestamp

## How to invoke

```
python skills/diagnose/diagnose.py [--json]
```

`--json` produces machine-readable JSON (one line per check, status field).
Without `--json`, human-readable output is printed.

## Exit codes

- `0` = all green
- `1` = warnings present (still operational)
- `2` = errors present (deployment affected)
- `3` = critical files missing

## Important

- **Do not** auto-fix based on findings. Report to the user first.
- If `providers.json` is malformed, **do not** rewrite it - just report the error.
- This skill is **read-only** with respect to configuration.
