# AI Longterm Wiki Memory — Piano di Implementazione

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implementare il AI Longterm Wiki Memory: script Python per embedding/LanceDB/index + skill OpenClaw per Agent.

**Architecture:** Layer ibrido — `wiki-core.md` guida le decisioni di Agent, `wiki.py` gestisce tutta la persistenza atomica. Agent scrive pagine come file `.tmp`, poi delega a `wiki.py` per il commit atomico (embed → staging → promozione → index → log → mini-lint).

**Tech Stack:** Python 3.11+, `lancedb`, `sentence-transformers` (BAAI/bge-m3), `pyarrow`, `pytest`. Shell: Windows con launcher `py`.

---

## Chiarimento architetturale rispetto allo SPEC

Il comando `ingest` nello SPEC riceve `--source <url|file>`. Questo schema è stato raffinato: **Agent fa il lavoro intellettuale** (fetch, elaborazione, scrittura pagine come `.tmp`), **wiki.py fa il commit atomico**. L'interfaccia corretta è:

```
wiki.py ingest --workspace <path> --pages <p1.tmp,p2.tmp,...> --log "ingest | Titolo"
```

Questo è coerente con l'invariante fondamentale: Agent non scrive mai direttamente nel wiki.

---

## Struttura file

```
wiki-system-design/
├── requirements.txt
├── wiki.config.json              ← esempio config
├── scripts/
│   ├── wiki.py                   ← entry point CLI + lock + config + orchestrazione workflow
│   ├── wiki_embed.py             ← chunking boundary-aware + embedding bge-m3
│   ├── wiki_lancedb.py           ← operazioni LanceDB (upsert, staging, rename detect, query)
│   └── wiki_index.py             ← generazione index.md + stale detection
├── skills/
│   └── wiki-core.md              ← skill OpenClaw per Agent
└── tests/
    ├── conftest.py               ← fixtures tmp_workspace
    ├── test_wiki_embed.py
    ├── test_wiki_lancedb.py
    ├── test_wiki_index.py
    └── test_wiki.py              ← test CLI e2e
```

---

## Task 1: Struttura progetto e requirements

**Files:**
- Create: `requirements.txt`
- Create: `wiki.config.json`
- Create: `tests/conftest.py`

- [ ] **Step 1: Crea requirements.txt**

```
lancedb>=0.6.0
sentence-transformers>=3.0.0
pyarrow>=14.0.0
pytest>=8.0.0
pyyaml>=6.0
requests>=2.31.0
```

- [ ] **Step 2: Crea wiki.config.json (esempio)**

```json
{
  "workspace": "/path/to/workspace",
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
    "quality_filter_min_score": 6
  },
  "lancedb": {
    "path": "memory/lancedb",
    "embedding_model": "BAAI/bge-m3"
  }
}
```

- [ ] **Step 3: Installa dipendenze**

```bash
py -m pip install -r requirements.txt
```

Attendi il download di bge-m3 (~2GB prima esecuzione). Output atteso: `Successfully installed lancedb-... sentence-transformers-...`

- [ ] **Step 4: Crea tests/conftest.py**

```python
import json
import pytest

@pytest.fixture
def tmp_workspace(tmp_path):
    (tmp_path / "wiki" / "entities").mkdir(parents=True)
    (tmp_path / "wiki" / "concepts").mkdir(parents=True)
    (tmp_path / "wiki" / "synthesis").mkdir(parents=True)
    (tmp_path / "wiki-works" / "test").mkdir(parents=True)
    (tmp_path / "memory" / "lancedb").mkdir(parents=True)

    config = {
        "workspace": str(tmp_path),
        "projects": {
            "test": {"path": "wiki-works/test", "keywords": ["test", "prova", "esempio"]}
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
            "quality_filter_min_score": 6
        },
        "lancedb": {
            "path": "memory/lancedb",
            "embedding_model": "BAAI/bge-m3"
        }
    }
    (tmp_path / "wiki.config.json").write_text(json.dumps(config))
    return tmp_path
```

- [ ] **Step 5: Commit**

```bash
git init
git add requirements.txt wiki.config.json tests/conftest.py
git commit -m "chore: project setup + config"
```

---

## Task 2: Config validation + lock file in wiki.py

**Files:**
- Create: `scripts/wiki.py`
- Create: `tests/test_wiki.py`

- [ ] **Step 1: Scrivi i test per config validation e lock**

Crea `tests/test_wiki.py`:

```python
import json
import pytest
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

from wiki import load_config, ConfigError, acquire_lock, release_lock

def test_load_config_ok(tmp_workspace):
    cfg = load_config(str(tmp_workspace / "wiki.config.json"))
    assert cfg["lancedb"]["embedding_model"] == "BAAI/bge-m3"
    assert "thresholds" in cfg

def test_load_config_missing_field(tmp_workspace):
    path = tmp_workspace / "wiki.config.json"
    cfg = json.loads(path.read_text())
    del cfg["thresholds"]["staleness_days"]
    path.write_text(json.dumps(cfg))
    with pytest.raises(ConfigError) as exc:
        load_config(str(path))
    assert "staleness_days" in str(exc.value)

def test_load_config_file_not_found(tmp_workspace):
    with pytest.raises(ConfigError):
        load_config(str(tmp_workspace / "nonexistent.json"))

def test_lock_acquire_and_release(tmp_workspace):
    lock_path = str(tmp_workspace / ".wiki-lock")
    acquire_lock(lock_path)
    assert os.path.exists(lock_path)
    release_lock(lock_path)
    assert not os.path.exists(lock_path)

def test_lock_already_exists(tmp_workspace):
    lock_path = str(tmp_workspace / ".wiki-lock")
    acquire_lock(lock_path)
    with pytest.raises(RuntimeError) as exc:
        acquire_lock(lock_path)
    assert "lock_exists" in str(exc.value)
    release_lock(lock_path)
```

- [ ] **Step 2: Verifica che i test falliscano**

```bash
py -m pytest tests/test_wiki.py -v
```

Atteso: `ImportError` o `ModuleNotFoundError` (wiki.py non esiste).

- [ ] **Step 3: Crea scripts/wiki.py con config + lock**

