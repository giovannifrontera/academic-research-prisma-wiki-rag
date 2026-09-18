#!/usr/bin/env python3
"""Bootstrap and inspect isolated study workspaces.

See docs/superpowers/specs/2026-09-17-isolated-study-workspace-design.md.
"""
import argparse
import json
import os
import re
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
