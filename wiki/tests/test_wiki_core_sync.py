"""CI guard: wiki-core.md must document the core research-memory workflow.

wiki-core.md has been simplified to cover only the research memory use case
(ingest, query, pdf-inbox, promotion, lint). Agent-specific features
(behavior-log, self-reflect, session tracking, identity layer) have been
deliberately removed from the public skill documentation.

This test verifies the simplified contract.
"""
import re
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.parent  # wiki/tests/ → wiki/ → repo root

# Sections that wiki-core.md must document for the research memory workflow.
REQUIRED_IN_WIKI_CORE = [
    ("two-layer architecture", r"wiki-works.*ricerca|Layer.*Path.*Contenuto|Due layer|two.layer"),
    ("INGEST workflow", r"§ingest|INGEST workflow"),
    ("QUERY workflow", r"§query|QUERY workflow"),
    ("LINT workflow", r"§lint|LINT workflow"),
    ("promotion criteria", r"§promotion|promotion"),
    ("process-raw vs ingest warning", r"process.raw.*ingest|ingest.*process.raw|process-raw"),
    ("PRISMA integration table", r"prisma-review|Momento.*Azione|Before PRISMA|Dopo PRISMA"),
    ("workspace configuration", r"wiki\.config\.json|workspace"),
]

# Commands that must appear in wiki-core.md (they are the public API).
REQUIRED_COMMANDS = ["query", "ingest", "ingest-pdf", "lint", "rebuild", "serve"]


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_wiki_core_covers_required_sections():
    wiki_core_path = REPO_ROOT / "skills" / "wiki-core.md"
    assert wiki_core_path.exists(), f"wiki-core.md not found at {wiki_core_path}"
    wiki_core = _read(wiki_core_path)

    missing = []
    for label, pattern in REQUIRED_IN_WIKI_CORE:
        if not re.search(pattern, wiki_core, re.IGNORECASE):
            missing.append(label)

    assert not missing, (
        "wiki-core.md is missing required research-memory sections:\n"
        + "\n".join(f"  • {m}" for m in missing)
    )


def test_wiki_core_documents_public_commands():
    """All public wiki commands must appear in wiki-core.md."""
    wiki_core_path = REPO_ROOT / "skills" / "wiki-core.md"
    assert wiki_core_path.exists(), f"wiki-core.md not found at {wiki_core_path}"
    wiki_core = _read(wiki_core_path)

    missing = [cmd for cmd in REQUIRED_COMMANDS if cmd not in wiki_core]
    assert not missing, (
        "These commands are part of the public API but missing from wiki-core.md:\n"
        + "\n".join(f"  • {c}" for c in missing)
    )
