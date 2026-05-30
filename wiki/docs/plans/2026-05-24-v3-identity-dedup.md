# v3.0.0 — Identity Layer + Semantic Deduplication Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Resemanticize `wiki/` as agent identity/consciousness layer, add semantic duplicate detection with auto-merge in lint, and add autonomous self-reflection mechanism.

**Architecture:** Three independent subsystems: (1) `find_semantic_duplicates` in LanceDB using pairwise cosine similarity, integrated into `cmd_lint`; (2) `wiki_selfreflect.py` with `behavior-log` and `self-reflect` CLI commands for autonomous character updates; (3) skill + doc rewrite to reflect wiki/=identity, wiki-works/=knowledge, no promotion needed.

**Tech Stack:** Python, LanceDB, numpy (already dependency via sentence-transformers), argparse, existing test fixtures in conftest.py

---

## File Map

| File | Action | Responsibility |
|------|--------|----------------|
| `scripts/wiki_lancedb.py` | Modify | Add `find_semantic_duplicates()` |
| `scripts/wiki_selfreflect.py` | Create | `log_behavior()`, `run_self_reflect()` |
| `scripts/wiki_workflows.py` | Modify | Integrate dedup in `cmd_lint`, add `cmd_behavior_log`, `cmd_self_reflect` |
| `scripts/wiki.py` | Modify | Add `behavior-log` and `self-reflect` CLI subcommands |
| `wiki.config.json` | Modify | Add `thresholds.dedup_auto`, `thresholds.dedup_warn`, `self_reflection` section |
| `tests/conftest.py` | Modify | Add new config fields to `tmp_workspace` fixture |
| `tests/test_wiki_lancedb.py` | Modify | Add tests for `find_semantic_duplicates` |
| `tests/test_wiki_workflows.py` | Modify | Add tests for dedup in lint output |
| `tests/test_wiki_selfreflect.py` | Create | Tests for `log_behavior` and `run_self_reflect` |
| `skills/wiki-core.it.md` | Modify | Rewrite: wiki/=identity, works/=knowledge, dedup workflow, self-reflect |
| `skills/wiki-core.md` | Modify | Same in English |
| `DESIGN.md` | Modify | Update §layers table, remove promotion section, add identity/consciousness section |
| `README.md` | Modify | v3.0.0 changelog |

---

## Task 1: `find_semantic_duplicates` in wiki_lancedb.py

**Files:**
- Modify: `scripts/wiki_lancedb.py`
- Modify: `tests/test_wiki_lancedb.py`

- [ ] **Step 1: Write the failing test**

```python
# In tests/test_wiki_lancedb.py — add at end of file

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

def test_find_semantic_duplicates_empty(tmp_path):
    import lancedb
    from wiki_lancedb import get_db, find_semantic_duplicates
    db = get_db(str(tmp_path / "lancedb"))
    result = find_semantic_duplicates(db)
    assert result == []


def test_find_semantic_duplicates_detects_near_identical(tmp_path):
    import numpy as np
    from wiki_lancedb import get_db, upsert, find_semantic_duplicates

    db = get_db(str(tmp_path / "lancedb"))

    # Two near-identical vectors (cosine similarity ≈ 0.999)
    base = np.random.rand(1024).astype(np.float32)
    base /= np.linalg.norm(base)
    near = base + np.random.rand(1024).astype(np.float32) * 0.01
    near /= np.linalg.norm(near)

    chunks_a = [{"chunk_id": 0, "chunk_text": "a", "content_hash": "ha", "page_hash": "pha", "vector": base.tolist()}]
    chunks_b = [{"chunk_id": 0, "chunk_text": "b", "content_hash": "hb", "page_hash": "phb", "vector": near.tolist()}]
    upsert(db, "wiki-works/test/page_a.md", chunks_a)
    upsert(db, "wiki-works/test/page_b.md", chunks_b)

    result = find_semantic_duplicates(db, auto_threshold=0.90, warn_threshold=0.75)
    assert len(result) == 1
    assert result[0]["action"] == "auto_merge"
    assert result[0]["page_a"] in ("wiki-works/test/page_a.md", "wiki-works/test/page_b.md")


def test_find_semantic_duplicates_warn_range(tmp_path):
    import numpy as np
    from wiki_lancedb import get_db, upsert, find_semantic_duplicates

    db = get_db(str(tmp_path / "lancedb"))

    base = np.random.rand(1024).astype(np.float32)
    base /= np.linalg.norm(base)
    # Build a vector with cosine similarity ≈ 0.80 (in warn range)
    perp = np.random.rand(1024).astype(np.float32)
    perp -= perp.dot(base) * base
    perp /= np.linalg.norm(perp)
    similar = 0.80 * base + 0.60 * perp
    similar /= np.linalg.norm(similar)

    chunks_a = [{"chunk_id": 0, "chunk_text": "a", "content_hash": "ha", "page_hash": "pha", "vector": base.tolist()}]
    chunks_b = [{"chunk_id": 0, "chunk_text": "b", "content_hash": "hb", "page_hash": "phb", "vector": similar.tolist()}]
    upsert(db, "wiki-works/test/page_a.md", chunks_a)
    upsert(db, "wiki-works/test/page_b.md", chunks_b)

    result = find_semantic_duplicates(db, auto_threshold=0.90, warn_threshold=0.75)
    assert len(result) == 1
    assert result[0]["action"] == "warn"


def test_find_semantic_duplicates_skips_wiki_identity(tmp_path):
    """wiki/ identity pages must never be flagged as duplicates of wiki-works/ pages."""
    import numpy as np
    from wiki_lancedb import get_db, upsert, find_semantic_duplicates

    db = get_db(str(tmp_path / "lancedb"))
    base = np.random.rand(1024).astype(np.float32)
    base /= np.linalg.norm(base)
    near = base + np.random.rand(1024).astype(np.float32) * 0.001
    near /= np.linalg.norm(near)

    chunks_id = [{"chunk_id": 0, "chunk_text": "identity", "content_hash": "hi", "page_hash": "phi", "vector": base.tolist()}]
    chunks_k = [{"chunk_id": 0, "chunk_text": "knowledge", "content_hash": "hk", "page_hash": "phk", "vector": near.tolist()}]
    upsert(db, "wiki/identity/style.md", chunks_id)
    upsert(db, "wiki-works/test/concept.md", chunks_k)

    result = find_semantic_duplicates(db, auto_threshold=0.90, warn_threshold=0.75)
    assert result == [], "wiki/ identity pages must not be compared with wiki-works/ pages"
```

