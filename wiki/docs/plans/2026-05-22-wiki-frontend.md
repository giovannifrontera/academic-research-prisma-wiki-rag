# Wiki Frontend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a read-only web frontend for navigating the AI wiki with an interactive D3.js force-directed graph, live WebSocket updates, and query hit animations — without touching any existing workflow.

**Architecture:** `wiki_graph.py` builds nodes + edges from filesystem and LanceDB; `wiki_server.py` is a FastAPI app with JWT cookie auth, REST endpoints, WebSocket broadcaster, and async file/query-log watchers; `frontend/index.html` is a zero-build SPA. `wiki.py` gains `serve` subcommand; `cmd_query` appends to `.wiki-query-log.jsonl`.

**Tech Stack:** FastAPI, uvicorn[standard], watchfiles, python-jose[cryptography], D3.js v7 (CDN), Marked.js (CDN), httpx (test only)

---

## File Map

| File | Action | Responsibility |
|------|--------|---------------|
| `requirements.txt` | Modify | Add 4 new server deps |
| `scripts/wiki_graph.py` | Create | Node/edge builder + graph cache |
| `scripts/wiki_server.py` | Create | FastAPI app, auth, REST, WebSocket, watchers |
| `frontend/index.html` | Create | SPA: D3 graph + page panel + WebSocket client |
| `scripts/wiki.py` | Modify | Add `serve` subcommand + dispatch |
| `scripts/wiki_workflows.py` | Modify | `cmd_serve` + query log append in `cmd_query` |
| `tests/test_wiki_graph.py` | Create | Unit tests for wiki_graph |
| `tests/test_wiki_server.py` | Create | API + auth tests |

---

## Task 1: Dependencies + Graph Node Builder

**Files:**
- Modify: `requirements.txt`
- Create: `scripts/wiki_graph.py`
- Create: `tests/test_wiki_graph.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_wiki_graph.py`:

```python
import json
import sys
import pytest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from wiki_graph import build_graph


def _make_page(path: Path, title: str, description: str = "", body: str = "Content.") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"---\ntitle: {title}\ndescription: {description}\n---\n\n{body}",
        encoding="utf-8",
    )


@pytest.fixture(autouse=True)
def reset_graph_cache():
    import wiki_graph
    wiki_graph._CACHE = None
    wiki_graph._CACHE_TIME = 0.0
    wiki_graph._DIRTY = False
    yield


def test_build_graph_nodes(tmp_workspace):
    _make_page(tmp_workspace / "wiki" / "entities" / "openai.md", "OpenAI", "AI company")
    _make_page(tmp_workspace / "wiki" / "concepts" / "rag.md", "RAG")

    cfg = json.loads((tmp_workspace / "wiki.config.json").read_text())
    result = build_graph(str(tmp_workspace), cfg)

    ids = {n["id"] for n in result["nodes"]}
    assert "wiki/entities/openai" in ids
    assert "wiki/concepts/rag" in ids
    assert result["edges"] == []


def test_build_graph_excludes_index_log(tmp_workspace):
    _make_page(tmp_workspace / "wiki" / "index.md", "Index")
    _make_page(tmp_workspace / "wiki" / "log.md", "Log")
    _make_page(tmp_workspace / "wiki" / "concepts" / "rag.md", "RAG")

    cfg = json.loads((tmp_workspace / "wiki.config.json").read_text())
    result = build_graph(str(tmp_workspace), cfg)

    ids = {n["id"] for n in result["nodes"]}
    assert "wiki/index" not in ids
    assert "wiki/log" not in ids
    assert "wiki/concepts/rag" in ids


def test_build_graph_excludes_raw_dirs(tmp_workspace):
    (tmp_workspace / "wiki-works" / "test" / "raw").mkdir(parents=True, exist_ok=True)
    _make_page(tmp_workspace / "wiki-works" / "test" / "raw" / "source.md", "Source")
    _make_page(tmp_workspace / "wiki" / "concepts" / "rag.md", "RAG")

    cfg = json.loads((tmp_workspace / "wiki.config.json").read_text())
    result = build_graph(str(tmp_workspace), cfg)

    ids = {n["id"] for n in result["nodes"]}
    assert not any("raw" in nid for nid in ids)
    assert "wiki/concepts/rag" in ids


def test_node_has_required_fields(tmp_workspace):
    _make_page(tmp_workspace / "wiki" / "entities" / "openai.md", "OpenAI", "AI company")

    cfg = json.loads((tmp_workspace / "wiki.config.json").read_text())
    result = build_graph(str(tmp_workspace), cfg)

    node = next(n for n in result["nodes"] if n["id"] == "wiki/entities/openai")
    for field in ("id", "path", "title", "category", "project", "description", "last_modified"):
        assert field in node, f"Missing field: {field}"
    assert node["title"] == "OpenAI"
    assert node["description"] == "AI company"
    assert node["category"] == "entities"
    assert node["project"] == "wiki"
```

- [ ] **Step 2: Run test to verify it fails**

```
cd C:\Users\giova\ai-wiki-system && pytest tests/test_wiki_graph.py -v
```
Expected: `ModuleNotFoundError: No module named 'wiki_graph'`

- [ ] **Step 3: Add dependencies to requirements.txt**

Replace `requirements.txt`:
```
lancedb>=0.6.0
sentence-transformers>=3.0.0
pyarrow>=14.0.0
pandas>=2.0.0
pytest>=8.0.0
pyyaml>=6.0
requests>=2.31.0
pdfplumber>=0.11.0
fastapi>=0.111.0
uvicorn[standard]>=0.29.0
watchfiles>=0.21.0
python-jose[cryptography]>=3.3.0
httpx>=0.27.0
```

- [ ] **Step 4: Install new dependencies**

```
pip install "fastapi>=0.111.0" "uvicorn[standard]>=0.29.0" "watchfiles>=0.21.0" "python-jose[cryptography]>=3.3.0" "httpx>=0.27.0"
```

- [ ] **Step 5: Create `scripts/wiki_graph.py`**

