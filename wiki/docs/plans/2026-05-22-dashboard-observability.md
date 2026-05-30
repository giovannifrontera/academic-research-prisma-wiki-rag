# Dashboard Observability Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a Stats tab to the wiki frontend that shows query frequency, page freshness, embedding coverage, lint status, and an auto-lint scheduler.

**Architecture:** Six tasks in dependency order — lint status file first (needed by stats endpoint), then backend endpoints, then the async scheduler, then the frontend tab. Each task is independently testable and committable.

**Tech Stack:** Python (asyncio, subprocess, pathlib, tempfile), FastAPI, pytest, vanilla JS + CSS (no new dependencies)

**Spec:** `docs/superpowers/specs/2026-05-22-dashboard-observability-design.md`

---

## File Map

| File | Action | Responsibility |
|------|--------|----------------|
| `scripts/wiki_workflows.py` | Modify `cmd_lint` | Write `.wiki-lint-status.json` atomically after lint |
| `scripts/wiki_server.py` | Add endpoints + task | `/api/stats`, `/api/lint`, `_auto_lint_task`, `_lint_busy` flag |
| `frontend/index.html` | Add Stats tab | `[Stats]` nav, `#stats-pane`, KPI cards, lint button |
| `tests/test_wiki_server.py` | Add 7 tests | All new backend behaviours |
| `tests/test_wiki_workflows.py` | Add 1 test | `cmd_lint` writes status file |

---

## Task 1: `cmd_lint` Writes `.wiki-lint-status.json`

**Files:**
- Modify: `scripts/wiki_workflows.py` — `cmd_lint` function (~line 202)
- Test: `tests/test_wiki_workflows.py` (new test)

### Step 1.1 — Write the failing test

In `tests/test_wiki_workflows.py`, add:

```python
def test_lint_status_written(tmp_workspace, monkeypatch):
    import wiki_lancedb, wiki_workflows

    class FakeTable:
        def to_pandas(self):
            import pandas as pd
            return pd.DataFrame({"path": []})
        def delete(self, expr):
            pass

    monkeypatch.setattr(wiki_workflows, "get_db", lambda path: object())
    monkeypatch.setattr(wiki_lancedb, "ensure_table", lambda db, table_name="wiki_pages": FakeTable())
    monkeypatch.setattr(wiki_workflows, "ensure_table", lambda db, table_name="wiki_pages": FakeTable())
    monkeypatch.setattr(wiki_workflows, "detect_renames", lambda db, fs_paths, workspace: [])

    cfg = json.loads((tmp_workspace / "wiki.config.json").read_text())

    class Args:
        workspace = str(tmp_workspace)
        full = True

    wiki_workflows.cmd_lint(Args(), cfg)

    status_path = tmp_workspace / ".wiki-lint-status.json"
    assert status_path.exists(), ".wiki-lint-status.json not created"
    data = json.loads(status_path.read_text())
    assert "last_run" in data
    assert "errors" in data
    assert "warnings" in data
    assert "detail" in data
    assert data["errors"] == 0
```

- [ ] **Step 1.1:** Aggiungere il test sopra a `tests/test_wiki_workflows.py`

### Step 1.2 — Verify test fails

```
pytest tests/test_wiki_workflows.py::test_lint_status_written -v
```

Expected: **FAILED** — `.wiki-lint-status.json` not created (AssertionError)

- [ ] **Step 1.2:** Eseguire e verificare che fallisce

### Step 1.3 — Implement: atomic write in `cmd_lint`

In `scripts/wiki_workflows.py`, sostituire il blocco `cmd_lint` (da `def cmd_lint(args, cfg):` fino a `ok(...)`) con:

