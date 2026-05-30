# PDF Ingestion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Aggiungere supporto PDF multi-sorgente al sistema wiki tramite una cartella `pdf-inbox/` come hub unico, con estrazione testo via pdfplumber, change detection basata su SHA-256, e due nuovi comandi CLI (`scan-inbox`, `ingest-pdf`).

**Architecture:** Una cartella `pdf-inbox/` nel workspace raccoglie PDF da tutte le sorgenti (Telegram, CLI, drop manuale). Un nuovo modulo `wiki_pdf_watcher.py` rileva file nuovi/modificati via hash, estrae testo con pdfplumber, e deposita `.md` in `wiki-works/<project>/raw/`. I comandi `wiki.py scan-inbox` e `wiki.py ingest-pdf` espongono questo comportamento. Il pipeline `wiki.py ingest` non viene modificato.

**Tech Stack:** Python 3.10+, pdfplumber>=0.11.0, pytest, unittest.mock

---

## File Map

| File | Azione | Responsabilità |
|------|--------|----------------|
| `requirements.txt` | Modifica | Aggiunge pdfplumber |
| `tests/conftest.py` | Modifica | Aggiunge `pdf_inbox` alla fixture `tmp_workspace` |
| `scripts/wiki_pdf_watcher.py` | Crea | Tutte le funzioni PDF: hash, registry, extract, deposit, scan |
| `tests/test_pdf_watcher.py` | Crea | 9 test unitari per wiki_pdf_watcher |
| `scripts/wiki_workflows.py` | Modifica | Aggiunge `cmd_scan_inbox`, `cmd_ingest_pdf` |
| `scripts/wiki.py` | Modifica | Registra i due nuovi sottocomandi nell'argparser e nel dispatch |
| `wiki.config.json` | Modifica | Aggiunge campo `pdf_inbox.project_default` |
| `skills/wiki-core.md` | Modifica | Aggiunge sezione `§pdf-inbox` |
| `AGENTS_PATCH.md` | Modifica | Aggiunge regole agente per PDF inbox |
| `AGENTS_PATCH.it.md` | Modifica | Versione italiana delle stesse regole |

---

## Task 1: Dipendenza pdfplumber e aggiornamento conftest

**Files:**
- Modify: `requirements.txt`
- Modify: `tests/conftest.py`

- [ ] **Step 1: Aggiungi pdfplumber a requirements.txt**

```text
lancedb>=0.6.0
sentence-transformers>=3.0.0
pyarrow>=14.0.0
pandas>=2.0.0
pytest>=8.0.0
pyyaml>=6.0
requests>=2.31.0
pdfplumber>=0.11.0
```

- [ ] **Step 2: Installa la dipendenza**

```bash
pip install pdfplumber>=0.11.0
```

Atteso: installazione senza errori.

- [ ] **Step 3: Aggiorna `tests/conftest.py` — aggiungi `pdf_inbox` alla config e la cartella `pdf-inbox/`**

Sostituisci l'intero file con:

```python
import json
import pytest

@pytest.fixture
def tmp_workspace(tmp_path):
    (tmp_path / "wiki" / "entities").mkdir(parents=True)
    (tmp_path / "wiki" / "concepts").mkdir(parents=True)
    (tmp_path / "wiki" / "synthesis").mkdir(parents=True)
    (tmp_path / "wiki-works" / "test").mkdir(parents=True)
    (tmp_path / "wiki-works" / "test" / "raw").mkdir(parents=True)
    (tmp_path / "memory" / "lancedb").mkdir(parents=True)
    (tmp_path / "pdf-inbox").mkdir(parents=True)

    config = {
        "workspace": str(tmp_path),
        "projects": {
            "test": {"path": "wiki-works/test", "keywords": ["test", "prova", "esempio"]}
        },
        "pdf_inbox": {
            "project_default": "test"
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
    (tmp_path / "wiki.config.json").write_text(json.dumps(config, indent=2))
    return tmp_path
```

- [ ] **Step 4: Verifica che i test esistenti passino ancora**

```bash
pytest tests/ -v --ignore=tests/test_pdf_watcher.py -x
```

Atteso: tutti i test esistenti passano (37 passed).

- [ ] **Step 5: Commit**

```bash
git add requirements.txt tests/conftest.py
git commit -m "feat: add pdfplumber dependency and pdf-inbox workspace fixture"
```

