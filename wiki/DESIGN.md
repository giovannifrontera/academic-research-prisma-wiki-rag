# 🧠 AI Longterm Wiki Memory — Design Document v2

> Based on Andrej Karpathy's pattern (llm-wiki), adapted for Linux CLI, autonomous,
> with semantic topology via bge-m3 vector embeddings and LanceDB.
> 2026-05-19.

---

## 📐 General Architecture

```
workspace/
├── wiki/                           ← Level 1: Permanent Knowledge
│   ├── .schema.md                  ← Conventions, rules, standards for this wiki
│   ├── log.md                      ← Append-only history
│   ├── entities/
│   ├── concepts/
│   └── synthesis/
│
├── wiki-works/                     ← Level 2: Active Research
│   ├── log.md                      ← Global research history
│   ├── trading/
│   │   ├── .schema.md
│   │   ├── log.md
│   │   ├── raw/                    ← Raw sources (excluded from vectors — see §raw)
│   │   ├── entities/
│   │   ├── concepts/
│   │   └── synthesis/
│   └── .../
│
└── memory/
    └── lancedb/                    ← Excluded from git (rebuildable — see §git)
```

**Note on index.md**: It does not exist as a manually maintained file.
`index.md` is generated on-demand from a filesystem scan (see §index-generation).
This eliminates the entire class of "index out of sync" bugs.

---

## 🗂️ Three Knowledge Layers

