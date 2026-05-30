#!/usr/bin/env python3
"""
setup_openclaw.py — injects wiki-context-plugin into the OpenClaw config file.

Usage:
    py scripts/setup_openclaw.py --workspace /path/to/workspace
    py scripts/setup_openclaw.py --workspace /path/to/workspace --config /path/to/openclaw/config.json

The script:
- Auto-detects the OpenClaw config file in common locations (or uses --config)
- Injects the wiki-context-plugin entry into the plugins array
- Skips silently if the plugin is already present
- Writes atomically (temp file + rename)
- Injects usage instructions into <workspace>/AGENTS.md (idempotent via sentinel marker)
"""

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path

USAGE_SENTINEL_START = "<!-- ai-wiki-system:usage-start -->"

USAGE_INSTRUCTIONS = """\
<!-- ai-wiki-system:usage-start -->
## Wiki Knowledge System

At the start of every session:
1. Read `wiki-session.md` for the current wiki context
2. Before any wiki operation, re-read `skills/wiki-core.md` to verify the protocol

The wiki is your persistent brain. Use it actively:
- Every relevant piece of knowledge should be ingested into the wiki
- Every complex question should first be checked against the wiki
- Run LINT proactively every 2 weeks

Never write directly into the `wiki/` or `wiki-works/` directories.
Always use `wiki.py` for any write operation.

## Wiki Context Injection

When context injection is active, every prompt arrives preceded by a block like:

```
<wiki-context>
Pre-loaded wiki context (top 3 pages by semantic relevance):

### wiki/concepts/rag.md  [relevance: 0.91]
[page content...]
</wiki-context>
```

Use this block directly as the starting context — it is already the most relevant knowledge for this prompt. Do not run `wiki.py query` again for the same query. If the block is absent, proceed normally with `skills/wiki-core.md`.

## Wiki Dashboard (v2.2+)

When the server is running (`wiki.py serve`), a `[Stats]` tab is available at `http://localhost:7331`.
Check there for: embedding coverage, stale pages, top queried pages, lint status.

REST endpoints (auth-protected):
- `GET  /api/stats` — full observability snapshot as JSON
- `POST /api/lint` — trigger lint (returns 409 if already running)

Auto-lint: add to `wiki.config.json`:
```json
{ "frontend": { "lint_interval_hours": 24 } }
```

## PDF Inbox

When the user sends a PDF file in chat or provides a file path/URL:
```
wiki.py ingest-pdf --workspace <workspace> --file <path|url>
wiki.py scan-inbox --workspace <workspace>
```
<!-- ai-wiki-system:usage-end -->
"""