---

## Task 2: Registry functions — compute_hash, load_registry, save_registry

**Files:**
- Create: `scripts/wiki_pdf_watcher.py`
- Create: `tests/test_pdf_watcher.py`

- [ ] **Step 1: Crea `tests/test_pdf_watcher.py` con i test per le funzioni registry**

```python
"""Tests for wiki_pdf_watcher."""

import hashlib
import json
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))


@pytest.fixture
def cfg(tmp_workspace):
    return json.loads((tmp_workspace / "wiki.config.json").read_text())


@pytest.fixture
def sample_pdf(tmp_workspace):
    """PDF fixture minimale (file binario fake per test di hash/registry)."""
    pdf_path = tmp_workspace / "pdf-inbox" / "paper1.pdf"
    pdf_path.write_bytes(b"%PDF-1.4 fake content for hashing")
    return pdf_path


# ── Registry tests ──────────────────────────────────────────────────────────

def test_compute_hash(sample_pdf):
    from wiki_pdf_watcher import compute_hash
    h = compute_hash(str(sample_pdf))
    assert h.startswith("sha256:")
    assert len(h) == 71  # len("sha256:") + 64 hex chars

def test_compute_hash_is_deterministic(sample_pdf):
    from wiki_pdf_watcher import compute_hash
    assert compute_hash(str(sample_pdf)) == compute_hash(str(sample_pdf))

def test_compute_hash_differs_on_content_change(tmp_workspace):
    from wiki_pdf_watcher import compute_hash
    p = tmp_workspace / "pdf-inbox" / "a.pdf"
    p.write_bytes(b"content A")
    h1 = compute_hash(str(p))
    p.write_bytes(b"content B")
    h2 = compute_hash(str(p))
    assert h1 != h2

def test_load_registry_returns_empty_dict_when_missing(tmp_workspace):
    from wiki_pdf_watcher import load_registry
    result = load_registry(str(tmp_workspace))
    assert result == {}

def test_registry_roundtrip(tmp_workspace):
    from wiki_pdf_watcher import load_registry, save_registry
    data = {"paper1.pdf": {"hash": "sha256:abc123", "status": "deposited"}}
    save_registry(str(tmp_workspace), data)
    assert load_registry(str(tmp_workspace)) == data

def test_registry_atomic_write_leaves_no_tmp_files(tmp_workspace):
    from wiki_pdf_watcher import save_registry
    save_registry(str(tmp_workspace), {"paper1.pdf": {"status": "deposited"}})
    tmp_files = list((tmp_workspace / "pdf-inbox").glob(".registry.*.tmp"))
    assert tmp_files == []
```

- [ ] **Step 2: Esegui i test — devono fallire con ModuleNotFoundError**

```bash
pytest tests/test_pdf_watcher.py -v
```

Atteso: `ModuleNotFoundError: No module named 'wiki_pdf_watcher'`

- [ ] **Step 3: Crea `scripts/wiki_pdf_watcher.py` con le sole funzioni registry**

```python
"""PDF inbox watcher: estrae testo da PDF e deposita in wiki-works/raw/."""

import hashlib
import json
import os
import tempfile
from datetime import datetime
from pathlib import Path

import pdfplumber

INBOX_DIR = "pdf-inbox"
REGISTRY_FILE = ".registry.json"


def compute_hash(pdf_path: str) -> str:
    """SHA-256 del file PDF."""
    h = hashlib.sha256()
    with open(pdf_path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return f"sha256:{h.hexdigest()}"


def load_registry(workspace: str) -> dict:
    """Legge pdf-inbox/.registry.json. Ritorna {} se non esiste."""
    path = Path(workspace) / INBOX_DIR / REGISTRY_FILE
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save_registry(workspace: str, data: dict) -> None:
    """Scrive .registry.json atomicamente via tempfile + os.replace."""
    inbox_dir = Path(workspace) / INBOX_DIR
    inbox_dir.mkdir(parents=True, exist_ok=True)
    target = inbox_dir / REGISTRY_FILE
    fd, tmp_path = tempfile.mkstemp(dir=str(inbox_dir), prefix=".registry.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, str(target))
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def extract_text(pdf_path: str) -> str:
    raise NotImplementedError


def deposit_raw(text: str, pdf_name: str, workspace: str, cfg: dict) -> str:
    raise NotImplementedError


def scan_inbox(workspace: str, cfg: dict) -> dict:
    raise NotImplementedError
```