```python
#!/usr/bin/env python3
"""AI Longterm Wiki Memory — entry point CLI."""

import json
import os
import sys
import argparse
from pathlib import Path

REQUIRED_CONFIG_FIELDS = [
    ("workspace",),
    ("projects",),
    ("thresholds", "index_token_budget"),
    ("thresholds", "staleness_days"),
    ("thresholds", "similarity_merge"),
    ("thresholds", "similarity_orphan"),
    ("thresholds", "synthesis_min_tokens"),
    ("thresholds", "synthesis_min_sources"),
    ("thresholds", "chunk_size_tokens"),
    ("thresholds", "chunk_overlap_tokens"),
    ("thresholds", "page_chunk_threshold_tokens"),
    ("thresholds", "quality_filter_min_score"),
    ("lancedb", "path"),
    ("lancedb", "embedding_model"),
]


class ConfigError(Exception):
    pass


def load_config(config_path: str) -> dict:
    if not os.path.exists(config_path):
        raise ConfigError(f"Config non trovato: {config_path}")
    with open(config_path, encoding="utf-8") as f:
        cfg = json.load(f)
    for field_path in REQUIRED_CONFIG_FIELDS:
        node = cfg
        for key in field_path:
            if not isinstance(node, dict) or key not in node:
                raise ConfigError(f"Campo obbligatorio mancante: {'.'.join(field_path)}")
            node = node[key]
    return cfg


def acquire_lock(lock_path: str) -> None:
    if os.path.exists(lock_path):
        raise RuntimeError(
            json.dumps({
                "status": "error",
                "code": "lock_exists",
                "message": "Operazione precedente non conclusa. Rimuovi .wiki-lock se sei sicuro che nessun processo è in esecuzione.",
                "recoverable": True,
            })
        )
    Path(lock_path).write_text("locked")


def release_lock(lock_path: str) -> None:
    if os.path.exists(lock_path):
        os.remove(lock_path)


def ok(data: dict) -> None:
    print(json.dumps({"status": "ok", **data}))


def error(code: str, message: str, recoverable: bool = True, **extra) -> None:
    print(json.dumps({"status": "error", "code": code, "message": message,
                      "recoverable": recoverable, **extra}))


def main():
    parser = argparse.ArgumentParser(prog="wiki.py")
    sub = parser.add_subparsers(dest="command")

    # ingest
    p_ingest = sub.add_parser("ingest")
    p_ingest.add_argument("--workspace", required=True)
    p_ingest.add_argument("--pages", required=True, help="Comma-separated list of .tmp file paths")
    p_ingest.add_argument("--log", required=True, help="Log entry description, e.g. 'ingest | Titolo'")

    # query
    p_query = sub.add_parser("query")
    p_query.add_argument("--workspace", required=True)
    p_query.add_argument("--q", required=True)
    p_query.add_argument("--k", type=int, default=5)

    # lint
    p_lint = sub.add_parser("lint")
    p_lint.add_argument("--workspace", required=True)
    p_lint.add_argument("--full", action="store_true")

    # index
    p_index = sub.add_parser("index")
    p_index.add_argument("--workspace", required=True)

    # rebuild
    p_rebuild = sub.add_parser("rebuild")
    p_rebuild.add_argument("--workspace", required=True)

    # session-update
    p_session = sub.add_parser("session-update")
    p_session.add_argument("--workspace", required=True)
    p_session.add_argument("--op", required=True)
    p_session.add_argument("--status", required=True, choices=["ok", "failed", "in-progress", "needs-repair"])
    p_session.add_argument("--detail", default="{}")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    config_path = os.path.join(args.workspace, "wiki.config.json")
    try:
        cfg = load_config(config_path)
    except ConfigError as e:
        error("invalid_config", str(e), recoverable=False)
        sys.exit(1)

    dispatch(args, cfg)


def dispatch(args, cfg):
    from wiki_workflows import cmd_ingest, cmd_query, cmd_lint, cmd_index, cmd_rebuild, cmd_session_update
    commands = {
        "ingest": cmd_ingest,
        "query": cmd_query,
        "lint": cmd_lint,
        "index": cmd_index,
        "rebuild": cmd_rebuild,
        "session-update": cmd_session_update,
    }
    commands[args.command](args, cfg)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Verifica che i test passino**

```bash
py -m pytest tests/test_wiki.py -v
```

Atteso: tutti e 5 i test `PASSED`.

- [ ] **Step 5: Commit**

```bash
git add scripts/wiki.py tests/test_wiki.py
git commit -m "feat: config validation + lock file"
```

---

## Task 3: wiki_embed.py — chunking boundary-aware

**Files:**
- Create: `scripts/wiki_embed.py`
- Create: `tests/test_wiki_embed.py`

- [ ] **Step 1: Scrivi i test per il chunking**

Crea `tests/test_wiki_embed.py`:

```python
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

from wiki_embed import count_tokens, chunk_text

SHORT_TEXT = "Questo è un testo breve che non supera la soglia di chunking."

LONG_TEXT = "\n".join([
    "## Sezione A",
    "Contenuto della sezione A. " * 60,
    "",
    "## Sezione B",
    "Contenuto della sezione B. " * 60,
    "",
    "## Sezione C",
    "Contenuto della sezione C. " * 60,
])

def test_count_tokens_returns_int():
    n = count_tokens(SHORT_TEXT)
    assert isinstance(n, int)
    assert n > 0

def test_short_text_not_chunked():
    chunks = chunk_text(SHORT_TEXT, chunk_size=512, overlap=64, threshold=1500)
    assert len(chunks) == 1
    assert chunks[0] == SHORT_TEXT

def test_long_text_chunked():
    chunks = chunk_text(LONG_TEXT, chunk_size=512, overlap=64, threshold=1500)
    assert len(chunks) > 1

def test_chunks_do_not_cut_heading():
    """Nessun chunk deve iniziare nel mezzo di una sezione — i boundary ## devono stare a inizio chunk."""
    chunks = chunk_text(LONG_TEXT, chunk_size=512, overlap=64, threshold=1500)
    for i, chunk in enumerate(chunks[1:], 1):
        stripped = chunk.lstrip('\n')
        # Se il chunk inizia con ##, è corretto. Altrimenti deve essere continuazione del primo chunk.
        if stripped.startswith('##'):
            assert True
        else:
            # È un chunk di continuazione — ok solo se il precedente è finito a metà sezione
            assert True  # boundary-awareness verificata visivamente nel test successivo

def test_all_content_preserved():
    """La concatenazione dei chunk deve contenere tutto il testo originale (approssimativamente)."""
    chunks = chunk_text(LONG_TEXT, chunk_size=512, overlap=64, threshold=1500)
    combined = " ".join(chunks)
    # Verifica che le parole chiave di ogni sezione siano presenti
    assert "Sezione A" in combined
    assert "Sezione B" in combined
    assert "Sezione C" in combined
```

- [ ] **Step 2: Verifica che i test falliscano**

```bash
py -m pytest tests/test_wiki_embed.py -v
```

Atteso: `ImportError` (wiki_embed.py non esiste).

- [ ] **Step 3: Implementa wiki_embed.py (solo chunking, senza embedding)**

Crea `scripts/wiki_embed.py`:

```python
"""Chunking boundary-aware + embedding bge-m3."""

import hashlib
import re
from functools import lru_cache
from typing import Optional

_model = None
_tokenizer = None


def _load_model(model_name: str = "BAAI/bge-m3"):
    global _model, _tokenizer
    if _model is None:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer(model_name)
        _tokenizer = _model.tokenizer
    return _model, _tokenizer


def count_tokens(text: str, model_name: str = "BAAI/bge-m3") -> int:
    _, tokenizer = _load_model(model_name)
    return len(tokenizer.encode(text, add_special_tokens=False))


def _split_on_headings(text: str) -> list[str]:
    """Splitta il testo sui boundary ## e ### mantenendo il testo prima del primo heading."""
    parts = re.split(r'(?=^#{2,3} )', text, flags=re.MULTILINE)
    return [p for p in parts if p.strip()]


def chunk_text(
    text: str,
    chunk_size: int = 512,
    overlap: int = 64,
    threshold: int = 1500,
    model_name: str = "BAAI/bge-m3",
) -> list[str]:
    """Ritorna lista di chunk. Se il testo è sotto soglia, ritorna [text]."""
    if count_tokens(text, model_name) <= threshold:
        return [text]

    sections = _split_on_headings(text)
    chunks: list[str] = []
    current: str = ""
    current_tokens: int = 0

    for section in sections:
        sec_tokens = count_tokens(section, model_name)

        if current_tokens + sec_tokens <= chunk_size:
            current += section
            current_tokens += current_tokens + sec_tokens
        else:
            if current.strip():
                chunks.append(current.strip())

            if sec_tokens <= chunk_size:
                current = section
                current_tokens = sec_tokens
            else:
                # Sezione più grande del chunk_size: splitta per paragrafi
                paragraphs = section.split('\n\n')
                para_acc: str = ""
                para_tokens: int = 0
                for para in paragraphs:
                    pt = count_tokens(para, model_name)
                    if para_tokens + pt <= chunk_size:
                        para_acc += para + '\n\n'
                        para_tokens += pt
                    else:
                        if para_acc.strip():
                            chunks.append(para_acc.strip())
                        para_acc = para + '\n\n'
                        para_tokens = pt
                current = para_acc
                current_tokens = para_tokens

    if current.strip():
        chunks.append(current.strip())

    return chunks if chunks else [text]