| Layer | Description | Nature |
|-------|-------------|--------|
| **Vector Memory** (LanceDB) | Automatic semantic retrieval — all layers indexed together | Implicit, rebuildable |
| **wiki-works/\<topic\>/** | Deep domain knowledge: concepts, research, entities per topic | Explicit, permanent |
| **wiki/** | Distilled cross-domain knowledge: promoted autonomously when relevant across topics | Explicit, permanent |
| **wiki/identity/** | Agent identity: values, style, learned behavioral patterns (self-reflect only) | Explicit, permanent |

---

## 🚀 Bootstrap and Initialization

First session in a new wiki:

```
1. Create directory: wiki/ (or wiki-works/<project>/)
2. Create .schema.md with rules for this specific wiki
3. Create empty log.md with header:
   # Log — <wiki name>
   <!-- format: ## [YYYY-MM-DD] type | description -->
4. LanceDB: create wiki_pages table with schema §vectors if it doesn't exist
5. Run rebuild-index to generate initial index.md (will be empty/minimal)
6. Log entry: ## [DATE] init | Bootstrap wiki <name>
```

For the main `wiki/`, optional seed: create `entities/Agent-nyx.md` and
`entities/gio.md` as foundational pages before any ingest.

---

## 🔄 The 3 Workflows

### 1. INGEST — Acquisition with Atomicity

The user specifies the **what**. The Agent handles the **how**, atomically and verifiably.

#### Phase A — Research and Filtering (read-only, no writes)

1. `web_search` to find 5–10 candidate sources
2. **Quality filter** (see §quality-filter): discard sources below threshold
3. `web_fetch` on promoted sources → save in `raw/` with name `YYYY-MM-DD-slug.md`
4. Read sources, extract key points, identify contradictions with existing wiki

#### Phase B — Atomic Write

Staging: all writes happen on `.tmp` files before being committed.

```
ATOMIC STAGING:
a) Write new/updated pages to <path>.tmp
b) Write new embeddings to LanceDB staging_wiki_pages table
c) CHECKPOINT: verify integrity (every .tmp readable, every embedding present)
d) If CHECKPOINT ok:
   - Rename all .tmp → final (atomic per-file operation)
   - Promote staging_wiki_pages → wiki_pages (upsert by path)
   - Regenerate index.md via rebuild-index
   - Append log.md
   - Run MINI-LINT (see §mini-lint)
e) If CHECKPOINT fails:
   - Delete all .tmp files
   - Delete staging_wiki_pages
   - Log entry: ## [DATE] ingest-failed | <reason>
   - Notify user with specific error
```

#### Phase C — Report

- Oral summary in chat: source, key points, conflicts found and resolved
- Validation questions if needed

---

### 2. QUERY — Response with Compounding

1. Call `rebuild-index` (if index.md is absent or stale vs filesystem)
2. Read index.md → identify relevant pages by category
3. Vector query on LanceDB for non-obvious semantic connections
4. Read selected pages → synthesize response with references `[page](path)`
5. **Evaluate synthesis threshold** (see §synthesis-threshold): if the synthesis exceeds the threshold → save it as a new page via the INGEST workflow (compounding)
6. No direct writes outside the INGEST workflow — maintains atomicity

---

### 3. LINT — Maintenance (full)

**When**: on user request, or proactively every 2 weeks.
**Automatic mini-lint**: after every INGEST (lightweight subset — see §mini-lint).

```
FULL LINT CHECKLIST:
□ DESYNC: rebuild-index → compare with index.md on disk → diff
□ STALE VECTORS: for each non-raw .md file → SHA256(content) ≠ content_hash in LanceDB?
□ UNEMBEDDED PAGES: .md files in wiki without entry in wiki_pages
□ ORPHAN ENTRIES: entries in wiki_pages with path that doesn't exist on filesystem
□ BROKEN LINKS: grep [[wikilink]] → verify target file exists
□ DUPLICATES: for each pair of pages with cosine_similarity > 0.95 → report and propose merge
□ SEMANTIC ORPHANS: pages with no neighbor with similarity > 0.50 → report
□ STALE CHUNKS: for each chunked page → chunk hash ≠ current hash → rechunk
□ STALENESS: pages with last_modified > 90 days → flag for review
□ GAP: concepts cited in ≥3 pages without a dedicated page → report
□ LOG INTEGRITY: every log entry has a valid timestamp and type
```

For each problem found, LINT does not just report — it **resolves**:

| Problem | Automatic Action |
|---------|-----------------|
| Stale vector | Re-embed immediately |
| Unembedded page | Embed |
| Orphan LanceDB entry | Delete entry |
| Broken link | Report in log, propose fix to user |
| Duplicates (similarity > 0.95) | Propose merge with draft of unified page |
| Semantic orphans | Add "See also" section with 3 nearest neighbors |
| Stale chunk | Rechunk and re-embed |

---

## 🔬 §mini-lint — Automatic Post-Ingest Mini-Lint

Executed automatically at the end of every successful INGEST. Lightweight, < 30s.

```
MINI-LINT (fast subset):
□ Do the just-written pages exist on the filesystem?
□ Do the just-written pages have entries in wiki_pages with correct hash?
□ Has index.md been regenerated (mtime > mtime of written pages)?
□ Is the log entry present?
□ No .tmp files left on disk?
```

If mini-lint fails → log entry `## [DATE] mini-lint-failed | <detail>` and notify user.
No rollback (the ingest is already committed) but marks the state as "needs repair".

---

## 🏷️ §synthesis-threshold — Criteria for Creating a Synthesis Page

A response to a QUERY becomes a wiki page if it satisfies **all** mandatory criteria
and at least one optional criterion:

**Mandatory criteria:**
- Synthesizes ≥ 2 distinct sources (different pages or raw files)
- Length ≥ 300 tokens (non-trivial)
- Adds an inference not literally present in any single source

**Optional criteria (≥ 1):**
- Answers a question the user explicitly asked
- Resolves a contradiction between existing pages
- Connects concepts from different domains (cross-wiki)
- Likely to be reused in future queries (Agent's judgment)

**Counter-indicators (automatically exclude):**
- It is a summary of a single source (goes in raw/, not synthesis/)
- Duplicates an existing page with similarity > 0.85
- Contains unverified claims without an explicit source

---

## 📦 §chunking — Chunking Strategy for Long Pages

Threshold: pages > **1500 tokens** are chunked before embedding.

**Chunking strategy:**
- Chunk size: 512 tokens with 64-token overlap
- Boundary-aware: chunks do not cut in the middle of a markdown section
  (respects `##` and `###` headings)
- Each chunk inherits the parent page's metadata

**LanceDB schema for chunked pages:**

```
wiki_pages:
├── path: string          ← file path (e.g. "wiki/concepts/strategies.md")
├── chunk_id: int         ← 0 for non-chunked pages, 1..N for chunks
├── chunk_text: string    ← chunk text (not the full page)
├── content_hash: string  ← SHA256(chunk_text) — hash of TEXT, not path
├── page_hash: string     ← SHA256(full page) — to detect if rechunking is needed
├── vector: float[1024]
└── last_embedded: float
```

**Retrieval**: when a query matches a chunk, retrieve the full page for context.
In results, always show the page path, not the chunk path.

**Re-chunking**: if `page_hash` ≠ SHA256(current file) → rechunk everything and re-embed all chunks.

---

## 🔐 §hash-semantics — Correct Hash Semantics

**Fundamental rule**: `content_hash = SHA256(chunk_or_page_text)`.
The path is NOT included in the hash. Path and hash are separate, independent fields.

This implies:

| Event | Hash changes? | Path changes? | Action |
|-------|--------------|--------------|--------|
| Edit the text | Yes | No | Re-embed, update existing entry |
| Rename the file | No | Yes | Find entry with old path → update path, no re-embedding |
| Move between folders | No | Yes | Same as rename |
| Git checkout same content | No | No | No action (hash matches) |
| Delete the file | — | — | LINT finds orphan entry → deletes it |

**Rename detection**: LINT compares `set(path in LanceDB)` with `set(files on filesystem)`.
Path only in LanceDB → orphan. Path only on filesystem → new file.
If an orphan and a new file share the same `content_hash` → it's a rename → update path.
If hashes differ → orphan deleted, new file embedded separately.

---

## 📂 §raw — Handling Raw Sources

The `raw/` directories contain sources downloaded via `web_fetch`. They are excluded from vectors.

**Rationale**: raw/ is unprocessed input material. Including it in vectors pollutes semantic
retrieval with duplicates and noise. The value of raw/ is in direct access during ingest,
not in semantic retrieval.

**Rule**: No file in `raw/` has an entry in `wiki_pages`.
LINT verifies this invariant: if it finds entries with a path containing `/raw/` → it deletes them.

**Raw naming convention**: `raw/YYYY-MM-DD-slug-source.md`

**Access**: during ingest the Agent reads raw/ directly with `read`.
During QUERY, raw/ is not indexed or searched semantically.

---

## 🔁 §index-generation — Filesystem-Generated Index

`index.md` is a **derived** file, not a source of truth. It is generated by:

```
rebuild-index(wiki_dir):
  pages = glob(wiki_dir + "/**/*.md") - exclude .schema.md, log.md, raw/**
  group by subdirectory (entities/, concepts/, synthesis/)
  for each page:
    - read YAML frontmatter if present (title, description)
    - fallback: use filename as title, first non-heading line as description
  write index.md with structure:
    # Index — <wiki name>
    _Generated: YYYY-MM-DD HH:MM — <N> pages_
    ## Entities
    - [[slug]] — description
    ## Concepts
    - [[slug]] — description
    ## Synthesis
    - [[slug]] — description
  if index.md exceeds TOKEN_BUDGET → see §token-budget
