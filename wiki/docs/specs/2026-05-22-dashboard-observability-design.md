# Wiki Dashboard — Observability Design

**Date:** 2026-05-22
**Status:** Approved
**Scope:** Add a Stats tab to the existing frontend with query frequency, freshness, embedding coverage, lint status, and auto-lint scheduling.

---

## Problem

The wiki grows silently. There is no way to see which pages are most used, which are stale, which have no embeddings, or when the last lint ran — without running CLI commands manually.

---

## Fundamental constraint

**The dashboard is read-only except for the lint trigger.** It aggregates data that already exists (query log, graph cache, LanceDB, lint output). No new persistent state is introduced beyond `.wiki-lint-status.json`.

---

## Architecture

```
frontend/index.html  ──── GET /api/stats ────► wiki_server.py
                     ──── POST /api/lint ────► wiki_server.py
                                                    │
                          ┌─────────────────────────┤
                          │                         │
                    wiki_graph.py             wiki_workflows.py
                    (nodes: last_modified)    (cmd_lint → writes
                    LanceDB (chunk counts,     .wiki-lint-status.json)
                    coverage)
                    .wiki-query-log.jsonl
                    .wiki-lint-status.json
```

Auto-lint runs as an `asyncio` task inside `wiki_server.py` (same pattern as `_file_watcher`). No external scheduler needed.

---

## New API endpoints

### `GET /api/stats`

Aggregates all observability data in a single call. Protected by auth middleware (same as `/api/graph`).

Response schema:
```json
{
  "summary": {
    "total_pages": 47,
    "total_chunks": 312,
    "embedding_coverage_pct": 94.2,
    "stale_pages_count": 3
  },
  "top_queried": [
    { "path": "wiki/concepts/rag.md", "title": "RAG", "query_count": 12 },
    { "path": "wiki/entities/openai.md", "title": "OpenAI", "query_count": 8 }
  ],
  "stale_pages": [
    { "path": "wiki/concepts/vecchio.md", "title": "Vecchio", "age_days": 120 }
  ],
  "unembedded_pages": [
    { "path": "wiki/new/draft.md", "title": "Draft" }
  ],
  "lint_status": {
    "last_run": "2026-05-20T14:32:00",
    "errors": 0,
    "warnings": 2,
    "detail": "2 orphan vectors removed"
  },
  "auto_lint": {
    "enabled": true,
    "interval_hours": 24,
    "next_run_iso": "2026-05-23T08:15:00"
  }
}
```

`top_queried`: top 10 by count, aggregated from `.wiki-query-log.jsonl`. Returns `[]` if file absent.

`stale_pages`: nodes where `(now - last_modified) > staleness_days * 86400`. `staleness_days` from `wiki.config.json → thresholds.staleness_days` (default 90).

`unembedded_pages`: filesystem nodes whose path does not appear in LanceDB. If LanceDB unavailable, returns `[]`.

`lint_status`: parsed from `.wiki-lint-status.json`. Returns `null` if file absent (lint never run).

`auto_lint.next_run_iso`: computed from server start time + interval. `null` if `lint_interval_hours` not set in config.

### `POST /api/lint`

Triggers `wiki.py lint --workspace <workspace>` as a subprocess. Returns stdout/stderr.

```json
{ "status": "ok", "output": "Lint complete. 0 errors, 2 warnings." }
{ "status": "error", "output": "..." }
```

Runs synchronously (lint is fast — typically <2s). If lint is already running, returns 409 Conflict.

---

## `cmd_lint` change: write `.wiki-lint-status.json`

After lint completes, `cmd_lint` in `wiki_workflows.py` appends one JSON line to `.wiki-lint-status.json` (overwrite, not append — always the latest status):

```json
{
  "last_run": "2026-05-22T14:32:00",
  "errors": 0,
  "warnings": 2,
  "detail": "2 orphan vectors removed"
}
```

