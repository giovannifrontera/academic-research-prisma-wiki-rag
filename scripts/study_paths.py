"""Path containment helpers shared by hybrid-rag and wiki scripts.

Kept dependency-free (stdlib only) so it can be imported from any skill
script without pulling in study_workspace's CLI/argparse surface.
"""
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