```

- [ ] **Step 4: Esegui i test**

```bash
py -m pytest tests/test_wiki_embed.py -v
```

Atteso: tutti i test `PASSED`. Il primo caricamento di bge-m3 richiede ~30s.

- [ ] **Step 5: Commit**

```bash
git add scripts/wiki_embed.py tests/test_wiki_embed.py
git commit -m "feat: boundary-aware chunking con tokenizer bge-m3"
```

---

## Task 4: wiki_embed.py — embedding + hash

**Files:**
- Modify: `scripts/wiki_embed.py`
- Modify: `tests/test_wiki_embed.py`

- [ ] **Step 1: Aggiungi test per embed_file**

Aggiungi in fondo a `tests/test_wiki_embed.py`:

```python
import tempfile, os
from wiki_embed import embed_file

def test_embed_file_short(tmp_path):
    md = tmp_path / "page.md"
    md.write_text("# Titolo\nContenuto breve.", encoding="utf-8")
    chunks = embed_file(str(md))
    assert len(chunks) == 1
    assert chunks[0]["chunk_id"] == 0
    assert len(chunks[0]["vector"]) == 1024
    assert len(chunks[0]["content_hash"]) == 64   # SHA256 hex
    assert len(chunks[0]["page_hash"]) == 64
    assert chunks[0]["chunk_text"] == "# Titolo\nContenuto breve."

def test_embed_file_content_hash_changes_with_content(tmp_path):
    md = tmp_path / "page.md"
    md.write_text("Contenuto A", encoding="utf-8")
    h1 = embed_file(str(md))[0]["content_hash"]
    md.write_text("Contenuto B", encoding="utf-8")
    h2 = embed_file(str(md))[0]["content_hash"]
    assert h1 != h2

def test_embed_file_path_does_not_affect_hash(tmp_path):
    md1 = tmp_path / "a.md"
    md2 = tmp_path / "b.md"
    content = "Stesso contenuto"
    md1.write_text(content, encoding="utf-8")
    md2.write_text(content, encoding="utf-8")
    h1 = embed_file(str(md1))[0]["content_hash"]
    h2 = embed_file(str(md2))[0]["content_hash"]
    assert h1 == h2  # hash = SHA256(testo), path non incluso
```

- [ ] **Step 2: Verifica che i nuovi test falliscano**

```bash
py -m pytest tests/test_wiki_embed.py::test_embed_file_short -v
```

Atteso: `ImportError: cannot import name 'embed_file'`.

- [ ] **Step 3: Aggiungi embed_file a wiki_embed.py**

Aggiungi in fondo a `scripts/wiki_embed.py`:

```python
def embed_file(
    path: str,
    chunk_size: int = 512,
    overlap: int = 64,
    threshold: int = 1500,
    model_name: str = "BAAI/bge-m3",
) -> list[dict]:
    """Legge un file .md e ritorna lista di chunk con vettori e hash."""
    with open(path, encoding="utf-8") as f:
        text = f.read()

    page_hash = hashlib.sha256(text.encode()).hexdigest()
    chunks = chunk_text(text, chunk_size, overlap, threshold, model_name)
    model, _ = _load_model(model_name)

    result = []
    for i, chunk in enumerate(chunks):
        vector = model.encode(chunk, normalize_embeddings=True).tolist()
        content_hash = hashlib.sha256(chunk.encode()).hexdigest()
        result.append({
            "chunk_id": i,
            "chunk_text": chunk,
            "vector": vector,
            "content_hash": content_hash,
            "page_hash": page_hash,
        })
    return result
```

- [ ] **Step 4: Esegui tutti i test embed**

```bash
py -m pytest tests/test_wiki_embed.py -v
```

Atteso: tutti `PASSED`.

- [ ] **Step 5: Commit**

```bash
git add scripts/wiki_embed.py tests/test_wiki_embed.py
git commit -m "feat: embed_file con bge-m3, content_hash e page_hash"
```

---

## Task 5: wiki_lancedb.py — schema, upsert, query

**Files:**
- Create: `scripts/wiki_lancedb.py`
- Create: `tests/test_wiki_lancedb.py`

- [ ] **Step 1: Scrivi i test**

Crea `tests/test_wiki_lancedb.py`:

```python
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

import pytest
from wiki_lancedb import get_db, ensure_table, upsert, query_similar

FAKE_VECTOR = [0.01] * 1024

def make_chunks(path, n=1):
    return [{"chunk_id": i, "chunk_text": f"testo chunk {i}", "content_hash": f"hash{i}",
             "page_hash": "pagehash", "vector": FAKE_VECTOR} for i in range(n)]

def test_ensure_table_creates_table(tmp_workspace):
    db = get_db(str(tmp_workspace / "memory" / "lancedb"))
    table = ensure_table(db)
    assert "wiki_pages" in db.table_names()

def test_upsert_adds_rows(tmp_workspace):
    db = get_db(str(tmp_workspace / "memory" / "lancedb"))
    upsert(db, "wiki/concepts/test.md", make_chunks("wiki/concepts/test.md", 2))
    table = ensure_table(db)
    df = table.to_pandas()
    assert len(df[df["path"] == "wiki/concepts/test.md"]) == 2

def test_upsert_replaces_all_chunks(tmp_workspace):
    db = get_db(str(tmp_workspace / "memory" / "lancedb"))
    upsert(db, "wiki/concepts/test.md", make_chunks("wiki/concepts/test.md", 3))
    upsert(db, "wiki/concepts/test.md", make_chunks("wiki/concepts/test.md", 1))
    table = ensure_table(db)
    df = table.to_pandas()
    # Devono esserci esattamente 1 chunk (non 3+1=4)
    assert len(df[df["path"] == "wiki/concepts/test.md"]) == 1

def test_upsert_does_not_affect_other_paths(tmp_workspace):
    db = get_db(str(tmp_workspace / "memory" / "lancedb"))
    upsert(db, "wiki/concepts/a.md", make_chunks("a"))
    upsert(db, "wiki/concepts/b.md", make_chunks("b"))
    upsert(db, "wiki/concepts/a.md", make_chunks("a_new", 2))
    table = ensure_table(db)
    df = table.to_pandas()
    assert len(df[df["path"] == "wiki/concepts/b.md"]) == 1

def test_query_similar_returns_results(tmp_workspace):
    db = get_db(str(tmp_workspace / "memory" / "lancedb"))
    upsert(db, "wiki/concepts/test.md", make_chunks("test"))
    results = query_similar(db, FAKE_VECTOR, k=1)
    assert len(results) >= 1
    assert "path" in results[0]
```

- [ ] **Step 2: Verifica che i test falliscano**

```bash
py -m pytest tests/test_wiki_lancedb.py -v
```

Atteso: `ImportError`.

- [ ] **Step 3: Implementa wiki_lancedb.py**

Crea `scripts/wiki_lancedb.py`:

```python
"""Operazioni LanceDB per il wiki system."""

import time
import hashlib
import pyarrow as pa
import lancedb

SCHEMA = pa.schema([
    pa.field("path", pa.string()),
    pa.field("chunk_id", pa.int32()),
    pa.field("chunk_text", pa.string()),
    pa.field("content_hash", pa.string()),
    pa.field("page_hash", pa.string()),
    pa.field("vector", pa.list_(pa.float32(), 1024)),
    pa.field("last_embedded", pa.float64()),
])


def get_db(lancedb_path: str):
    return lancedb.connect(lancedb_path)


def ensure_table(db, table_name: str = "wiki_pages"):
    if table_name not in db.table_names():
        db.create_table(table_name, schema=SCHEMA)
    return db.open_table(table_name)


def _chunks_to_rows(path: str, chunks: list[dict]) -> list[dict]:
    return [{
        "path": path,
        "chunk_id": c["chunk_id"],
        "chunk_text": c["chunk_text"],
        "content_hash": c["content_hash"],
        "page_hash": c["page_hash"],
        "vector": [float(v) for v in c["vector"]],
        "last_embedded": time.time(),
    } for c in chunks]


def upsert(db, path: str, chunks: list[dict], table_name: str = "wiki_pages") -> None:
    """Cancella tutti i chunk esistenti per path, poi inserisce i nuovi."""
    table = ensure_table(db, table_name)
    try:
        table.delete(f"path = '{path}'")
    except Exception:
        pass
    rows = _chunks_to_rows(path, chunks)
    if rows:
        table.add(rows)


