# Isolated Study Workspace Design

**Date:** 2026-09-17  
**Status:** Proposed  
**Scope:** Automatic study bootstrap and hard isolation of PRISMA data, Hybrid RAG, and wiki memory

## Objective

When a researcher starts a new study, the plugin asks only for its name and creates a complete, self-contained study directory inside the current Claude Code workspace. Every file, PDF, state artifact, vector database, wiki page, synthesis, protocol and export for that study must remain inside this directory. No study may read or write another study's RAG or wiki unless a future explicit import feature is designed separately.

## User Experience

Bootstrap can start in either of two ways:

1. Explicit command/skill intent: `/pipeline-ricerca nuova`.
2. Natural-language intent such as “iniziamo una nuova ricerca”.

Both paths use the same confirmation flow:

1. Ask for the study name only.
2. Normalize it to a filesystem-safe slug and show both name and slug.
3. Show the absolute target path `<CURRENT_WORKSPACE>/<slug>`.
4. Ask for confirmation before writing.
5. Create the complete structure and initial state atomically enough to avoid a partially valid project.
6. Change the operational project root to the new study directory and begin PRISMA Phase 0.

The parent directory is always the current workspace. The workflow does not ask the user to select another parent.

## Directory Layout

```text
<CURRENT_WORKSPACE>/
└── <study-slug>/                         # canonical study root
    ├── .project-state.json              # master state and isolation contract
    ├── README.md                        # generated study overview and commands
    ├── project-log.md                   # append-only orchestration log
    ├── prisma/
    │   ├── prisma_state.json
    │   ├── prisma_log.md
    │   ├── screening_log.md
    │   ├── screening_prisma.json
    │   ├── eligibility_prisma.json
    │   └── prisma_synthesis.md
    ├── sources/
    │   ├── pdf-inbox/
    │   └── pdf-inclusi/
    ├── database/
    │   ├── qdrant-rag/               # PRISMA/Hybrid RAG vector database
    │   └── qdrant-wiki/              # wiki vector database
    ├── wiki-memory/                      # private wiki workspace for this study
    │   ├── wiki.config.json
    │   ├── wiki-session.md
    │   ├── wiki/
    │   │   ├── concepts/
    │   │   ├── synthesis/
    │   │   └── identity/
    │   ├── wiki-works/
    │   │   └── <study-slug>/
    │   │       ├── raw/
    │   │       ├── entities/
    │   │       ├── concepts/
    │   │       └── synthesis/
    │   └── pdf-inbox/
    ├── synthesis/
    ├── design/
    ├── preprint/
    └── export/
```

Each study has exactly two embedded Qdrant databases, kept physically separate so RAG and wiki operations never contend for the same storage lock:

| Database | Collection | Allowed content | Vector model |
|---|---|---|---|
| `database/qdrant-rag/` | `prisma_papers` | Current eligibility export only | Hybrid RAG selected model |
| `database/qdrant-rag/` | `included_pdf_chunks` | Approved included PDFs only | Hybrid RAG selected model |
| `database/qdrant-wiki/` | `wiki_pages` | Structured wiki pages from this study | Wiki BGE-M3 model |
| `database/qdrant-wiki/` | `staging_wiki_pages` | Temporary wiki ingest staging | Wiki BGE-M3 model |

Splitting storage this way (instead of one shared database with four collections) means the Hybrid RAG process and the wiki server/CLI can each hold their own embedded Qdrant client open independently — no `database_in_use` coordination is needed between the two subsystems, only within each one. Collection and database names are fixed; no collection is shared, globally discovered, or selected from another project.

Embedded Qdrant still permits only one active storage owner per individual database directory. Two Hybrid RAG commands (or two wiki commands) must not run concurrently against the same study; that constraint is local to each database and does not cross-block the other subsystem.

### Wiki as the mandatory evidence layer for RAG

The wiki export step (`wiki-ingest` in `pipeline-ricerca`) is **mandatory**, not optional, for every study. Its purpose is not decorative: every paper indexed into `prisma_papers`/`included_pdf_chunks` must also exist as a human-readable Markdown entity page under `wiki-memory/wiki-works/<study-slug>/entities/`, and the review synthesis must exist as a wiki synthesis page. This gives a human reviewer a citable, readable artifact behind every RAG hit — RAG chunks are for retrieval, wiki pages are for verification. `hybrid-rag` `index-prisma`/`index-pdf` refuse to run if the corresponding wiki export for that eligibility snapshot has not been done, unless the researcher explicitly overrides with `--skip-wiki-export` (logged in `project-log.md`).

### Cross-encoder reranking on Hybrid RAG queries