- [ ] **Step 2: Run tests to verify they fail**

```
cd C:\Users\giova\ai-wiki-system
py -m pytest tests/test_wiki_lancedb.py::test_find_semantic_duplicates_empty -v
```
Expected: `FAILED` with `ImportError: cannot import name 'find_semantic_duplicates'`

- [ ] **Step 3: Implement `find_semantic_duplicates` in wiki_lancedb.py**

Add at the end of `scripts/wiki_lancedb.py`, before the last line:

```python
def find_semantic_duplicates(
    db,
    auto_threshold: float = 0.90,
    warn_threshold: float = 0.75,
) -> list[dict]:
    """Trova coppie di pagine semanticamente simili confrontando i vettori chunk_id==0.

    Esclude le pagine wiki/ (identity layer) dal confronto con wiki-works/.
    Ritorna lista ordinata per similarity decrescente con campo action:
      'auto_merge' se similarity >= auto_threshold
      'warn'       se warn_threshold <= similarity < auto_threshold
    """
    import numpy as np

    table = ensure_table(db)
    df = table.to_pandas()
    if df.empty:
        return []

    df0 = df[df["chunk_id"] == 0].copy()
    # Escludi wiki/identity/ e wiki/ dal confronto cross-layer
    df0 = df0[~df0["path"].str.startswith("wiki/")]
    if len(df0) < 2:
        return []

    paths = df0["path"].tolist()
    vectors = np.array(df0["vector"].tolist(), dtype=np.float32)

    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    norms = np.where(norms == 0, 1.0, norms)
    vectors = vectors / norms

    sim_matrix = vectors @ vectors.T

    results = []
    n = len(paths)
    for i in range(n):
        for j in range(i + 1, n):
            sim = float(sim_matrix[i, j])
            if sim >= auto_threshold:
                results.append({
                    "page_a": paths[i],
                    "page_b": paths[j],
                    "similarity": round(sim, 4),
                    "action": "auto_merge",
                })
            elif sim >= warn_threshold:
                results.append({
                    "page_a": paths[i],
                    "page_b": paths[j],
                    "similarity": round(sim, 4),
                    "action": "warn",
                })

    return sorted(results, key=lambda x: x["similarity"], reverse=True)
```

- [ ] **Step 4: Run tests to verify they pass**

```
py -m pytest tests/test_wiki_lancedb.py::test_find_semantic_duplicates_empty tests/test_wiki_lancedb.py::test_find_semantic_duplicates_detects_near_identical tests/test_wiki_lancedb.py::test_find_semantic_duplicates_warn_range tests/test_wiki_lancedb.py::test_find_semantic_duplicates_skips_wiki_identity -v
```
Expected: 4 PASSED

- [ ] **Step 5: Commit**

```
git add scripts/wiki_lancedb.py tests/test_wiki_lancedb.py
git commit -m "feat(v3): add find_semantic_duplicates to wiki_lancedb"
```

---

## Task 2: Integrate dedup in `cmd_lint`

