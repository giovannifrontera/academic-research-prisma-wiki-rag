<div align="center">

# 🔬 academic-research-prisma-wiki-rag

### PRISMA systematic review + persistent knowledge memory

[![Claude Code](https://img.shields.io/badge/Claude_Code-compatible-cc785c?style=flat-square&logo=anthropic&logoColor=white)](https://claude.ai/code)
[![Python](https://img.shields.io/badge/Python-3.11+-3776ab?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![MCP](https://img.shields.io/badge/MCP-5_servers-1a7f37?style=flat-square)](https://modelcontextprotocol.io)
[![LanceDB](https://img.shields.io/badge/LanceDB-vectors-f4a261?style=flat-square)](https://lancedb.com)
[![PRISMA](https://img.shields.io/badge/PRISMA-2020-8b1a1a?style=flat-square)](https://www.prisma-statement.org)
[![License](https://img.shields.io/badge/License-AGPL_3.0-blue?style=flat-square)](LICENSE)

[What it adds](#-what-this-adds) · [Architecture](#-architecture) · [Skills](#-skills) · [Wiki layer](#-wiki-memory-layer) · [MCP Servers](#-mcp-servers) · [Quick Start](#-quick-start) · [Ecosystem](#-ai-wiki-ecosystem)

</div>

---

> **Relation to [`academic-PRISMA-research-workflow`](https://github.com/giovannifrontera/academic-PRISMA-research-workflow):**
> The base repo provides the PRISMA pipeline as pure Claude Code skills + MCP servers.
> This repo adds a **persistent vector memory layer** — knowledge extracted from each review accumulates in LanceDB
> and is available to all future reviews and study designs, without re-reading any paper.
> The base repo is archived; use this one.

---

## 🎯 What this adds

A standard PRISMA review is stateless: every new session starts from zero, even if you reviewed the same topic months ago.

This project couples the PRISMA workflow to a **long-term research wiki** backed by LanceDB vector embeddings (BGE-M3). After each review, extracted evidence is ingested into the wiki. Before the next review, the wiki is queried — the agent already knows what you found last time. Knowledge compounds across projects.

Knowledge is stored in two layers:

| Layer | Path | What goes in |
|---|---|---|
| **Project knowledge** | `wiki-works/ricerca/<project>/` | Papers, syntheses, extraction tables for each PRISMA review |
| **Distilled knowledge** | `wiki/concepts/`, `wiki/synthesis/` | Cross-project concepts, promoted automatically by the agent |

The bridge is the `wiki_workspace` field in `prisma_state.json` — the PRISMA skill writes to it; the wiki skill reads from it.

---

## 🏗 Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                    Claude Code session                        │
│                                                              │
│  ┌──────────────┐   feeds    ┌────────────────────────────┐  │
│  │ prisma-review│ ─────────▶ │      wiki-core skill       │  │
│  │    skill     │            │  (wiki.py CLI interface)   │  │
│  └──────┬───────┘            └──────────┬─────────────────┘  │
│         │ state files                   │ ingest / query      │
│         ▼                               ▼                     │
│  prisma_state.json ◀─wiki_workspace─ LanceDB (BGE-M3)        │
│  prisma_log.md                       wiki-works/ricerca/      │
│  screening_log.md                    wiki/concepts/           │
│  extraction_matrix.md                wiki/synthesis/          │
└──────────────────────────────────────────────────────────────┘
         │
         ▼  query before new review
  "What do we already know about spaced repetition?"
  → retrieved from vector index, injected as context
```

### State-Handoff Pattern

Each pipeline stage writes a structured state file. A researcher can pause for weeks, resume in a new session, and reconstruct full context from files — no information is lost between sessions.

```
research-state/
  prisma_state.json       # phase tracker, DB results, wiki_workspace link
  prisma_log.md           # official methodological log → feeds paper Methods section
  screening_log.md        # inclusion/exclusion decisions with justifications
  extraction_matrix.md    # structured data: study, n, effect size, RoB, design
```

---

## 🛠 Skills

| Skill | Role |
|---|---|
| `prisma-review` | 4-phase PRISMA workflow with human gates; writes all state files |
| `wiki-core` | Long-term memory — ingest papers, query evidence, promote cross-project knowledge |
| `educational-pilot-design` | Quasi-experimental study protocol grounded in Visible Learning / Campbell standards |
| `hybrid-rag` | Dense (BGE-M3) + sparse (BM25) evidence synthesis from indexed PDFs |
| `pandoc-export` | APA 7 / Chicago / LaTeX publication-ready output from Markdown |
| `pipeline-ricerca` | Orchestrator — sequences the above skills across a full research project |

### Install skills

```bash
git clone https://github.com/giovannifrontera/academic-research-prisma-wiki-rag
cd academic-research-prisma-wiki-rag

# Linux/macOS
cp -r skills/* ~/.claude/skills/

# Windows
Copy-Item -Recurse skills\* $env:USERPROFILE\.claude\skills\
```

---

## 📚 Wiki Memory Layer

The wiki layer is a standalone Python system with a single CLI entry point: `wiki/scripts/wiki.py`.

### Components

| Script | Role |
|---|---|
| `wiki.py` | Entry point — `query`, `ingest`, `ingest-pdf`, `process-raw`, `serve` |
| `wiki_embed.py` | Text chunking + BGE-M3 embeddings |
| `wiki_lancedb.py` | LanceDB vector store operations |
| `wiki_index.py` | Generates browsable `index.md` from the knowledge graph |
| `wiki_graph.py` | D3.js knowledge graph data export |
| `wiki_server.py` | FastAPI server — `/api/context` for fast in-session retrieval |
| `wiki_workflows.py` | Automated promotion of `raw/` → indexed concepts |

### Browser frontend

`wiki/frontend/index.html` — knowledge graph visualisation and wiki browser. No build step required.

### Setup

```bash
pip install -r wiki/requirements.txt
```

Configure `wiki/wiki.config.json`: set `"workspace"` to the absolute path of your wiki directory.

### Usage from Claude Code

```
# Query existing knowledge before starting a new review
/wiki-core query "effect size of spaced repetition on retention"

# Ingest a completed PRISMA extraction
/wiki-core ingest research-state/extraction_matrix.md --project spaced-repetition-2026

# Serve for fast retrieval during a session
python wiki/scripts/wiki.py serve --workspace /path/to/wiki --port 7331
```

---

## 🌐 MCP Servers

Five MCP servers connect Claude directly to open academic databases:

| Server | Coverage | Key Use Case |
|---|---|---|
| **ERIC** | US education research (1.6M records) | EdTech, learning sciences |
| **OpenAIRE** | European open-access research | HORIZON-funded studies |
| **CORE** | 220M+ open-access papers | Broad academic search |
| **DOAJ** | Directory of Open Access Journals | Journal-level quality filter |
| **Zenodo** | CERN open research repository | Datasets, preprints, software |

```bash
claude mcp add eric python mcp-servers/eric/server.py
claude mcp add openaire python mcp-servers/openaire/server.py
claude mcp add core python mcp-servers/core/server.py
claude mcp add doaj python mcp-servers/doaj/server.py
claude mcp add zenodo python mcp-servers/zenodo/server.py
```

---

## 🚀 Quick Start

```bash
# 1. Clone and install skills
git clone https://github.com/giovannifrontera/academic-research-prisma-wiki-rag
cd academic-research-prisma-wiki-rag
cp -r skills/* ~/.claude/skills/

# 2. Install wiki dependencies
pip install -r wiki/requirements.txt

# 3. Configure MCP servers (see above)

# 4. Open Claude Code in your research project directory

# 5. Query wiki before starting (empty on first use — will grow with each review)
/wiki-core query "your research question"

# 6. Run a PRISMA review
/prisma-review "What is the effect of spaced repetition on long-term retention?"

# 7. Ingest results after completion — knowledge persists for future reviews
/wiki-core ingest research-state/extraction_matrix.md --project my-review-2026
```

---

## 📊 Theoretical Framework

### PRISMA 2020
The workflow follows the [PRISMA 2020 statement](https://www.prisma-statement.org) (Page et al., 2021). All pipeline stages map to the PRISMA flow: identification, screening, eligibility, inclusion.

### Evidence-Based Education
The research design module is grounded in Hattie's synthesis of 800+ meta-analyses (Hattie, 2009). Effect size thresholds (d > 0.40) and construct validity criteria follow Visible Learning methodology.

### Campbell Collaboration & Cochrane
Quality assessment follows the Campbell Collaboration's systematic review standards and Cochrane's risk-of-bias framework, adapted for educational and social science contexts.

---

## 🌐 AI-Wiki Ecosystem

| Project | LLM | Role |
|---|---|---|
| [ai-wiki-graph-RAG-lms](https://github.com/giovannifrontera/ai-wiki-graph-RAG-lms) | Anthropic / OpenAI | LTI 1.3 backend for Moodle, Canvas, Blackboard, Sakai, Open edX |
| [ai-longterm-wiki-memory-ClaudeCode](https://github.com/giovannifrontera/ai-longterm-wiki-memory-ClaudeCode) | Claude | Native Claude Code integration — MCP + hooks |
| [ai-longterm-wiki-memory-OpenClaw](https://github.com/giovannifrontera/ai-longterm-wiki-memory-OpenClaw) | Any (LLM-agnostic) | OpenClaw plugin — works with any model |
| [academic-PRISMA-research-workflow](https://github.com/giovannifrontera/academic-PRISMA-research-workflow) | Claude | Base PRISMA workflow — no wiki layer (archived) |
| **academic-research-prisma-wiki-rag** ← *you are here* | Claude | PRISMA + persistent wiki memory |

---

## 📖 References

1. Page, M. J., McKenzie, J. E., Bossuyt, P. M., et al. (2021). The PRISMA 2020 statement. *BMJ*, 372, n71.
2. Hattie, J. (2009). *Visible Learning*. Routledge.
3. Campbell Collaboration. (2023). *Systematic reviews in social science and education*.
4. Nosek, B. A., et al. (2015). Promoting an open research culture. *Science*, 348(6242), 1422–1425.
5. Gough, D., Oliver, S., & Thomas, J. (Eds.). (2017). *An Introduction to Systematic Reviews* (2nd ed.). SAGE.

---

<div align="center">

*Developed by [Giovanni Frontera, Ph.D.](https://github.com/giovannifrontera) · Part of the AI-Wiki Ecosystem*

</div>