- [ ] **Step 4: Esegui i test registry — devono passare**

```bash
pytest tests/test_pdf_watcher.py -v -k "hash or registry"
```

Atteso: 6 passed.

- [ ] **Step 5: Commit**

```bash
git add scripts/wiki_pdf_watcher.py tests/test_pdf_watcher.py
git commit -m "feat: wiki_pdf_watcher registry functions (compute_hash, load/save_registry)"
```

---

## Task 3: extract_text con pdfplumber

**Files:**
- Modify: `scripts/wiki_pdf_watcher.py`
- Modify: `tests/test_pdf_watcher.py`

- [ ] **Step 1: Aggiungi i test per `extract_text` in fondo a `tests/test_pdf_watcher.py`**

```python
# ── extract_text tests ───────────────────────────────────────────────────────

def test_extract_text_returns_text_from_pages(sample_pdf):
    from wiki_pdf_watcher import extract_text
    mock_page = MagicMock()
    mock_page.extract_text.return_value = "Hello World\nSecond line"
    with patch("wiki_pdf_watcher.pdfplumber") as mock_plumber:
        mock_plumber.open.return_value.__enter__.return_value.pages = [mock_page]
        result = extract_text(str(sample_pdf))
    assert "Hello World" in result
    assert "Second line" in result

def test_extract_text_joins_pages_with_double_newline(sample_pdf):
    from wiki_pdf_watcher import extract_text
    page1 = MagicMock()
    page1.extract_text.return_value = "Page one text"
    page2 = MagicMock()
    page2.extract_text.return_value = "Page two text"
    with patch("wiki_pdf_watcher.pdfplumber") as mock_plumber:
        mock_plumber.open.return_value.__enter__.return_value.pages = [page1, page2]
        result = extract_text(str(sample_pdf))
    assert result == "Page one text\n\nPage two text"

def test_scanned_pdf_no_text_returns_empty_string(sample_pdf):
    from wiki_pdf_watcher import extract_text
    mock_page = MagicMock()
    mock_page.extract_text.return_value = None
    with patch("wiki_pdf_watcher.pdfplumber") as mock_plumber:
        mock_plumber.open.return_value.__enter__.return_value.pages = [mock_page]
        result = extract_text(str(sample_pdf))
    assert result == ""
```

- [ ] **Step 2: Esegui i test — devono fallire con NotImplementedError**

```bash
pytest tests/test_pdf_watcher.py -v -k "extract"
```

Atteso: 3 failed con `NotImplementedError`.

- [ ] **Step 3: Implementa `extract_text` in `scripts/wiki_pdf_watcher.py`**

Sostituisci la funzione `extract_text`:

```python
def extract_text(pdf_path: str) -> str:
    """Estrae testo da PDF. Ritorna stringa vuota se nessun testo selezionabile."""
    text_parts = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)
    return "\n\n".join(text_parts)
```

- [ ] **Step 4: Esegui i test — devono passare**

```bash
pytest tests/test_pdf_watcher.py -v -k "extract"
```

Atteso: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add scripts/wiki_pdf_watcher.py tests/test_pdf_watcher.py
git commit -m "feat: wiki_pdf_watcher extract_text via pdfplumber"
```

---

## Task 4: deposit_raw

**Files:**
- Modify: `scripts/wiki_pdf_watcher.py`
- Modify: `tests/test_pdf_watcher.py`

- [ ] **Step 1: Aggiungi i test per `deposit_raw` in fondo a `tests/test_pdf_watcher.py`**

```python
# ── deposit_raw tests ────────────────────────────────────────────────────────

def test_deposit_raw_creates_file_in_raw_dir(tmp_workspace, cfg):
    from wiki_pdf_watcher import deposit_raw
    rel = deposit_raw("# Title\n\nAbstract here.", "paper1.pdf", str(tmp_workspace), cfg)
    out = tmp_workspace / rel.replace("/", os.sep)
    assert out.exists()