```python
def cmd_lint(args, cfg):
    db = get_db(_lancedb_path(args.workspace, cfg))
    report = []

    if args.full:
        import re
        for md_file in _wiki_md_files(args.workspace):
            try:
                text = md_file.read_text(encoding="utf-8")
            except OSError:
                continue
            for link in re.findall(r'\[\[([^\]]+)\]\]', text):
                matches = list(Path(args.workspace).rglob(f"{link}.md"))
                if not matches:
                    report.append({"type": "broken_link", "file": str(md_file), "link": link})

        table = ensure_table(db)
        df = table.to_pandas()
        for path in df["path"].unique():
            full = os.path.join(args.workspace, path.replace("/", os.sep))
            if not os.path.exists(full):
                report.append({"type": "orphan_entry", "path": path})
                try:
                    safe = path.replace("'", "''")
                    table.delete(f"path = '{safe}'")
                except Exception:
                    pass

        fs_paths = {
            str(md_file)
            for root_name in _WIKI_ROOTS
            if (Path(args.workspace) / root_name).is_dir()
            for md_file in (Path(args.workspace) / root_name).rglob("*.md")
            if md_file.name not in EXCLUDED_NAMES
            and "raw" not in md_file.parts
            and ".archive" not in md_file.parts
        }
        renames = detect_renames(db, fs_paths, args.workspace)
        for r in renames:
            report.append({"type": "rename_detected", **r})

    errors = sum(1 for r in report if r["type"] in ("broken_link", "orphan_entry"))
    warnings = sum(1 for r in report if r["type"] == "rename_detected")
    orphans = sum(1 for r in report if r["type"] == "orphan_entry")
    detail_parts = []
    if orphans:
        detail_parts.append(f"{orphans} orphan vectors removed")
    if errors - orphans:
        detail_parts.append(f"{errors - orphans} broken links")
    if warnings:
        detail_parts.append(f"{warnings} renames detected")
    detail_str = ", ".join(detail_parts) if detail_parts else "no issues"

    status = {
        "last_run": datetime.now().isoformat(timespec="seconds"),
        "errors": errors,
        "warnings": warnings,
        "detail": detail_str,
    }
    status_path = Path(args.workspace) / ".wiki-lint-status.json"
    fd, tmp_p = tempfile.mkstemp(dir=args.workspace, prefix=".wiki-lint-status.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(status, f)
        os.replace(tmp_p, status_path)
    except Exception:
        try:
            os.unlink(tmp_p)
        except OSError:
            pass

    ok({"op": "lint", "full": args.full, "issues": report, "issues_count": len(report)})
```

- [ ] **Step 1.3:** Sostituire `cmd_lint` in `scripts/wiki_workflows.py` con il codice sopra

### Step 1.4 — Verify test passes

```
pytest tests/test_wiki_workflows.py::test_lint_status_written -v
```

Expected: **PASSED**

- [ ] **Step 1.4:** Verificare che il test passa

### Step 1.5 — Commit

```bash
git add scripts/wiki_workflows.py tests/test_wiki_workflows.py
git commit -m "feat: cmd_lint writes .wiki-lint-status.json atomically"
```

- [ ] **Step 1.5:** Commit

---

## Task 2: GET `/api/stats` — Struttura Base + Top Queried

**Files:**
- Modify: `scripts/wiki_server.py` — aggiungere `_lint_busy`, `_build_stats()`, endpoint `/api/stats`
- Test: `tests/test_wiki_server.py` — `test_api_stats_endpoint`, `test_api_stats_top_queried`

### Step 2.1 — Write failing tests

Aggiungere in `tests/test_wiki_server.py`:

```python
def test_api_stats_endpoint(server_client, tmp_workspace):
    resp = server_client.get("/api/stats")
    assert resp.status_code == 200
    data = resp.json()
    for key in ("summary", "top_queried", "stale_pages", "unembedded_pages",
                "lint_status", "auto_lint"):
        assert key in data, f"Missing key: {key}"
    assert "total_pages" in data["summary"]
    assert "total_chunks" in data["summary"]
    assert "embedding_coverage_pct" in data["summary"]
    assert "stale_pages_count" in data["summary"]
    assert isinstance(data["top_queried"], list)
    assert isinstance(data["stale_pages"], list)


def test_api_stats_top_queried(server_client, tmp_workspace):
    import json
    log_path = tmp_workspace / ".wiki-query-log.jsonl"
    entries = [
        {"ts": "2026-05-20T10:00:00", "q": "what is RAG?", "paths": ["wiki/concepts/rag.md"]},
        {"ts": "2026-05-20T10:01:00", "q": "explain RAG", "paths": ["wiki/concepts/rag.md"]},
        {"ts": "2026-05-20T10:02:00", "q": "openai models", "paths": ["wiki/entities/openai.md"]},
    ]
    log_path.write_text("\n".join(json.dumps(e) for e in entries), encoding="utf-8")

    resp = server_client.get("/api/stats")
    assert resp.status_code == 200
    top = resp.json()["top_queried"]
    assert len(top) >= 1
    paths_in_top = [item["path"] for item in top]
    assert "wiki/concepts/rag.md" in paths_in_top
    rag_item = next(i for i in top if i["path"] == "wiki/concepts/rag.md")
    assert rag_item["query_count"] == 2
```

