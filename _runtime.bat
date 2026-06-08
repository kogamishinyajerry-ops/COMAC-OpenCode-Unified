@echo off
:: COMAC AgentOS _runtime.bat — SEED template (v2.3.4)
:: =====================================================
:: This file is TRACKED in git so that a fresh clone of COMAC-OpenCode-Unified
:: can run.bat / verify.bat / switch.bat / doctor.bat / benchmark.bat
:: immediately, without first having to run probe.py to generate it.
::
:: probe.py will OVERWRITE this file on every successful probe, replacing
:: the timestamp and *_ONLINE flags. The seed below matches the defaults in
:: providers.json (one enabled provider: llamacpp 3B; one opt-in: newapi
:: which is intentionally enabled=false in providers.json).
::
:: Layout convention: blocks of `set PROV_<UPPER_ID>_*` lines, one per
:: provider. After all blocks: `set PROV_COUNT=N` and
:: `set PROV_ONLINE_COUNT=N`. The .bat files consume these env vars via
:: `call "%~dp0_runtime.bat"` (errors suppressed with 2>nul so a missing
:: file falls through to the REPAIR_MODE branch).
:: =====================================================

:: --- Provider 1: newapi (REMOTE — disabled by default in providers.json) ---
:: To enable: edit providers.json and set newapi.enabled=true, then run
:: `memory probe`. Required: reachable baseURL + valid apiKey. On airgapped
:: networks this provider is permanently offline (PROV_NEWAPI_ONLINE=0).
set PROV_NEWAPI_ID=newapi
set PROV_NEWAPI_ONLINE=0
set PROV_NEWAPI_DISPLAY=New API (GLM-5.1-AWQ-4bit)
set PROV_NEWAPI_BASE_URL=http://10.136.232.50/v1
set PROV_NEWAPI_API_KEY=YOUR_NEWAPI_KEY_HERE
set PROV_NEWAPI_MODEL=GLM-5.1-AWQ-4bit

:: --- Provider 2: llamacpp (LOCAL — enabled by default) ---
:: The only provider that runs on a fully airgapped 16 GB / 1 GB vGPU
:: box. Requires:
::   1) ollama-models\qwen2.5-coder-3b-instruct-q4_k_m.gguf present
::   2) tools\llama-server.exe present (bundled in v2.3)
:: probe.py will set PROV_LLAMACPP_ONLINE=1 after start-qwen.bat succeeds
:: and the /v1/chat/completions probe returns 200.
set PROV_LLAMACPP_ID=llamacpp
set PROV_LLAMACPP_ONLINE=0
set PROV_LLAMACPP_DISPLAY=Qwen2.5-Coder-3B (llama.cpp, CPU-tuned)
set PROV_LLAMACPP_BASE_URL=http://127.0.0.1:11435/v1
set PROV_LLAMACPP_API_KEY=llama-local-key
set PROV_LLAMACPP_MODEL=qwen2.5-coder:3b-instruct-q4_K_M
set PROV_LLAMACPP_PORT=11435
set PROV_LLAMACPP_MODEL_PATH=ollama-models\qwen2.5-coder-3b-instruct-q4_k_m.gguf
set PROV_LLAMACPP_EXECUTABLE=tools\llama-server.exe

:: --- Provider 3: qwen-fast (LOCAL — opt-in, disabled by default) ---
:: Edit providers.json and set qwen-fast.enabled=true AFTER downloading
:: ollama-models/qwen2.5-1.5b-instruct-q4_k_m.gguf. Then re-run probe.
:: Skip the seed block below — probe.py will add it automatically.
:: set PROV_QWEN_FAST_ID=qwen-fast
:: set PROV_QWEN_FAST_ONLINE=0
:: set PROV_QWEN_FAST_DISPLAY=Qwen2.5-1.5B (llama.cpp, fast vGPU)
:: set PROV_QWEN_FAST_BASE_URL=http://127.0.0.1:11436/v1
:: set PROV_QWEN_FAST_API_KEY=llama-local-key
:: set PROV_QWEN_FAST_MODEL=qwen2.5:1.5b-instruct-q4_K_M
:: set PROV_QWEN_FAST_PORT=11436
:: set PROV_QWEN_FAST_MODEL_PATH=ollama-models\qwen2.5-1.5b-instruct-q4_k_m.gguf
:: set PROV_QWEN_FAST_EXECUTABLE=tools\llama-server.exe

:: --- Summary counters (probe.py will rewrite these) ---
set PROV_COUNT=2
set PROV_ONLINE_COUNT=0