def test_deposit_raw_includes_frontmatter(tmp_workspace, cfg):
    from wiki_pdf_watcher import deposit_raw
    rel = deposit_raw("Some text", "paper1.pdf", str(tmp_workspace), cfg)
    content = (tmp_workspace / rel.replace("/", os.sep)).read_text(encoding="utf-8")
    assert "source: pdf" in content
    assert "original: paper1.pdf" in content
    assert "extracted_at:" in content

def test_deposit_raw_preserves_text(tmp_workspace, cfg):
    from wiki_pdf_watcher import deposit_raw
    rel = deposit_raw("Important content here.", "paper1.pdf", str(tmp_workspace), cfg)
    content = (tmp_workspace / rel.replace("/", os.sep)).read_text(encoding="utf-8")
    assert "Important content here." in content

def test_deposit_raw_uses_project_default(tmp_workspace, cfg):
    from wiki_pdf_watcher import deposit_raw
    rel = deposit_raw("text", "paper1.pdf", str(tmp_workspace), cfg)
    assert "wiki-works/test/raw/paper1.md" == rel
```

- [ ] **Step 2: Esegui i test — devono fallire con NotImplementedError**

```bash
pytest tests/test_pdf_watcher.py -v -k "deposit"
```

Atteso: 4 failed con `NotImplementedError`.

- [ ] **Step 3: Implementa `deposit_raw` in `scripts/wiki_pdf_watcher.py`**

Sostituisci la funzione `deposit_raw`:

```python
def deposit_raw(text: str, pdf_name: str, workspace: str, cfg: dict) -> str:
    """Salva testo estratto in wiki-works/<project>/raw/<stem>.md con frontmatter.
    Ritorna il path relativo al workspace (slash forward)."""
    project = cfg.get("pdf_inbox", {}).get("project_default", "")
    if not project:
        projects = cfg.get("projects", {})
        project = next(iter(projects), "default") if projects else "default"

    raw_dir = Path(workspace) / "wiki-works" / project / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    stem = Path(pdf_name).stem
    out_path = raw_dir / f"{stem}.md"

    now = datetime.now().isoformat(timespec="seconds")
    content = f"---\nsource: pdf\noriginal: {pdf_name}\nextracted_at: {now}\n---\n\n{text}"
    out_path.write_text(content, encoding="utf-8")

    return os.path.relpath(str(out_path), workspace).replace("\\", "/")
```

- [ ] **Step 4: Esegui i test — devono passare**

```bash
pytest tests/test_pdf_watcher.py -v -k "deposit"
```

Atteso: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add scripts/wiki_pdf_watcher.py tests/test_pdf_watcher.py
git commit -m "feat: wiki_pdf_watcher deposit_raw with frontmatter"
```

---

## Task 5: scan_inbox — orchestratore principale

**Files:**
- Modify: `scripts/wiki_pdf_watcher.py`
- Modify: `tests/test_pdf_watcher.py`

- [ ] **Step 1: Aggiungi i test per `scan_inbox` in fondo a `tests/test_pdf_watcher.py`**

