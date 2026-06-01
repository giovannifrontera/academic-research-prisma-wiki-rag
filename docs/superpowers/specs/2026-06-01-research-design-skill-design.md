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
│   └── sessioni/                        ← log per sessione di somministrazione
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
**Decisione:** PICO definito. Database selezionati: ERIC, Semantic Scholar, OpenAIRE.
**Rationale:** Ambito educativo + AI. Range 2018-2025.

---
## [2026-06-01] [prisma-review] Fase 4 completata
**Risultato:** 14 paper inclusi. Effect size medio d=0.52.
**Handoff:** prisma_synthesis.md → OUTPUT PER PILOT STUDY compilato.

---
## [2026-06-08] [research-design] Fase 0 — Selezione paradigma
**Decisione:** Quasi-sperimentale pre-post con gruppo di controllo (MOD-QN1).
**Rationale:** PRISMA mostra 8 studi simili. Classi naturali disponibili.
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

La cartella di lavoro PRISMA è `<root>/prisma/`, non la root del progetto.

> **Compatibilità retroattiva:** Se `.project-state.json` non esiste ma `prisma_state.json` sì (progetto vecchio), `research-design` crea `.project-state.json` deducendo lo stato dalla presenza dei file esistenti e aggiunge una nota in `project-log.md`.

### 3.2 `pipeline-ricerca` — aggiornamenti necessari

1. Sostituire `educational-pilot-design` con `research-design`
2. Documentare `.project-state.json` come artefatto centrale
3. Aggiornare i percorsi file (ora in sottocartelle)
4. Aggiungere le fasi `instruments-admin` e `data-analysis` al flusso
5. Documentare `piano-analisi.json` come handoff verso `data-analysis`

### 3.3 `hybrid-rag` — nessuna modifica necessaria

Già scrive in `rag_db/` relativo alla cartella di lavoro. Funziona correttamente se invocato dalla root del progetto.

---

## 4. Architettura della skill `research-design`

**Nome skill:** `research-design`
**File:** `skills/research-design/SKILL.md`
**Trigger description:**
> Usa quando occorre progettare uno studio di ricerca nelle scienze dell'educazione o in ambiti correlati. Fa parte della pipeline PRISMA → preprint: legge il contesto da `prisma/prisma_synthesis.md` e scrive in `design/`. Guida la scelta del paradigma (qualitativo, quantitativo, misto, ricerca-azione, DBR) e la progettazione completa fino al preprint. NON usare per revisioni sistematiche (usa prisma-review).

### Struttura interna del file

```
SKILL.md
├── [AVVIO]
│   ├── Verifica .project-state.json (root progetto)
│   ├── Ripresa sessione da .research-state.json
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

### Compatibilità retroattiva

`educational-pilot-design` viene rinominata `research-design`. Se esiste `design/protocollo_ricerca.md` con Blocco STATO, la skill riprende da lì. Se il campo `paradigma` è assente, default a `quasi-sperimentale` (MOD-QN1).

---

## 5. Stato per-fase: `.research-state.json`

File nella sottocartella `design/`, traccia solo la fase di design:

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
    "1": { "completata": true,  "data": "2026-06-08", "framework": "SRL/Zimmerman", "rq_count": 2 },
    "2": { "completata": true,  "data": "2026-06-08", "design": "pre-post control group", "n_previsto": 40 },
    "3": { "completata": false, "data": null, "strumenti_scelti": [] }
  }
}
```

### Protocollo aggiornamento (regola ferrea)

