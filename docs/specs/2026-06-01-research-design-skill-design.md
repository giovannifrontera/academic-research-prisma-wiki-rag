# Design Spec — `research-design` skill

**Data:** 2026-06-01 (aggiornato 2026-06-01)
**Sostituisce:** `skills/educational-pilot-design/SKILL.md`
**Stato:** Approvato — pronto per implementazione

---

## 1. Problema e motivazione

`educational-pilot-design` presuppone la risposta prima ancora che il ricercatore abbia formulato la domanda: guida direttamente verso un design quasi-sperimentale, ignorando tutti gli altri paradigmi delle scienze dell'educazione.

L'obiettivo è trasformarla in un **framework decisionale completo** che:
1. Guida il ricercatore nella scelta del paradigma più adatto alla sua domanda
2. Copre tutti i paradigmi rilevanti (qualitativo, quantitativo, misto, ricerca-azione, DBR)
3. Garantisce tracciabilità rigorosa su progetti che si estendono su settimane o mesi
4. Si integra nella pipeline completa PRISMA → preprint come fase coerente
5. Massimizza il contenuto esistente (buono) aggiungendo solo ciò che manca

---

## 2. Principio architetturale fondamentale: spazio progetto unificato

**Il progetto di ricerca nasce in PRISMA Fase 0 e vive in un'unica cartella per l'intera durata del ciclo PRISMA → design → raccolta → analisi → preprint.**

Ogni skill della pipeline legge e scrive nella stessa cartella root del progetto, in sottocartelle dedicate. Nessuna skill ricrea la struttura da zero.

### Struttura cartella progetto (creata da PRISMA Fase 0)

```
mio-progetto-ricerca/                  ← creata in PRISMA Fase 0
│
├── .project-state.json                ← MASTER STATE — traccia l'intera pipeline
├── project-log.md                     ← log unificato append-only (tutte le skill)
│
├── prisma/                            ← FASE: prisma-review
│   ├── prisma_state.json
│   ├── prisma_log.md
│   ├── raw_*.json
│   ├── screening_prisma.json
│   ├── eligibility_prisma.json
│   ├── prisma_synthesis.md
│   ├── prisma_bibliography.md
│   └── pdf_manuali/
│
├── rag_db/                            ← FASE: hybrid-rag
│
├── design/                            ← FASE: research-design
│   ├── .research-state.json
│   ├── protocollo_ricerca.md
│   ├── fase-0-paradigma/
│   │   └── paradigma-selection.md
│   ├── fase-1-framework/
│   │   └── framework-ipotesi.md
│   ├── fase-2-design/
│   │   ├── design-ricerca.md
│   │   └── power-analysis.md
│   ├── fase-3-strumenti/
│   │   └── strumenti-valutazione.md
│   ├── fase-4-procedura/
│   │   ├── timeline.md
│   │   └── consenso-informato.md
│   ├── fase-5-analisi/
│   │   ├── piano-analisi.md
│   │   └── piano-analisi.json           ← handoff verso data-analysis
│   └── fase-6-preprint/
│       ├── preprint-bozza.md
│       └── preprint-target.md           ← template OSF/Zenodo/Preprints.org
│
├── raccolta-dati/                     ← FASE: instruments-admin (da creare)
│   ├── dati/
│   │   ├── grezzi/                      ← mai modificare
│   │   ├── elaborati/
│   │   └── strumenti/
│   └── sessioni/
│
├── analisi/                           ← FASE: data-analysis (da creare)
│   ├── output/
│   ├── figure/
│   └── report-analisi.md
│
└── preprint/                          ← output finale
    ├── preprint-bozza.md
    ├── refs.bib
    └── output/
        ├── preprint.pdf
        └── preprint.docx
```

### `.project-state.json` — master state dell'intera pipeline

Creato in PRISMA Fase 0, aggiornato da ogni skill alla fine della propria fase:

