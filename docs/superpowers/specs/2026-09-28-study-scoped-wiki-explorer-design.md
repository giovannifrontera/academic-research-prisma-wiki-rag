# Study-scoped wiki web explorer — Design

**Date:** 2026-09-28
**Status:** approved
**Scope:** `wiki.py serve`, `wiki_server.py`, `wiki/frontend/index.html`, docs

## Problem

Each sealed study owns its wiki (`<study>/wiki-memory`), and the web explorer
serves exactly one wiki per process, so isolation already holds. Two gaps remain:

1. The server must be started with the raw `--workspace <study>/wiki-memory`
   path; nothing ties it to the study state.
2. The interface never says which study it is showing. The project filter
   (`wiki` / `<slug>` / all) only splits folders of the same study wiki, so a
   user running explorers for two studies cannot tell them apart.

## Decision

One explorer process per study (chosen over a multi-study selector, which
would require scanning sibling directories — forbidden by the isolated study
workspace spec). Shared or cross-study memory is out of scope: the plugin is
study-only.

## Design

### 1. `serve --project`

- `wiki.py serve` takes `--project <path>` as an alternative to
  `--workspace`; exactly one of the two is required.
- `<path>` may be the study root or any directory inside it. The study root
  is found with `scripts/study_paths.containing_study_root` (walks up to
  `.project-state.json`).
- The wiki workspace is `resolve_in_study(root, state["paths"]["wiki_workspace"])`,
  so a state file pointing outside the study is rejected.
- Errors exit non-zero with a clear message: no `.project-state.json` found,
  unreadable state, `wiki_workspace` escaping the study, or missing directory.
- No sibling scanning. Two studies at once means two processes on different
  `--port` values.
- `--workspace` keeps working unchanged (non-sealed wikis, tests).

### 2. Study identity in the UI

- The server derives study metadata from the served workspace: if the
  workspace lies inside a sealed study, it reads `study_name`, `study_slug`,
  `study_id` from `.project-state.json`; otherwise `null`. This covers both
  `--project` and a `--workspace` that points into a study.
- `/api/graph` adds `"study": {"name", "slug", "id"} | null` (authenticated,
  like the rest of the graph payload).
- The header shows a "Studio: <name>" badge (slug in the tooltip) and
  `document.title` becomes `<name> — Wiki Memory`. With `study: null`
  nothing changes.
- The existing project filter is kept as is.

### 3. Pipeline and documentation

- `pipeline-ricerca` and the wiki guides (EN/IT) document
  `wiki.py serve --project .` from inside the study as the standard way to
  explore its memory; screenshots are refreshed to show the study badge.

## Testing

- `--project` on the study root and on a subdirectory resolves the same
  `wiki-memory`.
- `--project` on a directory without `.project-state.json` fails.
- A state whose `wiki_workspace` escapes the study fails.
- `/api/graph` returns study metadata for a study wiki and `null` for a plain
  workspace.
- Manual check in Chrome: badge, tab title, graph unchanged.

## Non-goals

- Shared memory across studies, identity/personality memory outside a study.
- Multi-study selector or directory scanning.