```python
"""Graph builder — read-only. Builds nodes + edges from filesystem and LanceDB."""

import re
import time
from pathlib import Path

_CACHE: dict | None = None
_CACHE_TIME: float = 0.0
_DIRTY: bool = False
_CACHE_TTL: float = 30.0

_EXCLUDED_FILES = {"index.md", "log.md"}
_EXCLUDED_DIRS = {"raw", ".archive"}

try:
    from wiki_lancedb import (
        get_db as _lancedb_get_db,
        ensure_table as _lancedb_ensure_table,
        query_similar as _lancedb_query_similar,
    )
    _LANCEDB_AVAILABLE = True
except ImportError:
    _LANCEDB_AVAILABLE = False


def mark_dirty() -> None:
    global _DIRTY
    _DIRTY = True


def _load_frontmatter(text: str) -> dict:
    if not text.startswith("---"):
        return {}
    lines = text.split("\n")
    end = -1
    for i, line in enumerate(lines[1:], 1):
        if line.strip() == "---":
            end = i
            break
    if end == -1:
        return {}
    fm: dict = {}
    for line in lines[1:end]:
        if ":" in line:
            key, _, value = line.partition(":")
            fm[key.strip()] = value.strip().strip('"').strip("'")
    return fm


def _node_id(path: Path, workspace: str) -> str:
    rel = path.relative_to(Path(workspace))
    return str(rel).replace("\\", "/").removesuffix(".md")


def _node_category(path: Path) -> str:
    for cat in ("entities", "concepts", "synthesis", "raw"):
        if cat in path.parts:
            return cat
    return "other"


def _node_project(path: Path, workspace: str) -> str:
    rel = path.relative_to(Path(workspace))
    parts = rel.parts
    if parts[0] == "wiki":
        return "wiki"
    if parts[0] == "wiki-works" and len(parts) > 1:
        return parts[1]
    return "wiki"


def _collect_md_files(workspace: str) -> list[Path]:
    ws = Path(workspace)
    files: list[Path] = []
    for root in (ws / "wiki", ws / "wiki-works"):
        if not root.exists():
            continue
        for p in root.rglob("*.md"):
            rel = p.relative_to(root)
            excluded = any(part in _EXCLUDED_DIRS for part in rel.parts[:-1])
            if not excluded and p.name not in _EXCLUDED_FILES:
                files.append(p)
    return files


def build_graph(workspace: str, cfg: dict) -> dict:
    global _CACHE, _CACHE_TIME, _DIRTY
    now = time.monotonic()
    if _CACHE is not None and not _DIRTY and (now - _CACHE_TIME) < _CACHE_TTL:
        return _CACHE

    files = _collect_md_files(workspace)
    nodes = []
    node_ids: set[str] = set()

    for p in files:
        text = p.read_text(encoding="utf-8")
        fm = _load_frontmatter(text)
        nid = _node_id(p, workspace)
        nodes.append({
            "id": nid,
            "path": str(p.relative_to(Path(workspace))).replace("\\", "/"),
            "title": fm.get("title", p.stem),
            "category": _node_category(p),
            "project": _node_project(p, workspace),
            "description": fm.get("description", ""),
            "last_modified": p.stat().st_mtime,
        })
        node_ids.add(nid)

    edges = _explicit_edges(files, node_ids, workspace)

    try:
        edges += _semantic_edges(workspace, cfg, files, node_ids)
    except Exception:
        pass

    _CACHE = {"nodes": nodes, "edges": edges}
    _CACHE_TIME = now
    _DIRTY = False
    return _CACHE


def _explicit_edges(files: list[Path], node_ids: set[str], workspace: str) -> list[dict]:
    edges: list[dict] = []
    seen: set[tuple] = set()
    for p in files:
        text = p.read_text(encoding="utf-8")
        src = _node_id(p, workspace)
        for m in re.finditer(r"\[\[([^\]]+)\]\]", text):
            slug = m.group(1).strip()
            target = next(
                (nid for nid in node_ids if nid.split("/")[-1] == slug),
                None,
            )
            if target and target != src:
                key = (src, target, "link")
                if key not in seen:
                    seen.add(key)
                    edges.append({"source": src, "target": target, "type": "link"})
    return edges


def _semantic_edges(workspace: str, cfg: dict, files: list[Path], node_ids: set[str]) -> list[dict]:
    import numpy as np
    if not _LANCEDB_AVAILABLE:
        return []

    db_path = str(Path(workspace) / cfg["lancedb"]["path"])
    db = _lancedb_get_db(db_path)
    table = _lancedb_ensure_table(db)
    df = table.to_pandas()
    if df.empty:
        return []

    edges: list[dict] = []
    seen: set[tuple] = set()

    for p in files:
        nid = _node_id(p, workspace)
        rel_path = str(p.relative_to(Path(workspace))).replace("\\", "/")
        page_rows = df[df["path"] == rel_path]
        if page_rows.empty:
            continue

        vecs = np.stack(page_rows["vector"].values)
        avg_vec = vecs.mean(axis=0).tolist()

        results = _lancedb_query_similar(db, avg_vec, k=6)
        for r in results:
            target_path = r.get("path", "")
            target_nid = target_path.replace("\\", "/").removesuffix(".md")
            if target_nid not in node_ids or target_nid == nid:
                continue
            distance = float(r.get("_distance", 1.0))
            similarity = round(1.0 - distance, 3)
            if similarity < 0.65:
                continue
            pair = tuple(sorted([nid, target_nid]))
            if pair in seen:
                continue
            seen.add(pair)
            edges.append({
                "source": nid, "target": target_nid,
                "type": "semantic", "weight": similarity,
            })

    return edges


def get_page_detail(workspace: str, path: str, cfg: dict) -> dict | None:
    ws = Path(workspace)
    full = (ws / path).resolve()
    if not full.is_relative_to(ws.resolve()) or not full.exists():
        return None

    text = full.read_text(encoding="utf-8")
    fm = _load_frontmatter(text)
    nid = _node_id(full, workspace)
    graph = build_graph(workspace, cfg)

    links_out = [e["target"] for e in graph["edges"] if e["source"] == nid and e["type"] == "link"]
    links_in = [e["source"] for e in graph["edges"] if e["target"] == nid and e["type"] == "link"]
    similar = sorted(
        [
            {"id": e["target"] if e["source"] == nid else e["source"],
             "weight": e.get("weight", 0.0)}
            for e in graph["edges"]
            if e["type"] == "semantic" and (e["source"] == nid or e["target"] == nid)
        ],
        key=lambda x: -x["weight"],
    )

    return {
        "content": text,
        "metadata": {**fm, "path": path, "last_modified": full.stat().st_mtime},
        "similar": similar,
        "links_out": links_out,
        "links_in": links_in,
    }
```

- [ ] **Step 6: Run tests**

```
pytest tests/test_wiki_graph.py -v
```
Expected: `4 passed`

- [ ] **Step 7: Commit**

```
git add requirements.txt scripts/wiki_graph.py tests/test_wiki_graph.py
git commit -m "feat: add wiki_graph node builder + server dependencies"
```

---

## Task 2: Explicit Link Edges + get_page_detail Tests

**Files:**
- Modify: `tests/test_wiki_graph.py`

- [ ] **Step 1: Append 4 tests to `tests/test_wiki_graph.py`**