```json
{
  "progetto": "review-chatbot-metacognizione",
  "ricercatore": "Nome Cognome",
  "data_avvio": "2026-06-01",
  "ultima_modifica": "2026-06-08",
  "fase_workflow_corrente": "research-design",
  "fasi_workflow": {
    "prisma":            { "stato": "completata",   "data_completamento": "2026-06-01" },
    "hybrid-rag":        { "stato": "completata",   "data_completamento": "2026-06-01" },
    "research-design":   { "stato": "in-corso",     "data_avvio": "2026-06-08" },
    "instruments-admin": { "stato": "non-avviata",  "data_avvio": null },
    "data-analysis":     { "stato": "non-avviata",  "data_avvio": null },
    "preprint":          { "stato": "non-avviata",  "data_avvio": null }
  },
  "percorsi": {
    "root": "./",
    "prisma": "./prisma/",
    "rag_db": "./rag_db/",
    "design": "./design/",
    "raccolta_dati": "./raccolta-dati/",
    "analisi": "./analisi/",
    "preprint": "./preprint/"
  }
}
```

### `project-log.md` — diario unificato dell'intero progetto

Un solo file append-only per tutte le skill. Ogni voce include la skill che l'ha scritta:

```markdown
# Project Log — review-chatbot-metacognizione

---
## [2026-06-01] [prisma-review] Fase 0 — Setup progetto
**Decisione:** PICO definito. Database: ERIC, Semantic Scholar, OpenAIRE.
**Rationale:** Ambito educativo + AI. Range 2018-2025.

---
## [2026-06-01] [prisma-review] Fase 4 completata
**Risultato:** 14 paper inclusi. Effect size medio d=0.52.
**Handoff:** prisma_synthesis.md → OUTPUT PER PILOT STUDY compilato.

---
## [2026-06-08] [research-design] Fase 0 — Selezione paradigma
**Decisione:** Quasi-sperimentale pre-post con gruppo di controllo (MOD-QN1).
**Rationale:** 8 studi simili in PRISMA. Classi naturali disponibili.
**Alternative scartate:** RCT (randomizzazione impossibile).
```

---

## 3. Implicazioni sulle skill esistenti

### 3.1 PRISMA Fase 0 — aggiornamenti necessari

La Fase 0 di `prisma-review` deve essere estesa per:

1. **Chiedere il nome del progetto** (non solo la cartella della review)
2. **Creare la struttura completa** delle cartelle (root + tutte le sottocartelle)
3. **Inizializzare `.project-state.json`** con tutte le fasi a `non-avviata`
4. **Inizializzare `project-log.md`** con intestazione progetto
5. **Scrivere i propri file in `prisma/`** invece che nella root

> **Compatibilità retroattiva:** Se `.project-state.json` non esiste ma `prisma_state.json` sì (progetto vecchio), `research-design` crea `.project-state.json` deducendo lo stato dalla presenza dei file esistenti e aggiunge una nota in `project-log.md`.

### 3.2 `pipeline-ricerca` — aggiornamenti necessari

1. Sostituire `educational-pilot-design` con `research-design`
2. Documentare `.project-state.json` come artefatto centrale
3. Aggiornare i percorsi file (ora in sottocartelle)
4. Aggiungere `instruments-admin` e `data-analysis` al flusso
5. Documentare `piano-analisi.json` come handoff verso `data-analysis`

### 3.3 `hybrid-rag` — nessuna modifica necessaria

Già scrive in `rag_db/` relativo alla cartella di lavoro. Funziona correttamente se invocato dalla root del progetto.

---

## 4. Architettura della skill `research-design`

**Nome skill:** `research-design`
**File:** `skills/research-design/SKILL.md`
**Trigger description:**
> Usa quando occorre progettare uno studio di ricerca nelle scienze dell'educazione o in ambiti correlati. Fa parte della pipeline PRISMA → preprint: legge il contesto da `prisma/prisma_synthesis.md` e scrive in `design/`. Guida la scelta del paradigma (qualitativo, quantitativo, misto, ricerca-azione, DBR) e la progettazione completa fino al preprint. NON usare per revisioni sistematiche (usa prisma-review).

### Struttura interna SKILL.md

