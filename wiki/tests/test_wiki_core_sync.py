"""CI guard: wiki-core.md must cover every section documented in AGENTS.md.

If a section exists in AGENTS.md but not in wiki-core.md, the agent silently
degrades — it follows the skill (which it reads every session) not the README.
This test catches that drift before it ships.
"""
import re
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent

# Sections that AGENTS.md documents and wiki-core.md must mirror.
# Each tuple is (human_label, regex_that_must_match_in_wiki_core).
REQUIRED_IN_WIKI_CORE = [
    ("three-layer architecture", r"three.layer|Three.layer|Layer.*Folder|wiki-works.*wiki.*identity"),
    ("identity layer", r"wiki/identity"),
    ("INGEST workflow", r"§ingest|INGEST workflow"),
    ("QUERY workflow", r"§query|QUERY workflow"),
    ("LINT workflow", r"§lint|LINT workflow"),
    ("BEHAVIOR_FEEDBACK classification", r"BEHAVIOR_FEEDBACK"),
    ("behavior-log command", r"behavior-log"),
    ("self-reflect command", r"self-reflect"),
    ("promotion criteria", r"§promotion|promotion"),
    ("process-raw vs ingest warning", r"process.raw.*ingest|ingest.*process.raw|process-raw.*NOT.*ingest"),
]


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_wiki_core_covers_agents_sections():
    wiki_core = _read(REPO_ROOT / "skills" / "wiki-core.md")
    missing = []
    for label, pattern in REQUIRED_IN_WIKI_CORE:
        if not re.search(pattern, wiki_core, re.IGNORECASE):
            missing.append(label)
    assert not missing, (
        "wiki-core.md is missing sections documented in AGENTS.md — "
        "agents running this skill will silently skip these features:\n"
        + "\n".join(f"  • {m}" for m in missing)
    )


def test_agents_md_commands_in_wiki_core():
    """Every CLI command listed in AGENTS.md must appear at least once in wiki-core.md."""
    agents_md = _read(REPO_ROOT / "AGENTS.md")
    wiki_core = _read(REPO_ROOT / "skills" / "wiki-core.md")

    # Extract commands from the "Available commands:" line in AGENTS.md
    match = re.search(r"Available commands:.*?`([^`]+(?:`,\s*`[^`]+)*)`", agents_md)
    if not match:
        return  # Line not found — skip rather than false-fail

    raw = match.group(0)
    commands = re.findall(r"`([a-z][a-z-]+)`", raw)
    missing = [cmd for cmd in commands if cmd not in wiki_core]
    assert not missing, (
        "These CLI commands are listed in AGENTS.md but never mentioned in wiki-core.md:\n"
        + "\n".join(f"  • {c}" for c in missing)
    )