```

**When to call rebuild-index**:
- End of every successful INGEST (already in the atomic workflow)
- Start of every QUERY (mtime check: if index.md is older than any .md → regenerate)
- During full LINT

**Never**: do not update index.md manually line by line. Always do a full rebuild.

---

## 💰 §token-budget — Token Budget for index.md

Maximum limit: **4000 tokens** for index.md (compatible with DeepSeek V4 context window).

If the wiki exceeds this threshold during rebuild-index:

```
Reduction strategy (in order):
1. Remove the "description" column → links only: - [[slug]]
   (saves ~50%)
2. If still > 4000 tokens: generate a separate per-category index
   index.md → only category list with page counts
   index-entities.md, index-concepts.md, index-synthesis.md → partial indexes
3. If a single category > 4000 tokens (huge wiki):
   index-concepts-A-M.md, index-concepts-N-Z.md (alphabetical split)
```

Warning threshold in `.schema.md`: `index_token_budget: 4000`.
Configurable per wiki (small wiki-works can use a larger budget).

---

## 🎯 §quality-filter — Quality Criteria for Sources

Before `web_fetch`, each candidate source is evaluated. Promotion only if it passes the threshold.

**Automatic exclusion criteria (any one → discard):**
- Domain on blacklist: SEO farms, low-quality aggregators, wiki spam
- Paywall with no abstract (web_fetch returns < 200 tokens of content)
- Predominantly advertising content (> 30% commercial markup)
- No detectable date and clearly outdated content (e.g. prices, statistics without year)

**Quality score (0–10, minimum threshold: 6):**

| Criterion | Points |
|-----------|--------|
| Identifiable author with verifiable credentials | +2 |
| Primary source (paper, official documentation, raw data) | +3 |
| Authoritative secondary source (peer-reviewed journal, institution) | +2 |
| Publication date ≤ 2 years (for time-sensitive topics) | +1 |
| Citations/references present | +1 |
| Concordance with sources already in the wiki | +1 |
| Discordance with sources in the wiki (informational value) | +1 |

**Maximum score**: 11 (capped at 10). Threshold 6 for promotion.
For historical or foundational topics (mathematics, physics, history), the date criterion is ignored.

Document the filtering process in the log:
```
## [DATE] ingest | Title
Candidate sources: 7 | Promoted: 3 | Discarded: 4
Discarded: [spam-domain.com (SEO farm), other.com (paywall), ...]
```

---

## ⚔️ §conflict-resolution — Conflict Resolution (not just reporting)

When ingest finds a claim P in a new source that contradicts
claim ¬P in an existing page:

**Conflict levels and resolution:**

**Level 1 — Dated conflict** (one source is more recent):
- Action: update the wiki page with the more recent information
- Keep note: `> ⚠️ Updated: [old claim] → [new]. Source: [link]. Date: YYYY-MM-DD`
- No user intervention required

**Level 2 — Interpretive conflict** (both sources are valid but disagree):
- Action: create a `## Conflicting Perspectives` section in the page
- Present both positions with source and quality score
- Add frontmatter tag `status: contested` to the page
- No user intervention required