```
SKILL.md
├── [AVVIO]
│   ├── Verifica .project-state.json (root progetto)
│   ├── Ripresa sessione da design/.research-state.json
│   ├── Lettura prisma/prisma_synthesis.md
│   └── Aggiorna .project-state.json: research-design → in-corso
├── [FASE 0]     Decision tree — selezione paradigma
├── [SEZIONI COMUNI]
│   ├── Etica e normativa (MIUR, GDPR, BES/DSA)
│   ├── Preprint e disseminazione
│   └── Handoff: aggiorna .project-state.json + project-log.md
└── [MODULI PARADIGMA]
    ├── MOD-QN1  Quasi-sperimentale / Pilot
    ├── MOD-QN2  RCT
    ├── MOD-QN3  Single-subject
    ├── MOD-QN4  Survey / Correlazionale
    ├── MOD-Q1   Fenomenologia
    ├── MOD-Q2   Grounded Theory
    ├── MOD-Q3   Etnografia
    ├── MOD-Q4   Ricerca Narrativa
    ├── MOD-MM   Mixed-Methods
    ├── MOD-AR   Ricerca-Azione (PAR)
    └── MOD-DBR  Design-Based Research
```

---

## 5. Stato per-fase: `design/.research-state.json`

```json
{
  "fase_corrente": 3,
  "fasi_completate": [0, 1, 2],
  "paradigma": "quasi-sperimentale",
  "modulo": "MOD-QN1",
  "livello": "sec-II",
  "profilo": "Ed-Tech",
  "framework": "SRL/Zimmerman",
  "n_previsto": 40,
  "prisma_file": "../prisma/prisma_synthesis.md",
  "rag_disponibile": true,
  "dati_raccolti": false,
  "preregistrazione_osf": null,
  "ultima_modifica": "2026-06-08",
  "fasi": {
    "0": { "completata": true,  "data": "2026-06-08", "paradigma_scelto": "quasi-sperimentale" },
    "1": { "completata": true,  "data": "2026-06-08", "framework": "SRL/Zimmerman" },
    "2": { "completata": true,  "data": "2026-06-08", "design": "pre-post control group", "n_previsto": 40 },
    "3": { "completata": false, "data": null, "strumenti_scelti": [] }
  }
}
```

### Protocollo aggiornamento

| Momento | File aggiornato |
|---------|----------------|
| Inizio skill | Leggi `.project-state.json` (root) + `design/.research-state.json` |
| Fine ogni fase | 1) `design/.research-state.json` 2) `project-log.md` 3) chiedi conferma |
| Fine skill | `.project-state.json`: research-design → completata |
| Interruzione | Appendi a `project-log.md`: stato + prossimo passo + data |

### Ripresa di sessione

```
Ho trovato .project-state.json e design/.research-state.json.
───────────────────────────────────────────
Progetto:        review-chatbot-metacognizione
Pipeline:        PRISMA ✓  RAG ✓  Design ▶  Raccolta □  Analisi □
Paradigma:       quasi-sperimentale (MOD-QN1)
Fase design:     3 — Strumenti e misure
Fasi ok:         0 ✓  1 ✓  2 ✓
Ultima sessione: 2026-06-08
───────────────────────────────────────────
Vuoi riprendere dalla Fase 3?
```

---

## 6. Fase 0 — Decision tree

### 0.0 — Verifica spazio progetto

1. Cerca `.project-state.json` nella directory corrente
   - Trovato → leggi, mostra stato pipeline, chiedi conferma ripresa
   - Non trovato → avvisa e chiedi percorso root progetto
2. Crea `design/` se non esiste
3. Cerca `prisma/prisma_synthesis.md` (fallback: `prisma_synthesis.md` in root per retrocompatibilità)

### 0.1 — Lettura contesto PRISMA (automatica)

Estrae da `prisma/prisma_synthesis.md`: stato conoscenza, gap, effect size aggregati, RQ aperte, framework dominante. Dichiara il contesto prima di procedere con le domande.

### 0.2 — 5 domande di routing (una alla volta)

**D1 — Obiettivo principale:**
> a) Comprendere — esplorare fenomeno, significati, esperienze vissute
> b) Misurare — testare effetto intervento, quantificare outcome
> c) Migliorare — cambiare pratica attraverso la ricerca stessa
> d) Progettare — creare e raffinare iterativamente uno strumento/ambiente

**D2 — Stato della conoscenza** *(saltata se PRISMA disponibile)*:
> a) Poco/nulla — fenomeno emergente
> b) Abbastanza — gap importanti
> c) Molto — voglio confermare in nuovo contesto