- [ ] **Step 2.1:** Aggiungere i due test a `tests/test_wiki_server.py`

### Step 2.2 — Verify tests fail

```
pytest tests/test_wiki_server.py::test_api_stats_endpoint tests/test_wiki_server.py::test_api_stats_top_queried -v
```

Expected: **FAILED** — 404 o 405 (endpoint non esiste)

- [ ] **Step 2.2:** Verificare che i test falliscono

### Step 2.3 — Implement `/api/stats` + `_build_stats`

In `scripts/wiki_server.py`:

**a)** Aggiungere dopo `_session_days: int = 7`:
```python
_lint_busy: bool = False
```

**b)** Aggiungere i moduli a livello di modulo dopo `import wiki_graph`:
```python
try:
    import wiki_lancedb as _wiki_lancedb
    from wiki_index import EXCLUDED_NAMES as _EXCLUDED_NAMES
    _LANCEDB_IMPORT_OK = True
except ImportError:
    _LANCEDB_IMPORT_OK = False
    _EXCLUDED_NAMES: set = set()
```

**c)** Aggiungere dopo `api_page()`:

```python
def _build_stats() -> dict:
    from collections import Counter

    # top_queried: aggrega .wiki-query-log.jsonl
    log_path = Path(_workspace) / ".wiki-query-log.jsonl"
    path_counts: Counter = Counter()
    if log_path.exists():
        try:
            for line in log_path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    for p in entry.get("paths", []):
                        path_counts[p] += 1
                except json.JSONDecodeError:
                    pass
        except OSError:
            pass

    graph_data = wiki_graph.build_graph(_workspace, _cfg)
    node_title: dict = {
        n["path"]: n.get("title", n["path"]) for n in graph_data.get("nodes", [])
    }
    top_queried = [
        {"path": p, "title": node_title.get(p, p), "query_count": c}
        for p, c in path_counts.most_common(10)
    ]

    # stale_pages: nodi dove (now - last_modified) > staleness_days * 86400
    staleness_days = _cfg.get("thresholds", {}).get("staleness_days", 90)
    now_ts = datetime.now(timezone.utc).timestamp()
    stale_pages = []
    for node in graph_data.get("nodes", []):
        lm = node.get("last_modified")
        if lm and (now_ts - lm) > staleness_days * 86400:
            age_days = int((now_ts - lm) / 86400)
            stale_pages.append({
                "path": node["path"],
                "title": node.get("title", node["path"]),
                "age_days": age_days,
            })
    stale_pages.sort(key=lambda x: x["age_days"], reverse=True)

    # unembedded_pages: filesystem vs LanceDB
    unembedded_pages: list = []
    total_chunks = 0
    embedding_coverage_pct = 0.0
    if _LANCEDB_IMPORT_OK:
        try:
            lancedb_path = os.path.join(
                _workspace, _cfg.get("lancedb", {}).get("path", "memory/lancedb")
            )
            db = _wiki_lancedb.get_db(lancedb_path)
            table = _wiki_lancedb.ensure_table(db)
            df = table.to_pandas()
            total_chunks = len(df)
            embedded_paths = set(df["path"].unique())
            total_pages = len(graph_data.get("nodes", []))
            if total_pages > 0:
                embedding_coverage_pct = round(len(embedded_paths) / total_pages * 100, 1)
            for root_name in ("wiki", "wiki-works"):
                root = Path(_workspace) / root_name
                if not root.is_dir():
                    continue
                for md_file in root.rglob("*.md"):
                    if md_file.name in _EXCLUDED_NAMES:
                        continue
                    if "raw" in md_file.parts or ".archive" in md_file.parts:
                        continue
                    rel = os.path.relpath(str(md_file), _workspace).replace("\\", "/")
                    if rel not in embedded_paths:
                        unembedded_pages.append({"path": rel, "title": rel})
        except Exception:
            pass

    # lint_status: legge .wiki-lint-status.json
    lint_status = None
    lint_file = Path(_workspace) / ".wiki-lint-status.json"
    if lint_file.exists():
        try:
            lint_status = json.loads(lint_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            pass

    # auto_lint: config
    interval = _cfg.get("frontend", {}).get("lint_interval_hours")
    auto_lint: dict = {"enabled": bool(interval), "interval_hours": interval, "next_run_iso": None}

    total_pages = len(graph_data.get("nodes", []))
    return {
        "summary": {
            "total_pages": total_pages,
            "total_chunks": total_chunks,
            "embedding_coverage_pct": embedding_coverage_pct,
            "stale_pages_count": len(stale_pages),
        },
        "top_queried": top_queried,
        "stale_pages": stale_pages,
        "unembedded_pages": unembedded_pages[:10],
        "lint_status": lint_status,
        "auto_lint": auto_lint,
    }


@app.get("/api/stats")
async def api_stats():
    return JSONResponse(_build_stats())
```