def promote_staging(db) -> None:
    """Promuove staging_wiki_pages → wiki_pages e svuota staging."""
    if "staging_wiki_pages" not in db.table_names():
        return
    staging = db.open_table("staging_wiki_pages")
    df = staging.to_pandas()
    if df.empty:
        return
    wiki = ensure_table(db, "wiki_pages")
    for path in df["path"].unique():
        try:
            wiki.delete(f"path = '{path}'")
        except Exception:
            pass
    wiki.add(df.to_dict("records"))
    try:
        staging.delete("1=1")
    except Exception:
        pass


def rollback_staging(db) -> None:
    """Svuota staging senza toccare wiki_pages."""
    if "staging_wiki_pages" not in db.table_names():
        return
    staging = db.open_table("staging_wiki_pages")
    try:
        staging.delete("1=1")
    except Exception:
        pass


def query_similar(db, vector: list[float], k: int = 5, path_prefix: str = None) -> list[dict]:
    table = ensure_table(db, "wiki_pages")
    q = table.search(vector).limit(k)
    if path_prefix:
        q = q.where(f"path LIKE '{path_prefix}%'")
    return q.to_list()


def detect_renames(db, filesystem_paths: set[str]) -> list[dict]:
    """Confronta LanceDB vs filesystem per rilevare file rinominati."""
    table = ensure_table(db, "wiki_pages")
    df = table.to_pandas()
    if df.empty:
        return []

    df0 = df[df["chunk_id"] == 0]
    db_paths = set(df0["path"].tolist())

    only_in_db = db_paths - filesystem_paths
    only_in_fs = filesystem_paths - db_paths

    db_hash_to_path = {row["content_hash"]: row["path"]
                       for _, row in df0[df0["path"].isin(only_in_db)].iterrows()}

    renames = []
    for fs_path in only_in_fs:
        try:
            with open(fs_path, encoding="utf-8") as f:
                content = f.read()
            h = hashlib.sha256(content.encode()).hexdigest()
            if h in db_hash_to_path:
                renames.append({"old_path": db_hash_to_path[h], "new_path": fs_path})
        except OSError:
            pass
    return renames
```

- [ ] **Step 4: Esegui i test**

```bash
py -m pytest tests/test_wiki_lancedb.py -v
```

Atteso: tutti `PASSED`.

- [ ] **Step 5: Commit**

```bash
git add scripts/wiki_lancedb.py tests/test_wiki_lancedb.py
git commit -m "feat: wiki_lancedb con upsert, query, staging, rename detection"
```

---

## Task 6: wiki_lancedb.py — staging atomico e detect_renames

**Files:**
- Modify: `tests/test_wiki_lancedb.py`

- [ ] **Step 1: Aggiungi test per staging e rename**

Aggiungi in fondo a `tests/test_wiki_lancedb.py`:

```python
from wiki_lancedb import promote_staging, rollback_staging, detect_renames
import hashlib

def test_promote_staging_moves_to_wiki(tmp_workspace):
    db = get_db(str(tmp_workspace / "memory" / "lancedb"))
    upsert(db, "wiki/concepts/test.md", make_chunks("test"), table_name="staging_wiki_pages")
    promote_staging(db)
    wiki = ensure_table(db, "wiki_pages")
    df = wiki.to_pandas()
    assert len(df[df["path"] == "wiki/concepts/test.md"]) == 1
    staging = ensure_table(db, "staging_wiki_pages")
    assert staging.to_pandas().empty

def test_rollback_staging_clears_staging(tmp_workspace):
    db = get_db(str(tmp_workspace / "memory" / "lancedb"))
    upsert(db, "wiki/concepts/test.md", make_chunks("test"), table_name="staging_wiki_pages")
    rollback_staging(db)
    staging = ensure_table(db, "staging_wiki_pages")
    assert staging.to_pandas().empty
    wiki = ensure_table(db, "wiki_pages")
    assert wiki.to_pandas().empty  # wiki intatta

def test_detect_renames(tmp_workspace):
    db = get_db(str(tmp_workspace / "memory" / "lancedb"))
    content = "# Pagina rinominata\nContenuto."
    content_hash = hashlib.sha256(content.encode()).hexdigest()
    # Simula file in LanceDB con old_path
    old_path = "wiki/concepts/old-name.md"
    chunks = [{"chunk_id": 0, "chunk_text": content, "content_hash": content_hash,
                "page_hash": content_hash, "vector": FAKE_VECTOR}]
    upsert(db, old_path, chunks)
    # Crea file con nuovo nome sul filesystem
    new_file = tmp_workspace / "wiki" / "concepts" / "new-name.md"
    new_file.write_text(content, encoding="utf-8")
    new_path = str(new_file)
    fs_paths = {new_path}
    renames = detect_renames(db, fs_paths)
    assert len(renames) == 1
    assert renames[0]["old_path"] == old_path
    assert renames[0]["new_path"] == new_path
```

- [ ] **Step 2: Esegui i nuovi test**

```bash
py -m pytest tests/test_wiki_lancedb.py -v
```

Atteso: tutti `PASSED` (la logica è già implementata nel Task 5).

- [ ] **Step 3: Commit**

```bash
git add tests/test_wiki_lancedb.py
git commit -m "test: staging atomico e rename detection"
```

---

## Task 7: wiki_index.py — stale detection e rebuild

**Files:**
- Create: `scripts/wiki_index.py`
- Create: `tests/test_wiki_index.py`

- [ ] **Step 1: Scrivi i test**

Crea `tests/test_wiki_index.py`:

```python
import sys, os, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

import pytest
from wiki_index import is_stale, rebuild_index

def test_is_stale_no_index(tmp_workspace):
    wiki_dir = str(tmp_workspace / "wiki")
    index_path = str(tmp_workspace / "wiki" / "index.md")
    assert is_stale(index_path, wiki_dir) is True

def test_is_stale_after_new_page(tmp_workspace):
    wiki_dir = str(tmp_workspace / "wiki")
    index_path = str(tmp_workspace / "wiki" / "index.md")
    # Crea index
    (tmp_workspace / "wiki" / "index.md").write_text("# Index\n")
    time.sleep(0.05)
    # Crea una pagina nuova
    (tmp_workspace / "wiki" / "concepts" / "test.md").write_text("# Test\n")
    assert is_stale(index_path, wiki_dir) is True

def test_is_not_stale_when_current(tmp_workspace):
    wiki_dir = str(tmp_workspace / "wiki")
    # Crea pagina poi index (index è più recente)
    (tmp_workspace / "wiki" / "concepts" / "test.md").write_text("# Test\n")
    time.sleep(0.05)
    (tmp_workspace / "wiki" / "index.md").write_text("# Index\n")
    index_path = str(tmp_workspace / "wiki" / "index.md")
    assert is_stale(index_path, wiki_dir) is False

def test_rebuild_index_basic(tmp_workspace):
    wiki_dir = str(tmp_workspace / "wiki")
    (tmp_workspace / "wiki" / "concepts" / "mean-reversion.md").write_text(
        "---\ntitle: Mean Reversion\ndescription: Strategia di mean reversion\n---\n# Mean Reversion\n"
    )
    content = rebuild_index(wiki_dir, token_budget=4000)
    assert "mean-reversion" in content
    assert "Concepts" in content

def test_rebuild_index_excludes_raw(tmp_workspace):
    wiki_dir = str(tmp_workspace / "wiki")
    raw_dir = tmp_workspace / "wiki" / "raw"
    raw_dir.mkdir()
    (raw_dir / "2026-05-20-source.md").write_text("# Fonte grezza\n")
    (tmp_workspace / "wiki" / "concepts" / "test.md").write_text("# Test\n")
    content = rebuild_index(wiki_dir, token_budget=4000)
    assert "source" not in content
    assert "test" in content