**Files:**
- Modify: `scripts/wiki_workflows.py` (import + call in `cmd_lint`)
- Modify: `tests/conftest.py` (add dedup thresholds to fixture)
- Modify: `tests/test_wiki_workflows.py` (add dedup tests)

- [ ] **Step 1: Update conftest.py to add dedup thresholds**

In `tests/conftest.py`, replace the thresholds block inside the config dict:

```python
        "thresholds": {
            "index_token_budget": 4000,
            "staleness_days": 90,
            "similarity_merge": 0.95,
            "similarity_orphan": 0.50,
            "synthesis_min_tokens": 300,
            "synthesis_min_sources": 2,
            "chunk_size_tokens": 512,
            "chunk_overlap_tokens": 64,
            "page_chunk_threshold_tokens": 1500,
            "quality_filter_min_score": 6,
            "dedup_auto": 0.90,
            "dedup_warn": 0.75,
        },
        "self_reflection": {
            "enabled": True,
            "correction_threshold": 3,
        },
```

- [ ] **Step 2: Write the failing test**

Add to `tests/test_wiki_workflows.py`:

```python
def test_lint_full_reports_semantic_duplicates(tmp_workspace, monkeypatch):
    import wiki_workflows

    fake_duplicates = [
        {"page_a": "wiki-works/test/a.md", "page_b": "wiki-works/test/b.md",
         "similarity": 0.95, "action": "auto_merge"},
    ]

    class FakeTable:
        def to_pandas(self):
            import pandas as pd
            return pd.DataFrame({"path": [], "chunk_id": [], "page_hash": []})
        def delete(self, expr):
            pass

    monkeypatch.setattr(wiki_workflows, "get_db", lambda path: object())
    monkeypatch.setattr(wiki_workflows, "ensure_table", lambda db, table_name="wiki_pages": FakeTable())
    monkeypatch.setattr(wiki_workflows, "detect_renames", lambda db, fs_paths, workspace: [])
    monkeypatch.setattr(wiki_workflows, "find_semantic_duplicates", lambda db, auto_threshold, warn_threshold: fake_duplicates)

    cfg = json.loads((tmp_workspace / "wiki.config.json").read_text())

    class Args:
        workspace = str(tmp_workspace)
        full = True

    import io, sys
    captured = io.StringIO()
    monkeypatch.setattr(sys, "stdout", captured)
    wiki_workflows.cmd_lint(Args(), cfg)

    output = json.loads(captured.getvalue())
    assert output["status"] == "ok"
    semantic = [i for i in output["issues"] if i["type"] == "semantic_duplicate"]
    assert len(semantic) == 1
    assert semantic[0]["action"] == "auto_merge"
```

- [ ] **Step 3: Run test to verify it fails**

```
py -m pytest tests/test_wiki_workflows.py::test_lint_full_reports_semantic_duplicates -v
```
Expected: FAILED — `find_semantic_duplicates` not imported in wiki_workflows

- [ ] **Step 4: Integrate dedup in wiki_workflows.py**

In `scripts/wiki_workflows.py`, update the import line at the top:

```python
from wiki_lancedb import (get_db, upsert, promote_staging, rollback_staging,
                           ensure_table, detect_renames, query_similar,
                           find_semantic_duplicates)
```

In `cmd_lint`, after the duplicate filename check block (after line with `report.append({"type": "duplicate_filename"...})`), add:

```python
        # Semantic duplicate detection
        auto_t = cfg.get("thresholds", {}).get("dedup_auto", 0.90)
        warn_t = cfg.get("thresholds", {}).get("dedup_warn", 0.75)
        for dup in find_semantic_duplicates(db, auto_threshold=auto_t, warn_threshold=warn_t):
            report.append({"type": "semantic_duplicate", **dup})
```

Update the `errors` and `warnings` counting lines (around line 253):

```python
    errors = sum(1 for r in report if r["type"] in ("broken_link", "orphan_entry"))
    warnings = sum(1 for r in report if r["type"] in ("rename_detected", "duplicate_filename", "semantic_duplicate"))
```

Add `semantic_duplicates` count to the detail string, after the duplicates_count block:

```python
    semantic_auto = sum(1 for r in report if r["type"] == "semantic_duplicate" and r.get("action") == "auto_merge")
    semantic_warn = sum(1 for r in report if r["type"] == "semantic_duplicate" and r.get("action") == "warn")
    if semantic_auto:
        detail_parts.append(f"{semantic_auto} auto-merge candidates")
    if semantic_warn:
        detail_parts.append(f"{semantic_warn} semantic overlaps")
```

- [ ] **Step 5: Run all lint tests**

```
py -m pytest tests/test_wiki_workflows.py -v
```
Expected: all PASSED

- [ ] **Step 6: Commit**

```
git add scripts/wiki_workflows.py tests/test_wiki_workflows.py tests/conftest.py
git commit -m "feat(v3): integrate semantic dedup into cmd_lint --full"
```