- [ ] **Step 2.3:** Aggiungere il codice sopra a `scripts/wiki_server.py`

### Step 2.4 — Verify tests pass

```
pytest tests/test_wiki_server.py::test_api_stats_endpoint tests/test_wiki_server.py::test_api_stats_top_queried -v
```

Expected: **PASSED**

- [ ] **Step 2.4:** Verificare che i test passano

### Step 2.5 — Commit

```bash
git add scripts/wiki_server.py tests/test_wiki_server.py
git commit -m "feat: add GET /api/stats endpoint with top_queried aggregation"
```

- [ ] **Step 2.5:** Commit

---

## Task 3: GET `/api/stats` — Unembedded Pages + Lint Status (test)

**Files:**
- Test: `tests/test_wiki_server.py` — `test_api_stats_unembedded`, `test_api_stats_lint_status`

Il codice è già nell'endpoint del Task 2. Questi test verificano le sezioni rimanenti.

### Step 3.1 — Write tests

Aggiungere in `tests/test_wiki_server.py`:

```python
def test_api_stats_unembedded(server_client, tmp_workspace, monkeypatch):
    import pandas as pd
    import wiki_lancedb

    (tmp_workspace / "wiki" / "concepts" / "embedding.md").write_text(
        "---\ntitle: Embedding\n---\n\nContent.", encoding="utf-8"
    )

    class FakeTable:
        def to_pandas(self):
            # Solo rag.md e' embedded
            return pd.DataFrame({"path": ["wiki/concepts/rag.md"]})

    monkeypatch.setattr(wiki_lancedb, "get_db", lambda path: object())
    monkeypatch.setattr(wiki_lancedb, "ensure_table",
                        lambda db, table_name="wiki_pages": FakeTable())

    resp = server_client.get("/api/stats")
    assert resp.status_code == 200
    unembedded = resp.json()["unembedded_pages"]
    unembedded_paths = [u["path"] for u in unembedded]
    assert "wiki/concepts/embedding.md" in unembedded_paths
    assert "wiki/concepts/rag.md" not in unembedded_paths


def test_api_stats_lint_status(server_client, tmp_workspace):
    import json
    status_data = {
        "last_run": "2026-05-20T14:32:00",
        "errors": 0,
        "warnings": 2,
        "detail": "2 orphan vectors removed",
    }
    (tmp_workspace / ".wiki-lint-status.json").write_text(
        json.dumps(status_data), encoding="utf-8"
    )

    resp = server_client.get("/api/stats")
    assert resp.status_code == 200
    lint = resp.json()["lint_status"]
    assert lint is not None
    assert lint["last_run"] == "2026-05-20T14:32:00"
    assert lint["errors"] == 0
    assert lint["warnings"] == 2
```

- [ ] **Step 3.1:** Aggiungere i due test a `tests/test_wiki_server.py`

### Step 3.2 — Verify tests pass

```
pytest tests/test_wiki_server.py::test_api_stats_unembedded tests/test_wiki_server.py::test_api_stats_lint_status -v
```

Expected: **PASSED**

Se `test_api_stats_unembedded` fallisce perché `monkeypatch` non intercetta l'import locale dentro `_build_stats`, verificare che `_build_stats` usi `_wiki_lancedb.get_db(...)` (modulo importato a livello globale) e non `from wiki_lancedb import get_db` locale. Questo è già garantito dal codice del Task 2.

- [ ] **Step 3.2:** Verificare che i test passano

### Step 3.3 — Commit

```bash
git add tests/test_wiki_server.py
git commit -m "test: verify unembedded_pages and lint_status in /api/stats"
```

- [ ] **Step 3.3:** Commit

---

## Task 4: POST `/api/lint` con 409 Conflict Guard

**Files:**
- Modify: `scripts/wiki_server.py` — aggiungere endpoint `POST /api/lint`
- Test: `tests/test_wiki_server.py` — `test_api_lint_trigger`, `test_api_lint_conflict`

