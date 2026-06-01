# Pipeline Ricerca Accademica — Specifica Completa di Progetto

**Data:** 2026-06-02  
**Versione:** 1.0 — documento unificato  
**Stato:** In lavorazione  

> Questo documento è la fonte di verità unica per l'intero sistema. Sostituisce i file in `docs/superpowers/specs/` per le decisioni architetturali. I piani di implementazione task-by-task rimangono separati in `docs/superpowers/plans/`.

---

## INDICE

1. [Visione e Principi](#1-visione-e-principi)
2. [Architettura del Sistema](#2-architettura-del-sistema)
3. [Spazio di Progetto](#3-spazio-di-progetto)
4. [Sistemi di Memoria](#4-sistemi-di-memoria)
5. [Skill: pipeline-regista](#5-skill-pipeline-regista)
6. [Skill: prisma-review](#6-skill-prisma-review)
7. [Skill: hybrid-rag](#7-skill-hybrid-rag)
8. [Skill: research-design](#8-skill-research-design)
9. [Skill: data-collection](#9-skill-data-collection)
10. [Skill: data-analysis](#10-skill-data-analysis)
11. [Skill: preprint](#11-skill-preprint)
12. [MCP Server](#12-mcp-server)
13. [Problemi Critici e Correzioni](#13-problemi-critici-e-correzioni)
14. [Roadmap di Implementazione](#14-roadmap-di-implementazione)

---

## 1. Visione e Principi

### 1.1 Obiettivo

Un sistema di skill coordinate che guida un ricercatore in scienze dell'educazione dall'identificazione delle domande di ricerca fino alla pubblicazione del preprint — senza mai perdere il filo, anche su sessioni separate distanziate di settimane.

### 1.2 Principi Non Negoziabili

1. **Zero perdita di dati tra sessioni.** Ogni skill aggiorna il proprio state file al termine di ogni interazione significativa, anche se interrotta. Tutti i write su state file usano il pattern atomico (scrivi in `.tmp`, poi `os.replace()`).

2. **Autonomia dello spazio di progetto.** Tutto il materiale di ricerca vive nella cartella di progetto `{project-root}/`. I path (project_root, wiki_workspace, repo_path) sono configurabili e registrati in `.project-state.json` — nessun path hardcoded nel codice delle skill.

3. **Regista come unico punto di ingresso.** Il ricercatore invoca sempre `pipeline-regista`. Le skill individuali possono essere invocate direttamente per uso avanzato, ma il flusso normale passa dal regista.

4. **Tracciabilità completa.** `project-log.md` documenta ogni decisione rilevante con timestamp, skill responsabile e rationale. È append-only — mai cancellare entry.

5. **Adattamento al paradigma.** Ogni skill che dipende dalla scelta metodologica legge `paradigm` da `.project-state.json` e adatta il comportamento senza chiedere di nuovo.

6. **Guardrail anti-allucinazione.** Nessuna skill cita letteratura senza fonte RAG verificata. Tutte le citazioni non recuperate via `hybrid_rag.py query` vanno marchiate `[CITARE: autore/anno da verificare]`. Il RAG viene costruito esclusivamente da `eligibility_prisma.json` (paper inclusi) — mai da `screening_prisma.json`.

7. **Output MCP in JSON strutturato.** Tutti i server MCP restituiscono JSON, non testo Markdown. L'abstract non viene troncato nel dato grezzo — solo nella presentazione conversazionale.

8. **Write atomico per tutti i state file.**
```python
import json, tempfile, os
def write_state(path: str, data: dict) -> None:
    dir_ = os.path.dirname(os.path.abspath(path))
    with tempfile.NamedTemporaryFile('w', dir=dir_, delete=False,
                                     suffix='.tmp', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        tmp = f.name
    os.replace(tmp, path)  # atomico su POSIX; near-atomico su Windows
```

---

## 2. Architettura del Sistema

```
┌─────────────────────────────────────────────────────────────────┐
│                    pipeline-regista                             │
│  skill orchestratrice interattiva — porta d'ingresso unica      │
│  legge .project-state.json — sa sempre dove si è arrivati       │
└────────────────────────┬────────────────────────────────────────┘
                         │ coordina
                         ▼

[MCP Servers bibliografici]
    Esistenti:  CORE · DOAJ · ERIC · OpenAIRE · Zenodo
    Mancanti:   Semantic Scholar · PubMed · arXiv
         ↓
[prisma-review]
    PICO + RQ + ipotesi
    Identificazione (8 database) → Screening → Eligibilità
    Sintesi sistematica + export wiki + build RAG
         ↓
    ┌────────────────────────────┐
    │  Wiki (LanceDB bge-m3)     │ ← memoria cross-progetto permanente
    │  wiki-works/{proj}/        │   entity page per ogni paper incluso
    │  entities/ + synthesis/    │   sintesi tematica
    └────────────────────────────┘
    ┌────────────────────────────┐
    │  hybrid-rag (rag_db/)      │ ← memoria locale al progetto
    │  chunks paper indicizzati  │   usato solo per citazioni nel preprint
    └────────────────────────────┘
         ↓
[research-design]
    Fase 0: scelta paradigma (decision tree 6 domande)
    Fase 1-6: framework → design → strumenti → procedura
              → piano analisi → preprint bozza
    Output: design/fase-5-analisi/piano-analisi.json
         ↓
[data-collection]
    Adattato al paradigma scelto
    Quantitativo: codebook + matrice CSV
    Qualitativo: trascrizioni + atlas codici + memo
    Mixed: entrambi in parallelo
    AR/DBR: journal di campo + documentazione cicli
         ↓
[data-analysis]
    Legge piano-analisi.json + domande di conferma obbligatorie
    Guida analisi per paradigma + indicatori appropriati
    Output: analisi/risultati_*.md + piano-analisi-confermato.json
         ↓
[preprint]
    Template: paradigma × piattaforma target
    Piattaforme: arXiv / Zenodo / Open Research Europe / SSRN / EdArXiv / PsyArXiv
    Reporting standard: CONSORT / STROBE / COREQ / SRQR / SQUIRE
    Output: preprint/preprint_bozza.md + submission_checklist.md
         ↓
[pandoc-export]
    Conversione Word / PDF
```

### 2.1 Skill Esistenti vs Da Creare

| Skill | Stato | Note |
|-------|-------|------|
| `prisma-review` | ✅ Esistente | Necessita correzioni (vedi §13) |
| `hybrid-rag` | ✅ Esistente | Necessita correzioni minori |
| `educational-pilot-design` | ⚠️ Deprecata | Sostituita da `research-design` |
| `pandoc-export` | ✅ Esistente | Nessuna modifica necessaria |
| `pipeline-ricerca` | ⚠️ Deprecata | Sostituita da `pipeline-regista` |
| `wiki-core` | ✅ Esistente (doc ref) | Nessuna modifica necessaria |
| `pipeline-regista` | ❌ Da creare | Priorità A |
| `research-design` | 🚧 In corso | MVP: Fase 0 + MOD-QN1 |
| `data-collection` | ❌ Da creare | Priorità C |
| `data-analysis` | ❌ Da creare | Priorità C |
| `preprint` | ❌ Da creare | Priorità C |

---

## 3. Spazio di Progetto

### 3.1 Layout {project-root}/

> **DECISIONE ARCHITETTURALE:** `prisma-review` scrive i propri file nella cartella di lavoro corrente (flat layout). Per non rompere una skill esistente e funzionante, il `{project-root}/` adotta il flat layout per i file PRISMA. Le nuove skill scrivono in sottocartelle dedicate.

```
{project-root}/                          ← CWD del ricercatore durante tutta la ricerca
│
├── .project-state.json                  ← MASTER STATE (vedi §3.2)
├── project-log.md                       ← AUDIT LOG append-only
│
│── prisma_state.json                    ← prisma-review (flat, invariato)
├── prisma_log.md
├── raw_semantic_scholar.json            ← risultati grezzi MCP, uno per database
├── raw_pubmed.json
├── raw_arxiv.json
├── raw_eric.json
├── raw_openaire.json
├── raw_core.json
├── raw_doaj.json
├── raw_zenodo.json
├── raw_pdf_manual.json                  ← Stream 2 PRISMA 2020 (PDF manuali)
├── pdf_manuali/                         ← PDF da indicizzare manualmente
├── prisma_screening.py                  ← script deduplicazione (da creare — C1)
├── screening_prisma.json                ← paper dopo deduplicazione (NON usare nel RAG)
├── eligibility_prisma.json              ← paper INCLUSI — unica fonte per RAG
├── prisma_synthesis.md                  ← sintesi + OUTPUT PER PILOT STUDY
├── prisma_bibliography.md
├── hybrid_rag.py                        ← copiato da template (vedi §7.3)
├── rag_db/                              ← indice RAG locale (solo eligibility_prisma)
│
├── design/                              ← research-design
│   ├── .research-state.json
│   ├── protocollo_ricerca.md
│   ├── strumenti_valutazione.md
│   ├── timeline_pilota.md
│   └── fase-5-analisi/
│       └── piano-analisi.json           ← handoff → data-analysis (validato con schema)
│
├── raccolta-dati/                       ← data-collection
│   ├── .collection-state.json
│   ├── codebook.md                      ← quantitativo / mixed
│   ├── matrice_dati.csv                 ← quantitativo / mixed (CSV, non XLSX)
│   ├── trascrizioni/                    ← qualitativo / mixed
│   │   └── INT-001.md, INT-002.md ...
│   ├── atlas_codici.md                  ← qualitativo / mixed
│   └── memo_analitico.md               ← qualitativo
│
├── analisi/                             ← data-analysis
│   ├── .analysis-state.json
│   ├── piano-analisi-confermato.json
│   ├── risultati_quantitativi.md
│   ├── risultati_qualitativi.md
│   └── integrazione_mm.md              ← solo mixed-methods
│
├── preprint/                            ← preprint skill
│   ├── .preprint-state.json
│   ├── preprint_bozza.md
│   ├── preprint_bozza.docx             ← pandoc-export
│   └── submission_checklist.md
│
└── .gitignore                           ← creato da pipeline-regista all'init (vedi §5.3)
```

### 3.2 Master State File (.project-state.json)

```json
{
  "project_name": "string",
  "project_root": "/path/assoluto/al/progetto",
  "repo_path": "/path/assoluto/a/academic-research-prisma-wiki-rag",
  "wiki_workspace": "/path/assoluto/al/wiki-data",
  "wiki_project_name": "slug-del-progetto",
  "wiki_configured": true,
  "created_at": "ISO8601",
  "researcher": {
    "name": "string",
    "institution": "string",
    "domain": "Ed-Tech | Psicopedagogia | Didattica | Pedagogia | Valutazione | FormDocenti"
  },
  "ethics": {
    "status": "pending | approved | exempt | not_required",
    "committee": "string",
    "protocol_id": "string",
    "approved_at": "ISO8601 | null"
  },
  "current_phase": "prisma | rag | research-design | data-collection | data-analysis | preprint",
  "phases": {
    "prisma": {
      "status": "completed | in_progress | pending | skipped",
      "started_at": "ISO8601 | null",
      "completed_at": "ISO8601 | null",
      "included_papers": 0,
      "rq_count": 0,
      "effect_size_range": "string | null"
    },
    "rag": {
      "status": "completed | pending",
      "backend": "lancedb | chromadb",
      "indexed_papers": 0,
      "completed_at": "ISO8601 | null"
    },
    "wiki": {
      "status": "completed | pending | not_configured",
      "pages_created": 0,
      "completed_at": "ISO8601 | null"
    },
    "research-design": {
      "status": "completed | in_progress | pending",
      "paradigm": "MOD-QN1 | MOD-QN2 | MOD-QN3 | MOD-QN4 | MOD-Q1 | MOD-Q2 | MOD-Q3 | MOD-Q4 | MOD-MM | MOD-AR | MOD-DBR | null",
      "current_internal_phase": 0,
      "started_at": "ISO8601 | null",
      "completed_at": "ISO8601 | null"
    },
    "data-collection": {
      "status": "completed | in_progress | pending",
      "started_at": "ISO8601 | null",
      "completed_at": "ISO8601 | null"
    },
    "data-analysis": {
      "status": "completed | in_progress | pending",
      "started_at": "ISO8601 | null",
      "completed_at": "ISO8601 | null"
    },
    "preprint": {
      "status": "completed | in_progress | pending",
      "platform": "arxiv | zenodo | ore | ssrn | edarxiv | psyarxiv | null",
      "started_at": "ISO8601 | null",
      "completed_at": "ISO8601 | null"
    }
  },
  "last_updated": "ISO8601",
  "last_skill": "string",
  "last_session": "ISO8601"
}
```

### 3.3 Audit Log (project-log.md)

Append-only. Ogni skill aggiunge entry senza mai sovrascrivere.

```markdown
## [ISO8601] pipeline-regista | Progetto inizializzato
**Ricercatore:** Nome | **Istituzione:** Ateneo
**Dominio:** Ed-Tech | **Livello:** Secondaria II

## [ISO8601] prisma-review | Fase 0 completata
**PICO:** P=[studenti sec. II] I=[chatbot AI] C=[didattica tradizionale] O=[motivazione, SRL]
**Database configurati:** Semantic Scholar, PubMed, ERIC, arXiv, CORE, DOAJ, OpenAIRE, Zenodo

## [ISO8601] prisma-review | Fase 4 completata
**Paper inclusi:** 24 | **Esclusi:** 187 | **Effect size medio:** d=0.48 (range 0.2–0.8)

## [ISO8601] hybrid-rag | RAG costruito
**File:** eligibility_prisma.json | **Backend:** lancedb | **Paper indicizzati:** 24

## [ISO8601] wiki | Entity pages ingested
**Pagine create:** 25 (24 entity + 1 synthesis)

## [ISO8601] research-design | Paradigma selezionato
**Paradigma:** MOD-QN1 — Quasi-sperimentale
**Routing:** Q1=misurare, Q2=consolidata, Q3=quantitativo, Q4=no-rand, Q5=cross, Q6=n/a

## [ISO8601] data-collection | Raccolta completata
**N effettivo:** 38 (target: 42) | **Dropout:** 4 (9.5%)
**Go/No-go:** 4/5 criteri soddisfatti — PROCEED
```

---

## 4. Sistemi di Memoria

### 4.1 Due Sistemi Distinti

| | **Wiki** (bge-m3 + LanceDB) | **hybrid-rag** (RRF + LanceDB/ChromaDB) |
|--|--|--|
| Scope | Cross-progetto, permanente | Locale al singolo progetto |
| Workspace | `{wiki_workspace}/` esterno al progetto | `{project-root}/rag_db/` |
| Cosa contiene | Entity pages strutturate + sintesi | Chunks dei paper per retrieval |
| Costruito quando | Dopo PRISMA Fase 4 e Fase 6 | Dopo PRISMA Fase 4 |
| Query | `wiki.py query --workspace W --q "..." --k 5` | `py hybrid_rag.py query "..." --n 3` |
| Usato da | Tutte le skill per conoscenza trasversale | Solo preprint (guardrail anti-allucinazione) |
| Abstract | Completo nella entity page | Chunk 512 token con overlap 64 |

### 4.2 Wiki Workspace Structure

```
{wiki_workspace}/                        ← path in .project-state.json → wiki_workspace
├── wiki.config.json
├── wiki/                                ← conoscenza permanente cross-progetto
│   ├── .schema.md
│   ├── log.md
│   ├── concepts/
│   └── synthesis/
├── wiki-works/
│   └── {wiki_project_name}/            ← attivo per questo progetto
│       ├── .schema.md
│       ├── log.md
│       ├── entities/                   ← una pagina MD per ogni paper incluso
│       ├── concepts/
│       └── synthesis/
└── memory/
    └── lancedb/                        ← indice vettoriale (ricostruibile)
```

### 4.3 Formato Entity Page

```markdown
# [Titolo completo del paper]

**Autori:** Cognome A., Cognome B. | **Anno:** YYYY | **DOI:** [doi o "n/a"]
**Database:** semantic_scholar | pubmed | arxiv | eric | core | doaj | openaire | zenodo
**Outcome principale:** [es. motivazione intrinseca, SRL, risultati scolastici]
**Effect size:** d=[X] | η²=[X] | r=[X] (Hedges' g se n₁≠n₂)
**Framework teorico:** [es. Self-Determination Theory, TPACK]
**Strumenti:** [es. MSLQ, AMS-C28, log interazioni]
**Campione:** N=[X] | Livello: [es. secondaria II] | Paese: [es. Italia]
**Qualità:** [punteggio 0–6 scala quantitativa o CASP qualitativa]
**Tipo studio:** [RCT | quasi-exp | survey | qualitativo | MM]

## Abstract
[Abstract completo — non troncato]

## Note per il progetto
[Rilevanza specifica per questa ricerca, gap identificati, strumenti da riusare]
```

### 4.4 Flusso Wiki: Quando Ogni Skill Scrive e Legge

| Momento | Sistema | Operazione | Comando |
|---------|---------|------------|---------|
| Pre-PRISMA Fase 1 | Wiki | Query conoscenza pre-esistente | `wiki.py query --workspace W --q "PICO topic" --k 5` |
| Post-PRISMA Fase 4 | Wiki | Ingest 24 entity pages | `wiki.py ingest --workspace W --pages "e1.tmp,e2.tmp,..."` |
| Post-PRISMA Fase 4 | hybrid-rag | Indicizza paper (solo eligibility) | `py hybrid_rag.py index-prisma eligibility_prisma.json` |
| Post-PRISMA Fase 6 | Wiki | Ingest synthesis page | `wiki.py ingest --workspace W --pages "synthesis.tmp"` |
| research-design Fase 1 | Wiki | Query framework teorici | `wiki.py query --workspace W --q "framework [dominio]" --k 3` |
| data-collection | Wiki | Query strumenti da letteratura | `wiki.py query --workspace W --q "strumenti [costrutto]" --k 3` |
| data-analysis | Wiki | Query effect size da letteratura | `wiki.py query --workspace W --q "effect size [intervento]" --k 3` |
| preprint ogni sezione | hybrid-rag | Chunks per citazioni | `py hybrid_rag.py query "[costrutto]" --n 3` |

---

## 5. Skill: pipeline-regista

### 5.1 Ruolo

Skill orchestratrice interattiva. Il ricercatore non deve sapere quale skill invocare — il regista determina la prossima azione leggendo `.project-state.json`.

### 5.2 Avvio

```
AVVIO:
  .project-state.json esiste?
  
  NO → Nuovo progetto:
       Chiedi: nome progetto, dominio, livello scolastico, obiettivo generale
       Chiedi: path wiki workspace (o "nessuno per ora")
       Esegui §5.3 (Inizializzazione)
       → Invoca prisma-review
  
  SÌ → Ripresa progetto:
       Leggi .project-state.json + ultime 10 righe project-log.md
       Mostra riepilogo (§5.4)
       Attendi input → Delega alla skill appropriata
```

### 5.3 Inizializzazione Nuovo Progetto

```
1. Crea {project-root}/ e sottocartelle:
   design/ raccolta-dati/ analisi/ preprint/

2. Crea .project-state.json (write atomico) con tutti i campi

3. Crea project-log.md con prima entry

4. Crea .gitignore:
   raccolta-dati/trascrizioni/
   raccolta-dati/matrice_dati.*
   rag_db/
   memory/
   *.tmp
   __pycache__/
   .env

5. Wiki workspace configurato?
   SÌ → Verifica {wiki_workspace}/wiki.config.json
        Crea wiki-works/{wiki_project_name}/ se non esiste
        .project-state.json → wiki.status = "ready"
   NO  → .project-state.json → wiki_configured = false, wiki.status = "not_configured"
        Avvisa: "Wiki non configurata. Le skill funzioneranno senza memoria
                 cross-progetto. Puoi configurarla successivamente con
                 wiki_check_setup.py --workspace /path/scelto"

6. Aggiorna project-log.md con entry inizializzazione

7. Invoca prisma-review
```

### 5.4 Riepilogo Visivo (ripresa)

```
Progetto: [nome] | Ultimo accesso: [data]
Ricercatore: [nome] | Dominio: [dominio] | Livello: [livello]

✅ PRISMA:          24 paper inclusi (completato 2026-05-28)
✅ RAG:             24 paper indicizzati, backend: lancedb
✅ Wiki:            25 pagine, wiki-works/progetto-x/
🔄 Research-design: Fase 3/6 — MOD-QN1 — in corso
⏳ Data-collection: in attesa
⏳ Data-analysis:   in attesa
⏳ Preprint:        in attesa

Comandi: continua | stato | log [N] | vai a [fase] | prossimo passo | esporta
```

### 5.5 Dipendenze tra Fasi

| Fase | Dipendenze obbligatorie | Opzionali |
|------|------------------------|-----------|
| `rag` | `prisma` completata | — |
| `wiki-ingest` | `prisma` completata | — |
| `research-design` | `prisma` completata | `rag` (abilita query locale), `wiki` (abilita query cross-progetto) |
| `data-collection` | `research-design` Fase 5 completata (piano-analisi.json presente) | — |
| `data-analysis` | `data-collection` completata | — |
| `preprint` | `data-analysis` completata | — |

---

## 6. Skill: prisma-review

### 6.1 Stato Attuale

Skill esistente e funzionante (47KB). **Non riscrivere.** Applicare le correzioni puntuali elencate in §13.

### 6.2 Flusso Corretto

```
Fase 0:  Setup PICO + configurazione progetto + wiki pre-query
Fase 1:  Identificazione (8 database MCP) → raw_*.json (JSON strutturato, abstract completo)
Fase 2:  prisma_screening.py → deduplicazione → screening_prisma.json
Fase 3:  Screening titolo/abstract → lista candidati
Fase 4:  Eligibilità full-text → eligibility_prisma.json + quality assessment
         Wiki ingest: entity page per ogni paper incluso
         hybrid-rag: index-prisma eligibility_prisma.json (NON screening)
Fase 5:  hybrid-rag build + wiki synthesis page
Fase 6:  Report generazione (solo da RAG — guardrail)
```

### 6.3 File Prodotti (flat in {project-root}/)

| File | Fase | Contenuto |
|------|------|-----------|
| `prisma_state.json` | 0 | Stato operativo |
| `prisma_log.md` | 0 | Log metodologico |
| `raw_*.json` | 1 | Record grezzi da ogni MCP (JSON strutturato, abstract completo) |
| `prisma_screening.py` | 2 | Script deduplicazione (da creare — C1) |
| `screening_prisma.json` | 2 | Paper dopo deduplicazione — NON usare per RAG |
| `eligibility_prisma.json` | 4 | Paper inclusi — unica fonte per RAG |
| `prisma_synthesis.md` | 4–6 | Sintesi tematica + OUTPUT PER PILOT STUDY |
| `prisma_bibliography.md` | 4 | Schede bibliografiche |

### 6.4 Schema JSON MCP Output (tutti i server)

```json
{
  "results": [
    {
      "title": "string",
      "doi": "string | null",
      "year": 2022,
      "authors": ["Cognome A.", "Cognome B."],
      "abstract": "string completo, NON troncato",
      "source_db": "eric | semantic_scholar | pubmed | arxiv | core | doaj | openaire | zenodo",
      "url": "string",
      "id": "string",
      "journal": "string | null",
      "keywords": ["string"]
    }
  ],
  "total": 150,
  "query": "string",
  "filters_applied": {}
}
```

---

## 7. Skill: hybrid-rag

### 7.1 Stato Attuale

Skill esistente. Correzioni puntuali in §13.

### 7.2 Regola Fondamentale (Guardrail)

```
RAG accetta SOLO eligibility_prisma.json come input.
Se il file non esiste → STOP con messaggio:
"Il RAG non può essere costruito: Fase 4 di prisma-review non completata.
Completare la valutazione di eligibilità prima di procedere."
NON accettare screening_prisma.json come fallback.
```

### 7.3 Deployment hybrid_rag.py

Il file `hybrid_rag.py` (48KB) viene copiato nel `{project-root}/` tramite il comando Write tool dalla sorgente nel repository:

```
{repo_path}/skills/hybrid-rag/hybrid_rag_template.py → {project-root}/hybrid_rag.py
```

Il path `{repo_path}` è registrato in `.project-state.json`. La skill `pipeline-regista` esegue questa copia all'inizializzazione se il file non esiste.

### 7.4 Comandi

```bash
py hybrid_rag.py choose-backend --backend lancedb     # prima di init
py hybrid_rag.py init                                  # crea rag_db/
py hybrid_rag.py index-prisma eligibility_prisma.json # SOLO eligibility
py hybrid_rag.py index-pdf pdf_manuali/               # opzionale: Stream 2
py hybrid_rag.py query "costrutto" --n 3              # retrieval
py hybrid_rag.py query "costrutto" --n 5 --only-prisma
py hybrid_rag.py status
```

---

## 8. Skill: research-design

### 8.1 Paradigmi Supportati

| Codice | Nome | Stato MVP |
|--------|------|-----------|
| MOD-QN1 | Quasi-sperimentale | ✅ Piano scritto |
| MOD-QN2 | RCT | 🚧 Piano 2 |
| MOD-QN3 | Single-Subject Design | 🚧 Piano 2 |
| MOD-QN4 | Survey correlazionale | 🚧 Piano 2 |
| MOD-Q1 | Fenomenologia (IPA) | 🚧 Piano 2 |
| MOD-Q2 | Grounded Theory | 🚧 Piano 2 |
| MOD-Q3 | Etnografia | 🚧 Piano 3 |
| MOD-Q4 | Ricerca Narrativa | 🚧 Piano 3 |
| MOD-MM | Mixed-Methods | 🚧 Piano 2 |
| MOD-AR | Action Research | 🚧 Piano 3 |
| MOD-DBR | Design-Based Research | 🚧 Piano 3 |

### 8.2 Fase 0 — Decision Tree (6 Domande)

> **CORREZIONE rispetto alla spec precedente:** La quinta domanda (Q5) è stata affinata e aggiunta una sesta (Q6) per disambiguare i casi qualitativi. Le righe vanno valutate in ordine top-down: **prima corrispondenza vince.**

| Q | Domanda |
|---|---------|
| Q1 | Obiettivo primario: comprendere / misurare / migliorare / progettare |
| Q2 | Stato conoscenza: consolidata / emergente / inesistente |
| Q3 | Tipo outcome atteso: quantitativo / qualitativo / entrambi |
| Q4 | Vincoli pratici: no-randomizzazione / N<10 / N>100 / nessuno |
| Q5 | Sequenza temporale: cross-sectional / longitudinale / iterativo |
| Q6 | Focus epistemologico (solo se Q3=qualitativo): esperienza-vissuta / teoria-emergente / contesto-culturale / narrazione |

**Routing Table (prima corrispondenza vince):**

| Q1 | Q2 | Q3 | Q4 | Q5 | Q6 | → Paradigma |
|----|----|----|----|----|----|----|
| misurare | qualsiasi | quant | nessuno | qualsiasi | — | **MOD-QN2** RCT |
| misurare | qualsiasi | quant | no-rand | qualsiasi | — | **MOD-QN1** Quasi-exp |
| misurare | qualsiasi | quant | N<10 | qualsiasi | — | **MOD-QN3** Single-Subject |
| misurare | qualsiasi | quant | N>100 | cross | — | **MOD-QN4** Survey |
| qualsiasi | qualsiasi | entrambi | qualsiasi | qualsiasi | — | **MOD-MM** Mixed-Methods |
| migliorare | qualsiasi | qualsiasi | qualsiasi | iterativo | — | **MOD-AR** Action Research |
| progettare | qualsiasi | qualsiasi | qualsiasi | iterativo | — | **MOD-DBR** Design-Based |
| comprendere | qualsiasi | qual | qualsiasi | qualsiasi | esperienza-vissuta | **MOD-Q1** Fenomenologia |
| comprendere | inesistente | qual | qualsiasi | qualsiasi | teoria-emergente | **MOD-Q2** Grounded Theory |
| comprendere | qualsiasi | qual | qualsiasi | longitudinale | contesto-culturale | **MOD-Q3** Etnografia |
| comprendere | qualsiasi | qual | qualsiasi | qualsiasi | narrazione | **MOD-Q4** Narrativo |

### 8.3 Struttura Fasi per Modulo

| Fase | Tutte le metodologie | QN specifico | Q specifico |
|------|---------------------|-------------|-------------|
| 0 | Decision tree | — | — |
| 1 | Framework teorico, RQ | Ipotesi H1/H0, power analysis | Domande aperte, posizionalità |
| 2 | Design specifico | Quasi-exp/RCT/SS/Survey, criteri go/no-go, stopping rules | Protocollo interviste/FG/osservazione |
| 3 | Strumenti | Scale validate, codebook numerico | Interview guide, atlas codici |
| 4 | Procedura, etica, consenso | Randomizzazione/matching, fidelity check | Saturation check, member checking |
| 5 | Piano analisi → `piano-analisi.json` | ANCOVA/HLM, FIML→MI, OSF pre-reg | Thematic Analysis (Braun & Clarke 2021), κ inter-rater |
| 6 | Preprint bozza, roadmap post-studio | IMRAD standard | IMRAD qualitativo |

### 8.4 Correzioni Scientifiche Obbligatorie

**Effect size:**
- Sostituire ovunque "d=0.5 (conservativo)" con "d=0.5 (medio secondo Cohen 1988 — stima in assenza di dati empirici)"
- Per campioni diseguali (n₁ ≠ n₂) o piccoli (< 20/gruppo): preferire **Hedges' g** a Cohen's d. JASP e R (`effsize` package) lo calcolano automaticamente.

**Missing data per ANCOVA:**
- Rimuovere riferimento a FIML per ANCOVA
- Sostituire con:
  ```
  Missing data:
  - MCAR (Little's test): listwise deletion accettabile
  - MAR (più comune): Multiple Imputation con mice (R) o JASP 0.19+
    poi pooling con Rubin's Rules
  - MNAR: sensitivity analysis (pattern mixture model)
  FIML: appropriato per SEM/path analysis, non per ANCOVA classica
  ```

**Cronbach's α:**
- Sostituire "α < .50 → strumento inutilizzabile" con:
  ```
  α < .50: inaccettabile per scale ≥ 6 item
  Per scale brevi (3–5 item): usare ω di McDonald o split-half reliability
  α .50–.70: segnalare come limitazione, valutare alternative
  α ≥ .70: accettabile; α ≥ .80 preferibile
  ```

**Pre-registrazione OSF:**
- Aggiungere warning esplicito: "⚠️ La pre-registrazione deve avvenire PRIMA di somministrare qualsiasi strumento. Una volta raccolto anche un solo dato, il valore della pre-registrazione è compromesso. Conferma di non aver ancora avviato la raccolta?"

### 8.5 piano-analisi.json — Schema e Validazione

Schema in `skills/research-design/piano-analisi-schema.json`.  
**Validazione obbligatoria** prima di scrivere il file:

```python
import json, jsonschema
SCHEMA_PATH = f"{repo_path}/skills/research-design/piano-analisi-schema.json"
schema = json.loads(open(SCHEMA_PATH).read())
instance = { ... }  # dati da compilare
jsonschema.validate(instance, schema)  # lancia ValidationError se invalido
write_state("design/fase-5-analisi/piano-analisi.json", instance)
```

---

## 9. Skill: data-collection

### 9.1 Attivazione

Invocata dopo che `research-design` ha completato la Fase 5 e `piano-analisi.json` esiste e valida.

### 9.2 Adattamento al Paradigma

Legge `.project-state.json` → `phases.research-design.paradigm` → attiva modulo:

**Modulo Quantitativo (MOD-QN1-4):**
- Guida costruzione codebook con variabili pre-compilate da `piano-analisi.json`
- Crea `raccolta-dati/matrice_dati.csv` con header: `[ID_partecipante, gruppo, pretest_VD1, pretest_VD2, ..., posttest_VD1, posttest_VD2, ..., covariata1, ...]`
- Checklist qualità dati: range plausibili, valori mancanti, codici errore
- Verifica criteri go/no-go da `piano-analisi.json → go_nogo_criteria`

**Modulo Qualitativo (MOD-Q1-4):**
- Guida trascrizione verbatim (formato: `INT-001.md` con header standardizzato)
- Template atlas codici: codice / definizione / esempio / anti-esempio / memo
- Saturazione teorica: checklist per valutare quando fermarsi (Fase 2: ≥ 2 interviste senza nuovi codici)
- Memo analitico: journaling durante il coding

**Modulo Mixed (MOD-MM):**
- Entrambi i moduli in parallelo
- Tabella sincronizzazione: ID cross-referenziato tra dataset quant e qual
- Integrazione temporale: specifica il punto di convergenza dei dati

**Modulo AR/DBR:**
- Journal di campo per ciclo (formato: `ciclo-01.md`)
- Template ciclo: obiettivo → azione → osservazione → riflessione → decisione per ciclo N+1

### 9.3 Nota su matrice_dati

La matrice dati viene creata come **CSV** (creabile con Write tool). Se necessario, la conversione in Excel avviene con:
```python
import pandas as pd
pd.read_csv("raccolta-dati/matrice_dati.csv").to_excel("raccolta-dati/matrice_dati.xlsx", index=False)
```

### 9.4 State File (.collection-state.json)

```json
{
  "paradigm": "MOD-QN1",
  "collection_status": "in_progress",
  "participants": { "target": 42, "enrolled": 38, "dropout": 2, "complete": 0 },
  "instruments_administered": [],
  "go_nogo_result": null,
  "last_updated": "ISO8601"
}
```

---

## 10. Skill: data-analysis

### 10.1 Fase di Conferma (Obbligatoria Prima di Qualsiasi Analisi)

Legge `design/fase-5-analisi/piano-analisi.json` e ripropone ogni scelta:

```
Piano di analisi trovato (definito il [data]):

1. Test: ANCOVA con pre-test come covariata
   → Confermi? Hai riscontrato problemi in raccolta che modificano questo?

2. Missing data: Multiple Imputation (mice)
   → Quanti missing hai? [___]% → strategia ancora appropriata?

3. Software: JASP
   → Disponibile? Alternativa: R (pacchetti: car, emmeans, mice)

4. Ipotesi pre-registrata: H1 = d ≥ 0.4 (Hedges' g)
   → Analisi esplorative non pre-registrate da aggiungere?
      (le dichiarerò come tali nel preprint)

5. Criteri go/no-go: [lista da piano-analisi.json]
   → Esito raccolta: [__]/5 criteri soddisfatti → PROCEED / STOP / REVISE
```

### 10.2 Guida per Paradigma

**MOD-QN1 (quasi-sperimentale):**
1. Statistiche descrittive: M, SD, range per variabile × gruppo
2. Test equivalenza baseline (t-test o Mann-Whitney U sul pretest)
3. Verifica assunzioni ANCOVA: normalità residui (Shapiro-Wilk), omoschedasticità (Levene), linearità covariata-DV, omogeneità pendii regressione
4. ANCOVA: F(df1,df2)=X, p=.XX, η²p=.XX, IC 95%; Hedges' g=X
5. Se assunzioni violate e N piccolo: Mann-Whitney U o Wilcoxon signed-rank
6. Multiple Imputation se MAR: mice → pooling Rubin's Rules

**MOD-Q1-4 (qualitativo):**
Thematic Analysis Riflessiva (Braun & Clarke 2006; 2021):
1. Familiarizzazione (trascrizione verbatim, letture ripetute)
2. Coding (etichette descrittive, riflessività su bias del ricercatore)
3. Generazione temi (raggruppamento codici significativi)
4. Revisione temi (coerenza interna, distinzione tra temi)
5. Definizione e denominazione (definizione per ogni tema)
6. Scrittura (narrativa + 2–3 citazioni esemplari per tema)
- Inter-rater: Cohen's κ ≥ .70 dopo step 2 (se secondo codificatore disponibile)
- Member checking se disponibile

**MOD-MM:** Componente prioritaria prima, poi secondaria, poi joint display  
**MOD-AR/DBR:** Analisi riflessiva per ciclo, pattern tra cicli, indicatori cambiamento pratico

### 10.3 Output

| File | Contenuto |
|------|-----------|
| `analisi/piano-analisi-confermato.json` | Piano aggiornato con scelte reali |
| `analisi/risultati_quantitativi.md` | Tabelle in formato IMRAD, statistiche complete |
| `analisi/risultati_qualitativi.md` | Temi + definizioni + citazioni esemplari |
| `analisi/integrazione_mm.md` | Joint display (solo MOD-MM) |
| `analisi/.analysis-state.json` | Stato analisi |

---

## 11. Skill: preprint

### 11.1 Selezione Template (paradigma × piattaforma)

**Per paradigma:**

| Paradigma | Struttura |
|-----------|-----------|
| MOD-QN1-4 | IMRAD: Abstract → Intro → Methods → Results → Discussion → Conclusions |
| MOD-Q1-4 | IMRAD qualitativo: Abstract → Intro → Theoretical Framework → Methodology → Findings → Discussion |
| MOD-MM | IMRAD misto: Methods diviso in quant+qual; Results dual; Discussion integrata con joint display |
| MOD-AR | Ciclico: Background → Problem Statement → Cicli (1..N) → Cross-cycle Reflection → Implications |
| MOD-DBR | Iterativo: Problem → Design Principles → Iterations → Efficacy Study → Theoretical Contribution |

**Per piattaforma:**

| Piattaforma | Dominio | Lingua | Requisiti specifici |
|-------------|---------|--------|---------------------|
| arXiv | Ed-Tech, AI, informatica educativa | Inglese obbligatorio | LaTeX o PDF; categoria cs.AI o cs.CY |
| Zenodo | Tutti | Italiano o inglese | PDF/Word; DOI auto-assegnato; licenza CC |
| Open Research Europe | Ricerca Horizon EU | Inglese o italiano | Peer review aperta; FAIR data statement; Data Availability |
| SSRN | Scienze sociali, psicologia | Inglese | Word o PDF; abstract strutturato |
| EdArXiv | Educazione, didattica | Italiano o inglese | PDF; abstract 150–250 parole |
| PsyArXiv | Psicologia, psicopedagogia | Inglese | APA format; open materials badge |

### 11.2 Domande Iniziali Obbligatorie

```
1. Per quale piattaforma stai preparando il preprint?
2. Il lavoro è finanziato da un grant Horizon EU? (→ Open Research Europe se sì)
3. Vuoi includere i dati grezzi come supplemento open?
4. Hai conflitti di interesse da dichiarare?
5. Vuoi aggiungere la dichiarazione CRediT per i contributi autoriali?
```

### 11.3 Reporting Standards per Paradigma

| Paradigma | Standard obbligatorio | Link |
|-----------|----------------------|------|
| MOD-QN2 (RCT) | CONSORT 2010 + extension | equator-network.org |
| MOD-QN1 (quasi-exp) | TREND | CDC |
| MOD-QN3 (single-subject) | SCRIBE | |
| MOD-QN4 (survey) | STROBE | equator-network.org |
| MOD-Q1-2 (interviste/FG) | COREQ | |
| MOD-Q1-4 (qualitativo generale) | SRQR | |
| MOD-AR | SQUIRE 2.0 | squire-statement.org |
| MOD-MM | GRAMMS | |

La skill allega la checklist del reporting standard come `preprint/reporting_checklist.md`.

### 11.4 Sezioni Obbligatorie per Piattaforme Open

**Open Research Europe / Zenodo:**
- Data Availability Statement: "I dati sono disponibili su [repository] con DOI [doi]" oppure "I dati non sono pubblicamente disponibili per [motivazione — GDPR/privacy minori]"
- FAIR data: Findable (DOI), Accessible (deposito aperto), Interoperable (formato CSV/JSON), Reusable (licenza CC BY 4.0)

**Tutte le piattaforme:**
- Conflict of Interest: "Gli autori dichiarano [nessun conflitto / conflitto specifico]"
- CRediT (se richiesto): Conceptualization: X; Methodology: X; Investigation: X; Writing: X; ...

### 11.5 Guardrail Anti-Allucinazione nel Preprint

Per ogni affermazione citata in Introduction, Methods o Discussion:
```bash
py hybrid_rag.py query "[costrutto da citare]" --n 3
```
- Se il paper è nel RAG → cita normalmente con (Autore, Anno)
- Se non è nel RAG → marca come `[CITARE: Autore, Anno — da verificare]`
- MAI inserire citazioni da memoria del modello

---

## 12. MCP Server

### 12.1 Stato e Gap

| Server | File | Status | Note |
|--------|------|--------|------|
| CORE | `mcp-servers/core/server.py` | ⚠️ Da verificare output JSON | |
| DOAJ | `mcp-servers/doaj/server.py` | ⚠️ Da verificare output JSON | |
| ERIC | `mcp-servers/eric/server.py` | ❌ Output Markdown, non JSON | Abstract troncato 300 chars |
| OpenAIRE | `mcp-servers/openaire/server.py` | ⚠️ Da verificare output JSON | |
| Zenodo | `mcp-servers/zenodo/server.py` | ⚠️ Da verificare output JSON | |
| Semantic Scholar | — | ❌ Non implementato | Alta priorità |
| PubMed | — | ❌ Non implementato | Alta priorità |
| arXiv | — | ❌ Non implementato | Media priorità |

### 12.2 Standard di Implementazione (tutti i server)

```python
# Pattern obbligatorio per tutti i server MCP

import time
RATE_LIMIT_DELAY = 0.5  # secondi tra richieste paginate
REQUEST_TIMEOUT = 30    # secondi timeout per chiamata

def _make_result(record: dict, source_db: str) -> dict:
    """Formato JSON standard — abstract NON troncato."""
    return {
        "title": record.get("title", ""),
        "doi": record.get("doi") or None,
        "year": int(record.get("year", 0)) or None,
        "authors": record.get("authors", []),
        "abstract": record.get("abstract", ""),   # COMPLETO
        "source_db": source_db,
        "url": record.get("url", ""),
        "id": record.get("id", ""),
        "journal": record.get("journal") or None,
        "keywords": record.get("keywords", [])
    }

def search(query: str, limit: int = 200, **filters) -> dict:
    results = []
    for page in _paginate(query, limit, **filters):
        results.extend([_make_result(r, SOURCE_DB) for r in page])
        time.sleep(RATE_LIMIT_DELAY)
    return {"results": results, "total": len(results), "query": query}
```

### 12.3 API Semantic Scholar (da implementare)

```
Base URL: https://api.semanticscholar.org/graph/v1/
Endpoint: /paper/search?query=...&fields=title,authors,year,abstract,externalIds,url
API Key: opzionale (rate limit più alto con chiave)
Rate limit senza key: 100 req/5min → delay 3s tra richieste paginate
Pagination: offset + limit (max 100 per chiamata)
```

### 12.4 API PubMed (da implementare)

```
Base URL: https://eutils.ncbi.nlm.nih.gov/entrez/eutils/
Endpoint search: /esearch.fcgi?db=pubmed&term=...&retmax=200&retmode=json
Endpoint fetch: /efetch.fcgi?db=pubmed&id=...&retmode=xml
API Key: obbligatoria per > 10 req/sec (gratuita su NCBI)
Parsing: XML → BeautifulSoup o xml.etree per abstract completo
```

---

## 13. Problemi Critici e Correzioni

### CRITICO — C1: Script Python mancanti

**Problema:** `prisma_screening.py` (deduplicazione cross-database) e `extract_pdf_metadata.py` (ingestion PDF) sono dichiarati nella skill ma non esistono.

**Soluzione — `prisma_screening.py`:**
Script da creare in `{project-root}/` che:
1. Legge tutti i `raw_*.json` presenti
2. Normalizza i record allo schema standard (§6.4)
3. Deduplica per DOI (esatta) poi per titolo+anno (fuzzy, soglia 0.85)
4. Produce `screening_prisma.json` con campo `source_databases: [lista]` per ogni record

Dipendenze Python: `rapidfuzz` (fuzzy matching), `json`, `pathlib`

**Soluzione — `extract_pdf_metadata.py`:**
Script da creare in `skills/prisma-review/scripts/` che:
1. Legge PDF dalla cartella `pdf_manuali/`
2. Estrae metadati con `pdfplumber` (titolo, autori se presenti, abstract)
3. Produce `raw_pdf_manual.json` nello schema standard

---

### CRITICO — C2: Output server ERIC è Markdown, non JSON

**Problema:** `mcp-servers/eric/server.py` restituisce testo formattato Markdown. `prisma_screening.py` si aspetta JSON strutturato con campi tipizzati.

**Soluzione:** Refactoring del server per separare presentazione da dati:
```python
# Prima: restituisce Markdown
def _format_results(data): return "1. **Titolo**\n   Authors: ..."

# Dopo: restituisce JSON strutturato
def search_eric(...) -> dict:
    raw = _fetch_eric_api(...)
    return {
        "results": [_make_result(r, "eric") for r in raw],
        "total": raw["response"]["numFound"],
        "query": query
    }
```
La presentazione Markdown per l'utente viene generata dal chiamante (la skill PRISMA), non dal server.

Stesso refactoring va applicato a tutti i server MCP esistenti.

---

### CRITICO — C3: Fallback RAG su screening_prisma.json

**Problema:** Se `eligibility_prisma.json` non esiste, la skill permette il fallback a `screening_prisma.json`. Questo viola il guardrail: il RAG indicizza paper non inclusi nello studio.

**Soluzione:** Eliminare il fallback. Aggiungere in `hybrid-rag/SKILL.md`:
```
Se eligibility_prisma.json non esiste → STOP:
"RAG non costruibile: Fase 4 di prisma-review non completata.
Il RAG deve contenere SOLO i paper inclusi (eligibility_prisma.json).
Usare screening_prisma.json comprometterebbe il guardrail anti-allucinazione."
```

---

### CRITICO — C4: Struttura file prisma-review vs architettura

**Problema:** `prisma-review` scrive flat in `{project-root}/`. La spec architetturale (versione precedente) prevedeva una sottocartella `prisma/`. Incompatibilità.

**Soluzione:** La spec adotta il **flat layout per PRISMA** (vedi §3.1). Non modificare la skill esistente. Le nuove skill (`research-design`, `data-collection`, `data-analysis`, `preprint`) usano sottocartelle dedicate.

---

### SCIENTIFICO — S1: "d=0.5 conservativo" è impreciso

**Testo da sostituire in research-design/SKILL.md e educational-pilot-design/SKILL.md:**
- ❌ `d = 0.5 (convenzionale — dichiara esplicitamente che è stima conservativa)`
- ✅ `d = 0.5 (effect size medio secondo Cohen 1988 — stima in assenza di dati. Se PRISMA riporta effect size diversi, usare il valore empirico. Per interventi nuovi con incertezza alta, giustificare la scelta.)`

---

### SCIENTIFICO — S2: Hedges' g per campioni diseguali

**Da aggiungere in research-design Fase 5 e data-analysis:**
```
Effect size consigliato:
- Campioni uguali (n₁ = n₂): Cohen's d accettabile
- Campioni diseguali (n₁ ≠ n₂) o piccoli (< 20/gruppo): Hedges' g obbligatorio
  JASP: calcola automaticamente; R: effsize::cohen.d(..., hedges.correction=TRUE)
- Per misure ripetute o disegni complessi: η²p (partial eta squared)
```

---

### SCIENTIFICO — S3: Decision tree — gap e overlap risolti

**Soluzione:** Aggiunta Q6 e routing top-down (vedi §8.2). Le condizioni più specifiche (RCT, Single-Subject, AR, DBR) hanno priorità sulle più generiche.

---

### SCIENTIFICO — S4: FIML non applicabile a ANCOVA classica

**Correzione:** vedi §8.4.

---

### SCIENTIFICO — S5: α Cronbach — soglia assoluta contestabile

**Correzione:** vedi §8.4.

---

### SCIENTIFICO — S6: OSF pre-registrazione — timing non esplicito

**Correzione:** vedi §8.4.

---

### SCIENTIFICO — S7: Reporting standards assenti

**Soluzione:** Aggiunta sezione §11.3 con mapping paradigma → standard (CONSORT, STROBE, COREQ, ecc.).

---

### LOGICA — L1: eligibility_prisma.json vs extraction_table.json

**Decisione:** `eligibility_prisma.json` è il nome canonico. Rimuovere ogni riferimento a `extraction_table.json` dalla documentazione, o documentare esplicitamente che sono file distinti con contenuto diverso (i dati estratti vanno in `eligibility_prisma.json`).

---

### LOGICA — L2: wiki.py — path assoluto

**Correzione:** In tutte le skill, usare il path costruito da `.project-state.json → repo_path`:
```bash
py {repo_path}/wiki/scripts/wiki.py query --workspace {wiki_workspace} --q "..."
```

---

### LOGICA — L3: hybrid_rag.py — deployment scalabile

**Soluzione:** `pipeline-regista` copia il file all'inizializzazione. Vedi §7.3.

---

### LOGICA — L4: Percorso "no-wiki"

**Soluzione:** Vedi §5.3. Se wiki non configurata: `wiki_configured = false`, le skill saltano le query wiki e funzionano solo con hybrid-rag per il guardrail.

---

### LOGICA — L5: Atomic write per state file

**Soluzione:** Pattern obbligatorio in §1.2 Principio 8. Da applicare in `pipeline-regista`, `research-design`, `data-collection`, `data-analysis`, `preprint`.

---

### STABILITÀ — ST1: Rate limiting server MCP

**Soluzione:** Pattern obbligatorio in §12.2. `RATE_LIMIT_DELAY = 0.5` tra richieste paginate. `REQUEST_TIMEOUT = 30` per ogni chiamata.

---

### STABILITÀ — ST2: Abstract troncato nel server ERIC

**Soluzione:** inclusa in C2. Abstract completo nel JSON raw; presentazione troncata solo in conversazione.

---

### STABILITÀ — ST3: Validazione piano-analisi.json

**Soluzione:** Snippet di validazione in §8.5. Obbligatorio prima di scrivere il file.

---

### STABILITÀ — ST4: matrice_dati — CSV non XLSX

**Soluzione:** Vedi §9.3. CSV creabile natively; conversione xlsx opzionale con pandas.

---

### MIGLIORAMENTI — M1–M9

| # | Miglioramento | Sezione |
|---|---------------|---------|
| M1 | CRediT taxonomy per authorship | §11.2 domanda 5 |
| M2 | FAIR data statement | §11.4 |
| M3 | Registered Reports come tipo submission | Da aggiungere in preprint skill |
| M4 | .gitignore creato all'init | §5.3 passo 4 |
| M5 | Timeout 30s per chiamate MCP | §12.2 |
| M6 | Lingua preprint per piattaforma | §11.1 tabella colonna Lingua |
| M7 | Ethics tracking in master state | §3.2 campo ethics |
| M8 | Conflict of interest nel preprint | §11.2 domanda 4 |
| M9 | .gitignore protegge dati sensibili | §5.3 passo 4 |

---

## 14. Roadmap di Implementazione

### Sprint 1 — Fondamenta (prerequisito per tutto il resto)

**Obiettivo:** Rendere la pipeline esistente stabile e corretta prima di aggiungere nuove skill.

| Task | File | Stima |
|------|------|-------|
| S1.1 Refactoring tutti i server MCP → output JSON strutturato | `mcp-servers/*/server.py` | 2h/server |
| S1.2 Creare `prisma_screening.py` | `skills/prisma-review/scripts/` | 3h |
| S1.3 Creare `extract_pdf_metadata.py` | `skills/prisma-review/scripts/` | 2h |
| S1.4 Rimuovere fallback RAG da hybrid-rag | `skills/hybrid-rag/SKILL.md` | 30min |
| S1.5 Canonicalizzare `eligibility_prisma.json` (rimuovere `extraction_table.json`) | `skills/prisma-review/SKILL.md` | 1h |
| S1.6 Aggiungere rate limiting e timeout a tutti i server MCP | `mcp-servers/*/server.py` | 30min/server |
| S1.7 Pattern write atomico — snippet riusabile | `skills/` (utils) | 1h |

**Deliverable:** Pipeline PRISMA → RAG funzionante end-to-end con dati strutturati.

---

### Sprint 2 — Rigore Scientifico (prima del testing con utenti reali)

**Obiettivo:** Correggere tutti gli errori metodologici nelle skill.

| Task | File | Stima |
|------|------|-------|
| S2.1 Fix terminologia d=0.5 | `skills/educational-pilot-design/SKILL.md` + `research-design/SKILL.md` | 30min |
| S2.2 Aggiungere Hedges' g | Stessi file | 30min |
| S2.3 Fix decision tree — aggiungere Q6, routing top-down | `skills/research-design/SKILL.md` | 1h |
| S2.4 Fix FIML → Multiple Imputation | `skills/research-design/SKILL.md` + piano-analisi-schema.json | 1h |
| S2.5 Fix soglie α Cronbach | `skills/research-design/SKILL.md` | 30min |
| S2.6 Warning OSF timing | `skills/research-design/SKILL.md` | 15min |
| S2.7 Aggiungere reporting standards (CONSORT, STROBE, ecc.) | `skills/preprint/SKILL.md` (da creare) | 2h |

**Deliverable:** Skill metodologicamente corrette, pronte per review da metodologi.

---

### Sprint 3 — Pipeline-Regista e Research-Design MVP

**Obiettivo:** Creare le skill mancanti ad alta priorità.

| Task | File | Piano |
|------|------|-------|
| S3.1 Creare `skills/pipeline-regista/SKILL.md` | — | Da pianificare |
| S3.2 Completare `skills/research-design/SKILL.md` (Fase 0 + MOD-QN1) | `docs/superpowers/plans/2026-06-01-research-design-skill-mvp.md` | Piano esistente |
| S3.3 Creare MCP Semantic Scholar | `mcp-servers/semantic-scholar/server.py` | Da pianificare |
| S3.4 Creare MCP PubMed | `mcp-servers/pubmed/server.py` | Da pianificare |
| S3.5 Deprecare `pipeline-ricerca` e `educational-pilot-design` | Skills esistenti | 1h |

**Deliverable:** Ricercatore può avviare un nuovo progetto end-to-end fino a research-design.

---

### Sprint 4 — Nuove Skill

**Obiettivo:** Completare l'intera pipeline con data-collection, data-analysis, preprint.

| Task | Piano |
|------|-------|
| S4.1 Creare `skills/data-collection/SKILL.md` | Da pianificare |
| S4.2 Creare `skills/data-analysis/SKILL.md` | Da pianificare |
| S4.3 Creare `skills/preprint/SKILL.md` | Da pianificare |
| S4.4 Creare MCP arXiv | Da pianificare |
| S4.5 Validazione piano-analisi.json integrata | Sprint 4 |

**Deliverable:** Pipeline completa end-to-end funzionante per MOD-QN1.

---

### Sprint 5 — Estensione Paradigmi e Ottimizzazioni

| Task | Note |
|------|------|
| S5.1 research-design MOD-QN2-4, MOD-Q1-2, MOD-MM | Piano 2 (da scrivere) |
| S5.2 research-design MOD-Q3-4, MOD-AR, MOD-DBR | Piano 3 (da scrivere) |
| S5.3 data-collection moduli Q, MM, AR/DBR | Parallelo con S5.1 |
| S5.4 Audit lint wiki + ottimizzazioni RAG | Manutenzione |

---

*Fine documento — `docs/PROJECT-SPEC.md` v1.0*
