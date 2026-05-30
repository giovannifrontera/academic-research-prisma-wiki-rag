"""Implementazione dei workflow INGEST, QUERY, LINT, INDEX, REBUILD, SESSION-UPDATE."""

import fnmatch
import json
import os
import shutil
import sys
import tempfile
from datetime import datetime
from pathlib import Path

from wiki import ok, error, acquire_lock, release_lock
from wiki_embed import embed_file, _load_model
from wiki_lancedb import (get_db, upsert, promote_staging, rollback_staging,
                           ensure_table, detect_renames, query_similar,
                           find_semantic_duplicates)
from wiki_index import rebuild_index, is_stale, EXCLUDED_NAMES


def _lancedb_path(workspace: str, cfg: dict) -> str:
    return os.path.join(workspace, cfg["lancedb"]["path"])


def _append_log(workspace: str, wiki_subdir: str, entry: str) -> None:
    log_path = Path(workspace) / wiki_subdir / "log.md"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    date = datetime.now().strftime("%Y-%m-%d")
    line = f"## [{date}] {entry}\n"
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(line)


def _mini_lint(workspace: str, written_paths: list, db) -> str:
    """Verifica le invarianti post-ingest. Ritorna 'ok' o descrizione errore."""
    table = ensure_table(db)
    df = table.to_pandas()
    for path in written_paths:
        if not os.path.exists(path):
            return f"file_missing:{path}"
        rel = os.path.relpath(path, workspace).replace("\\", "/")
        if df[df["path"] == rel].empty:
            return f"not_embedded:{rel}"
    for root_name in ("wiki", "wiki-works"):
        root = Path(workspace) / root_name
        if root.is_dir():
            for p in root.rglob("*.tmp"):
                return f"tmp_remaining:{p}"
    return "ok"


def cmd_ingest(args, cfg):
    workspace = args.workspace
    lock_path = os.path.join(workspace, ".wiki-lock")
    db = get_db(_lancedb_path(workspace, cfg))
    thresholds = cfg["thresholds"]

    try:
        acquire_lock(lock_path)
    except RuntimeError as e:
        print(e.args[0])
        sys.exit(1)

    _write_session(workspace, "ingest", "in-progress", {})

    # Normalizza i path .tmp in assoluti: l'agente può passarli relativi al workspace
    raw_paths = [p.strip() for p in args.pages.split(",")]
    tmp_paths = [p if os.path.isabs(p) else os.path.join(workspace, p) for p in raw_paths]
    final_paths = []
    moved: list[tuple[str, str]] = []  # (tmp_path, final_path) spostati con successo

    try:
        for tmp_path in tmp_paths:
            if not os.path.exists(tmp_path):
                raise FileNotFoundError(f"File .tmp non trovato: {tmp_path}")

        for tmp_path in tmp_paths:
            rel_final = os.path.relpath(tmp_path, workspace).replace("\\", "/")
            if rel_final.endswith(".tmp"):
                rel_final = rel_final[:-4]
            chunks = embed_file(
                tmp_path,
                chunk_size=thresholds["chunk_size_tokens"],
                overlap=thresholds["chunk_overlap_tokens"],
                threshold=thresholds["page_chunk_threshold_tokens"],
                model_name=cfg["lancedb"]["embedding_model"],
            )
            upsert(db, rel_final, chunks, table_name="staging_wiki_pages")
            final_paths.append((tmp_path, os.path.join(workspace, rel_final.replace("/", os.sep))))

        for tmp_path, final_path in final_paths:
            os.makedirs(os.path.dirname(final_path), exist_ok=True)
            shutil.move(tmp_path, final_path)
            moved.append((tmp_path, final_path))

        promote_staging(db)

        wiki_dir = os.path.join(workspace, "wiki")
        if os.path.isdir(wiki_dir):
            idx_content = rebuild_index(wiki_dir, thresholds["index_token_budget"])
            Path(wiki_dir, "index.md").write_text(idx_content, encoding="utf-8")

        log_entry = args.log or f"ingest | {datetime.now().strftime('%Y-%m-%d %H:%M')} | {len(final_paths)} page(s)"
        _append_log(workspace, "wiki", log_entry)

        written = [fp for _, fp in final_paths]
        lint_result = _mini_lint(workspace, written, db)

        if lint_result != "ok":
            _append_log(workspace, "wiki", f"mini-lint-failed | {lint_result}")

        _write_session(workspace, "ingest", "ok",
                       {"pages_written": len(final_paths), "mini_lint": lint_result})
        ok({"op": "ingest", "pages_written": len(final_paths), "mini_lint": lint_result, "conflicts": []})

    except Exception as e:
        rollback_staging(db)
        # Ripristina i file già spostati prima dell'errore
        for tmp_p, final_p in moved:
            try:
                if os.path.exists(final_p):
                    shutil.move(final_p, tmp_p)
            except OSError:
                pass
        pending = [tp for tp in tmp_paths if os.path.exists(tp)]
        _write_session(workspace, "ingest", "failed", {"error": str(e), "pending_tmp": pending})
        _append_log(workspace, "wiki", f"ingest-failed | {e} | pending: {len(pending)} file .tmp")
        error("ingest_failed", str(e), pending_tmp=pending)
    finally:
        release_lock(lock_path)