Written atomically (`.wiki-lint-status.json.tmp` → rename). Does not affect current stdout output.

---

## Auto-lint scheduler

`asyncio` task started at server startup alongside `_file_watcher` and `_query_log_watcher`.

```python
async def _auto_lint_task():
    interval = _cfg.get("frontend", {}).get("lint_interval_hours")
    if not interval:
        return  # disabled if not configured
    while True:
        await asyncio.sleep(interval * 3600)
        # run lint as subprocess
```

- If server is restarted, the timer resets (acceptable — no persistent schedule state)
- Lint output is written to `.wiki-lint-status.json` via the updated `cmd_lint`
- No broadcast to WebSocket clients (lint result visible on next `/api/stats` poll)

---

## Frontend — Stats tab

Added to existing `frontend/index.html`. Navigation: header gains a `[Stats]` tab alongside `[Graph]`. Clicking toggles visibility of `#graph-pane` vs `#stats-pane` — single-page, no routing library.

**Layout (responsive — stacks vertically on narrow screens):**

```
┌──────────────────────────────────────────────────────────┐
│  AI Wiki Memory  [Graph] [Stats]   🔍  ● live            │
├──────────────────────────────────────────────────────────┤
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌─────────┐  │
│  │ 47 pagine│  │ 312 chunk│  │ 94% cov. │  │ 3 stale │  │
│  └──────────┘  └──────────┘  └──────────┘  └─────────┘  │
│                                                          │
│  Più interrogate          Pagine stale (>90gg)           │
│  ─────────────────        ──────────────────────         │
│  rag.md          12q      concepts/vecchio.md  120gg     │
│  openai.md        8q      entities/foo.md       95gg     │
│                                                          │
│  Pagine senza embedding   Lint                           │
│  ──────────────────────   ──────────────────────         │
│  wiki/new/draft.md        2026-05-20 14:32               │
│                           0 errori · 2 avvisi            │
│                           [Esegui lint ora]              │
│                                                          │
│  Auto-lint: ogni 24h · prossima: 2026-05-23 08:15        │
└──────────────────────────────────────────────────────────┘
```

- Summary cards: 4 KPI in a CSS grid (2×2 on mobile, 4×1 on desktop)
- All lists capped at 10 items
- "Esegui lint ora" button: POST `/api/lint`, shows spinner, updates status inline on completion
- Stats are fetched once on tab activation; a "Aggiorna" button triggers a re-fetch
- No auto-polling — lint and query data change infrequently

---

## Config (optional)

```json
{
  "frontend": {
    "lint_interval_hours": 24
  }
}
```

If omitted, auto-lint is disabled. The dashboard still shows manual lint button and last status.

---

## Files modified

| File | Action |
|------|--------|
| `scripts/wiki_server.py` | + `/api/stats`, `/api/lint`, `_auto_lint_task`, lint-busy flag |
| `scripts/wiki_workflows.py` | `cmd_lint` writes `.wiki-lint-status.json` atomically |
| `frontend/index.html` | + `[Stats]` nav tab, `#stats-pane`, fetch `/api/stats`, lint button |
| `wiki.config.json` | document `frontend.lint_interval_hours` (no change to file) |

No new Python packages required.

---

## Testing

| Test | What it verifies |
|------|-----------------|
| `test_api_stats_endpoint` | Response has all required keys; works with empty query log |
| `test_api_stats_top_queried` | Correct aggregation from multi-line `.wiki-query-log.jsonl` |
| `test_api_stats_unembedded` | Pages in filesystem but not in LanceDB appear in `unembedded_pages` |
| `test_api_lint_trigger` | POST `/api/lint` calls subprocess, returns output |
| `test_api_lint_conflict` | Second concurrent POST returns 409 |
| `test_lint_status_written` | `cmd_lint` writes `.wiki-lint-status.json` after execution |
| `test_api_stats_lint_status` | `/api/stats` reads and returns lint status from file |
