# Pipeline Ricerca Accademica — Architettura Completa

**Data:** 2026-06-01  
**Versione:** 1.2 — fix numerazione, righe orfane, principio 2, wiki_workspace in state  
**Sostituisce:** tutti i riferimenti architetturali in `pipeline-ricerca/SKILL.md`

---

## 1. Visione

Un sistema di skill coordinate che guida un ricercatore in scienze dell'educazione dall'identificazione delle domande di ricerca fino alla pubblicazione del preprint — senza mai perdere il filo, anche su sessioni separate distanziate di settimane.

**Principio fondamentale:** l'intera ricerca vive in uno **spazio di progetto autonomo** creato in PRISMA Fase 0. Ogni skill legge e scrive in quello spazio. Il ricercatore non deve mai ricordare "dove eravamo rimasti" — lo fa il sistema.

---

## 2. Due Sistemi di Memoria — Ruoli Distinti

Il sistema usa **due meccanismi di memoria complementari**, non intercambiabili:

| | **Wiki** (LanceDB bge-m3) | **hybrid-rag** (LanceDB/ChromaDB) |
|--|--------------------------|----------------------------------|
| **Scope** | Cross-progetto, permanente | Locale al singolo progetto |
| **Workspace** | Directory separata configurata in `wiki/wiki.config.json` | `{project-root}/rag_db/` |
| **Cosa contiene** | Entity pages strutturate dei paper + sintesi distillate | Chunks dei paper per retrieval RAG |
| **Costruito quando** | `wiki ingest` dopo PRISMA Fase 4 e 6 | `hybrid_rag.py index-prisma` dopo PRISMA Fase 4 |
| **Query** | `wiki.py query --q "..."` — risposta semantica narrativa | `hybrid_rag.py query "..."` — chunks rilevanti |
| **Usato da** | Tutte le fasi per conoscenza trasversale | Preprint e report per guardrail anti-allucinazione |
| **Promossa a livello superiore** | Sì: `wiki-works/{proj}/` → `wiki/` se cross-progetto | No — rimane locale |

### Wiki Workspace Structure (separato da {project-root})

```
{wiki-workspace}/                    ← configurato in wiki/wiki.config.json
│                                       path ESTERNO al progetto, condiviso tra ricerche
├── wiki/                            ← conoscenza permanente cross-progetto
│   ├── .schema.md
│   ├── log.md                       ← append-only
│   ├── concepts/
│   └── synthesis/
│
├── wiki-works/
│   └── {project-name}/              ← attivato per questa ricerca
│       ├── .schema.md
│       ├── log.md
│       ├── entities/                ← una pagina per ogni paper incluso
│       ├── concepts/
│       └── synthesis/
│
└── memory/
    └── lancedb/                     ← indice vettoriale bge-m3 (ricostruibile)
```

---

## 3. Architettura a Skill Coordinate

```
┌─────────────────────────────────────────────────────────────────┐
│                    pipeline-regista                             │
│  skill orchestratrice interattiva — guida dall'inizio alla fine │
│  conosce lo stato di ogni fase — sa sempre dove si è arrivati   │
└────────────────────────┬────────────────────────────────────────┘
                         │ coordina
    ┌────────────────────┼──────────────────────────┐
    ▼                    ▼                          ▼

[MCP Servers bibliografici]
    Semantic Scholar · PubMed · arXiv          ← mancanti, da implementare
    CORE · DOAJ · ERIC · OpenAIRE · Zenodo     ← esistenti
         ↓
[prisma-review]
    Pre-PRISMA: wiki query (conoscenza pre-esistente cross-progetto)
    PICO + RQ + ipotesi + selezione articoli
    Post-PRISMA Fase 4: wiki ingest entity pages + hybrid-rag index-prisma
    Post-PRISMA Fase 6: wiki ingest synthesis page
         ↓
         ├──→ wiki-works/{progetto}/   [entity pages + sintesi — memoria permanente]
         └──→ rag_db/                  [chunks indicizzati — retrieval locale]
         ↓
[research-design]
    Fase 0: scelta paradigma (decision tree)
    Fase 1-6: framework, design, strumenti, procedura, piano analisi
    Usa: wiki query per framework cross-progetto
         ↓
[data-collection]
    adattato al tipo di dati (paradigma scelto)
    Usa: wiki query per strumenti usati in letteratura
         ↓
[data-analysis]
    conferma piano + guida analisi per paradigma
    Usa: wiki query per benchmarking effect size da letteratura
         ↓
[preprint]
    template per paradigma × piattaforma target
    Usa: hybrid_rag query per ogni citazione (guardrail anti-allucinazione)
         Usa: wiki query per conoscenza cross-progetto
         ↓
[pandoc-export]
    conversione Word / PDF
```
---

