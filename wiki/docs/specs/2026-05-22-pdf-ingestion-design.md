# PDF Ingestion Design — ai-longterm-wiki-memory

**Date:** 2026-05-22  
**Status:** Approved  
**Scope:** Add multi-source PDF ingestion to the wiki system via a watched inbox folder

---

## Problem

The system currently supports only `.md` files. `embed_file` opens files as UTF-8 text (crashes on binary PDFs), and all workflows glob only `*.md`. Users cannot ingest PDFs from Telegram, the CLI, or a watched folder.

---

## Approach: Inbox-centric hub

A `pdf-inbox/` folder inside the workspace acts as the single convergence point for all PDF sources. A new script `wiki_pdf_watcher.py` detects new or changed PDFs via SHA-256 hash comparison, extracts their text with pdfplumber, and deposits the result as `.md` files in `wiki-works/<project>/raw/`. The agent then structures the raw text into wiki pages using the existing `wiki.py ingest` pipeline — unchanged.

**Key invariant:** `wiki.py ingest` is not modified. The PDF layer inserts itself upstream and hands off `.md` files, which is the format the agent already knows how to handle.

---

## Architecture

### Data flow

```
[Telegram upload / CLI --file / manual drop]
          ↓
    workspace/pdf-inbox/<file.pdf>
          ↓
wiki.py scan-inbox  ←  cron or explicit trigger
          ↓
wiki_pdf_watcher.scan_inbox()
  • compute SHA-256 for each PDF
  • compare with pdf-inbox/.registry.json
  • for each new/changed PDF:
      extract text (pdfplumber)
      → wiki-works/<project>/raw/<name>.md  (with frontmatter)
      → update .registry.json atomically
          ↓
session update: "N PDFs ready in raw/"
          ↓
[Agent reads raw/ → creates .tmp pages → wiki.py ingest]
```

### Folder structure

```
workspace/
├── pdf-inbox/                        ← new: all sources converge here
│   ├── paper1.pdf
│   └── .registry.json                ← hash + status per PDF
├── wiki/
│   ├── entities/
│   ├── concepts/
│   └── synthesis/
├── wiki-works/
│   └── <project>/
│       └── raw/
│           └── paper1.md             ← extracted text, ready for agent
├── scripts/
├── skills/
├── wiki.config.json
└── wiki-session.md
```

---

## Components

### New: `scripts/wiki_pdf_watcher.py`

| Function | Responsibility |
|----------|---------------|
| `compute_hash(path)` | SHA-256 of the PDF file |
| `load_registry(workspace)` | Read `pdf-inbox/.registry.json` |
| `save_registry(workspace, data)` | Write registry atomically via `tempfile` + `os.replace` |
| `extract_text(pdf_path)` | Extract text with pdfplumber; returns `""` on scanned PDFs |
| `deposit_raw(text, pdf_name, workspace, cfg)` | Save to `wiki-works/<project>/raw/<name>.md` with frontmatter |
| `scan_inbox(workspace, cfg)` | Main: detect new/changed, extract, deposit, update registry |

Frontmatter added to each deposited raw file:
```markdown
---
source: pdf
original: paper1.pdf
extracted_at: 2026-05-22T10:30:00
---
```

### Changes to existing files

**`scripts/wiki.py`** — two new subcommands:

```
scan-inbox   --workspace <path>
ingest-pdf   --workspace <path> --file <local-path|url>
```

`ingest-pdf` is a thin wrapper: copy/download PDF to `pdf-inbox/`, then call `scan_inbox`. No duplicated logic.

**`wiki.config.json`** — new optional field:
```json
{
  "pdf_inbox": {
    "project_default": "research"
  }
}
```
Used when the target project cannot be determined from the filename.

**`requirements.txt`** — add `pdfplumber>=0.11.0`

**`skills/wiki-core.md`** — new `§pdf-inbox` section: instructs the agent on recognizing raw PDF files and the structuring workflow.

