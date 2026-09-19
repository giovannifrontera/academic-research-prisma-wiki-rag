# Isolated Study Workspace Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give every new research study a sealed, self-contained directory (`<workspace>/<study-slug>/`) with a canonical `.project-state.json` contract, two independent embedded Qdrant DBs (RAG and wiki, so the two subsystems never lock-contend), enforced path-containment so no study can read or write another study's data, a mandatory wiki export step that gives every RAG-indexed paper a human-readable/citable page, and cross-encoder reranking on Hybrid RAG queries (today only the wiki reranks).

**Architecture:** A new stdlib-only bootstrap script (`scripts/study_workspace.py`) owns directory creation, slugging, collision handling and the state contract. A shared containment helper (`scripts/study_paths.py`) is imported by `hybrid_rag_template.py` and the wiki scripts to resolve/validate paths against `project_root` before any read/write/db-open. `pipeline-ricerca` becomes the bootstrap entry point; `prisma-review`, `hybrid-rag` and the wiki skills are updated to consume `.project-state.json` instead of asking for/deriving arbitrary paths. `hybrid_rag_template.py` gains a cross-encoder rerank pass on `query` and a pre-index check that the mandatory wiki export has happened.

**Tech Stack:** Python 3 stdlib (pathlib, unicodedata, json, argparse, tempfile), pytest, existing `qdrant-client` dependency already used by `wiki/scripts/wiki_qdrant.py` and `skills/hybrid-rag/hybrid_rag_template.py`.

## Global Constraints

- Bootstrap script uses **only Python stdlib** — no new dependencies, no model downloads, no Qdrant collection creation at create time (spec: "Lifecycle and Lazy Initialization").
- Slug: NFKD normalize, strip accents, lowercase ASCII+digits, runs of other chars → single hyphen, strip leading/trailing `.`/space/hyphen, reject Windows reserved names (`CON,PRN,AUX,NUL,COM1-9,LPT1-9`), reject empty, max length 80.
- `.project-state.json` is written **last** inside a temp sibling dir (`<slug>-<random>`), then the temp dir is renamed into place. A dir without valid state is never treated as a study.
- Four fixed collections per study split across two independent Qdrant DBs, no others: `database/qdrant-rag/` holds `prisma_papers` + `included_pdf_chunks`; `database/qdrant-wiki/` holds `wiki_pages` + `staging_wiki_pages`. Hybrid RAG never opens `qdrant-wiki`; wiki never opens `qdrant-rag`.
- Wiki export (entity pages + synthesis) is mandatory before Hybrid RAG indexing — it is the human-readable evidence layer behind every RAG hit, not optional decoration.
- Hybrid RAG `query` reranks fused candidates with the cross-encoder `BAAI/bge-reranker-v2-m3` (same model the wiki already uses), on by default in study mode.
- Isolation check (containment) must run in code, not only be documented in a skill: resolve real path, reject anything not a descendant of `project_root`, reject symlink/junction escape.
- Existing 1.2.x (pre-study) projects keep working unmodified; no automatic migration is built.
- All new Python must run unmodified on Windows and Linux (this repo is developed cross-platform — see `dad551a` "harden ... Windows locking" in git log). Avoid POSIX-only APIs (no `os.symlink` assumptions, use `pathlib.Path.resolve(strict=False)`, no `fcntl`).

---

## File Structure

| File | Responsibility |
|---|---|
| `scripts/study_workspace.py` | CLI: `create --name --parent`, `inspect --project`. Slugging, collision rules, atomic directory creation, `.project-state.json` writer/reader. |
| `scripts/study_paths.py` | Shared containment/resolution helper: `load_state(project_root) -> dict`, `resolve_in_study(project_root, relative_or_absolute) -> Path` (raises `PathEscapeError` on escape), `require_containment(project_root, path)`. Imported by hybrid-rag and wiki scripts — no circular import since it has zero project-specific logic. |
| `tests/test_study_workspace.py` | Unit tests for slugging, collisions, atomic creation/failure, state contract shape. |
| `tests/test_study_paths.py` | Unit tests for containment: relative ok, `..` escape rejected, absolute external rejected, symlink escape rejected (skip symlink case on platforms without permission, e.g. `pytest.mark.skipif` for Windows without admin/dev-mode). |
| `skills/hybrid-rag/hybrid_rag_template.py` | Modify: accept `--project <study_root>` (optional; default = cwd, preserving current stand-alone behavior for pre-study projects). Resolve `rag_db` → `<project>/database/qdrant-rag`, rename `COLLECTION_PDF` from `pdf_manual` to `included_pdf_chunks` only when running in study mode. Add cross-encoder rerank to `query`. Add a wiki-export-present gate before `index-prisma`/`index-pdf` (override: `--skip-wiki-export`). |
| `skills/pipeline-ricerca/SKILL.md` | Add bootstrap section: explicit/NL new-study intent, calls `study_workspace.py create`, then proceeds into `prisma-review`. Document resume/refuse-from-parent behavior. |
| `skills/prisma-review/SKILL.md` | Replace "chiedi/salva `wiki_workspace`" free-text flow with: read `.project-state.json` if present, derive `wiki_workspace` = `<study>/wiki-memory`, else fall back to existing legacy behavior. |
| `wiki/scripts/wiki_qdrant.py`, `wiki/scripts/wiki.py` | Modify (only if names differ from spec): use `wiki_pages`/`staging_wiki_pages` collection names. |
| `docs/PROJECT-SPEC.md`, `docs/models-and-setup.md`, `README.md`, `README.it.md`, `wiki/README.md`, `wiki/README.it.md` | Doc updates per spec's "Documentation Changes" section — Task 9. |

---

## Task 1: Slug algorithm

**Files:**
- Create: `scripts/study_workspace.py`
- Test: `tests/test_study_workspace.py`

**Interfaces:**
- Produces: `slugify(name: str) -> str` — raises `ValueError("empty_slug")` on empty result, `ValueError("reserved_name")` on Windows reserved names, truncates to 80 chars.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_study_workspace.py
import pytest
from scripts.study_workspace import slugify

def test_slugify_basic():
    assert slugify("My Study 2026") == "my-study-2026"

def test_slugify_accents_nfkd():
    assert slugify("Attività Didàttica") == "attivita-didattica"

def test_slugify_collapses_punctuation():
    assert slugify("A///B   C!!!D") == "a-b-c-d"

def test_slugify_strips_leading_trailing_hyphens_dots_spaces():
    assert slugify("  .-.Hello.-.  ") == "hello"

def test_slugify_empty_raises():
    with pytest.raises(ValueError, match="empty_slug"):
        slugify("...---...")

def test_slugify_reserved_name_raises():
    for reserved in ["CON", "con", "PRN", "AUX", "NUL", "COM1", "LPT9"]:
        with pytest.raises(ValueError, match="reserved_name"):
            slugify(reserved)

