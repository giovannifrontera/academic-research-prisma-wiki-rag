import pytest
import uuid
from scripts.study_workspace import slugify

def test_slugify_basic():
    assert slugify("My Study 2026") == "my-study-2026"

def test_slugify_accents_nfkd():
    assert slugify("Attività Didàttica") == "attivita-didattica"

def test_slugify_collapses_punctuation():
    assert slugify("A///B   C!!!D") == "a-b-c-d"

def test_slugify_strips_leading_trailing_hyphens_dots_spaces():
    assert slugify("  .-.Hello.-.  ") == "hello"

def test_slugify_empty_raises():
    with pytest.raises(ValueError, match="empty_slug"):
        slugify("...---...")

def test_slugify_reserved_name_raises():
    for reserved in ["CON", "con", "PRN", "AUX", "NUL", "COM1", "LPT9"]:
        with pytest.raises(ValueError, match="reserved_name"):
            slugify(reserved)

def test_slugify_max_length_80():
    long_name = "a" * 200
    assert len(slugify(long_name)) == 80

def test_build_state_shape(tmp_path):
    from scripts.study_workspace import build_state
    root = tmp_path / "my-study"
    state = build_state("My Study", "my-study", root)
    assert state["schema_version"] == 1
    assert state["study_name"] == "My Study"
    assert state["study_slug"] == "my-study"
    assert state["project_root"] == str(root)
    assert state["isolation"] == {
        "mode": "sealed", "allow_external_reads": False, "allow_external_writes": False
    }
    assert state["paths"] == {
        "prisma": "prisma", "sources": "sources", "qdrant": "database/qdrant",
        "wiki_workspace": "wiki-memory", "synthesis": "synthesis",
        "design": "design", "preprint": "preprint", "export": "export",
    }
    assert state["phases"]["wiki"] == "ready"
    assert state["phases"]["prisma"] == "not_started"
    uuid.UUID(state["study_id"])  # valid uuid4, raises if not

def test_read_state_missing_raises(tmp_path):
    from scripts.study_workspace import read_state
    with pytest.raises(FileNotFoundError):
        read_state(tmp_path / "nope")

def test_read_state_invalid_json_raises(tmp_path):
    from scripts.study_workspace import read_state, STATE_FILENAME
    d = tmp_path / "study"
    d.mkdir()
    (d / STATE_FILENAME).write_text("{not json", encoding="utf-8")
    with pytest.raises(ValueError, match="invalid_state"):
        read_state(d)
