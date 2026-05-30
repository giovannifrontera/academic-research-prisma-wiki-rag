---
name: wiki-core
description: AI Agent wiki protocol v3 — three-layer brain, autonomous promotion, semantic dedup, self-reflection
---

# Wiki Core — AI Agent Protocol v3

> **This is a local skill file.**
> Access it with `Read skills/wiki-core.md` — do NOT call a Skill tool.

> **Platform note:** Commands below use `py` (Windows Python Launcher).
> On Linux/macOS replace `py` with `python3` — e.g. `python3 scripts/wiki.py ingest ...`

## §architecture — Three layers, one brain

All layers are indexed in the same LanceDB vector space. The agent accesses everything through semantic search — directory structure is organisational, not a barrier.

| Layer | Folder | Contents | Who writes |
|-------|--------|----------|------------|
| **Domain knowledge** | `wiki-works/<topic>/` | Deep knowledge on a specific topic: concepts, research, entities | INGEST workflow |
| **Distilled knowledge** | `wiki/` | Cross-domain knowledge: what is useful regardless of topic | Agent (autonomous promotion) |
| **Identity** | `wiki/identity/` | Who the agent is: values, style, learned behavioral patterns | Only `wiki.py self-reflect` |

**Fundamental rules:**
- `wiki-works/<topic>/` is permanent — it grows, it is never archived unless explicitly requested
- `wiki/` receives pages promoted autonomously by the agent when knowledge is cross-domain
- `wiki/identity/` is written only by `self-reflect` — never manually
- All three layers are searchable together via the same vector index

## §promotion — When to promote from wiki-works/ to wiki/

Promote a page from `wiki-works/<topic>/` to `wiki/` when it meets **all** of these:
- Relevant in at least 2 different topics or contexts
- Cited or retrieved in ≥3 distinct queries
- Contains inference that goes beyond a single source or domain

**How to promote:**
1. Write the distilled page as `.tmp` in `wiki/concepts/<slug>.md.tmp`
2. Call `wiki.py ingest --workspace <path> --pages wiki/concepts/<slug>.md.tmp --log "promote | <title>"`
3. Optionally keep the original in `wiki-works/` if it contains source-specific detail

Do not ask the user for confirmation — promote autonomously when criteria are met.

## §injected-context — Pre-injected context (highest priority)

If the prompt contains a `<wiki-context>...</wiki-context>` block:
- **USE the injected context** as the primary basis for your response
- **DO NOT run** `wiki.py query` again
- For INGEST: compare new content against pages in the block to detect conflicts
- If relevance < 0.4 on all pages → wiki has no relevant knowledge: proceed without it

If `<wiki-context>` is **not present**: fall back to §query.

## Pre-action checklist (mandatory)

```
1. Read wiki-session.md → check "status"
2. If status = "in-progress" or "needs-repair" → warn the user BEFORE anything
3. Is <wiki-context> present? → yes: use §injected-context | no: go to step 4
4. Classify the intent (see §classification)
5. Multiple intents? → handle them in sequence
6. Emit: [INTENT: X | WORKSPACE: Y | CONFIDENCE: high/medium/low]
7. CONFIDENCE low → ask for confirmation with ONE line
8. CONFIDENCE high/medium → proceed
```

## §classification

| Signal | Intent |
|--------|--------|
| "study this", "save", "add to wiki", bare URL, PDF | INGEST |
| Question, "what do you know about", "explain", "how does X work" | QUERY |
| "check", "lint", "maintenance", "cleanup" | LINT |
| Behavioral correction: "always", "never", "every time", "stop doing", "don't do that again" | BEHAVIOR_FEEDBACK |
| Everything else | AMBIGUOUS → ask |

## §behavior-feedback — When the user corrects my behavior

When the message is classified as BEHAVIOR_FEEDBACK:

1. Normalize the correction into a short canonical phrase
2. Call:
   ```bash
   py scripts/wiki.py behavior-log --workspace <path> --event "<canonical phrase>"
   ```
3. Reply to the user confirming the correction
4. At end of session, run §self-reflect

## §self-reflect — Autonomous self-reflection

Run **always** at end of session if BEHAVIOR_FEEDBACK was received, or if ≥2 corrections of any kind were received:

