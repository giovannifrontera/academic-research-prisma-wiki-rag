# Research-Design Skill — Design Specification

**Data:** 2026-06-01  
**Progetto:** academic-research-prisma-wiki-rag  
**Sostituisce:** `educational-pilot-design` (skill monoparadigma)

---

## 1. Problema

Il skill `educational-pilot-design` presuppone implicitamente il disegno quasi-sperimentale (MOD-QN1). Non guida il ricercatore nella scelta del paradigma — lo forza in un'unica metodologia indipendentemente dall'obiettivo di ricerca. Questo blocca ricercatori che devono condurre studi qualitativi, mixed-methods, action research o design-based research.

---

## 2. Soluzione: Skill `research-design`

Il nuovo skill `research-design` sostituisce `educational-pilot-design` con un framework paradigm-agnostic che:

1. **Fase 0 (Decision Tree):** 5 domande di routing per determinare il paradigma appropriato
2. **11 moduli paradigma:** uno per ogni metodologia supportata
3. **Struttura a 6 fasi unificata:** uguale per tutti i paradigmi, contenuto paradigma-specifico
4. **State persistence:** ripresa multi-sessione senza ripetere decisioni già prese

---

## 3. Architettura Unified Project Workspace

### 3.1 Struttura Cartelle (creata da PRISMA Fase 0)

```
{project-root}/
├── .project-state.json        # master state di tutto il pipeline
├── project-log.md             # audit log append-only, tutti i skill
├── prisma/                    # PRISMA review outputs
│   └── prisma_synthesis.md    # handoff → research-design
├── rag_db/                    # hybrid-rag index
├── design/                    # research-design outputs
│   ├── .research-state.json   # state per-fase del research-design skill
│   ├── fase-0-paradigma/
│   ├── fase-1-framework/
│   ├── fase-2-design/
│   ├── fase-3-strumenti/
│   ├── fase-4-procedura/
│   └── fase-5-analisi/
│       └── piano-analisi.json # handoff → data-analysis
├── raccolta-dati/
├── analisi/
└── preprint/
```

### 3.2 Master State File (`.project-state.json`)

```json
{
  "project_name": "string",
  "created_at": "ISO8601",
  "current_phase": "research-design",
  "phases": {
    "prisma": { "status": "completed", "completed_at": "ISO8601" },
    "rag": { "status": "completed", "completed_at": "ISO8601" },
    "research-design": { "status": "in_progress", "started_at": "ISO8601" },
    "instruments-admin": { "status": "pending" },
    "data-analysis": { "status": "pending" },
    "preprint": { "status": "pending" }
  }
}
```

### 3.3 Research State File (`design/.research-state.json`)

```json
{
  "current_phase": 2,
  "completed_phases": [0, 1],
  "paradigm": "MOD-QN1",
  "paradigm_label": "Quasi-sperimentale",
  "modulo": "MOD-QN1",
  "routing_answers": {
    "q1_obiettivo": "misurare",
    "q2_conoscenza": "esistente",
    "q3_outcome": "quantitativo",
    "q4_vincoli": "no_randomizzazione",
    "q5_sequenza": "cross-sectional"
  },
  "sample_size": null,
  "framework_selected": null,
  "last_updated": "ISO8601"
}
```

### 3.4 Audit Log (`project-log.md`)

Ogni skill aggiunge entry append-only:

```
## [ISO8601] research-design | Fase 0 completata
**Decisione:** paradigma MOD-QN1 selezionato
**Rationale:** obiettivo misurare, assenza randomizzazione, outcome quantitativo
**Alternative considerate:** MOD-MM (scartato: N insufficiente per componente qual.)
```

---

## 4. Backward Compatibility

Se `.project-state.json` è assente ma esiste `prisma_state.json` (vecchia struttura):
1. `research-design` auto-crea il master state inferendo dalle date dei file esistenti
2. Documenta l'inferenza in `project-log.md` con tag `[AUTO-MIGRATED]`
3. Seleziona automaticamente MOD-QN1 se `protocollo_ricerca.md` esiste (vecchio format)

---

## 5. Fase 0: Decision Tree (Routing)

### 5.1 Le 5 Domande

