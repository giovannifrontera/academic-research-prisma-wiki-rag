---
name: hybrid-rag
description: Create and query a per-review hybrid RAG index of included PRISMA evidence. Uses dense sentence-transformers retrieval plus BM25 (Qdrant/ChromaDB) or native FTS (LanceDB), fused with Reciprocal Rank Fusion.
---

# Hybrid RAG — Ricerche Accademiche

Risolvi `<PLUGIN_ROOT>` dalla posizione di questa skill installata: `hybrid_rag_template.py` è accanto a questo file. Esegui il template direttamente con path assoluto; non serve copiarlo nella review. Sostituisci i segnaposto mantenendo le virgolette. Usa `python` dal venv attivo in Windows/Linux; vedi [setup e modelli](../../docs/models-and-setup.md).

## Setup

Lavora dalla directory dati della review: `rag_db/` dipende dalla directory corrente. Per un nuovo indice Qdrant + BGE:

```text
python "<PLUGIN_ROOT>/skills/hybrid-rag/hybrid_rag_template.py" choose-backend --backend qdrant
python "<PLUGIN_ROOT>/skills/hybrid-rag/hybrid_rag_template.py" choose-model --model bge-m3
python "<PLUGIN_ROOT>/skills/hybrid-rag/hybrid_rag_template.py" init
```

Qdrant è il backend predefinito; MiniLM resta il modello predefinito se non chiami `choose-model`. Modelli disponibili: `minilm`, `e5-large`, `bge-m3`. I prefissi E5 sono gestiti dal codice. Non scegliere il modello in base a soglie arbitrarie di numero di paper: valuta lingua, memoria e latenza. Per selezioni automatiche usa sempre i flag diretti: senza `--model` / `--backend` i comandi possono chiedere input interattivo.

`init` installa eventuali dipendenze mancanti nello stesso interprete: sentence-transformers, PyMuPDF e quelle del backend. Per Qdrant servono qdrant-client e rank-bm25. ChromaDB e LanceDB sono alternative opzionali, non componenti della wiki. La wiki usa un indice distinto Qdrant + BGE-M3 + reranker; il RAG locale usa RRF e non eredita il reranker.

## Corpus ammesso

Per la sintesi PRISMA indicizza **solo gli studi inclusi dopo eligibility umana**:

- `eligibility_prisma.json` (o una tabella di estrazione con soli inclusi), con abstract e dati estratti verificati.
- `pdf_inclusi/`: solo PDF associati a quegli studi. Nel log eligibility registra file, DOI/ID, decisione, motivazione, revisore e data prima dell'indicizzazione.

`pdf_manuali/` è una inbox di identificazione, non un corpus incluso. Non indicizzarla in blocco. Non usare `screening_prisma.json` come fallback: contiene candidati ed esclusi. Se manca l'elenco finale, completa eligibility prima di creare il RAG. Il parser accetta anche liste JSON generiche e `prisma_state.json`, ma questa compatibilità non certifica l'inclusione e lo stato può mancare di abstract.

Linee guida, documenti ministeriali e altri materiali di contesto vanno in una directory dati e un indice separati. Non citarli come evidenza inclusa né contarli nei risultati PRISMA. `--only-pdf` distingue il formato, non l'eleggibilità.

## Comandi

```text
python "<PLUGIN_ROOT>/skills/hybrid-rag/hybrid_rag_template.py" index-prisma "eligibility_prisma.json"
python "<PLUGIN_ROOT>/skills/hybrid-rag/hybrid_rag_template.py" index-pdf "pdf_inclusi/"
python "<PLUGIN_ROOT>/skills/hybrid-rag/hybrid_rag_template.py" status
python "<PLUGIN_ROOT>/skills/hybrid-rag/hybrid_rag_template.py" query "self-regulated learning effect size" --n 5
python "<PLUGIN_ROOT>/skills/hybrid-rag/hybrid_rag_template.py" query "metacognition" --only-prisma
python "<PLUGIN_ROOT>/skills/hybrid-rag/hybrid_rag_template.py" query "intervention outcomes" --only-pdf
python "<PLUGIN_ROOT>/skills/hybrid-rag/hybrid_rag_template.py" query "AI tutor" --filter "year>=2020,source_db=eric"
```

Filtri `>=`, `<=`, `=` disponibili con Qdrant e LanceDB. BM25 è lessicale: usa preferibilmente la lingua dei documenti. L'output Markdown mostra estratti troncati; verifica citazioni e risultati nel documento originale, non solo nello snippet.

L'indicizzazione usa upsert, ma non elimina automaticamente record ritirati dal corpus. Se cambiano inclusioni, modello o backend, conserva una copia del vecchio indice e ricostruisci un indice vuoto dal corpus approvato; verifica lo stato prima della sintesi. Non cancellare directory senza identificare il percorso dati esatto.

## Handoff

Invoca da `prisma-review` dopo l'inclusione; interroga durante il report e `educational-pilot-design`. La provenienza umana nel log, non il semplice recupero RAG, stabilisce quali studi sono evidenza inclusa. Per corpora piccoli la lettura diretta dei documenti può bastare se concordata nel workflow.