## 4. Spazio di Progetto (creato da PRISMA Fase 0)

Ogni ricerca ha una cartella radice dedicata. **Tutta la ricerca vive lì.** Il ricercatore non deve mai copiare file tra cartelle.

```
{project-root}/                          ← creato da pipeline-regista o prisma-review Fase 0
│                                           NON contiene la wiki (workspace separato)
├── .project-state.json                  ← MASTER STATE — stato di ogni fase
├── project-log.md                       ← AUDIT LOG append-only — ogni sessione scrive qui
│
├── prisma/                              ← output di prisma-review
│   ├── prisma_state.json
│   ├── prisma_log.md
│   ├── raw_semantic_scholar.json        ← risultati grezzi da ogni MCP (Fase 1)
│   ├── raw_pubmed.json
│   ├── raw_arxiv.json
│   ├── raw_eric.json
│   ├── raw_openaire.json
│   ├── raw_core.json
│   ├── raw_doaj.json
│   ├── raw_zenodo.json
│   ├── screening_prisma.json
│   ├── eligibility_prisma.json
│   ├── extraction_table.json
│   ├── prisma_synthesis.md              ← handoff critico → research-design
│   └── prisma_bibliography.md
│
├── rag_db/                              ← hybrid-rag index (locale, solo questo progetto)
│   └── config.json
│
│   [wiki-workspace separato]           ← NON qui — vedi §2
│   wiki-works/{project-name}/          ← entity pages paper + sintesi (LanceDB bge-m3)
│
├── design/                              ← output di research-design
│   ├── .research-state.json
│   ├── protocollo_ricerca.md
│   ├── strumenti_valutazione.md
│   ├── timeline_pilota.md
│   └── fase-5-analisi/
│       └── piano-analisi.json           ← handoff critico → data-analysis
│
├── raccolta-dati/                       ← output di data-collection
│   ├── .collection-state.json
│   ├── codebook.md                      ← (quantitativo / mixed)
│   ├── matrice_dati.xlsx                ← (quantitativo / mixed)
│   ├── trascrizioni/                    ← (qualitativo / mixed)
│   │   └── [INT-001.md, INT-002.md, ...]
│   ├── atlas_codici.md                  ← (qualitativo / mixed)
│   └── memo_analitico.md               ← (qualitativo)
│
├── analisi/                             ← output di data-analysis
│   ├── .analysis-state.json
│   ├── piano-analisi-confermato.json    ← piano confermato con domande di verifica
│   ├── risultati_quantitativi.md        ← tabelle, statistiche, effect size
│   ├── risultati_qualitativi.md         ← temi, codici, citazioni esemplari
│   └── integrazione_mm.md              ← (solo mixed-methods)
│
└── preprint/                            ← output di preprint skill
    ├── .preprint-state.json
    ├── preprint_bozza.md                ← documento completo
    ├── preprint_bozza.docx              ← (pandoc-export)
    └── submission_checklist.md          ← checklist per la piattaforma target
```

---

## 5. Master State File (`.project-state.json`)

Aggiornato da ogni skill al completamento di ogni fase. Letto da `pipeline-regista` per sapere dove si è arrivati.