```python
# ── scan_inbox tests ─────────────────────────────────────────────────────────

def test_scan_new_pdf_is_deposited(tmp_workspace, cfg, sample_pdf):
    from wiki_pdf_watcher import scan_inbox, load_registry
    with patch("wiki_pdf_watcher.extract_text", return_value="Extracted content"):
        result = scan_inbox(str(tmp_workspace), cfg)
    assert result["status"] == "ok"
    assert result["processed"] == 1
    assert result["failed"] == 0
    raw = tmp_workspace / "wiki-works" / "test" / "raw" / "paper1.md"
    assert raw.exists()
    assert load_registry(str(tmp_workspace))["paper1.pdf"]["status"] == "deposited"

def test_scan_unchanged_pdf_is_skipped(tmp_workspace, cfg, sample_pdf):
    from wiki_pdf_watcher import scan_inbox
    with patch("wiki_pdf_watcher.extract_text", return_value="Content"):
        scan_inbox(str(tmp_workspace), cfg)      # prima passata
        result = scan_inbox(str(tmp_workspace), cfg)  # seconda passata
    assert result["processed"] == 0
    assert result["skipped"] == 1

def test_scan_modified_pdf_is_reprocessed(tmp_workspace, cfg, sample_pdf):
    from wiki_pdf_watcher import scan_inbox
    with patch("wiki_pdf_watcher.extract_text", return_value="First version"):
        scan_inbox(str(tmp_workspace), cfg)

    sample_pdf.write_bytes(b"%PDF-1.4 modified content")  # cambia hash

    with patch("wiki_pdf_watcher.extract_text", return_value="Updated version"):
        result = scan_inbox(str(tmp_workspace), cfg)

    assert result["processed"] == 1
    raw = tmp_workspace / "wiki-works" / "test" / "raw" / "paper1.md"
    assert "Updated version" in raw.read_text(encoding="utf-8")

def test_scan_scanned_pdf_marked_as_failed(tmp_workspace, cfg, sample_pdf):
    from wiki_pdf_watcher import scan_inbox, load_registry
    with patch("wiki_pdf_watcher.extract_text", return_value=""):
        result = scan_inbox(str(tmp_workspace), cfg)
    assert result["failed"] == 1
    assert load_registry(str(tmp_workspace))["paper1.pdf"]["status"] == "failed"

def test_scan_creates_pdf_inbox_if_missing(tmp_workspace, cfg):
    from wiki_pdf_watcher import scan_inbox
    import shutil
    inbox = tmp_workspace / "pdf-inbox"
    shutil.rmtree(str(inbox))
    assert not inbox.exists()
    result = scan_inbox(str(tmp_workspace), cfg)
    assert inbox.exists()
    assert result["processed"] == 0

def test_scan_output_json_structure(tmp_workspace, cfg, sample_pdf):
    from wiki_pdf_watcher import scan_inbox
    with patch("wiki_pdf_watcher.extract_text", return_value="Text"):
        result = scan_inbox(str(tmp_workspace), cfg)
    assert set(result.keys()) == {"status", "op", "processed", "skipped", "failed", "deposited", "failures"}
    assert result["op"] == "scan-inbox"
```

- [ ] **Step 2: Esegui i test — devono fallire con NotImplementedError**

```bash
pytest tests/test_pdf_watcher.py -v -k "scan"
```

Atteso: 6 failed con `NotImplementedError`.

- [ ] **Step 3: Implementa `scan_inbox` in `scripts/wiki_pdf_watcher.py`**

Sostituisci la funzione `scan_inbox`:

```python
def scan_inbox(workspace: str, cfg: dict) -> dict:
    """Scansiona pdf-inbox/, processa PDF nuovi/modificati. Ritorna report JSON-serializzabile."""
    inbox_dir = Path(workspace) / INBOX_DIR
    inbox_dir.mkdir(parents=True, exist_ok=True)

    registry = load_registry(workspace)
    processed: list[str] = []
    skipped: list[str] = []
    failed: list[dict] = []

    for pdf_file in sorted(inbox_dir.glob("*.pdf")):
        name = pdf_file.name
        current_hash = compute_hash(str(pdf_file))
        entry = registry.get(name, {})

        # Salta se già processato o fallito con lo stesso hash
        if entry.get("hash") == current_hash and entry.get("status") in ("deposited", "failed"):
            skipped.append(name)
            continue

        # Marca pending prima di iniziare (crash recovery: pending → reprocessed al prossimo scan)
        registry[name] = {
            "hash": current_hash,
            "deposited_to": None,
            "processed_at": datetime.now().isoformat(timespec="seconds"),
            "status": "pending",
        }
        save_registry(workspace, registry)

        try:
            text = extract_text(str(pdf_file))
            if not text.strip():
                raise ValueError("no text extractable (scanned PDF)")

            rel_path = deposit_raw(text, name, workspace, cfg)

            registry[name] = {
                "hash": current_hash,
                "deposited_to": rel_path,
                "processed_at": datetime.now().isoformat(timespec="seconds"),
                "status": "deposited",
            }
            processed.append(Path(rel_path).name)

        except Exception as e:
            registry[name] = {
                "hash": current_hash,
                "deposited_to": None,
                "processed_at": datetime.now().isoformat(timespec="seconds"),
                "status": "failed",
                "error": str(e),
            }
            failed.append({"name": name, "error": str(e)})

        save_registry(workspace, registry)

    return {
        "status": "ok",
        "op": "scan-inbox",
        "processed": len(processed),
        "skipped": len(skipped),
        "failed": len(failed),
        "deposited": processed,
        "failures": failed,
    }
```

- [ ] **Step 4: Esegui tutti i test del modulo**

```bash
pytest tests/test_pdf_watcher.py -v
```

