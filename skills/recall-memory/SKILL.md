---
name: comac-recall-memory
description: Search the agent's persistent memory (agent-memory/) for facts and session history
---

# COMAC Recall Memory

Use this skill when:

- The user asks "what do you remember about X"
- You need to retrieve a previously stored fact (via `memory add`)
- Before answering a project question (to check for prior context)
- You want to summarize recent sessions

## What it searches

- `agent-memory/FACTS.json` - key-value facts (categories: project, person, tool, etc.)
- `agent-memory/sessions/*.md` - session logs (one file per session, appended)
- `agent-memory/identity.md` - agent identity (always included in output)

## How to invoke

```
python skills/recall-memory/recall.py [--query <text>] [--limit N] [--json]
```

- `--query <text>` - case-insensitive substring search across facts and session files
- `--limit N` - max session files to scan (default 20, most recent first)
- `--json` - machine-readable JSON output

If `--query` is omitted, lists the most recent sessions and all facts.

## Output structure

```
identity: <snippet from identity.md>
facts:    [list of {key, value, category, updatedAt} matches]
sessions: [list of {file, date, snippet} matches]
```

## Exit codes

- `0` = matches found (or no query)
- `1` = no matches
- `2` = agent-memory/ missing
- `3` = FACTS.json parse error

## Important

- This skill is **read-only**. To add facts, use `memory add` (the existing `memory.bat` CLI).
- If `FACTS.json` is malformed, report but do not rewrite.