| # | Domanda | Opzioni |
|---|---------|---------|
| Q1 | Qual è il tuo obiettivo primario? | comprendere / misurare / migliorare / progettare |
| Q2 | Qual è lo stato della conoscenza nell'area? | consolidata / emergente / inesistente |
| Q3 | Che tipo di outcome ti aspetti? | quantitativo / qualitativo / entrambi |
| Q4 | Hai vincoli pratici (N piccolo, no randomizzazione)? | sì / no |
| Q5 | Hai bisogno di sequenza temporale? | longitudinale / cross-sectional / iterativo |

### 5.2 Routing Table

| Q1 | Q2 | Q3 | Q4 | Q5 | Paradigma |
|----|----|----|----|----|-----------|
| misurare | qualsiasi | quantitativo | no | qualsiasi | **MOD-QN2** (RCT) |
| misurare | qualsiasi | quantitativo | sì (no rand.) | qualsiasi | **MOD-QN1** (quasi-exp) |
| misurare | qualsiasi | quantitativo | sì (N<10) | qualsiasi | **MOD-QN3** (single-subject) |
| misurare | qualsiasi | quantitativo | N>100 | cross | **MOD-QN4** (survey) |
| comprendere | emergente | qualitativo | sì | qualsiasi | **MOD-Q1** (fenomenologia) |
| comprendere | inesistente | qualitativo | sì | qualsiasi | **MOD-Q2** (grounded theory) |
| comprendere | qualsiasi | qualitativo | contesto | longitudinale | **MOD-Q3** (etnografia) |
| comprendere | qualsiasi | qualitativo | sì | qualsiasi | **MOD-Q4** (narrativo) |
| qualsiasi | qualsiasi | entrambi | qualsiasi | qualsiasi | **MOD-MM** (mixed-methods) |
| migliorare | qualsiasi | qualsiasi | pratica | iterativo | **MOD-AR** (action research) |
| progettare | qualsiasi | qualsiasi | artefatto | iterativo | **MOD-DBR** (design-based) |

---

## 6. Moduli Paradigma (11)

### 6.1 Quantitativi
- **MOD-QN1** — Quasi-sperimentale (eredita contenuto da `educational-pilot-design`)
- **MOD-QN2** — RCT (Randomized Controlled Trial)
- **MOD-QN3** — Single-Subject Design (A-B-A, multiple baseline)
- **MOD-QN4** — Survey correlazionale/descrittivo

### 6.2 Qualitativi
- **MOD-Q1** — Fenomenologia (IPA, analisi tematica)
- **MOD-Q2** — Grounded Theory (saturazione teorica, memoing)
- **MOD-Q3** — Etnografia (osservazione partecipante, field notes)
- **MOD-Q4** — Ricerca narrativa (story analysis, biographical method)

### 6.3 Altri
- **MOD-MM** — Mixed-Methods (convergent, sequential, embedded)
- **MOD-AR** — Action Research (cicli PAR: plan-act-observe-reflect)
- **MOD-DBR** — Design-Based Research (iterative design + efficacy testing)

### 6.4 Struttura Fasi per Modulo (identica, contenuto diverso)

| Fase | Nome | QN | Q | MM | AR | DBR |
|------|------|----|---|----|----|-----|
| 0 | Decision Tree | routing | routing | routing | routing | routing |
| 1 | Framework/Ipotesi | power analysis, RQ, H0/H1 | domande apertura, framework teorico | ipotesi miste, priority | problema pratico, obiettivi ciclici | design principles, obiettivi design |
| 2 | Design Specifico | controllo gruppi, baseline | protocollo interviste/FG | design sequenziale/convergente | cicli AR, stakeholder | prototipo iniziale, iterazioni |
| 3 | Strumenti | scale validate, test standardizzati | interview guide, osservazione | multi-strumento | strumenti partecipativi | rubric valutazione design |
| 4 | Procedura/Etica | randomizzazione/matching, IRB | consenso, anonimato, saturation | integrazione dati, consent | co-ricerca, GDPR | test utenti, consent |
| 5 | Piano Analisi | ANCOVA/ANOVA/HLM | tematic analysis/IPA/GT | integrazione qual+quant | riflessività, cicli riflessivi | efficacy analysis, design revision |
| 6 | Preprint/Roadmap | IMRAD quantitativo | IMRAD qualitativo | IMRAD mixed | report partecipativo | DBR paper format |

