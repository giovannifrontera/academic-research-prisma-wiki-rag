"""Graph builder — read-only. Builds nodes + edges from filesystem and LanceDB."""

import re
import time
from pathlib import Path

_CACHE: dict | None = None
_CACHE_TIME: float = 0.0
_DIRTY: bool = False
_CACHE_TTL: float = 30.0

_EXCLUDED_FILES = {"index.md", "log.md"}
_EXCLUDED_DIRS = {"raw", ".archive"}

try:
    from wiki_lancedb import (
        get_db as _lancedb_get_db,
        ensure_table as _lancedb_ensure_table,
        query_similar as _lancedb_query_similar,
    )
    _LANCEDB_AVAILABLE = True
except ImportError:
    _LANCEDB_AVAILABLE = False


def mark_dirty() -> None:
    global _DIRTY
    _DIRTY = True


def _load_frontmatter(text: str) -> dict:
    if not text.startswith("---"):
        return {}
    lines = text.split("\n")
    end = -1
    for i, line in enumerate(lines[1:], 1):
        if line.strip() == "---":
            end = i
            break
    if end == -1:
        return {}
    fm: dict = {}
    for line in lines[1:end]:
        if ":" in line:
            key, _, value = line.partition(":")
            fm[key.strip()] = value.strip().strip('"').strip("'")
    return fm


def _node_id(path: Path, workspace: str) -> str:
    ws = Path(workspace)
    # resolve() normalises relative workspace (e.g. ".") so relative_to always
    # receives a matching absolute prefix even when workspace is not yet absolute.
    rel = path.resolve().relative_to(ws.resolve())
    return str(rel).replace("\\", "/").removesuffix(".md")


def _node_category(path: Path) -> str:
    for cat in ("entities", "concepts", "synthesis", "raw"):
        if cat in path.parts:
            return cat
    return "other"


def _node_project(path: Path, workspace: str) -> str:
    rel = path.relative_to(Path(workspace))
    parts = rel.parts
    if parts[0] == "wiki":
        return "wiki"
    if parts[0] == "wiki-works" and len(parts) > 1:
        return parts[1]
    return "wiki"


def _collect_md_files(workspace: str) -> list[Path]:
    ws = Path(workspace)
    files: list[Path] = []
    for root in (ws / "wiki", ws / "wiki-works"):
        if not root.exists():
            continue
        for p in root.rglob("*.md"):
            rel = p.relative_to(root)
            excluded = any(part in _EXCLUDED_DIRS for part in rel.parts[:-1])
            if not excluded and p.name not in _EXCLUDED_FILES:
                files.append(p)
    return files


def build_graph(workspace: str, cfg: dict) -> dict:
    global _CACHE, _CACHE_TIME, _DIRTY
    now = time.monotonic()
    if _CACHE is not None and not _DIRTY and (now - _CACHE_TIME) < _CACHE_TTL:
        return dict(_CACHE)

    files = _collect_md_files(workspace)
    nodes = []
    node_ids: set[str] = set()
    file_texts: list[tuple[Path, str]] = []

    for p in files:
        text = p.read_text(encoding="utf-8")
        file_texts.append((p, text))
        fm = _load_frontmatter(text)
        nid = _node_id(p, workspace)
        nodes.append({
            "id": nid,
            "path": str(p.relative_to(Path(workspace))).replace("\\", "/"),
            "title": fm.get("title", p.stem),
            "category": _node_category(p),
            "project": _node_project(p, workspace),
            "description": fm.get("description", ""),
            "last_modified": p.stat().st_mtime,
        })
        node_ids.add(nid)

    edges = _explicit_edges(file_texts, node_ids, workspace)

    try:
        edges += _semantic_edges(workspace, cfg, files, node_ids)
    except Exception:
        pass

    _CACHE = {"nodes": nodes, "edges": edges}
    _CACHE_TIME = now
    _DIRTY = False
    # Shallow copy so callers cannot replace _CACHE["nodes"] / _CACHE["edges"];
    # node/edge dicts themselves are shared (D3 attaches x/y in-place, which is intentional).
    return dict(_CACHE)


def _explicit_edges(file_texts: list[tuple[Path, str]], node_ids: set[str], workspace: str) -> list[dict]:
    edges: list[dict] = []
    seen: set[tuple] = set()
    for p, text in file_texts:
        src = _node_id(p, workspace)
        for m in re.finditer(r"\[\[([^\]]+)\]\]", text):
            slug = m.group(1).strip()
            target = next(
                (nid for nid in node_ids if nid.split("/")[-1] == slug),
                None,
            )
            if target and target != src:
                key = (src, target, "link")
                if key not in seen:
                    seen.add(key)
                    edges.append({"source": src, "target": target, "type": "link"})
    return edges


def _semantic_edges(workspace: str, cfg: dict, files: list[Path], node_ids: set[str]) -> list[dict]:
    import numpy as np
    if not _LANCEDB_AVAILABLE:
        return []

    db_path = str(Path(workspace) / cfg["lancedb"]["path"])
    db = _lancedb_get_db(db_path)
    table = _lancedb_ensure_table(db)
    df = table.to_pandas()
    if df.empty:
        return []

    edges: list[dict] = []
    seen: set[tuple] = set()

    for p in files:
        nid = _node_id(p, workspace)
        rel_path = str(p.relative_to(Path(workspace))).replace("\\", "/")
        page_rows = df[df["path"] == rel_path]
        if page_rows.empty:
            continue

        vecs = np.stack(page_rows["vector"].values)
        avg_vec = vecs.mean(axis=0).tolist()

        results = _lancedb_query_similar(db, avg_vec, k=6)
        for r in results:
            target_path = r.get("path", "")
            target_nid = target_path.replace("\\", "/").removesuffix(".md")
            if target_nid not in node_ids or target_nid == nid:
                continue
            distance = float(r.get("_distance", 1.0))
            similarity = round(1.0 - distance, 3)
            if similarity < 0.65:
                continue
            pair = tuple(sorted([nid, target_nid]))
            if pair in seen:
                continue
            seen.add(pair)
            edges.append({
                "source": nid, "target": target_nid,
                "type": "semantic", "weight": similarity,
            })

    return edges


def get_page_detail(workspace: str, path: str, cfg: dict) -> dict | None:
    import os
    workspace = os.path.abspath(workspace)
    ws = Path(workspace)
    full = (ws / path).resolve()
    if not full.is_relative_to(ws) or not full.exists():
        return None

    text = full.read_text(encoding="utf-8")
    fm = _load_frontmatter(text)
    nid = _node_id(full, workspace)
    graph = build_graph(workspace, cfg)

    links_out = [e["target"] for e in graph["edges"] if e["source"] == nid and e["type"] == "link"]
    links_in = [e["source"] for e in graph["edges"] if e["target"] == nid and e["type"] == "link"]
    similar = sorted(
        [
            {"id": e["target"] if e["source"] == nid else e["source"],
             "weight": e.get("weight", 0.0)}
            for e in graph["edges"]
            if e["type"] == "semantic" and (e["source"] == nid or e["target"] == nid)
        ],
        key=lambda x: -x["weight"],
    )

    return {
        "content": text,
        "metadata": {**fm, "path": path, "last_modified": full.stat().st_mtime},
        "similar": similar,
        "links_out": links_out,
        "links_in": links_in,
    }