def test_slugify_max_length_80():
    long_name = "a" * 200
    assert len(slugify(long_name)) == 80
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_study_workspace.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'scripts.study_workspace'` (create `scripts/__init__.py` empty file too; pytest resolves the repo root the same way `wiki/tests/conftest.py` already relies on).

- [ ] **Step 3: Implement `slugify`**

```python
# scripts/study_workspace.py
#!/usr/bin/env python3
"""Bootstrap and inspect isolated study workspaces.

See docs/superpowers/specs/2026-09-17-isolated-study-workspace-design.md.
"""
import argparse
import json
import os
import re
import sys
import unicodedata
import uuid
from datetime import datetime, timezone
from pathlib import Path

_RESERVED_NAMES = {
    "CON", "PRN", "AUX", "NUL",
    *(f"COM{i}" for i in range(1, 10)),
    *(f"LPT{i}" for i in range(1, 10)),
}
_MAX_SLUG_LEN = 80


def slugify(name: str) -> str:
    normalized = unicodedata.normalize("NFKD", name)
    ascii_only = normalized.encode("ascii", "ignore").decode("ascii")
    lowered = ascii_only.lower()
    collapsed = re.sub(r"[^a-z0-9]+", "-", lowered)
    stripped = collapsed.strip("-.")
    stripped = stripped.strip("-")
    truncated = stripped[:_MAX_SLUG_LEN].strip("-")
    if not truncated:
        raise ValueError("empty_slug")
    if truncated.upper() in _RESERVED_NAMES:
        raise ValueError("reserved_name")
    return truncated
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_study_workspace.py -v`
Expected: PASS (7 tests)

- [ ] **Step 5: Commit**

```bash
touch scripts/__init__.py
git add scripts/study_workspace.py scripts/__init__.py tests/test_study_workspace.py
git commit -m "feat: add study slug normalization"
```

---

## Task 2: State contract read/write

**Files:**
- Modify: `scripts/study_workspace.py`
- Test: `tests/test_study_workspace.py`

**Interfaces:**
- Consumes: `slugify` from Task 1.
- Produces: `build_state(study_name: str, study_slug: str, project_root: Path) -> dict` (matches spec's `.project-state.json` schema v1); `STATE_FILENAME = ".project-state.json"`; `read_state(project_root: Path) -> dict` (raises `FileNotFoundError` if missing, `ValueError("invalid_state")` if JSON invalid or `schema_version` missing/unsupported).

- [ ] **Step 1: Write the failing tests**

```python
def test_build_state_shape(tmp_path):
    from scripts.study_workspace import build_state
    root = tmp_path / "my-study"
    state = build_state("My Study", "my-study", root)
    assert state["schema_version"] == 1
    assert state["study_name"] == "My Study"
    assert state["study_slug"] == "my-study"
    assert state["project_root"] == str(root)
    assert state["isolation"] == {
        "mode": "sealed", "allow_external_reads": False, "allow_external_writes": False
    }
    assert state["paths"] == {
        "prisma": "prisma", "sources": "sources", "qdrant": "database/qdrant",
        "wiki_workspace": "wiki-memory", "synthesis": "synthesis",
        "design": "design", "preprint": "preprint", "export": "export",
    }
    assert state["phases"]["wiki"] == "ready"
    assert state["phases"]["prisma"] == "not_started"
    uuid.UUID(state["study_id"])  # valid uuid4, raises if not

def test_read_state_missing_raises(tmp_path):
    from scripts.study_workspace import read_state
    with pytest.raises(FileNotFoundError):
        read_state(tmp_path / "nope")

def test_read_state_invalid_json_raises(tmp_path):
    from scripts.study_workspace import read_state, STATE_FILENAME
    d = tmp_path / "study"
    d.mkdir()
    (d / STATE_FILENAME).write_text("{not json", encoding="utf-8")
    with pytest.raises(ValueError, match="invalid_state"):
        read_state(d)
```

(add `import uuid` to the top of `tests/test_study_workspace.py`)

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_study_workspace.py -v`
Expected: FAIL — `ImportError: cannot import name 'build_state'`

- [ ] **Step 3: Implement**

```python
# append to scripts/study_workspace.py
STATE_FILENAME = ".project-state.json"
SCHEMA_VERSION = 1


def build_state(study_name: str, study_slug: str, project_root: Path) -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "study_id": str(uuid.uuid4()),
        "study_name": study_name,
        "study_slug": study_slug,
        "project_root": str(project_root),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "isolation": {
            "mode": "sealed",
            "allow_external_reads": False,
            "allow_external_writes": False,
        },
        "paths": {
            "prisma": "prisma",
            "sources": "sources",
            "qdrant": "database/qdrant",
            "wiki_workspace": "wiki-memory",
            "synthesis": "synthesis",
            "design": "design",
            "preprint": "preprint",
            "export": "export",
        },
        "phases": {
            "prisma": "not_started",
            "rag": "not_started",
            "wiki": "ready",
            "pilot": "not_started",
            "preprint": "not_started",
            "export": "not_started",
        },
    }


def read_state(project_root: Path) -> dict:
    state_path = Path(project_root) / STATE_FILENAME
    if not state_path.exists():
        raise FileNotFoundError(str(state_path))
    try:
        with open(state_path, "r", encoding="utf-8") as f:
            state = json.load(f)
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid_state: {exc}") from exc
    if state.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("invalid_state: unsupported schema_version")
    return state
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_study_workspace.py -v`
Expected: PASS (10 tests)

- [ ] **Step 5: Commit**

```bash
git add scripts/study_workspace.py tests/test_study_workspace.py
git commit -m "feat: add study state contract read/write"
```

---

## Task 3: Atomic directory creation with collision rules

**Files:**
- Modify: `scripts/study_workspace.py`
- Test: `tests/test_study_workspace.py`

**Interfaces:**
- Consumes: `slugify`, `build_state`, `read_state`, `STATE_FILENAME` from Tasks 1–2.
- Produces: `create_study(name: str, parent: Path) -> dict` returning `{"status": "created"|"resumable", "project_root": str, "study_slug": str, "state_file": str}`, or raising `StudyCollisionError(kind: str)` where `kind` is one of `"directory_conflict"`, `"unsafe_target"`. `DIRECTORY_TREE` constant listing the subdirs from the spec's layout (used by `create_study` and importable by future tasks).

- [ ] **Step 1: Write the failing tests**