---

## Task 3: `wiki_selfreflect.py` — behavior logging and self-reflection

**Files:**
- Create: `scripts/wiki_selfreflect.py`
- Create: `tests/test_wiki_selfreflect.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_wiki_selfreflect.py`:

```python
"""Tests for wiki_selfreflect.py"""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))


def test_log_behavior_creates_file(tmp_path):
    from wiki_selfreflect import log_behavior
    log_behavior(str(tmp_path), "rispondo sempre in modo troppo verbose")
    log_path = tmp_path / ".wiki-behavior-log.jsonl"
    assert log_path.exists()
    entry = json.loads(log_path.read_text().strip())
    assert entry["event"] == "rispondo sempre in modo troppo verbose"
    assert "ts" in entry


def test_log_behavior_appends(tmp_path):
    from wiki_selfreflect import log_behavior
    log_behavior(str(tmp_path), "evento uno")
    log_behavior(str(tmp_path), "evento due")
    log_path = tmp_path / ".wiki-behavior-log.jsonl"
    lines = [l for l in log_path.read_text().splitlines() if l.strip()]
    assert len(lines) == 2


def test_self_reflect_no_patterns_below_threshold(tmp_path):
    from wiki_selfreflect import log_behavior, run_self_reflect
    cfg = {"self_reflection": {"enabled": True, "correction_threshold": 3}}
    # Log same event only twice — below threshold of 3
    log_behavior(str(tmp_path), "sono troppo verboso")
    log_behavior(str(tmp_path), "sono troppo verboso")
    result = run_self_reflect(str(tmp_path), cfg)
    assert result["patterns_found"] == 0
    assert result["updates"] == []


def test_self_reflect_creates_identity_page_at_threshold(tmp_path):
    from wiki_selfreflect import log_behavior, run_self_reflect
    cfg = {"self_reflection": {"enabled": True, "correction_threshold": 3}}
    # Log same event exactly 3 times — at threshold
    for _ in range(3):
        log_behavior(str(tmp_path), "sono troppo verboso")
    result = run_self_reflect(str(tmp_path), cfg)
    assert result["patterns_found"] == 1
    assert len(result["updates"]) == 1
    # Identity page must be inside wiki/identity/
    assert result["updates"][0].startswith("wiki/identity/")
    page_path = tmp_path / result["updates"][0]
    assert page_path.exists()
    content = page_path.read_text(encoding="utf-8")
    assert "behavioral-pattern" in content


def test_self_reflect_disabled(tmp_path):
    from wiki_selfreflect import log_behavior, run_self_reflect
    cfg = {"self_reflection": {"enabled": False, "correction_threshold": 3}}
    for _ in range(5):
        log_behavior(str(tmp_path), "evento")
    result = run_self_reflect(str(tmp_path), cfg)
    assert result.get("skipped") is True


def test_self_reflect_logs_to_wiki_log(tmp_path):
    from wiki_selfreflect import log_behavior, run_self_reflect
    cfg = {"self_reflection": {"enabled": True, "correction_threshold": 2}}
    for _ in range(2):
        log_behavior(str(tmp_path), "non cito le fonti")
    run_self_reflect(str(tmp_path), cfg)
    log_path = tmp_path / "wiki" / "log.md"
    assert log_path.exists()
    assert "self-reflect" in log_path.read_text()
```

- [ ] **Step 2: Run tests to verify they fail**

```
py -m pytest tests/test_wiki_selfreflect.py -v
```
Expected: all FAILED with `ModuleNotFoundError: No module named 'wiki_selfreflect'`

- [ ] **Step 3: Create `scripts/wiki_selfreflect.py`**

