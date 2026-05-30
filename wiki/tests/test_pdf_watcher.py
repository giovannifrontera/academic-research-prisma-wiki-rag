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
    fake_pdf = tmp_path / "external.pdf"
    fake_pdf.write_bytes(b"%PDF-1.4 test")

    result = run_wiki_cmd(tmp_workspace, "ingest-pdf", "--file", str(fake_pdf))

    inbox_pdf = tmp_workspace / "pdf-inbox" / "external.pdf"
    assert inbox_pdf.exists()
    assert result["status"] == "ok"
    assert result["failed"] == 1