```python
def test_build_graph_explicit_links(tmp_workspace):
    _make_page(
        tmp_workspace / "wiki" / "concepts" / "rag.md", "RAG",
        body="[[embedding]] is the core technique.",
    )
    _make_page(tmp_workspace / "wiki" / "concepts" / "embedding.md", "Embedding")

    cfg = json.loads((tmp_workspace / "wiki.config.json").read_text())
    result = build_graph(str(tmp_workspace), cfg)

    link_edges = [e for e in result["edges"] if e["type"] == "link"]
    assert len(link_edges) == 1
    assert link_edges[0]["source"] == "wiki/concepts/rag"
    assert link_edges[0]["target"] == "wiki/concepts/embedding"


def test_missing_link_ignored(tmp_workspace):
    _make_page(
        tmp_workspace / "wiki" / "concepts" / "rag.md", "RAG",
        body="[[nonexistent_page]] is referenced.",
    )

    cfg = json.loads((tmp_workspace / "wiki.config.json").read_text())
    result = build_graph(str(tmp_workspace), cfg)

    assert result["edges"] == []


def test_get_page_detail_links_out(tmp_workspace):
    from wiki_graph import get_page_detail
    _make_page(
        tmp_workspace / "wiki" / "concepts" / "rag.md", "RAG",
        description="Retrieval-Augmented Generation",
        body="[[embedding]] is the core technique.",
    )
    _make_page(tmp_workspace / "wiki" / "concepts" / "embedding.md", "Embedding")

    cfg = json.loads((tmp_workspace / "wiki.config.json").read_text())
    detail = get_page_detail(str(tmp_workspace), "wiki/concepts/rag.md", cfg)

    assert detail is not None
    assert "RAG" in detail["content"]
    assert detail["metadata"]["title"] == "RAG"
    assert "wiki/concepts/embedding" in detail["links_out"]
    assert detail["links_in"] == []


def test_get_page_detail_links_in(tmp_workspace):
    from wiki_graph import get_page_detail
    _make_page(
        tmp_workspace / "wiki" / "concepts" / "rag.md", "RAG",
        body="[[embedding]] is the core technique.",
    )
    _make_page(tmp_workspace / "wiki" / "concepts" / "embedding.md", "Embedding")

    cfg = json.loads((tmp_workspace / "wiki.config.json").read_text())
    detail = get_page_detail(str(tmp_workspace), "wiki/concepts/embedding.md", cfg)

    assert "wiki/concepts/rag" in detail["links_in"]
    assert detail["links_out"] == []
```

- [ ] **Step 2: Run tests**

```
pytest tests/test_wiki_graph.py -v
```
Expected: `8 passed`

- [ ] **Step 3: Commit**

```
git add tests/test_wiki_graph.py
git commit -m "test: explicit link edges and get_page_detail coverage"
```

---

## Task 3: Semantic Edges + Graph Cache Tests

**Files:**
- Modify: `tests/test_wiki_graph.py`

- [ ] **Step 1: Append 3 tests**

```python
def test_build_graph_semantic_edges(tmp_workspace, monkeypatch):
    import numpy as np
    import pandas as pd
    import wiki_graph

    _make_page(tmp_workspace / "wiki" / "concepts" / "rag.md", "RAG")
    _make_page(tmp_workspace / "wiki" / "concepts" / "transformer.md", "Transformer")

    fake_df = pd.DataFrame([
        {"path": "wiki/concepts/rag.md", "chunk_id": 0,
         "vector": np.ones(1024).tolist(),
         "chunk_text": "rag", "content_hash": "a", "page_hash": "a", "last_embedded": 0.0},
        {"path": "wiki/concepts/transformer.md", "chunk_id": 0,
         "vector": np.ones(1024).tolist(),
         "chunk_text": "transformer", "content_hash": "b", "page_hash": "b", "last_embedded": 0.0},
    ])

    class FakeTable:
        def to_pandas(self):
            return fake_df

    monkeypatch.setattr(wiki_graph, "_LANCEDB_AVAILABLE", True)
    monkeypatch.setattr(wiki_graph, "_lancedb_get_db", lambda path: object())
    monkeypatch.setattr(wiki_graph, "_lancedb_ensure_table", lambda db, table_name="wiki_pages": FakeTable())
    monkeypatch.setattr(wiki_graph, "_lancedb_query_similar", lambda db, vec, k=5, path_prefix=None: [
        {"path": "wiki/concepts/transformer.md", "_distance": 0.1,
         "chunk_id": 0, "chunk_text": "transformer"},
    ])

    cfg = json.loads((tmp_workspace / "wiki.config.json").read_text())
    result = build_graph(str(tmp_workspace), cfg)

    sem_edges = [e for e in result["edges"] if e["type"] == "semantic"]
    assert len(sem_edges) == 1
    pair = {sem_edges[0]["source"], sem_edges[0]["target"]}
    assert pair == {"wiki/concepts/rag", "wiki/concepts/transformer"}
    assert sem_edges[0]["weight"] == pytest.approx(0.9, abs=0.01)


def test_graph_cache_reused(tmp_workspace):
    _make_page(tmp_workspace / "wiki" / "concepts" / "rag.md", "RAG")
    cfg = json.loads((tmp_workspace / "wiki.config.json").read_text())
    r1 = build_graph(str(tmp_workspace), cfg)
    r2 = build_graph(str(tmp_workspace), cfg)
    assert r1 is r2


def test_mark_dirty_forces_rebuild(tmp_workspace):
    import wiki_graph
    _make_page(tmp_workspace / "wiki" / "concepts" / "rag.md", "RAG")
    cfg = json.loads((tmp_workspace / "wiki.config.json").read_text())
    r1 = build_graph(str(tmp_workspace), cfg)

    _make_page(tmp_workspace / "wiki" / "concepts" / "embedding.md", "Embedding")
    wiki_graph.mark_dirty()
    r2 = build_graph(str(tmp_workspace), cfg)

    assert r1 is not r2
    ids = {n["id"] for n in r2["nodes"]}
    assert "wiki/concepts/embedding" in ids
```

- [ ] **Step 2: Run tests**

```
pytest tests/test_wiki_graph.py -v
```
Expected: `11 passed`

- [ ] **Step 3: Commit**

```
git add tests/test_wiki_graph.py
git commit -m "test: semantic edges + graph cache coverage"
```

---

## Task 4: wiki.py serve subcommand + cmd_query log + cmd_serve

**Files:**
- Modify: `scripts/wiki.py`
- Modify: `scripts/wiki_workflows.py`
- Modify: `tests/test_wiki_graph.py`

- [ ] **Step 1: Write failing test for query log**

Append to `tests/test_wiki_graph.py`:

```python
def test_query_log_written(tmp_workspace, monkeypatch):
    import wiki_workflows
    import wiki_lancedb
    import wiki_embed

    def fake_query_similar(db, vector, k=5, path_prefix=None):
        return [{"path": "wiki/concepts/rag.md", "chunk_id": 0,
                 "_distance": 0.1, "chunk_text": "rag chunk"}]

    class FakeModel:
        def encode(self, text, normalize_embeddings=True):
            import numpy as np
            return np.zeros(1024)

    monkeypatch.setattr(wiki_lancedb, "query_similar", fake_query_similar)
    monkeypatch.setattr(wiki_lancedb, "get_db", lambda path: object())
    monkeypatch.setattr(wiki_embed, "_load_model", lambda name: (FakeModel(), None))

    cfg = json.loads((tmp_workspace / "wiki.config.json").read_text())

    class Args:
        workspace = str(tmp_workspace)
        q = "what is RAG?"
        k = 5

    wiki_workflows.cmd_query(Args(), cfg)

    log_path = tmp_workspace / ".wiki-query-log.jsonl"
    assert log_path.exists(), ".wiki-query-log.jsonl not created"
    entry = json.loads(log_path.read_text().strip())
    assert entry["q"] == "what is RAG?"
    assert "wiki/concepts/rag.md" in entry["paths"]
    assert "ts" in entry
```

