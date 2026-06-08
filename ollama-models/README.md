# ollama-models\

This directory is **intentionally empty** in the package.

## What to put here

Place one or more GGUF model files. Default config (`providers.json` → `llamacpp.modelPath`) expects:

```
qwen3-4b-q4_k_m.gguf    (~2.5 GB, recommended)
```

Any Qwen 3 / Qwen 2.5 / Llama 3 GGUF works. llama-server.exe auto-detects from filename.

## How to download (offline-safe)

1. Get `qwen3-4b-q4_k_m.gguf` from Hugging Face / ModelScope on an internet-enabled machine
2. Copy to this folder via USB / SMB
3. Run `python probe.py` — it will auto-discover the file
4. The `modelPath` field in `providers.json` is relative to the package root, so no path editing needed if filename matches

## Disk usage

- Single 4B model: ~2.5 GB
- Single 7B model: ~4.5 GB
- Single 14B model: ~9 GB (not recommended for <16 GB RAM)

## Verifying

After dropping a GGUF here, run:
```
python ..\probe.py
```

You should see `[ON]  Qwen3-4B (llama.cpp)` in the menu.