```json
{
  "project_name": "string",
  "project_root": "/path/assoluto/al/progetto",
  "wiki_workspace": "/path/assoluto/al/wiki-data",
  "wiki_project_name": "nome-progetto-in-wiki-works",
  "created_at": "ISO8601",
  "researcher": {
    "name": "string",
    "institution": "string",
    "domain": "Ed-Tech | Psicopedagogia | Didattica | Pedagogia | Valutazione | FormDocenti"
  },
  "current_phase": "research-design",
  "phases": {
    "prisma": {
      "status": "completed | in_progress | pending | skipped",
      "started_at": "ISO8601",
      "completed_at": "ISO8601",
      "key_outputs": {
        "rq_count": 3,
        "included_papers": 24,
        "dominant_paradigm": "quasi-experimental",
        "effect_size_range": "0.3-0.7"
      }
    },
    "rag": {
      "status": "completed | pending",
      "backend": "lancedb | chromadb",
      "indexed_papers": 24
    },
    "wiki": {
      "status": "completed | pending",
      "pages_created": 25
    },
    "research-design": {
      "status": "in_progress",
      "started_at": "ISO8601",
      "paradigm": "MOD-QN1",
      "current_internal_phase": 3
    },
    "data-collection": {
      "status": "pending"
    },
    "data-analysis": {
      "status": "pending"
    },
    "preprint": {
      "status": "pending"
    }
  },
  "last_updated": "ISO8601",
  "last_skill": "research-design",
  "last_session": "ISO8601"
}
```

---

## 6. Audit Log (`project-log.md`)

**Append-only.** Ogni skill aggiunge entry — mai sovrascrive. Consente di ricostruire l'intera storia decisionale anche senza aprire i file di stato.

```markdown
## [ISO8601] pipeline-regista | Progetto avviato
**Ricercatore:** [nome] | **Istituzione:** [istituzione]
**Dominio:** [dominio] | **Livello scolastico:** [livello]

## [ISO8601] prisma-review | Fase 0 completata
**PICO:** P=[...] I=[...] C=[...] O=[...]
**Database interrogati:** Semantic Scholar, PubMed, ERIC, arXiv

## [ISO8601] prisma-review | Fase 4 completata
**Paper inclusi:** 24 | **Esclusi:** 187 | **Effect size medio:** d=0.52

## [ISO8601] research-design | Paradigma selezionato
**Paradigma:** MOD-QN1 — Quasi-sperimentale
**Rationale:** [Q1=misurare, Q3=quantitativo, Q4=no rand.]

## [ISO8601] data-collection | Raccolta avviata
**Tipo dati:** quantitativo + qualitativo (Explanatory Sequential)
**N partecipanti confermati:** 42

...
```

---

## 7. Skill Regista (pipeline-regista)

### 7.1 Ruolo

`pipeline-regista` è la **porta d'ingresso** al sistema. Il ricercatore non deve sapere quale skill invocare — lo fa il regista in base allo stato del progetto.

### 7.2 Comportamento all'avvio

```
1. Esiste .project-state.json nella cartella corrente?
   
   NO → "Vuoi avviare un nuovo progetto di ricerca?
         Dimmi: (a) nome progetto, (b) dominio disciplinare,
         (c) livello scolastico, (d) obiettivo generale"
        → crea struttura cartelle + .project-state.json
        → invoca prisma-review

   SÌ → leggi .project-state.json + ultime 5 righe di project-log.md
        → presenta riepilogo:
          "Progetto: [nome] | Fase attiva: [fase] | Ultimo accesso: [data]
           [riepilogo di cosa è stato fatto e cosa manca]
           Vuoi continuare dalla fase [X] o fare qualcos'altro?"
        → invoca la skill appropriata
```

### 7.3 Comandi disponibili per il ricercatore

| Comando | Azione |
|---------|--------|
| `stato` | mostra .project-state.json in formato leggibile |
| `log` | mostra le ultime N entry di project-log.md |
| `vai a [fase]` | salta a una fase specifica (con conferma se ci sono dipendenze non soddisfatte) |
| `riepilogo [fase]` | riassume i risultati di una fase completata |
| `prossimo passo` | identifica la prossima azione da compiere |
| `esporta` | invoca pandoc-export sul file preprint_bozza.md |

### 7.4 Gestione dipendenze tra fasi

Il regista verifica le dipendenze prima di consentire l'ingresso in una fase:

| Fase | Dipendenze obbligatorie | Dipendenze opzionali |
|------|------------------------|---------------------|
| `rag` | `prisma` completata | — |
| `research-design` | `prisma` completata | `rag` (abilita query) |
| `data-collection` | `research-design` Fase 5 completata | — |
| `data-analysis` | `data-collection` completata | — |
| `preprint` | `data-analysis` completata | — |

