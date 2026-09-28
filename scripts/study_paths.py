"""Path containment helpers shared by hybrid-rag and wiki scripts.

Kept dependency-free (stdlib only) so it can be imported from any skill
script without pulling in study_workspace's CLI/argparse surface.
"""
import json
from pathlib import Path

STATE_FILENAME = ".project-state.json"


class PathEscapeError(Exception):
    pass


def resolve_in_study(project_root, relative_or_absolute) -> Path:
    root = Path(project_root).resolve()
    candidate = Path(relative_or_absolute)
    target = candidate if candidate.is_absolute() else root / candidate
    resolved = target.resolve(strict=False)
    try:
        resolved.relative_to(root)
    except ValueError:
        raise PathEscapeError(f"{resolved} escapes study root {root}")
    return resolved


def containing_study_root(start) -> Path | None:
    current = Path(start).resolve()
    for candidate in [current, *current.parents]:
        if (candidate / STATE_FILENAME).is_file():
            return candidate
    return None


class StudyStateError(Exception):
    pass


def _read_state(root: Path) -> dict:
    try:
        return json.loads((root / STATE_FILENAME).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise StudyStateError(f"unreadable {STATE_FILENAME} in {root}: {exc}") from exc


def resolve_study_wiki(path) -> Path:
    """Wiki workspace of the sealed study containing `path` (root or any subdirectory)."""
    root = containing_study_root(path)
    if root is None:
        raise StudyStateError(f"no {STATE_FILENAME} found in {Path(path).resolve()} or its parents")
    rel = _read_state(root).get("paths", {}).get("wiki_workspace")
    if not rel:
        raise StudyStateError(f"{STATE_FILENAME} in {root} has no paths.wiki_workspace")
    wiki = resolve_in_study(root, rel)
    if not wiki.is_dir():
        raise StudyStateError(f"wiki workspace {wiki} does not exist")
    return wiki


def study_metadata(path) -> dict | None:
    """Name/slug/id of the sealed study containing `path`, or None outside a study."""
    root = containing_study_root(path)
    if root is None:
        return None
    try:
        state = _read_state(root)
    except StudyStateError:
        return None
    return {"name": state.get("study_name", ""), "slug": state.get("study_slug", ""),
            "id": state.get("study_id", "")}
