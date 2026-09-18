# Python, models and portable paths

> Release 1.2.0 · [English README](../README.md) · [Guida italiana](../README.it.md)

Use Python 3.11+ and one activated virtual environment for installation, CLI commands and the Claude process that launches the MCP servers. Create the environment outside the installed plugin cache. Replace all example paths with your own absolute paths.

Linux (Bash):

```bash
python3 -m venv "/path/to/research env"
source "/path/to/research env/bin/activate"
python -m pip install -r "/path/to/plugin/requirements.txt"
```

Windows (PowerShell):

```powershell
py -3 -m venv "C:/path/to/research env"
& "C:/path/to/research env/Scripts/Activate.ps1"
python -m pip install -r "C:/path/to/plugin/requirements.txt"
```

If activation is unavailable, use the environment's absolute Python executable for every command (PowerShell requires `&` before a quoted executable path). Verify `python -c "import sys; print(sys.executable)"` and start Claude from this same terminal. The plugin's MCP configuration invokes `python` from PATH. On Windows, `py` can create the environment but is not the executable used by the plugin.

Optional MCP credentials are read from the process environment:

| Variable | Required | Purpose |
|---|---|---|
| `CORE_API_KEY` | Recommended | Practical CORE API rate limits |
| `SEMANTIC_SCHOLAR_API_KEY` | Optional | Higher Semantic Scholar limits |

Set them before starting Claude. Never put them in the plugin manifest, documentation, or a tracked `.env` file.

## GPU and model setup

For GPU acceleration, select your OS and supported compute platform in the [official PyTorch installer](https://pytorch.org/get-started/locally/), and run its command with `python -m pip` in this environment. Do not copy a CUDA wheel version from another machine. Verify the installed build:

```text
python -c "import torch; print('torch:', torch.__version__); print('CUDA build:', torch.version.cuda); print('GPU available:', torch.cuda.is_available()); print(torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU')"
```

Automatic device selection uses an available supported accelerator and otherwise CPU; CPU execution is valid but slower. A missing driver or CPU-only PyTorch build can make an installed GPU unavailable. The first model load downloads weights; offline execution requires those weights already cached. Do not commit machine-specific interpreter or cache paths.

Run a real embedding and reranker inference using the configured wiki models:

```text
python "<PLUGIN_ROOT>/wiki/scripts/check_models.py" --workspace "<W>"
python "<PLUGIN_ROOT>/wiki/scripts/check_models.py" --workspace "<W>" --require-cuda
```

The first check accepts CPU. The optional second check requires CUDA and fails if only CPU is available; the JSON output identifies the interpreter, torch build and model devices.

| Component | Configuration |
|---|---|
| Wiki memory | Qdrant, `BAAI/bge-m3`, `BAAI/bge-reranker-v2-m3` with reranking enabled in `wiki.config.json` |
| Per-review hybrid RAG | Qdrant default, dense + BM25 + RRF; MiniLM remains the model default; explicitly select `bge-m3` for the BGE workflow |

These are independent indexes. Hybrid RAG does not automatically inherit the wiki model or reranker. See the official [BGE-M3 model card](https://huggingface.co/BAAI/bge-m3) and [reranker model card](https://huggingface.co/BAAI/bge-reranker-v2-m3).

## Plugin code versus research data

Resolve `<PLUGIN_ROOT>` from the installed skill location: a skill at `<PLUGIN_ROOT>/skills/<name>/SKILL.md` has its resources alongside that file. Use the actual installation path, not a presumed user skills directory. `<REVIEW>` is the review's data directory; `<W>` is the separate wiki data workspace. These angle-bracket names are placeholders, not shell variables. Substitute literal absolute paths and retain quotes.

Run hybrid RAG from `<REVIEW>` because `rag_db/` is relative to the current directory. Execute code by absolute path, for example:

```text
python "<PLUGIN_ROOT>/skills/hybrid-rag/hybrid_rag_template.py" choose-backend --backend qdrant
python "<PLUGIN_ROOT>/skills/hybrid-rag/hybrid_rag_template.py" choose-model --model bge-m3
python "<PLUGIN_ROOT>/skills/hybrid-rag/hybrid_rag_template.py" init
python "<PLUGIN_ROOT>/wiki/scripts/wiki.py" query --workspace "<W>" --q "research question" --k 5
```

All commands above occupy a single line and work in Bash and PowerShell after substitution and activation. Wiki page paths passed to `--pages` are relative to `<W>`, not the review directory. Copy `wiki/wiki.config.json` from the resolved plugin root to `<W>/wiki.config.json` before configuring your data workspace.

### Sealed study directory layout

A study bootstrapped with `python "<PLUGIN_ROOT>/scripts/study_workspace.py" create --name "<study name>" --parent "<CURRENT_WORKSPACE>"` generates a self-contained study root (`<CURRENT_WORKSPACE>/<study-slug>/`) with this layout (see `docs/superpowers/specs/2026-09-17-isolated-study-workspace-design.md`, "Directory Layout"):

```text
<CURRENT_WORKSPACE>/
└── <study-slug>/                         # canonical study root
    ├── .project-state.json              # master state and isolation contract
    ├── README.md                        # generated study overview and commands
    ├── project-log.md                   # append-only orchestration log
    ├── prisma/
    │   ├── prisma_state.json
    │   ├── prisma_log.md
    │   ├── screening_log.md
    │   ├── screening_prisma.json
    │   ├── eligibility_prisma.json
    │   └── prisma_synthesis.md
    ├── sources/
    │   ├── pdf-inbox/
    │   └── pdf-inclusi/
    ├── database/
    │   ├── qdrant-rag/               # PRISMA/Hybrid RAG vector database
    │   └── qdrant-wiki/              # wiki vector database
    ├── wiki-memory/                      # private wiki workspace for this study
    │   ├── wiki.config.json
    │   ├── wiki-session.md
    │   ├── wiki/
    │   │   ├── concepts/
    │   │   ├── synthesis/
    │   │   └── identity/
    │   ├── wiki-works/
    │   │   └── <study-slug>/
    │   │       ├── raw/
    │   │       ├── entities/
    │   │       ├── concepts/
    │   │       └── synthesis/
    │   └── pdf-inbox/
    ├── synthesis/
    ├── design/
    ├── preprint/
    └── export/
```

With this layout, all research data (PRISMA files, PDF sources, both vector databases, wiki-memory, synthesis, design, preprint, export) lives under the generated study root — `<REVIEW>` and `<W>` above both resolve inside it (`<study-root>` and `<study-root>/wiki-memory` respectively). Plugin code (`skills/`, `scripts/`, `wiki/`) remains the only external read boundary; it is never a write target for study data.