- [ ] **Step 2: Run test to verify it fails**

```
pytest tests/test_wiki_graph.py::test_query_log_written -v
```
Expected: FAIL — `cmd_query` does not write the log yet.

- [ ] **Step 3: Modify `cmd_query` in `scripts/wiki_workflows.py`**

Find and replace the `cmd_query` function:

```python
def cmd_query(args, cfg):
    import json as _json
    from datetime import datetime

    db = get_db(_lancedb_path(args.workspace, cfg))
    model, _ = _load_model(cfg["lancedb"]["embedding_model"])
    vector = model.encode(args.q, normalize_embeddings=True).tolist()

    results = query_similar(db, vector, k=args.k)

    paths = list({r["path"] for r in results})
    log_path = Path(args.workspace) / ".wiki-query-log.jsonl"
    entry = {"ts": datetime.now().isoformat(), "q": args.q, "paths": paths}
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(_json.dumps(entry) + "\n")

    ok({"op": "query", "results": [
        {"path": r["path"], "chunk_id": r["chunk_id"],
         "score": float(r.get("_distance", 0)), "excerpt": r["chunk_text"][:200]}
        for r in results
    ]})
```

- [ ] **Step 4: Add `serve` parser to `scripts/wiki.py`**

In `main()`, after `p_ingest_pdf.add_argument("--file", ...)`, before `args = parser.parse_args()`:

```python
    p_serve = sub.add_parser("serve")
    p_serve.add_argument("--workspace", required=True)
    p_serve.add_argument("--host", default="127.0.0.1")
    p_serve.add_argument("--port", type=int, default=7331)
    p_serve.add_argument("--no-auth", action="store_true")
```

In `dispatch()`, update the import and commands dict:

```python
def dispatch(args, cfg):
    from wiki_workflows import (cmd_ingest, cmd_query, cmd_lint, cmd_index,
                                cmd_rebuild, cmd_session_update,
                                cmd_scan_inbox, cmd_ingest_pdf, cmd_serve)
    commands = {
        "ingest": cmd_ingest,
        "query": cmd_query,
        "lint": cmd_lint,
        "index": cmd_index,
        "rebuild": cmd_rebuild,
        "session-update": cmd_session_update,
        "scan-inbox": cmd_scan_inbox,
        "ingest-pdf": cmd_ingest_pdf,
        "serve": cmd_serve,
    }
    commands[args.command](args, cfg)
```

- [ ] **Step 5: Add `cmd_serve` to end of `scripts/wiki_workflows.py`**

```python
def cmd_serve(args, cfg):
    import uvicorn
    import wiki_server
    no_auth = getattr(args, "no_auth", False)
    wiki_server.configure(args.workspace, cfg, no_auth)
    uvicorn.run("wiki_server:app", host=args.host, port=args.port, reload=False)
```

- [ ] **Step 6: Run tests**

```
pytest tests/test_wiki_graph.py -v
```
Expected: `12 passed`

- [ ] **Step 7: Commit**

```
git add scripts/wiki.py scripts/wiki_workflows.py tests/test_wiki_graph.py
git commit -m "feat: serve subcommand + query log append in cmd_query"
```

---

## Task 5: wiki_server.py — Auth + REST Endpoints

**Files:**
- Create: `scripts/wiki_server.py`
- Create: `tests/test_wiki_server.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_wiki_server.py`:

```python
import json
import sys
import pytest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))


def _make_page(path: Path, title: str, body: str = "Content.") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"---\ntitle: {title}\n---\n\n{body}", encoding="utf-8")


@pytest.fixture
def server_client(tmp_workspace):
    import wiki_graph
    wiki_graph._CACHE = None
    wiki_graph._CACHE_TIME = 0.0
    wiki_graph._DIRTY = False
    _make_page(tmp_workspace / "wiki" / "concepts" / "rag.md", "RAG")

    import wiki_server
    cfg = json.loads((tmp_workspace / "wiki.config.json").read_text())
    wiki_server.configure(str(tmp_workspace), cfg, no_auth=True)

    from fastapi.testclient import TestClient
    return TestClient(wiki_server.app)


@pytest.fixture
def auth_client(tmp_workspace):
    import wiki_graph
    wiki_graph._CACHE = None

    import wiki_server
    cfg = json.loads((tmp_workspace / "wiki.config.json").read_text())
    cfg.setdefault("frontend", {})["password"] = "testpass"
    wiki_server.configure(str(tmp_workspace), cfg, no_auth=False)

    from fastapi.testclient import TestClient
    return TestClient(wiki_server.app, raise_server_exceptions=True)


def test_api_graph_endpoint(server_client):
    resp = server_client.get("/api/graph")
    assert resp.status_code == 200
    data = resp.json()
    assert "nodes" in data
    assert "edges" in data
    assert any(n["id"] == "wiki/concepts/rag" for n in data["nodes"])


def test_api_page_endpoint(server_client, tmp_workspace):
    resp = server_client.get("/api/page/wiki/concepts/rag.md")
    assert resp.status_code == 200
    data = resp.json()
    assert "content" in data
    assert "RAG" in data["content"]
    assert "metadata" in data


def test_api_page_not_found(server_client):
    resp = server_client.get("/api/page/wiki/concepts/nonexistent.md")
    assert resp.status_code == 404


def test_auth_required(auth_client):
    resp = auth_client.get("/api/graph", cookies={})
    assert resp.status_code == 401


def test_auth_login(auth_client):
    resp = auth_client.post("/auth/login", json={"password": "testpass"})
    assert resp.status_code == 200
    assert "wiki_session" in resp.cookies


def test_auth_wrong_password(auth_client):
    resp = auth_client.post("/auth/login", json={"password": "wrongpass"})
    assert resp.status_code == 401


def test_auth_cookie_grants_access(auth_client):
    login = auth_client.post("/auth/login", json={"password": "testpass"})
    assert login.status_code == 200
    token = login.cookies["wiki_session"]
    resp = auth_client.get("/api/graph", cookies={"wiki_session": token})
    assert resp.status_code == 200


def test_auth_logout(auth_client):
    login = auth_client.post("/auth/login", json={"password": "testpass"})
    token = login.cookies["wiki_session"]
    logout = auth_client.post("/auth/logout", cookies={"wiki_session": token})
    assert logout.status_code == 200
```

- [ ] **Step 2: Run tests to verify they fail**

```
pytest tests/test_wiki_server.py -v
```
Expected: `ModuleNotFoundError: No module named 'wiki_server'`

