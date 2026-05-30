---
name: hybrid-rag
description: Use when creating, updating, or querying a local Hybrid RAG database from PRISMA JSON metadata or PDF documents in a folder. Triggered by prisma-review (after Fase 4) or educational-pilot-design (to query evidence). Hybrid RAG combines dense vector search (sentence-transformers) and sparse retrieval — native FTS via LanceDB (recommended) or BM25 — fused with Reciprocal Rank Fusion. Results are displayed as Markdown.
---

# Hybrid RAG — Ricerche Accademiche

## Overview

Gestisce un database RAG locale che combina **ricerca densa** (sentence-transformers) e **ricerca sparsa** (FTS nativa su LanceDB, oppure BM25 su ChromaDB/Qdrant) con **Reciprocal Rank Fusion (RRF)**. Supporta due fonti di documenti:

- **PRISMA JSON** — metadati strutturati estratti dalla skill `prisma-review`
- **PDF manuali** — documenti PDF in una cartella fornita dall'utente

Il DB è **per-progetto**: vive in `rag_db/` nella cartella di lavoro corrente.

---

## Setup iniziale (prima volta per ogni progetto)

1. Verifica se `hybrid_rag.py` esiste nella cartella di lavoro corrente.
2. Se non esiste → usare il tool **Read** su `~/.claude/skills/hybrid-rag/hybrid_rag_template.py`, poi il tool **Write** per creare `./hybrid_rag.py` con lo stesso contenuto. Questo è il passaggio che genera lo script nella cartella del progetto — l'utente non può eseguirlo prima di questo momento.
3. **Per nuovi progetti: scegli il backend prima di `init`** (INC-4):
   ```bash
   py hybrid_rag.py choose-backend --backend lancedb   # raccomandato
   ```
4. Esegui: `py hybrid_rag.py init`
   - Installa automaticamente le dipendenze Python in base al backend scelto:
     - `lancedb` → `sentence-transformers`, `pymupdf`, `lancedb` (no rank-bm25)
     - `chromadb` → `sentence-transformers`, `rank-bm25`, `pymupdf`, `chromadb`
     - `qdrant` → `sentence-transformers`, `rank-bm25`, `pymupdf`, `qdrant-client`
   - Crea la cartella `rag_db/` nella directory di lavoro corrente.
   - Il DB è locale al progetto: ogni review ha il suo.

**Il DB è idempotente:** `init` e `index-prisma` usano `upsert` — è sempre sicuro rieseguirli. Per svuotare il DB da zero: `rm -rf rag_db/` poi `py hybrid_rag.py init`.

---

## Operazioni

| Operazione | Quando usarla | Comando |
|---|---|---|
| `init` | Prima volta nel progetto | `py hybrid_rag.py init` |
| `choose-backend` | Per scegliere ChromaDB o Qdrant | `py hybrid_rag.py choose-backend` |
| `choose-model` | Prima di indicizzare — scelta modello embedding | `py hybrid_rag.py choose-model --n-papers N` |
| `index-prisma` | Dopo Fase 4 di prisma-review | `py hybrid_rag.py index-prisma <file.json>` |
| `index-pdf` | Quando l'utente fornisce una cartella PDF | `py hybrid_rag.py index-pdf <cartella>` |
| `query` | Per cercare evidenze (da qualsiasi skill) | `py hybrid_rag.py query "<testo>" --n 5` |
| `status` | Per verificare contenuto DB, modello e backend | `py hybrid_rag.py status` |

### choose-model — selezione modello con stime hardware

> ⚠️ **Claude Code non supporta prompt interattivi.** I comandi `choose-model` e `choose-backend` senza argomenti usano `input()` e si bloccano. Usa **sempre** i flag diretti:
> ```bash
> py hybrid_rag.py choose-model --model minilm
> py hybrid_rag.py choose-backend --backend chromadb
> ```

```bash
py hybrid_rag.py choose-model --n-papers 50    # mostra tabella + stime per 50 paper
py hybrid_rag.py choose-model --model e5-large # imposta direttamente senza prompt
```