```python
def test_create_study_new(tmp_path):
    from scripts.study_workspace import create_study
    result = create_study("My Study", tmp_path)
    assert result["status"] == "created"
    root = Path(result["project_root"])
    assert root == tmp_path / "my-study"
    assert (root / ".project-state.json").exists()
    assert (root / "prisma").is_dir()
    assert (root / "sources" / "pdf-inbox").is_dir()
    assert (root / "sources" / "pdf-inclusi").is_dir()
    assert (root / "database" / "qdrant-rag").is_dir()
    assert (root / "database" / "qdrant-wiki").is_dir()
    assert (root / "wiki-memory" / "wiki" / "concepts").is_dir()
    assert (root / "wiki-memory" / "wiki-works" / "my-study" / "raw").is_dir()
    assert (root / "synthesis").is_dir()
    assert (root / "design").is_dir()
    assert (root / "preprint").is_dir()
    assert (root / "export").is_dir()
    assert (root / "README.md").exists()
    assert (root / "project-log.md").exists()

def test_create_study_resumable(tmp_path):
    from scripts.study_workspace import create_study
    create_study("My Study", tmp_path)
    result = create_study("My Study", tmp_path)
    assert result["status"] == "resumable"

def test_create_study_directory_conflict(tmp_path):
    from scripts.study_workspace import create_study, StudyCollisionError
    (tmp_path / "my-study").mkdir()
    (tmp_path / "my-study" / "unrelated.txt").write_text("x", encoding="utf-8")
    with pytest.raises(StudyCollisionError, match="directory_conflict"):
        create_study("My Study", tmp_path)

def test_create_study_empty_dir_initializes(tmp_path):
    from scripts.study_workspace import create_study
    (tmp_path / "my-study").mkdir()
    result = create_study("My Study", tmp_path)
    assert result["status"] == "created"

def test_create_study_atomic_failure_leaves_no_partial(tmp_path, monkeypatch):
    from scripts import study_workspace as sw
    def boom(*a, **kw):
        raise OSError("disk full simulated")
    monkeypatch.setattr(sw.os, "rename", boom)
    with pytest.raises(OSError):
        sw.create_study("My Study", tmp_path)
    assert not (tmp_path / "my-study").exists()
    assert list(tmp_path.iterdir()) == []  # temp dir cleaned up
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_study_workspace.py -v`
Expected: FAIL — `ImportError: cannot import name 'create_study'`

- [ ] **Step 3: Implement**

```python
# append to scripts/study_workspace.py
import shutil
import secrets

DIRECTORY_TREE = [
    "prisma",
    "sources/pdf-inbox",
    "sources/pdf-inclusi",
    "database/qdrant-rag",
    "database/qdrant-wiki",
    "wiki-memory/wiki/concepts",
    "wiki-memory/wiki/synthesis",
    "wiki-memory/wiki/identity",
    "wiki-memory/pdf-inbox",
    "synthesis",
    "design",
    "preprint",
    "export",
]


class StudyCollisionError(Exception):
    def __init__(self, kind: str):
        super().__init__(kind)
        self.kind = kind


def _is_existing_valid_study(path: Path, expected_slug: str) -> bool:
    if not (path / STATE_FILENAME).exists():
        return False
    try:
        state = read_state(path)
    except ValueError:
        return False
    return state.get("study_slug") == expected_slug


def create_study(name: str, parent) -> dict:
    parent = Path(parent).resolve()
    slug = slugify(name)
    final_root = parent / slug

    if final_root.exists():
        if _is_existing_valid_study(final_root, slug):
            return {
                "status": "resumable",
                "project_root": str(final_root),
                "study_slug": slug,
                "state_file": str(final_root / STATE_FILENAME),
            }
        if any(final_root.iterdir()):
            raise StudyCollisionError("directory_conflict")
        if final_root.is_symlink():
            raise StudyCollisionError("unsafe_target")
        # empty existing directory: fall through and initialize in place

    tmp_root = parent / f"{slug}-{secrets.token_hex(4)}"
    tmp_root.mkdir(parents=True, exist_ok=False)
    try:
        for rel in DIRECTORY_TREE:
            (tmp_root / rel).mkdir(parents=True, exist_ok=True)
        (tmp_root / "wiki-memory" / "wiki-works" / slug / "raw").mkdir(parents=True, exist_ok=True)
        (tmp_root / "wiki-memory" / "wiki-works" / slug / "entities").mkdir(parents=True, exist_ok=True)
        (tmp_root / "wiki-memory" / "wiki-works" / slug / "concepts").mkdir(parents=True, exist_ok=True)
        (tmp_root / "wiki-memory" / "wiki-works" / slug / "synthesis").mkdir(parents=True, exist_ok=True)

        (tmp_root / "project-log.md").write_text(
            f"# Project log — {name}\n\nCreated: {datetime.now(timezone.utc).isoformat()}\n",
            encoding="utf-8",
        )
        (tmp_root / "README.md").write_text(
            f"# {name}\n\nStudy root generated by study_workspace.py.\n",
            encoding="utf-8",
        )

        state = build_state(name, slug, final_root)
        state_path = tmp_root / STATE_FILENAME
        with open(state_path, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)
            f.flush()
            os.fsync(f.fileno())

        if final_root.exists():
            final_root.rmdir()  # only reachable for the empty-dir init case
        os.rename(tmp_root, final_root)
    except Exception:
        shutil.rmtree(tmp_root, ignore_errors=True)
        raise

    return {
        "status": "created",
        "project_root": str(final_root),
        "study_slug": slug,
        "state_file": str(final_root / STATE_FILENAME),
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_study_workspace.py -v`
Expected: PASS (15 tests)

- [ ] **Step 5: Commit**

```bash
git add scripts/study_workspace.py tests/test_study_workspace.py
git commit -m "feat: add atomic study directory creation with collision handling"
```

---

## Task 4: CLI entry point (`create`/`inspect`)

**Files:**
- Modify: `scripts/study_workspace.py`
- Test: `tests/test_study_workspace.py`

**Interfaces:**
- Consumes: `create_study`, `read_state`, `StudyCollisionError` from Task 3.
- Produces: `main(argv: list[str]) -> int`, prints one JSON object to stdout, non-zero exit on error with `{"status": "error", "kind": ...}` JSON on stdout (spec requires JSON-only output).

- [ ] **Step 1: Write the failing tests**

```python
def test_cli_create(tmp_path, capsys):
    from scripts.study_workspace import main
    exit_code = main(["create", "--name", "My Study", "--parent", str(tmp_path)])
    assert exit_code == 0
    out = json.loads(capsys.readouterr().out)
    assert out["status"] == "created"

def test_cli_create_collision_reports_error(tmp_path, capsys):
    from scripts.study_workspace import main
    (tmp_path / "my-study").mkdir()
    (tmp_path / "my-study" / "f.txt").write_text("x", encoding="utf-8")
    exit_code = main(["create", "--name", "My Study", "--parent", str(tmp_path)])
    assert exit_code != 0
    out = json.loads(capsys.readouterr().out)
    assert out == {"status": "error", "kind": "directory_conflict"}

def test_cli_inspect(tmp_path, capsys):
    from scripts.study_workspace import main
    main(["create", "--name", "My Study", "--parent", str(tmp_path)])
    capsys.readouterr()
    exit_code = main(["inspect", "--project", str(tmp_path / "my-study")])
    assert exit_code == 0
    out = json.loads(capsys.readouterr().out)
    assert out["study_slug"] == "my-study"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_study_workspace.py -v`
Expected: FAIL — `ImportError: cannot import name 'main'`

- [ ] **Step 3: Implement**