**Level 3 — Fundamental conflict** (irreconcilable, high impact):
- Action: create dedicated synthesis page `conflicts/conflict-title.md`
- Summarize both positions, analyze implications
- Notify user in the final report with a specific question: "Which version do you consider canonical?"
- Block the merge of the new claim into reference pages until answered

**Detection**: during ingest, after reading the new source and before writing,
Agent searches the 5 most similar pages by vector + grep for key entities/concepts.
For each page found, compare key claims. Classify the conflict level.

---

## 🧭 Three Navigation Systems

### A. Generated index (index.md)
Category-based navigation. Generated from filesystem (§index-generation).

### B. Explicit links (markdown [[wikilink]])
Backlinks findable with `grep -rl "page-name" wiki/`.

### C. Semantic topology (vectors)
bge-m3 embeddings (1024-dim), chunk-aware, for every non-raw page.

- **Neighborhood**: query `search(embedding, k=5, filter="chunk_id=0")` on LanceDB
- **Clusters**: recalculated during full LINT (k-means on all chunk_id=0 vectors)
- **Bridges**: pages with neighbors in different clusters
- **Semantic orphans**: pages with no neighbor with similarity > 0.50

```
Page: mean-reversion-strategies.md
├── 0.92 → backtesting-fundamentals.md
├── 0.87 → technical-indicators.md
├── 0.81 → risk-management.md
└── 0.74 → trading-psychology.md
```

No PNG, no graph view. Only on-demand textual distances.

---

## 🛠️ Technology Stack

