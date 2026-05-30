"""Generazione index.md e stale detection."""

import os
from datetime import datetime
from pathlib import Path

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False

EXCLUDED_NAMES = {".schema.md", "log.md", "index.md", "index-entities.md",
                  "index-concepts.md", "index-synthesis.md"}


def is_stale(index_path: str, wiki_dir: str) -> bool:
    """True se index.md non esiste o è più vecchio di qualsiasi .md nel wiki."""
    if not os.path.exists(index_path):
        return True
    index_mtime = os.path.getmtime(index_path)
    for md_file in Path(wiki_dir).rglob("*.md"):
        if md_file.name in EXCLUDED_NAMES:
            continue
        if "raw" in md_file.parts:
            continue
        if md_file.stat().st_mtime > index_mtime:
            return True
    return False


def _approx_tokens(text: str) -> int:
    return len(text) // 4


def _get_metadata(md_path: Path) -> dict:
    try:
        content = md_path.read_text(encoding="utf-8")
        if HAS_YAML and content.startswith("---"):
            end = content.find("---", 3)
            if end != -1:
                fm = yaml.safe_load(content[3:end])
                if isinstance(fm, dict):
                    return {
                        "title": fm.get("title", md_path.stem),
                        "description": fm.get("description", ""),
                    }
        lines = [l for l in content.split("\n") if l.strip() and not l.startswith("#")]
        desc = lines[0][:120] if lines else ""
        return {"title": md_path.stem, "description": desc}
    except OSError:
        return {"title": md_path.stem, "description": ""}


def _collect_pages(wiki_dir: str) -> dict:
    wiki_path = Path(wiki_dir)
    categories = {"entities": [], "concepts": [], "synthesis": []}
    for cat in categories:
        cat_path = wiki_path / cat
        if not cat_path.exists():
            continue
        for md_file in sorted(cat_path.glob("*.md")):
            if md_file.name.startswith(".") or md_file.name in EXCLUDED_NAMES:
                continue
            meta = _get_metadata(md_file)
            categories[cat].append({
                "slug": md_file.stem,
                "description": meta["description"],
            })
    return categories


def _build_full(categories: dict, now: str, total: int, wiki_dir: str) -> str:
    lines = [f"# Index — {Path(wiki_dir).name}", f"_Generato: {now} — {total} pagine_", ""]
    for cat, pages in categories.items():
        if not pages:
            continue
        lines.append(f"## {cat.capitalize()}")
        for p in pages:
            if p["description"]:
                lines.append(f"- [[{p['slug']}]] — {p['description']}")
            else:
                lines.append(f"- [[{p['slug']}]]")
        lines.append("")
    return "\n".join(lines)


def _build_slugs_only(categories: dict, now: str, total: int, wiki_dir: str) -> str:
    lines = [f"# Index — {Path(wiki_dir).name}", f"_Generato: {now} — {total} pagine_", ""]
    for cat, pages in categories.items():
        if not pages:
            continue
        lines.append(f"## {cat.capitalize()}")
        for p in pages:
            lines.append(f"- [[{p['slug']}]]")
        lines.append("")
    return "\n".join(lines)


def rebuild_index(wiki_dir: str, token_budget: int = 4000) -> str:
    """Genera e ritorna il contenuto di index.md.

    Strategia 1 e 2: solo return, nessuna scrittura su disco.
    Strategia 3 (budget superato): scrive anche index-{cat}.md in wiki_dir
    come effetto collaterale, poi ritorna il contenuto dell'index principale.
    """
    categories = _collect_pages(wiki_dir)
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    total = sum(len(v) for v in categories.values())

    content = _build_full(categories, now, total, wiki_dir)
    if _approx_tokens(content) <= token_budget:
        return content

    content = _build_slugs_only(categories, now, total, wiki_dir)
    if _approx_tokens(content) <= token_budget:
        return content

    # Strategia 3: solo conteggi + indici separati scritti su disco
    lines = [f"# Index — {Path(wiki_dir).name}", f"_Generato: {now} — {total} pagine_", ""]
    for cat, pages in categories.items():
        if pages:
            lines.append(f"## {cat.capitalize()} ({len(pages)} pagine)")
            lines.append(f"→ Vedi index-{cat}.md")
    wiki_path = Path(wiki_dir)
    for cat, pages in categories.items():
        if not pages:
            continue
        plines = [f"# Index {cat.capitalize()}", ""]
        for p in pages:
            plines.append(f"- [[{p['slug']}]]")
        (wiki_path / f"index-{cat}.md").write_text("\n".join(plines), encoding="utf-8")

    return "\n".join(lines)