- [ ] **Step 3: Create `scripts/wiki_server.py`**

```python
"""Wiki frontend server — FastAPI + WebSocket + file watcher + JWT auth."""

import asyncio
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Set

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse

_workspace: str = ""
_cfg: dict = {}
_no_auth: bool = False
_secret_key: str = ""
_session_days: int = 7

_ws_clients: Set[WebSocket] = set()

app = FastAPI(docs_url=None, redoc_url=None)


def configure(workspace: str, cfg: dict, no_auth: bool) -> None:
    global _workspace, _cfg, _no_auth, _secret_key, _session_days
    _workspace = workspace
    _cfg = cfg
    _no_auth = no_auth
    frontend = cfg.get("frontend", {})
    _secret_key = os.environ.get("WIKI_PASSWORD") or frontend.get("password", "changeme")
    _session_days = int(frontend.get("session_days", 7))


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if _no_auth:
            return await call_next(request)
        if request.url.path.startswith("/auth/"):
            return await call_next(request)
        token = request.cookies.get("wiki_session")
        if not token or not _verify_token(token):
            return JSONResponse({"error": "unauthorized"}, status_code=401)
        return await call_next(request)


app.add_middleware(AuthMiddleware)


def _make_token() -> str:
    from jose import jwt
    exp = datetime.now(timezone.utc) + timedelta(days=_session_days)
    return jwt.encode({"exp": exp}, _secret_key, algorithm="HS256")


def _verify_token(token: str) -> bool:
    from jose import jwt, JWTError
    try:
        jwt.decode(token, _secret_key, algorithms=["HS256"])
        return True
    except JWTError:
        return False


@app.post("/auth/login")
async def login(request: Request):
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "invalid_body"}, status_code=400)
    if body.get("password") != _secret_key:
        return JSONResponse({"error": "unauthorized"}, status_code=401)
    token = _make_token()
    resp = JSONResponse({"status": "ok"})
    resp.set_cookie(
        "wiki_session", token, httponly=False, samesite="lax",
        max_age=_session_days * 86400,
    )
    return resp


@app.post("/auth/logout")
async def logout():
    resp = JSONResponse({"status": "ok"})
    resp.delete_cookie("wiki_session")
    return resp


@app.get("/api/graph")
async def api_graph():
    import sys
    from pathlib import Path as _P
    sys.path.insert(0, str(_P(__file__).parent))
    import wiki_graph
    data = wiki_graph.build_graph(_workspace, _cfg)
    return JSONResponse(data)


@app.get("/api/page/{path:path}")
async def api_page(path: str):
    import sys
    from pathlib import Path as _P
    sys.path.insert(0, str(_P(__file__).parent))
    import wiki_graph
    detail = wiki_graph.get_page_detail(_workspace, path, _cfg)
    if detail is None:
        return JSONResponse({"error": "not_found"}, status_code=404)
    return JSONResponse(detail)


@app.get("/")
async def index():
    html_path = Path(__file__).parent.parent / "frontend" / "index.html"
    if html_path.exists():
        return FileResponse(str(html_path))
    return HTMLResponse("<h1>Frontend not found</h1>", status_code=404)


@app.websocket("/ws")
async def ws_endpoint(websocket: WebSocket):
    if not _no_auth:
        token = websocket.cookies.get("wiki_session")
        if not token or not _verify_token(token):
            await websocket.close(code=1008)
            return
    await websocket.accept()
    _ws_clients.add(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        _ws_clients.discard(websocket)


async def _broadcast(message: dict) -> None:
    dead: Set[WebSocket] = set()
    payload = json.dumps(message)
    for ws in list(_ws_clients):
        try:
            await ws.send_text(payload)
        except Exception:
            dead.add(ws)
    _ws_clients.difference_update(dead)


@app.on_event("startup")
async def startup():
    asyncio.create_task(_file_watcher())
    asyncio.create_task(_query_log_watcher())


async def _file_watcher():
    try:
        from watchfiles import awatch
    except ImportError:
        return
    import wiki_graph
    ws = Path(_workspace)
    watch_dirs = [str(d) for d in (ws / "wiki", ws / "wiki-works") if d.exists()]
    if not watch_dirs:
        return
    async for _changes in awatch(*watch_dirs):
        wiki_graph.mark_dirty()
        await _broadcast({"type": "graph_update"})


async def _query_log_watcher():
    log_path = Path(_workspace) / ".wiki-query-log.jsonl"
    pos = log_path.stat().st_size if log_path.exists() else 0
    while True:
        await asyncio.sleep(0.5)
        if not log_path.exists():
            continue
        size = log_path.stat().st_size
        if size <= pos:
            continue
        with open(log_path, encoding="utf-8") as f:
            f.seek(pos)
            new_content = f.read()
        pos = size
        for line in new_content.splitlines():
            if not line.strip():
                continue
            try:
                entry = json.loads(line)
                paths = entry.get("paths", [])
                if paths:
                    await _broadcast({"type": "query_hit", "paths": paths})
            except json.JSONDecodeError:
                pass
```

- [ ] **Step 4: Run tests**

```
pytest tests/test_wiki_server.py -v
```
Expected: `8 passed`. If `test_auth_login` fails, verify `_secret_key` is set from `cfg["frontend"]["password"]` in `configure()` and that the `login` endpoint compares against `_secret_key`.

- [ ] **Step 5: Run full test suite**

```
pytest -v
```
Expected: all existing tests still pass.

- [ ] **Step 6: Commit**

```
git add scripts/wiki_server.py tests/test_wiki_server.py
git commit -m "feat: wiki_server FastAPI core with auth and REST endpoints"
```

---

## Task 6: WebSocket Tests

**Files:**
- Modify: `tests/test_wiki_server.py`

- [ ] **Step 1: Append WebSocket tests**

```python
def test_websocket_connects_no_auth(server_client):
    import wiki_server
    with server_client.websocket_connect("/ws") as ws:
        assert len(wiki_server._ws_clients) == 1


def test_websocket_auth_rejected_without_cookie(auth_client):
    try:
        with auth_client.websocket_connect("/ws", cookies={}) as ws:
            ws.receive_text()
        rejected = False
    except Exception:
        rejected = True
    assert rejected, "Expected WebSocket to be rejected without valid cookie"
```

- [ ] **Step 2: Run tests**

```
pytest tests/test_wiki_server.py -v
```
Expected: `10 passed`

- [ ] **Step 3: Commit**

```
git add tests/test_wiki_server.py
git commit -m "test: WebSocket connection coverage"
```

---

## Task 7: frontend/index.html — Complete SPA

**Files:**
- Create: `frontend/index.html`

No automated tests — manual visual verification.

- [ ] **Step 1: Create `frontend/` directory**

```
mkdir C:\Users\giova\ai-wiki-system\frontend
```

- [ ] **Step 2: Create `frontend/index.html`**

