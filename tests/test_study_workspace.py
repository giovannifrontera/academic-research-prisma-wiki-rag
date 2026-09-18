import json
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

def test_create_study_new(tmp_path):
    from scripts.study_workspace import create_study
    from pathlib import Path
    result = create_study("My Study", tmp_path)
    assert result["status"] == "created"
    root = Path(result["project_root"])
    assert root == tmp_path / "my-study"
    assert (root / ".project-state.json").exists()
    assert (root / "prisma").is_dir()
    assert (root / "sources" / "pdf-inbox").is_dir()
    assert (root / "sources" / "pdf-inclusi").is_dir()
    assert (root / "database" / "qdrant-rag").is_dir()
    assert (root / "database" / "qdrant-wiki").is_dir()
    assert (root / "wiki-memory" / "wiki" / "concepts").is_dir()
    assert (root / "wiki-memory" / "wiki-works" / "my-study" / "raw").is_dir()
    assert (root / "synthesis").is_dir()
    assert (root / "design").is_dir()
    assert (root / "preprint").is_dir()
    assert (root / "export").is_dir()
    assert (root / "README.md").exists()
    assert (root / "project-log.md").exists()

def test_create_study_resumable(tmp_path):
    from scripts.study_workspace import create_study
    create_study("My Study", tmp_path)
    result = create_study("My Study", tmp_path)
    assert result["status"] == "resumable"

def test_create_study_directory_conflict(tmp_path):
    from scripts.study_workspace import create_study, StudyCollisionError
    (tmp_path / "my-study").mkdir()
    (tmp_path / "my-study" / "unrelated.txt").write_text("x", encoding="utf-8")
    with pytest.raises(StudyCollisionError, match="directory_conflict"):
        create_study("My Study", tmp_path)

def test_create_study_empty_dir_initializes(tmp_path):
    from scripts.study_workspace import create_study
    (tmp_path / "my-study").mkdir()
    result = create_study("My Study", tmp_path)
    assert result["status"] == "created"

def test_create_study_atomic_failure_leaves_no_partial(tmp_path, monkeypatch):
    from scripts import study_workspace as sw
    def boom(*a, **kw):
        raise OSError("disk full simulated")
    monkeypatch.setattr(sw.os, "rename", boom)
    with pytest.raises(OSError):
        sw.create_study("My Study", tmp_path)
    assert not (tmp_path / "my-study").exists()
    assert list(tmp_path.iterdir()) == []  # temp dir cleaned up

def test_cli_create(tmp_path, capsys):
    from scripts.study_workspace import main
    exit_code = main(["create", "--name", "My Study", "--parent", str(tmp_path)])
    assert exit_code == 0
    out = json.loads(capsys.readouterr().out)
    assert out["status"] == "created"

def test_cli_create_collision_reports_error(tmp_path, capsys):
    from scripts.study_workspace import main
    (tmp_path / "my-study").mkdir()
    (tmp_path / "my-study" / "f.txt").write_text("x", encoding="utf-8")
    exit_code = main(["create", "--name", "My Study", "--parent", str(tmp_path)])
    assert exit_code != 0
    out = json.loads(capsys.readouterr().out)
    assert out == {"status": "error", "kind": "directory_conflict"}

def test_cli_inspect(tmp_path, capsys):
    from scripts.study_workspace import main
    main(["create", "--name", "My Study", "--parent", str(tmp_path)])
    capsys.readouterr()
    exit_code = main(["inspect", "--project", str(tmp_path / "my-study")])
    assert exit_code == 0
    out = json.loads(capsys.readouterr().out)
    assert out["study_slug"] == "my-study"