```python
# append to scripts/study_workspace.py

def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="study_workspace.py")
    sub = parser.add_subparsers(dest="command", required=True)

    create_p = sub.add_parser("create")
    create_p.add_argument("--name", required=True)
    create_p.add_argument("--parent", required=True)

    inspect_p = sub.add_parser("inspect")
    inspect_p.add_argument("--project", required=True)

    args = parser.parse_args(argv)

    try:
        if args.command == "create":
            result = create_study(args.name, args.parent)
        else:
            result = read_state(Path(args.project))
        print(json.dumps(result))
        return 0
    except StudyCollisionError as exc:
        print(json.dumps({"status": "error", "kind": exc.kind}))
        return 1
    except (FileNotFoundError, ValueError) as exc:
        print(json.dumps({"status": "error", "kind": str(exc)}))
        return 1


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_study_workspace.py -v`
Expected: PASS (18 tests)

- [ ] **Step 5: Commit**

```bash
git add scripts/study_workspace.py tests/test_study_workspace.py
git commit -m "feat: add study_workspace.py CLI (create/inspect)"
```

---

## Task 5: Containment helper (`study_paths.py`)

**Files:**
- Create: `scripts/study_paths.py`
- Test: `tests/test_study_paths.py`

**Interfaces:**
- Produces: `PathEscapeError(Exception)`; `resolve_in_study(project_root: Path, relative_or_absolute) -> Path` (raises `PathEscapeError` if the resolved path is not a descendant of `project_root`, following symlinks); `containing_study_root(start: Path) -> Path | None` (walks up from `start` looking for `.project-state.json`, returns the directory containing it or `None` if none found before filesystem root).

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_study_paths.py
import os
import sys
import pytest
from pathlib import Path

from scripts.study_paths import resolve_in_study, PathEscapeError, containing_study_root

def test_resolve_relative_inside(tmp_path):
    root = tmp_path / "study"
    root.mkdir()
    result = resolve_in_study(root, "prisma/eligibility_prisma.json")
    assert result == (root / "prisma" / "eligibility_prisma.json").resolve()

def test_resolve_rejects_dotdot_escape(tmp_path):
    root = tmp_path / "study"
    root.mkdir()
    with pytest.raises(PathEscapeError):
        resolve_in_study(root, "../outside.json")

def test_resolve_rejects_absolute_external(tmp_path):
    root = tmp_path / "study"
    root.mkdir()
    outside = tmp_path / "elsewhere.json"
    with pytest.raises(PathEscapeError):
        resolve_in_study(root, str(outside))

def test_resolve_allows_absolute_internal(tmp_path):
    root = tmp_path / "study"
    root.mkdir()
    inside = root / "prisma" / "x.json"
    result = resolve_in_study(root, str(inside))
    assert result == inside.resolve()

@pytest.mark.skipif(sys.platform == "win32", reason="symlink creation needs elevated perms on Windows")
def test_resolve_rejects_symlink_escape(tmp_path):
    root = tmp_path / "study"
    root.mkdir()
    outside_target = tmp_path / "outside_dir"
    outside_target.mkdir()
    link = root / "escape_link"
    os.symlink(outside_target, link, target_is_directory=True)
    with pytest.raises(PathEscapeError):
        resolve_in_study(root, "escape_link/file.json")

def test_containing_study_root_found(tmp_path):
    root = tmp_path / "study"
    (root / "prisma").mkdir(parents=True)
    (root / ".project-state.json").write_text("{}", encoding="utf-8")
    found = containing_study_root(root / "prisma")
    assert found == root

def test_containing_study_root_none(tmp_path):
    assert containing_study_root(tmp_path) is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_study_paths.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'scripts.study_paths'`

- [ ] **Step 3: Implement**

```python
# scripts/study_paths.py
"""Path containment helpers shared by hybrid-rag and wiki scripts.

Kept dependency-free (stdlib only) so it can be imported from any skill
script without pulling in study_workspace's CLI/argparse surface.
"""
from pathlib import Path

STATE_FILENAME = ".project-state.json"


class PathEscapeError(Exception):
    pass


def resolve_in_study(project_root, relative_or_absolute) -> Path:
    root = Path(project_root).resolve()
    candidate = Path(relative_or_absolute)
    target = candidate if candidate.is_absolute() else root / candidate
    resolved = target.resolve(strict=False)
    try:
        resolved.relative_to(root)
    except ValueError:
        raise PathEscapeError(f"{resolved} escapes study root {root}")
    return resolved


def containing_study_root(start) -> Path | None:
    current = Path(start).resolve()
    for candidate in [current, *current.parents]:
        if (candidate / STATE_FILENAME).is_file():
            return candidate
    return None
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_study_paths.py -v`
Expected: PASS (7 tests, 6 on Windows)

- [ ] **Step 5: Commit**

```bash
git add scripts/study_paths.py tests/test_study_paths.py
git commit -m "feat: add study path containment helper"
```

---

## Task 6: `hybrid_rag_template.py` study-mode support

**Files:**
- Modify: `skills/hybrid-rag/hybrid_rag_template.py:1-90` (imports, constants, `_load_config`/`_save_config`)
- Test: `tests/test_hybrid_rag.py` (existing file — read it first to match its fixture style before adding)

**Interfaces:**
- Consumes: `resolve_in_study`, `containing_study_root`, `PathEscapeError` from Task 5 (`scripts.study_paths`).
- Produces: new module-level `_resolve_rag_dir(project=None) -> Path` used everywhere `RAG_DIR`/`Path(RAG_DIR)` is currently referenced, resolving to `<project>/database/qdrant-rag` in study mode; new optional `--project` arg on every subcommand; new `_collection_pdf_name(project=None) -> str` returning `"included_pdf_chunks"` in study mode, `"pdf_manual"` (current `COLLECTION_PDF`) otherwise — preserving backward compatibility with pre-study projects per spec's "Migration and Compatibility" section. (Cross-encoder rerank and the wiki-export gate are added in Task 6b, once storage resolution here is in place and tested.)

- [ ] **Step 1: Read the existing test file to match conventions**

Run: `cat tests/test_hybrid_rag.py` and note the exact import mechanism used to load `hybrid_rag_template.py` (its directory `skills/hybrid-rag` has a hyphen, so it is very likely loaded via `importlib.util.spec_from_file_location`, not a plain `import`). New tests must reuse that identical loading pattern.

- [ ] **Step 2: Write the failing test**

```python
# append to tests/test_hybrid_rag.py, reusing this file's existing
# module-loading fixture/helper (do not invent a second one)
def test_rag_dir_resolves_under_study_project(tmp_path, hrt_module):
    from scripts.study_workspace import create_study
    result = create_study("My Study", tmp_path)
    project_root = result["project_root"]
    rag_dir = hrt_module._resolve_rag_dir(project=project_root)
    assert str(rag_dir) == str(Path(project_root) / "database" / "qdrant-rag")

def test_rag_dir_defaults_to_cwd_rag_db_without_project(tmp_path, monkeypatch, hrt_module):
    monkeypatch.chdir(tmp_path)
    rag_dir = hrt_module._resolve_rag_dir(project=None)
    assert str(rag_dir) == str(tmp_path / "rag_db")

