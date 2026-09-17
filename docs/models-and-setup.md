# Python, models and portable paths

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

If activation is unavailable, use the environment's absolute Python executable for every command (PowerShell requires `&` before a quoted executable path). Verify `python -c "import sys; print(sys.executable)"` and start Claude from this same terminal. The plugin's MCP configuration invokes `python` from PATH.

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
