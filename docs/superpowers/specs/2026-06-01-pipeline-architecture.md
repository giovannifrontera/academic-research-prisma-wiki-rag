# Pipeline Ricerca Accademica — Architettura Completa

**Data:** 2026-06-01  
**Versione:** 1.0  
**Sostituisce:** tutti i riferimenti architetturali in `pipeline-ricerca/SKILL.md`

---

## 1. Visione

Un sistema di skill coordinate che guida un ricercatore in scienze dell'educazione dall'identificazione delle domande di ricerca fino alla pubblicazione del preprint — senza mai perdere il filo, anche su sessioni separate distanziate di settimane.

**Principio fondamentale:** l'intera ricerca vive in uno **spazio di progetto autonomo** creato in PRISMA Fase 0. Ogni skill legge e scrive in quello spazio. Il ricercatore non deve mai ricordare "dove eravamo rimasti" — lo fa il sistema.

---

## 2. Architettura a Skill Coordinate

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
    Semantic Scholar · PubMed · arXiv
    CORE · DOAJ · ERIC · OpenAIRE · Zenodo
         ↓
[prisma-review]
    PICO + RQ + ipotesi
    selezione e screening articoli
    sintesi sistematica
         ↓
[hybrid-rag + wiki] ←─────────────────────────────────────┐
    MEMORIA PERSISTENTE CROSS-SESSIONE                     │
    indicizzazione articoli selezionati                    │ ogni skill
    query semantica durante tutte le fasi                  │ legge e scrive
    export entità su wiki per navigazione                  │ su wiki/rag
         ↓                                                 │
[research-design]  ────────────────────────────────────→  ┤
    Fase 0: scelta paradigma (decision tree)               │
    Fase 1-6: framework, design, strumenti,                │
              procedura, piano analisi, preprint bozza     │
         ↓                                                 │
[data-collection]  ────────────────────────────────────→  ┤
    adattato al tipo di dati (paradigma scelto)            │
    quantitativo: matrice dati, codebook numerico          │
    qualitativo: trascrizioni, atlas codici, memo          │
    mixed: entrambi in parallelo                           │
         ↓                                                 │
[data-analysis]    ────────────────────────────────────→  ┤
    legge piano-analisi.json da research-design            │
    ri-propone domande di conferma prima di procedere      │
    suggerisce indicatori e metodi per il paradigma        │
    guida interpretazione risultati                        │
         ↓                                                 │
[preprint]         ────────────────────────────────────→  ┘
    template adattato a paradigma + dominio di ricerca
    piattaforma target: arXiv, Zenodo, ORE, SSRN
    produce documento pronto per submission
         ↓
[pandoc-export]
    conversione Word / PDF
```

---

## 3. Spazio di Progetto (creato da PRISMA Fase 0)

Ogni ricerca ha una cartella radice dedicata. **Tutta la ricerca vive lì.** Il ricercatore non deve mai copiare file tra cartelle.

```
{project-root}/                          ← creato da pipeline-regista o prisma-review Fase 0
│
├── .project-state.json                  ← MASTER STATE — stato di ogni fase
├── project-log.md                       ← AUDIT LOG append-only — ogni sessione scrive qui
│
├── prisma/                              ← output di prisma-review
│   ├── prisma_state.json
│   ├── prisma_log.md
│   ├── eligibility_prisma.json
│   ├── extraction_table.json
│   ├── prisma_synthesis.md              ← handoff critico → research-design
│   └── prisma_bibliography.md
│
├── rag_db/                              ← database RAG (hybrid-rag)
│   └── config.json
│
├── wiki/                                ← spazio wiki (OpenClaw)
│   └── [entity pages per paper + synthesis]
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

## 4. Master State File (`.project-state.json`)

Aggiornato da ogni skill al completamento di ogni fase. Letto da `pipeline-regista` per sapere dove si è arrivati.

