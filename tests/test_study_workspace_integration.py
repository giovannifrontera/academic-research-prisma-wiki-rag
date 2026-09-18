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