| Momento | File aggiornato |
|---------|----------------|
| Inizio skill | Leggi `.project-state.json` (root) + `.research-state.json` (design/) |
| Fine ogni fase | 1) `design/.research-state.json` 2) `project-log.md` (root) 3) chiedi conferma |
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
Prossimo passo:  [da project-log.md]
───────────────────────────────────────────
Vuoi riprendere dalla Fase 3?
```

---

## 6. Fase 0 — Decision tree

### Struttura Fase 0

**0.0 — Verifica spazio progetto**

Prima azione assoluta:
1. Cerca `.project-state.json` nella directory corrente
   - Se trovato → leggi, mostra stato pipeline, chiedi conferma ripresa
   - Se non trovato → avvisa: *"Non trovo `.project-state.json`. Sei nella cartella root del progetto? Indicami il percorso."*
2. Cerca `design/` → se non esiste, creala
3. Cerca `prisma/prisma_synthesis.md` → se non trovato, cerca `prisma_synthesis.md` nella root (retrocompatibilità) o chiedi

**0.1 — Lettura contesto PRISMA (automatica)**
- Legge `prisma/prisma_synthesis.md` → estrae: stato conoscenza, gap, effect size aggregati, RQ aperte, framework dominante
- Se RAG disponibile: annota in `.research-state.json`
- Dichiara: *"Ho letto il contesto PRISMA. [Trovato: N paper inclusi, ES medio d=X, framework prevalente: Y, gap: Z]. Ora ti guido nella scelta del design."*

**0.2 — 5 domande di routing (una alla volta)**

D1 — Obiettivo principale:
> a) Comprendere (esplorare, significati, esperienze vissute)
> b) Misurare (testare effetto intervento, quantificare outcome)
> c) Migliorare (cambiare pratica attraverso la ricerca stessa)
> d) Progettare (creare e raffinare iterativamente uno strumento/ambiente)

D2 — Stato della conoscenza *(saltata se PRISMA disponibile)*:
> a) Poco/nulla — fenomeno emergente, voglio esplorare
> b) Abbastanza — gap importanti da colmare
> c) Molto — voglio confermare/misurare in nuovo contesto

D3 — Natura dell'outcome:
> a) Numeri e misure (punteggi, confronti statistici)
> b) Significati e interpretazioni (temi, categorie, narrazioni)
> c) Entrambi (triangolazione)

D4 — Vincoli pratici *(solo se D1=b o D1=d)*:
> a) N ≥ 20/gruppo + randomizzazione possibile → RCT
> b) N ≥ 10/gruppo + classi/gruppi naturali → Quasi-sperimentale
> c) N < 10 o singolo caso → Single-subject
> d) N grande, nessun intervento → Survey/correlazionale

D5 — Sequenza *(solo se D3=c)*:
> a) Prima misuro, poi capisco → Explanatory Sequential
> b) Prima comprendo, poi confermo → Exploratory Sequential
> c) In parallelo per triangolazione → Convergent Parallel

**Tabella di routing completa:**

| D1 | D2 | D3 | D4 | D5 | Modulo |
|----|----|----|----|----|--------|
| b | * | a | a | — | MOD-QN2 (RCT) |
| b | * | a | b | — | MOD-QN1 (Quasi-sperimentale) |
| b | * | a | c | — | MOD-QN3 (Single-subject) |
| b | * | a | d | — | MOD-QN4 (Survey) |
| a | a | b | — | — | MOD-Q1 (Fenomenologia) |
| a | b | b | — | — | MOD-Q2 (Grounded Theory) |
| a | * | b | — | — | MOD-Q3/Q4 † |
| * | * | c | — | a | MOD-MM (Explanatory Sequential) |
| * | * | c | — | b | MOD-MM (Exploratory Sequential) |
| * | * | c | — | c | MOD-MM (Convergent Parallel) |
| c | * | * | — | — | MOD-AR (Ricerca-Azione PAR) |
| d | * | * | — | — | MOD-DBR (Design-Based Research) |

† Tra MOD-Q3 (Etnografia) e MOD-Q4 (Ricerca Narrativa): domanda aggiuntiva
> "Sei interessato a pratiche collettive/contesto (etnografia) o a storie individuali (narrativa)?"

**0.3 — Output raccomandazione + salvataggio**

```
RACCOMANDAZIONE DESIGN
───────────────────────────────────────────
Paradigma:    Quasi-sperimentale pre-post con controllo
Modulo:       MOD-QN1
Motivazione:  Obiettivo misurare effetto intervento (D1=b);
              classi naturali disponibili (D4=b);
              PRISMA: 8 studi simili, ES medio d=0.52.
Alternative:  Mixed-Methods Explanatory (se vuoi capire il
              perché dei risultati); Action Research (se il
              docente è co-ricercatore).
