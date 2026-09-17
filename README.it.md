<div align="center">

# 🔬 academic-research-prisma-wiki-rag

### Revisione sistematica, studi pilota e pubblicazione accademica assistiti dall'AI — con memoria persistente

[![Claude Code](https://img.shields.io/badge/Claude_Code-compatibile-cc785c?style=flat-square&logo=anthropic&logoColor=white)](https://claude.ai/code)
[![Release](https://img.shields.io/badge/release-v1.2.0-informational?style=flat-square)](https://github.com/giovannifrontera/academic-research-prisma-wiki-rag/releases/tag/v1.2.0)
[![Python](https://img.shields.io/badge/Python-3.11+-3776ab?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![MCP](https://img.shields.io/badge/MCP-6_server-1a7f37?style=flat-square)](https://modelcontextprotocol.io)
[![Qdrant](https://img.shields.io/badge/Qdrant-vectors-f4a261?style=flat-square)](https://qdrant.tech)
[![PRISMA](https://img.shields.io/badge/PRISMA-2020-8b1a1a?style=flat-square)](https://www.prisma-statement.org)
[![Licenza](https://img.shields.io/badge/Licenza-AGPL_3.0-blue?style=flat-square)](LICENSE)

**Italiano** · [English](README.md)

[Problema](#-il-problema) · [Pipeline](#-pipeline-di-ricerca) · [Skill](#-skill-principali) · [Wiki](#-memoria-wiki) · [MCP](#-server-mcp-accademici) · [Installazione](#-avvio-rapido) · [Operatività](#️-operatività-e-risoluzione-dei-problemi) · [Sicurezza](#-confini-dei-dati-e-sicurezza)

</div>

---

> **Edizione estesa di [`academic-PRISMA-research-workflow`](https://github.com/giovannifrontera/academic-PRISMA-research-workflow) (archiviato).**
> Mantiene l'intera pipeline — PICO → PRISMA → sintesi → studio pilota → preprint — e aggiunge una memoria Qdrant persistente. La conoscenza estratta viene riutilizzata nei progetti successivi invece di andare persa al termine della sessione.

---

## 🎯 Il problema

Una revisione sistematica rigorosa richiede mesi di ricerca, deduplicazione, screening, valutazione del full text, estrazione dati e controllo qualità. Nei settori ad alta produzione scientifica la sintesi non tiene il passo con le pubblicazioni e ogni nuova revisione riparte da zero, anche quando condivide costrutti o popolazioni con lavori precedenti.

Questo plugin trasforma Claude Code in un **orchestratore metodologico specializzato**. Automatizza le attività ripetitive senza rimuovere i gate umani: ogni esclusione è motivata, ogni fase produce uno stato persistente e il corpus RAG accetta soltanto i contratti di export eligibility previsti dalla pipeline.

### Quadro metodologico

- **PRISMA 2020:** identificazione, screening, eligibility e inclusione sono mappati nei file di stato e nei log.
- **Campbell e Cochrane:** qualità e rischio di bias sono adattati alle scienze educative e sociali.
- **Evidence-Based Education:** effect size, validità dei costrutti e strumenti sono estratti in forma confrontabile.
- **Open Science:** gli output sono predisposti per audit, riuso e deposito aperto.

L'AI assiste il processo; non sostituisce il revisore su criteri, casi borderline, qualità metodologica o interpretazione finale.

---

## 🔄 Pipeline di ricerca

```text
Memoria Wiki → PICO → Identificazione → Deduplicazione → Screening
     ↑                                                   ↓
     └─ nuova conoscenza ← Estrazione ← Qualità ← Eligibility full text
                              ↓
                  Hybrid RAG → Studio pilota → DOCX
```

### Handoff persistente

Ogni fase scrive file JSON e Markdown che permettono di interrompere e riprendere il lavoro senza dipendere dalla cronologia della chat:

```text
research-state/
├── prisma_state.json       # fase, PICO, risultati e workspace wiki
├── prisma_log.md           # log metodologico per la sezione Methods
├── screening_log.md        # decisioni e motivazioni
├── eligibility_prisma.json # soli studi inclusi
├── extraction_matrix.md    # campione, design, outcome, effect size, RoB
├── synthesis-evidence.md   # sintesi narrativa fondata sulle fonti
└── export-manifest.json    # configurazione DOCX
```

`wiki_workspace` collega la revisione alla memoria trasversale. Il database RAG della singola revisione resta separato e locale al progetto.

---

## 🛠 Skill principali

### Revisione PRISMA in sei fasi

| Fase | Automazione | Gate umano |
|---|---|---|
| **1. Identificazione** | query multi-database tramite MCP | conferma delle stringhe |
| **2. Deduplicazione** | normalizzazione DOI e confronto titoli | verifica dei casi dubbi |
| **3. Screening** | classificazione titolo/abstract sui criteri PICO | convalida delle esclusioni |
| **4. Eligibility** | estrazione PDF e checklist full text | decisione sui borderline |
| **5. Qualità** | rubriche rischio di bias Campbell/Cochrane | punteggi finali |
| **6. Estrazione** | matrice di studio, campione, outcome ed effect size | verifica dei dati |

| Skill | Responsabilità | Output |
|---|---|---|
| `prisma-review` | PICO, ricerca, dedup, screening, eligibility, qualità, estrazione | export eligibility, log e tabelle |
| `hybrid-rag` | retrieval dense + BM25, fusione RRF e filtri | evidenze recuperate con origine |
| `educational-pilot-design` | protocollo, potenza, strumenti, etica e analisi | protocollo/preprint |
| `pandoc-export` | conversione Markdown in Word | documento `.docx` |
| `pipeline-ricerca` | coordinamento degli handoff e dei gate | stato end-to-end coerente |
| `wiki-core` / `wiki-setup` | memoria, ingest, query, lint e setup | Markdown + indice Qdrant |

### Vincolo di inclusione

`index-prisma` accetta soltanto:

- `eligibility_prisma.json` o `extraction_table.json`;
- `prisma_state.json` con `fase4.paper_inclusi`;
- record marcati esplicitamente `included: true`.

Un file di screening privo del nome, della struttura o dei marker previsti viene rifiutato; qualsiasi marker esplicito di esclusione causa errore. La conferma umana è il gate obbligatorio che precede la produzione dell'export. Se un paper scompare dall'export corrente, la reindicizzazione lo elimina dal database.

---

## 🧠 Memoria wiki

La wiki conserva conoscenza leggibile in Markdown e la indicizza nello stesso momento in Qdrant.

```text
<W>/
├── wiki.config.json
├── wiki/                      # conoscenza trasversale distillata
│   ├── concepts/  ├── synthesis/  └── identity/
├── wiki-works/<progetto>/     # conoscenza specifica della ricerca
│   ├── raw/  ├── entities/  ├── concepts/  └── synthesis/
└── memory/qdrant/             # indice locale ricostruibile
```

### Retrieval wiki

1. BGE-M3 produce l'embedding della query.
2. Qdrant recupera un insieme più ampio di candidati.
3. Esclusioni configurate e duplicati di pagina vengono rimossi.
4. `BAAI/bge-reranker-v2-m3` riordina i chunk completi.
5. Se il reranker non è disponibile, resta valido l'ordine vettoriale.

I modelli usano CUDA quando PyTorch e driver la espongono; la CPU resta un fallback valido ma più lento. Guida operativa: [wiki/README.it.md](wiki/README.it.md).

---

## 🌐 Server MCP accademici

| Server | Copertura | Utilizzo |
|---|---|---|
| **ERIC** | ricerca educativa | pedagogia, curriculum e outcome |
| **OpenAIRE** | ricerca europea e Horizon | progetti finanziati e open access |
| **CORE** | full text open access | reperimento del testo |
| **DOAJ** | riviste open access | verifica della sede editoriale |
| **Zenodo** | preprint, dataset, deliverable | letteratura grigia e dati |
| **Semantic Scholar** | grafo citazionale | studi correlati |

Gli strumenti mantengono il formato testuale e supportano `output_format="json"` per record completi e paginazione. Il vincolo `mcp>=1,<2` preserva la compatibilità con FastMCP 1.x.

---

## 🔬 Approfondimento tecnico

Le skill installate contengono ruolo, protocollo di fase, schema di output e gate qualitativi. Claude Code le scopre dalla directory `skills/` del plugin; i sei server MCP sono dichiarati direttamente nel manifest, quindi non servono registrazioni manuali con `claude mcp add`.

Esempio semplificato dello stato di screening:

```json
{
  "phase": "screening",
  "research_question": "...",
  "pico": {"P": "...", "I": "...", "C": "...", "O": "..."},
  "wiki_workspace": "/percorso/wiki",
  "included": [{"doi": "...", "title": "...", "rationale": "..."}],
  "excluded": [{"doi": "...", "reason": "criterio_3"}],
  "pending_human_review": ["doi:..."]
}
```

L'export accademico corrente è intenzionalmente semplice:

```text
synthesis.md → Pandoc 3.x → output.docx
                              └─ reference.docx opzionale
```

PDF, LaTeX e stile CSL automatico non fanno parte della skill attuale.

---

## 🚀 Avvio rapido

### 1. Installa

```text
/plugin marketplace add giovannifrontera/academic-research-prisma-wiki-rag
/plugin install academic-research-prisma-wiki-rag@academic-research-prisma
```

Per sviluppo locale: clona il repository e avvia `claude --plugin-dir .` dalla sua directory.

### 2. Ambiente Python

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
python -m pip install -r "<PLUGIN_ROOT>/requirements.txt"
```

Avvia Claude dallo stesso terminale: i server MCP invocano `python` dal `PATH`.

### 3. Configura e avvia

Le variabili opzionali sono `CORE_API_KEY` e `SEMANTIC_SCHOLAR_API_KEY`. Copia `wiki/wiki.config.json` nel workspace dati `<W>` e modifica progetto, keyword e percorsi. Poi invoca:

```text
/prisma-review "Qual è l'effetto della spaced repetition sulla ritenzione a lungo termine nell'istruzione superiore?"
```

### 4. Verifica

```bash
python "<PLUGIN_ROOT>/wiki/scripts/wiki_check_setup.py" --workspace "<W>"
python "<PLUGIN_ROOT>/wiki/scripts/check_models.py" --workspace "<W>"
python "<PLUGIN_ROOT>/wiki/scripts/check_models.py" --workspace "<W>" --require-cuda
```

L'ultimo comando fallisce intenzionalmente se embedding o reranker restano su CPU.

---

## ⚙️ Operatività e risoluzione dei problemi

| Sintomo | Verifica | Soluzione |
|---|---|---|
| Modelli su CPU | `torch.cuda.is_available()` e `torch.version.cuda` | Installa il wheel PyTorch indicato dal configuratore ufficiale e riavvia Claude |
| Import MCP fallito | `python -c "import sys; print(sys.executable)"` | Usa lo stesso virtualenv per installazione e processo Claude |
| Su Windows funziona `py` ma non il plugin | `where python` | Il plugin usa `python`: porta `Scripts` del virtualenv in testa al `PATH` |
| Paper esclusi ancora presenti | `hybrid_rag_template.py status` | Reindicizza l'export eligibility corrente |
| Modello offline non trovato | cache Hugging Face | Scarica i pesi una volta online o usa una cache popolata |
| Qdrant locale bloccato | processi sul workspace | Usa un solo writer per directory Qdrant |

La CI esegue i test su Windows e Ubuntu con Python 3.11 e PyTorch CPU. La GPU viene verificata separatamente su hardware CUDA reale.

---

## 🔐 Confini dei dati e sicurezza

- Codice plugin, workspace wiki e directory della revisione sono separati.
- `memory/qdrant/`, `rag_db/`, PDF, tabelle e credenziali non devono essere committati.
- L'endpoint di contesto accetta solo chiamate loopback.
- Le chiavi API sono lette dall'ambiente.
- Il retrieval non sostituisce il log metodologico o la conferma umana dell'eligibility.
- Usa path assoluti e tra virgolette, soprattutto su Windows.

---

## 📚 Documentazione

| Documento | Contenuto |
|---|---|
| [README English](README.md) | Edizione inglese completa |
| [Guida wiki IT](wiki/README.it.md) / [EN](wiki/README.md) | CLI, server, Qdrant e recovery |
| [Setup modelli](docs/models-and-setup.md) | virtualenv Windows/Linux, CUDA e path |
| [Specifica progetto](docs/PROJECT-SPEC.md) | contratti canonici della pipeline |
| [Manifest plugin](.claude-plugin/plugin.json) | skill e server MCP |

---

## 📦 Release 1.2.0

- Memoria wiki Qdrant embedded e reranking BGE.
- Retrieval Hybrid RAG, filtri, BM25/RRF e vincolo eligibility corretti.
- Output JSON completi per MCP, mantenendo il testo.
- Diagnostica GPU reale e fallback CPU esplicito.
- Compatibilità Windows/Linux per locking, path, ambiente e CI.
- Documentazione italiana e inglese riallineata al plugin Claude Code.

Vedi [CHANGELOG.md](CHANGELOG.md) per la cronologia completa.

---

## 🌐 Ecosistema AI-Wiki

| Progetto | Ruolo |
|---|---|
| [ai-wiki-graph-RAG-lms](https://github.com/giovannifrontera/ai-wiki-graph-RAG-lms) | backend LTI 1.3 per LMS |
| [ai-longterm-wiki-memory-ClaudeCode](https://github.com/giovannifrontera/ai-longterm-wiki-memory-ClaudeCode) | integrazione wiki nativa per Claude Code |
| [ai-longterm-wiki-memory-OpenClaw](https://github.com/giovannifrontera/ai-longterm-wiki-memory-OpenClaw) | memoria wiki per OpenClaw |
| [academic-PRISMA-research-workflow](https://github.com/giovannifrontera/academic-PRISMA-research-workflow) | workflow PRISMA di base archiviato |
| **academic-research-prisma-wiki-rag** | pipeline completa con memoria persistente |

## 📚 Riferimenti essenziali

1. Page, M. J., et al. (2021). PRISMA 2020. *BMJ*, 372, n71.
2. Hattie, J. (2009). *Visible Learning*. Routledge.
3. Campbell Collaboration. (2023). *Systematic reviews in social science and education*.
4. Nosek, B. A., et al. (2015). Promoting an open research culture. *Science*, 348(6242), 1422–1425.
5. Gough, D., Oliver, S., & Thomas, J. (2017). *An Introduction to Systematic Reviews*. SAGE.

---

<div align="center">

*Sviluppato da [Giovanni Frontera, Ph.D.](https://github.com/giovannifrontera) · Parte dell'ecosistema AI-Wiki*

</div>