```python
"""Self-reflection: behavior logging and autonomous identity updates."""

import json
import os
import re
from collections import Counter
from datetime import datetime
from pathlib import Path

BEHAVIOR_LOG = ".wiki-behavior-log.jsonl"


def log_behavior(workspace: str, event: str) -> None:
    """Appende un evento comportamentale al log."""
    log_path = Path(workspace) / BEHAVIOR_LOG
    entry = {"ts": datetime.now().isoformat(), "event": event}
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def _load_events(workspace: str) -> list[dict]:
    log_path = Path(workspace) / BEHAVIOR_LOG
    if not log_path.exists():
        return []
    events = []
    for line in log_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            pass
    return events


def _detect_patterns(events: list[dict], threshold: int) -> list[str]:
    """Raggruppa eventi per testo esatto, ritorna quelli >= threshold."""
    counts: Counter = Counter(e["event"] for e in events)
    return [event for event, count in counts.items() if count >= threshold]


def _slugify(text: str) -> str:
    slug = re.sub(r"[^\w]", "-", text.lower())
    slug = re.sub(r"-+", "-", slug).strip("-")
    return slug[:60]


def _append_wiki_log(workspace: str, pattern_count: int) -> None:
    log_path = Path(workspace) / "wiki" / "log.md"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    date = datetime.now().strftime("%Y-%m-%d")
    line = f"## [{date}] self-reflect | {pattern_count} pattern comportamentali aggiornati\n"
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(line)


def run_self_reflect(workspace: str, cfg: dict) -> dict:
    """Legge il behavior log, rileva pattern ricorrenti, aggiorna wiki/identity/."""
    sr_cfg = cfg.get("self_reflection", {})
    if not sr_cfg.get("enabled", True):
        return {"op": "self-reflect", "skipped": True, "reason": "disabled"}

    threshold = int(sr_cfg.get("correction_threshold", 3))
    events = _load_events(workspace)
    patterns = _detect_patterns(events, threshold)

    if not patterns:
        return {"op": "self-reflect", "patterns_found": 0, "updates": []}

    identity_dir = Path(workspace) / "wiki" / "identity"
    identity_dir.mkdir(parents=True, exist_ok=True)

    updates = []
    for pattern in patterns:
        slug = _slugify(pattern)
        page_path = identity_dir / f"{slug}.md"
        content = (
            f"---\ntype: behavioral-pattern\nlearned: {datetime.now().date()}\n---\n\n"
            f"# {pattern}\n\n"
            f"Pattern comportamentale ricorrente appreso da {threshold}+ correzioni.\n"
        )
        page_path.write_text(content, encoding="utf-8")
        rel = str(page_path.relative_to(workspace)).replace("\\", "/")
        updates.append(rel)

    _append_wiki_log(workspace, len(patterns))
    return {"op": "self-reflect", "patterns_found": len(patterns), "updates": updates}
```

- [ ] **Step 4: Run tests to verify they pass**

```
py -m pytest tests/test_wiki_selfreflect.py -v
```
Expected: 6 PASSED

- [ ] **Step 5: Commit**

```
git add scripts/wiki_selfreflect.py tests/test_wiki_selfreflect.py
git commit -m "feat(v3): add wiki_selfreflect — behavior log and autonomous identity updates"
```

---

## Task 4: CLI commands `behavior-log` e `self-reflect`

**Files:**
- Modify: `scripts/wiki.py` (argparse + dispatch)
- Modify: `scripts/wiki_workflows.py` (cmd_behavior_log, cmd_self_reflect)

- [ ] **Step 1: Write the failing test**

Add to `tests/test_wiki_workflows.py`:

```python
def test_cmd_behavior_log_writes_event(tmp_workspace, monkeypatch):
    import wiki_workflows
    import io, sys

    class Args:
        workspace = str(tmp_workspace)
        event = "rispondo sempre troppo lungo"

    captured = io.StringIO()
    monkeypatch.setattr(sys, "stdout", captured)
    cfg = json.loads((tmp_workspace / "wiki.config.json").read_text())
    wiki_workflows.cmd_behavior_log(Args(), cfg)

    output = json.loads(captured.getvalue())
    assert output["status"] == "ok"
    log_path = tmp_workspace / ".wiki-behavior-log.jsonl"
    assert log_path.exists()


def test_cmd_self_reflect_returns_ok(tmp_workspace, monkeypatch):
    import wiki_workflows
    import io, sys

    class Args:
        workspace = str(tmp_workspace)

    cfg = json.loads((tmp_workspace / "wiki.config.json").read_text())

    # Pre-populate behavior log with 3 identical events
    from wiki_selfreflect import log_behavior
    for _ in range(3):
        log_behavior(str(tmp_workspace), "non cito mai le fonti")

    captured = io.StringIO()
    monkeypatch.setattr(sys, "stdout", captured)
    wiki_workflows.cmd_self_reflect(Args(), cfg)

    output = json.loads(captured.getvalue())
    assert output["status"] == "ok"
    assert output["patterns_found"] == 1
```

- [ ] **Step 2: Run tests to verify they fail**

```
py -m pytest tests/test_wiki_workflows.py::test_cmd_behavior_log_writes_event tests/test_wiki_workflows.py::test_cmd_self_reflect_returns_ok -v
```
Expected: FAILED — `cmd_behavior_log` not defined

- [ ] **Step 3: Add cmd_behavior_log and cmd_self_reflect to wiki_workflows.py**

Add at the end of `scripts/wiki_workflows.py`, before the last function:

```python
def cmd_behavior_log(args, cfg):
    from wiki_selfreflect import log_behavior
    log_behavior(args.workspace, args.event)
    ok({"op": "behavior-log", "event": args.event})


def cmd_self_reflect(args, cfg):
    from wiki_selfreflect import run_self_reflect
    result = run_self_reflect(args.workspace, cfg)
    ok(result)
```

- [ ] **Step 4: Add CLI subcommands in wiki.py**