### 7.5 Inizializzazione nuovo progetto

Quando il ricercatore risponde alle domande iniziali, il regista esegue in sequenza:

```
1. Crea {project-root}/ e sottocartelle:
   prisma/ rag_db/ design/ raccolta-dati/ analisi/ preprint/

2. Crea .project-state.json con:
   - project_name, project_root (path assoluto)
   - wiki_workspace (chiede: "Dove si trova il tuo wiki workspace?
     Es. C:/Users/nome/Documents/wiki-data")
   - wiki_project_name (suggerisce: slugify(project_name))
   - researcher.name, researcher.institution, researcher.domain
   - tutte le fasi a status: "pending"
   - created_at: now()

3. Crea project-log.md con prima entry

4. Verifica wiki workspace:
   - Esiste {wiki_workspace}/wiki.config.json? → OK
   - No → avvisa: "Wiki workspace non configurato.
     Vuoi configurarlo ora? Percorso suggerito: [path]"
   - Se OK → crea wiki-works/{wiki_project_name}/ nel workspace

5. Aggiorna .project-state.json: wiki.status = "ready"

6. Invoca prisma-review
```

### 7.6 Ripresa di un progetto esistente

```
1. Leggi .project-state.json → identifica current_phase e last_skill
2. Leggi ultime 10 righe di project-log.md
3. Presenta riepilogo sintetico:

   "Progetto: [nome] | Ultimo accesso: [data]
    ✅ PRISMA: 24 paper inclusi (completato [data])
    ✅ RAG: indicizzato (completato [data])
    ✅ Wiki: 25 pagine ingested (completato [data])
    🔄 Research-design: in corso — Fase 3/6, paradigma MOD-QN1
    ⏳ Data-collection: in attesa
    ⏳ Data-analysis: in attesa
    ⏳ Preprint: in attesa

    Vuoi continuare con research-design Fase 3?
    Oppure: stato / log / vai a [fase] / prossimo passo"

4. Attende input e delega alla skill appropriata
```

---

## 8. Skill: data-collection

### 8.1 Attivazione

Invocata da `pipeline-regista` dopo che `research-design` ha completato la Fase 5 (piano-analisi.json generato).

### 8.2 Adattamento al tipo di dati

Legge `design/fase-5-analisi/piano-analisi.json` → campo `paradigm` → attiva il modulo appropriato:

**Modulo Quantitativo** (MOD-QN1-4):
- Guida costruzione codebook numerico (variabili, scale, coding)
- Template matrice dati `.xlsx` con header pre-compilati da piano-analisi.json
- Checklist qualità dati: valori mancanti, outlier, range plausibili
- Verifica completezza rispetto ai criteri go/no-go da piano-analisi.json

**Modulo Qualitativo** (MOD-Q1-4):
- Guida alla trascrizione verbatim (formato standard: INT-001.md, INT-002.md)
- Template atlas codici (codice / definizione / esempio / anti-esempio)
- Memo analitico: dove documentare osservazioni e intuizioni durante il coding
- Saturazione teorica: checklist per valutare quando fermarsi

**Modulo Mixed-Methods** (MOD-MM):
- Entrambi i moduli in parallelo
- Guida alla sincronizzazione temporale dei dataset
- Tabella di integrazione: ID partecipante cross-referenziato tra dataset qual e quant

**Modulo Action Research / DBR** (MOD-AR, MOD-DBR):
- Journal di campo per ogni ciclo
- Template documentazione iterazioni (ciclo N: obiettivo → azione → osservazione → riflessione)

### 8.3 State file (`.collection-state.json`)

```json
{
  "paradigm": "MOD-QN1",
  "data_type": "quantitative",
  "collection_status": "in_progress",
  "participants": {
    "target": 42,
    "enrolled": 38,
    "dropout": 2,
    "complete": 0
  },
  "instruments_administered": [],
  "go_nogo_check": null,
  "last_updated": "ISO8601"
}
```

### 8.4 Output (handoff → data-analysis)

