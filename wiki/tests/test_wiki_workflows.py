"""Tests for wiki_workflows.py"""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))


def test_lint_status_written(tmp_workspace, monkeypatch):
    import wiki_workflows

    class FakeTable:
        def to_pandas(self):
            import pandas as pd
            return pd.DataFrame({"path": []})
        def delete(self, expr):
            pass

    monkeypatch.setattr(wiki_workflows, "get_db", lambda path: object())
    monkeypatch.setattr(wiki_workflows, "ensure_table", lambda db, table_name="wiki_pages": FakeTable())
    monkeypatch.setattr(wiki_workflows, "detect_renames", lambda db, fs_paths, workspace: [])
    monkeypatch.setattr(wiki_workflows, "find_semantic_duplicates", lambda db, auto_threshold, warn_threshold: [])

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


def test_lint_status_written_no_full(tmp_workspace, monkeypatch):
    import wiki_workflows

    monkeypatch.setattr(wiki_workflows, "get_db", lambda path: object())

    cfg = json.loads((tmp_workspace / "wiki.config.json").read_text())

    class Args:
        workspace = str(tmp_workspace)
        full = False

    wiki_workflows.cmd_lint(Args(), cfg)

    status_path = tmp_workspace / ".wiki-lint-status.json"
    assert status_path.exists(), ".wiki-lint-status.json not created for full=False"
    data = json.loads(status_path.read_text())
    assert data["errors"] == 0
    assert data["warnings"] == 0


def test_lint_full_reports_semantic_duplicates(tmp_workspace, monkeypatch):
    import wiki_workflows
    import io, sys

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

    captured = io.StringIO()
    monkeypatch.setattr(sys, "stdout", captured)
    wiki_workflows.cmd_lint(Args(), cfg)

    output = json.loads(captured.getvalue())
    assert output["status"] == "ok"
    semantic = [i for i in output["issues"] if i["type"] == "semantic_duplicate"]
    assert len(semantic) == 1
    assert semantic[0]["action"] == "auto_merge"


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
    assert output["event"] == "rispondo sempre troppo lungo"
    log_path = tmp_workspace / ".wiki-behavior-log.jsonl"
    assert log_path.exists()


def test_cmd_self_reflect_returns_ok(tmp_workspace, monkeypatch):
    import wiki_workflows
    import io, sys
    from wiki_selfreflect import log_behavior

    class Args:
        workspace = str(tmp_workspace)

    cfg = json.loads((tmp_workspace / "wiki.config.json").read_text())

    for _ in range(3):
        log_behavior(str(tmp_workspace), "non cito mai le fonti")

    captured = io.StringIO()
    monkeypatch.setattr(sys, "stdout", captured)
    wiki_workflows.cmd_self_reflect(Args(), cfg)

    output = json.loads(captured.getvalue())
    assert output["status"] == "ok"
    assert output["patterns_found"] == 1


def test_ingest_pdf_already_in_inbox_does_not_crash(tmp_workspace, monkeypatch):
    """Se il file è già in pdf-inbox/, ingest-pdf non deve crashare con WinError 32."""
    from wiki_workflows import cmd_ingest_pdf

    # Crea un PDF finto già nell'inbox
    pdf = tmp_workspace / "pdf-inbox" / "test.pdf"
    pdf.write_bytes(b"%PDF-1.4 fake")

    # Mock scan_inbox per non richiedere lancedb/embeddings
    # scan_inbox è importata localmente dentro cmd_ingest_pdf da wiki_pdf_watcher
    # Ensure the module is loaded before patching (safe pattern)
    import importlib
    wiki_pdf_watcher = importlib.import_module("wiki_pdf_watcher")
    monkeypatch.setattr(wiki_pdf_watcher, "scan_inbox",
                        lambda ws, cfg: {"processed": 1, "deposited": [], "failed": 0})

    class Args:
        file = str(pdf)
        workspace = str(tmp_workspace)

    cfg = json.loads((tmp_workspace / "wiki.config.json").read_text())
    # Non deve sollevare eccezioni
    cmd_ingest_pdf(Args(), cfg)


def test_process_raw_promotes_files_to_index(tmp_workspace, monkeypatch):
    """process-raw deve spostare i file da raw/ all'indice via ingest."""
    from wiki_workflows import cmd_process_raw

    # Crea struttura raw
    raw_dir = tmp_workspace / "wiki-works" / "ricerca" / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    raw_file = raw_dir / "paper_test.md"
    raw_file.write_text("# Test paper\nContenuto di test.", encoding="utf-8")

    ingest_calls = []

    def mock_cmd_ingest(args, cfg):
        ingest_calls.append(args.pages)
        # Simula spostamento file: rinomina .tmp -> .md
        for p in args.pages.split(","):
            p = p.strip()
            final = p.replace(".md.tmp", ".md")
            Path(p).rename(final)

    monkeypatch.setattr("wiki_workflows.cmd_ingest", mock_cmd_ingest)

    cfg = json.loads((tmp_workspace / "wiki.config.json").read_text())

    class Args:
        workspace = str(tmp_workspace)
        project = None

    cmd_process_raw(Args(), cfg)

    assert len(ingest_calls) == 1
    assert "paper_test.md.tmp" in ingest_calls[0]
    assert not raw_file.exists()
    final = tmp_workspace / "wiki-works" / "ricerca" / "paper_test.md"
    assert final.exists()


def test_process_raw_no_files_is_a_noop(tmp_workspace):
    """Se non ci sono file in raw/, process-raw non deve crashare."""
    from wiki_workflows import cmd_process_raw
    cfg = json.loads((tmp_workspace / "wiki.config.json").read_text())

    class Args:
        workspace = str(tmp_workspace)
        project = None

    # Non deve sollevare eccezioni
    cmd_process_raw(Args(), cfg)