Today only the wiki (`wiki_qdrant.py` / `wiki_rerank.py`) reranks results with `BAAI/bge-reranker-v2-m3`; `hybrid_rag_template.py`'s `query` command returns raw RRF-fused hits with no cross-encoder pass. This is closed: `hybrid-rag query` gains the same cross-encoder rerank step, reusing `BAAI/bge-reranker-v2-m3` (same model, same dependency already required by the wiki), applied to the fused dense+sparse candidate set before returning results. This is on by default for study-mode projects (`--project` given) and configurable via `rag_db/config.json`'s `rerank: true|false`, mirroring the wiki's `wiki.config.json` convention.

## Canonical State Contract

`.project-state.json` is the only authority for resolving study paths. Version 1 of the contract is:

```json
{
  "schema_version": 1,
  "study_id": "uuid-v4",
  "study_name": "Human-readable study name",
  "study_slug": "human-readable-study-name",
  "project_root": "/absolute/current-workspace/human-readable-study-name",
  "created_at": "ISO-8601",
  "isolation": {
    "mode": "sealed",
    "allow_external_reads": false,
    "allow_external_writes": false
  },
  "paths": {
    "prisma": "prisma",
    "sources": "sources",
    "qdrant_rag": "database/qdrant-rag",
    "qdrant_wiki": "database/qdrant-wiki",
    "wiki_workspace": "wiki-memory",
    "synthesis": "synthesis",
    "design": "design",
    "preprint": "preprint",
    "export": "export"
  },
  "phases": {
    "prisma": "not_started",
    "rag": "not_started",
    "wiki": "ready",
    "pilot": "not_started",
    "preprint": "not_started",
    "export": "not_started"
  }
}
```

Paths below `paths` are stored as normalized relative paths. Consumers resolve them against the canonical `project_root`, then enforce containment before filesystem or database access.

## Bootstrap Component

A small standard-library Python command owns filesystem creation. Skills must call it instead of independently creating directories.

Proposed interface:

```text
python "<PLUGIN_ROOT>/scripts/study_workspace.py" create --name "Study name" --parent "."
python "<PLUGIN_ROOT>/scripts/study_workspace.py" inspect --project "./study-slug"
```

`--parent` is supplied by the skill as the absolute current workspace and is not requested interactively from the researcher. The command prints JSON only:

```json
{
  "status": "created",
  "project_root": "/absolute/workspace/study-name",
  "study_slug": "study-name",
  "state_file": "/absolute/workspace/study-name/.project-state.json"
}
```

The script uses only the Python standard library. It does not download models or create Qdrant collections during bootstrap.

## Naming and Collision Rules

The slug algorithm must be deterministic on Windows and Linux:

- Unicode normalized with NFKD, accents removed where representable.
- Lowercase ASCII letters and digits retained.
- Any run of other characters becomes one hyphen.
- Leading/trailing dots, spaces and hyphens removed.
- Windows reserved names (`CON`, `PRN`, `AUX`, `NUL`, `COM1`–`COM9`, `LPT1`–`LPT9`) rejected.
- Empty slug rejected and the user is asked for a different name.
- Maximum slug length: 80 characters.

Collision behavior:

- Existing directory with a valid `.project-state.json` whose `project_root` and slug match: report `status: resumable`; do not rewrite it; ask the user before resuming.
- Existing empty directory: it may be initialized only after explicit confirmation.
- Existing non-empty directory without valid state: stop with `directory_conflict`; never merge or overwrite.
- Existing symlink, junction or reparse-point target: stop with `unsafe_target`.

## Automatic Full-Text Acquisition

Today the automated database search (`core`, `doaj`, `eric`, `openaire`, `zenodo`, `semantic-scholar` MCP servers) only returns abstracts/metadata; no full text is fetched, and only manually supplied PDFs (Stream 2, `pdf_manuali/`) are ever stored as a complete document. This changes: when a search record exposes a resolvable open-access full-text URL (e.g. CORE's `sourceFulltextUrls`, OpenAIRE's OA links, DOAJ/Zenodo download links), the pipeline downloads it automatically and stores it as the source-of-record copy.