def inject_usage_instructions(workspace: Path, dry_run: bool = False) -> None:
    agents_md = workspace / "AGENTS.md"
    if agents_md.exists():
        content = agents_md.read_text(encoding="utf-8")
        if USAGE_SENTINEL_START in content:
            print(f"Usage instructions already present in {agents_md} — skipping.")
            return
        new_content = content.rstrip("\n") + "\n\n" + USAGE_INSTRUCTIONS
    else:
        new_content = USAGE_INSTRUCTIONS

    if dry_run:
        print(f"DRY RUN — would write usage instructions to: {agents_md}")
        return

    fd, tmp_path = tempfile.mkstemp(dir=workspace, prefix=".agents_md.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(new_content)
        os.replace(tmp_path, agents_md)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise
    print(f"Usage instructions injected into {agents_md}")


CANDIDATE_PATHS = [
    Path.home() / ".openclaw" / "config.json",
    Path.home() / ".config" / "openclaw" / "config.json",
    Path(os.environ.get("APPDATA", "")) / "openclaw" / "config.json",
    Path(os.environ.get("LOCALAPPDATA", "")) / "openclaw" / "config.json",
    Path.cwd() / "openclaw.config.json",
]


def find_openclaw_config() -> Path | None:
    for p in CANDIDATE_PATHS:
        if p.exists():
            return p
    return None


def detect_python() -> str:
    return "py" if os.name == "nt" else "python3"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Inject wiki-context-plugin into OpenClaw config"
    )
    parser.add_argument(
        "--workspace",
        required=True,
        help="Absolute path to the wiki workspace (directory containing wiki.config.json)",
    )
    parser.add_argument(
        "--config",
        help="Path to the OpenClaw config file (default: auto-detected)",
    )
    parser.add_argument(
        "--python",
        default=detect_python(),
        help=f"Python executable (default: {detect_python()})",
    )
    parser.add_argument(
        "--k",
        type=int,
        default=3,
        help="Number of wiki chunks to inject per prompt (default: 3)",
    )
    parser.add_argument(
        "--timeout-ms",
        type=int,
        default=15000,
        dest="timeout_ms",
        help="Timeout for wiki_context.py in milliseconds (default: 15000)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the resulting config without writing it",
    )
    args = parser.parse_args()

    # Resolve workspace
    workspace = Path(args.workspace).resolve()
    if not workspace.exists():
        print(f"ERROR: workspace not found: {workspace}", file=sys.stderr)
        sys.exit(1)
    if not (workspace / "wiki.config.json").exists():
        print(f"ERROR: wiki.config.json not found in {workspace}", file=sys.stderr)
        print("--workspace must point to the directory that contains wiki.config.json,", file=sys.stderr)
        print("not to a subdirectory (e.g. wiki/ or wiki-works/).", file=sys.stderr)
        sys.exit(1)

    # Resolve wiki_context.py path
    script_path = (Path(__file__).parent / "wiki_context.py").resolve()
    if not script_path.exists():
        print(f"ERROR: wiki_context.py not found at {script_path}", file=sys.stderr)
        sys.exit(1)

    # Resolve plugin directory
    plugin_path = (Path(__file__).parent.parent / "plugins" / "wiki-context-plugin").resolve()
    if not plugin_path.exists():
        print(f"ERROR: plugin directory not found at {plugin_path}", file=sys.stderr)
        sys.exit(1)

    # Locate OpenClaw config
    if args.config:
        config_path = Path(args.config).resolve()
        if not config_path.exists():
            print(f"ERROR: config file not found: {config_path}", file=sys.stderr)
            sys.exit(1)
    else:
        config_path = find_openclaw_config()
        if config_path is None:
            print("ERROR: could not auto-detect OpenClaw config file.", file=sys.stderr)
            print("Tried:", file=sys.stderr)
            for p in CANDIDATE_PATHS:
                print(f"  {p}", file=sys.stderr)
            print("\nPass --config /path/to/openclaw/config.json explicitly.", file=sys.stderr)
            sys.exit(1)

    # Load existing config
    try:
        with open(config_path, encoding="utf-8") as f:
            config = json.load(f)
    except json.JSONDecodeError as e:
        print(f"ERROR: could not parse {config_path}: {e}", file=sys.stderr)
        sys.exit(1)

    # Check if already installed — OpenClaw uses plugins.entries.<id> dict format
    entries = config.setdefault("plugins", {}).setdefault("entries", {})
    if "wiki-context-plugin" in entries:
        print(f"Plugin already present in {config_path} — nothing to do.")
        sys.exit(0)

    # Build plugin entry (no top-level "id" or "path" — OpenClaw resolves by key)
    plugin_entry = {
        "config": {
            "workspace": str(workspace).replace("\\", "/"),
            "wikiContextScript": str(script_path).replace("\\", "/"),
            "pythonExecutable": args.python,
            "k": args.k,
            "timeoutMs": args.timeout_ms,
        },
    }
    entries["wiki-context-plugin"] = plugin_entry

    if args.dry_run:
        print(f"DRY RUN — would write to: {config_path}\n")
        print(json.dumps(config, indent=2))
        inject_usage_instructions(workspace, dry_run=True)
        return

    # Write atomically
    fd, tmp_path = tempfile.mkstemp(dir=config_path.parent, prefix=".openclaw.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)
            f.write("\n")
        os.replace(tmp_path, config_path)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise

    print(f"Plugin injected into {config_path}")
    print(f"  workspace  : {str(workspace).replace(chr(92), '/')}")
    print(f"  script     : {str(script_path).replace(chr(92), '/')}")
    print(f"  plugin dir : {str(plugin_path).replace(chr(92), '/')}")
    print(f"  python     : {args.python}")
    print(f"  k          : {args.k}")
    print()
    print("Restart OpenClaw to activate the plugin.")

    inject_usage_instructions(workspace, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
