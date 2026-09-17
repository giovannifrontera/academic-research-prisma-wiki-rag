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
    │   └── qdrant/                  # the study's only vector database
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

Each study has exactly one embedded Qdrant database at `<study>/database/qdrant/`. RAG and wiki data are isolated logically through collections inside that database:

| Collection | Allowed content | Vector model |
|---|---|---|
| `prisma_papers` | Current eligibility export only | Hybrid RAG selected model |
| `included_pdf_chunks` | Approved included PDFs only | Hybrid RAG selected model |
| `wiki_pages` | Structured wiki pages from this study | Wiki BGE-M3 model |
| `staging_wiki_pages` | Temporary wiki ingest staging | Wiki BGE-M3 model |

Qdrant supports a different vector schema per collection, so Hybrid RAG and wiki collections may use different embedding dimensions without requiring separate databases. Collection names are fixed and no collection is shared, globally discovered, or selected from another project.

Embedded Qdrant permits only one active storage owner reliably across Windows and Linux. Pipeline commands therefore open the study database for one operation and close it deterministically. The optional wiki web server must release/close its client before a Hybrid RAG command runs; if it is actively serving, the pipeline stops with a clear `database_in_use` error instead of opening a second client against the same storage.

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
    "qdrant": "database/qdrant",
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
- Exports wiki pages only to the private `<study>/wiki-memory/` workspace.

### Hybrid RAG

- Stops deriving storage solely from the process current directory.
- Uses Qdrant for sealed workspaces and accepts an explicit project/state argument resolved to the shared `<study>/database/qdrant/`.
- Writes only `prisma_papers` and `included_pdf_chunks`; it never reads, clears or rebuilds wiki collections.
- Accepts eligibility input only from `<study>/prisma/` and included PDFs only from `<study>/sources/pdf-inclusi/`.
- Preserves current inclusion-contract validation and stale-record deletion.

### Wiki

- `wiki_workspace` is always `<study>/wiki-memory/`.
- Generated `wiki.config.json` contains the absolute private workspace, the canonical `<study>/database/qdrant/` path and one project keyed by the study slug.
- Wiki operations use only `wiki_pages` and `staging_wiki_pages`; rebuild never deletes evidence collections.
- Setup, query, ingest, rebuild and server commands validate containment against the master state when invoked through the research pipeline.
- No automatic query of an older/shared wiki is permitted.

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
- Generated state/config values, one Qdrant path and four non-overlapping collection names.

### Integration tests

- Natural-language and explicit skill instructions route to the same bootstrap command.
- PRISMA writes only under `prisma/`.
- Hybrid RAG cannot index a sibling study's eligibility file or open its Qdrant directory.
- Wiki query/ingest cannot open a sibling wiki.
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
3. Each study has one Qdrant path, and a second study in the same parent workspace resolves to a different Qdrant directory.
4. Attempts to read or write a sibling study through managed pipeline commands fail closed.
5. Existing valid studies resume without overwrite; unrelated existing directories are untouched.
6. Windows and Ubuntu CI pass bootstrap, containment and resume tests.
7. Documentation in both languages matches the implemented layout and commands.

## Explicit Non-Goals

- Shared wiki memory across studies.
- Automatic import from older or external projects.
- Automatic migration of existing 1.2.x directory layouts.
- Eager model download or empty database creation during bootstrap.
- Selecting a parent outside the current Claude Code workspace.