```json
{
  "project_name": "string",
  "project_root": "/path/assoluto/al/progetto",
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

## 5. Audit Log (`project-log.md`)

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

## 6. Skill Regista (pipeline-regista)

### 6.1 Ruolo

`pipeline-regista` è la **porta d'ingresso** al sistema. Il ricercatore non deve sapere quale skill invocare — lo fa il regista in base allo stato del progetto.

### 6.2 Comportamento all'avvio

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

### 6.3 Comandi disponibili per il ricercatore

| Comando | Azione |
|---------|--------|
| `stato` | mostra .project-state.json in formato leggibile |
| `log` | mostra le ultime N entry di project-log.md |
| `vai a [fase]` | salta a una fase specifica (con conferma se ci sono dipendenze non soddisfatte) |
| `riepilogo [fase]` | riassume i risultati di una fase completata |
| `prossimo passo` | identifica la prossima azione da compiere |
| `esporta` | invoca pandoc-export sul file preprint_bozza.md |

### 6.4 Gestione dipendenze tra fasi

Il regista verifica le dipendenze prima di consentire l'ingresso in una fase:

| Fase | Dipendenze obbligatorie | Dipendenze opzionali |
|------|------------------------|---------------------|
| `rag` | `prisma` completata | — |
| `research-design` | `prisma` completata | `rag` (abilita query) |
| `data-collection` | `research-design` Fase 5 completata | — |
| `data-analysis` | `data-collection` completata | — |
| `preprint` | `data-analysis` completata | — |

---

## 7. Skill: data-collection

### 7.1 Attivazione

Invocata da `pipeline-regista` dopo che `research-design` ha completato la Fase 5 (piano-analisi.json generato).

### 7.2 Adattamento al tipo di dati

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

### 7.3 State file (`.collection-state.json`)

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

### 7.4 Output (handoff → data-analysis)

| File | Contenuto |
|------|-----------|
| `raccolta-dati/codebook.md` | Definizione variabili e coding |
| `raccolta-dati/matrice_dati.xlsx` | Dataset pulito (quant) |
| `raccolta-dati/trascrizioni/INT-*.md` | Trascrizioni (qual) |
| `raccolta-dati/atlas_codici.md` | Codebook qualitativo |
| `raccolta-dati/.collection-state.json` | Stato raccolta + go/no-go esito |

---

## 8. Skill: data-analysis

### 8.1 Attivazione

Invocata da `pipeline-regista` dopo che `data-collection` è completata.

### 8.2 Fase di conferma (obbligatoria)

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

### 8.3 Guida per paradigma

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

### 8.4 Output (handoff → preprint)

| File | Contenuto |
|------|-----------|
| `analisi/piano-analisi-confermato.json` | Piano aggiornato con scelte reali |
| `analisi/risultati_quantitativi.md` | Tabelle risultati in formato IMRAD |
| `analisi/risultati_qualitativi.md` | Temi + citazioni |
| `analisi/integrazione_mm.md` | Joint display (se MM) |
| `analisi/.analysis-state.json` | Stato analisi |

---

## 9. Skill: preprint

### 9.1 Attivazione

Invocata da `pipeline-regista` dopo `data-analysis` completata.

### 9.2 Selezione template

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

### 9.3 Struttura guidata

Genera `preprint/preprint_bozza.md` sezione per sezione:
- Legge i file di output da ogni fase (prisma_synthesis.md, protocollo_ricerca.md, risultati_*.md)
- Pre-compila le sezioni con i dati già raccolti
- Chiede input solo dove mancano decisioni autoriali (interpretazione, limitazioni, implicazioni)
- Guardrail anti-allucinazione: tutte le citazioni da `hybrid_rag.py query` o `[CITARE: da verificare]`

### 9.4 Checklist pre-submission (per piattaforma)

Genera `preprint/submission_checklist.md` con checklist specifica per la piattaforma target.

**Esempio per Zenodo:**
- [ ] DOI richiesto (Zenodo assegna DOI automaticamente)
- [ ] Licenza selezionata (CC BY 4.0 raccomandato per open access)
- [ ] Metadati compilati: titolo, autori, keywords, dominio
- [ ] Data Availability Statement incluso nel documento
- [ ] Affiliazioni istituzionali verificate
- [ ] ORCID autori incluso se disponibile

---

## 10. Ruolo di Wiki + RAG come Memoria Persistente

### 10.1 Cosa viene memorizzato e quando

| Fase | Cosa scrive su Wiki/RAG | Cosa legge da Wiki/RAG |
|------|------------------------|----------------------|
| prisma-review | Entity page per ogni paper incluso; synthesis page | — |
| research-design | Framework teorici selezionati; ipotesi formulate | Paper rilevanti per il framework scelto |
| data-collection | — | Strumenti usati in letteratura (per confronto) |
| data-analysis | — | Effect size dalla letteratura (per benchmarking) |
| preprint | — | Citazioni per ogni sezione |

### 10.2 Comandi RAG disponibili a tutte le skill

```bash
py hybrid_rag.py query "<costrutto>" --n 3          # recupera paper rilevanti
py hybrid_rag.py query "<strumento>" --filter year>=2020 --n 5
py hybrid_rag.py status                              # verifica stato indice
```

### 10.3 Wiki (OpenClaw)

- Entity page per ogni paper: titolo, autori, anno, abstract, outcome, framework, strumenti
- Synthesis page: mappa tematica risultati PRISMA
- Navigabile durante tutte le fasi successive

---

## 11. MCP Server — Stato Attuale e Gap

### 11.1 Esistenti

| Server | File | Database |
|--------|------|----------|
| CORE | `mcp-servers/core/server.py` | CORE (open access aggregator) |
| DOAJ | `mcp-servers/doaj/server.py` | Directory of Open Access Journals |
| ERIC | `mcp-servers/eric/server.py` | Education Resources Information Center |
| OpenAIRE | `mcp-servers/openaire/server.py` | European open research |
| Zenodo | `mcp-servers/zenodo/server.py` | CERN open repository |

### 11.2 Mancanti (da implementare)

| Server | Database | Priorità | Note |
|--------|----------|----------|------|
| **Semantic Scholar** | 200M+ paper, citation graph | ALTA | API gratuita, buona copertura Ed-Tech |
| **PubMed** | MEDLINE, biomedical | ALTA | Essenziale per psicopedagogia clinica |
| **arXiv** | Preprint tecnici e educazione | MEDIA | Rilevante per Ed-Tech e AI in education |

### 11.3 Struttura standard dei server MCP

Tutti i server seguono lo stesso pattern (vedi `mcp-servers/eric/server.py` come riferimento):
- Tool: `search_{database}(query, limit, filters)` → lista paper con metadati
- Tool: `get_{database}_paper(id)` → dettaglio singolo paper
- Output format: compatibile con `eligibility_prisma.json` schema

---

## 12. Roadmap Implementazione

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

## 13. Principi di Design (non negoziabili)

1. **Zero perdita di dati tra sessioni:** ogni skill aggiorna il proprio state file alla fine di ogni interazione significativa, anche se interrotta a metà.

2. **Autonomia dello spazio di progetto:** tutto vive nella cartella di progetto — nessun file fuori da essa, nessuna dipendenza da path assoluti hardcoded.

3. **Regista come unico punto di ingresso:** il ricercatore invoca sempre `pipeline-regista`. Le skill individuali possono essere invocate direttamente per uso avanzato, ma il flusso normale passa dal regista.

4. **Tracciabilità completa:** project-log.md documenta ogni decisione rilevante con timestamp, rationale e chi l'ha presa (ricercatore vs sistema). È append-only — mai cancellare entry.

5. **Adattamento al paradigma:** ogni skill che dipende dalla scelta metodologica legge `paradigm` da `.project-state.json` e adatta il proprio comportamento senza chiedere di nuovo.

6. **Guardrail anti-allucinazione:** nessuna skill cita mai letteratura senza fonte RAG verificata. Tutte le citazioni non recuperate via RAG vanno marchiate `[CITARE: autore/anno da verificare]`.