The file uses D3.js v7 and Marked.js from CDN. Dynamic HTML content (node IDs, page titles) is always escaped with `esc()` before insertion to prevent XSS. Markdown body is rendered via `marked.parse()` into a sandboxed container which is the expected behavior for a personal wiki viewer.

```html
<!DOCTYPE html>
<html lang="it">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>AI Wiki Memory</title>
<script src="https://cdn.jsdelivr.net/npm/d3@7/dist/d3.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/marked@9/marked.min.js"></script>
<style>
:root {
  --bg: #0d1117; --surface: #161b22; --border: #30363d;
  --text: #e6edf3; --muted: #8b949e; --accent: #58a6ff;
  --header-h: 50px;
}
* { box-sizing: border-box; margin: 0; padding: 0; }
body { background: var(--bg); color: var(--text);
       font-family: system-ui,-apple-system,sans-serif;
       height: 100vh; display: flex; flex-direction: column; overflow: hidden; }

#header { height: var(--header-h); display: flex; align-items: center; gap: 12px;
           padding: 0 16px; background: var(--surface);
           border-bottom: 1px solid var(--border); flex-shrink: 0; }
.logo { font-weight: 700; font-size: 15px; color: var(--accent); white-space: nowrap; }
#project-tabs { display: flex; gap: 6px; overflow-x: auto; flex-shrink: 0; }
.tab { padding: 4px 12px; border-radius: 20px; font-size: 12px; cursor: pointer;
        border: 1px solid var(--border); background: transparent; color: var(--muted);
        white-space: nowrap; transition: all 0.15s; }
.tab.active { background: var(--accent); border-color: var(--accent); color: #000; }
#search { margin-left: auto; background: var(--bg); border: 1px solid var(--border);
           color: var(--text); padding: 5px 10px; border-radius: 6px;
           font-size: 13px; width: 180px; }
#search:focus { outline: none; border-color: var(--accent); }
#ws-dot { width: 8px; height: 8px; border-radius: 50%; background: #555; flex-shrink: 0; }
#ws-dot.on { background: #3fb950; }

#main { display: flex; flex: 1; overflow: hidden; }
#graph-pane { flex: 1; position: relative; overflow: hidden; }
#graph-svg { width: 100%; height: 100%; }
.link { fill: none; stroke: #8b949e; }
.node circle { cursor: pointer; stroke: var(--bg); stroke-width: 1.5px; }
.node text { font-size: 10px; fill: var(--text); pointer-events: none;
              paint-order: stroke; stroke: var(--bg); stroke-width: 3px; }
.node.dimmed { opacity: 0.12; }
.node.hl circle { stroke: var(--accent); stroke-width: 2.5px; }

@keyframes qpulse {
  0%   { filter: drop-shadow(0 0 6px #f0a500) drop-shadow(0 0 14px #f0a500); }
  60%  { filter: drop-shadow(0 0 12px #ff5500) drop-shadow(0 0 24px #ff5500); }
  100% { filter: none; }
}
.qhit { animation: qpulse 4s ease-out forwards; }

#page-pane { width: 400px; min-width: 280px; border-left: 1px solid var(--border);
              background: var(--surface); overflow-y: auto; display: none;
              flex-direction: column; }
#ph { padding: 14px 16px; border-bottom: 1px solid var(--border);
       position: sticky; top: 0; background: var(--surface); z-index: 1; }
#ph-title { font-size: 17px; font-weight: 700; margin-bottom: 3px; }
#ph-meta { font-size: 11px; color: var(--muted); }
#close-btn { float: right; background: none; border: none; color: var(--muted);
              font-size: 18px; cursor: pointer; line-height: 1; padding: 0; }
#close-btn:hover { color: var(--text); }
#pb { padding: 16px; font-size: 13px; line-height: 1.65; }
#pb h1,#pb h2,#pb h3 { margin: 14px 0 6px; }
#pb p { margin-bottom: 10px; }
#pb code { background: var(--bg); padding: 1px 5px; border-radius: 4px; font-size: 12px; }
#pb pre { background: var(--bg); padding: 10px; border-radius: 6px;
           overflow-x: auto; margin-bottom: 10px; }
#pb a { color: var(--accent); }
#pl { padding: 0 16px 20px; }
.ls { margin-top: 14px; }
.ls-title { font-size: 11px; text-transform: uppercase; color: var(--muted);
             letter-spacing: 0.06em; margin-bottom: 6px; }
.chip { display: inline-block; padding: 3px 10px; border-radius: 12px; font-size: 12px;
         margin: 3px 3px 0 0; cursor: pointer; border: 1px solid var(--border);
         color: var(--text); background: var(--bg); transition: border-color 0.15s; }
.chip:hover { border-color: var(--accent); color: var(--accent); }
.sim-row { display: flex; justify-content: space-between; align-items: center;
            padding: 4px 0; font-size: 13px; cursor: pointer; border-radius: 4px; }
.sim-row:hover { color: var(--accent); }
.sim-pct { font-size: 11px; color: var(--muted); }

#login-overlay { position: fixed; inset: 0; background: var(--bg);
                  display: none; align-items: center; justify-content: center; z-index: 100; }
#login-box { background: var(--surface); border: 1px solid var(--border);
              border-radius: 10px; padding: 32px; width: 310px; text-align: center; }
#login-box h2 { margin-bottom: 20px; font-size: 16px; }
#lpw { width: 100%; padding: 10px; background: var(--bg); border: 1px solid var(--border);
        color: var(--text); border-radius: 6px; font-size: 14px; margin-bottom: 12px; }
#lpw:focus { outline: none; border-color: var(--accent); }
#lbtn { width: 100%; padding: 10px; background: var(--accent); color: #000;
         border: none; border-radius: 6px; font-size: 14px; font-weight: 600; cursor: pointer; }
#lbtn:hover { opacity: 0.9; }
#lerr { color: #f85149; font-size: 13px; margin-top: 8px; display: none; }
</style>
</head>
<body>

<div id="login-overlay">
  <div id="login-box">
    <h2>AI Wiki Memory</h2>
    <input id="lpw" type="password" placeholder="Password" autofocus>
    <button id="lbtn">Accedi</button>
    <div id="lerr">Password non corretta</div>
  </div>
</div>

<header id="header">
  <span class="logo">AI Wiki Memory</span>
  <div id="project-tabs"></div>
  <input id="search" type="text" placeholder="Cerca...">
  <div id="ws-dot" title="WebSocket"></div>
</header>

<main id="main">
  <div id="graph-pane"><svg id="graph-svg"></svg></div>
  <aside id="page-pane">
    <div id="ph">
      <button id="close-btn" aria-label="Chiudi">&times;</button>
      <div id="ph-title"></div>
      <div id="ph-meta"></div>
    </div>
    <div id="pb"></div>
    <div id="pl"></div>
  </aside>
</main>

<script>
'use strict';

const COLORS = {
  entities: '#4A90D9', concepts: '#5CB85C',
  synthesis: '#9B59B6', raw: '#AAAAAA', other: '#AAAAAA',
};

// Escape user-controlled strings before DOM insertion
function esc(s) {
  return String(s)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;')
    .replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#39;');
}

let graphData = { nodes: [], edges: [] };
let selectedProject = 'tutti';
let searchTerm = '';
let simulation = null;

const svg = d3.select('#graph-svg');
const root = svg.append('g');
const zoom = d3.zoom().scaleExtent([0.1, 4]).on('zoom', e => root.attr('transform', e.transform));
svg.call(zoom);
const linkGroup = root.append('g');
const nodeGroup = root.append('g');

const tip = d3.select('body').append('div')
  .style('position','fixed').style('background','#161b22')
  .style('border','1px solid #30363d').style('border-radius','6px')
  .style('padding','6px 10px').style('font-size','12px').style('color','#e6edf3')
  .style('pointer-events','none').style('display','none')
  .style('max-width','200px').style('z-index','50');

function gsize() {
  const el = document.getElementById('graph-pane');
  return { w: el.clientWidth, h: el.clientHeight };
}

function filteredData() {
  let nodes = graphData.nodes;
  if (selectedProject !== 'tutti') nodes = nodes.filter(n => n.project === selectedProject);
  if (searchTerm) {
    const q = searchTerm.toLowerCase();
    nodes = nodes.filter(n =>
      n.title.toLowerCase().includes(q) || (n.description || '').toLowerCase().includes(q));
  }
  const ids = new Set(nodes.map(n => n.id));
  const edges = graphData.edges.filter(e => {
    const s = typeof e.source === 'object' ? e.source.id : e.source;
    const t = typeof e.target === 'object' ? e.target.id : e.target;
    return ids.has(s) && ids.has(t);
  });
  return { nodes, edges };
}

function degrees(nodes, edges) {
  const d = {};
  nodes.forEach(n => d[n.id] = 0);
  edges.forEach(e => {
    const s = typeof e.source === 'object' ? e.source.id : e.source;
    const t = typeof e.target === 'object' ? e.target.id : e.target;
    if (d[s] !== undefined) d[s]++;
    if (d[t] !== undefined) d[t]++;
  });
  return d;
}

function renderGraph() {
  const { w, h } = gsize();
  const { nodes, edges } = filteredData();
  const deg = degrees(nodes, edges);

  linkGroup.selectAll('line')
    .data(edges, e => {
      const s = typeof e.source === 'object' ? e.source.id : e.source;
      const t = typeof e.target === 'object' ? e.target.id : e.target;
      return s + '|' + t + '|' + e.type;
    })
    .join(
      en => en.append('line').attr('class','link')
              .attr('stroke-dasharray', d => d.type === 'semantic' ? '5,3' : null)
              .attr('stroke-opacity', d => d.type === 'semantic'
                ? Math.max(0.15, (d.weight || 0.65) * 0.45) : 0.55)
              .attr('stroke-width', 1),
      up => up,
      ex => ex.transition().duration(300).style('opacity', 0).remove()
    );

  nodeGroup.selectAll('g.node')
    .data(nodes, d => d.id)
    .join(
      en => {
        const g = en.append('g').attr('class','node')
          .call(d3.drag()
            .on('start', (ev, d) => { if (!ev.active) simulation.alphaTarget(0.3).restart(); d.fx = d.x; d.fy = d.y; })
            .on('drag',  (ev, d) => { d.fx = ev.x; d.fy = ev.y; })
            .on('end',   (ev, d) => { if (!ev.active) simulation.alphaTarget(0); d.fx = null; d.fy = null; }))
          .on('click',   (ev, d) => { ev.stopPropagation(); loadPage(d); })
          .on('dblclick',(ev, d) => { ev.stopPropagation(); centerOn(d); })
          .on('mouseover', (ev, d) => {
            tip.style('display','block').text(d.title + (d.description ? ' — ' + d.description : ''));
          })
          .on('mousemove', ev => tip.style('left',(ev.clientX+12)+'px').style('top',(ev.clientY-10)+'px'))
          .on('mouseout', () => tip.style('display','none'));
        g.append('circle');
        g.append('text').attr('dy','0.35em');
        return g;
      },
      up => up,
      ex => ex.transition().duration(300).style('opacity',0).remove()
    );

  nodeGroup.selectAll('g.node circle')
    .attr('r', d => 6 + (deg[d.id] || 0) * 1.5)
    .attr('fill', d => COLORS[d.category] || COLORS.other);
  nodeGroup.selectAll('g.node text')
    .text(d => d.title)
    .attr('x', d => 9 + (deg[d.id] || 0) * 1.5);

  if (simulation) simulation.stop();

  simulation = d3.forceSimulation(nodes)
    .force('link', d3.forceLink(edges).id(d => d.id)
      .distance(d => d.type === 'semantic' ? 130 : 80))
    .force('charge', d3.forceManyBody().strength(-260))
    .force('center', d3.forceCenter(w / 2, h / 2))
    .force('collision', d3.forceCollide(d => 10 + (deg[d.id] || 0) * 1.5));

  simulation.on('tick', () => {
    linkGroup.selectAll('line')
      .attr('x1', d => d.source.x).attr('y1', d => d.source.y)
      .attr('x2', d => d.target.x).attr('y2', d => d.target.y);
    nodeGroup.selectAll('g.node')
      .attr('transform', d => `translate(${d.x || 0},${d.y || 0})`);
  });
}

function renderTabs() {
  const projects = ['tutti', ...new Set(graphData.nodes.map(n => n.project))].sort();
  const tabs = document.getElementById('project-tabs');
  tabs.textContent = '';
  projects.forEach(p => {
    const btn = document.createElement('button');
    btn.className = 'tab' + (p === selectedProject ? ' active' : '');
    btn.textContent = p;
    btn.addEventListener('click', () => { selectedProject = p; renderTabs(); renderGraph(); });
    tabs.appendChild(btn);
  });
}

document.getElementById('search').addEventListener('input', e => {
  searchTerm = e.target.value.trim(); renderGraph();
});

svg.on('click', () => {
  nodeGroup.selectAll('g.node').classed('hl', false);
  document.getElementById('page-pane').style.display = 'none';
});

function centerOn(d) {
  const { w, h } = gsize();
  const s = 1.5;
  svg.transition().duration(500).call(
    zoom.transform,
    d3.zoomIdentity.translate(w/2 - s*d.x, h/2 - s*d.y).scale(s)
  );
}

async function loadPage(d) {
  const resp = await fetch('/api/page/' + encodeURIComponent(d.path));
  if (resp.status === 401) { showLogin(); return; }
  if (!resp.ok) return;
  const data = await resp.json();

  document.getElementById('ph-title').textContent = data.metadata.title || d.title;
  const ts = data.metadata.last_modified
    ? new Date(data.metadata.last_modified * 1000).toLocaleDateString('it-IT')
    : '';
  document.getElementById('ph-meta').textContent =
    [d.category, d.project !== 'wiki' ? d.project : null, ts].filter(Boolean).join(' · ');

  // Markdown body — intentional HTML rendering of user's own wiki content
  document.getElementById('pb').innerHTML = marked.parse(data.content || '');

  const pl = document.getElementById('pl');
  pl.textContent = '';

  function makeSection(labelText, items, clickFn) {
    if (!items || !items.length) return;
    const sec = document.createElement('div');
    sec.className = 'ls';
    const h = document.createElement('div');
    h.className = 'ls-title';
    h.textContent = labelText;
    sec.appendChild(h);
    items.forEach(item => {
      const el = document.createElement('span');
      el.className = 'chip';
      el.textContent = typeof item === 'string' ? item.split('/').pop() : item.id.split('/').pop();
      el.addEventListener('click', () => clickFn(item));
      sec.appendChild(el);
    });
    pl.appendChild(sec);
  }

  function makeSimSection(similar) {
    if (!similar || !similar.length) return;
    const sec = document.createElement('div');
    sec.className = 'ls';
    const h = document.createElement('div');
    h.className = 'ls-title';
    h.textContent = 'Pagine simili';
    sec.appendChild(h);
    similar.forEach(s => {
      const row = document.createElement('div');
      row.className = 'sim-row';
      const name = document.createElement('span');
      name.textContent = s.id.split('/').pop();
      const pct = document.createElement('span');
      pct.className = 'sim-pct';
      pct.textContent = Math.round(s.weight * 100) + '%';
      row.appendChild(name);
      row.appendChild(pct);
      row.addEventListener('click', () => jumpTo(s.id));
      sec.appendChild(row);
    });
    pl.appendChild(sec);
  }

  makeSection('Link uscenti', data.links_out, id => jumpTo(id));
  makeSection('Link entranti', data.links_in, id => jumpTo(id));
  makeSimSection(data.similar);

  document.getElementById('page-pane').style.display = 'flex';
  nodeGroup.selectAll('g.node').classed('hl', nd => nd.id === d.id);
}

function jumpTo(nodeId) {
  const nd = graphData.nodes.find(n => n.id === nodeId);
  if (nd) loadPage(nd);
}

document.getElementById('close-btn').addEventListener('click', () => {
  document.getElementById('page-pane').style.display = 'none';
  nodeGroup.selectAll('g.node').classed('hl', false);
});

function handleQueryHit(paths) {
  paths.forEach(path => {
    const nid = path.replace(/\.md$/, '');
    nodeGroup.selectAll('g.node').filter(d => d.id === nid).each(function() {
      this.classList.remove('qhit');
      void this.offsetWidth;
      this.classList.add('qhit');
      setTimeout(() => this.classList.remove('qhit'), 4200);
    });
  });
  if (simulation) simulation.alpha(0.3).restart();
}

const wsDot = document.getElementById('ws-dot');

function connectWS() {
  const proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
  const ws = new WebSocket(proto + '//' + location.host + '/ws');
  ws.onopen  = () => wsDot.classList.add('on');
  ws.onclose = () => { wsDot.classList.remove('on'); setTimeout(connectWS, 3000); };
  ws.onerror = () => ws.close();
  ws.onmessage = async e => {
    const msg = JSON.parse(e.data);
    if (msg.type === 'graph_update') await fetchGraph();
    else if (msg.type === 'query_hit') handleQueryHit(msg.paths || []);
  };
}

async function fetchGraph() {
  const resp = await fetch('/api/graph');
  if (resp.status === 401) { showLogin(); return; }
  graphData = await resp.json();
  renderTabs();
  renderGraph();
}

function showLogin() {
  document.getElementById('login-overlay').style.display = 'flex';
}

document.getElementById('lbtn').addEventListener('click', async () => {
  const pw = document.getElementById('lpw').value;
  const resp = await fetch('/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ password: pw }),
  });
  if (resp.ok) {
    document.getElementById('login-overlay').style.display = 'none';
    await init();
  } else {
    document.getElementById('lerr').style.display = 'block';
  }
});

document.getElementById('lpw').addEventListener('keydown', e => {
  if (e.key === 'Enter') document.getElementById('lbtn').click();
});

window.addEventListener('resize', () => {
  if (simulation) {
    const { w, h } = gsize();
    simulation.force('center', d3.forceCenter(w / 2, h / 2)).alpha(0.1).restart();
  }
});

async function init() {
  await fetchGraph();
  connectWS();
}

init();
</script>
</body>
</html>
```

