# AGENTS.md Patch

> **Deprecated (v2.3.0):** These instructions are now injected automatically into your workspace `AGENTS.md` by the setup script (`setup_openclaw.py`). You no longer need to apply this patch manually. This file is kept for reference and backward compatibility.

Add these lines at the end of the operative instructions section in your `AGENTS.md`:

---

## Wiki Knowledge System

At the start of every session:
1. Read `wiki-session.md` for the current wiki context
2. Before any wiki operation, re-read `skills/wiki-core.md` to verify the protocol

The wiki is your persistent brain. Use it actively:
- Every relevant piece of knowledge should be ingested into the wiki
- Every complex question should first be checked against the wiki
- Run LINT proactively every 2 weeks

Never write directly into the `wiki/` or `wiki-works/` directories.
Always use `wiki.py` for any write operation.

---

## Wiki Context Injection

When context injection is active, every prompt arrives preceded by a block like:

```
<wiki-context>
Pre-loaded wiki context (top 3 pages by semantic relevance):

### wiki/concepts/rag.md  [relevance: 0.91]
[page content...]

### wiki-works/research/synthesis/llm-memory.md  [relevance: 0.84]
[page content...]
</wiki-context>
```

Use this block directly as the starting context for your response — it is already the
most relevant knowledge from the wiki for this prompt. Do not run `wiki.py query` again
for the same query; that would be redundant. If the block is absent, proceed normally
with the checklist in `skills/wiki-core.md`.

---

## Wiki Dashboard (v2.2+)

When the server is running (`wiki.py serve`), a `[Stats]` tab is available at `http://localhost:7331`.

**What to check there:**
- Embedding coverage — pages present on disk but not in LanceDB appear under "Unembedded"
- Stale pages — pages not modified in the last 90 days (configurable)
- Top queried — most accessed pages since the last log rotation
- Lint status — last run result with error/warning counts

**REST endpoints** (same auth as the web interface):
```
GET  /api/stats   → full observability snapshot as JSON
POST /api/lint    → trigger wiki.py lint --full (returns 409 if already running)
```

**Auto-lint:** add to `wiki.config.json` to lint automatically every N hours:
```json
{ "frontend": { "lint_interval_hours": 24 } }
```
If omitted, lint only runs when triggered manually (button in the Stats tab or `wiki.py lint` CLI).

---

## PDF Inbox

When the user sends a PDF file in chat or provides a file path/URL:
```
wiki.py ingest-pdf --workspace <workspace> --file <path|url>
```
Never save PDF files manually or write directly to `wiki-works/`.

To process all PDFs added to the inbox since the last session:
```
wiki.py scan-inbox --workspace <workspace>
```

Files deposited in `wiki-works/<project>/raw/` with `source: pdf` in their frontmatter are raw extracted text — not finished wiki pages. Always structure them into `.tmp` pages before calling `wiki.py ingest`.

After `scan-inbox` completes, check `wiki-session.md` — the "last operation" section lists which raw files are ready for structuring.