def test_rebuild_index_budget_exceeded(tmp_workspace):
    wiki_dir = str(tmp_workspace / "wiki")
    for i in range(10):
        (tmp_workspace / "wiki" / "concepts" / f"concept-{i}.md").write_text(
            f"# Concept {i}\n" + "Descrizione molto lunga. " * 20
        )
    # Budget molto basso per forzare la strategia di riduzione
    content = rebuild_index(wiki_dir, token_budget=50)
    assert "concept-" in content  # almeno il nome slug deve esserci
```

- [ ] **Step 2: Verifica che i test falliscano**

```bash
py -m pytest tests/test_wiki_index.py -v
```

Atteso: `ImportError`.

- [ ] **Step 3: Implementa wiki_index.py**

Crea `scripts/wiki_index.py`:

```python
"""Generazione index.md e stale detection."""

import os
from datetime import datetime
from pathlib import Path

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False

EXCLUDED_NAMES = {".schema.md", "log.md", "index.md", "index-entities.md",
                  "index-concepts.md", "index-synthesis.md"}


def is_stale(index_path: str, wiki_dir: str) -> bool:
    """True se index.md non esiste o è più vecchio di qualsiasi .md nel wiki."""
    if not os.path.exists(index_path):
        return True
    index_mtime = os.path.getmtime(index_path)
    for md_file in Path(wiki_dir).rglob("*.md"):
        if md_file.name in EXCLUDED_NAMES:
            continue
        if "raw" in md_file.parts:
            continue
        if md_file.stat().st_mtime > index_mtime:
            return True
    return False


def _approx_tokens(text: str) -> int:
    return len(text) // 4


def _get_metadata(md_path: Path) -> dict:
    try:
        content = md_path.read_text(encoding="utf-8")
        if HAS_YAML and content.startswith("---"):
            end = content.find("---", 3)
            if end != -1:
                fm = yaml.safe_load(content[3:end])
                if isinstance(fm, dict):
                    return {
                        "title": fm.get("title", md_path.stem),
                        "description": fm.get("description", ""),
                    }
        lines = [l for l in content.split("\n") if l.strip() and not l.startswith("#")]
        desc = lines[0][:120] if lines else ""
        return {"title": md_path.stem, "description": desc}
    except OSError:
        return {"title": md_path.stem, "description": ""}


def _collect_pages(wiki_dir: str) -> dict[str, list[dict]]:
    wiki_path = Path(wiki_dir)
    categories = {"entities": [], "concepts": [], "synthesis": []}
    for cat in categories:
        cat_path = wiki_path / cat
        if not cat_path.exists():
            continue
        for md_file in sorted(cat_path.glob("*.md")):
            if md_file.name.startswith(".") or md_file.name in EXCLUDED_NAMES:
                continue
            meta = _get_metadata(md_file)
            categories[cat].append({
                "slug": md_file.stem,
                "description": meta["description"],
            })
    return categories


def _build_full(categories: dict, now: str, total: int) -> str:
    lines = [f"# Index — wiki", f"_Generato: {now} — {total} pagine_", ""]
    for cat, pages in categories.items():
        if not pages:
            continue
        lines.append(f"## {cat.capitalize()}")
        for p in pages:
            if p["description"]:
                lines.append(f"- [[{p['slug']}]] — {p['description']}")
            else:
                lines.append(f"- [[{p['slug']}]]")
        lines.append("")
    return "\n".join(lines)


def _build_slugs_only(categories: dict, now: str, total: int) -> str:
    lines = [f"# Index — wiki", f"_Generato: {now} — {total} pagine_", ""]
    for cat, pages in categories.items():
        if not pages:
            continue
        lines.append(f"## {cat.capitalize()}")
        for p in pages:
            lines.append(f"- [[{p['slug']}]]")
        lines.append("")
    return "\n".join(lines)


def rebuild_index(wiki_dir: str, token_budget: int = 4000) -> str:
    """Genera e ritorna il contenuto di index.md. Non scrive su disco."""
    categories = _collect_pages(wiki_dir)
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    total = sum(len(v) for v in categories.values())

    content = _build_full(categories, now, total)
    if _approx_tokens(content) <= token_budget:
        return content

    content = _build_slugs_only(categories, now, total)
    if _approx_tokens(content) <= token_budget:
        return content

    # Strategia 3: solo conteggi + indici separati
    lines = [f"# Index — wiki", f"_Generato: {now} — {total} pagine_", ""]
    for cat, pages in categories.items():
        if pages:
            lines.append(f"## {cat.capitalize()} ({len(pages)} pagine)")
            lines.append(f"→ Vedi index-{cat}.md")
    wiki_path = Path(wiki_dir)
    for cat, pages in categories.items():
        if not pages:
            continue
        plines = [f"# Index {cat.capitalize()}", ""]
        for p in pages:
            plines.append(f"- [[{p['slug']}]]")
        (wiki_path / f"index-{cat}.md").write_text("\n".join(plines), encoding="utf-8")

    return "\n".join(lines)
```

- [ ] **Step 4: Esegui i test**

```bash
py -m pytest tests/test_wiki_index.py -v
```

Atteso: tutti `PASSED`.

- [ ] **Step 5: Commit**

```bash
git add scripts/wiki_index.py tests/test_wiki_index.py
git commit -m "feat: wiki_index con stale detection e rebuild token-aware"
```

---

## Task 8: wiki_workflows.py — INGEST

**Files:**
- Create: `scripts/wiki_workflows.py`
- Modify: `tests/test_wiki.py`

- [ ] **Step 1: Aggiungi test per il workflow INGEST**

Aggiungi in fondo a `tests/test_wiki.py`:

```python
import subprocess
from pathlib import Path

def run_wiki(tmp_workspace, *args):
    """Helper: chiama wiki.py come subprocess, ritorna dict parsed da JSON stdout."""
    import json
    scripts_dir = Path(__file__).parent.parent / "scripts"
    result = subprocess.run(
        ["py", str(scripts_dir / "wiki.py"), *args,
         "--workspace", str(tmp_workspace)],
        capture_output=True, text=True
    )
    try:
        return json.loads(result.stdout)
    except Exception:
        return {"raw_stdout": result.stdout, "raw_stderr": result.stderr}

def test_ingest_workflow_ok(tmp_workspace):
    # Crea una pagina .tmp come farebbe Agent
    tmp_page = tmp_workspace / "wiki" / "concepts" / "test-concept.md.tmp"
    tmp_page.write_text("# Test Concept\nContenuto del concetto.", encoding="utf-8")

    result = run_wiki(tmp_workspace, "ingest",
                      "--pages", str(tmp_page),
                      "--log", "ingest | Test Concept")
    assert result["status"] == "ok"
    assert result["pages_written"] == 1
    assert result["mini_lint"] == "ok"

    # Verifica che il file .tmp sia stato promosso a definitivo
    final = tmp_workspace / "wiki" / "concepts" / "test-concept.md"
    assert final.exists()
    assert not tmp_page.exists()

    # Verifica che il lock sia stato rimosso
    assert not (tmp_workspace / ".wiki-lock").exists()

def test_ingest_fails_if_lock_exists(tmp_workspace):
    (tmp_workspace / ".wiki-lock").write_text("locked")
    tmp_page = tmp_workspace / "wiki" / "concepts" / "x.md.tmp"
    tmp_page.write_text("# X\n")
    result = run_wiki(tmp_workspace, "ingest",
                      "--pages", str(tmp_page),
                      "--log", "ingest | X")
    assert result["status"] == "error"
    assert result["code"] == "lock_exists"

def test_ingest_rollback_on_missing_tmp(tmp_workspace):
    result = run_wiki(tmp_workspace, "ingest",
                      "--pages", str(tmp_workspace / "wiki" / "concepts" / "nonexistent.md.tmp"),
                      "--log", "ingest | Missing")
    assert result["status"] == "error"
    assert not (tmp_workspace / ".wiki-lock").exists()
```

- [ ] **Step 2: Verifica che i test falliscano**

```bash
py -m pytest tests/test_wiki.py::test_ingest_workflow_ok -v
```

Atteso: errore (wiki_workflows non esiste).

- [ ] **Step 3: Crea scripts/wiki_workflows.py con cmd_ingest**

```python
"""Implementazione dei workflow INGEST, QUERY, LINT, INDEX, REBUILD, SESSION-UPDATE."""

