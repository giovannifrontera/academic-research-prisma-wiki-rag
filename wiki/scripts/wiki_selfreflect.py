"""Self-reflection: behavior logging and autonomous identity updates."""

import json
import re
from collections import Counter
from datetime import datetime
from pathlib import Path

BEHAVIOR_LOG = ".wiki-behavior-log.jsonl"


def log_behavior(workspace: str, event: str) -> None:
    """Appende un evento comportamentale al log."""
    log_path = Path(workspace) / BEHAVIOR_LOG
    entry = {"ts": datetime.now().isoformat(), "event": event}
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def _load_events(workspace: str) -> list[dict]:
    log_path = Path(workspace) / BEHAVIOR_LOG
    if not log_path.exists():
        return []
    events = []
    for line in log_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            pass
    return events


def event_count(workspace: str, event: str) -> int:
    """Conta quante volte un evento specifico è stato loggato."""
    return sum(1 for e in _load_events(workspace) if e["event"] == event)


def _detect_patterns(events: list[dict], threshold: int) -> list[str]:
    """Raggruppa eventi per testo esatto, ritorna quelli >= threshold."""
    counts: Counter = Counter(e["event"] for e in events)
    return [event for event, count in counts.items() if count >= threshold]


def _slugify(text: str) -> str:
    slug = re.sub(r"[^\w]", "-", text.lower())
    slug = re.sub(r"-+", "-", slug).strip("-")
    return slug[:60]


def _append_wiki_log(workspace: str, pattern_count: int) -> None:
    log_path = Path(workspace) / "wiki" / "log.md"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    date = datetime.now().strftime("%Y-%m-%d")
    line = f"## [{date}] self-reflect | {pattern_count} pattern comportamentali aggiornati\n"
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(line)


def run_self_reflect(workspace: str, cfg: dict) -> dict:
    """Legge il behavior log, rileva pattern ricorrenti, aggiorna wiki/identity/."""
    sr_cfg = cfg.get("self_reflection", {})
    if not sr_cfg.get("enabled", True):
        return {"op": "self-reflect", "skipped": True, "reason": "disabled"}

    threshold = int(sr_cfg.get("correction_threshold", 3))
    events = _load_events(workspace)
    patterns = _detect_patterns(events, threshold)

    if not patterns:
        return {"op": "self-reflect", "patterns_found": 0, "updates": []}

    identity_dir = Path(workspace) / "wiki" / "identity"
    identity_dir.mkdir(parents=True, exist_ok=True)

    updates = []
    for pattern in patterns:
        slug = _slugify(pattern)
        page_path = identity_dir / f"{slug}.md"
        content = (
            f"---\ntype: behavioral-pattern\nlearned: {datetime.now().date()}\n---\n\n"
            f"# {pattern}\n\n"
            f"Pattern comportamentale ricorrente appreso da {threshold}+ correzioni.\n"
        )
        page_path.write_text(content, encoding="utf-8")
        rel = str(page_path.relative_to(workspace)).replace("\\", "/")
        updates.append(rel)

    _append_wiki_log(workspace, len(patterns))
    return {"op": "self-reflect", "patterns_found": len(patterns), "updates": updates}
