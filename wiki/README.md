<div align="center">

# 🧠 PRISMA Wiki Memory

### Persistent, inspectable knowledge for the Academic PRISMA Claude Code plugin

[![Release](https://img.shields.io/badge/release-v1.2.0-informational?style=flat-square)](https://github.com/giovannifrontera/academic-research-prisma-wiki-rag/releases/tag/v1.2.0)
[![Tests](https://img.shields.io/badge/tests-140%20passed-brightgreen?style=flat-square)](tests/)
[![Python](https://img.shields.io/badge/python-3.11+-3776ab?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![Qdrant](https://img.shields.io/badge/vector_store-Qdrant-f4a261?style=flat-square)](https://qdrant.tech)
[![License](https://img.shields.io/badge/license-AGPL--3.0-blue?style=flat-square)](../LICENSE)

[Italiano](README.it.md) · **English** · [Main README](../README.md)

[Concept](#-what-the-wiki-does) · [Architecture](#️-architecture) · [Retrieval](#-retrieval-pipeline) · [Quick Start](#-quick-start) · [CLI](#-cli-reference) · [Server](#-local-web-server) · [Recovery](#-recovery-and-troubleshooting)

</div>

---

The wiki is the cross-project memory layer of `academic-research-prisma-wiki-rag`. It is not a separate OpenClaw plugin and it is not the per-review Hybrid RAG database. Markdown remains the source of truth; embedded Qdrant provides semantic retrieval over that source.

## 🎯 What the wiki does

| Layer | Directory | Purpose | Writer |
|---|---|---|---|
| **Domain knowledge** | `wiki-works/<project>/` | Papers, entities, concepts and syntheses from one domain | ingest workflows |
| **Distilled knowledge** | `wiki/` | Cross-project concepts and syntheses | controlled promotion/ingest |
| **Identity** | `wiki/identity/` | Stable behavioral guidance | reflection workflow |

All layers share one Qdrant vector space. Directory boundaries organize ownership; they do not hide pages from search.

### Core invariants

- Markdown pages are authoritative; `memory/qdrant/` is rebuildable.
- Pages enter through `wiki.py ingest`, using staged `.md.tmp` inputs and a workspace lock.
- Raw PDF text is deposited under `raw/` before transformation into structured pages.
- Paths matching `exclude_from_index` never enter retrieval.
- CLI and HTTP queries share ranking and reranker configuration.
- One embedded Qdrant directory has one writer at a time.

---

## 🏗️ Architecture

```text
<W>/                              # data workspace, outside the plugin
├── wiki.config.json
├── wiki-session.md                # operation and recovery state
├── wiki/
│   ├── concepts/  ├── entities/  ├── synthesis/  └── identity/
├── wiki-works/<project>/
│   ├── raw/  ├── concepts/  ├── entities/  └── synthesis/
├── pdf-inbox/.registry.json
└── memory/qdrant/                # generated local index

<PLUGIN_ROOT>/wiki/                 # executable code, never research data
├── scripts/wiki.py                 # CLI entry point
├── scripts/wiki_workflows.py       # ingest/query/lint
├── scripts/wiki_embed.py           # chunking and BGE-M3
├── scripts/wiki_qdrant.py          # Qdrant operations
├── scripts/wiki_rerank.py          # BGE cross-encoder ranking
├── scripts/wiki_pdf_watcher.py     # local/remote PDF intake
├── scripts/wiki_graph.py           # graph and page details
├── scripts/wiki_server.py          # FastAPI, auth, WebSocket
└── frontend/index.html             # D3 browser UI
```

### Staged ingest and recovery

```text
.md.tmp pages → lock → validate → Qdrant staging
              → promote Markdown + vectors → index/log/mini-lint → unlock
```

Validation and pre-promotion failures leave committed pages unchanged. A late failure after vector promotion can require `lint --full` and `rebuild` to resynchronize Qdrant with the restored Markdown; `wiki-session.md` surfaces incomplete or repair-required work at the next session.

---

## 🔎 Retrieval pipeline

```text
query → BAAI/bge-m3 (1024d) → Qdrant candidates (k × 4)
      → exclusions + one chunk/page → BGE reranker → top-k excerpts
```

CLI and `/api/context` rank full chunks before truncation. If `BAAI/bge-reranker-v2-m3` cannot infer, the query logs a warning and returns vector order rather than failing. Model load, embedding, Qdrant access and reranking run off the HTTP event loop.

Verify actual GPU placement through inference:

```bash
python "<PLUGIN_ROOT>/wiki/scripts/check_models.py" --workspace "<W>"
python "<PLUGIN_ROOT>/wiki/scripts/check_models.py" --workspace "<W>" --require-cuda
```

The JSON includes Python, Torch/CUDA, both model devices, vector size and a reranker score.

---

## 🚀 Quick Start

Use Python 3.11+ and one environment shared by installation and Claude Code.

Linux:

```bash
python3 -m venv "/path/to/research-env"
source "/path/to/research-env/bin/activate"
python -m pip install -r "<PLUGIN_ROOT>/requirements.txt"
```

Windows PowerShell:

```powershell
py -3 -m venv "C:/path/to/research-env"
& "C:/path/to/research-env/Scripts/Activate.ps1"
python -m pip install -r "C:/path/to/plugin/requirements.txt"
```

Start Claude from that terminal. The manifest launches `python`, not the Windows-only `py` alias.

There is no shared/global wiki workspace to hand-configure: each study gets its own sealed `<W>` automatically. Bootstrap a study with `pipeline-ricerca` (`/pipeline-ricerca nuova`, or the natural-language intent "let's start a new research"):

```bash
python "<PLUGIN_ROOT>/scripts/study_workspace.py" create --name "<study name>" --parent "<CURRENT_WORKSPACE>"
```

This generates `<CURRENT_WORKSPACE>/<study-slug>/` with `wiki-memory/` already containing a study-scoped `wiki.config.json` — `<W>` below is `<study-root>/wiki-memory`. Confirm the printed `project_root` before using it. Then run:

```bash
python "<PLUGIN_ROOT>/wiki/scripts/wiki_check_setup.py" --workspace "<W>"
python "<PLUGIN_ROOT>/wiki/scripts/wiki.py" rebuild --workspace "<W>"
python "<PLUGIN_ROOT>/wiki/scripts/wiki.py" query --workspace "<W>" --q "research question" --k 5
```

Paths must be absolute and quoted. Page paths passed to `--pages` are relative to `<W>`.

---

## 🧰 CLI Reference

```text
python "<PLUGIN_ROOT>/wiki/scripts/wiki.py" <command> ...

ingest         --workspace <W> --pages <p1.tmp,p2.tmp,...> --log <message>
query          --workspace <W> --q <text> [--k 5]
lint           --workspace <W> [--full]
index          --workspace <W>
rebuild        --workspace <W>
session-update --workspace <W> --op <type> --status <status> [--detail <json>]
scan-inbox     --workspace <W>
ingest-pdf     --workspace <W> --file <local-path-or-url>
process-raw    --workspace <W>
serve          --workspace <W> [--host 127.0.0.1] [--port 7331] [--no-auth]
```

Examples:

```bash
python "<PLUGIN_ROOT>/wiki/scripts/wiki.py" ingest-pdf --workspace "<W>" --file "/data/paper.pdf"
python "<PLUGIN_ROOT>/wiki/scripts/wiki.py" ingest --workspace "<W>" --pages "wiki-works/research/entities/paper.md.tmp" --log "ingest | paper"
python "<PLUGIN_ROOT>/wiki/scripts/wiki.py" lint --workspace "<W>" --full
```

---

## 🌐 Local web server

```bash
python "<PLUGIN_ROOT>/wiki/scripts/wiki.py" serve --workspace "<W>" --host 127.0.0.1 --port 7331
```

The FastAPI server exposes the D3 graph, page details, statistics, lint actions and WebSocket updates. `/api/context` accepts loopback callers only. Authentication is enabled unless `--no-auth` is selected; set `WIKI_PASSWORD` rather than storing a password in version control.

---

## 🩺 Recovery and troubleshooting

| Symptom | Cause | Action |
|---|---|---|
| `lock_exists` | another write or interrupted operation | verify the owner; never remove a live lock |
| CUDA expected, CPU reported | CPU Torch build, driver mismatch or hidden GPU | run `check_models.py --require-cuda` from Claude's environment |
| model missing offline | weights absent from cache | download online once or supply a populated Hugging Face cache |
| dimension mismatch | index created with another embedding model | keep the model or run `rebuild` |
| no results | empty/stale index or exclusions | check setup/exclusions, then rebuild |
| Windows import errors | Claude uses another Python | activate the environment and launch Claude from the same PowerShell |
| Qdrant storage error | concurrent writers or permissions | stop the other process and verify the path |

Safe recovery: read `wiki-session.md`; stop other writers; run `wiki_check_setup.py`; run `lint --full`; rebuild only after validating Markdown. The index is disposable, source pages are not.

---

## 🧪 Verification and docs

```bash
python -m pytest wiki/tests -q
python -m compileall -q wiki/scripts
```

CI runs on Windows and Ubuntu. Hosted runners verify CPU; CUDA hardware uses `check_models.py --require-cuda`.

- [Main README](../README.md) / [Italian](../README.it.md)
- [Windows/Linux and model setup](../docs/models-and-setup.md)
- [Design](DESIGN.md) / [Italian](DESIGN.it.md)
- [Specification](SPEC.md) / [Italian](SPEC.it.md)
- [Roadmap](ROADMAP.md) / [Italian](ROADMAP.it.md)

---

<div align="center">Part of **academic-research-prisma-wiki-rag v1.2.0**</div>