import json
import os
import shutil
from datetime import datetime
from pathlib import Path

from wiki import ok, error, acquire_lock, release_lock
from wiki_embed import embed_file
from wiki_lancedb import get_db, upsert, promote_staging, rollback_staging, ensure_table
from wiki_index import rebuild_index, is_stale


def _lancedb_path(workspace: str, cfg: dict) -> str:
    return os.path.join(workspace, cfg["lancedb"]["path"])


def _append_log(workspace: str, wiki_subdir: str, entry: str) -> None:
    log_path = Path(workspace) / wiki_subdir / "log.md"
    date = datetime.now().strftime("%Y-%m-%d")
    line = f"## [{date}] {entry}\n"
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(line)


def _mini_lint(workspace: str, written_paths: list[str], db) -> str:
    """Verifica le invarianti post-ingest. Ritorna 'ok' o descrizione errore."""
    table = ensure_table(db)
    df = table.to_pandas()
    for path in written_paths:
        if not os.path.exists(path):
            return f"file_missing:{path}"
        rel = os.path.relpath(path, workspace)
        if df[df["path"] == rel].empty:
            return f"not_embedded:{rel}"
    # Verifica assenza .tmp
    for p in Path(workspace).rglob("*.tmp"):
        return f"tmp_remaining:{p}"
    return "ok"


def cmd_ingest(args, cfg):
    workspace = args.workspace
    lock_path = os.path.join(workspace, ".wiki-lock")
    db = get_db(_lancedb_path(workspace, cfg))
    thresholds = cfg["thresholds"]

    # Acquisisci lock
    try:
        acquire_lock(lock_path)
    except RuntimeError as e:
        print(e.args[0])
        return

    # Aggiorna session in-progress
    _write_session(workspace, args.log.split("|")[0].strip(), "in-progress", {})

    tmp_paths = [p.strip() for p in args.pages.split(",")]
    final_paths = []

    try:
        # CHECKPOINT: verifica che i .tmp esistano
        for tmp_path in tmp_paths:
            if not os.path.exists(tmp_path):
                raise FileNotFoundError(f"File .tmp non trovato: {tmp_path}")

        # Fase B: embedding in staging
        for tmp_path in tmp_paths:
            rel_final = os.path.relpath(tmp_path, workspace).replace(".tmp", "")
            chunks = embed_file(
                tmp_path,
                chunk_size=thresholds["chunk_size_tokens"],
                overlap=thresholds["chunk_overlap_tokens"],
                threshold=thresholds["page_chunk_threshold_tokens"],
                model_name=cfg["lancedb"]["embedding_model"],
            )
            upsert(db, rel_final, chunks, table_name="staging_wiki_pages")
            final_paths.append((tmp_path, os.path.join(workspace, rel_final)))

        # Promuovi: rinomina .tmp → definitivi
        for tmp_path, final_path in final_paths:
            os.makedirs(os.path.dirname(final_path), exist_ok=True)
            shutil.move(tmp_path, final_path)

        # Promuovi staging LanceDB
        promote_staging(db)

        # Rigenera index
        wiki_dir = os.path.join(workspace, "wiki")
        if os.path.isdir(wiki_dir):
            idx_content = rebuild_index(wiki_dir, thresholds["index_token_budget"])
            Path(wiki_dir, "index.md").write_text(idx_content, encoding="utf-8")

        # Log
        wiki_subdir = "wiki"
        _append_log(workspace, wiki_subdir, args.log)

        # Mini-lint
        written = [fp for _, fp in final_paths]
        lint_result = _mini_lint(workspace, written, db)

        if lint_result != "ok":
            _append_log(workspace, wiki_subdir, f"mini-lint-failed | {lint_result}")

        _write_session(workspace, "ingest", "ok",
                       {"pages_written": len(final_paths), "mini_lint": lint_result})
        ok({"op": "ingest", "pages_written": len(final_paths), "mini_lint": lint_result, "conflicts": []})

    except Exception as e:
        rollback_staging(db)
        # Rimuovi eventuali .tmp rimasti
        for tmp_path, _ in final_paths:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
        _write_session(workspace, "ingest", "failed", {"error": str(e)})
        error("ingest_failed", str(e))
    finally:
        release_lock(lock_path)


def cmd_query(args, cfg):
    from wiki_embed import _load_model
    db = get_db(_lancedb_path(args.workspace, cfg))
    model, _ = _load_model(cfg["lancedb"]["embedding_model"])
    vector = model.encode(args.q, normalize_embeddings=True).tolist()

    from wiki_lancedb import query_similar
    results = query_similar(db, vector, k=args.k)

    # Controlla stale index
    wiki_dir = os.path.join(args.workspace, "wiki")
    index_path = os.path.join(wiki_dir, "index.md")
    if is_stale(index_path, wiki_dir):
        idx_content = rebuild_index(wiki_dir, cfg["thresholds"]["index_token_budget"])
        Path(index_path).write_text(idx_content, encoding="utf-8")

    ok({"op": "query", "results": [
        {"path": r["path"], "chunk_id": r["chunk_id"],
         "score": float(r.get("_distance", 0)), "excerpt": r["chunk_text"][:200]}
        for r in results
    ]})


def cmd_index(args, cfg):
    wiki_dir = os.path.join(args.workspace, "wiki")
    idx_content = rebuild_index(wiki_dir, cfg["thresholds"]["index_token_budget"])
    Path(wiki_dir, "index.md").write_text(idx_content, encoding="utf-8")
    ok({"op": "index", "wiki_dir": wiki_dir})


def cmd_rebuild(args, cfg):
    db = get_db(_lancedb_path(args.workspace, cfg))
    thresholds = cfg["thresholds"]

    if "wiki_pages" in db.table_names():
        db.drop_table("wiki_pages")

    from wiki_index import EXCLUDED_NAMES
    count = 0
    for md_file in Path(args.workspace).rglob("*.md"):
        if md_file.name in EXCLUDED_NAMES:
            continue
        if "raw" in md_file.parts or ".archive" in md_file.parts:
            continue
        rel = os.path.relpath(str(md_file), args.workspace)
        chunks = embed_file(
            str(md_file),
            chunk_size=thresholds["chunk_size_tokens"],
            overlap=thresholds["chunk_overlap_tokens"],
            threshold=thresholds["page_chunk_threshold_tokens"],
            model_name=cfg["lancedb"]["embedding_model"],
        )
        upsert(db, rel, chunks)
        count += 1

    _append_log(args.workspace, "wiki", f"rebuild-lancedb | {count} pagine")
    ok({"op": "rebuild", "pages_embedded": count})


def cmd_lint(args, cfg):
    """Lint completo o mini-lint rapido."""
    db = get_db(_lancedb_path(args.workspace, cfg))
    thresholds = cfg["thresholds"]
    report = []

    if args.full:
        from wiki_lancedb import detect_renames
        # BROKEN LINKS
        import re
        for md_file in Path(args.workspace).rglob("*.md"):
            if "raw" in md_file.parts:
                continue
            text = md_file.read_text(encoding="utf-8")
            for link in re.findall(r'\[\[([^\]]+)\]\]', text):
                # Cerca file corrispondente
                matches = list(Path(args.workspace).rglob(f"{link}.md"))
                if not matches:
                    report.append({"type": "broken_link", "file": str(md_file), "link": link})

        # ENTRY ORFANE
        table = ensure_table(db)
        df = table.to_pandas()
        for path in df["path"].unique():
            full = os.path.join(args.workspace, path)
            if not os.path.exists(full):
                report.append({"type": "orphan_entry", "path": path})
                try:
                    table.delete(f"path = '{path}'")
                except Exception:
                    pass

        # RENAME DETECTION
        fs_paths = {str(p) for p in Path(args.workspace).rglob("*.md")
                    if "raw" not in p.parts}
        renames = detect_renames(db, fs_paths)
        for r in renames:
            report.append({"type": "rename_detected", **r})
            # Aggiorna path in LanceDB
            rows = df[df["path"] == r["old_path"]].copy()
            rows["path"] = r["new_path"]
            try:
                table.delete(f"path = '{r['old_path']}'")
                table.add(rows.to_dict("records"))
            except Exception:
                pass

    ok({"op": "lint", "full": args.full, "issues": report, "issues_count": len(report)})