def cmd_query(args, cfg):
    from datetime import datetime as _datetime
    db = get_db(_lancedb_path(args.workspace, cfg))
    model, _ = _load_model(cfg["lancedb"]["embedding_model"])
    vector = model.encode(args.q, normalize_embeddings=True).tolist()

    results = query_similar(db, vector, k=args.k)

    paths = list({r["path"] for r in results})
    log_path = Path(args.workspace) / ".wiki-query-log.jsonl"
    entry = {"ts": _datetime.now().isoformat(), "q": args.q, "paths": paths}
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")

    ok({"op": "query", "results": [
        {"path": r["path"], "chunk_id": r["chunk_id"],
         "score": float(r.get("_distance", 0)), "excerpt": r["chunk_text"][:200]}
        for r in results
    ]})


def cmd_index(args, cfg):
    wiki_dir = os.path.join(args.workspace, "wiki")
    os.makedirs(wiki_dir, exist_ok=True)
    idx_content = rebuild_index(wiki_dir, cfg["thresholds"]["index_token_budget"])
    Path(wiki_dir, "index.md").write_text(idx_content, encoding="utf-8")
    ok({"op": "index", "wiki_dir": wiki_dir})


_WIKI_ROOTS = ("wiki", "wiki-works")
_MAX_FILE_BYTES = 200_000


def _wiki_md_files(workspace: str, exclude_patterns: list = None):
    """Itera solo su wiki/ e wiki-works/, salta file >200 KB."""
    for root_name in _WIKI_ROOTS:
        root = Path(workspace) / root_name
        if not root.is_dir():
            continue
        for md_file in root.rglob("*.md"):
            if md_file.name in EXCLUDED_NAMES:
                continue
            if "raw" in md_file.parts or ".archive" in md_file.parts:
                continue
            if md_file.stat().st_size > _MAX_FILE_BYTES:
                continue
            if exclude_patterns:
                rel_path = os.path.relpath(str(md_file), workspace).replace("\\", "/")
                if any(fnmatch.fnmatch(rel_path, pattern) for pattern in exclude_patterns):
                    continue
            yield md_file


def cmd_rebuild(args, cfg):
    db = get_db(_lancedb_path(args.workspace, cfg))
    thresholds = cfg["thresholds"]

    existing = db.list_tables().tables
    if "wiki_pages" in existing:
        db.drop_table("wiki_pages")

    count = 0
    for md_file in _wiki_md_files(args.workspace, cfg.get("exclude_from_index", [])):
        rel = os.path.relpath(str(md_file), args.workspace).replace("\\", "/")
        chunks = embed_file(
            str(md_file),
            chunk_size=thresholds["chunk_size_tokens"],
            overlap=thresholds["chunk_overlap_tokens"],
            threshold=thresholds["page_chunk_threshold_tokens"],
            model_name=cfg["lancedb"]["embedding_model"],
        )
        upsert(db, rel, chunks)
        count += 1

    _append_log(args.workspace, "wiki", f"rebuild-lancedb | {count} pagine")
    ok({"op": "rebuild", "pages_embedded": count})