| File | Contenuto |
|------|-----------|
| `raccolta-dati/codebook.md` | Definizione variabili e coding |
| `raccolta-dati/matrice_dati.xlsx` | Dataset pulito (quant) |
| `raccolta-dati/trascrizioni/INT-*.md` | Trascrizioni (qual) |
| `raccolta-dati/atlas_codici.md` | Codebook qualitativo |
| `raccolta-dati/.collection-state.json` | Stato raccolta + go/no-go esito |

---

## 9. Skill: data-analysis

### 9.1 Attivazione

Invocata da `pipeline-regista` dopo che `data-collection` è completata.

### 9.2 Fase di conferma (obbligatoria)

Prima di procedere, legge `design/fase-5-analisi/piano-analisi.json` e ripropone le scelte chiave al ricercatore per conferma:

```
Ho trovato il piano di analisi definito in fase di progettazione:

1. Test pianificato: ANCOVA (controllando pre-test)
   → Confermi? Hai riscontrato problemi durante la raccolta che cambiano questo?

2. Strategia missing data: FIML
   → Quanti missing hai effettivamente? [X]% → la strategia è ancora appropriata?

3. Ipotesi pre-registrata: H1 = d ≥ 0.4
   → Vuoi aggiungere analisi esplorative non pre-registrate? (le dichiarerò come tali)

4. Software pianificato: JASP
   → Hai JASP disponibile? Oppure preferisci R / SPSS?
```

### 9.3 Guida per paradigma

**Quantitativo:**
- Statistiche descrittive: M, SD, range per variabile e gruppo
- Test di equivalenza baseline
- ANCOVA/t-test/HLM secondo piano confermato
- Effect size + IC 95% obbligatori
- Verifica assunzioni: normalità, omoschedasticità, sfericità (se misure ripetute)
- Suggerisce test non parametrici se assunzioni violate e campione piccolo

**Qualitativo:**
- Guida step-by-step Thematic Analysis Riflessiva (Braun & Clarke 2021)
- Template per ogni tema: definizione + codici associati + citazioni esemplari
- Calcolo κ inter-rater (se secondo codificatore disponibile)
- Member checking: procedura guidata

**Mixed-Methods:**
- Prima componente prioritaria (es. quant se Explanatory Sequential)
- Poi componente secondaria
- Integrazione: joint display guidato
- Gestione divergenze: istruzioni per interpretare risultati contrastanti

**Action Research / DBR:**
- Analisi riflessiva per ciclo
- Pattern tra cicli: cosa migliora, cosa persiste
- Indicatori di cambiamento pratico

### 9.4 Output (handoff → preprint)

| File | Contenuto |
|------|-----------|
| `analisi/piano-analisi-confermato.json` | Piano aggiornato con scelte reali |
| `analisi/risultati_quantitativi.md` | Tabelle risultati in formato IMRAD |
| `analisi/risultati_qualitativi.md` | Temi + citazioni |
| `analisi/integrazione_mm.md` | Joint display (se MM) |
| `analisi/.analysis-state.json` | Stato analisi |

---

## 10. Skill: preprint

### 10.1 Attivazione

Invocata da `pipeline-regista` dopo `data-analysis` completata.

### 10.2 Selezione template

Il template del preprint dipende da **due variabili**: paradigma + dominio di ricerca.

**Per paradigma:**

| Paradigma | Struttura documento |
|-----------|---------------------|
| QN (quasi-exp, RCT, survey) | IMRAD standard: Intro → Methods → Results → Discussion |
| Q (fenomenologia, GT, etnografia) | IMRAD qualitativo: Intro → Approach → Findings → Discussion (no Results numerico) |
| MM | IMRAD misto: sezione Methods con due sotto-sezioni; Results dual; Discussion integrata |
| AR | Formato ciclico: Background → Cicli (1...N) → Riflessioni trasversali → Implicazioni |
| DBR | Formato iterativo: Problema → Principi design → Iterazioni → Efficacy → Contributo teorico |

**Per piattaforma di destinazione:**

