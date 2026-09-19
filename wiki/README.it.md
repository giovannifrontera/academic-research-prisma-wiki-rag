<div align="center">

# 🧠 Memoria Wiki PRISMA

### Conoscenza persistente e ispezionabile per il plugin Academic PRISMA di Claude Code

[![Release](https://img.shields.io/badge/release-v1.2.0-informational?style=flat-square)](https://github.com/giovannifrontera/academic-research-prisma-wiki-rag/releases/tag/v1.2.0)
[![Test](https://img.shields.io/badge/test-140%20passati-brightgreen?style=flat-square)](tests/)
[![Python](https://img.shields.io/badge/python-3.11+-3776ab?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![Qdrant](https://img.shields.io/badge/vector_store-Qdrant-f4a261?style=flat-square)](https://qdrant.tech)
[![Licenza](https://img.shields.io/badge/licenza-AGPL--3.0-blue?style=flat-square)](../LICENSE)

**Italiano** · [English](README.md) · [README principale](../README.it.md)

[Concetto](#-cosa-fa-la-wiki) · [Architettura](#️-architettura) · [Retrieval](#-pipeline-di-retrieval) · [Avvio](#-avvio-rapido) · [CLI](#-riferimento-cli) · [Server](#-server-web-locale) · [Ripristino](#-ripristino-e-risoluzione-dei-problemi)

</div>

---

La wiki è la memoria cross-progetto di `academic-research-prisma-wiki-rag`. Non è un plugin OpenClaw separato e non coincide con il database Hybrid RAG della singola revisione. I file Markdown sono la fonte autorevole; Qdrant embedded fornisce il recupero semantico.

## 🎯 Cosa fa la wiki

| Livello | Directory | Scopo | Chi scrive |
|---|---|---|---|
| **Dominio** | `wiki-works/<progetto>/` | Paper, entità, concetti e sintesi del dominio | workflow ingest |
| **Distillato** | `wiki/` | Concetti e sintesi cross-progetto | promozione/ingest controllato |
| **Identità** | `wiki/identity/` | Indicazioni comportamentali stabili | workflow di riflessione |

Tutti i livelli condividono lo stesso spazio Qdrant. Le directory organizzano la proprietà, ma non impediscono la ricerca.

### Invarianti

- Il Markdown è autorevole; `memory/qdrant/` è ricostruibile.
- Le pagine entrano tramite `wiki.py ingest`, da `.md.tmp` in staging e sotto lock.
- Il testo PDF grezzo va in `raw/` prima della trasformazione.
- I path in `exclude_from_index` non entrano nel retrieval.
- CLI e HTTP condividono ranking e reranker.
- Una directory Qdrant embedded ha un solo writer.

---

## 🏗️ Architettura

```text
<W>/                              # dati fuori dal plugin
├── wiki.config.json
├── wiki-session.md                # stato e recovery
├── wiki/
│   ├── concepts/  ├── entities/  ├── synthesis/  └── identity/
├── wiki-works/<progetto>/
│   ├── raw/  ├── concepts/  ├── entities/  └── synthesis/
├── pdf-inbox/.registry.json
└── memory/qdrant/                # indice locale generato

<PLUGIN_ROOT>/wiki/                 # codice, mai dati di ricerca
├── scripts/wiki.py                 # entry point CLI
├── scripts/wiki_workflows.py       # ingest/query/lint
├── scripts/wiki_embed.py           # chunking e BGE-M3
├── scripts/wiki_qdrant.py          # operazioni Qdrant
├── scripts/wiki_rerank.py          # ranking cross-encoder
├── scripts/wiki_pdf_watcher.py     # ingresso PDF
├── scripts/wiki_graph.py           # grafo e pagine
├── scripts/wiki_server.py          # FastAPI, auth, WebSocket
└── frontend/index.html             # UI D3
```

### Ingest in staging e recovery

```text
pagine .md.tmp → lock → validazione → staging Qdrant
                → promozione Markdown + vettori → indice/log/mini-lint → unlock
```

Gli errori prima della promozione non alterano le pagine committate. Un errore tardivo dopo la promozione vettoriale può richiedere `lint --full` e `rebuild` per riallineare Qdrant al Markdown ripristinato; `wiki-session.md` segnala i lavori incompleti o da riparare.

---

## 🔎 Pipeline di retrieval

```text
query → BAAI/bge-m3 (1024d) → candidati Qdrant (k × 4)
      → esclusioni + un chunk/pagina → reranker BGE → estratti top-k
```

CLI e `/api/context` riordinano i chunk completi prima del taglio. Se `BAAI/bge-reranker-v2-m3` fallisce, viene registrata una warning e resta l'ordine vettoriale. Modelli, embedding, Qdrant e reranking lavorano fuori dall'event loop HTTP.

Verifica il dispositivo con inferenza reale:

```bash
python "<PLUGIN_ROOT>/wiki/scripts/check_models.py" --workspace "<W>"
python "<PLUGIN_ROOT>/wiki/scripts/check_models.py" --workspace "<W>" --require-cuda
```

Il JSON riporta Python, Torch/CUDA, device dei due modelli, dimensione e score del reranker.

---

## 🚀 Avvio rapido

Usa Python 3.11+ e un solo ambiente per installazione e Claude Code.

Linux:

```bash
python3 -m venv "/percorso/research-env"
source "/percorso/research-env/bin/activate"
python -m pip install -r "<PLUGIN_ROOT>/requirements.txt"
```

Windows PowerShell:

```powershell
py -3 -m venv "C:/percorso/research-env"
& "C:/percorso/research-env/Scripts/Activate.ps1"
python -m pip install -r "C:/percorso/plugin/requirements.txt"
```

Avvia Claude dallo stesso terminale. Il manifest usa `python`, non l'alias Windows `py`.

Non esiste più un workspace wiki condiviso/globale da configurare a mano: ogni studio riceve automaticamente il proprio `<W>` sigillato. Avvia uno studio con `pipeline-ricerca` (`/pipeline-ricerca nuova`, oppure l'intento in linguaggio naturale "iniziamo una nuova ricerca"):

```bash
python "<PLUGIN_ROOT>/scripts/study_workspace.py" create --name "<nome studio>" --parent "<CURRENT_WORKSPACE>"
```

Questo genera `<CURRENT_WORKSPACE>/<study-slug>/` con `wiki-memory/` già contenente un `wiki.config.json` specifico dello studio — `<W>` qui sotto è `<study-root>/wiki-memory`. Conferma il `project_root` stampato prima di usarlo. Poi esegui:

```bash
python "<PLUGIN_ROOT>/wiki/scripts/wiki_check_setup.py" --workspace "<W>"
python "<PLUGIN_ROOT>/wiki/scripts/wiki.py" rebuild --workspace "<W>"
python "<PLUGIN_ROOT>/wiki/scripts/wiki.py" query --workspace "<W>" --q "domanda di ricerca" --k 5
```

I path devono essere assoluti e tra virgolette. I path di `--pages` sono relativi a `<W>`.

---

## 🧰 Riferimento CLI

```text
python "<PLUGIN_ROOT>/wiki/scripts/wiki.py" <comando> ...

ingest         --workspace <W> --pages <p1.tmp,p2.tmp,...> --log <messaggio>
query          --workspace <W> --q <testo> [--k 5]
lint           --workspace <W> [--full]
index          --workspace <W>
rebuild        --workspace <W>
session-update --workspace <W> --op <tipo> --status <stato> [--detail <json>]
scan-inbox     --workspace <W>
ingest-pdf     --workspace <W> --file <path-locale-o-url>
process-raw    --workspace <W>
serve          --workspace <W> [--host 127.0.0.1] [--port 7331] [--no-auth]
```

Esempi:

```bash
python "<PLUGIN_ROOT>/wiki/scripts/wiki.py" ingest-pdf --workspace "<W>" --file "/dati/paper.pdf"
python "<PLUGIN_ROOT>/wiki/scripts/wiki.py" ingest --workspace "<W>" --pages "wiki-works/ricerca/entities/paper.md.tmp" --log "ingest | paper"
python "<PLUGIN_ROOT>/wiki/scripts/wiki.py" lint --workspace "<W>" --full
```

---

## 🌐 Server web locale

```bash
python "<PLUGIN_ROOT>/wiki/scripts/wiki.py" serve --workspace "<W>" --host 127.0.0.1 --port 7331
```

FastAPI espone grafo D3, pagine, statistiche, lint e WebSocket. `/api/context` accetta solo loopback. L'autenticazione è attiva salvo `--no-auth`; usa `WIKI_PASSWORD` anziché salvare password nel repository.

---

## 🩺 Ripristino e risoluzione dei problemi

| Sintomo | Causa | Azione |
|---|---|---|
| `lock_exists` | altra scrittura o operazione interrotta | verifica il proprietario; non rimuovere un lock vivo |
| GPU attesa, CPU rilevata | Torch CPU, driver o GPU nascosta | esegui `check_models.py --require-cuda` nell'ambiente Claude |
| modello offline assente | pesi non in cache | scarica online o fornisci una cache Hugging Face |
| dimensione errata | indice creato con altro modello | mantieni il modello o usa `rebuild` |
| nessun risultato | indice vuoto/obsoleto o esclusioni | controlla setup/esclusioni e ricostruisci |
| import Windows fallito | Claude usa un altro Python | attiva l'ambiente e avvia Claude dalla stessa PowerShell |
| storage Qdrant in errore | writer concorrenti o permessi | arresta l'altro processo e verifica il path |

Recovery sicuro: leggi `wiki-session.md`; arresta altri writer; esegui `wiki_check_setup.py`; esegui `lint --full`; ricostruisci solo dopo aver validato il Markdown. L'indice è eliminabile, le fonti no.

---

## 🧪 Verifica e documenti

```bash
python -m pytest wiki/tests -q
python -m compileall -q wiki/scripts
```

La CI gira su Windows e Ubuntu. I runner hosted verificano la CPU; l'hardware CUDA usa `check_models.py --require-cuda`.

- [README principale](../README.it.md) / [English](../README.md)
- [Setup Windows/Linux e modelli](../docs/models-and-setup.md)
- [Design](DESIGN.it.md) / [English](DESIGN.md)
- [Specifica](SPEC.it.md) / [English](SPEC.md)
- [Roadmap](ROADMAP.it.md) / [English](ROADMAP.md)

---

<div align="center">Parte di **academic-research-prisma-wiki-rag v1.2.0**</div>