- New download happens during Stream 1 (automated search), right after a record is retained post-deduplication, not only after eligibility — so a reviewer screening on full text has it available, closing part of the "solo abstract" limitation documented in `prisma-review`.
- Downloads land in `<study>/sources/pdf-inbox/`, named by a stable id (DOI-derived slug or source id), and the local path is recorded back onto the record (`local_pdf_path` field) so later stages (screening, eligibility, `hybrid-rag index-pdf`) can find it without re-downloading.
- On eligibility inclusion, the file already in `pdf-inbox/` is copied (not re-downloaded) into `sources/pdf-inclusi/`, same as the existing manual-PDF flow.
- Download guards (new — no prior implementation exists despite earlier prose assuming one): HTTPS-only, resolve the URL's host and reject private/loopback/link-local IP ranges before connecting (SSRF guard), enforce a maximum response size (streamed, abort over limit), verify `Content-Type` is a PDF-like type before treating the body as one, and never follow a redirect to a host that fails the same guard.
- A failed or skipped download (paywalled, guard rejection, timeout) is not an error: the record keeps `local_pdf_path: null` and screening/eligibility proceed on the abstract exactly as today. This is a best-effort enrichment, not a new required gate.
- This applies per study, inside the sealed `sources/pdf-inbox/`; it never writes outside `project_root`.

## Isolation Enforcement

Isolation must be enforced in executable code, not only in skill instructions.

Before every managed read/write, database open, PDF import or export:

1. Resolve `project_root` and the requested path with platform-native canonicalization.
2. Reject paths whose resolved form is not a descendant of `project_root`.
3. Reject symlink/junction traversal that escapes the root.
4. For source imports, copy the file into `sources/` first; subsequent processing uses the internal copy.
5. For remote PDFs, download only into the study inbox after existing SSRF/size validation.
6. Never scan sibling directories or infer a wiki workspace from global configuration.

The plugin installation directory is the only allowed external read boundary, and only for executable scripts, templates and static configuration defaults. It is never a data destination.

## Skill and Pipeline Changes

### `pipeline-ricerca`

- Becomes the single bootstrap owner.
- Recognizes explicit and natural-language new-research intent.
- Requires name and confirmation, calls `study_workspace.py`, changes operational root, then invokes PRISMA.
- On every later invocation, finds `.project-state.json` in the active study root and validates it before routing.
- Refuses to operate from the parent workspace when multiple studies exist and no active study was selected by entering its directory.

### `prisma-review`

- Reads/writes all state under `<study>/prisma/`.
- Sets `wiki_workspace` from `.project-state.json`; it no longer asks for an arbitrary path.
- Imports PDFs into `<study>/sources/` before processing.
- During Stream 1, auto-downloads full text into `sources/pdf-inbox/` when a record exposes a guard-passing open-access URL (see "Automatic Full-Text Acquisition"); silently keeps `local_pdf_path: null` otherwise.
- Exports wiki pages only to the private `<study>/wiki-memory/` workspace.

### Hybrid RAG

- Stops deriving storage solely from the process current directory.
- Accepts an explicit project/state argument resolved to `<study>/database/qdrant-rag/`, its own database, independent of the wiki's.
- Writes only `prisma_papers` and `included_pdf_chunks`; it never opens or touches `qdrant-wiki`.
- Accepts eligibility input only from `<study>/prisma/` and included PDFs only from `<study>/sources/pdf-inclusi/`.
- Preserves current inclusion-contract validation and stale-record deletion.
- Query results are reranked with the cross-encoder (`BAAI/bge-reranker-v2-m3`) before being returned, by default in study mode.
- Refuses `index-prisma`/`index-pdf` when the mandatory wiki export for the current eligibility snapshot is missing, unless `--skip-wiki-export` is passed (logged in `project-log.md`).

### Wiki

- `wiki_workspace` is always `<study>/wiki-memory/`.
- Generated `wiki.config.json` points `qdrant.path` at `<study>/database/qdrant-wiki/`, its own database, independent of Hybrid RAG's, and contains one project keyed by the study slug.
- Wiki operations use only `wiki_pages` and `staging_wiki_pages`; rebuild never deletes evidence collections.
- Setup, query, ingest, rebuild and server commands validate containment against the master state when invoked through the research pipeline.
- No automatic query of an older/shared wiki is permitted.
- Wiki export of paper entities and the review synthesis is mandatory (not optional) before Hybrid RAG indexing, so every RAG-indexed paper has a human-readable, citable wiki page behind it.

### Pilot, Preprint and Export

- Read inputs through paths in master state.
- Write only to `design/`, `preprint/` and `export/` respectively.
- Pandoc reference templates may be copied into the study before use; output never targets an external directory.

## Lifecycle and Lazy Initialization

Bootstrap creates directories, configuration and empty state files but does not load ML models.

- The study Qdrant directory is created on the first wiki or evidence operation that needs it.
- Each component creates only its own collections. Evidence collections are initialized only after eligibility is complete; wiki collections are initialized on first rebuild/ingest/query.
- Model downloads occur only at the first operation that needs the selected model.

This keeps a new research project fast while preserving a complete and predictable filesystem contract.

