import os
import sys
import pytest
from pathlib import Path

from scripts.study_paths import resolve_in_study, PathEscapeError, containing_study_root

def test_resolve_relative_inside(tmp_path):
    root = tmp_path / "study"
    root.mkdir()
    result = resolve_in_study(root, "prisma/eligibility_prisma.json")
    assert result == (root / "prisma" / "eligibility_prisma.json").resolve()

def test_resolve_rejects_dotdot_escape(tmp_path):
    root = tmp_path / "study"
    root.mkdir()
    with pytest.raises(PathEscapeError):
        resolve_in_study(root, "../outside.json")

def test_resolve_rejects_absolute_external(tmp_path):
    root = tmp_path / "study"
    root.mkdir()
    outside = tmp_path / "elsewhere.json"
    with pytest.raises(PathEscapeError):
        resolve_in_study(root, str(outside))

def test_resolve_allows_absolute_internal(tmp_path):
    root = tmp_path / "study"
    root.mkdir()
    inside = root / "prisma" / "x.json"
    result = resolve_in_study(root, str(inside))
    assert result == inside.resolve()

@pytest.mark.skipif(sys.platform == "win32", reason="symlink creation needs elevated perms on Windows")
def test_resolve_rejects_symlink_escape(tmp_path):
    root = tmp_path / "study"
    root.mkdir()
    outside_target = tmp_path / "outside_dir"
    outside_target.mkdir()
    link = root / "escape_link"
    os.symlink(outside_target, link, target_is_directory=True)
    with pytest.raises(PathEscapeError):
        resolve_in_study(root, "escape_link/file.json")

def test_containing_study_root_found(tmp_path):
    root = tmp_path / "study"
    (root / "prisma").mkdir(parents=True)
    (root / ".project-state.json").write_text("{}", encoding="utf-8")
    found = containing_study_root(root / "prisma")
    assert found == root

def test_containing_study_root_none(tmp_path):
    assert containing_study_root(tmp_path) is None


def _study(tmp_path, wiki="wiki-memory"):
    import json
    root = tmp_path / "my-study"
    (root / "wiki-memory").mkdir(parents=True)
    (root / "prisma").mkdir()
    (root / ".project-state.json").write_text(json.dumps({
        "study_name": "My Study", "study_slug": "my-study", "study_id": "uuid-1",
        "paths": {"wiki_workspace": wiki},
    }), encoding="utf-8")
    return root

def test_resolve_study_wiki_from_root_and_subdir(tmp_path):
    from scripts.study_paths import resolve_study_wiki
    root = _study(tmp_path)
    expected = (root / "wiki-memory").resolve()
    assert resolve_study_wiki(root) == expected
    assert resolve_study_wiki(root / "prisma") == expected

def test_resolve_study_wiki_requires_state(tmp_path):
    from scripts.study_paths import resolve_study_wiki, StudyStateError
    with pytest.raises(StudyStateError):
        resolve_study_wiki(tmp_path)

def test_resolve_study_wiki_rejects_escape(tmp_path):
    from scripts.study_paths import resolve_study_wiki, PathEscapeError
    root = _study(tmp_path, wiki="../elsewhere")
    with pytest.raises(PathEscapeError):
        resolve_study_wiki(root)

def test_study_metadata(tmp_path):
    from scripts.study_paths import study_metadata
    root = _study(tmp_path)
    assert study_metadata(root / "wiki-memory") == {"name": "My Study", "slug": "my-study", "id": "uuid-1"}
    assert study_metadata(tmp_path) is None