**`AGENTS_PATCH.md` / `AGENTS_PATCH.it.md`** — new section with three agent rules:
1. When user sends a PDF → call `wiki.py ingest-pdf --file <path>`, never write directly
2. Files in `raw/` with `source: pdf` frontmatter are extracted PDFs, not finished wiki pages — the agent must structure them into `.tmp` pages
3. After `scan-inbox` → check `wiki-session.md` for how many raw files are ready

**No changes to:** `wiki_workflows.py`, `wiki_embed.py`, `wiki_lancedb.py`, `wiki_index.py`

---

## Change detection and registry

`.registry.json` structure:

```json
{
  "paper1.pdf": {
    "hash": "sha256:a3f1...",
    "deposited_to": "wiki-works/research/raw/paper1.md",
    "processed_at": "2026-05-22T10:30:00",
    "status": "deposited"
  },
  "paper2.pdf": {
    "hash": "sha256:b9c2...",
    "deposited_to": null,
    "processed_at": "2026-05-22T10:31:00",
    "status": "failed",
    "error": "no text extractable (scanned PDF)"
  }
}
```

**Decision logic in `scan_inbox`:**

| Condition | Action |
|-----------|--------|
| File not in registry | New — process |
| Hash differs from registry | Modified — reprocess (overwrite raw) |
| Hash matches + status `deposited` | Already processed — skip |
| Hash matches + status `failed` | Known failure — skip (avoids loop on corrupt PDFs) |
| Status is `pending` (crash recovery) | Reprocess |

Status `pending` is written before extraction begins. A mid-operation crash leaves status as `pending`, which triggers reprocessing on the next scan — no silent data loss.

**Output JSON** (consistent with all other commands):
```json
{"status": "ok", "op": "scan-inbox", "processed": 2, "skipped": 1, "failed": 0, "deposited": ["paper1.md", "paper2.md"]}
```

---

## Sources

### CLI

```bash
# Local file
wiki.py ingest-pdf --workspace <path> --file /path/to/paper.pdf

# Remote URL (downloads PDF to pdf-inbox/ first)
wiki.py ingest-pdf --workspace <path> --file https://arxiv.org/pdf/2401.00001

# Scan entire inbox (cron or explicit trigger)
wiki.py scan-inbox --workspace <path>
```

### Telegram / OpenClaw

No new plugin required. OpenClaw already passes attachment paths to the agent via bash access. The agent rule (added in `AGENTS_PATCH.md`):

> When user sends a PDF in chat → call `wiki.py ingest-pdf --workspace <path> --file <attachment_path>`

### Cron

```bash
py scripts/wiki.py scan-inbox --workspace /path/to/workspace
```

`scan-inbox` is idempotent: no new PDFs → `{"processed": 0, "skipped": N}`, no side effects. Safe to run frequently.

---

## Error handling

| Case | Behavior |
|------|----------|
| Scanned PDF (no selectable text) | status `failed`, error `no_text_extractable` — skipped on future scans |
| Corrupt / unparseable PDF | status `failed`, error `pdf_parse_error: <msg>` |
| Unreachable URL | Immediate error, PDF never enters inbox |
| Crash during extraction | status remains `pending` → reprocessed on next scan |
| `pdf-inbox/` missing | Created automatically by `scan-inbox` via `os.makedirs` |

---

## Testing

New file: `tests/test_pdf_watcher.py`

| Test | What it verifies |
|------|-----------------|
| `test_scan_new_pdf` | New PDF is extracted and deposited in raw/ |
| `test_scan_unchanged_skipped` | Already-processed PDF (same hash) is skipped |
| `test_scan_modified_reprocessed` | Modified PDF (different hash) is reprocessed and raw/ overwritten |
| `test_scanned_pdf_no_text` | PDF with no selectable text → status failed, no exception raised |
| `test_registry_atomic_write` | Simulated crash does not corrupt .registry.json |
| `test_ingest_pdf_from_url` | Mock HTTP download, verify deposit in pdf-inbox/ and raw/ |

PDF fixtures are minimal files generated programmatically — no binary blobs committed to the repo.