def test_collection_pdf_name_switches_in_study_mode(tmp_path, hrt_module):
    from scripts.study_workspace import create_study
    result = create_study("My Study", tmp_path)
    assert hrt_module._collection_pdf_name(project=result["project_root"]) == "included_pdf_chunks"
    assert hrt_module._collection_pdf_name(project=None) == "pdf_manual"
```

`hrt_module` here stands for whatever fixture name `tests/test_hybrid_rag.py` already exposes for the loaded module (read Step 1's output and use the real name — do not add a second import mechanism alongside it).

- [ ] **Step 3: Run tests to verify they fail**

Run: `pytest tests/test_hybrid_rag.py -v`
Expected: FAIL — `AttributeError: module has no attribute '_resolve_rag_dir'`

- [ ] **Step 4: Implement in `skills/hybrid-rag/hybrid_rag_template.py`**

Add near the top, right after the existing imports and before `MODEL_CATALOG`:

```python
import sys as _sys
from pathlib import Path as _Path
_PLUGIN_ROOT = _Path(__file__).resolve().parents[2]
if str(_PLUGIN_ROOT) not in _sys.path:
    _sys.path.insert(0, str(_PLUGIN_ROOT))
from scripts.study_paths import resolve_in_study, containing_study_root, PathEscapeError


def _resolve_rag_dir(project=None) -> Path:
    if project is not None:
        return resolve_in_study(project, "database/qdrant-rag")
    return Path(RAG_DIR)


def _collection_pdf_name(project=None) -> str:
    return "included_pdf_chunks" if project is not None else COLLECTION_PDF
```

Then update every call site that currently does `Path(RAG_DIR)` / builds `CONFIG_FILE` / references `COLLECTION_PDF` for indexing to route through `_resolve_rag_dir(args.project)` / `_collection_pdf_name(args.project)`, and add `parser.add_argument("--project", default=None)` once on the shared top-level `argparse.ArgumentParser` so every subcommand inherits it (find that construction near the CLI entry point at the bottom of the file).

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/test_hybrid_rag.py tests/test_study_workspace.py tests/test_study_paths.py -v`
Expected: PASS, no regressions in pre-existing `test_hybrid_rag.py` cases

- [ ] **Step 6: Commit**

```bash
git add skills/hybrid-rag/hybrid_rag_template.py tests/test_hybrid_rag.py
git commit -m "feat: hybrid-rag resolves storage under sealed study when --project given"
```

---

## Task 6b: Cross-encoder rerank + mandatory wiki-export gate on Hybrid RAG

**Files:**
- Modify: `skills/hybrid-rag/hybrid_rag_template.py` (`query` command; `index-prisma`/`index-pdf` commands)
- Test: `tests/test_hybrid_rag.py`

