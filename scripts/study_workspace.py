#!/usr/bin/env python3
"""Bootstrap and inspect isolated study workspaces.

See docs/superpowers/specs/2026-09-17-isolated-study-workspace-design.md.
"""
import argparse
import json
import os
import re
import secrets
import shutil
import sys
import unicodedata
import uuid
from datetime import datetime, timezone
from pathlib import Path

_RESERVED_NAMES = {
    "CON", "PRN", "AUX", "NUL",
    *(f"COM{i}" for i in range(1, 10)),
    *(f"LPT{i}" for i in range(1, 10)),
}
_MAX_SLUG_LEN = 80


def slugify(name: str) -> str:
    normalized = unicodedata.normalize("NFKD", name)
    ascii_only = normalized.encode("ascii", "ignore").decode("ascii")
    lowered = ascii_only.lower()
    collapsed = re.sub(r"[^a-z0-9]+", "-", lowered)
    stripped = collapsed.strip("-.")
    stripped = stripped.strip("-")
    truncated = stripped[:_MAX_SLUG_LEN].strip("-")
    if not truncated:
        raise ValueError("empty_slug")
    if truncated.upper() in _RESERVED_NAMES:
        raise ValueError("reserved_name")
    return truncated


STATE_FILENAME = ".project-state.json"
SCHEMA_VERSION = 1


def build_state(study_name: str, study_slug: str, project_root: Path) -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "study_id": str(uuid.uuid4()),
        "study_name": study_name,
        "study_slug": study_slug,
        "project_root": str(project_root),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "isolation": {
            "mode": "sealed",
            "allow_external_reads": False,
            "allow_external_writes": False,
        },
        "paths": {
            "prisma": "prisma",
            "sources": "sources",
            "qdrant": "database/qdrant",
            "wiki_workspace": "wiki-memory",
            "synthesis": "synthesis",
            "design": "design",
            "preprint": "preprint",
            "export": "export",
        },
        "phases": {
            "prisma": "not_started",
            "rag": "not_started",
            "wiki": "ready",
            "pilot": "not_started",
            "preprint": "not_started",
            "export": "not_started",
        },
    }


def read_state(project_root: Path) -> dict:
    state_path = Path(project_root) / STATE_FILENAME
    if not state_path.exists():
        raise FileNotFoundError(str(state_path))
    try:
        with open(state_path, "r", encoding="utf-8") as f:
            state = json.load(f)
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid_state: {exc}") from exc
    if state.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("invalid_state: unsupported schema_version")
    return state


DIRECTORY_TREE = [
    "prisma",
    "sources/pdf-inbox",
    "sources/pdf-inclusi",
    "database/qdrant-rag",
    "database/qdrant-wiki",
    "wiki-memory/wiki/concepts",
    "wiki-memory/wiki/synthesis",
    "wiki-memory/wiki/identity",
    "wiki-memory/pdf-inbox",
    "synthesis",
    "design",
    "preprint",
    "export",
]


class StudyCollisionError(Exception):
    def __init__(self, kind: str):
        super().__init__(kind)
        self.kind = kind


def _is_existing_valid_study(path: Path, expected_slug: str) -> bool:
    if not (path / STATE_FILENAME).exists():
        return False
    try:
        state = read_state(path)
    except ValueError:
        return False
    return state.get("study_slug") == expected_slug


def create_study(name: str, parent) -> dict:
    parent = Path(parent).resolve()
    slug = slugify(name)
    final_root = parent / slug

    if final_root.exists():
        if _is_existing_valid_study(final_root, slug):
            return {
                "status": "resumable",
                "project_root": str(final_root),
                "study_slug": slug,
                "state_file": str(final_root / STATE_FILENAME),
            }
        if any(final_root.iterdir()):
            raise StudyCollisionError("directory_conflict")
        if final_root.is_symlink():
            raise StudyCollisionError("unsafe_target")
        # empty existing directory: fall through and initialize in place

    tmp_root = parent / f"{slug}-{secrets.token_hex(4)}"
    tmp_root.mkdir(parents=True, exist_ok=False)
    try:
        for rel in DIRECTORY_TREE:
            (tmp_root / rel).mkdir(parents=True, exist_ok=True)
        (tmp_root / "wiki-memory" / "wiki-works" / slug / "raw").mkdir(parents=True, exist_ok=True)
        (tmp_root / "wiki-memory" / "wiki-works" / slug / "entities").mkdir(parents=True, exist_ok=True)
        (tmp_root / "wiki-memory" / "wiki-works" / slug / "concepts").mkdir(parents=True, exist_ok=True)
        (tmp_root / "wiki-memory" / "wiki-works" / slug / "synthesis").mkdir(parents=True, exist_ok=True)

        (tmp_root / "project-log.md").write_text(
            f"# Project log — {name}\n\nCreated: {datetime.now(timezone.utc).isoformat()}\n",
            encoding="utf-8",
        )
        (tmp_root / "README.md").write_text(
            f"# {name}\n\nStudy root generated by study_workspace.py.\n",
            encoding="utf-8",
        )

        wiki_config = {
            "workspace": str(final_root / "wiki-memory"),
            "projects": {
                slug: {
                    "path": f"wiki-works/{slug}",
                    "keywords": ["paper", "studio", "PRISMA", "articolo", "ricerca",
                                 "review", "systematic", "pilot"],
                }
            },
            "thresholds": {
                "index_token_budget": 4000, "staleness_days": 90,
                "similarity_merge": 0.95, "similarity_orphan": 0.50,
                "synthesis_min_tokens": 300, "synthesis_min_sources": 2,
                "chunk_size_tokens": 512, "chunk_overlap_tokens": 64,
                "page_chunk_threshold_tokens": 1500,
                "quality_filter_min_score": 6, "dedup_auto": 0.90, "dedup_warn": 0.75,
            },
            "qdrant": {
                "path": str(final_root / "database" / "qdrant-wiki"),
                "embedding_model": "BAAI/bge-m3",
                "reranker_model": "BAAI/bge-reranker-v2-m3",
                "rerank": True,
            },
            "exclude_from_index": [],
        }
        with open(tmp_root / "wiki-memory" / "wiki.config.json", "w", encoding="utf-8") as f:
            json.dump(wiki_config, f, indent=2)

        state = build_state(name, slug, final_root)
        state_path = tmp_root / STATE_FILENAME
        with open(state_path, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)
            f.flush()
            os.fsync(f.fileno())

        if final_root.exists():
            final_root.rmdir()  # only reachable for the empty-dir init case
        os.rename(tmp_root, final_root)
    except Exception:
        shutil.rmtree(tmp_root, ignore_errors=True)
        raise

    return {
        "status": "created",
        "project_root": str(final_root),
        "study_slug": slug,
        "state_file": str(final_root / STATE_FILENAME),
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="study_workspace.py")
    sub = parser.add_subparsers(dest="command", required=True)

    create_p = sub.add_parser("create")
    create_p.add_argument("--name", required=True)
    create_p.add_argument("--parent", required=True)

    inspect_p = sub.add_parser("inspect")
    inspect_p.add_argument("--project", required=True)

    args = parser.parse_args(argv)

    try:
        if args.command == "create":
            result = create_study(args.name, args.parent)
        else:
            result = read_state(Path(args.project))
        print(json.dumps(result))
        return 0
    except StudyCollisionError as exc:
        print(json.dumps({"status": "error", "kind": exc.kind}))
        return 1
    except (FileNotFoundError, ValueError) as exc:
        print(json.dumps({"status": "error", "kind": str(exc)}))
        return 1


if __name__ == "__main__":
    sys.exit(main())