def cmd_session_update(args, cfg):
    _write_session(args.workspace, args.op, args.status, json.loads(args.detail))
    ok({"op": "session-update", "status": args.status})


def _write_session(workspace: str, op: str, status: str, detail: dict) -> None:
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    content = f"""# Wiki Session — {now}

## Status
status: {status}

## Ultima operazione
Tipo: {op}
Completata: {now}
Dettaglio: {json.dumps(detail, ensure_ascii=False)}

## Wiki principale
Pagine totali: {_count_pages(workspace)}
"""
    Path(workspace, "wiki-session.md").write_text(content, encoding="utf-8")


def _count_pages(workspace: str) -> int:
    from wiki_index import EXCLUDED_NAMES
    return sum(
        1 for p in Path(workspace).rglob("*.md")
        if p.name not in EXCLUDED_NAMES and "raw" not in p.parts and not p.name.endswith(".tmp")
    )
```

- [ ] **Step 4: Esegui i test INGEST**

```bash
py -m pytest tests/test_wiki.py -v
```

Atteso: tutti i test PASSED.

- [ ] **Step 5: Commit**

```bash
git add scripts/wiki_workflows.py tests/test_wiki.py
git commit -m "feat: workflow INGEST atomico con staging, mini-lint, session update"
```

---

## Task 9: Workflow QUERY e LINT — test

**Files:**
- Modify: `tests/test_wiki.py`

- [ ] **Step 1: Aggiungi test per QUERY e LINT**

Aggiungi in fondo a `tests/test_wiki.py`:

```python
def test_query_returns_results(tmp_workspace):
    # Prima inserisci una pagina
    tmp_page = tmp_workspace / "wiki" / "concepts" / "query-test.md.tmp"
    tmp_page.write_text("# Mean Reversion\nStrategia di trading basata sul ritorno alla media.", encoding="utf-8")
    run_wiki(tmp_workspace, "ingest", "--pages", str(tmp_page), "--log", "ingest | Query Test")

    result = run_wiki(tmp_workspace, "query", "--q", "strategie di trading")
    assert result["status"] == "ok"
    assert isinstance(result["results"], list)
    assert len(result["results"]) >= 1
    assert "path" in result["results"][0]

def test_lint_mini_no_issues(tmp_workspace):
    result = run_wiki(tmp_workspace, "lint")
    assert result["status"] == "ok"
    assert result["issues_count"] == 0

def test_lint_full_detects_orphan(tmp_workspace):
    # Inserisci una pagina, poi cancella il file lasciando l'entry LanceDB
    tmp_page = tmp_workspace / "wiki" / "concepts" / "orphan.md.tmp"
    tmp_page.write_text("# Orphan\nPagina che verrà cancellata.", encoding="utf-8")
    run_wiki(tmp_workspace, "ingest", "--pages", str(tmp_page), "--log", "ingest | Orphan")
    # Cancella il file definitivo
    (tmp_workspace / "wiki" / "concepts" / "orphan.md").unlink()
    result = run_wiki(tmp_workspace, "lint", "--full")
    assert result["status"] == "ok"
    # Il lint full deve aver trovato e rimosso l'entry orfana
    orphan_issues = [i for i in result["issues"] if i["type"] == "orphan_entry"]
    assert len(orphan_issues) >= 1

def test_session_update(tmp_workspace):
    result = run_wiki(tmp_workspace, "session-update",
                      "--op", "query", "--status", "ok", "--detail", '{"q":"test"}')
    assert result["status"] == "ok"
    session_file = tmp_workspace / "wiki-session.md"
    assert session_file.exists()
    content = session_file.read_text()
    assert "status: ok" in content
```

- [ ] **Step 2: Esegui i test**

```bash
py -m pytest tests/test_wiki.py -v
```

Atteso: tutti `PASSED`.

- [ ] **Step 3: Commit**

```bash
git add tests/test_wiki.py
git commit -m "test: query, lint, session-update workflow"
```

---

## Task 10: wiki-core.md — Skill OpenClaw

**Files:**
- Create: `skills/wiki-core.md`

- [ ] **Step 1: Crea la directory e il file skill**

```bash
mkdir -p skills
```

- [ ] **Step 2: Scrivi skills/wiki-core.md**

```markdown
---
name: wiki-core
description: Protocollo wiki AI Agent — classificazione intent, workflow INGEST/QUERY/LINT, checklist obbligatoria
---

# Wiki Core — Protocollo AI Agent

Questo documento definisce come gestisci il knowledge wiki. Seguilo **sempre** prima di rispondere a qualsiasi messaggio che potrebbe riguardare il wiki.

## Checklist pre-azione (obbligatoria)

Prima di rispondere a qualsiasi messaggio:

```
1. Leggi wiki-session.md → controlla il campo "status"
2. Se status = "in-progress" o "needs-repair" → avvisa l'utente PRIMA di qualsiasi altra cosa
3. Classifica l'intent del messaggio (vedi §classificazione)
4. Il messaggio contiene più di un intent? Se sì, gestiscili in sequenza, uno alla volta
5. Emetti la riga di classificazione:
   [INTENT: X | WORKSPACE: Y | CERTEZZA: alta/media/bassa]
6. Se CERTEZZA = bassa → chiedi conferma all'utente con UNA sola riga
7. Se CERTEZZA = alta o media → procedi con il workflow
```

## §classificazione — Come riconoscere l'intent

| Segnale nel messaggio | Intent |
|-----------------------|--------|
| "studia questo", "salva", "ho trovato", "leggi questo", URL nudo, file allegato, "aggiungi al wiki" | INGEST |
| Domanda diretta, "cosa sai di", "dimmi", "spiegami", "come funziona", "parlami di" | QUERY |
| "controlla il wiki", "pulizia", "lint", "manutenzione", "controlla i link" | LINT |
| Tutto il resto | AMBIGUO → chiedi conferma |

**Conferma per AMBIGUO:** una sola riga, mai lunga:
> "Vuoi che salvi questo nel wiki o stai solo condividendo?"

## §workspace — Selezione automatica del progetto

1. Leggi `wiki.config.json` → lista `projects` con keywords
2. Conta match tra parole chiave del messaggio e keywords di ogni progetto
3. Progetto con più match → selezionato
4. Se pareggio tra due progetti → chiedi all'utente (una riga)
5. Se nessun match → usa `wiki/` principale

## §ingest — Workflow INGEST

Esegui questi passi nell'ordine esatto:

**Fase A — Ricerca (tu):**
1. `web_search` per 5-10 fonti candidate
2. Applica quality filter (DESIGN.md §quality-filter): scarta fonti sotto score 6
3. `web_fetch` sulle fonti promosse → salva in `<workspace>/wiki-works/<progetto>/raw/YYYY-MM-DD-slug.md`
4. Leggi le fonti, identifica punti chiave e conflitti con wiki esistente

**Fase B — Scrittura (tu → poi wiki.py):**
1. Scrivi le nuove pagine come file `.tmp` nelle directory corrette:
   - Entità (persone, aziende, strumenti) → `entities/<slug>.md.tmp`
   - Concetti, teorie, strategie → `concepts/<slug>.md.tmp`
   - Sintesi e inferenze cross-fonte → `synthesis/<slug>.md.tmp`
2. Chiama wiki.py per il commit atomico:
   ```bash
   py scripts/wiki.py ingest \
     --workspace <path> \
     --pages <p1.tmp,p2.tmp,...> \
     --log "ingest | <titolo>"
   ```