Riferimento:  Creswell & Creswell (2018); Trinchero (2004)
───────────────────────────────────────────
Confermi questo design o vuoi esplorare un'alternativa?
```

Dopo conferma:
- Scrive `design/fase-0-paradigma/paradigma-selection.md` con rationale completo
- Aggiorna `design/.research-state.json` (paradigma, modulo)
- Aggiorna `.project-state.json` (research-design: in-corso)
- Appende a `project-log.md`

---

## 7. Moduli paradigma (fasi 1-6)

### Schema uniforme

Ogni modulo segue le stesse 6 fasi. Il contenuto varia, la struttura no.

```
FASE 1 — Framework e ipotesi/domande di ricerca
FASE 2 — Design specifico del paradigma
FASE 3 — Strumenti e raccolta dati
FASE 4 — Procedura, timeline, etica         [COMUNE a tutti]
FASE 5 — Piano di analisi → piano-analisi.json
FASE 6 — Preprint e disseminazione          [COMUNE a tutti]
```

### Contenuto distintivo per modulo

**MOD-QN1 — Quasi-sperimentale / Pilot** (~90% contenuto attuale riusato)
- F1: H1/H0, RQ confermative, ES da PRISMA
- F2: Pre-post gruppi naturali, go/no-go, stopping rules, power analysis G*Power
- F3: Strumenti validati, α Cronbach, learning analytics
- F5: ANCOVA, Cohen's d, IC 95%, missing data strategy
- Ref: Creswell (2018); Julious (2005); Trinchero (2004)

**MOD-QN2 — RCT**
- F2: Sequence generation, allocation concealment, blinding, CONSORT 2010 checklist
- F5: ITT vs per-protocol, analisi per subgroup pre-specificata
- Ref: CONSORT 2010; Schulz et al. (2010)

**MOD-QN3 — Single-subject**
- F2: Design A-B, A-B-A, A-B-A-B, Multiple Baseline; criteri stabilità baseline (5+ punti stabili)
- F5: Analisi visiva, Tau-U, PND (Percentage Non-Overlapping Data)
- Ref: Horner & Baer (1978); Parker et al. (2011); Kratochwill et al. (2013)

**MOD-QN4 — Survey / Correlazionale**
- F2: Campionamento (probabilistico/non), calcolo margine d'errore, tasso risposta target
- F3: Design questionario, scale Likert, piloting strumento
- F5: Correlazione, regressione multipla, analisi fattoriale esplorativa
- Ref: Fowler (2014); Field (2018)

**MOD-Q1 — Fenomenologia**
- F1: Domande esplorative aperte, bracketing (epoché), posizionamento epistemologico
- F2: IPA (Smith et al.) o Giorgi; N=6-12 purposive
- F3: Traccia intervista semi-strutturata, 60-90 min, trascrizione verbatim
- F5: IPA 6 steps; clustering temi esperienziali
- Ref: Smith, Flowers & Larkin (2009); Giorgi (2009)

**MOD-Q2 — Grounded Theory**
- F1: RQ aperta ("Come/Cosa accade quando...")
- F2: Glaser & Strauss classica vs. Charmaz costruttivista; theoretical sampling; saturazione
- F3: Interviste, osservazione, documenti; memo writing sin dall'inizio
- F5: Coding open→axial→selective; comparazione costante; core category; diagramma categorie
- Ref: Glaser & Strauss (1967); Charmaz (2014)

**MOD-Q3 — Etnografia**
- F2: Negoziazione accesso al campo; ruolo osservatore; durata minima 3-6 mesi
- F3: Note campo strutturate (descrittive + riflessive), key informant, documenti istituzionali
- F4: Ethics ongoing (rinegoziazione continua del consenso)
- F5: Thick description (Geertz); triangolazione fonti
- Ref: Geertz (1973); Hammersley & Atkinson (2007)

**MOD-Q4 — Ricerca Narrativa**
- F2: Selezione narratori; tipo racconto (life history, episodico)
- F3: Intervista narrativa non direttiva, documenti biografici, diari
- F5: Analisi struttura (Labov), contenuto (tematica), performance (Riessman)
- Ref: Riessman (2008); Clandinin & Connelly (2000)

**MOD-MM — Mixed-Methods**
- F2: Design (Explanatory/Exploratory/Convergent); punto di integrazione; priority quant vs. qual
- F5: Joint display; meta-inferenze; gestione divergenze (divergenze = risultati, non errori)
- Ref: Creswell & Plano Clark (2018); Teddlie & Tashakkori (2009)

**MOD-AR — Ricerca-Azione (PAR)**
- F1: Problema pratico + comunità coinvolta + obiettivo trasformativo
- F2: Cicli PAR (pianifica→agisci→osserva→rifletti); N cicli da definire
- F3: Strumenti partecipativi (world cafè, photovoice, focus group)
- F4: Consenso della comunità (non solo individuale); etica della reciprocità
- F5: Analisi per ciclo; spiral reflection; validazione collaborativa
- F6: Report riflessivo; artefatti come output primario
- Ref: Kemmis & McTaggart (1988); Reason & Bradbury (2008)

**MOD-DBR — Design-Based Research**
- F1: Problema di design + utenti target + teoria dell'intervento iniziale
- F2: Iterazioni micro (sessione) e macro (ciclo); criteri revisione tra iterazioni
- F3: Usability data, log sistema, osservazione implementazione
- F5: Analisi comparativa iterazioni; principi di design emergenti
- F6: Design principles come output primario; changelog strumento
- Ref: van den Akker et al. (2006); McKenney & Reeves (2012)

### Struttura dati per paradigma (in `raccolta-dati/dati/`)

| Paradigma | `grezzi/` | `elaborati/` |
|-----------|-----------|-------------|
| QN1/QN2 | `pre-test.csv`, `post-test.csv`, `covariate.csv`, `dropout-log.md` | `ancova-output.csv`, `effect-size.json`, `figures/` |
| QN3 | `misure-ripetute.csv`, `sessione-log.md` | `grafico-AB.png`, `tau-u.json` |
| QN4 | `risposte.csv`, `metadata-campione.csv` | `correlazioni.csv`, `regressione.json` |
| Q1/Q2/Q4 | `trascrizioni/`, `memo.md` | `codebook.md`, `temi/`, `diagramma-categorie.md` |
| Q3 | `note-osservazione/`, `documenti-istituzionali/` | `cronologia-eventi.md`, `mappa-relazioni.md` |
| AR | `cicli/ciclo-N/{01-pianificazione, 02-attuazione-log, 03-osservazioni, 04-riflessione}.md` | `sintesi-cicli.md` |
| DBR | `iterazioni/iter-N/{design, implement, analyze, redesign}.md` | `principi-design.md`, `changelog.md` |

---

## 8. Handoff tra skill

| Da | A | File | Contenuto |
|----|---|------|-----------|
| `prisma-review` | `research-design` | `prisma/prisma_synthesis.md` | Effect size, framework, RQ aperte, gap popolazione |
| `research-design` | `instruments-admin` | `design/fase-5-analisi/piano-analisi.json` | Paradigma, variabili, strumenti, formato dati atteso |
| `research-design` | `data-analysis` | `design/fase-5-analisi/piano-analisi.json` | Piano analisi pre-specificato |
| `research-design` | `pandoc-export` | `design/fase-6-preprint/preprint-bozza.md` | Bozza preprint |
| qualsiasi skill | qualsiasi skill | `.project-state.json` | Stato globale pipeline |
| qualsiasi skill | qualsiasi skill | `project-log.md` | Decisioni e handoff |

### `piano-analisi.json` (handoff research-design → data-analysis)

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

## 9. Elementi trasversali (tutti i moduli)

| Elemento | Implementazione |
|----------|-----------------|
| Aggiornamento `.research-state.json` | Fine ogni fase, in `design/` |
| Aggiornamento `.project-state.json` | Inizio e fine skill, in root |
| Append `project-log.md` | Ogni decisione con skill + data + rationale |
| Checkpoint utente | Prima di avanzare alla fase successiva |
| Guardrail anti-allucinazione | `[CITARE: da verificare]` per ogni riferimento |
| Pre-registrazione OSF | Fase 2 per paradigmi quantitativi (prima raccolta dati) |
| Normativa italiana | MIUR, GDPR, L.104/92, L.170/2010 per tutti i livelli |

---

## 10. File da creare/modificare (implementazione)

| Azione | File | Priorità |
|--------|------|----------|
| CREA | `skills/research-design/SKILL.md` | P1 |
| CREA | `skills/research-design/references/` (riusa da educational-pilot-design) | P1 |
| CREA | `skills/research-design/imrad-protocol-paper.md` (riusa) | P1 |
| CREA | `skills/research-design/imrad-results-paper.md` (riusa) | P1 |
| MODIFICA | `skills/prisma-review/SKILL.md` — Fase 0: crea struttura completa progetto | P1 |
| MODIFICA | `skills/pipeline-ricerca/SKILL.md` — aggiorna flusso e percorsi | P1 |
| DEPRECA | `skills/educational-pilot-design/SKILL.md` — nota deprecazione | P2 |

---

*Spec approvata — 2026-06-01*
*Prossimo step: writing-plans per piano implementazione task-by-task*