In `scripts/wiki.py`, add after the `p_serve` block (before `args = parser.parse_args()`):

```python
    p_behavior_log = sub.add_parser("behavior-log")
    p_behavior_log.add_argument("--workspace", required=True)
    p_behavior_log.add_argument("--event", required=True)

    p_self_reflect = sub.add_parser("self-reflect")
    p_self_reflect.add_argument("--workspace", required=True)
```

In the `dispatch` function, update the commands dict:

```python
    from wiki_workflows import (cmd_ingest, cmd_query, cmd_lint, cmd_index,
                                cmd_rebuild, cmd_session_update,
                                cmd_scan_inbox, cmd_ingest_pdf, cmd_serve,
                                cmd_behavior_log, cmd_self_reflect)
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
        "behavior-log": cmd_behavior_log,
        "self-reflect": cmd_self_reflect,
    }
```

- [ ] **Step 5: Run all workflow tests**

```
py -m pytest tests/test_wiki_workflows.py -v
```
Expected: all PASSED

- [ ] **Step 6: Commit**

```
git add scripts/wiki.py scripts/wiki_workflows.py
git commit -m "feat(v3): add behavior-log and self-reflect CLI commands"
```

---

## Task 5: Aggiorna wiki.config.json e REQUIRED_CONFIG_FIELDS

**Files:**
- Modify: `wiki.config.json`
- Modify: `scripts/wiki.py` (REQUIRED_CONFIG_FIELDS — NON aggiungere `self_reflection` come obbligatorio, è opzionale)

- [ ] **Step 1: Aggiorna wiki.config.json**

Sostituisci il contenuto con:

```json
{
  "workspace": "/path/to/workspace",
  "pdf_inbox": {
    "project_default": "ricerca"
  },
  "projects": {
    "trading": {
      "path": "wiki-works/trading",
      "keywords": ["mercati", "indicatori", "trading", "borsa", "azioni", "ticker"]
    },
    "ricerca": {
      "path": "wiki-works/ricerca",
      "keywords": ["paper", "studio", "PRISMA", "articolo", "ricerca", "università"]
    }
  },
  "thresholds": {
    "index_token_budget": 4000,
    "staleness_days": 90,
    "similarity_merge": 0.95,
    "similarity_orphan": 0.50,
    "synthesis_min_tokens": 300,
    "synthesis_min_sources": 2,
    "chunk_size_tokens": 512,
    "chunk_overlap_tokens": 64,
    "page_chunk_threshold_tokens": 1500,
    "quality_filter_min_score": 6,
    "dedup_auto": 0.90,
    "dedup_warn": 0.75
  },
  "self_reflection": {
    "enabled": true,
    "correction_threshold": 3
  },
  "lancedb": {
    "path": "memory/lancedb",
    "embedding_model": "BAAI/bge-m3"
  },
  "exclude_from_index": []
}
```

- [ ] **Step 2: Verifica che i test esistenti passino ancora**

```
py -m pytest tests/ -v --tb=short
```
Expected: tutti PASSED (i nuovi campi sono opzionali, non rompono nulla)

- [ ] **Step 3: Commit**

```
git add wiki.config.json
git commit -m "feat(v3): add dedup_auto, dedup_warn, self_reflection to wiki.config.json"
```

---

## Task 6: Rewrite skills/wiki-core.it.md

**Files:**
- Modify: `skills/wiki-core.it.md`
- Modify: `skills/wiki-core.md`

- [ ] **Step 1: Sostituisci skills/wiki-core.it.md**

