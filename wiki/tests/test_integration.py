"""Test end-to-end del sistema wiki completo."""

import sys
import os
import json
import subprocess

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

import pytest
from pathlib import Path


def run_wiki(tmp_workspace, *args):
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


def test_full_ingest_query_cycle(tmp_workspace):
    """Ciclo completo: ingest → query → trova il documento."""
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