### Step 4.1 — Write failing tests

Aggiungere in `tests/test_wiki_server.py`:

```python
def test_api_lint_trigger(server_client, tmp_workspace, monkeypatch):
    import subprocess
    fake_result = subprocess.CompletedProcess(
        args=[], returncode=0,
        stdout="Lint complete. 0 errors, 0 warnings.", stderr=""
    )
    monkeypatch.setattr(subprocess, "run", lambda *a, **kw: fake_result)

    resp = server_client.post("/api/lint")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "output" in data


def test_api_lint_conflict(server_client, monkeypatch):
    import wiki_server
    wiki_server._lint_busy = True
    try:
        resp = server_client.post("/api/lint")
        assert resp.status_code == 409
    finally:
        wiki_server._lint_busy = False
```

- [ ] **Step 4.1:** Aggiungere i due test a `tests/test_wiki_server.py`

### Step 4.2 — Verify tests fail

```
pytest tests/test_wiki_server.py::test_api_lint_trigger tests/test_wiki_server.py::test_api_lint_conflict -v
```

Expected: **FAILED** — 405 Method Not Allowed

- [ ] **Step 4.2:** Verificare che i test falliscono

### Step 4.3 — Implement POST `/api/lint`

Aggiungere in `scripts/wiki_server.py` dopo `api_stats()`:

```python
@app.post("/api/lint")
async def api_lint():
    global _lint_busy
    if _lint_busy:
        return JSONResponse({"error": "lint already running"}, status_code=409)
    _lint_busy = True
    try:
        import subprocess
        wiki_py = Path(__file__).parent.parent / "wiki.py"
        result = subprocess.run(
            [sys.executable, str(wiki_py), "lint", "--workspace", _workspace, "--full"],
            capture_output=True, text=True, timeout=60,
        )
        output = (result.stdout + result.stderr).strip()
        status = "ok" if result.returncode == 0 else "error"
        return JSONResponse({"status": status, "output": output})
    except subprocess.TimeoutExpired:
        return JSONResponse({"status": "error", "output": "lint timed out"}, status_code=500)
    except Exception as e:
        return JSONResponse({"status": "error", "output": str(e)}, status_code=500)
    finally:
        _lint_busy = False
```

- [ ] **Step 4.3:** Aggiungere l'endpoint a `scripts/wiki_server.py`

### Step 4.4 — Verify tests pass

```
pytest tests/test_wiki_server.py::test_api_lint_trigger tests/test_wiki_server.py::test_api_lint_conflict -v
```

Expected: **PASSED**

- [ ] **Step 4.4:** Verificare che i test passano

### Step 4.5 — Commit

```bash
git add scripts/wiki_server.py tests/test_wiki_server.py
git commit -m "feat: add POST /api/lint with 409 conflict guard"
```

- [ ] **Step 4.5:** Commit

---

## Task 5: Auto-Lint Asyncio Scheduler

**Files:**
- Modify: `scripts/wiki_server.py` — aggiungere `_auto_lint_task`, avviare in `startup()`

### Step 5.1 — Add `_auto_lint_task` and update `startup()`

In `scripts/wiki_server.py`, aggiungere dopo `_query_log_watcher()`:

```python
async def _auto_lint_task():
    interval = _cfg.get("frontend", {}).get("lint_interval_hours")
    if not interval:
        return
    while True:
        await asyncio.sleep(float(interval) * 3600)
        import subprocess
        wiki_py = Path(__file__).parent.parent / "wiki.py"
        try:
            subprocess.run(
                [sys.executable, str(wiki_py), "lint", "--workspace", _workspace, "--full"],
                capture_output=True, text=True, timeout=120,
            )
        except Exception:
            pass
```

Sostituire `startup()` con:

```python
@app.on_event("startup")
async def startup():
    asyncio.create_task(_file_watcher())
    asyncio.create_task(_query_log_watcher())
    asyncio.create_task(_auto_lint_task())
```

- [ ] **Step 5.1:** Aggiungere `_auto_lint_task` e aggiornare `startup()`

### Step 5.2 — Verify `auto_lint` field presente in stats

```
pytest tests/test_wiki_server.py::test_api_stats_endpoint -v
```

Expected: **PASSED**

- [ ] **Step 5.2:** Verificare il test

### Step 5.3 — Commit

```bash
git add scripts/wiki_server.py
git commit -m "feat: auto-lint asyncio scheduler reads lint_interval_hours from config"
```