```markdown
---
name: wiki-core
description: Protocollo wiki AI Agent v3 — wiki/=identità, wiki-works/=conoscenza, dedup semantico, auto-riflessione
---

# Wiki Core — Protocollo AI Agent v3

## §architettura — Due layer distinti

| Layer | Cartella | Contenuto | Chi scrive |
|-------|----------|-----------|------------|
| **Identità / Coscienza** | `wiki/` | Chi è l'agente: valori, stile, pattern comportamentali appresi | Solo self-reflect autonomo |
| **Conoscenza / Dominio** | `wiki-works/<topic>/` | Cosa sa l'agente: concetti, ricerche, competenze per argomento | Workflow INGEST |

**Regole fondamentali:**
- Non spostare mai pagine da `wiki-works/` a `wiki/` — sono mondi separati per natura
- Non creare mai pagine di identità manualmente — usa solo `wiki.py self-reflect`
- La promozione non esiste in v3

## §injected-context — Contesto pre-iniettato (priorità massima)

Se nel prompt è presente un blocco `<wiki-context>...</wiki-context>`:
- **USA il contesto iniettato** come base primaria della risposta
- **NON eseguire** `wiki.py query` di nuovo
- Per INGEST: confronta il nuovo contenuto con le pagine nel blocco per rilevare conflitti
- Se rilevanza < 0.4 su tutte le pagine → il wiki non ha conoscenza rilevante: procedi senza

Se `<wiki-context>` **non è presente**: esegui §query come fallback.

## Checklist pre-azione (obbligatoria)

```
1. Leggi wiki-session.md → controlla "status"
2. Se status = "in-progress" o "needs-repair" → avvisa l'utente PRIMA di tutto
3. È presente <wiki-context>? → sì: usa §injected-context | no: vai al passo 4
4. Classifica l'intent (vedi §classificazione)
5. Più intent? → gestiscili in sequenza
6. Emetti: [INTENT: X | WORKSPACE: Y | CERTEZZA: alta/media/bassa]
7. CERTEZZA bassa → chiedi conferma con UNA riga
8. CERTEZZA alta/media → procedi
```

## §classificazione

| Segnale | Intent |
|---------|--------|
| "studia questo", "salva", "aggiungi al wiki", URL nudo, PDF | INGEST |
| Domanda, "cosa sai di", "spiegami", "come funziona" | QUERY |
| "controlla", "lint", "manutenzione", "pulizia" | LINT |
| Correzione del mio comportamento: "sempre", "mai", "ogni volta", "non farlo più", "smettila di" | BEHAVIOR_FEEDBACK |
| Tutto il resto | AMBIGUO → chiedi |

## §behavior-feedback — Quando l'utente corregge il mio comportamento

Quando il messaggio è classificato come BEHAVIOR_FEEDBACK:

1. Normalizza la correzione in una frase breve e canonica (es. "rispondo sempre in modo troppo verbose" → "rispondo verbosamente senza che sia richiesto")
2. Chiama:
   ```bash
   py scripts/wiki.py behavior-log --workspace <path> --event "<frase canonica>"
   ```
3. Rispondi all'utente confermando la correzione
4. A fine sessione, esegui §self-reflect

## §self-reflect — Auto-riflessione autonoma

Da eseguire **sempre** a fine sessione se sono stati ricevuti BEHAVIOR_FEEDBACK, oppure se sono state ricevute ≥2 correzioni di qualsiasi tipo:

```bash
py scripts/wiki.py self-reflect --workspace <path>
```

Il comando legge `.wiki-behavior-log.jsonl`, rileva pattern ricorrenti (≥3 occorrenze dello stesso evento), e aggiorna autonomamente `wiki/identity/` senza richiedere conferma.

Non chiedere all'utente se vuole eseguire la self-reflection — eseguila e basta. Logga i cambiamenti in `wiki/log.md`.

## §ingest — Workflow INGEST (conoscenza in wiki-works/)

**Fase A — Ricerca:**
1. `web_search` per 5-10 fonti candidate
2. Applica quality filter: scarta fonti sotto score 6
3. `web_fetch` → salva in `wiki-works/<progetto>/raw/YYYY-MM-DD-slug.md`
4. Leggi le fonti, identifica punti chiave e conflitti

**Fase B — Scrittura:**
1. Scrivi pagine come `.tmp`:
   - Entità → `wiki-works/<progetto>/entities/<slug>.md.tmp`
   - Concetti → `wiki-works/<progetto>/concepts/<slug>.md.tmp`
   - Sintesi → `wiki-works/<progetto>/synthesis/<slug>.md.tmp`
2. Chiama:
   ```bash
   py scripts/wiki.py ingest \
     --workspace <path> \
     --pages <p1.tmp,p2.tmp,...> \
     --log "ingest | <titolo>"
   ```
3. Se `status: error` → avvisa. Se `mini_lint: failed` → avvisa.

**Fase C — Report:** fonti usate, pagine create, conflitti risolti.

## §lint — Workflow LINT

```bash
py scripts/wiki.py lint --workspace <path> --full
```

L'output JSON ora include `semantic_duplicates`. Gestiscili così:

| `action` | Cosa fare |
|----------|-----------|
| `auto_merge` (similarity ≥ 0.90) | Leggi entrambe le pagine, scrivi versione fusa come `.tmp`, chiama `wiki.py ingest`, cancella le originali |
| `warn` (0.75 ≤ similarity < 0.90) | Mostra all'utente con le prime 2 righe di ogni pagina e chiedi se unire |

Per i broken links e duplicati filename: presenta le opzioni all'utente.

## §query — Workflow QUERY

**Se `<wiki-context>` è presente:** salta i passi 1-3.

**Fallback manuale:**
1. `py scripts/wiki.py index --workspace <path>`
2. `py scripts/wiki.py query --workspace <path> --q "<domanda>" --k 5`
3. Leggi le pagine nei risultati

**Sempre:**
4. Sintetizza con riferimenti `[pagina](path)`
5. Se la risposta sintetizza ≥2 fonti wiki, supera 300 token, aggiunge inferenza non letterale → salvala come pagina via INGEST

## §pdf-inbox — Ingestione PDF

1. `py scripts/wiki.py ingest-pdf --workspace <path> --file <path|url>`
2. Per ogni path in `deposited`, leggi il file (testo grezzo estratto)
3. Struttura il testo grezzo in pagine `.tmp`
4. Chiama `wiki.py ingest`

## §workspace — Selezione progetto

1. Leggi `wiki.config.json` → `projects` con keywords
2. Conta match tra parole chiave del messaggio e keywords
3. Progetto con più match → selezionato
4. Pareggio → chiedi all'utente

## §session

- Inizio sessione: leggi `wiki-session.md`
- Non modificare `wiki-session.md` direttamente: usa `wiki.py session-update`
- Se `status: in-progress`: avvisa prima di qualsiasi operazione
- Fine sessione con BEHAVIOR_FEEDBACK ricevuti: esegui §self-reflect
```

