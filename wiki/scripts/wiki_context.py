#!/usr/bin/env python3
"""
wiki_context.py — Pre-prompt wiki context injector.

Usage:
    py scripts/wiki_context.py --workspace <path> --q "<query>" [--k 3]

Outputs a <wiki-context> block to stdout with the most relevant wiki chunks.
Designed for use as a pre-hook in OpenClaw.

Exit codes:
    0 — always (hook must never block the user's prompt)
"""

import argparse
import fnmatch
import json
import os
import sys
import warnings
from datetime import datetime, timezone
from pathlib import Path

# Silence all Python warnings to stdout — this is a hook, stdout must stay clean
warnings.filterwarnings("ignore")


def load_config(workspace: str) -> dict | None:
    config_path = os.path.join(workspace, "wiki.config.json")
    if not os.path.exists(config_path):
        print(
            f"wiki_context: wiki.config.json not found in {workspace!r} — "
            "check that --workspace points to the directory containing wiki.config.json, "
            "not to a subdirectory (e.g. wiki/ or wiki-works/).",
            file=sys.stderr,
        )
        return None
    with open(config_path, encoding="utf-8") as f:
        return json.load(f)


def main():
    # Windows: stdout defaults to CP1252 — force UTF-8 so Claude Code can read the output
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(
        description="Inietta contesto wiki prima di ogni prompt."
    )
    parser.add_argument("--workspace", required=True,
                        help="Path al workspace (deve contenere wiki.config.json)")
    parser.add_argument("--q", default="",
                        help="Testo della query (il prompt utente); se omesso legge CLAUDE_USER_PROMPT")
    parser.add_argument("--k", type=int, default=3,
                        help="Numero di pagine da restituire (default: 3)")
    parser.add_argument("--max-chars", type=int, default=600, dest="max_chars",
                        help="Caratteri massimi per chunk (default: 600)")
    args = parser.parse_args()

    # Shell expansion of $CLAUDE_USER_PROMPT is unreliable on Windows (PowerShell
    # treats it as a PS variable, not an env var). Always prefer the env var set
    # by Claude Code on the subprocess environment.
    if not args.q.strip():
        args.q = os.environ.get("CLAUDE_USER_PROMPT", "").strip()

    try:
        _run(args)
    except Exception:
        pass  # Hook deve sempre fallire silenziosamente
    sys.exit(0)


def _run(args):
    if not args.q.strip():
        return  # nothing to search — avoid embedding an empty string

    cfg = load_config(args.workspace)
    if not cfg:
        return

    lancedb_path = os.path.join(args.workspace, cfg["lancedb"]["path"])
    if not os.path.exists(lancedb_path):
        return

    try:
        import lancedb
        os.environ.setdefault("TRANSFORMERS_VERBOSITY", "error")
        os.environ.setdefault("HF_HUB_VERBOSITY", "error")
        os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
        from sentence_transformers import SentenceTransformer
        import logging
        logging.getLogger("sentence_transformers").setLevel(logging.ERROR)
        logging.getLogger("transformers").setLevel(logging.ERROR)
        logging.getLogger("huggingface_hub").setLevel(logging.ERROR)
    except ImportError:
        return

    db = lancedb.connect(lancedb_path)
    table_result = db.list_tables()
    existing = getattr(table_result, "tables", None) or list(table_result)
    if "wiki_pages" not in existing:
        return

    table = db.open_table("wiki_pages")
    model = SentenceTransformer(cfg["lancedb"]["embedding_model"], device="cpu")
    vector = model.encode(args.q, normalize_embeddings=True).tolist()

    # Over-fetch per deduplicare per pagina, poi prendere i top-k
    raw = table.search(vector).limit(args.k * 4).to_list()

    exclude_patterns = cfg.get("exclude_from_index", [])
    seen: dict[str, dict] = {}
    for r in raw:
        chunk = r.get("chunk_text") or ""
        if not chunk:
            continue
        path = r["path"]
        if any(fnmatch.fnmatch(path, p) for p in exclude_patterns):
            continue
        dist = float(r.get("_distance", 1.0))
        if path not in seen or dist < seen[path]["dist"]:
            seen[path] = {"dist": dist, "chunk_text": chunk[: args.max_chars]}

    top = sorted(seen.items(), key=lambda x: x[1]["dist"])[: args.k]

    # Check for stale .tmp files — warn regardless of whether semantic results exist
    stale_tmp = []
    for root_name in ("wiki", "wiki-works"):
        root = Path(args.workspace) / root_name
        if root.is_dir():
            stale_tmp.extend(
                os.path.relpath(str(p), args.workspace).replace("\\", "/")
                for p in root.rglob("*.tmp")
            )

    if not top and not stale_tmp:
        return

    # Write to query log so the dashboard can animate the retrieved nodes
    if top:
        try:
            log_path = os.path.join(args.workspace, ".wiki-query-log.jsonl")
            entry = {"ts": datetime.now(timezone.utc).isoformat(), "q": args.q, "paths": [p for p, _ in top]}
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception:
            pass

    lines = ["<wiki-context>"]

    if stale_tmp:
        lines.append(
            f"⚠️ STALE .TMP FILES: {len(stale_tmp)} unprocessed staging file(s) found — "
            f"run `wiki.py ingest` or remove them: {', '.join(stale_tmp[:5])}"
        )
        lines.append("")

    if top:
        lines.append(
            f"Pre-loaded wiki context (top {len(top)} pages by semantic relevance):\n"
        )
    for path, info in top:
        score = round(1.0 - info["dist"], 3)
        lines.append(f"### {path}  [relevance: {score}]")
        lines.append(info["chunk_text"])
        lines.append("")
    lines.append(
        "</wiki-context>\n"
        "Use the context above to inform your response, detect conflicts during INGEST, "
        "or disambiguate uncertain intents. Do not run wiki.py query if this context is already sufficient."
    )

    print("\n".join(lines))


if __name__ == "__main__":
    main()
