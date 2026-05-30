#!/usr/bin/env python3
"""AI Wiki System — entry point CLI."""

import json
import os
import sys
import argparse
from pathlib import Path

REQUIRED_CONFIG_FIELDS = [
    ("workspace",),
    ("projects",),
    ("thresholds", "index_token_budget"),
    ("thresholds", "staleness_days"),
    ("thresholds", "similarity_merge"),
    ("thresholds", "similarity_orphan"),
    ("thresholds", "synthesis_min_tokens"),
    ("thresholds", "synthesis_min_sources"),
    ("thresholds", "chunk_size_tokens"),
    ("thresholds", "chunk_overlap_tokens"),
    ("thresholds", "page_chunk_threshold_tokens"),
    ("thresholds", "quality_filter_min_score"),
    ("lancedb", "path"),
    ("lancedb", "embedding_model"),
]


class ConfigError(Exception):
    pass


def load_config(config_path: str) -> dict:
    if not os.path.exists(config_path):
        raise ConfigError(f"Config non trovato: {config_path}")
    with open(config_path, encoding="utf-8") as f:
        cfg = json.load(f)
    for field_path in REQUIRED_CONFIG_FIELDS:
        node = cfg
        for key in field_path:
            if not isinstance(node, dict) or key not in node:
                raise ConfigError(f"Campo obbligatorio mancante: {'.'.join(field_path)}")
            node = node[key]
    return cfg


def _pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except PermissionError:
        return True   # Processo esiste ma non abbiamo i permessi per segnalarlo
    except OSError:
        return False  # ProcessLookupError: PID non esiste


def acquire_lock(lock_path: str) -> None:
    if os.path.exists(lock_path):
        try:
            pid = int(Path(lock_path).read_text().strip())
            if _pid_alive(pid):
                raise RuntimeError(
                    json.dumps({
                        "status": "error",
                        "code": "lock_exists",
                        "message": f"Operazione in corso (PID {pid}). Rimuovi .wiki-lock solo se quel processo non esiste più.",
                        "recoverable": True,
                    })
                )
        except (ValueError, OSError):
            pass
        # Lock stale (processo morto) → rimuovi silenziosamente
        os.remove(lock_path)
    Path(lock_path).write_text(str(os.getpid()))


def release_lock(lock_path: str) -> None:
    if os.path.exists(lock_path):
        os.remove(lock_path)


def ok(data: dict) -> None:
    print(json.dumps({"status": "ok", **data}))


def error(code: str, message: str, recoverable: bool = True, **extra) -> None:
    print(json.dumps({"status": "error", "code": code, "message": message,
                      "recoverable": recoverable, **extra}))


def main():
    parser = argparse.ArgumentParser(prog="wiki.py")
    sub = parser.add_subparsers(dest="command")

    p_ingest = sub.add_parser("ingest")
    p_ingest.add_argument("--workspace", required=True)
    p_ingest.add_argument("--pages", required=True, metavar='"p1.tmp,p2.tmp"',
                          help="Comma-separated list of .tmp file paths to ingest")
    p_ingest.add_argument("--log", default=None,
                          help="Log entry (auto-generated from timestamp if omitted)")

    p_query = sub.add_parser("query")
    p_query.add_argument("--workspace", required=True)
    p_query.add_argument("--q", required=True)
    p_query.add_argument("--k", type=int, default=5)

    p_lint = sub.add_parser("lint")
    p_lint.add_argument("--workspace", required=True)
    p_lint.add_argument("--full", action="store_true")

    p_index = sub.add_parser("index")
    p_index.add_argument("--workspace", required=True)

    p_rebuild = sub.add_parser("rebuild")
    p_rebuild.add_argument("--workspace", required=True)

    p_session = sub.add_parser("session-update")
    p_session.add_argument("--workspace", required=True)
    p_session.add_argument("--op", required=True)
    p_session.add_argument("--status", required=True, choices=["ok", "failed", "in-progress", "needs-repair", "partial-failure"])
    p_session.add_argument("--detail", default="{}")

    p_scan_inbox = sub.add_parser("scan-inbox")
    p_scan_inbox.add_argument("--workspace", required=True)

    p_ingest_pdf = sub.add_parser("ingest-pdf")
    p_ingest_pdf.add_argument("--workspace", required=True)
    p_ingest_pdf.add_argument("--file", required=True)

    p_process_raw = sub.add_parser("process-raw",
        help="Promote files in */raw/ to the index (use after bulk PDF import)")
    p_process_raw.add_argument("--workspace", required=True)
    p_process_raw.add_argument("--project", default=None,
        help="Limit to a specific project (e.g. 'ricerca')")

    p_serve = sub.add_parser("serve")
    p_serve.add_argument("--workspace", required=True)
    p_serve.add_argument("--host", default="127.0.0.1")
    p_serve.add_argument("--port", type=int, default=7331)
    p_serve.add_argument("--no-auth", action="store_true")

    p_behavior_log = sub.add_parser("behavior-log")
    p_behavior_log.add_argument("--workspace", required=True)
    p_behavior_log.add_argument("--event", required=True)

    p_self_reflect = sub.add_parser("self-reflect")
    p_self_reflect.add_argument("--workspace", required=True)

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    config_path = os.path.join(args.workspace, "wiki.config.json")
    try:
        cfg = load_config(config_path)
    except ConfigError as e:
        error("invalid_config", str(e), recoverable=False)
        sys.exit(1)

    dispatch(args, cfg)


def dispatch(args, cfg):
    from wiki_workflows import (cmd_ingest, cmd_query, cmd_lint, cmd_index,
                                cmd_rebuild, cmd_session_update,
                                cmd_scan_inbox, cmd_ingest_pdf, cmd_serve,
                                cmd_behavior_log, cmd_self_reflect,
                                cmd_process_raw)
    commands = {
        "ingest": cmd_ingest,
        "query": cmd_query,
        "lint": cmd_lint,
        "index": cmd_index,
        "rebuild": cmd_rebuild,
        "session-update": cmd_session_update,
        "scan-inbox": cmd_scan_inbox,
        "ingest-pdf": cmd_ingest_pdf,
        "serve": cmd_serve,
        "behavior-log": cmd_behavior_log,
        "self-reflect": cmd_self_reflect,
        "process-raw": cmd_process_raw,
    }
    commands[args.command](args, cfg)


if __name__ == "__main__":
    main()
