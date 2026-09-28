# Study-scoped Wiki Explorer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Start the wiki web explorer from a sealed study (`serve --project`) and show which study it serves.

**Architecture:** Two stdlib helpers in `scripts/study_paths.py` resolve a study's wiki and read its identity from `.project-state.json`. `wiki.py serve` uses the first; `/api/graph` exposes the second; the frontend shows it in the existing header subtitle.

**Tech Stack:** Python 3.11+ stdlib, FastAPI, vanilla JS (D3 frontend).

**Spec:** `docs/superpowers/specs/2026-09-28-study-scoped-wiki-explorer-design.md`

## Global Constraints

- One explorer process per study; never scan sibling directories.
- `--workspace` keeps working unchanged; exactly one of `--project` / `--workspace` for `serve`.
- `wiki_workspace` must be resolved with `resolve_in_study` (containment).
- `scripts/study_paths.py` stays stdlib-only.
- Python 3.11 grammar (CI matrix).
- Test command: `python -m pytest wiki/tests tests skills -q`

---

### Task 1: Study helpers in `scripts/study_paths.py`

**Files:**
- Modify: `scripts/study_paths.py`
- Test: `tests/test_study_paths.py`

**Interfaces:**
- Produces: `resolve_study_wiki(path) -> Path` (raises `StudyStateError` or `PathEscapeError`), `study_metadata(path) -> dict | None` returning `{"name", "slug", "id"}`, `class StudyStateError(Exception)`.

- [ ] **Step 1: Write the failing tests** (append to `tests/test_study_paths.py`)

```python
def _study(tmp_path, wiki="wiki-memory"):
    import json
    root = tmp_path / "my-study"
    (root / "wiki-memory").mkdir(parents=True)
    (root / "prisma").mkdir()
    (root / ".project-state.json").write_text(json.dumps({
        "study_name": "My Study", "study_slug": "my-study", "study_id": "uuid-1",
        "paths": {"wiki_workspace": wiki},
    }), encoding="utf-8")
    return root

def test_resolve_study_wiki_from_root_and_subdir(tmp_path):
    from scripts.study_paths import resolve_study_wiki
    root = _study(tmp_path)
    expected = (root / "wiki-memory").resolve()
    assert resolve_study_wiki(root) == expected
    assert resolve_study_wiki(root / "prisma") == expected

def test_resolve_study_wiki_requires_state(tmp_path):
    from scripts.study_paths import resolve_study_wiki, StudyStateError
    with pytest.raises(StudyStateError):
        resolve_study_wiki(tmp_path)

def test_resolve_study_wiki_rejects_escape(tmp_path):
    from scripts.study_paths import resolve_study_wiki, PathEscapeError
    root = _study(tmp_path, wiki="../elsewhere")
    with pytest.raises(PathEscapeError):
        resolve_study_wiki(root)

def test_study_metadata(tmp_path):
    from scripts.study_paths import study_metadata
    root = _study(tmp_path)
    assert study_metadata(root / "wiki-memory") == {"name": "My Study", "slug": "my-study", "id": "uuid-1"}
    assert study_metadata(tmp_path) is None
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/test_study_paths.py -q`
Expected: 4 FAIL with `ImportError: cannot import name 'resolve_study_wiki'`

- [ ] **Step 3: Implement** (append to `scripts/study_paths.py`; add `import json` at top)

```python
class StudyStateError(Exception):
    pass


def _read_state(root: Path) -> dict:
    try:
        return json.loads((root / STATE_FILENAME).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise StudyStateError(f"unreadable {STATE_FILENAME} in {root}: {exc}") from exc


def resolve_study_wiki(path) -> Path:
    """Wiki workspace of the sealed study containing `path` (root or any subdirectory)."""
    root = containing_study_root(path)
    if root is None:
        raise StudyStateError(f"no {STATE_FILENAME} found in {Path(path).resolve()} or its parents")
    rel = _read_state(root).get("paths", {}).get("wiki_workspace")
    if not rel:
        raise StudyStateError(f"{STATE_FILENAME} in {root} has no paths.wiki_workspace")
    wiki = resolve_in_study(root, rel)
    if not wiki.is_dir():
        raise StudyStateError(f"wiki workspace {wiki} does not exist")
    return wiki


def study_metadata(path) -> dict | None:
    """Name/slug/id of the sealed study containing `path`, or None outside a study."""
    root = containing_study_root(path)
    if root is None:
        return None
    try:
        state = _read_state(root)
    except StudyStateError:
        return None
    return {"name": state.get("study_name", ""), "slug": state.get("study_slug", ""),
            "id": state.get("study_id", "")}
```

- [ ] **Step 4: Run tests** — `python -m pytest tests/test_study_paths.py -q` → all PASS
- [ ] **Step 5: Commit** — `git commit -am "feat: resolve study wiki and metadata from project state"`

---

### Task 2: `serve --project` and study in `/api/graph`

**Files:**
- Modify: `wiki/scripts/wiki.py` (serve parser ~L160-164, `main()` ~L166-177)
- Modify: `wiki/scripts/wiki_server.py` (`api_graph` ~L115-119)
- Test: `wiki/tests/test_wiki_server.py`, `wiki/tests/test_wiki.py`

**Interfaces:**
- Consumes: `resolve_study_wiki`, `study_metadata`, `StudyStateError`, `PathEscapeError` from Task 1.
- Produces: `/api/graph` JSON key `study: {"name","slug","id"} | null`.

- [ ] **Step 1: Failing tests**

`wiki/tests/test_wiki_server.py`:

```python
def test_api_graph_has_null_study_outside_sealed_study(server_client):
    assert server_client.get("/api/graph").json()["study"] is None


def test_api_graph_reports_study(tmp_workspace, monkeypatch):
    import wiki_server, wiki_graph
    wiki_graph._CACHE = None
    monkeypatch.setattr(wiki_server, "study_metadata",
                        lambda ws: {"name": "My Study", "slug": "my-study", "id": "u1"})
    cfg = json.loads((tmp_workspace / "wiki.config.json").read_text())
    wiki_server.configure(str(tmp_workspace), cfg, no_auth=True)
    from fastapi.testclient import TestClient
    assert TestClient(wiki_server.app).get("/api/graph").json()["study"]["name"] == "My Study"
```

`wiki/tests/test_wiki.py` (CLI resolution; `cmd_serve` stubbed so no server starts):

```python
def test_serve_project_rejects_wiki_outside_study(tmp_workspace, monkeypatch):
    import json, wiki
    study = tmp_workspace.parent / "study-x"
    study.mkdir()
    (study / ".project-state.json").write_text(json.dumps(
        {"study_slug": "study-x", "paths": {"wiki_workspace": str(tmp_workspace)}}))
    monkeypatch.setattr(sys, "argv", ["wiki.py", "serve", "--project", str(study)])
    with pytest.raises(SystemExit) as exc:
        wiki.main()
    assert exc.value.code == 1


def test_serve_project_starts_on_study_wiki(tmp_path, monkeypatch):
    import json, wiki, wiki_workflows
    study = tmp_path / "study-y"
    ws = study / "wiki-memory"
    ws.mkdir(parents=True)
    (study / ".project-state.json").write_text(json.dumps(
        {"study_slug": "study-y", "paths": {"wiki_workspace": "wiki-memory"}}))
    src = Path(__file__).parent.parent / "wiki.config.json"
    cfg = json.loads(src.read_text(encoding="utf-8"))
    cfg["workspace"] = str(ws)
    (ws / "wiki.config.json").write_text(json.dumps(cfg))
    seen = {}
    monkeypatch.setattr(wiki_workflows, "cmd_serve", lambda args, cfg: seen.update(ws=args.workspace))
    monkeypatch.setattr(sys, "argv", ["wiki.py", "serve", "--project", str(ws)])
    wiki.main()
    assert Path(seen["ws"]) == ws.resolve()
```

- [ ] **Step 2: Run** — `python -m pytest wiki/tests/test_wiki_server.py wiki/tests/test_wiki.py -q -k "study or project"` → FAIL (`KeyError: 'study'`, argparse error on `--project`)

- [ ] **Step 3: Implement**

`wiki/scripts/wiki.py` — make the repo-root `scripts` package importable (after the imports):

```python
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
```

serve parser:

```python
    p_serve = sub.add_parser("serve")
    target = p_serve.add_mutually_exclusive_group(required=True)
    target.add_argument("--workspace")
    target.add_argument("--project", help="sealed study root or any directory inside it")
```

`main()` before `config_path = ...`:

```python
    if getattr(args, "project", None):
        from scripts.study_paths import resolve_study_wiki, StudyStateError, PathEscapeError
        try:
            args.workspace = str(resolve_study_wiki(args.project))
        except (StudyStateError, PathEscapeError) as e:
            error("invalid_study", str(e), recoverable=False)
            sys.exit(1)
```

`wiki/scripts/wiki_server.py` — near the other module imports:

```python
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
from scripts.study_paths import study_metadata  # noqa: E402
```

and in `api_graph`, after the `agent_name` line:

```python
    data["study"] = study_metadata(_workspace)
```

- [ ] **Step 4: Run** the same tests → PASS; then full suite → all PASS
- [ ] **Step 5: Commit** — `git commit -am "feat: serve --project opens the sealed study wiki and reports it"`

---

### Task 3: Frontend study label + docs

**Files:**
- Modify: `wiki/frontend/index.html` (`fetchGraph` ~L1219-1223, next to `updateAgentName`)
- Modify: `wiki/README.md`, `wiki/README.it.md` (section "Local web server" / "Server web locale"), `skills/pipeline-ricerca/SKILL.md`, `CHANGELOG.md` (1.4.1)
- Refresh: `wiki/docs/images/explorer-graph.png`, `explorer-page.png`

- [ ] **Step 1: Implement label** — after `updateAgentName`:

```js
function updateStudy(study) {
  if (!study || !study.name) return;
  const sub = document.getElementById('agent-subtitle');
  if (sub) { sub.textContent = 'Studio: ' + study.name; sub.title = study.slug; sub.style.display = 'block'; }
  document.title = study.name + ' — Wiki Memory';
}
```

and in `fetchGraph`, after the `agent_name` line: `if (fresh.study) updateStudy(fresh.study);`

- [ ] **Step 2: Docs** — in both wiki guides the start command becomes `wiki.py serve --project "<study>"` (study root or any subfolder; `--workspace` still accepted) with a note: one process and port per study. In `pipeline-ricerca`: "Esplora la memoria dello studio: `python "<PLUGIN_ROOT>/wiki/scripts/wiki.py" serve --project .`". CHANGELOG 1.4.1 EN/IT: "Added: `serve --project` and study name in the explorer header".
- [ ] **Step 3: Manual check** — start `serve --project <demo study>`, log in with Chrome, confirm subtitle "Studio: Spaced repetition review" and tab title; retake graph/page screenshots (1400px, PNG8).
- [ ] **Step 4: Full suite + `claude plugin validate --strict .claude-plugin/plugin.json`**
- [ ] **Step 5: Commit** — `git commit -am "feat: show study in wiki explorer; document serve --project"`