- [ ] **Step 5.3:** Commit

---

## Task 6: Frontend — Stats Tab

**Files:**
- Modify: `frontend/index.html` — aggiungere tab Stats, pane, KPI, liste, lint button, JS

### Step 6.1 — Add nav button and CSS

In `frontend/index.html`:

**a)** Nel blocco `<style>`, aggiungere:
```css
.tab-btn { background: none; border: 1px solid var(--border); color: var(--text-dim); padding: 4px 12px; border-radius: 4px; cursor: pointer; font-family: inherit; font-size: 13px; }
.tab-btn.active { border-color: var(--accent-blue); color: var(--accent-blue); }
.kpi-card { background: var(--panel-bg); border: 1px solid var(--border); border-radius: 8px; padding: 16px; text-align: center; }
.kpi-val { font-size: 28px; font-weight: 700; color: var(--text); font-family: 'DM Mono', monospace; }
.kpi-label { font-size: 12px; color: var(--text-dim); margin-top: 4px; text-transform: uppercase; letter-spacing: .05em; }
@media (max-width: 700px) { #kpi-grid { grid-template-columns: 1fr 1fr !important; } }
```

**b)** Nell'header, aggiungere `id="btn-graph"` e classe `active` al bottone Graph esistente, poi aggiungere il bottone Stats:
```html
<button id="btn-graph" class="tab-btn active" onclick="switchTab('graph')">Graph</button>
<button id="btn-stats" class="tab-btn" onclick="switchTab('stats')">Stats</button>
```

- [ ] **Step 6.1:** Aggiungere CSS e bottoni tab all'header

### Step 6.2 — Add `#stats-pane` HTML

Dopo il div principale del grafo (es. `#main-pane` o `#graph-pane`), aggiungere:

```html
<div id="stats-pane" style="display:none; padding:24px; overflow-y:auto; height:100%; box-sizing:border-box;">
  <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:20px;">
    <h2 style="margin:0; font-size:18px; color:var(--text);">Statistiche Wiki</h2>
    <button onclick="loadStats()" style="background:none;border:1px solid var(--border);color:var(--text-dim);padding:4px 12px;border-radius:4px;cursor:pointer;font-family:inherit;font-size:13px;">Aggiorna</button>
  </div>

  <div id="kpi-grid" style="display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:24px;">
    <div class="kpi-card"><div class="kpi-val" id="kpi-pages">—</div><div class="kpi-label">Pagine</div></div>
    <div class="kpi-card"><div class="kpi-val" id="kpi-chunks">—</div><div class="kpi-label">Chunk</div></div>
    <div class="kpi-card"><div class="kpi-val" id="kpi-coverage">—</div><div class="kpi-label">Copertura</div></div>
    <div class="kpi-card"><div class="kpi-val" id="kpi-stale">—</div><div class="kpi-label">Stale</div></div>
  </div>

  <div style="display:grid;grid-template-columns:1fr 1fr;gap:24px;margin-bottom:24px;">
    <div>
      <h3 style="font-size:13px;color:var(--text-dim);margin:0 0 8px;text-transform:uppercase;letter-spacing:.05em;">Più interrogate</h3>
      <ul id="top-queried-list" style="list-style:none;padding:0;margin:0;font-size:13px;"></ul>
    </div>
    <div>
      <h3 style="font-size:13px;color:var(--text-dim);margin:0 0 8px;text-transform:uppercase;letter-spacing:.05em;">Pagine stale (&gt;90gg)</h3>
      <ul id="stale-list" style="list-style:none;padding:0;margin:0;font-size:13px;"></ul>
    </div>
  </div>

  <div style="display:grid;grid-template-columns:1fr 1fr;gap:24px;">
    <div>
      <h3 style="font-size:13px;color:var(--text-dim);margin:0 0 8px;text-transform:uppercase;letter-spacing:.05em;">Senza embedding</h3>
      <ul id="unembedded-list" style="list-style:none;padding:0;margin:0;font-size:13px;"></ul>
    </div>
    <div>
      <h3 style="font-size:13px;color:var(--text-dim);margin:0 0 8px;text-transform:uppercase;letter-spacing:.05em;">Lint</h3>
      <div id="lint-status-block" style="font-size:13px;color:var(--text-dim);margin-bottom:12px;">—</div>
      <button id="btn-run-lint" onclick="runLint()" style="background:var(--accent-blue);border:none;color:#000;padding:6px 14px;border-radius:4px;cursor:pointer;font-family:inherit;font-size:13px;font-weight:600;">Esegui lint ora</button>
      <span id="lint-spinner" style="display:none;margin-left:8px;color:var(--text-dim);">...</span>
      <div id="auto-lint-info" style="margin-top:12px;font-size:12px;color:var(--text-dim);"></div>
    </div>
  </div>
</div>
```