## Error Handling and Recovery

Creation uses a temporary sibling directory named from the slug plus a random suffix. Files are written and fsynced where supported, then the temporary directory is renamed to the final slug. If the final rename fails, the temporary directory is removed and no valid study is reported.

The generated `.project-state.json` is written last inside the temporary structure. A directory without valid state is never treated as a study.

Runtime errors follow these rules:

- Path escape or unsafe link: fail closed; no partial operation.
- Invalid/corrupt state: report the exact field and do not guess paths.
- Database lock: report the store path and owning-process evidence when available; never delete a live lock automatically.
- Late wiki ingest inconsistency: mark wiki phase `needs_repair`, then require lint/rebuild from Markdown.
- RAG indexing failure: keep the prior usable index where backend semantics allow; do not mark the phase complete.

## Migration and Compatibility

Existing projects are not silently moved. Version 1.2.x projects continue to work through their existing skills, but the new bootstrap only creates sealed schema-version-1 workspaces.

A future explicit migration command may copy an existing project into the sealed layout. It is outside this implementation scope because automatic migration could mix unrelated wiki data into a new study.

No shared-memory import/export feature is included. If cross-study reuse is later required, it must copy selected, provenance-bearing Markdown pages into the target study after user confirmation and re-index them locally.

## Testing Strategy

### Unit tests

- Slug normalization, reserved names and maximum length.
- New creation, empty-directory initialization, resumable study and unsafe collision.
- Atomic failure leaves no valid final project.
- Relative path resolution and rejection of `..`, absolute external paths, symlink escape and Windows-style traversal.
- Generated state/config values, two distinct Qdrant paths (`qdrant-rag`, `qdrant-wiki`) and four non-overlapping collection names split across them.

### Integration tests

- Natural-language and explicit skill instructions route to the same bootstrap command.
- PRISMA writes only under `prisma/`.
- Hybrid RAG cannot index a sibling study's eligibility file or open its `qdrant-rag` directory, and never opens `qdrant-wiki`.
- Wiki query/ingest cannot open a sibling wiki, and never opens `qdrant-rag`.
- Hybrid RAG and wiki commands can run back-to-back (or concurrently) against the same study without a `database_in_use` error, since each owns its own Qdrant directory.
- `hybrid-rag index-prisma`/`index-pdf` refuses to run when the mandatory wiki export is missing, and proceeds when `--skip-wiki-export` is passed.
- `hybrid-rag query` results come back reranked (cross-encoder score present) in study mode.
- PDF import copies into the current study before processing.
- Pilot, preprint and DOCX output remain inside the study.
- Resuming a valid study preserves all existing files.

### Cross-platform CI

Run the isolation/bootstrap tests on `windows-latest` and `ubuntu-latest`. Tests use temporary directories and include platform-specific link behavior where supported. No test may depend on a machine-specific home directory.

## Documentation Changes

- Main English and Italian README: replace shared wiki examples with sealed study bootstrap.
- Wiki English and Italian README: state that the wiki is private to one study in this plugin.
- `docs/PROJECT-SPEC.md`: update canonical layout and state contract.
- `docs/models-and-setup.md`: explain that code may be installed globally but all research data remains below the generated study root.
- Skill instructions: use state-derived paths and document recovery/collision behavior.

## Acceptance Criteria

The feature is complete when:

1. A user can start with either supported intent, provide only a name, confirm, and receive `<CURRENT_WORKSPACE>/<slug>/`.
2. The generated directory contains valid master state, private wiki configuration and the complete documented structure.
3. Each study has two independent Qdrant paths (`qdrant-rag`, `qdrant-wiki`), and a second study in the same parent workspace resolves to different directories for both.
4. Attempts to read or write a sibling study through managed pipeline commands fail closed.
5. Existing valid studies resume without overwrite; unrelated existing directories are untouched.
6. Every RAG-indexed paper has a corresponding human-readable wiki entity page; `hybrid-rag query` returns cross-encoder-reranked results.
7. A search record with a guard-passing open-access full-text URL is auto-downloaded into `sources/pdf-inbox/` during Stream 1, with `local_pdf_path` set on the record; a record without one, or one that fails the SSRF/size/content-type guard, proceeds abstract-only with no error.
8. Windows and Ubuntu CI pass bootstrap, containment and resume tests.
9. Documentation in both languages matches the implemented layout and commands.

## Explicit Non-Goals

- Shared wiki memory across studies.
- Automatic import from older or external projects.
- Automatic migration of existing 1.2.x directory layouts.
- Eager model download or empty database creation during bootstrap.
- Selecting a parent outside the current Claude Code workspace.