**D3 — Natura dell'outcome:**
> a) Numeri e misure
> b) Significati e interpretazioni
> c) Entrambi (triangolazione)

**D4 — Vincoli pratici** *(solo se D1=b o D1=d)*:
> a) N ≥ 20/gruppo + randomizzazione → RCT
> b) N ≥ 10/gruppo + classi naturali → Quasi-sperimentale
> c) N < 10 o singolo caso → Single-subject
> d) N grande, nessun intervento → Survey

**D5 — Sequenza** *(solo se D3=c)*:
> a) Prima misuro, poi capisco → Explanatory Sequential
> b) Prima comprendo, poi confermo → Exploratory Sequential
> c) In parallelo → Convergent Parallel

### Tabella di routing

| D1 | D2 | D3 | D4 | D5 | Modulo |
|----|----|----|----|----|--------|
| b | * | a | a | — | MOD-QN2 (RCT) |
| b | * | a | b | — | MOD-QN1 (Quasi-sperimentale) |
| b | * | a | c | — | MOD-QN3 (Single-subject) |
| b | * | a | d | — | MOD-QN4 (Survey) |
| a | a | b | — | — | MOD-Q1 (Fenomenologia) |
| a | b | b | — | — | MOD-Q2 (Grounded Theory) |
| a | * | b | — | — | MOD-Q3/Q4 † |
| * | * | c | — | a | MOD-MM Explanatory |
| * | * | c | — | b | MOD-MM Exploratory |
| * | * | c | — | c | MOD-MM Convergent |
| c | * | * | — | — | MOD-AR (Ricerca-Azione) |
| d | * | * | — | — | MOD-DBR |

† Domanda aggiuntiva tra MOD-Q3/Q4: pratiche collettive/contesto (etnografia) vs. storie individuali (narrativa).

### 0.3 — Output raccomandazione

```
RACCOMANDAZIONE DESIGN
───────────────────────────────────────────
Paradigma:    [nome]
Modulo:       [MOD-XX]
Motivazione:  [2-3 frasi basate su D1-D5 + PRISMA]
Alternative:  [1-2 con trade-off sintetico]
Riferimento:  [Creswell & Creswell 2018; specifico per paradigma]
───────────────────────────────────────────
Confermi questo design o vuoi esplorare un'alternativa?
```

Dopo conferma: scrive `design/fase-0-paradigma/paradigma-selection.md`, aggiorna `design/.research-state.json`, aggiorna `.project-state.json`, appende a `project-log.md`.

---

## 7. Moduli paradigma (fasi 1-6)

Ogni modulo segue le stesse 6 fasi. Il contenuto varia, la struttura no.

| Modulo | Contenuto distintivo | Riuso da skill esistente |
|--------|---------------------|--------------------------|
| **MOD-QN1** Quasi-sperimentale | H1/H0, go/no-go, stopping rules, power analysis G*Power, ANCOVA | ~90% (contenuto attuale) |
| **MOD-QN2** RCT | Sequence generation, allocation concealment, blinding, CONSORT 2010, ITT | ~50% |
| **MOD-QN3** Single-subject | Design A-B-A-B, baseline criteria, Tau-U, PND, analisi visiva | Nuovo |
| **MOD-QN4** Survey | Campionamento, margine errore, tasso risposta, regressione, analisi fattoriale | Nuovo |
| **MOD-Q1** Fenomenologia | IPA/Giorgi, bracketing (epoché), N=6-12 purposive, 6 steps IPA | Nuovo |
| **MOD-Q2** Grounded Theory | Theoretical sampling, saturazione, memo writing, coding open→axial→selective | Nuovo |
| **MOD-Q3** Etnografia | Accesso al campo, note campo strutturate, thick description, ethics ongoing | Nuovo |
| **MOD-Q4** Ricerca Narrativa | Life history, analisi struttura/contenuto/performance (Riessman) | Nuovo |
| **MOD-MM** Mixed-Methods | Joint display, meta-inferenze, gestione divergenze | ~60% |
| **MOD-AR** Ricerca-Azione | Cicli PAR, consenso comunità, validazione collaborativa, report riflessivo | Nuovo |
| **MOD-DBR** Design-Based Research | Iterazioni micro/macro, principi di design emergenti, changelog strumento | Nuovo |