- [ ] **Step 3: Verify server starts**

```
cd C:\Users\giova\ai-wiki-system
py scripts/wiki.py serve --workspace . --no-auth
```
Expected output: `INFO:     Uvicorn running on http://127.0.0.1:7331`

Open `http://127.0.0.1:7331` in browser. Check:
- Graph renders with nodes (if any `.md` files exist in wiki/)
- Project tabs visible
- Click a node → page panel opens with rendered markdown
- WebSocket dot turns green
- No console errors (`F12 → Console`)

Stop server: `Ctrl+C`

- [ ] **Step 4: Run full test suite**

```
pytest -v
```
Expected: all tests pass.

- [ ] **Step 5: Commit**

```
git add frontend/index.html
git commit -m "feat: SPA frontend — D3 graph, page panel, WebSocket, query hit animation"
```

---

## Self-Review Checklist

**Spec coverage:**
- [x] `wiki_graph.py` — nodes from filesystem, explicit `[[slug]]` edges, semantic edges from LanceDB, 30s cache with dirty flag, `mark_dirty()`, `get_page_detail()`
- [x] `wiki_server.py` — `/api/graph`, `/api/page/{path}`, `/`, `/auth/login`, `/auth/logout`, `/ws` WebSocket, file watcher via `watchfiles.awatch`, query log watcher polling `.wiki-query-log.jsonl`, JWT cookie auth, `--no-auth` bypass, `configure()` reads `WIKI_PASSWORD` env or `cfg.frontend.password`
- [x] `frontend/index.html` — D3 force-directed, category colors, degree-sized nodes, solid/dashed edges, click→panel, double-click→zoom, drag, zoom, project tabs, search highlight, query hit CSS animation + alpha bump, graph_update refetch with D3 join, login overlay on 401, `esc()` for all dynamic string insertion
- [x] `wiki.py` — `serve` subcommand with `--workspace`, `--host`, `--port`, `--no-auth`; port default 7331
- [x] `cmd_query` appends `{"ts", "q", "paths"}` to `.wiki-query-log.jsonl`
- [x] `frontend.password` + `WIKI_PASSWORD` env var
- [x] `session_days` configurable

**Tests from spec:**
- [x] `test_build_graph_nodes`
- [x] `test_build_graph_explicit_links`
- [x] `test_build_graph_semantic_edges`
- [x] `test_missing_link_ignored`
- [x] `test_query_log_written`
- [x] `test_api_graph_endpoint`
- [x] `test_api_page_endpoint`
- [x] `test_auth_required`
- [x] `test_auth_login`
- [x] `test_auth_wrong_password`