```bash
py scripts/wiki.py self-reflect --workspace <path>
```

Reads `.wiki-behavior-log.jsonl`, detects recurring patterns (≥3 occurrences), and autonomously updates `wiki/identity/`. Run without asking the user. Log changes in `wiki/log.md`.

## §ingest — INGEST workflow (knowledge into wiki-works/)

**Phase A — Research:**
1. `web_search` for 5-10 candidate sources
2. Apply quality filter: discard sources below score 6
3. `web_fetch` → save in `wiki-works/<project>/raw/YYYY-MM-DD-slug.md`
4. Read sources, identify key points and conflicts

**Phase B — Writing:**
1. Write pages as `.tmp` files in `wiki-works/<project>/`:
   - Entities → `entities/<slug>.md.tmp`
   - Concepts → `concepts/<slug>.md.tmp`
   - Synthesis → `synthesis/<slug>.md.tmp`
2. Call:
   ```bash
   py scripts/wiki.py ingest \
     --workspace <path> \
     --pages <p1.tmp,p2.tmp,...> \
     --log "ingest | <title>"
   ```
3. If `status: error` → warn user. If `mini_lint: failed` → warn user.

**Phase C — Report:** sources used, pages created, conflicts resolved.
After ingestion, evaluate §promotion criteria for each new page.

## §lint — LINT workflow

```bash
py scripts/wiki.py lint --workspace <path> --full
```

JSON output includes `semantic_duplicates`. Handle them as follows:

| `action` | What to do |
|----------|------------|
| `auto_merge` (similarity ≥ 0.90) | Read both pages, write merged version as `.tmp`, call `wiki.py ingest`, delete originals |
| `warn` (0.75 ≤ similarity < 0.90) | Show user the first 2 lines of each page and ask whether to merge |

For broken links and duplicate filenames: present options to the user.

## §query — QUERY workflow

**If `<wiki-context>` is present:** skip steps 1-3.

**Manual fallback:**
1. `py scripts/wiki.py index --workspace <path>`
2. `py scripts/wiki.py query --workspace <path> --q "<question>" --k 5`
3. Read the pages in the results

**Always:**
4. Synthesise with references `[page](path)`
5. If the response synthesises ≥2 wiki sources, exceeds 300 tokens, adds non-literal inference → save it as a page via INGEST, then evaluate §promotion

## §pdf-inbox — PDF ingestion

Text extraction is done via **pdfplumber** (bundled in `wiki_pdf_watcher.py`).
Do NOT extract PDF text manually — always use the commands below.

1. `py scripts/wiki.py ingest-pdf --workspace <path> --file <path|url>`
2. For each path in `deposited`, **read** the raw file (extracted text)
3. **Write** structured `.tmp` pages in `wiki-works/<project>/` (see §ingest Phase B)
4. Call `wiki.py ingest --workspace <path> --pages <file.tmp,...>`

> **WARNING — process-raw ≠ ingest:**
> `wiki.py process-raw` only re-indexes files already in `raw/` — it does NOT
> create structured wiki pages. It is for bulk re-indexing only.
> Always follow the full §ingest workflow for new knowledge.

`scan-inbox` checks the PDF inbox directory defined in `wiki.config.json` and enqueues any new PDFs for the §pdf-inbox workflow.

## §maintenance — Rebuild and serve

**Rebuild** (re-embeds all wiki pages from scratch — use after bulk import or index corruption):
```bash
py scripts/wiki.py rebuild --workspace <path>
```

**Serve** (web dashboard at `http://localhost:7331` — graph view + stats):
```bash
py scripts/wiki.py serve --workspace <path> [--no-auth]
```

Do not run `rebuild` during normal operation — it drops and recreates the entire vector index.

## §workspace — Project selection

1. Read `wiki.config.json` → `projects` with keywords
2. Count matches between message keywords and project keywords
3. Project with most matches → selected
4. Tie → ask the user

## §session

- Session start: read `wiki-session.md`
- Never modify `wiki-session.md` directly: use `wiki.py session-update`
- If `status: in-progress`: warn before any operation
- Session end with BEHAVIOR_FEEDBACK received: run §self-reflect
