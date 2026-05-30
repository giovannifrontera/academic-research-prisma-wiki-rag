<div align="center">

# AI Longterm Wiki Memory — OpenClaw Plugin

**Semantic long-term memory for AI agents**

Your AI agent forgets everything between sessions. This gives it a structured, self-healing knowledge base it actually maintains — where every page is simultaneously a readable document and a searchable vector.

[![Version](https://img.shields.io/badge/version-3.1.2-informational)](CHANGELOG.md)
[![Tests](https://img.shields.io/badge/tests-124%20passed-brightgreen)](tests/)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-AGPL--3.0-blue)](LICENSE)
[![OpenClaw](https://img.shields.io/badge/works%20with-OpenClaw-purple)](https://github.com/openclaw/openclaw)

[Quick Start](#quick-start) · [Features](#features) · [Architecture](#architecture) · [PDF Ingestion](#multi-source-pdf-ingestion-v20) · [Web Interface](#web-interface-v21) · [Dashboard](#dashboard-observability-v22) · [Integration](#integration) · [CLI Reference](#cli-reference)

---

</div>

> ### 🤖 If you are an AI agent reading this repo
>
> **Do not proceed without reading your platform's install file first.**
>
> | You are running on… | Read this file immediately |
> |---------------------|---------------------------|
> | **OpenClaw** | [`AGENTS.md`](AGENTS.md) |
>
> This file contains mandatory installation steps. Skipping them means the wiki context injection will not work and every subsequent action may silently fail.

## Interface

**Graph view** — the D3 force graph shows all wiki pages as nodes, coloured by category. When the agent retrieves pages to answer a prompt, the activated nodes pulse gold in real time via WebSocket.

![Graph view with query-hit animation](docs/images/graph-view.svg)

**Stats tab** — embedding coverage, most-queried pages, stale pages, semantic duplicate warnings, and auto-lint countdown.

![Stats dashboard](docs/images/stats-tab.svg)

---

## The problem

AI agents forget everything between sessions. Existing memory systems are flat — a pile of timestamped facts, not a knowledge base. When you work on recurring research (academic literature, competitive analysis, trading signals, legal cases), you need knowledge that is **organized, interconnected, and semantically searchable** — and that grows over time without human bookkeeping.

## What it does

AI Longterm Wiki Memory gives your agent a **three-layer brain** it maintains autonomously — all layers indexed together in a single LanceDB vector space:

| Layer | Directory | Contents | Who writes |
|-------|-----------|----------|------------|
| **Domain knowledge** | `wiki-works/<topic>/` | Deep knowledge per domain: concepts, research, entities | INGEST workflow |
| **Distilled knowledge** | `wiki/` | Cross-domain knowledge, promoted autonomously when useful across ≥2 topics | Agent (autonomous promotion) |
| **Identity** | `wiki/identity/` | Behavioral patterns, values, style — learned from corrections | Only `wiki.py self-reflect` |

The agent ingests web pages, papers, and PDFs; retrieves by semantic meaning (not keywords); promotes knowledge autonomously between layers; detects stale or contradictory knowledge; and synthesizes new pages automatically when multiple sources support a non-obvious inference — all without corrupting the knowledge base even if a process crashes mid-operation.

```
User: "study this paper on RAG architectures"

Agent: [INTENT: INGEST | WORKSPACE: research | CONFIDENCE: high]
       → writes structured pages as .tmp files
       → wiki.py ingest: atomic staging → production commit
       → markdown + embeddings written in the same operation
       → "2 pages written. Mini-lint: ok."
       → checks promotion criteria: retrieved in ≥3 queries, cross-domain?
       → promotes to wiki/concepts/rag.md autonomously if criteria met

User: "what do you know about retrieval-augmented generation?"

Agent: [INTENT: QUERY | WORKSPACE: research | CONFIDENCE: high]
       → <wiki-context> already injected (pre-prompt hook)
       → reads relevant pages, synthesizes with citations
       → synthesis meets threshold → auto-saved as new wiki page

User: "stop adding a summary at the end of every response"

Agent: [INTENT: BEHAVIOR_FEEDBACK | CONFIDENCE: high]
       → wiki.py behavior-log --event "no trailing summary"
       → at session end: wiki.py self-reflect → wiki/identity/ updated
```

---

## The core idea: wiki and vector DB as one

> **Karpathy's wiki pattern** ([gist](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)) has the LLM navigate the wiki by *reading* markdown files. This breaks down at scale — the agent cannot scan dozens of pages on every query.

This project solves that with a **dual-representation architecture**: every page has two synchronized forms.

```
  Write a wiki page
        │
        ▼
┌───────────────────┐     ┌──────────────────────────┐
│  Markdown file    │     │  LanceDB vector store     │
│  wiki/concepts/   │◄────►  bge-m3 embeddings        │
│  rag.md           │     │  (1024-dim, HNSW index)   │
└───────────────────┘     └──────────────────────────┘
   humans browse               LLM retrieves
   LLM generates               semantically
```

Markdown and embeddings are **written atomically** and kept in sync at all times. The lint pass detects and repairs any drift.

A query about *"how LLMs handle long context"* retrieves pages about *"positional encoding"* and *"sliding window attention"* — with no keyword overlap — because the meaning is close in embedding space.

---

## Features

### Semantic vector search
[bge-m3](https://huggingface.co/BAAI/bge-m3) embeddings — multilingual (100+ languages), 1024-dim, HNSW index. Queries retrieve by meaning. No re-indexing step. The vector DB is the index, maintained continuously.

### Atomic writes — crash-safe
Every ingest follows a `.tmp → staging LanceDB → atomic promotion` pattern. A crash leaves the system in a detectable state (`in-progress` in `wiki-session.md`). The agent recovers at the next session with no data loss, no silent corruption.

### Pre-prompt context injection
`wiki_context.py` runs a vector search **before every user message** and prepends a `<wiki-context>` block with the most relevant pages. This eliminates the main failure mode of skill-based approaches — the agent getting context only when it classifies a message as QUERY:

```
User types a message
        │
        ▼
wiki_context.py → vector search
        │
        ▼
<wiki-context> block prepended to the prompt
        │
        ▼
Agent has relevant context — regardless of intent classification
```

Install for OpenClaw (one command):
```bash
py scripts/setup_openclaw.py --workspace /path/to/workspace
```

### Multi-project routing
Define multiple research domains in `wiki.config.json` with keyword lists. The agent auto-selects the right workspace from message content — no manual specification needed.

### Automatic synthesis
When a query response integrates ≥2 wiki sources, exceeds 300 tokens, and adds non-literal inference, the agent saves it as a new wiki page with embeddings. Knowledge compounds over time.

### Self-healing lint
`wiki.py lint --full` detects and repairs:
- **Broken wiki links** (`[[page]]` with no matching file)
- **Orphan LanceDB entries** (vectors for deleted files — auto-removed)
- **Renames** (file moved → updates DB path without re-embedding via `content_hash`)
- **Semantic duplicates** (cosine similarity > 0.95 across pages)

### Token-budget index
`index.md` respects a configurable token budget (default 4000). When exceeded, applies reduction strategies automatically — so the agent can navigate even on small context windows.

### Observability dashboard
A `[Stats]` tab in the web frontend gives a live view of the wiki health: pages embedded vs unembedded, stale pages (configurable threshold), top-10 most queried pages, lint status with last-run timestamp and warning count, and the auto-lint schedule. Lint can also be triggered manually from the browser.

### Autonomous promotion
When a page from `wiki-works/<topic>/` is retrieved in ≥3 distinct queries and proves relevant across ≥2 topics, the agent promotes it to `wiki/` without user confirmation — cross-domain knowledge compounds automatically.

### Semantic deduplication
`wiki.py lint --full` detects semantically similar pages via cosine similarity. Similarity ≥ 0.90 → auto-merge candidate; 0.75–0.90 → user warning. Configurable via `thresholds.dedup_auto` and `thresholds.dedup_warn`.

### Behavioral self-reflection (Identity layer)
When the user corrects the agent's behavior ("always", "never", "stop doing X"), the correction is logged with `wiki.py behavior-log`. At end of session, `wiki.py self-reflect` reads the log and autonomously updates `wiki/identity/` when a pattern reaches the threshold (default: 3 occurrences). The agent learns without human approval of each update.

---

## Multi-source PDF ingestion *(v2.0)*

Any PDF from any source converges at `pdf-inbox/` and is processed automatically.

```
┌─────────────────┐   ┌──────────────────┐   ┌───────────────────┐
│  Telegram chat  │   │  CLI / URL       │   │  Manual file drop │
│  (attachment)   │   │  (ingest-pdf)    │   │  (filesystem)     │
└────────┬────────┘   └────────┬─────────┘   └────────┬──────────┘
         │                     │                       │
         └─────────────────────┼───────────────────────┘
                               ▼
                    workspace/pdf-inbox/
                       paper.pdf
                    .registry.json  ← SHA-256 hash per file
                               │
                    wiki.py scan-inbox
                               │
                    wiki_pdf_watcher.py
                       extract_text (pdfplumber)
                               │
                               ▼
              wiki-works/<project>/raw/paper.md
              (frontmatter: source: pdf, original, extracted_at)
                               │
                               ▼
                    Agent structures into .tmp pages
                               │
                               ▼
                    wiki.py ingest → wiki/ + LanceDB
```

**How change detection works:** SHA-256 hash per file. Same hash + `deposited` → skip. Different hash → reprocess. Status `pending` written before extraction begins — a crash leaves the registry recoverable.

**Commands:**
```bash
# Local file
wiki.py ingest-pdf --workspace <path> --file paper.pdf

# Remote URL (50 MB cap — SSRF-protected)
wiki.py ingest-pdf --workspace <path> --file https://arxiv.org/pdf/2401.00001

# Scan entire inbox — idempotent, safe for cron
wiki.py scan-inbox --workspace <path>
```

**Telegram / OpenClaw:** no new plugin needed. The agent rule in `AGENTS_PATCH.md` covers it:
> When user sends a PDF → call `wiki.py ingest-pdf --workspace <path> --file <attachment_path>`

**Scanned PDFs** (no selectable text) are flagged with `status: failed` in the registry and skipped on future scans — no infinite retry loops.

---

## Web Interface *(v2.1)*

A read-only web frontend for exploring the wiki in a browser — without touching any workflow.

```
py scripts/wiki.py serve --workspace /path/to/workspace [--port 7331] [--no-auth]
```

Open `http://localhost:7331`.

```
┌──────────────────────────────────────────────────────────┐
│  AI Wiki Memory   [wiki] [research] [tutti]    🔍  ● live │
├───────────────────────────┬──────────────────────────────┤
│                           │  # Page Title                │
│    KNOWLEDGE GRAPH        │  concept · research · date   │
│    (D3 force-directed)    │  ──────────────────────────  │
│                           │  [rendered markdown]         │
│  ● entities (blue)        │                              │
│  ● concepts (green)       │  ── Outgoing links ──        │
│  ● synthesis (violet)     │  ── Incoming links ──        │
│  ── explicit link         │  ── Similar pages ──         │
│  ╌╌ semantic similarity   │     embedding (87%)          │
└───────────────────────────┴──────────────────────────────┘
```

**Features:**
- **Force-directed graph** — nodes sized by degree, colored by category (entities/concepts/synthesis), labels on all nodes
- **Explicit edges** — `[[wiki-link]]` references rendered as solid arrows
- **Semantic edges** — LanceDB cosine similarity ≥ 0.65 rendered as dashed lines
- **Live updates** — WebSocket pushes `graph_update` on any file change; graph transitions smoothly without snapping node positions
- **Query hit animation** — when `wiki.py query` runs, the retrieved nodes pulse gold→red for 4 seconds
- **Page panel** — click any node → rendered markdown, outgoing/incoming links, similar pages with similarity bars
- **Project tabs** — filter graph to one workspace at a time
- **Password protection** — JWT cookie auth (7-day session); set via `wiki.config.json` or `WIKI_PASSWORD` env var; bypass with `--no-auth` for local use

**Config (optional):**
```json
{
  "frontend": {
    "password": "your-password",
    "session_days": 7
  }
}
```

**Public exposure with ngrok:**
```bash
py scripts/wiki.py serve --workspace . --host 0.0.0.0
ngrok http 7331
```

**The frontend is strictly read-only for wiki content.** All wiki workflows (ingest, query, lint) continue to function identically whether the server is running or not.

---

## Dashboard Observability *(v2.2)*

A `[Stats]` tab built into the web server shows the health of the wiki at a glance — no CLI commands needed.

```
┌──────────────────────────────────────────────────────────┐
│  AI Wiki Memory  [Graph] [Stats]          🔍  ● live     │
├──────────────────────────────────────────────────────────┤
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌─────────┐  │
│  │ 47 pages │  │ 312 chunk│  │ 94% cov. │  │ 3 stale │  │
│  └──────────┘  └──────────┘  └──────────┘  └─────────┘  │
│                                                          │
│  Top queried                  Lint status                │
│  ─────────────────            ─────────────────────────  │
│  rag.md           12q         Last run: 2026-05-23       │
│  openai.md         8q         0 errors · 2 warnings      │
│                               [Run lint now]             │
│  Auto-lint: every 24h · next: 2026-05-24 08:15           │
└──────────────────────────────────────────────────────────┘
```

**What it shows:**
- **4 KPI cards** — total pages, total chunks, embedding coverage %, stale pages count
- **Top queried** — top-10 pages by query frequency, aggregated from `.wiki-query-log.jsonl`
- **Stale pages** — pages not modified in more than `thresholds.staleness_days` (default 90 days)
- **Unembedded pages** — files present on disk but missing from LanceDB
- **Lint status** — last run timestamp, error count, warning count (from `.wiki-lint-status.json`)
- **Auto-lint schedule** — next scheduled run if `frontend.lint_interval_hours` is configured

**Lint trigger:** The "Run lint now" button calls `POST /api/lint`. Returns 409 if a lint run is already in progress.

**Auto-lint:** Add to `wiki.config.json` to run lint automatically on a schedule:
```json
{
  "frontend": {
    "lint_interval_hours": 24
  }
}
```
The scheduler starts with the server. If omitted, auto-lint is disabled and the button remains available for manual runs.

**REST endpoints (auth-protected):**
| Endpoint | Description |
|----------|-------------|
| `GET /api/stats` | Returns all observability data as JSON |
| `POST /api/lint` | Triggers `wiki.py lint --full`; 409 if busy |

---

## Architecture

```
workspace/
├── skills/
│   └── wiki-core.md          ← permanent skill: intent classification, workflows (v3)
├── wiki-session.md           ← live session state (generated by wiki.py)
├── wiki.config.json          ← configuration
├── scripts/
│   ├── wiki.py               ← unified CLI entry point (11 commands)
│   ├── wiki_context.py       ← pre-prompt context injector (hook)
│   ├── wiki_pdf_watcher.py   ← PDF inbox scanner (hash detection + pdfplumber)
│   ├── wiki_embed.py         ← boundary-aware chunking + bge-m3 embeddings
│   ├── wiki_lancedb.py       ← LanceDB ops (upsert, staging, rename detection)
│   ├── wiki_index.py         ← token-budget index generation
│   ├── wiki_graph.py         ← node/edge builder (filesystem + LanceDB, 30s cache)
│   └── wiki_server.py        ← FastAPI server: REST, WebSocket, JWT auth, stats/lint endpoints
├── frontend/
│   └── index.html            ← SPA: D3.js graph + page panel + WebSocket client
├── pdf-inbox/                ← all PDF sources converge here
│   └── .registry.json        ← hash + status per PDF (atomic write)
├── .wiki-lint-status.json    ← last lint result (written atomically by cmd_lint)
├── .wiki-behavior-log.jsonl  ← behavioral corrections log (appended by behavior-log)
├── wiki/                     ← distilled cross-domain knowledge + identity layer
│   ├── entities/             ← people, tools, organizations (cross-domain)
│   ├── concepts/             ← theories, strategies, definitions (cross-domain)
│   ├── synthesis/            ← cross-source inferences (cross-domain)
│   └── identity/             ← behavioral patterns (written only by self-reflect)
├── wiki-works/               ← deep domain knowledge (permanent, per topic)
│   └── <topic>/
│       ├── raw/              ← raw fetched sources and extracted PDFs
│       ├── entities/
│       ├── concepts/
│       └── synthesis/
└── memory/
    └── lancedb/              ← vector database — all three layers indexed together
```

**Core invariant:** The agent never writes directly to the wiki. Everything goes through `wiki.py`. The skill guides *when* and *why*; the scripts handle *how*.

---

## Integration

Works with any agent that can read files and call bash commands. This repo provides first-class support for OpenClaw.

### Claude Code

For the native Claude Code MCP integration (recommended), see the dedicated repo: [`ai-longterm-wiki-memory-ClaudeCode`](https://github.com/giovannifrontera/ai-longterm-wiki-memory-ClaudeCode).

> This repo focuses on the OpenClaw plugin. The `wiki_context.py` script is still shared — both integrations call the same Python backend.

### OpenClaw

[OpenClaw](https://github.com/openclaw/openclaw) connects Telegram, Discord, and web to AI agents with bash/file/browser access on your filesystem.

**Agent-driven setup (recommended):** provide the repo link in chat and ask the OpenClaw agent to install. It reads `AGENTS.md` and runs:
```bash
py scripts/setup_openclaw.py --workspace /absolute/path/to/workspace
```
The script auto-detects the OpenClaw config file and injects the plugin entry. Pass `--config /path/to/config.json` if auto-detection fails.

**Manual setup:**
```bash
cd plugins/wiki-context-plugin
npm install && npm run build
```

Add to OpenClaw config:
```json
{
  "plugins": [
    {
      "id": "wiki-context-plugin",
      "path": "/absolute/path/to/ai-wiki-system/plugins/wiki-context-plugin",
      "config": {
        "workspace": "/absolute/path/to/workspace",
        "wikiContextScript": "/absolute/path/to/scripts/wiki_context.py",
        "pythonExecutable": "python",
        "k": 3
      }
    }
  ]
}

### What the agent does automatically

| User says | Agent does |
|-----------|-----------|
| URL / "study this" / file attachment | INGEST: fetch → structure → atomic write + embed → evaluate promotion |
| PDF via Telegram / CLI / URL | INGEST-PDF: inbox → extract → deposit in raw/ → structure |
| Direct question / "explain" / "what do you know about" | QUERY: `<wiki-context>` already injected → read pages → synthesize → auto-save if threshold met |
| "check the wiki" / "maintenance" / "broken links" | LINT: broken links, orphans, renames, semantic duplicates |
| "always", "never", "stop doing X" (behavioral correction) | BEHAVIOR_FEEDBACK: log correction → self-reflect at session end → `wiki/identity/` updated |
| Ambiguous | Asks one clarifying question, never guesses |

The agent always emits a classification line before acting — you can correct it before execution:
```
[INTENT: INGEST | WORKSPACE: research | CONFIDENCE: high]
```

### Session state

`wiki-session.md` (managed exclusively by `wiki.py`) tracks:
- Status: `ok` / `in-progress` / `needs-repair` / `partial-failure`
- Last operation: type, timestamp, detail
- Active workspace and page count

If the agent finds `in-progress` at session start, it warns before doing anything.

---

## Quick Start

### Requirements

- Python 3.10+
- ~2 GB disk (BAAI/bge-m3 model, downloaded automatically on first run)

### Install

```bash
git clone https://github.com/giovannifrontera/ai-longterm-wiki-memory-OpenClaw
cd ai-longterm-wiki-memory-OpenClaw
pip install -r requirements.txt
```

### Configure

```bash
cp wiki.config.json my-workspace/wiki.config.json
# Edit: set workspace path, add your projects and keywords
```

Minimal config:
```json
{
  "workspace": "/path/to/your/workspace",
  "pdf_inbox": {
    "project_default": "research"
  },
  "projects": {
    "research": {
      "path": "wiki-works/research",
      "keywords": ["paper", "study", "article", "review"]
    }
  },
  "thresholds": {
    "index_token_budget": 4000,
    "staleness_days": 90,
    "similarity_merge": 0.95,
    "similarity_orphan": 0.50,
    "synthesis_min_tokens": 300,
    "synthesis_min_sources": 2,
    "chunk_size_tokens": 512,
    "chunk_overlap_tokens": 64,
    "page_chunk_threshold_tokens": 1500,
    "quality_filter_min_score": 6
  },
  "lancedb": {
    "path": "memory/lancedb",
    "embedding_model": "BAAI/bge-m3"
  }
}
```

> **`pdf_inbox.project_default`** — where PDFs go when the filename doesn't match any project's keywords. If omitted, falls back to the first project in config.

### Initialize and test

```bash
py scripts/wiki.py rebuild --workspace my-workspace/
pytest tests/ -v
# Expected: 124 passed
```

### Dependencies

| Package | Purpose |
|---------|---------|
| `lancedb ≥ 0.6.0` | Vector database — stores bge-m3 embeddings with staging table for atomic ingest |
| `sentence-transformers ≥ 3.0.0` | Loads BAAI/bge-m3 locally — multilingual chunked embedding |
| `pyarrow ≥ 14.0.0` | Columnar storage for LanceDB batch operations |
| `pandas ≥ 2.0.0` | DataFrame ops for lint statistics and rename detection |
| `pdfplumber ≥ 0.11.0` | PDF text extraction — used by `wiki_pdf_watcher.py` |
| `pyyaml ≥ 6.0` | Parses `wiki.config.json` and YAML frontmatter |
| `requests ≥ 2.31.0` | HTTP fetching during source ingestion |
| `pytest ≥ 8.0.0` | Test runner — 124 tests covering all workflows |
| `fastapi ≥ 0.111.0` | Web server for the browser frontend |
| `uvicorn[standard] ≥ 0.29.0` | ASGI server — runs FastAPI with WebSocket support |
| `watchfiles ≥ 0.21.0` | Async file watcher — triggers live graph updates |
| `python-jose[cryptography] ≥ 3.3.0` | JWT cookie auth for the frontend |
| `httpx ≥ 0.27.0` | Async HTTP client (test only) |

---

## CLI Reference

```
wiki.py <command> [arguments]

  ingest         --workspace <path> --pages <p1.tmp,p2.tmp,...> --log <str>
  query          --workspace <path> --q <string> [--k 5]
  lint           --workspace <path> [--full]
  index          --workspace <path>
  rebuild        --workspace <path>
  session-update --workspace <path> --op <type>
                   --status <ok|failed|in-progress|partial-failure> [--detail <json>]
  scan-inbox     --workspace <path>
  ingest-pdf     --workspace <path> --file <local-path|url>
  serve          --workspace <path> [--host 127.0.0.1] [--port 7331] [--no-auth]
  behavior-log   --workspace <path> --event "<canonical correction phrase>"
  self-reflect   --workspace <path>

wiki_context.py  (hook — outputs <wiki-context> block to stdout)
  --workspace <path>  --q <string>  [--k 3]  [--max-chars 600]
```

Every command outputs JSON to stdout:
```json
{ "status": "ok",   "op": "ingest",     "pages_written": 2, "mini_lint": "ok" }
{ "status": "ok",   "op": "scan-inbox", "processed": 1, "skipped": 0, "failed": 0,
  "deposited": ["wiki-works/research/raw/paper.md"], "failures": [] }
{ "status": "error","code": "lock_exists", "message": "...", "recoverable": true }
```

---

## How It Works

**Chunking** — Pages split using the bge-m3 native tokenizer. Boundaries respect `##` and `###` headings — chunks never cut mid-section. Pages under 1500 tokens are embedded whole; larger pages are chunked at 512 tokens with 64-token overlap.

**Upsert semantics** — `upsert(path, chunks)` deletes all existing chunks for that path before inserting new ones. This prevents orphan chunks when a page changes chunk count.

**Rename detection** — During lint, compares `content_hash` between DB-only paths and filesystem-only paths. Matching hashes = rename → path updated in DB without re-embedding.

**Staging table** — Ingest writes vectors to `staging_wiki_pages` first. Only `promote_staging()` moves them to `wiki_pages`. A crash leaves staging populated; the next session clears it and logs the event.

**PDF crash recovery** — Status `pending` is written to `.registry.json` before extraction begins. A mid-operation crash leaves `pending`, which triggers reprocessing on the next scan.

---

## Comparison with Karpathy's pattern

| Dimension | Karpathy's pattern | AI Longterm Wiki Memory |
|-----------|-------------------|------------------------|
| **Form** | Conceptual pattern — prose + guidelines | Full Python implementation with CLI |
| **Retrieval** | LLM reads/scans markdown files | Semantic vector search — LLM never scans files |
| **Wiki + vectors** | Separate concerns | One atomic operation: write page = write embeddings |
| **Crash safety** | Not addressed | Atomic `.tmp → staging → promotion` pipeline |
| **Multi-project** | Single wiki | Routed workspaces via `wiki.config.json` |
| **PDF ingestion** | Not addressed | Multi-source: Telegram, URL, CLI, folder drop |
| **Knowledge compounding** | Query answers stay in chat | Auto-synthesis + autonomous promotion across three layers |
| **Lint** | Basic health check concept | Self-healing: orphan vectors, semantic duplicates, renames |
| **Context injection** | Not addressed | `wiki_context.py` pre-injects relevant pages before every prompt |
| **Behavioral learning** | Not addressed | `behavior-log` + `self-reflect` → `wiki/identity/` updated autonomously |
| **Visualization** | Not addressed | Interactive D3 graph with live WebSocket updates |
| **Languages** | English-focused | Multilingual — bge-m3 supports 100+ languages |
| **Testing** | None | 106 automated tests |

---

## Documentation

| File | Contents |
|------|----------|
| [`AGENTS.md`](AGENTS.md) | Agent install instructions for OpenClaw |
| [`DESIGN.md`](DESIGN.md) | Full architecture, workflow specs, LanceDB schema, conflict resolution |
| [`SPEC.md`](SPEC.md) | Implementation spec, error states table, integration detail |
| [`skills/wiki-core.md`](skills/wiki-core.md) | The skill file to install in your agent |
| [`AGENTS_PATCH.md`](AGENTS_PATCH.md) | *(legacy)* Usage instructions — now auto-injected by setup scripts |
| [`README.it.md`](README.it.md) | Documentazione in italiano |

---

## Changelog

### v3.1.2 — 2026-05-27

Internal refactor and test improvements. No functional changes to the OpenClaw plugin.

### v3.1.1 — 2026-05-26

**`wiki_context.py` robustness on Windows**

- **fix: stdout encoding on Windows** — Added `sys.stdout.reconfigure(encoding="utf-8")` at startup. Python on Windows defaults to CP1252, which could cause the hook output to be silently discarded.
- **fix: empty-query early return** — If `--q` and the `CLAUDE_USER_PROMPT` env var are both empty, the script exits immediately without running an embedding search.
- **refactor: `--q` now optional** — `--q` defaults to `""` instead of `required=True`. The env var is the primary source; `--q` remains supported for direct invocations.

### v3.1.0 — 2026-05-25

**Installation robustness + new CLI commands + OpenClaw tool + wiki-setup skill**

- **feat: `process-raw` subcommand** — `wiki.py process-raw --workspace <path> [--project <name>]` bulk-promotes files from `wiki-works/*/raw/` to the index after a PDF scan. Previously required manual `.tmp` workaround.
- **fix: `ingest-pdf` same-path crash** — `shutil.copy2(src, dest)` when `src == dest` raised `PermissionError: [WinError 32]` on Windows. Now guarded with `src.resolve() != dest.resolve()`.
- **feat: OpenClaw `wiki_process_raw` tool** — the TypeScript plugin exposes `wiki_process_raw` as a callable tool from chat. Agents can trigger bulk raw promotion without leaving the conversation.
- **feat: OpenClaw startup Python check** — the plugin validates that the configured Python can import `lancedb` at startup and logs a visible warning if not.
- **feat: `wiki-setup` rigid skill** — `skills/wiki-setup.md` guides any agent through full OpenClaw installation step by step.
- **docs: Windows Store Python troubleshooting** — `docs/install-openclaw.md` documents the `py` launcher issue and how to use the absolute Python path.
- **AGENTS.md**: `wiki.config.json` template updated to complete schema (was incomplete — missing `workspace`, `projects`, `thresholds`).

**Testing:** 116 tests, all green.

### v3.0.1 — 2026-05-24

**Architecture correction + node animation fix + UI mockups**

- **Architecture corrected**: v3.0.0 incorrectly removed the promotion mechanism and limited `wiki/` to identity only. Correct design: `wiki-works/<topic>/` = permanent domain knowledge; `wiki/` = cross-domain distilled knowledge (autonomously promoted); `wiki/identity/` = behavioral patterns (self-reflect). All layers indexed together in LanceDB.
- **fix: node animation** — `wiki_context.py` (the hook that runs on every prompt) now writes retrieved page paths to `.wiki-query-log.jsonl`. The server's WebSocket watcher picks these up and broadcasts `query_hit` to the frontend, which animates the activated nodes gold in real time.
- **UI mockups**: SVG illustrations of the graph view (with query-hit animation) and the Stats tab added to the README.
- All human-facing docs (README, DESIGN, ROADMAP, AGENTS.md, skills) updated to reflect the corrected architecture.

### v3.0.0 — 2026-05-24

**Three-layer brain + Autonomous Promotion + Semantic Deduplication + Self-Reflection**

- **Three-layer architecture**: `wiki-works/<topic>/` stores permanent deep knowledge per domain. `wiki/` holds cross-domain distilled knowledge, promoted autonomously by the agent. `wiki/identity/` stores behavioral patterns learned from corrections. All three layers are indexed together in LanceDB — one unified vector space.
- **Autonomous promotion**: the agent promotes pages from `wiki-works/` to `wiki/` without user confirmation when knowledge is cross-domain (relevant in ≥2 topics, retrieved in ≥3 queries).
- **Semantic deduplication**: `lint --full` detects semantic duplicates via cosine similarity. Similarity ≥ 0.90 → auto-merge candidate. 0.75–0.90 → warning. Configurable via `thresholds.dedup_auto` and `thresholds.dedup_warn`.
- **Autonomous self-reflection**: `wiki.py behavior-log` logs behavioral corrections. `wiki.py self-reflect` autonomously updates `wiki/identity/` when a pattern exceeds the threshold (`self_reflection.correction_threshold`, default 3). No human approval required.

### v2.3.0 — 2026-05-24

**Agent-driven installation**

- `AGENTS.md` — install instructions and full usage protocol inline — no separate patch file needed
- `scripts/setup_openclaw.py` — one-command OpenClaw setup: auto-detects config in 5 standard locations (Windows AppData, Linux XDG, home, local), injects plugin entry atomically, idempotent
- `setup_openclaw.py` injects usage instructions into the workspace `AGENTS.md` automatically after setup — idempotent via `<!-- ai-wiki-system:usage-start -->` sentinel marker

**lint improvements**

- `exclude_from_index` support in `cmd_lint`: pages matching configured patterns are filtered from LanceDB indexing; patterns use `fnmatch` (explicit, not recursive glob)
- Duplicate filename detection in `cmd_lint --full`: warns when two pages share the same basename across different directories
- `wiki_context.py`: reads `chunk_text` directly from LanceDB instead of re-reading files on every query — eliminates redundant disk I/O

**Testing:** 92 tests, all green (unchanged)

---

### v2.2.0 — 2026-05-23

**New: Dashboard Observability** (Stats tab)

- `GET /api/stats` — returns summary KPIs: total pages, embedded pages, stale pages (≥7 days), unembedded pages, top-10 queried pages, lint status and auto-lint schedule
- `POST /api/lint` — triggers `wiki.py lint` in a subprocess; returns 409 if a lint run is already in progress
- Auto-lint asyncio scheduler: reads `frontend.lint_interval_hours` from `config.yaml`; runs lint automatically in the background; exposes `next_run_iso` in `/api/stats`
- `cmd_lint` writes `.wiki-lint-status.json` atomically (tmp → rename) after every lint run, recording `timestamp`, `warnings`, `errors`, `exit_code`
- Frontend `[Stats]` tab: 4 KPI cards (Pages, Embedded, Stale, Unembedded), top-queried list (capped at 10), lint trigger button with 409 feedback

**Testing:** 10 new tests — **92 total, all green**

---

### v2.1.0 — 2026-05-22

**New: Web interface** (`wiki.py serve`)

- `scripts/wiki_graph.py` — builds nodes + edges from filesystem and LanceDB; 30-second cache with dirty flag; `get_page_detail()` with path traversal prevention
- `scripts/wiki_server.py` — FastAPI app: `/api/graph`, `/api/page/{path}`, WebSocket `/ws`, JWT cookie auth; async file watcher (watchfiles) and query-log tail watcher
- `frontend/index.html` — zero-build SPA: D3.js force-directed graph, page panel with rendered markdown (DOMPurify sanitized), live graph updates preserving node positions, query-hit pulse animation
- New CLI command: `wiki.py serve --workspace <path> [--host] [--port 7331] [--no-auth]`
- `wiki.py query` now appends to `.wiki-query-log.jsonl` — picked up by the server for live node animation

**Robustness (post-review)**
- `_query_log_watcher`: `pos = f.tell()` fixes race condition that caused silent query-hit misses
- JWT signing key derived via HMAC from password — never the raw password string
- `httponly=True` on session cookie — reduces XSS surface
- `sys.path.insert` moved to module level in `wiki_server.py`
- `fetchGraph()` preserves D3 `x/y/vx/vy` on existing nodes — no position snap on live updates

**Testing:** 26 new tests (22 frontend-specific + 2 path traversal + 2 WebSocket) — **82 total, all green**

---

### v2.0 — 2026-05-22

**New: Multi-source PDF ingestion**
- `scripts/wiki_pdf_watcher.py` — SHA-256 hash change detection, pdfplumber extraction, atomic registry, crash recovery via `pending` status
- New CLI: `scan-inbox` and `ingest-pdf --file <path|url>` (50 MB cap, path sanitization)
- `pdf-inbox/` convergence point — Telegram, CLI, URL, and manual drops all unified
- No new OpenClaw plugin needed for Telegram PDF attachments
- `partial-failure` added as valid session-update status

**Robustness fixes (pre-release review)**
- `cmd_ingest`: suffix-only `.tmp` strip in `rel_final`; `sys.exit(1)` on lock failure
- `cmd_ingest_pdf`: 50 MB download cap; filename path-traversal protection
- `cmd_session_update`: structured error on malformed JSON `--detail`
- `deposited` list now contains full relative paths, not bare filenames

**Testing:** 21 new unit tests for `wiki_pdf_watcher` — 56 total, all green

---

### v1.1.1 — 2026-05-21

**Bug fixes — Python core**
- **[CRITICAL]** `wiki_lancedb.py`: `table_names()` deprecated — fixed to `.list_tables().tables`
- **[HIGH]** `wiki_workflows.py` `cmd_ingest`: mid-loop `shutil.move` failure left files without vectors — tracked and reversed on exception
- **[MEDIUM]** `cmd_lint`: rename detection scoped to `wiki/` and `wiki-works/` only

**Bug fixes — OpenClaw plugin**
- **[CRITICAL]** `src/index.ts`: `api.getConfig()` doesn't exist — fixed to `api.config`
- **[HIGH]** Build output now copied to plugin root for correct OpenClaw resolution

---

### v1.1.0 — 2026-05-21

**New:** `scripts/wiki_context.py` — pre-prompt context injection. Runs a vector search before every user message and prepends `<wiki-context>`. Eliminates instruction drift as a failure mode.

**Bug fixes**
- **[CRITICAL]** `wiki_index.py`: `rebuild_index()` crashed with `NameError` on every call — `wiki_dir` added as explicit parameter
- **[MEDIUM]** `cmd_index`: `FileNotFoundError` on fresh workspaces — fixed with `os.makedirs`

---

## License

AGPL-3.0 — requires anyone who distributes or runs the software as a service to share the source code.

---

<div align="center">

Works with [OpenClaw](https://github.com/openclaw/openclaw) · Embeddings by [BAAI/bge-m3](https://huggingface.co/BAAI/bge-m3) · Vector store by [LanceDB](https://lancedb.github.io/lancedb/)

</div>