Atteso: tutti e 22 i test passano.

- [ ] **Step 5: Esegui la suite completa per verificare nessuna regressione**

```bash
pytest tests/ -v --ignore=tests/test_integration.py -x
```

Atteso: tutti i test passano.

- [ ] **Step 6: Commit**

```bash
git add scripts/wiki_pdf_watcher.py tests/test_pdf_watcher.py
git commit -m "feat: wiki_pdf_watcher scan_inbox with hash-based change detection"
```

---

## Task 6: Nuovi comandi CLI — scan-inbox e ingest-pdf

**Files:**
- Modify: `scripts/wiki_workflows.py` — aggiunge `cmd_scan_inbox`, `cmd_ingest_pdf`
- Modify: `scripts/wiki.py` — registra i due comandi nell'argparser e nel dispatch

- [ ] **Step 1: Aggiungi i test CLI in fondo a `tests/test_pdf_watcher.py`**

```python
# ── CLI command tests ────────────────────────────────────────────────────────

import subprocess

def run_wiki_cmd(tmp_workspace, *args):
    scripts_dir = Path(__file__).parent.parent / "scripts"
    result = subprocess.run(
        [sys.executable, str(scripts_dir / "wiki.py"), *args,
         "--workspace", str(tmp_workspace)],
        capture_output=True, text=True
    )
    try:
        return json.loads(result.stdout)
    except Exception:
        return {"raw_stdout": result.stdout, "raw_stderr": result.stderr}

def test_scan_inbox_cli_empty(tmp_workspace):
    result = run_wiki_cmd(tmp_workspace, "scan-inbox")
    assert result["status"] == "ok"
    assert result["op"] == "scan-inbox"
    assert result["processed"] == 0

def test_ingest_pdf_cli_local_file(tmp_workspace, tmp_path):
    # Crea un PDF fake fuori dal workspace
    fake_pdf = tmp_path / "external.pdf"
    fake_pdf.write_bytes(b"%PDF-1.4 test")

    result = run_wiki_cmd(tmp_workspace, "ingest-pdf", "--file", str(fake_pdf))

    # Il file viene copiato in pdf-inbox/ prima che l'estrazione venga tentata
    inbox_pdf = tmp_workspace / "pdf-inbox" / "external.pdf"
    assert inbox_pdf.exists()
    # L'estrazione del PDF fake fallisce, ma il comando ritorna comunque ok
    assert result["status"] == "ok"
    assert result["failed"] == 1
```

> **Nota:** `test_ingest_pdf_cli_local_file` verifica solo che il file venga copiato in `pdf-inbox/` (comportamento del subprocess). L'estrazione è testata a livello unitario in Task 5.

- [ ] **Step 2: Esegui i test CLI — devono fallire**

```bash
pytest tests/test_pdf_watcher.py -v -k "cli"
```

Atteso: 2 failed (comandi non ancora registrati).

- [ ] **Step 3: Aggiungi `cmd_scan_inbox` e `cmd_ingest_pdf` in `scripts/wiki_workflows.py`**

Aggiungi queste due funzioni alla fine del file, prima della funzione `_write_session`:

```python
def cmd_scan_inbox(args, cfg):
    from wiki_pdf_watcher import scan_inbox
    result = scan_inbox(args.workspace, cfg)
    _write_session(args.workspace, "scan-inbox", "ok", {
        "processed": result["processed"],
        "deposited": result["deposited"],
    })
    ok(result)


def cmd_ingest_pdf(args, cfg):
    import shutil
    import urllib.request
    from wiki_pdf_watcher import scan_inbox

    inbox_dir = Path(args.workspace) / "pdf-inbox"
    inbox_dir.mkdir(parents=True, exist_ok=True)

    file_arg = args.file
    if file_arg.startswith("http://") or file_arg.startswith("https://"):
        filename = Path(file_arg.split("?")[0]).name
        if not filename.lower().endswith(".pdf"):
            filename = filename + ".pdf"
        dest = inbox_dir / filename
        urllib.request.urlretrieve(file_arg, str(dest))
    else:
        src = Path(file_arg)
        if not src.exists():
            error("file_not_found", f"File non trovato: {file_arg}", recoverable=False)
            return
        dest = inbox_dir / src.name
        shutil.copy2(str(src), str(dest))

    result = scan_inbox(args.workspace, cfg)
    _write_session(args.workspace, "ingest-pdf", "ok", {
        "processed": result["processed"],
        "deposited": result["deposited"],
    })
    ok(result)
```