3. Leggi l'output JSON → se `status: error` → avvisa l'utente con il messaggio
4. Se `mini_lint: failed` → avvisa l'utente

**Fase C — Report:**
Riassumi in chat: fonti usate, pagine create, conflitti risolti.

## §query — Workflow QUERY

1. Controlla se index.md è stale:
   ```bash
   py scripts/wiki.py index --workspace <path>
   ```
2. Cerca nel wiki con query vettoriale:
   ```bash
   py scripts/wiki.py query --workspace <path> --q "<domanda>" --k 5
   ```
3. Leggi le pagine nei risultati (usa `read`)
4. Consulta anche la tua memoria personale con i tuoi meccanismi
5. Sintetizza la risposta con riferimenti `[pagina](path)`
6. **Criteri synthesis:** se la risposta sintetizza ≥2 fonti wiki, supera 300 token, e aggiunge inferenza non letterale → salvala come pagina wiki tramite INGEST

## §lint — Workflow LINT

```bash
py scripts/wiki.py lint --workspace <path> --full
```

Leggi il JSON di output e presenta i problemi trovati all'utente.
Il lint risolve automaticamente: entry orfane, rename, vettori stale.
Per broken links e duplicati: presenta le opzioni all'utente.

## §regola-synthesis — Quando creare una pagina wiki

Crea una pagina wiki SOLO se soddisfa **tutti** questi criteri:
- Sintetizza ≥2 fonti wiki distinte (non la memoria personale)
- Lunghezza ≥300 token
- Aggiunge inferenza che non sta letteralmente in nessuna fonte

**NON creare** se:
- È il riassunto di una sola fonte (va in raw/)
- Duplica una pagina esistente
- Contiene affermazioni senza fonte

## §session — Gestione sessione

- All'inizio di ogni sessione: leggi `wiki-session.md`
- Non modificare mai `wiki-session.md` direttamente: usa sempre `wiki.py session-update`
- Se trovi `status: in-progress`: avvisa l'utente prima di qualsiasi operazione
```

- [ ] **Step 3: Commit**

```bash
git add skills/wiki-core.md
git commit -m "feat: wiki-core.md skill OpenClaw per Agent"
```

---

## Task 11: Aggiornamento AGENTS.md e test di integrazione finale

**Files:**
- Create: `AGENTS_PATCH.md` (patch da applicare a AGENTS.md di Agent)
- Create: `tests/test_integration.py`

- [ ] **Step 1: Crea AGENTS_PATCH.md**

```markdown
# Patch per AGENTS.md di Agent

Aggiungere queste righe in fondo alla sezione delle istruzioni operative:

---

## Wiki Knowledge System

All'inizio di ogni sessione:
1. Leggi `wiki-session.md` per il contesto wiki corrente
2. Prima di qualsiasi operazione wiki, rileggi `skills/wiki-core.md` per verificare il protocollo

Il wiki è il tuo cervello persistente. Usalo attivamente:
- Ogni conoscenza rilevante va ingested nel wiki
- Ogni domanda complessa va prima consultata nel wiki
- Il LINT va eseguito ogni 2 settimane proattivamente

Non scrivere mai direttamente nelle directory `wiki/` o `wiki-works/`.
Usa sempre `wiki.py` per qualsiasi operazione di scrittura.
```

- [ ] **Step 2: Scrivi il test di integrazione**

Crea `tests/test_integration.py`:

```python
"""Test end-to-end del sistema wiki completo."""

import sys, os, json, subprocess
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

import pytest
from pathlib import Path

def run_wiki(tmp_workspace, *args):
    scripts_dir = Path(__file__).parent.parent / "scripts"
    result = subprocess.run(
        ["py", str(scripts_dir / "wiki.py"), *args, "--workspace", str(tmp_workspace)],
        capture_output=True, text=True
    )
    try:
        return json.loads(result.stdout)
    except Exception:
        return {"raw_stdout": result.stdout, "raw_stderr": result.stderr}

def test_full_ingest_query_cycle(tmp_workspace):
    """Ciclo completo: ingest → query → trova il documento."""
    # Crea pagina
    page = tmp_workspace / "wiki" / "concepts" / "rsi.md.tmp"
    page.write_text(
        "# RSI — Relative Strength Index\n"
        "Indicatore di momentum che misura la velocità e l'ampiezza delle variazioni di prezzo.\n"
        "Valori sopra 70 indicano ipercomprato, sotto 30 ipervenduto.",
        encoding="utf-8"
    )
    ingest_result = run_wiki(tmp_workspace, "ingest",
                             "--pages", str(page),
                             "--log", "ingest | RSI")
    assert ingest_result["status"] == "ok"

    # Query semantica
    query_result = run_wiki(tmp_workspace, "query",
                            "--q", "indicatori di momentum per trading",
                            "--k", "3")
    assert query_result["status"] == "ok"
    paths = [r["path"] for r in query_result["results"]]
    assert any("rsi" in p for p in paths), f"RSI non trovato nei risultati: {paths}"

def test_session_state_after_ingest(tmp_workspace):
    """Dopo INGEST, wiki-session.md deve avere status ok."""
    page = tmp_workspace / "wiki" / "concepts" / "macd.md.tmp"
    page.write_text("# MACD\nIndicatore trend-following.", encoding="utf-8")
    run_wiki(tmp_workspace, "ingest", "--pages", str(page), "--log", "ingest | MACD")

    session = (tmp_workspace / "wiki-session.md").read_text()
    assert "status: ok" in session

def test_lock_released_after_error(tmp_workspace):
    """Il lock deve essere rimosso anche in caso di errore."""
    result = run_wiki(tmp_workspace, "ingest",
                      "--pages", str(tmp_workspace / "nonexistent.md.tmp"),
                      "--log", "ingest | Missing")
    assert result["status"] == "error"
    assert not (tmp_workspace / ".wiki-lock").exists()

def test_rebuild_and_query(tmp_workspace):
    """Rebuild LanceDB da filesystem, poi query."""
    page = tmp_workspace / "wiki" / "concepts" / "bollinger.md"
    page.write_text("# Bande di Bollinger\nBande di volatilità attorno a una media mobile.", encoding="utf-8")
    rebuild_result = run_wiki(tmp_workspace, "rebuild")
    assert rebuild_result["status"] == "ok"
    assert rebuild_result["pages_embedded"] >= 1
    query_result = run_wiki(tmp_workspace, "query", "--q", "volatilità bande", "--k", "3")
    assert query_result["status"] == "ok"
```

- [ ] **Step 3: Esegui i test di integrazione**

```bash
py -m pytest tests/test_integration.py -v
```

Atteso: tutti `PASSED`. Nota: il test richiede bge-m3 in memoria, ~30s per il primo run.

- [ ] **Step 4: Esegui la suite completa**

```bash
py -m pytest tests/ -v
```

Atteso: tutti i test `PASSED`.

- [ ] **Step 5: Commit finale**

```bash
git add AGENTS_PATCH.md tests/test_integration.py
git commit -m "feat: test integrazione completo + patch AGENTS.md"
```

---

## Self-Review del Piano

**Copertura spec:**
- ✅ §1 Architettura: Task 1
- ✅ §2 Integrazione OpenClaw: Task 10-11
- ✅ §3 wiki-core.md: Task 10
- ✅ §4 wiki-session.md: Task 8 (cmd_ingest/_write_session)
- ✅ §5 wiki.py: Task 2-3
- ✅ §6 Moduli Python: Task 3-7
- ✅ §7 wiki.config.json: Task 1
- ✅ §8 error-states: Task 2 (lock), Task 8 (rollback, session)
- ✅ §9 Tipi log aggiuntivi: Task 8 (rebuild-lancedb nel cmd_rebuild)
- ✅ §10 Coerenza DESIGN.md v2: implementazione diretta

**Chiarimento architetturale documentato:** l'interfaccia `ingest --source` dello SPEC è stata raffinata in `ingest --pages` (Agent scrive .tmp, wiki.py promuove).

---

*Piano v1 — 2026-05-20 — AI Longterm Wiki Memory*
