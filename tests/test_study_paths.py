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
