# AGENTS.md — ai-longterm-wiki-memory-OpenClaw

> ## ⛔ STOP — READ THIS BEFORE ANYTHING ELSE
>
> **Every session, before any action:**
> 1. `Read wiki-session.md` — check current status
> 2. `Read skills/wiki-core.md` — load the full protocol
>
> These are local files, not plugins. Use the **Read tool**, not a Skill/Tool call.
> If you see `<wiki-briefing>` in your context, it already contains the summary —
> but you must still Read skills/wiki-core.md for the full protocol.
>
---

This repo provides a long-term wiki memory system for AI agents.
It injects semantically relevant wiki pages into every prompt automatically.

## Installation

### OpenClaw agent

```bash
py scripts/setup_openclaw.py --workspace /absolute/path/to/workspace
```

If auto-detection fails: add `--config /path/to/openclaw/config.json`

Restart the agent after installation.

## PDF ingestion — CRITICAL workflow

Text extraction uses **pdfplumber** (bundled in `wiki_pdf_watcher.py`).

```bash
wiki.py ingest-pdf --workspace <path> --file <path|url>
```

This deposits extracted raw text into `wiki-works/<project>/raw/`.

**After `ingest-pdf`, the agent must:**
1. Read each deposited file in `raw/`
2. Write structured `.tmp` pages (see `skills/wiki-core.md §ingest`)
3. Call `wiki.py ingest --workspace <path> --pages <file.tmp>`

## process-raw vs ingest — DO NOT CONFUSE

| Command | When to use |
|---------|-------------|
| `wiki.py ingest` | Always — agent writes `.tmp` pages, then calls this |
| `wiki.py process-raw` | ONLY for bulk re-indexing of raw files already in `raw/` — does NOT create structured wiki pages |

**Never use `process-raw` as a shortcut for the INGEST workflow.**

## Architecture (v3) — three layers, one brain

| Layer | Directory | Contents | Who writes |
|-------|-----------|----------|------------|
| **Domain knowledge** | `wiki-works/<topic>/` | Deep knowledge per topic: concepts, research, entities | INGEST workflow |
| **Distilled knowledge** | `wiki/` | Cross-domain knowledge, promoted autonomously | Agent (autonomous) |
| **Identity** | `wiki/identity/` | Values, style, learned behavioral patterns | Only `wiki.py self-reflect` |

Promote a page from `wiki-works/` to `wiki/` autonomously when relevant in ≥2 topics and retrieved in ≥3 queries.

## Behavioral feedback

When the user corrects behavior:
```bash
wiki.py behavior-log --workspace <path> --event "<canonical phrase>"
```
At end of session, run autonomously if ≥1 correction received:
```bash
wiki.py self-reflect --workspace <path>
```

## Wiki context injection

Every prompt arrives preceded by:
```
<wiki-context>
Pre-loaded wiki context (top 3 pages by semantic relevance):
### wiki/concepts/rag.md  [relevance: 0.91]
[page content...]
</wiki-context>
```

Use this directly. Do not re-run `wiki.py query` for the same prompt.
If all relevance scores < 0.4 → wiki has no relevant knowledge, proceed normally.

## Dashboard

```bash
wiki.py serve --workspace <path> [--no-auth]
```

Opens at `http://localhost:7331`. Tabs: **Graf** (page graph) and **Stats**.

## First-time wiki setup

### Workspace = repo directory (most common)

`wiki.config.json` already exists with placeholder values. Run:

```bash
py scripts/wiki.py rebuild --workspace /absolute/path/to/this/repo
```

### Workspace = separate directory

```bash
mkdir -p /path/to/workspace/wiki /path/to/workspace/wiki-works /path/to/workspace/memory
```

`wiki.config.json` template (replace `<WORKSPACE>` with the absolute path):
```json
{
  "workspace": "<WORKSPACE>",
  "pdf_inbox": { "project_default": "ricerca" },
  "projects": {
    "ricerca": { "path": "wiki-works/ricerca", "keywords": [] }
  },
  "thresholds": {
    "index_token_budget": 4000, "staleness_days": 90,
    "similarity_merge": 0.95, "similarity_orphan": 0.50,
    "synthesis_min_tokens": 300, "synthesis_min_sources": 2,
    "chunk_size_tokens": 512, "chunk_overlap_tokens": 64,
    "page_chunk_threshold_tokens": 1500, "quality_filter_min_score": 6,
    "dedup_auto": 0.90, "dedup_warn": 0.75
  },
  "self_reflection": { "enabled": true, "correction_threshold": 3 },
  "lancedb": { "path": "memory/lancedb", "embedding_model": "BAAI/bge-m3" },
  "exclude_from_index": []
}
```

Then:
```bash
py scripts/wiki.py rebuild --workspace /path/to/workspace
```

Available commands: `ingest`, `query`, `lint`, `index`, `rebuild`, `session-update`,
`scan-inbox`, `ingest-pdf`, `process-raw`, `serve`, `behavior-log`, `self-reflect`