Modelli disponibili (chiavi):
- `minilm` — `paraphrase-multilingual-MiniLM-L12-v2` (default, 400 MB, ~0.08s/paper)
- `e5-large` — `intfloat/multilingual-e5-large` (1.2 GB, ~0.45s/paper, ottima qualità)
- `bge-m3` — `BAAI/bge-m3` (2.3 GB, ~1.1s/paper, eccellente qualità)

I prefissi `query: ` / `passage: ` per `e5-large` sono gestiti automaticamente.

**Raccomandazione per corpus PRISMA tipici:**
| N paper inclusi | Modello consigliato | Motivazione |
|---|---|---|
| < 30 | `minilm` | Velocità > qualità a questo volume |
| 30–150 | `e5-large` | Miglior bilanciamento qualità/velocità |
| > 150 | `bge-m3` | Qualità massima; tempo accettabile |

**Attenzione:** cambiare modello dopo l'indicizzazione richiede di re-indicizzare (`rm -rf rag_db/` → `init` → `index-*`). Il sistema avverte se rileva incompatibilità.

### choose-backend — selezione backend vettoriale

```bash
py hybrid_rag.py choose-backend --backend lancedb   # raccomandato
py hybrid_rag.py choose-backend --backend chromadb
py hybrid_rag.py choose-backend --backend qdrant
```

| Backend | Quando usarlo |
|---|---|
| `lancedb` **(raccomandato)** | FTS nativa (tantivy) sostituisce BM25. Stessa libreria del wiki system. Filtri SQL su qualsiasi campo. |
| `chromadb` (default storico) | Uso legacy, zero config. BM25 manuale via rank-bm25. |
| `qdrant` | Corpus > 200 paper, HNSW ottimizzato. Richiede qdrant-client. |

**Filtri su metadati** — disponibili con backend LanceDB e Qdrant:
```bash
py hybrid_rag.py query "SRL chatbot" --filter "year>=2020"
py hybrid_rag.py query "metacognition" --filter "year>=2019,source_db=eric"
py hybrid_rag.py query "AI tutor" --filter "source_db=prisma_json"
```

Operatori supportati: `>=`, `<=`, `=` su qualsiasi campo metadato (`year`, `source_db`, `doi`, ecc.).

**Attenzione:** cambiare backend dopo l'indicizzazione richiede di re-indicizzare (stessi step del cambio modello).

### Varianti query

```bash
py hybrid_rag.py query "chatbot self-regulated learning" --n 5          # tutte le fonti
py hybrid_rag.py query "chatbot metacognizione" --only-prisma            # solo PRISMA JSON
py hybrid_rag.py query "istruzioni ministeriali AI" --only-pdf           # solo PDF manuali
```

**Lingua delle query:** l'embedding multilingue gestisce italiano e inglese. Il **dense retrieval** è robusto in entrambe le lingue. Il **BM25** è lessicale: per paper in inglese, query in inglese migliorano la copertura BM25. Strategia consigliata: usa la lingua dei documenti target (inglese per PRISMA, italiano per PDF ministeriali/normativi).

### File JSON accettati da `index-prisma`

Accetta qualsiasi di questi formati prodotti da `prisma-review`:
- `screening_prisma.json` — lista di paper dopo Fase 2
- `eligibility_prisma.json` — paper dopo Fase 3
- `prisma_state.json` — struttura completa (legge `fase4.paper_inclusi`)
- Qualsiasi lista JSON di oggetti con campi `title/titolo`, `abstract`, `doi`, ecc.

---

## Integrazione con altre skill

> Tutte le skill si invocano tramite il tool **`Skill`** di Claude Code. Per il flusso completo tra le skill, consulta la skill **`pipeline-ricerca`**.

### Da prisma-review (sostituisce build_rag_db.py e query_rag.py)

Alla **fine della Fase 4**, invece di generare `build_rag_db.py`:
```bash
py hybrid_rag.py init                                    # se prima volta
py hybrid_rag.py index-prisma eligibility_prisma.json   # paper inclusi dopo Fase 3
# oppure: index-prisma prisma_state.json  (legge fase4.paper_inclusi)
```

In **Fase 6**, per ogni sezione del report, invece di `query_rag.py`:
```bash
py hybrid_rag.py query "self-regulated learning effect size chatbot" --n 5
```