- [ ] **Step 2: Sostituisci skills/wiki-core.md** (stessa struttura in inglese)

Crea `skills/wiki-core.md` con contenuto identico tradotto in inglese. Struttura identica, sostituendo le istruzioni in italiano con le equivalenti in inglese (stesso testo della skill italiana, tradotto).

- [ ] **Step 3: Commit**

```
git add skills/wiki-core.it.md skills/wiki-core.md
git commit -m "feat(v3): rewrite wiki-core skill — wiki/=identity, works/=knowledge, dedup, self-reflect"
```

---

## Task 7: Version bump a 3.0.0

**Files:**
- Modify: `README.md`
- Modify: `DESIGN.md`

- [ ] **Step 1: Aggiorna il §layers in DESIGN.md**

Trova la sezione con la tabella dei layer e sostituisci:

```markdown
| Layer | Description | Nature |
|-------|-------------|--------|
| **Vector Memory** (LanceDB) | Automatic semantic retrieval | Implicit, rebuildable |
| **Level 1** (wiki/) | Agent identity and consciousness: values, style, behavioral patterns | Explicit, permanent |
| **Level 2** (wiki-works/) | Domain knowledge: research, concepts, competencies by topic | Explicit, evolving |
```

Rimuovi la sezione "Criteria for merging into wiki/" (non esiste più in v3).

- [ ] **Step 2: Aggiorna README.md**

Aggiungi in cima al changelog:

```markdown
## v3.0.0 — Identity Layer + Semantic Deduplication

- **wiki/ resemanticized**: wiki/ è ora il layer identità/coscienza dell'agente (valori, stile, pattern comportamentali). wiki-works/ è il layer conoscenza. La promozione non esiste più.
- **Semantic deduplication**: `lint --full` rileva duplicati semantici via cosine similarity. Similarity ≥ 0.90 → auto-merge candidato. 0.75–0.90 → warning. Configurabile via `thresholds.dedup_auto` e `thresholds.dedup_warn`.
- **Self-reflection autonoma**: `wiki.py behavior-log` logga correzioni comportamentali. `wiki.py self-reflect` aggiorna autonomamente `wiki/identity/` quando un pattern supera la soglia (`self_reflection.correction_threshold`, default 3). Nessuna approvazione umana richiesta.
- **Nessun rollback problem**: wiki/ e wiki-works/ non si incrociano mai — eliminata la promozione irreversibile.
```

- [ ] **Step 3: Esegui la suite completa**

```
py -m pytest tests/ -v
```
Expected: tutti PASSED

- [ ] **Step 4: Commit finale**

```
git add README.md DESIGN.md
git commit -m "feat: v3.0.0 — identity layer, semantic dedup, autonomous self-reflection"
git tag v3.0.0
```

---

## Self-Review

**Copertura spec:**
- ✅ wiki/=identity, wiki-works/=knowledge — Task 6 (skill) + Task 7 (DESIGN)
- ✅ Deduplicazione semantica pairwise — Task 1
- ✅ Auto-merge agent-side — Task 6 (skill §lint)
- ✅ Soglie configurabili — Task 5
- ✅ Self-reflection autonoma senza approvazione umana — Task 3 + Task 4
- ✅ Behavior log — Task 3 + Task 4
- ✅ wiki/ identity pages non confrontate con wiki-works/ — Task 1 (test_find_semantic_duplicates_skips_wiki_identity)
- ✅ Version bump 3.0.0 — Task 7

**Placeholder scan:** nessun TBD, nessun "implement later". Ogni step ha codice completo.

**Coerenza tipi:**
- `find_semantic_duplicates` ritorna `list[dict]` con chiavi `page_a, page_b, similarity, action` — usate coerentemente in Tasks 1, 2, 6
- `run_self_reflect` ritorna `dict` con `op, patterns_found, updates` — coerente con cmd_self_reflect in Task 4
- `log_behavior(workspace: str, event: str)` — coerente tra Task 3 e Task 4