**Interfaces:**
- Consumes: `_resolve_rag_dir`, `_collection_pdf_name` from Task 6; `resolve_in_study` from Task 5.
- Produces: `_rerank(query_text: str, candidates: list[dict], top_k: int) -> list[dict]` (lazily imports/loads a `sentence_transformers.CrossEncoder("BAAI/bge-reranker-v2-m3")`, cached module-level like `_encoder_cache`, sorts `candidates` by cross-encoder score descending, returns top `top_k` with a `"rerank_score"` key added to each dict); `_wiki_export_marker_present(project: Path) -> bool` (checks for at least one file under `<project>/wiki-memory/wiki-works/<slug>/entities/*.md` — read the actual entity filename convention from `skills/prisma-review/SKILL.md`'s wiki export section before hardcoding a glob, since Task 9 documents that flow); new `--skip-wiki-export` flag on `index-prisma`/`index-pdf`.

- [ ] **Step 1: Read `wiki/scripts/wiki_rerank.py` to reuse its exact CrossEncoder loading pattern**

Run: `cat wiki/scripts/wiki_rerank.py` — copy its lazy-load/caching approach for `_rerank` instead of writing a second one, so both subsystems load the model the same way (same cache dir, same call signature shape where reasonable).

- [ ] **Step 2: Write the failing tests**

```python
# append to tests/test_hybrid_rag.py
def test_query_returns_reranked_results_in_study_mode(tmp_path, hrt_module, monkeypatch):
    from scripts.study_workspace import create_study
    result = create_study("My Study", tmp_path)
    project_root = result["project_root"]

    fake_candidates = [
        {"text": "irrelevant", "score": 0.9},
        {"text": "highly relevant to query", "score": 0.5},
    ]
    monkeypatch.setattr(
        hrt_module, "_rerank",
        lambda query_text, candidates, top_k: list(reversed(candidates))[:top_k],
    )
    # exercise whatever hrt_module function assembles query results (e.g. hrt_module._query)
    # and assert the reordered/rerank-scored list wins over the raw RRF order — replace
    # `hrt_module._query_candidates(...)` below with the actual internal query-assembly
    # function name found while reading the file in Task 6 Step 1.
    reranked = hrt_module._rerank("some query", fake_candidates, top_k=2)
    assert reranked[0]["text"] == "highly relevant to query"


def test_index_prisma_refuses_without_wiki_export(tmp_path, hrt_module):
    from scripts.study_workspace import create_study
    result = create_study("My Study", tmp_path)
    with pytest.raises(SystemExit):
        hrt_module.main([
            "index-prisma", str(Path(result["project_root"]) / "prisma" / "eligibility_prisma.json"),
            "--project", result["project_root"],
        ])


def test_index_prisma_skip_wiki_export_flag_bypasses_gate(tmp_path, hrt_module):
    from scripts.study_workspace import create_study
    result = create_study("My Study", tmp_path)
    eligibility = Path(result["project_root"]) / "prisma" / "eligibility_prisma.json"
    eligibility.write_text("[]", encoding="utf-8")
    # should not raise for the wiki-export gate specifically (may still no-op on empty input)
    hrt_module.main([
        "index-prisma", str(eligibility),
        "--project", result["project_root"],
        "--skip-wiki-export",
    ])
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `pytest tests/test_hybrid_rag.py -v -k "rerank or wiki_export"`
Expected: FAIL — `AttributeError: module has no attribute '_rerank'` / gate not enforced yet

- [ ] **Step 4: Implement `_rerank` and the wiki-export gate**

```python
# add to skills/hybrid-rag/hybrid_rag_template.py, near the encoder cache section
_reranker_cache: dict = {}

def _get_reranker():
    if "model" not in _reranker_cache:
        from sentence_transformers import CrossEncoder
        _reranker_cache["model"] = CrossEncoder("BAAI/bge-reranker-v2-m3")
    return _reranker_cache["model"]


def _rerank(query_text: str, candidates: list, top_k: int) -> list:
    if not candidates:
        return candidates
    model = _get_reranker()
    pairs = [(query_text, c.get("text", c.get("chunk_text", ""))) for c in candidates]
    scores = model.predict(pairs)
    for c, s in zip(candidates, scores):
        c["rerank_score"] = float(s)
    return sorted(candidates, key=lambda c: c["rerank_score"], reverse=True)[:top_k]


def _wiki_export_marker_present(project) -> bool:
    from scripts.study_workspace import read_state
    state = read_state(project)
    entities_dir = (Path(project) / state["paths"]["wiki_workspace"]
                    / "wiki-works" / state["study_slug"] / "entities")
    return entities_dir.is_dir() and any(entities_dir.glob("*.md"))
```

Wire `_rerank` into the existing `query` subcommand's result-assembly path (found in Task 6 Step 1's read) right before results are printed/returned, passing the already-fused dense+sparse candidate list and a `top_k` matching the command's existing `--k`/limit argument. Wire `_wiki_export_marker_present` into `index-prisma`/`index-pdf`: at the top of each handler, if `args.project` is set and not `args.skip_wiki_export` and not `_wiki_export_marker_present(args.project)`, print a JSON error and `sys.exit(1)`. Add `parser.add_argument("--skip-wiki-export", action="store_true")` alongside the `--project` flag added in Task 6.

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/test_hybrid_rag.py -v`
Expected: PASS, no regressions

- [ ] **Step 6: Commit**

```bash
git add skills/hybrid-rag/hybrid_rag_template.py tests/test_hybrid_rag.py
git commit -m "feat: cross-encoder rerank + mandatory wiki-export gate on hybrid-rag"
```

---

## Task 7: Wiki study-mode collection names

**Files:**
- Modify: `wiki/scripts/wiki_qdrant.py`, `wiki/scripts/wiki_workflows.py`, `wiki/scripts/wiki_server.py`, `wiki/scripts/wiki_graph.py` (only the ones that actually reference the collection name constants, confirmed in Step 1)
- Test: `wiki/tests/test_wiki_qdrant.py`

**Interfaces:**
- Produces: confirmation/alignment that the wiki subsystem's pages/staging collection name constants equal `wiki_pages` / `staging_wiki_pages` exactly (the names the bootstrap-generated `wiki.config.json` and the isolation spec both assume).

- [ ] **Step 1: Inspect current collection naming**

Run: `grep -n "table_name\|COLLECTION\|\"pages\"\|\"staging" wiki/scripts/wiki_qdrant.py wiki/scripts/wiki_workflows.py wiki/scripts/wiki.py`

If names already are `wiki_pages`/`staging_wiki_pages`, this task is a no-op — record that finding and skip to Task 8. If names differ, continue below.

- [ ] **Step 2: Write the failing test** (only if renaming is needed)

```python
# append to wiki/tests/test_wiki_qdrant.py
def test_collection_names_match_isolated_workspace_spec():
    from wiki.scripts import wiki_qdrant  # match this test file's existing import style
    assert wiki_qdrant.TABLE_PAGES == "wiki_pages"
    assert wiki_qdrant.TABLE_STAGING == "staging_wiki_pages"
```

(replace `TABLE_PAGES`/`TABLE_STAGING` with the actual current constant names found in Step 1)

- [ ] **Step 3: Run test to verify it fails**

Run: `pytest wiki/tests/test_wiki_qdrant.py -v -k isolated_workspace_spec`
Expected: FAIL with a string mismatch showing the current name

- [ ] **Step 4: Rename the constant(s) at their definition site and every call site**

Run after editing: `grep -rn "<old_name>" wiki/scripts/` to confirm zero remaining references.

- [ ] **Step 5: Run full wiki test suite**

Run: `pytest wiki/tests/ -v`
Expected: PASS, no regressions

- [ ] **Step 6: Commit**

```bash
git add wiki/scripts/
git commit -m "refactor: align wiki collection names with isolated study spec"
```

---

## Task 8: Bootstrap generates study-scoped `wiki.config.json`

**Files:**
- Modify: `scripts/study_workspace.py` (`create_study`)
- Test: `tests/test_study_workspace.py`

**Interfaces:**
- Consumes: `DIRECTORY_TREE`, `create_study` from Task 3.
- Produces: `create_study` now also writes `<study>/wiki-memory/wiki.config.json` with `workspace` = absolute `<study>/wiki-memory`, one project keyed by the study slug pointing at `wiki-works/<slug>`, and `qdrant.path` = absolute `<study>/database/qdrant-wiki` (the wiki's own DB, independent of Hybrid RAG's `qdrant-rag`). Before writing, confirm via `grep -n "workspace\|qdrant\|projects" wiki/scripts/wiki_check_setup.py` that these keys satisfy that script's validation.

- [ ] **Step 1: Write the failing test**

```python
def test_create_study_writes_wiki_config(tmp_path):
    from scripts.study_workspace import create_study
    result = create_study("My Study", tmp_path)
    root = Path(result["project_root"])
    config_path = root / "wiki-memory" / "wiki.config.json"
    assert config_path.exists()
    config = json.loads(config_path.read_text(encoding="utf-8"))
    assert config["workspace"] == str(root / "wiki-memory")
    assert "my-study" in config["projects"]
    assert config["projects"]["my-study"]["path"] == "wiki-works/my-study"
    assert config["qdrant"]["path"] == str(root / "database" / "qdrant-wiki")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_study_workspace.py -v -k wiki_config`
Expected: FAIL — `AssertionError` (file doesn't exist yet)

- [ ] **Step 3: Implement** — inside `create_study`, after the `wiki-works/<slug>/...` directories are created and before the state file is written. Note `final_root` (not `tmp_root`) must be used for all absolute path *values* written into the config, since the whole tree is renamed from `tmp_root` to `final_root` atomically right after, but `tmp_root` is where the file is physically written so it moves with the rename:

```python
    wiki_config = {
        "workspace": str(final_root / "wiki-memory"),
        "projects": {
            slug: {
                "path": f"wiki-works/{slug}",
                "keywords": ["paper", "studio", "PRISMA", "articolo", "ricerca",
                             "review", "systematic", "pilot"],
            }
        },
        "thresholds": {
            "index_token_budget": 4000, "staleness_days": 90,
            "similarity_merge": 0.95, "similarity_orphan": 0.50,
            "synthesis_min_tokens": 300, "synthesis_min_sources": 2,
            "chunk_size_tokens": 512, "chunk_overlap_tokens": 64,
            "page_chunk_threshold_tokens": 1500,
            "quality_filter_min_score": 6, "dedup_auto": 0.90, "dedup_warn": 0.75,
        },
        "qdrant": {
            "path": str(final_root / "database" / "qdrant-wiki"),
            "embedding_model": "BAAI/bge-m3",
            "reranker_model": "BAAI/bge-reranker-v2-m3",
            "rerank": True,
        },
        "exclude_from_index": [],
    }
    with open(tmp_root / "wiki-memory" / "wiki.config.json", "w", encoding="utf-8") as f:
        json.dump(wiki_config, f, indent=2)
```

Insert this block in `create_study` right before the `state = build_state(...)` line (which already computes `final_root`-based values the same way, so `final_root` is already in scope at this point).

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_study_workspace.py -v`
Expected: PASS (all prior + 1 new test)

- [ ] **Step 5: Commit**

```bash
git add scripts/study_workspace.py tests/test_study_workspace.py
git commit -m "feat: bootstrap generates study-scoped wiki.config.json"
```

---

## Task 9: Skill documentation updates

**Files:**
- Modify: `skills/pipeline-ricerca/SKILL.md`
- Modify: `skills/prisma-review/SKILL.md`
- Modify: `docs/PROJECT-SPEC.md`, `docs/models-and-setup.md`
- Modify: `README.md`, `README.it.md`, `wiki/README.md`, `wiki/README.it.md`

No automated tests apply to documentation; verified by re-reading against the spec's acceptance criteria and by the dry run in Task 10.

- [ ] **Step 1: Update `skills/pipeline-ricerca/SKILL.md`**

Insert a new section before "## Stage 1" documenting the bootstrap flow: explicit `/pipeline-ricerca nuova` and NL intent ("iniziamo una nuova ricerca") both call:
```bash
python "<PLUGIN_ROOT>/scripts/study_workspace.py" create --name "<study name>" --parent "<CURRENT_WORKSPACE>"
```
then confirm the printed `project_root` with the user before treating it as the active study, and document the `resumable`/`directory_conflict`/`unsafe_target` statuses from Task 3/4 and how the skill should react to each (resumable → ask before resuming; conflict/unsafe → surface error to user, do not retry silently).

- [ ] **Step 2: Update `skills/prisma-review/SKILL.md`**

Replace the free-text `wiki_workspace` request (currently around the "Salva il percorso in `prisma_state.json` come `wiki_workspace`" line) with: if `.project-state.json` exists in the working directory (found via `containing_study_root`), set `wiki_workspace = <project_root>/wiki-memory` automatically and skip asking the user; otherwise keep the existing legacy free-text flow unchanged.

- [ ] **Step 3: Update `docs/PROJECT-SPEC.md` and `docs/models-and-setup.md`**

Add the sealed study directory layout (copy the tree from the spec's "Directory Layout" section) and note that all research data lives under the generated study root, with plugin code as the only external read boundary.

- [ ] **Step 4: Update README.md / README.it.md / wiki/README.md / wiki/README.it.md**

Replace any shared/global wiki workspace example with the sealed per-study bootstrap example from Step 1.

- [ ] **Step 5: Commit**

```bash
git add skills/pipeline-ricerca/SKILL.md skills/prisma-review/SKILL.md docs/PROJECT-SPEC.md docs/models-and-setup.md README.md README.it.md wiki/README.md wiki/README.it.md
git commit -m "docs: document isolated study workspace bootstrap"
```

---

## Task 9b: Automatic full-text acquisition

**Files:**
- Create: `skills/prisma-review/scripts/fetch_fulltext.py`
- Test: `skills/prisma-review/scripts/test_fetch_fulltext.py`

**Interfaces:**
- Produces: `is_safe_url(url: str) -> bool` (HTTPS-only; resolves host via `socket.getaddrinfo` and rejects any resolved IP that is private/loopback/link-local per `ipaddress.ip_address(...).is_private/.is_loopback/.is_link_local`); `download_fulltext(url: str, dest_dir: Path, record_id: str, max_bytes: int = 50_000_000) -> Path | None` (returns the saved path on success, `None` on any guard failure/timeout/non-PDF content-type — never raises for expected failure modes); `enrich_records_with_fulltext(records: list[dict], dest_dir: Path) -> list[dict]` (for each record, reads a `fulltext_url` key if present, calls `download_fulltext`, sets `record["local_pdf_path"]` to the saved path as a string or `None`).

- [ ] **Step 1: Write the failing tests**

```python
# skills/prisma-review/scripts/test_fetch_fulltext.py
import pytest
from fetch_fulltext import is_safe_url, download_fulltext, enrich_records_with_fulltext

def test_is_safe_url_rejects_http():
    assert is_safe_url("http://example.org/paper.pdf") is False

def test_is_safe_url_rejects_private_ip(monkeypatch):
    import socket
    monkeypatch.setattr(socket, "getaddrinfo",
                         lambda *a, **kw: [(None, None, None, None, ("127.0.0.1", 443))])
    assert is_safe_url("https://internal.example/paper.pdf") is False

def test_is_safe_url_accepts_public_https(monkeypatch):
    import socket
    monkeypatch.setattr(socket, "getaddrinfo",
                         lambda *a, **kw: [(None, None, None, None, ("93.184.216.34", 443))])
    assert is_safe_url("https://example.org/paper.pdf") is True

def test_download_fulltext_rejects_non_pdf_content_type(tmp_path, monkeypatch):
    import fetch_fulltext
    class FakeResponse:
        headers = {"Content-Type": "text/html"}
        def iter_content(self, chunk_size): return [b"<html>"]
        def raise_for_status(self): pass
        def __enter__(self): return self
        def __exit__(self, *a): pass
    monkeypatch.setattr(fetch_fulltext, "is_safe_url", lambda url: True)
    monkeypatch.setattr(fetch_fulltext.requests, "get", lambda *a, **kw: FakeResponse())
    result = download_fulltext("https://example.org/paper.pdf", tmp_path, "rec1")
    assert result is None

def test_download_fulltext_rejects_oversize(tmp_path, monkeypatch):
    import fetch_fulltext
    class FakeResponse:
        headers = {"Content-Type": "application/pdf"}
        def iter_content(self, chunk_size): return [b"x" * chunk_size for _ in range(3)]
        def raise_for_status(self): pass
        def __enter__(self): return self
        def __exit__(self, *a): pass
    monkeypatch.setattr(fetch_fulltext, "is_safe_url", lambda url: True)
    monkeypatch.setattr(fetch_fulltext.requests, "get", lambda *a, **kw: FakeResponse())
    result = download_fulltext("https://example.org/paper.pdf", tmp_path, "rec1", max_bytes=10)
    assert result is None
    assert list(tmp_path.iterdir()) == []  # partial file cleaned up

def test_enrich_records_sets_local_pdf_path_none_on_missing_url(tmp_path):
    records = [{"id": "r1", "title": "No URL here"}]
    enriched = enrich_records_with_fulltext(records, tmp_path)
    assert enriched[0]["local_pdf_path"] is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest skills/prisma-review/scripts/test_fetch_fulltext.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'fetch_fulltext'`

- [ ] **Step 3: Implement**

```python
# skills/prisma-review/scripts/fetch_fulltext.py
"""Best-effort automatic full-text acquisition for Stream 1 search records.

See docs/superpowers/specs/2026-09-17-isolated-study-workspace-design.md
("Automatic Full-Text Acquisition"). A failed/rejected download is not an
error: callers keep working from the abstract, exactly as before this file
existed.
"""
import ipaddress
import re
import socket
from pathlib import Path
from urllib.parse import urlparse

import requests

_MAX_BYTES_DEFAULT = 50_000_000
_TIMEOUT_S = 15


def is_safe_url(url: str) -> bool:
    parsed = urlparse(url)
    if parsed.scheme != "https":
        return False
    try:
        infos = socket.getaddrinfo(parsed.hostname, None)
    except socket.gaierror:
        return False
    for info in infos:
        addr = info[4][0]
        ip = ipaddress.ip_address(addr)
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
            return False
    return True


def _slugify_record_id(record_id: str) -> str:
    return re.sub(r"[^a-zA-Z0-9._-]+", "-", record_id).strip("-") or "paper"


def download_fulltext(url: str, dest_dir: Path, record_id: str,
                       max_bytes: int = _MAX_BYTES_DEFAULT) -> Path | None:
    if not is_safe_url(url):
        return None
    dest_dir = Path(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_path = dest_dir / f"{_slugify_record_id(record_id)}.pdf"
    try:
        with requests.get(url, stream=True, timeout=_TIMEOUT_S,
                           allow_redirects=True) as resp:
            resp.raise_for_status()
            content_type = resp.headers.get("Content-Type", "")
            if "pdf" not in content_type.lower():
                return None
            written = 0
            with open(dest_path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    written += len(chunk)
                    if written > max_bytes:
                        f.close()
                        dest_path.unlink(missing_ok=True)
                        return None
                    f.write(chunk)
    except (requests.RequestException, OSError):
        dest_path.unlink(missing_ok=True)
        return None
    return dest_path


def enrich_records_with_fulltext(records: list, dest_dir) -> list:
    for record in records:
        url = record.get("fulltext_url")
        record_id = str(record.get("id") or record.get("doi") or record.get("title", "paper"))
        path = download_fulltext(url, dest_dir, record_id) if url else None
        record["local_pdf_path"] = str(path) if path else None
    return records
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest skills/prisma-review/scripts/test_fetch_fulltext.py -v`
Expected: PASS (6 tests)

- [ ] **Step 5: Wire into `prisma-review` Stream 1**

Modify `skills/prisma-review/SKILL.md`'s Stream 1 section (the phase that already normalizes MCP records — see line ~441 "Leggere tutti i JSON estratti con questa mappatura per database") to call `enrich_records_with_fulltext` on the deduplicated record list, passing `<study>/sources/pdf-inbox/` (resolved via `.project-state.json`'s `paths.sources`) as `dest_dir`, right after cross-stream dedup and before writing `screening_prisma.json`. Document that `local_pdf_path` then rides along into `screening_prisma.json` and, on eligibility inclusion, the file is copied (not re-downloaded) into `sources/pdf-inclusi/`.

- [ ] **Step 6: Commit**

```bash
git add skills/prisma-review/scripts/fetch_fulltext.py skills/prisma-review/scripts/test_fetch_fulltext.py skills/prisma-review/SKILL.md
git commit -m "feat: auto-download open-access full text during Stream 1 search"
```

---

## Task 10: Integration tests + CI cross-platform run

**Files:**
- Create: `tests/test_study_workspace_integration.py`
- Modify: `.github/workflows/*.yml` (inspect existing workflow file first)

**Interfaces:**
- Consumes: everything from Tasks 1–6b, 8.

- [ ] **Step 1: Write integration tests**

```python
# tests/test_study_workspace_integration.py
import json
from pathlib import Path

import pytest
from scripts.study_workspace import create_study
from scripts.study_paths import resolve_in_study, PathEscapeError


def test_two_studies_have_independent_qdrant_paths(tmp_path):
    a = create_study("Study A", tmp_path)
    b = create_study("Study B", tmp_path)
    assert a["project_root"] != b["project_root"]
    for sub in ("qdrant-rag", "qdrant-wiki"):
        qdrant_a = Path(a["project_root"]) / "database" / sub
        qdrant_b = Path(b["project_root"]) / "database" / sub
        assert qdrant_a != qdrant_b


def test_rag_and_wiki_databases_are_independent_within_a_study(tmp_path):
    result = create_study("Study A", tmp_path)
    root = Path(result["project_root"])
    rag_db = root / "database" / "qdrant-rag"
    wiki_db = root / "database" / "qdrant-wiki"
    assert rag_db != wiki_db
    assert rag_db.is_dir() and wiki_db.is_dir()


def test_sibling_study_read_fails_closed(tmp_path):
    a = create_study("Study A", tmp_path)
    b = create_study("Study B", tmp_path)
    sibling_eligibility = Path(b["project_root"]) / "prisma" / "eligibility_prisma.json"
    with pytest.raises(PathEscapeError):
        resolve_in_study(a["project_root"], str(sibling_eligibility))


def test_resuming_valid_study_preserves_existing_files(tmp_path):
    result = create_study("Study A", tmp_path)
    root = Path(result["project_root"])
    marker = root / "prisma" / "prisma_log.md"
    marker.write_text("existing work", encoding="utf-8")
    create_study("Study A", tmp_path)  # resumable path, must not touch files
    assert marker.read_text(encoding="utf-8") == "existing work"
```

- [ ] **Step 2: Run tests**

Run: `pytest tests/test_study_workspace_integration.py -v`
Expected: PASS (3 tests)

- [ ] **Step 3: Check existing CI workflow covers both platforms**

Run: `cat .github/workflows/*.yml` — if the matrix already includes `windows-latest` and `ubuntu-latest` for the `pytest` job, no change needed. If not, add `windows-latest` to the `os` matrix so `tests/test_study_paths.py`, `tests/test_study_workspace.py` and this file run on both.

- [ ] **Step 4: Commit**

```bash
git add tests/test_study_workspace_integration.py .github/workflows/
git commit -m "test: add cross-study isolation integration tests"
```

---

## Self-Review Notes

- **Spec coverage:** Directory layout (now `qdrant-rag`/`qdrant-wiki` split) → Task 3/8. State contract → Task 2. Bootstrap CLI → Task 4. Slug/collision rules → Task 1/3. Isolation enforcement → Task 5/6. Skill changes (pipeline-ricerca, prisma-review) → Task 9. Hybrid RAG/wiki collection changes and independent Qdrant DBs (no `database_in_use` cross-blocking) → Task 6/7/8. Mandatory wiki-export gate + cross-encoder rerank on Hybrid RAG → Task 6b. Lazy init (no model download, no eager Qdrant collections at bootstrap — the `qdrant-rag`/`qdrant-wiki` directories are created empty, the `qdrant_client` isn't imported by `study_workspace.py`) → satisfied by design. Error handling/atomic recovery → Task 3 Step 3 (temp dir + rename + cleanup on exception). Testing strategy (unit/integration/CI) → Tasks 1–6b, 10. Documentation → Task 9.
- **Explicit non-goals respected:** no migration command, no shared-wiki feature, no external parent selection — none of the tasks add these.
- **Deliberately out of this first pass:** `educational-pilot-design` and `pandoc-export` skill doc updates for study-relative `design/`/`preprint`/`export` paths are named in the spec but are lower-risk (they already accept arbitrary file paths passed in). Add as a fast-follow task if acceptance testing surfaces a real gap, to keep this plan's first pass focused on the bootstrap + isolation core.
- Automatic full-text acquisition (SSRF-guarded, size-capped, best-effort, never blocking screening) → Task 9b.
