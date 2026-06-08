# COMAC AgentOS v2.2 — Offline Multi-Provider AI Agent

Windows x64 offline: OpenCode CLI + remote New API (GLM) + local llama.cpp (Qwen)

---

## v2.0 What's New

- **providers.json** — single config file, add a provider = add a JSON block
- **probe.py** — auto-detect all providers, auto-start local ones, generate opencode.json
- **watchdog.bat** — background health monitor, auto-restart on crash
- **agent-memory/** — persistent agent memory (identity, facts, session logs)
- **memory.bat** — CLI for managing agent memory

## Architecture

```
providers.json (single source of truth)
       |
       v
   probe.py (detect all -> generate runtime + opencode.json)
       |
       +-> _runtime.bat (env vars)
       +-> opencode.json (OpenCode config)
       +-> agent-memory/state.json
       |
       v
   run.bat (menu -> OpenCode)
       |
       +-> watchdog.bat (background health monitor)
       +-> _generate_context.py -> CONTEXT.md
```

## Quick Start

### First Deploy

1. Copy entire directory to intranet machine
2. Double-click setup.bat — extracts OpenCode, opens providers.json in Notepad
3. Edit providers.json: set New API key, model paths
4. Double-click run.bat

### Daily Use

Double-click run.bat — auto-detects all providers, shows menu:

```
COMAC AgentOS v2.0
============================================================
Detecting providers...
  [ON]  New API (GLM-5.1-AWQ-4bit)
  [ON]  Qwen3-4B (llama.cpp)
============================================================

Select a provider:
  [1] GLM — New API (GLM-5.1-AWQ-4bit)
  [2] Qwen — Qwen3-4B (llama.cpp)
  [V] Verify  (full diagnostic)
  [Q] Quit
```

### Memory CLI

```
memory add  "project" "APU thermal simulation"    — store a fact
memory recall "project"                            — retrieve it
memory list                                        — list all facts
memory context                                     — show agent context
memory log  "completed mesh generation"             — log to session
memory probe                                       — re-run provider check
```

## Directory Structure

```
COMAC-OpenCode-Unified/
  providers.json          <- ALL config here (edit this)
  probe.py                <- Detection engine (Python 3.11.8)
  _generate_context.py    <- Context generator
  run.bat                 <- Smart launcher
  setup.bat               <- First-time setup
  verify.bat              <- Full diagnostic
  watchdog.bat            <- Health monitor (background)
  memory.bat              <- Memory management CLI
  start-qwen.bat          <- Start local Qwen
  stop-qwen.bat           <- Stop local Qwen
  messages/zh.txt         <- Chinese messages
  -- v2.2 optional add-ons (zero impact on deployment) --
  doctor.bat / doctor.py       <- Health check
  webui.bat  / webui.py        <- Browser dashboard
  switch.bat  / switch.py      <- Switch active provider
  benchmark.bat / benchmark.py <- Performance benchmark
  archive.bat / archive.py     <- Archive project to Desktop
  aliases.bat                  <- Install cmd aliases
  skills/                      <- OpenCode skills (switch-provider / diagnose / recall-memory)
  agent-memory/           <- Persistent memory
    identity.md           <- Agent identity
    FACTS.json            <- Key-value store
    state.json            <- Provider status (auto)
    CONTEXT.md            <- Session context (auto)
    sessions/             <- Session logs
  bin/                    <- OpenCode extracted
  tools/                  <- llama-server.exe
  ollama-models/          <- GGUF models
  downloads/              <- OpenCode offline zip
```

## Adding a New Provider

Add a JSON block to providers.json:

```json
{
  "id": "my-new-model",
  "display": "My New Model",
  "type": "remote",
  "baseURL": "http://x.x.x.x:port/v1",
  "apiKey": "sk-xxx",
  "model": "model-name",
  "context": 32768,
  "output": 4096,
  "timeout": 5,
  "enabled": true
}
```

For local providers (lifecycle-managed), add `"type": "local"` with `executable`, `modelPath`, `port`, and `healthCheck`.

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| No providers online | Run memory probe to re-detect |
| New API 401 | Update apiKey in providers.json |
| Qwen won't start | Check tools/llama-server.exe exists |
| Port conflict | Edit port in providers.json -> llamacpp |
| Memory commands fail | Check Python 3.11.8 is in PATH |

---

## Optional Add-ons (v2.2)

All 9 of these are **strictly optional**. They do not affect `run.bat`, `setup.bat`,
`verify.bat`, or `watchdog.bat`. None of them auto-register. None of them modify
`providers.json` (except `switch.bat` which the user invokes explicitly).
Python stdlib only — no extra pip packages.

### Tools (4 — root-level .bat + .py)

| Tool | Purpose |
|------|---------|
| `doctor.bat`   | One-click health check (Python, paths, ports, disk, watchdog, memory state). ANSI color report, exit 0/1/2. |
| `webui.bat`    | Browser dashboard on `http://127.0.0.1:8080` (set `WEBUI_PORT=8090` to override). 5s auto-refresh, no JS framework. |
| `switch.bat`   | Interactive menu to swap the active provider. Atomic write; only the `enabled` field is touched. |
| `benchmark.bat`| 5-round streaming benchmark per enabled provider. Reports first-token latency (ms) and tokens/s. |

### OpenCode Skills (3 — under `skills/`)

Copy the `skills/<name>/` folder into `~/.opencode/skills/` (or your project's
`.opencode/skills/`) and OpenCode will pick them up automatically.

| Skill | Purpose |
|-------|---------|
| `skills/switch-provider/` | Thin wrapper around root `switch.py`; agent can flip providers mid-conversation. |
| `skills/diagnose/`       | Focused 6-check diagnose with `--json` output. Read-only. |
| `skills/recall-memory/`  | Substring search across `agent-memory/FACTS.json` and `sessions/*.md`. |

### Plugins (2 — root-level)

| Plugin | Purpose |
|--------|---------|
| `aliases.bat`  | Installs 6 cmd aliases (`comac`, `comac-doctor`, `comac-webui`, `comac-switch`, `comac-bench`, `comac-archive`) into `%USERPROFILE%\bin`. Also installs `comac-uninstall`. |
| `archive.bat`  | One-click zips the project (excluding `bin/`, `tools/`, `ollama-models/`, `downloads/`) to Desktop as `COMAC-AgentOS-YYYYMMDD-HHMM.zip`. |

### Quick Start (Add-ons)

```cmd
:: Health check
doctor

:: Browser dashboard (then open http://127.0.0.1:8080)
webui

:: Switch active provider
switch

:: Performance benchmark
benchmark

:: Install cmd aliases (one-time)
aliases
:: ... then in a NEW cmd window:
comac-doctor
comac-webui

:: Archive project to Desktop
archive

:: OpenCode skills - copy entire skills/ folder to:
::   %USERPROFILE%\.opencode\skills\
```

### Removing the Add-ons

```cmd
:: If you installed aliases:
comac-uninstall

:: Otherwise, just delete the 9 new files. They share no state with
;; the core deployment:
del doctor.bat doctor.py webui.bat webui.py switch.bat switch.py
del benchmark.bat benchmark.py archive.bat archive.py aliases.bat
rmdir /S /Q skills
```

The core v2.1 deployment (`run.bat`, `setup.bat`, `verify.bat`, `watchdog.bat`,
`memory.bat`, `start-qwen.bat`, `stop-qwen.bat`, `probe.py`, `providers.json`,
`messages/zh.txt`, `agent-memory/`) is **completely untouched** by all 9 add-ons.