Se l'utente ha PDF manuali da aggiungere, chiedi:
> "Hai documenti PDF aggiuntivi da includere nel RAG (es. paper scaricati manualmente, linee guida, documenti ministeriali)? Se sì, indicami il percorso della cartella."

### Da educational-pilot-design

In qualsiasi fase, per recuperare evidenze dalla letteratura:
```bash
py hybrid_rag.py query "<domanda di ricerca o costrutto>" --n 5
```

Mostra i risultati in MD nella conversazione. Non scrivere file di output separati.

---

## Formato output query (Markdown)

L'output della query viene stampato come Markdown e mostrato direttamente in conversazione:

```markdown
## Risultati RAG — Query: `chatbot self-regulated learning`
*5 risultati, Hybrid RAG (Dense + BM25 + RRF)*

### [1] Smith et al. (2022) — Effects of chatbots on SRL
**Score RRF:** 0.0312 | **Dense:** 0.891
**DOI:** 10.1016/j.compedu.2022.104423
**Fonte:** PRISMA JSON

> ABSTRACT: This study examined... EFFECT SIZE: d=0.61...

---

### [2] documento.pdf (chunk 3/8)
**Score RRF:** 0.0287 | **Dense:** 0.743
**Fonte:** PDF manuale

> Il testo estratto dal chunk...

---
```

---

## Note tecniche

**Stack:**
- **LanceDB** (raccomandato) — columnar Arrow format, FTS nativa (tantivy), filtri SQL, stessa libreria del wiki system — `rag_db/`
- **ChromaDB** (legacy default) — persistente, locale — `rag_db/`; usa `rank-bm25` per sparse retrieval
- **Qdrant** (opzionale) — HNSW ottimizzato, filtri nativi su metadati — richiede `qdrant-client`
- `sentence-transformers` — modello selezionabile via `choose-model` (comune a tutti i backend)
- `pymupdf` (fitz) — estrazione testo PDF
- RRF con k=60 — applicato su dense + FTS/BM25

**Config:** `rag_db/config.json` — persiste la scelta del modello, del backend, e tiene traccia di quale modello ha generato gli embedding nel DB.

**Collezioni (entrambi i backend):**
- `prisma_papers` — paper indicizzati da PRISMA JSON
- `pdf_manual` — chunk da PDF manuali

**Dipendenze:** installate automaticamente da `init` in base al backend scelto
```
sentence-transformers, pymupdf          (comuni a tutti i backend)
+ lancedb                               (backend=lancedb, raccomandato — no rank-bm25)
+ chromadb, rank-bm25                   (backend=chromadb, legacy default)
+ qdrant-client, rank-bm25              (backend=qdrant, opzionale)
```

**Chunking PDF:** ~800 caratteri per chunk, chunk < 50 caratteri scartati automaticamente.

**BM25:** ricalcolato in memoria a ogni query (adeguato per corpora < 500 documenti).

**Preview output query:** il testo mostrato in conversazione è troncato a 800 caratteri per risultato. Il documento completo è nel DB — se serve il testo integrale, usa `--n 3` (meno risultati, più leggibili) o interroga direttamente il file JSON di origine.

**Corpus minimo consigliato:** con meno di 10-15 paper indicizzati il RAG non aggiunge valore significativo rispetto a leggere i file direttamente. Sotto questa soglia, preferisci leggere `eligibility_prisma.json` via Read tool.

**Qdrant — note specifiche:**
- IDs: stringa → UUID deterministico via `uuid5(NAMESPACE_DNS, str_id)`; l'ID originale è salvato nel payload come `_doc_id`
- Il campo `year` è salvato come `int` per abilitare i filtri range (`year>=2020`)
- Filtri disponibili con backend LanceDB e Qdrant: `--filter 'year>=2020,source_db=eric'`
- `get_all()` usa `scroll` con limite hardcoded a 10.000: con corpus PDF molto estesi (centinaia di documenti lunghi, migliaia di chunk) i risultati BM25 possono essere incompleti. Per corpora così grandi preferisci Qdrant + filtri invece di BM25 puro.

**Portabilità path:** i comandi `init` e setup usano path relativi (`rag_db/`) e funzionano su qualsiasi sistema. Il path assoluto `C:/Users/<username>/...` appare solo nelle istruzioni di installazione della skill — su Windows: C:/Users/<username>/.claude/skills/.