| Piattaforma | Dominio | Requisiti specifici |
|-------------|---------|---------------------|
| **arXiv** | Ed-Tech, informatica educativa, AI | Formato LaTeX o PDF; sezione cs.AI o cs.CY |
| **Zenodo** | Tutti i domini | PDF o Word; metadati DOI; licenza CC obbligatoria |
| **Open Research Europe** | Ricerca finanziata Horizon EU | Peer review aperta; dati FAIR; Data Availability statement |
| **SSRN** | Scienze sociali, psicologia, educazione | Word o PDF; abstract strutturato |
| **EdArXiv** | Educazione, didattica | PDF; abstract 150-250 parole |
| **PsyArXiv** | Psicologia, psicopedagogia | Formato APA; open materials badge |

La skill chiede:
1. *"Per quale piattaforma stai preparando il preprint?"*
2. *"Il lavoro è finanziato da un grant Horizon EU?"* (→ Open Research Europe obbligatorio se sì)
3. *"Vuoi includere i dati grezzi come supplemento?"*

### 10.3 Struttura guidata

Genera `preprint/preprint_bozza.md` sezione per sezione:
- Legge i file di output da ogni fase (prisma_synthesis.md, protocollo_ricerca.md, risultati_*.md)
- Pre-compila le sezioni con i dati già raccolti
- Chiede input solo dove mancano decisioni autoriali (interpretazione, limitazioni, implicazioni)
- Guardrail anti-allucinazione: tutte le citazioni da `hybrid_rag.py query` o `[CITARE: da verificare]`

### 10.4 Checklist pre-submission (per piattaforma)

Genera `preprint/submission_checklist.md` con checklist specifica per la piattaforma target.

**Esempio per Zenodo:**
- [ ] DOI richiesto (Zenodo assegna DOI automaticamente)
- [ ] Licenza selezionata (CC BY 4.0 raccomandato per open access)
- [ ] Metadati compilati: titolo, autori, keywords, dominio
- [ ] Data Availability Statement incluso nel documento
- [ ] Affiliazioni istituzionali verificate
- [ ] ORCID autori incluso se disponibile

---

## 11. Wiki e hybrid-rag: Quando Usare Cosa

### 11.1 Flusso di scrittura (quando ogni skill alimenta la memoria)

| Momento | Sistema | Azione | Comando |
|---------|---------|--------|---------|
| Prima di PRISMA Fase 1 | Wiki | Query conoscenza pre-esistente | `wiki.py query --q "PICO topic" --k 5` |
| Dopo PRISMA Fase 4 | Wiki | Ingest entity pages (una per paper) | `wiki.py ingest --pages entity-*.tmp` |
| Dopo PRISMA Fase 4 | hybrid-rag | Index paper per retrieval RAG | `hybrid_rag.py index-prisma eligibility_prisma.json` |
| Dopo PRISMA Fase 6 | Wiki | Ingest synthesis page | `wiki.py ingest --pages synthesis.tmp` |

### 11.2 Flusso di lettura (quando ogni skill interroga la memoria)

| Skill | Sistema | Cosa cerca | Comando |
|-------|---------|-----------|---------|
| research-design | Wiki | Framework teorici cross-progetto | `wiki.py query --q "framework [dominio]" --k 3` |
| data-collection | Wiki | Strumenti usati in letteratura simile | `wiki.py query --q "strumenti [costrutto]" --k 3` |
| data-analysis | Wiki | Effect size di riferimento dalla letteratura | `wiki.py query --q "effect size [intervento]" --k 3` |
| preprint | hybrid-rag | Chunks per ogni citazione | `hybrid_rag.py query "[costrutto]" --n 3` |
| preprint | Wiki | Sintesi cross-progetto per discussione | `wiki.py query --q "[tema discussione]" --k 3` |

### 11.3 Struttura delle entity pages (wiki-works/{proj}/entities/)

```markdown
# [Titolo Paper]

**Autori:** [lista] | **Anno:** YYYY | **DOI:** [doi]
**Database origine:** Semantic Scholar / PubMed / arXiv / ...
**Outcome:** [outcome principale] | **Effect size:** d=[X]
**Framework:** [framework teorico]
**Strumenti:** [lista strumenti usati]
**Campione:** N=[X], [livello scolastico], [paese]
**Qualità:** [punteggio 0-6]

## Abstract
[abstract completo o estratto]

## Note per il progetto
[note specifiche sulla rilevanza per questa ricerca]
```

