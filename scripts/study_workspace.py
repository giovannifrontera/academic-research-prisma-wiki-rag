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