> `Path` e `ok`, `error` sono già importati in `wiki_workflows.py` — non aggiungere import duplicati.

- [ ] **Step 4: Registra i due comandi in `scripts/wiki.py`**

In `main()`, dopo il blocco `p_session` (riga ~117), aggiungi:

```python
    p_scan_inbox = sub.add_parser("scan-inbox")
    p_scan_inbox.add_argument("--workspace", required=True)

    p_ingest_pdf = sub.add_parser("ingest-pdf")
    p_ingest_pdf.add_argument("--workspace", required=True)
    p_ingest_pdf.add_argument("--file", required=True)
```

In `dispatch()`, aggiungi al dizionario `commands`:

```python
        "scan-inbox": cmd_scan_inbox,
        "ingest-pdf": cmd_ingest_pdf,
```

E aggiorna l'import in `dispatch()`:

```python
    from wiki_workflows import (cmd_ingest, cmd_query, cmd_lint, cmd_index,
                                cmd_rebuild, cmd_session_update,
                                cmd_scan_inbox, cmd_ingest_pdf)
```

- [ ] **Step 5: Esegui i test CLI**

```bash
pytest tests/test_pdf_watcher.py -v -k "cli"
```

Atteso: 2 passed.

- [ ] **Step 6: Esegui la suite completa**

```bash
pytest tests/ -v --ignore=tests/test_integration.py -x
```

Atteso: tutti i test passano.

- [ ] **Step 7: Commit**

```bash
git add scripts/wiki_workflows.py scripts/wiki.py tests/test_pdf_watcher.py
git commit -m "feat: add scan-inbox and ingest-pdf CLI commands"
```

---

## Task 7: Aggiornamento documentazione e skill

**Files:**
- Modify: `wiki.config.json`
- Modify: `skills/wiki-core.md`
- Modify: `skills/wiki-core.it.md`
- Modify: `AGENTS_PATCH.md`
- Modify: `AGENTS_PATCH.it.md`

- [ ] **Step 1: Aggiorna `wiki.config.json` — aggiungi il campo `pdf_inbox`**

Aggiungi dopo il campo `"projects"`:

```json
  "pdf_inbox": {
    "project_default": "research"
  },
```

Il file completo dopo la modifica:

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
    "quality_filter_min_score": 6
  },
  "lancedb": {
    "path": "memory/lancedb",
    "embedding_model": "BAAI/bge-m3"
  }
}
```

- [ ] **Step 2: Aggiungi la sezione `§pdf-inbox` a `skills/wiki-core.md`**

Leggi `skills/wiki-core.md` e aggiungi questa sezione dopo `§classification`:

```markdown
## §pdf-inbox — PDF ingestion workflow

When the user sends a PDF (attachment, file path, or URL):

1. Call `wiki.py ingest-pdf --workspace <path> --file <path|url>`
   Never write directly to `wiki-works/` or save the file manually.
2. The command copies the PDF to `pdf-inbox/` and extracts its text automatically.
   Output: `{"status": "ok", "op": "scan-inbox", "processed": N, "deposited": [...]}`
3. For each filename listed in `deposited`, read `wiki-works/<project>/raw/<name>.md`.
   This file contains raw extracted text — it is NOT a finished wiki page.
4. Structure the raw text into `.tmp` wiki pages (entities, concepts, synthesis as appropriate).
5. Call `wiki.py ingest --workspace <path> --pages <list> --log "INGEST | <pdf name>"`

To check for new PDFs added to the inbox since the last session:
- Call `wiki.py scan-inbox --workspace <path>`
- Read `wiki-session.md` — the "last operation" section lists which raw files are ready.

Files in `raw/` with `source: pdf` frontmatter are always raw extracted text.
Always structure them before calling `wiki.py ingest`.
```

- [ ] **Step 3: Aggiungi la sezione `§pdf-inbox` a `skills/wiki-core.it.md`**

Aggiungi dopo `§classification` nella versione italiana:

```markdown
## §pdf-inbox — Workflow di ingestione PDF

Quando l'utente invia un PDF (allegato, percorso file, o URL):