---

## 7. Integrazioni con Skills Esistenti

### 7.1 Input: `prisma-review` → `research-design`

File handoff: `prisma/prisma_synthesis.md`, sezione **OUTPUT PER PILOT STUDY**

Campi consumati:
- `effect_size_aggregates` → Fase 1, power analysis (solo paradigmi QN)
- `dominant_frameworks` → Fase 1, selezione framework teorico
- `instrument_frequency_table` → Fase 3, selezione strumenti validati
- `unanswered_rqs` → Fase 1, formulazione RQ
- `population_gaps` → Fase 0, routing Q4 (vincoli pratici)
- `intervention_duration` → Fase 4, pianificazione procedura

### 7.2 Output: `research-design` → `data-analysis`

File handoff: `design/fase-5-analisi/piano-analisi.json`

```json
{
  "paradigm": "MOD-QN1",
  "variables": {
    "dependent": [{"name": "...", "scale": "interval", "instrument": "..."}],
    "independent": [{"name": "...", "levels": [...]}],
    "covariates": [{"name": "...", "rationale": "..."}]
  },
  "tests": [
    {"test": "ANCOVA", "software": "JASP", "assumptions": ["normality", "homogeneity"]}
  ],
  "data_format": "SPSS_sav | CSV | XLSX",
  "missing_data_strategy": "FIML | listwise | multiple_imputation"
}
```

### 7.3 Output: `research-design` → `pandoc-export`

File: `preprint/preprint-bozza.md` con template IMRAD appropriato al paradigma

### 7.4 Coordinamento: `pipeline-ricerca`

`pipeline-ricerca` aggiorna il riferimento a `research-design` come sostituto di `educational-pilot-design` nel workflow stage 3.

---

## 8. Session Recovery

All'avvio del skill, sequenza di check:

1. Esiste `.project-state.json`? → leggi `current_phase` e stato pipeline
2. Esiste `design/.research-state.json`? → leggi `current_phase` interno
3. Mostra riepilogo:
   ```
   [RIPRESA] Progetto: {nome} | Paradigma: {MOD-XX} | Fase corrente: {N}/6
   Ultima decisione registrata: {ultima entry project-log.md}
   Continuare da Fase {N}? [sì/no/lista-fasi]
   ```
4. Se assente tutto → avvia da Fase 0

---

## 9. Normativa Italiana

Tutti i moduli includono riferimenti normativi pertinenti:
- **MIUR** — linee guida valutazione e sperimentazione didattica
- **GDPR (Reg. EU 2016/679)** — protezione dati, consenso minori
- **L. 104/1992** — disabilità, inclusione, BES
- **L. 170/2010** — DSA, misure compensative e dispensative
- **D.Lgs. 196/2003 + D.Lgs. 101/2018** — Codice Privacy IT

---

## 10. Roadmap Implementazione

### Priorità Alta
1. Creare `skills/research-design/SKILL.md` con Fase 0 + MOD-QN1 (migrazione da educational-pilot-design)
2. Aggiornare `pipeline-ricerca` per referenziare `research-design`
3. Aggiungere `piano-analisi.json` schema a `skills/research-design/`

### Priorità Media
4. MOD-QN2, MOD-QN3, MOD-QN4 (altri paradigmi quantitativi)
5. MOD-Q1, MOD-Q2 (fenomenologia e grounded theory — più richiesti)
6. MOD-MM (mixed-methods)

### Priorità Bassa
7. MOD-Q3 (etnografia), MOD-Q4 (narrativo)
8. MOD-AR (action research)
9. MOD-DBR (design-based research)

---

## 11. File da Creare/Modificare

| File | Azione | Note |
|------|--------|------|
| `skills/research-design/SKILL.md` | **CREARE** | Skill principale (nuovo) |
| `skills/research-design/piano-analisi-schema.json` | **CREARE** | JSON schema per handoff |
| `skills/research-design/references/normativa-it.md` | **CREARE** | Normativa italiana |
| `skills/educational-pilot-design/SKILL.md` | **DEPRECARE** | Aggiungere notice deprecation → research-design |
| `skills/pipeline-ricerca/SKILL.md` | **MODIFICARE** | Aggiornare stage 3 reference |