def cmd_lint(args, cfg):
    db = get_db(_lancedb_path(args.workspace, cfg))
    report = []

    if args.full:
        import re
        for md_file in _wiki_md_files(args.workspace, cfg.get("exclude_from_index", [])):
            try:
                text = md_file.read_text(encoding="utf-8")
            except OSError:
                continue
            for link in re.findall(r'\[\[([^\]]+)\]\]', text):
                matches = list(Path(args.workspace).rglob(f"{link}.md"))
                if not matches:
                    report.append({"type": "broken_link", "file": str(md_file), "link": link})

        table = ensure_table(db)
        df = table.to_pandas()
        for path in df["path"].unique():
            full = os.path.join(args.workspace, path.replace("/", os.sep))
            if not os.path.exists(full):
                report.append({"type": "orphan_entry", "path": path})
                try:
                    safe = path.replace("'", "''")
                    table.delete(f"path = '{safe}'")
                except Exception:
                    pass

        fs_paths = {
            str(md_file)
            for md_file in _wiki_md_files(args.workspace, cfg.get("exclude_from_index", []))
        }
        renames = detect_renames(db, fs_paths, args.workspace)
        for r in renames:
            report.append({"type": "rename_detected", **r})

        # Duplicate filename check — reuse fs_paths, normalize to lowercase for case-insensitive comparison
        from collections import defaultdict
        name_to_paths: dict[str, list[str]] = defaultdict(list)
        for path_str in fs_paths:
            rel = os.path.relpath(path_str, args.workspace).replace("\\", "/")
            name_to_paths[Path(path_str).name.lower()].append(rel)
        for filename, paths in name_to_paths.items():
            if len(paths) > 1:
                report.append({"type": "duplicate_filename", "filename": filename, "paths": sorted(paths)})

        # Semantic duplicate detection
        auto_t = cfg.get("thresholds", {}).get("dedup_auto", 0.90)
        warn_t = cfg.get("thresholds", {}).get("dedup_warn", 0.75)
        for dup in find_semantic_duplicates(db, auto_threshold=auto_t, warn_threshold=warn_t):
            report.append({"type": "semantic_duplicate", **dup})

    errors = sum(1 for r in report if r["type"] in ("broken_link", "orphan_entry"))
    warnings = sum(1 for r in report if r["type"] in ("rename_detected", "duplicate_filename", "semantic_duplicate"))
    orphans = sum(1 for r in report if r["type"] == "orphan_entry")
    broken = sum(1 for r in report if r["type"] == "broken_link")
    detail_parts = []
    if orphans:
        detail_parts.append(f"{orphans} orphan vectors removed")
    if broken:
        detail_parts.append(f"{broken} broken links")
    renames_count = sum(1 for r in report if r["type"] == "rename_detected")
    duplicates_count = sum(1 for r in report if r["type"] == "duplicate_filename")
    if renames_count:
        detail_parts.append(f"{renames_count} renames detected")
    if duplicates_count:
        detail_parts.append(f"{duplicates_count} duplicate filenames")
    semantic_auto = sum(1 for r in report if r["type"] == "semantic_duplicate" and r.get("action") == "auto_merge")
    semantic_warn = sum(1 for r in report if r["type"] == "semantic_duplicate" and r.get("action") == "warn")
    if semantic_auto:
        detail_parts.append(f"{semantic_auto} auto-merge candidates")
    if semantic_warn:
        detail_parts.append(f"{semantic_warn} semantic overlaps")
    detail_str = ", ".join(detail_parts) if detail_parts else "no issues"

    status = {
        "last_run": datetime.now().isoformat(timespec="seconds"),
        "errors": errors,
        "warnings": warnings,
        "detail": detail_str,
    }
    status_path = Path(args.workspace) / ".wiki-lint-status.json"
    fd, tmp_p = tempfile.mkstemp(dir=args.workspace, prefix=".wiki-lint-status.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(status, f)
        os.replace(tmp_p, status_path)
    except Exception:
        try:
            os.unlink(tmp_p)
        except OSError:
            pass
        raise

    ok({"op": "lint", "full": args.full, "issues": report, "issues_count": len(report)})


def cmd_session_update(args, cfg):
    try:
        detail = json.loads(args.detail)
    except json.JSONDecodeError as e:
        from wiki import error
        error("invalid_detail", f"detail non è JSON valido: {e}", recoverable=False)
        sys.exit(1)
    _write_session(args.workspace, args.op, args.status, detail)
    ok({"op": "session-update", "status": args.status})


def cmd_scan_inbox(args, cfg):
    from wiki_pdf_watcher import scan_inbox
    result = scan_inbox(args.workspace, cfg)
    session_status = "partial-failure" if result["failed"] > 0 else "ok"
    _write_session(args.workspace, "scan-inbox", session_status, {
        "processed": result["processed"],
        "deposited": result["deposited"],
        "failed": result["failed"],
    })
    ok(result)


def cmd_ingest_pdf(args, cfg):
    import urllib.request
    from wiki_pdf_watcher import scan_inbox

    inbox_dir = Path(args.workspace) / "pdf-inbox"
    inbox_dir.mkdir(parents=True, exist_ok=True)

    _MAX_PDF_BYTES = 50 * 1024 * 1024  # 50 MB hard cap

    file_arg = args.file
    if file_arg.startswith("http://") or file_arg.startswith("https://"):
        filename = Path(file_arg.split("?")[0]).name
        if not filename.lower().endswith(".pdf"):
            filename = filename + ".pdf"
        dest = inbox_dir / filename
        with urllib.request.urlopen(file_arg, timeout=30) as response:
            data = response.read(_MAX_PDF_BYTES + 1)
        if len(data) > _MAX_PDF_BYTES:
            error("pdf_too_large", f"Il PDF supera il limite di 50 MB", recoverable=False)
            return
        dest.write_bytes(data)
    else:
        src = Path(file_arg)
        if not src.exists():
            error("file_not_found", f"File non trovato: {file_arg}", recoverable=False)
            return
        dest = inbox_dir / src.name
        # Skip copy if source and destination are the same file (avoids WinError 32)
        if src.resolve() != dest.resolve():
            shutil.copy2(str(src), str(dest))

    result = scan_inbox(args.workspace, cfg)
    session_status = "partial-failure" if result["failed"] > 0 else "ok"
    _write_session(args.workspace, "ingest-pdf", session_status, {
        "processed": result["processed"],
        "deposited": result["deposited"],
        "failed": result["failed"],
    })
    ok(result)


def cmd_process_raw(args, cfg):
    """Promote all files in */raw/ to the index via ingest.

    Useful after scan-inbox bulk import. Raw files are deleted only after
    a successful ingest call.
    """
    workspace = Path(args.workspace)
    project_filter = getattr(args, "project", None)

    search_root = workspace / "wiki-works"
    if not search_root.exists():
        ok({"op": "process-raw", "promoted": 0, "message": "no raw files found"})
        return

    raw_files: list[Path] = []
    for raw_dir in search_root.rglob("raw"):
        if not raw_dir.is_dir():
            continue
        if project_filter and raw_dir.parent.name != project_filter:
            continue
        raw_files.extend(raw_dir.glob("*.md"))

    if not raw_files:
        ok({"op": "process-raw", "promoted": 0, "message": "no raw files found"})
        return

    tmp_paths: list[tuple[Path, Path]] = []
    for raw_file in raw_files:
        tmp_dest = raw_file.parent.parent / (raw_file.stem + ".md.tmp")
        shutil.copy2(str(raw_file), str(tmp_dest))
        tmp_paths.append((raw_file, tmp_dest))

    pages_arg = ",".join(str(t) for _, t in tmp_paths)
    log_msg = f"process-raw | {len(tmp_paths)} files promoted from raw/"

    from types import SimpleNamespace
    _ingest_args = SimpleNamespace(pages=pages_arg, workspace=str(args.workspace), log=log_msg)

    try:
        cmd_ingest(_ingest_args, cfg)
        for raw_file, _ in tmp_paths:
            try:
                raw_file.unlink()
            except OSError:
                pass
    except BaseException:
        for _, tmp_file in tmp_paths:
            try:
                tmp_file.unlink()
            except OSError:
                pass
        raise


def _write_session(workspace: str, op: str, status: str, detail: dict,
                   project: str = "", project_path: str = "") -> None:
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    content = f"""# Wiki Session — {now}

## Status
status: {status}

## Workspace attivo
Progetto: {project or "wiki principale"}
Path: {project_path or "wiki/"}

## Ultima operazione
Tipo: {op}
Completata: {now}
Dettaglio: {json.dumps(detail, ensure_ascii=False)}

## Wiki principale
Pagine totali: {_count_pages(workspace)}
"""
    target = Path(workspace, "wiki-session.md")
    fd, tmp_path = tempfile.mkstemp(dir=workspace, prefix=".wiki-session.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
        os.replace(tmp_path, target)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def _count_pages(workspace: str) -> int:
    return sum(
        1 for md_file in _wiki_md_files(workspace)
        if not md_file.name.endswith(".tmp")
    )


def cmd_serve(args, cfg):
    import uvicorn
    import wiki_server
    no_auth = getattr(args, "no_auth", False)
    wiki_server.configure(args.workspace, cfg, no_auth)
    uvicorn.run("wiki_server:app", host=args.host, port=args.port, reload=False)


def cmd_behavior_log(args, cfg):
    from wiki_selfreflect import log_behavior, event_count, run_self_reflect
    log_behavior(args.workspace, args.event)

    threshold = int(cfg.get("self_reflection", {}).get("correction_threshold", 3))
    count = event_count(args.workspace, args.event)

    result = {"op": "behavior-log", "event": args.event, "count": count, "threshold": threshold}

    if count >= threshold:
        reflect = run_self_reflect(args.workspace, cfg)
        result["auto_reflect"] = reflect

    ok(result)


def cmd_self_reflect(args, cfg):
    from wiki_selfreflect import run_self_reflect
    result = run_self_reflect(args.workspace, cfg)
    ok(result)