| Component | Tool | Notes |
|-----------|------|-------|
| File system | Markdown directories | Already in place |
| Index | Generated from filesystem | Never maintained manually |
| Log | `log.md` append-only | Parseable format |
| Explicit links | `[[wikilink]]` + `grep` | Backlinks with `grep -rl` |
| Embedding | bge-m3 (already installed) | 1024-dim, chunk-aware |
| Vector DB | LanceDB (already installed) | Table `wiki_pages` |
| Text search | `grep` | Fallback for links and text |
| Web search | `web_search` | Autonomous |
| Page fetch | `web_fetch` | Clean markdown → raw/ |
| Versioning | `git` | Excludes lancedb/ (§git) |

---

## 📋 Special Files

### .schema.md
Defines for each wiki:
- Active folder structure
- Required YAML frontmatter format
- Lint thresholds (e.g. `staleness_days: 90`, `similarity_merge_threshold: 0.95`)
- `index_token_budget: 4000`
- Link style and naming conventions

### log.md
- Append-only, never edited retroactively
- Format: `## [YYYY-MM-DD] type | description`
- Types: `init`, `ingest`, `ingest-failed`, `query`, `lint`, `mini-lint-failed`, `sync`, `archive`, `conflict-resolved`
- Quick query: `grep "^\#\# \[" log.md | tail -10`

---

## 🔁 Project Lifecycle (Level 2)

```
  ACTIVE → DORMANT → ARCHIVED
     ↓
  MERGED INTO wiki/ (Level 1)
```

- **Active**: receives ingests and queries
- **Dormant**: untouched, available read-only
- **Archived**: `wiki-works/.archive/project-name/` — LanceDB entries deleted
- **Archived**: `wiki-works/.archive/project-name/` — LanceDB entries deleted

**Note (v3):** Promotion from wiki-works/ to wiki/ is autonomous — the agent promotes when knowledge is cross-domain (relevant in ≥2 topics, retrieved in ≥3 queries). wiki/identity/ is updated only via `wiki.py self-reflect`.

---

## 🗄️ §git — Git / LanceDB Strategy

**LanceDB is excluded from git.**

```
# .gitignore (add):
memory/lancedb/
```

**Rationale**: LanceDB is entirely rebuildable from the markdown filesystem.
It contains no information that cannot be derived from the pages. Committing it
would cause enormous commits, irresolvable binary conflicts, and false security.

**Rebuild procedure**:
```
rebuild-lancedb(wiki_dir):
  delete wiki_pages table
  for each .md not in raw/ and not in .archive/:
    chunk if > 1500 tokens (§chunking)
    for each chunk: embed with bge-m3, insert into wiki_pages
  log entry: ## [DATE] sync | LanceDB rebuilt from filesystem
```

**When to rebuild**: after `git clone`, `git reset --hard`, or if LanceDB is corrupted.
Estimated time: ~2 min per 1000 pages on standard hardware.

**Git tracks**: all `.md`, `.schema.md`, `log.md` files. Does not track: `lancedb/`, `*.tmp`.

---

## 🔑 §lancedb-schema — Full LanceDB Schema

```
Table: wiki_pages
├── path         string       ← relative path from workspace root
├── chunk_id     int          ← 0 = full page (< 1500 tok); 1..N = chunk
├── chunk_text   string       ← embedded text (chunk or full page)
├── content_hash string       ← SHA256(chunk_text) — text only, never path
├── page_hash    string       ← SHA256(full page) — to detect rechunk need
├── vector       float[1024]  ← bge-m3 embedding of chunk_text
└── last_embedded float       ← unix timestamp

Table: staging_wiki_pages  ← identical schema, used for atomic ingest
                              deleted/emptied after each ingest (ok or failed)

Index: (path, chunk_id) UNIQUE
Index: vector ANN (HNSW)
```

---

## 🚦 Implementation Rules

1. **Do not touch the existing system** (LanceDB memories, daily notes, MEMORY.md)
2. The wiki **adds to** memory, it does not replace it
3. `index.md` is always generated, never written manually
4. Every write goes through atomic staging — no partial pages on disk
5. Mini-lint after every ingest — always
6. LanceDB outside git — always rebuildable
7. `raw/` not in vectors — invariant verified by lint
8. Conflicts resolved (not just reported) per §conflict-resolution
9. No new dependencies to install

---

*v2 — 2026-05-19 — Reviewed by Claude Code*