- [ ] **Step 6.2:** Aggiungere `#stats-pane` HTML dopo il pane del grafo

### Step 6.3 — Add JavaScript

Aggiungere nello `<script>`:

```javascript
function switchTab(tab) {
  const graphPane = document.getElementById('graph-pane') || document.getElementById('main-pane');
  const statsPane = document.getElementById('stats-pane');
  const btnGraph = document.getElementById('btn-graph');
  const btnStats = document.getElementById('btn-stats');
  if (tab === 'stats') {
    if (graphPane) graphPane.style.display = 'none';
    statsPane.style.display = 'block';
    if (btnGraph) btnGraph.classList.remove('active');
    btnStats.classList.add('active');
    loadStats();
  } else {
    if (graphPane) graphPane.style.display = '';
    statsPane.style.display = 'none';
    if (btnGraph) btnGraph.classList.add('active');
    btnStats.classList.remove('active');
  }
}

function _buildListItem(leftText, rightText, rightColor) {
  const li = document.createElement('li');
  li.style.cssText = 'display:flex;justify-content:space-between;padding:4px 0;border-bottom:1px solid var(--border);';
  const left = document.createElement('span');
  left.textContent = leftText;
  left.style.color = 'var(--text)';
  li.appendChild(left);
  if (rightText !== undefined) {
    const right = document.createElement('span');
    right.textContent = rightText;
    right.style.color = rightColor || 'var(--text-dim)';
    li.appendChild(right);
  }
  return li;
}

function _renderEmptyItem(msg) {
  const li = document.createElement('li');
  li.style.color = 'var(--text-dim)';
  li.textContent = msg;
  return li;
}

async function loadStats() {
  try {
    const r = await fetch('/api/stats');
    if (!r.ok) return;
    const d = await r.json();

    document.getElementById('kpi-pages').textContent = d.summary.total_pages;
    document.getElementById('kpi-chunks').textContent = d.summary.total_chunks;
    document.getElementById('kpi-coverage').textContent = d.summary.embedding_coverage_pct + '%';
    document.getElementById('kpi-stale').textContent = d.summary.stale_pages_count;

    const tqEl = document.getElementById('top-queried-list');
    tqEl.replaceChildren();
    if (!d.top_queried.length) {
      tqEl.appendChild(_renderEmptyItem('nessuna query registrata'));
    } else {
      d.top_queried.forEach(item => {
        tqEl.appendChild(_buildListItem(item.title || item.path, item.query_count + 'q', 'var(--accent-blue)'));
      });
    }

    const staleEl = document.getElementById('stale-list');
    staleEl.replaceChildren();
    if (!d.stale_pages.length) {
      staleEl.appendChild(_renderEmptyItem('nessuna pagina stale'));
    } else {
      d.stale_pages.slice(0, 10).forEach(item => {
        staleEl.appendChild(_buildListItem(item.title || item.path, item.age_days + 'gg', '#f59e0b'));
      });
    }

    const unembEl = document.getElementById('unembedded-list');
    unembEl.replaceChildren();
    if (!d.unembedded_pages.length) {
      unembEl.appendChild(_renderEmptyItem('tutte le pagine sono indicizzate'));
    } else {
      d.unembedded_pages.forEach(item => {
        unembEl.appendChild(_buildListItem(item.path, undefined, undefined));
      });
    }

    const lintEl = document.getElementById('lint-status-block');
    if (d.lint_status) {
      const dt = new Date(d.lint_status.last_run).toLocaleString('it-IT');
      const parts = [dt, d.lint_status.errors + ' errori', d.lint_status.warnings + ' avvisi'];
      if (d.lint_status.detail) parts.push(d.lint_status.detail);
      lintEl.textContent = parts.join(' · ');
    } else {
      lintEl.textContent = 'Lint mai eseguito';
    }

    const alEl = document.getElementById('auto-lint-info');
    alEl.textContent = d.auto_lint.enabled
      ? 'Auto-lint: ogni ' + d.auto_lint.interval_hours + 'h'
      : 'Auto-lint: disabilitato (imposta frontend.lint_interval_hours in wiki.config.json)';
  } catch (e) {
    console.error('loadStats error', e);
  }
}

async function runLint() {
  const btn = document.getElementById('btn-run-lint');
  const spinner = document.getElementById('lint-spinner');
  btn.disabled = true;
  spinner.style.display = 'inline';
  try {
    const r = await fetch('/api/lint', { method: 'POST' });
    if (r.status === 409) {
      alert('Lint già in esecuzione, attendi.');
      return;
    }
    await loadStats();
  } catch (e) {
    console.error('runLint error', e);
  } finally {
    btn.disabled = false;
    spinner.style.display = 'none';
  }
}
```