### Struttura dati per paradigma (in `raccolta-dati/dati/`)

| Paradigma | `grezzi/` | `elaborati/` |
|-----------|-----------|-------------|
| QN1/QN2 | `pre-test.csv`, `post-test.csv`, `covariate.csv`, `dropout-log.md` | `ancova-output.csv`, `effect-size.json`, `figures/` |
| QN3 | `misure-ripetute.csv`, `sessione-log.md` | `grafico-AB.png`, `tau-u.json` |
| QN4 | `risposte.csv`, `metadata-campione.csv` | `correlazioni.csv`, `regressione.json` |
| Q1/Q2/Q4 | `trascrizioni/`, `memo.md` | `codebook.md`, `temi/`, `diagramma-categorie.md` |
| Q3 | `note-osservazione/`, `documenti-istituzionali/` | `cronologia-eventi.md`, `mappa-relazioni.md` |
| AR | `cicli/ciclo-N/` (01-pianificazione, 02-attuazione, 03-osservazioni, 04-riflessione) | `sintesi-cicli.md` |
| DBR | `iterazioni/iter-N/` (design, implement, analyze, redesign) | `principi-design.md`, `changelog.md` |

---

## 8. Handoff tra skill

| Da | A | File | Contenuto |
|----|---|------|-----------|
| `prisma-review` | `research-design` | `prisma/prisma_synthesis.md` | Effect size, framework, RQ aperte, gap |
| `research-design` | `instruments-admin` | `design/fase-5-analisi/piano-analisi.json` | Paradigma, variabili, strumenti, formato dati |
| `research-design` | `data-analysis` | `design/fase-5-analisi/piano-analisi.json` | Piano analisi pre-specificato |
| `research-design` | `pandoc-export` | `design/fase-6-preprint/preprint-bozza.md` | Bozza preprint |
| tutte | tutte | `.project-state.json` | Stato globale pipeline |
| tutte | tutte | `project-log.md` | Decisioni e handoff |

### `piano-analisi.json`

```json
{
  "paradigma": "quasi-sperimentale",
  "modulo": "MOD-QN1",
  "variabili": {
    "dipendenti": ["MSLQ-SRL", "MSLQ-Motivazione"],
    "indipendente": "chatbot-intervento",
    "covariate": ["pre-test", "genere", "SES"]
  },
  "test_previsti": ["ANCOVA", "Cohen-d", "IC-95"],
  "missing_data_strategy": "multiple-imputation",
  "formato_dati": "CSV",
  "percorso_dati": "../raccolta-dati/dati/grezzi/",
  "alpha": 0.05,
  "software_consigliato": ["JASP", "R", "SPSS"]
}
```

---

## 9. Elementi trasversali

| Elemento | Implementazione |
|----------|-----------------|
| `design/.research-state.json` | Aggiornato fine ogni fase |
| `.project-state.json` | Aggiornato inizio e fine skill |
| `project-log.md` | Append ogni decisione con skill + data |
| Checkpoint utente | Prima di avanzare alla fase successiva |
| Guardrail anti-allucinazione | `[CITARE: da verificare]` sempre |
| Pre-registrazione OSF | Fase 2 per paradigmi quantitativi |
| Normativa italiana | MIUR, GDPR, L.104/92, L.170/2010 |

---

## 10. File da creare/modificare

| Azione | File | Priorità |
|--------|------|----------|
| CREA | `skills/research-design/SKILL.md` | P1 |
| CREA | `skills/research-design/references/` (riusa da educational-pilot-design) | P1 |
| CREA | `skills/research-design/imrad-protocol-paper.md` (riusa) | P1 |
| CREA | `skills/research-design/imrad-results-paper.md` (riusa) | P1 |
| MODIFICA | `skills/prisma-review/SKILL.md` — Fase 0: crea struttura progetto completa | P1 |
| MODIFICA | `skills/pipeline-ricerca/SKILL.md` — aggiorna flusso e percorsi | P1 |
| DEPRECA | `skills/educational-pilot-design/SKILL.md` — aggiunge nota deprecazione | P2 |

---

*Spec approvata — 2026-06-01*
*Prossimo step: writing-plans per piano implementazione task-by-task*