1. Chiama `wiki.py ingest-pdf --workspace <path> --file <path|url>`
   Non scrivere mai direttamente in `wiki-works/` né salvare il file manualmente.
2. Il comando copia il PDF in `pdf-inbox/` ed estrae automaticamente il testo.
   Output: `{"status": "ok", "op": "scan-inbox", "processed": N, "deposited": [...]}`
3. Per ogni filename in `deposited`, leggi `wiki-works/<progetto>/raw/<nome>.md`.
   Questo file contiene testo grezzo estratto — NON è una pagina wiki finita.
4. Struttura il testo grezzo in pagine `.tmp` (entities, concepts, synthesis secondo il contenuto).
5. Chiama `wiki.py ingest --workspace <path> --pages <lista> --log "INGEST | <nome pdf>"`

Per verificare nuovi PDF aggiunti all'inbox dall'ultima sessione:
- Chiama `wiki.py scan-inbox --workspace <path>`
- Leggi `wiki-session.md` — la sezione "ultima operazione" elenca i raw file pronti.

I file in `raw/` con frontmatter `source: pdf` sono sempre testo grezzo estratto.
Strutturarli sempre prima di chiamare `wiki.py ingest`.
```

- [ ] **Step 4: Aggiungi la sezione PDF a `AGENTS_PATCH.md`**

Aggiungi in fondo al file:

```markdown
---

## PDF Inbox

When the user sends a PDF file in chat or provides a file path/URL:
```
wiki.py ingest-pdf --workspace <workspace> --file <path|url>
```
Never save PDF files manually or write directly to `wiki-works/`.

To process all PDFs added to the inbox since the last session:
```
wiki.py scan-inbox --workspace <workspace>
```

Files deposited in `wiki-works/<project>/raw/` with `source: pdf` in their frontmatter are raw extracted text — not finished wiki pages. Always structure them into `.tmp` pages before calling `wiki.py ingest`.

After `scan-inbox` completes, check `wiki-session.md` — the "last operation" section lists which raw files are ready for structuring.
```

- [ ] **Step 5: Aggiungi la sezione PDF a `AGENTS_PATCH.it.md`**

Aggiungi in fondo al file:

```markdown
---

## PDF Inbox

Quando l'utente invia un file PDF in chat o fornisce un percorso/URL:
```
wiki.py ingest-pdf --workspace <workspace> --file <percorso|url>
```
Non salvare mai i PDF manualmente né scrivere direttamente in `wiki-works/`.

Per processare tutti i PDF aggiunti all'inbox dall'ultima sessione:
```
wiki.py scan-inbox --workspace <workspace>
```

I file depositati in `wiki-works/<progetto>/raw/` con frontmatter `source: pdf` sono testo grezzo estratto — non pagine wiki finite. Strutturarli sempre in pagine `.tmp` prima di chiamare `wiki.py ingest`.

Dopo `scan-inbox`, controlla `wiki-session.md` — la sezione "ultima operazione" elenca i raw file pronti per la strutturazione.
```

- [ ] **Step 6: Esegui la suite completa per verifica finale**

```bash
pytest tests/ -v --ignore=tests/test_integration.py
```

Atteso: tutti i test passano (37 preesistenti + 22 nuovi = 59 passed).

- [ ] **Step 7: Commit**

```bash
git add wiki.config.json skills/wiki-core.md skills/wiki-core.it.md AGENTS_PATCH.md AGENTS_PATCH.it.md
git commit -m "docs: add pdf-inbox section to skill, agents patch, and config"
```

- [ ] **Step 8: Push**

```bash
git push
```

---

## Riepilogo commit

| Commit | Contenuto |
|--------|-----------|
| `feat: add pdfplumber dependency and pdf-inbox workspace fixture` | requirements.txt + conftest.py |
| `feat: wiki_pdf_watcher registry functions` | compute_hash, load/save_registry |
| `feat: wiki_pdf_watcher extract_text via pdfplumber` | extract_text |
| `feat: wiki_pdf_watcher deposit_raw with frontmatter` | deposit_raw |
| `feat: wiki_pdf_watcher scan_inbox with hash-based change detection` | scan_inbox |
| `feat: add scan-inbox and ingest-pdf CLI commands` | wiki_workflows.py + wiki.py |
| `docs: add pdf-inbox section to skill, agents patch, and config` | Tutta la documentazione |