### 11.4 Configurazione wiki workspace

`wiki/wiki.config.json` → campo `"workspace"` = path assoluto alla directory dati (es. `C:/Users/nome/Documents/wiki-data`).

Il path è **esterno** a `{project-root}/` e sopravvive alla chiusura del progetto.

---

## 12. MCP Server — Stato Attuale e Gap

### 12.1 Esistenti

| Server | File | Database |
|--------|------|----------|
| CORE | `mcp-servers/core/server.py` | CORE (open access aggregator) |
| DOAJ | `mcp-servers/doaj/server.py` | Directory of Open Access Journals |
| ERIC | `mcp-servers/eric/server.py` | Education Resources Information Center |
| OpenAIRE | `mcp-servers/openaire/server.py` | European open research |
| Zenodo | `mcp-servers/zenodo/server.py` | CERN open repository |

### 12.2 Mancanti (da implementare)

| Server | Database | Priorità | Note |
|--------|----------|----------|------|
| **Semantic Scholar** | 200M+ paper, citation graph | ALTA | API gratuita, buona copertura Ed-Tech |
| **PubMed** | MEDLINE, biomedical | ALTA | Essenziale per psicopedagogia clinica |
| **arXiv** | Preprint tecnici e educazione | MEDIA | Rilevante per Ed-Tech e AI in education |

### 12.3 Struttura standard dei server MCP

Tutti i server seguono lo stesso pattern (vedi `mcp-servers/eric/server.py` come riferimento):
- Tool: `search_{database}(query, limit, filters)` → lista paper con metadati
- Tool: `get_{database}_paper(id)` → dettaglio singolo paper
- Output format: compatibile con `eligibility_prisma.json` schema

---

## 13. Roadmap Implementazione

### Fase A — Fondamenta (prerequisito per tutto)
1. **pipeline-regista** — skill interattiva (senza regista, il sistema non ha punto di ingresso)
2. **MCP Semantic Scholar** — il database più usato in Ed-Tech
3. **MCP PubMed** — essenziale per psicopedagogia
4. Aggiornare **pipeline-ricerca** → deprecarlo a favore di pipeline-regista

### Fase B — Completare research-design MVP
5. **research-design/SKILL.md** — secondo il piano `2026-06-01-research-design-skill-mvp.md`

### Fase C — Nuove skill
6. **data-collection** — adattivo per paradigma
7. **data-analysis** — con fase di conferma
8. **preprint** — con template per paradigma × piattaforma

### Fase D — Estensione paradigmi
9. **research-design MOD-QN2-4** (RCT, single-subject, survey)
10. **research-design MOD-Q1-4** (fenomenologia, GT, etnografia, narrativo)
11. **research-design MOD-MM, MOD-AR, MOD-DBR**

### Fase E — MCP supplementari
12. **MCP arXiv**

---

## 14. Principi di Design (non negoziabili)

1. **Zero perdita di dati tra sessioni:** ogni skill aggiorna il proprio state file alla fine di ogni interazione significativa, anche se interrotta a metà.

2. **Autonomia dello spazio di progetto:** tutto il materiale di ricerca vive nella cartella di progetto. I path (project_root, wiki_workspace) sono configurabili e registrati in `.project-state.json` — nessun path hardcoded nel codice delle skill.

3. **Regista come unico punto di ingresso:** il ricercatore invoca sempre `pipeline-regista`. Le skill individuali possono essere invocate direttamente per uso avanzato, ma il flusso normale passa dal regista.

4. **Tracciabilità completa:** project-log.md documenta ogni decisione rilevante con timestamp, rationale e chi l'ha presa (ricercatore vs sistema). È append-only — mai cancellare entry.

5. **Adattamento al paradigma:** ogni skill che dipende dalla scelta metodologica legge `paradigm` da `.project-state.json` e adatta il proprio comportamento senza chiedere di nuovo.

6. **Guardrail anti-allucinazione:** nessuna skill cita mai letteratura senza fonte RAG verificata. Tutte le citazioni non recuperate via RAG vanno marchiate `[CITARE: autore/anno da verificare]`.