- [ ] **Step 6.3:** Aggiungere `switchTab`, `loadStats`, `runLint` (e helper `_buildListItem`, `_renderEmptyItem`) nello script

### Step 6.4 — Manual smoke test

```bash
cd C:/Users/giova/ai-wiki-system
py scripts/wiki.py serve --workspace . --no-auth
```

Aprire `http://localhost:8000`:

- [ ] Il bottone `[Stats]` è visibile nell'header
- [ ] Click su `[Stats]` mostra il pannello con le 4 KPI card
- [ ] Click su `[Graph]` torna al grafo
- [ ] Il bottone `[Esegui lint ora]` mostra `...` durante l'esecuzione
- [ ] `[Aggiorna]` ricarica i dati
- [ ] Su finestra stretta (&lt;700px) le card si dispongono 2×2

- [ ] **Step 6.4:** Smoke test manuale

### Step 6.5 — Commit

```bash
git add frontend/index.html
git commit -m "feat: add Stats tab to frontend with KPI cards, query list, lint trigger"
```

- [ ] **Step 6.5:** Commit

---

## Task 7: Full Test Suite + Release v2.2.0

### Step 7.1 — Run full test suite

```
pytest tests/ -v --tb=short 2>&1 | tail -40
```

Expected: tutti i test passano, zero failure.

- [ ] **Step 7.1:** Eseguire la suite completa e verificare zero failure

### Step 7.2 — Bump version and update README

In `README.md` e `README.it.md`:
- Badge versione `v2.1.0` → `v2.2.0`
- Aggiungere sezione "Dashboard Osservabilità (v2.2)" con:
  - Tab `[Stats]` nel frontend
  - Endpoint `GET /api/stats` (summary, top_queried, stale, unembedded, lint)
  - Endpoint `POST /api/lint` con conflict guard
  - Config `frontend.lint_interval_hours` per auto-lint
- Aggiungere entry v2.2.0 al changelog

- [ ] **Step 7.2:** Aggiornare README.md e README.it.md

### Step 7.3 — Final commit, tag, push

```bash
git add README.md README.it.md
git commit -m "docs: v2.2.0 — dashboard observability (Stats tab, /api/stats, /api/lint)"
git tag v2.2.0
git push origin master --tags
```

- [ ] **Step 7.3:** Commit finale, tag v2.2.0, push

---

## Checklist spec coverage

| Requisito spec | Task |
|----------------|------|
| `cmd_lint` scrive `.wiki-lint-status.json` atomicamente | Task 1 |
| GET `/api/stats` — summary, top_queried, stale_pages | Task 2 |
| GET `/api/stats` — unembedded_pages, lint_status, auto_lint | Task 3 |
| POST `/api/lint` — subprocess, returncode check | Task 4 |
| POST `/api/lint` — 409 se busy | Task 4 |
| Auto-lint asyncio task, legge `lint_interval_hours` | Task 5 |
| Frontend `[Stats]` nav tab, `#stats-pane` | Task 6 |
| KPI cards (4), responsive CSS grid | Task 6 |
| Lista top_queried (cap 10) | Task 6 |
| Lista stale_pages | Task 6 |
| Lista unembedded_pages | Task 6 |
| Lint status block + bottone "Esegui lint ora" | Task 6 |
| Spinner durante lint, aggiornamento inline | Task 6 |
| Riga auto-lint info | Task 6 |
| `test_api_stats_endpoint` | Task 2 |
| `test_api_stats_top_queried` | Task 2 |
| `test_api_stats_unembedded` | Task 3 |
| `test_api_lint_trigger` | Task 4 |
| `test_api_lint_conflict` | Task 4 |
| `test_lint_status_written` | Task 1 |
| `test_api_stats_lint_status` | Task 3 |
