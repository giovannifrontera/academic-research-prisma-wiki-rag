# research-design Skill — Piano di Implementazione

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Creare la skill `research-design` che sostituisce `educational-pilot-design` con decision tree per 11 paradigmi di ricerca, spazio progetto unificato con `.project-state.json`, e integrazione nella pipeline PRISMA → preprint.

**Architecture:** Skill Markdown unica `SKILL.md` con sezioni AVVIO + Fase 0 (decision tree D1-D5) + sezioni comuni + 11 moduli paradigma. Cartella progetto creata da PRISMA Fase 0 con struttura `prisma/ design/ raccolta-dati/ analisi/ preprint/` e `.project-state.json` in root. Aggiorna anche `prisma-review` Fase 0 e `pipeline-ricerca`.

**Tech Stack:** Markdown (Claude Code skill format), JSON (state files). Spec: `docs/specs/2026-06-01-research-design-skill-design.md`.

---

## Mappa file

| Azione | File | Note |
|--------|------|------|
| CREA | `skills/research-design/SKILL.md` | File principale (~70KB) |
| CREA | `skills/research-design/imrad-protocol-paper.md` | Copia da educational-pilot-design |
| CREA | `skills/research-design/imrad-results-paper.md` | Copia da educational-pilot-design |
| CREA | `skills/research-design/references/` | Copia da educational-pilot-design |
| MODIFICA | `skills/prisma-review/SKILL.md` | Fase 0: struttura progetto unificata |
| MODIFICA | `skills/pipeline-ricerca/SKILL.md` | Aggiorna flusso e percorsi |
| MODIFICA | `skills/educational-pilot-design/SKILL.md` | Prepend nota deprecazione |

---

## Task 1: Setup directory e file di supporto

**Files:**
- Create: `skills/research-design/imrad-protocol-paper.md`
- Create: `skills/research-design/imrad-results-paper.md`
- Modify: `skills/educational-pilot-design/SKILL.md`

- [ ] **Step 1: Copia imrad-protocol-paper.md**

Leggi `skills/educational-pilot-design/imrad-protocol-paper.md` e crea `skills/research-design/imrad-protocol-paper.md` con contenuto identico, aggiungendo in fondo questa sezione per i paradigmi qualitativi:

```markdown
---

## Struttura alternativa — Paradigmi Qualitativi

Per Fenomenologia, Grounded Theory, Etnografia, Ricerca Narrativa la struttura IMRAD si adatta:

```
## Abstract
## 1. Introduction (problema + posizionamento epistemologico + RQ esplorativa)
## 2. Theoretical Framework
## 3. Methodology
   ### 3.1 Research Design e Paradigma
   ### 3.2 Partecipanti e Campionamento (purposive, N e criteri)
   ### 3.3 Raccolta dati (strumenti qualitativi)
   ### 3.4 Analisi (metodo specifico: IPA, GT coding, thick description, Riessman)
   ### 3.5 Trustworthiness (credibility, transferability, dependability, confirmability)
   ### 3.6 Posizionalità del ricercatore
   ### 3.7 Etica
## 4. Findings (temi/categorie con citazioni esemplificative)
## 5. Discussion
## 6. Conclusions
## References
```

---

## Struttura alternativa — Ricerca-Azione (PAR)

```
## Abstract
## 1. Introduction (problema pratico + comunità coinvolta)
## 2. Theoretical Framework (PAR, Kemmis & McTaggart)
## 3. Methodology
   ### 3.1 PAR Design e cicli
   ### 3.2 Partecipanti e co-ricercatori
   ### 3.3 Raccolta dati per ciclo
   ### 3.4 Analisi riflessiva
   ### 3.5 Validazione collaborativa
   ### 3.6 Etica della reciprocità
## 4. Findings (per ciclo: pianificazione → azione → osservazione → riflessione)
## 5. Discussion e implicazioni pratiche
## 6. Conclusions (cambiamenti ottenuti + roadmap futura)
## References
```

---

## Struttura alternativa — Design-Based Research (DBR)

```
## Abstract
## 1. Introduction (problema di design + teoria dell'intervento iniziale)
## 2. Theoretical Framework
## 3. Methodology
   ### 3.1 DBR Design e iterazioni
   ### 3.2 Partecipanti e contesto
   ### 3.3 Raccolta dati per iterazione
   ### 3.4 Analisi comparativa iterazioni
## 4. Design Iterations (per iterazione: design → implement → analyze → redesign)
## 5. Emerging Design Principles
## 6. Discussion
## 7. Conclusions
## References
```
```

- [ ] **Step 2: Copia imrad-results-paper.md**

Crea `skills/research-design/imrad-results-paper.md` identico a `skills/educational-pilot-design/imrad-results-paper.md`.

- [ ] **Step 3: Aggiungi nota deprecazione a educational-pilot-design**

Leggi `skills/educational-pilot-design/SKILL.md`. Prependi queste righe PRIMA del frontmatter `---`:

```markdown
> ⚠️ **DEPRECATA** — Sostituita da `research-design`, che guida la scelta tra 11 paradigmi di ricerca (qualitativo, quantitativo, misto, ricerca-azione, DBR) e si integra nello spazio progetto unificato della pipeline PRISMA → preprint. I progetti esistenti con `protocollo_ricerca.md` vengono ripresi automaticamente da `research-design`.

```

- [ ] **Step 4: Verifica**

```bash
ls skills/research-design/
# Atteso: imrad-protocol-paper.md  imrad-results-paper.md
head -3 skills/educational-pilot-design/SKILL.md
# Atteso: riga con ⚠️ DEPRECATA
```

- [ ] **Step 5: Commit**

```bash
git add skills/research-design/imrad-protocol-paper.md
git add skills/research-design/imrad-results-paper.md
git add skills/educational-pilot-design/SKILL.md
git commit -m "feat: setup research-design dir + deprecate educational-pilot-design"
```

---

## Task 2: SKILL.md — Header, AVVIO, Fase 0

**Files:**
- Create: `skills/research-design/SKILL.md`

- [ ] **Step 1: Crea SKILL.md con header e sezione AVVIO**

Crea `skills/research-design/SKILL.md`:

```markdown
---
name: research-design
description: Usa quando occorre progettare uno studio di ricerca nelle scienze dell'educazione o in ambiti correlati. Fa parte della pipeline PRISMA → preprint: legge il contesto da prisma/prisma_synthesis.md e scrive in design/. Guida la scelta del paradigma (qualitativo, quantitativo, misto, ricerca-azione, DBR) e la progettazione completa. Copre tutti i livelli scolastici italiani e contesti internazionali. NON usare per revisioni sistematiche (usa prisma-review).
---

# Progettazione Studio di Ricerca — Scienze dell'Educazione

## Overview

Guida la progettazione rigorosa di studi di ricerca in tutti i paradigmi delle scienze dell'educazione. Prima di entrare nel merito del design, aiuta il ricercatore a scegliere il **paradigma più adatto** alla sua domanda tramite un decision tree strutturato.

**Tipo di skill:** Rigida — segui le fasi nell'ordine indicato.

**Regola d'oro:** Non passare alla fase successiva senza conferma esplicita dell'utente.

**Pipeline:** `prisma-review` → `hybrid-rag` → **`research-design`** → `instruments-admin` → `data-analysis` → `pandoc-export`

---

## Avvio (esegui prima di qualsiasi altra azione)

### 1. Verifica spazio progetto

Cerca `.project-state.json` nella directory corrente:

**Trovato →** leggi e mostra:
```
Progetto:   [progetto]
Pipeline:   PRISMA [✓/▶/□]  RAG [✓/▶/□]  Design [▶]  Raccolta [□]  Analisi [□]
```
Chiedi: *"Vuoi riprendere questo progetto?"*

**Non trovato →** cerca `prisma_state.json` o `prisma_synthesis.md` nella root (progetto pre-esistente). Se trovati → crea `.project-state.json` retroattivamente (vedi §retrocompatibilità). Se non trovati → *"Non trovo `.project-state.json`. Sei nella cartella root del progetto?"*

### 2. Ripresa sessione

Cerca `design/.research-state.json`:

**Trovato →** mostra riepilogo:
```
Progetto:        [nome]
Pipeline:        PRISMA ✓  RAG ✓  Design ▶  Raccolta □  Analisi □
Paradigma:       [paradigma] ([modulo])
Fase design:     [N] — [nome]
Fasi ok:         [lista ✓]
Ultima sessione: [data]
```
Chiedi: *"Vuoi riprendere dalla Fase [N]?"*

**Non trovato →** prima sessione di design. Crea `design/` se non esiste. Vai a Fase 0.

### 3. Lettura contesto PRISMA (automatica)

Cerca (in ordine): `prisma/prisma_synthesis.md`, poi `prisma_synthesis.md` in root.

**Trovato →** estrai e annota: N paper inclusi, effect size medio, framework dominante, RQ aperte, gap popolazione, strumenti più usati.

Dichiara: *"Ho letto il contesto PRISMA: [N] paper, ES d=[X], framework: [Y], gap: [Z]."*

**Non trovato →** avvisa e chiedi percorso. Procedi se l'utente conferma.

### 4. Aggiorna `.project-state.json`

```json
{ "fasi_workflow": { "research-design": { "stato": "in-corso", "data_avvio": "[oggi]" } } }
```

### §retrocompatibilità

Se `prisma_state.json` o `prisma_synthesis.md` esistono in root ma non `.project-state.json`:
1. Crea `.project-state.json` con `prisma: completata`, `research-design: in-corso`
2. Crea `project-log.md` con intestazione
3. Appendi a `project-log.md`: *"[data] [research-design] Progetto pre-esistente: .project-state.json creato retroattivamente."*
4. Non spostare i file PRISMA esistenti

### §livello-scolastico

> "Lo studio si svolge in: (a) scuola dell'infanzia, (b) primaria, (c) secondaria I grado, (d) secondaria II grado, (e) università / alta formazione, (f) formazione professionale / IeFP, (g) contesto internazionale?"

[riusa tabella completa da `skills/educational-pilot-design/SKILL.md` sezione "Livello scolastico e contesto"]

Per i dettagli normativi completi, leggi `references/contesti-regolatori.md` quando la Fase 4 è in esecuzione.

### §profilo-disciplinare

[riusa sezione "Profilo disciplinare" da `skills/educational-pilot-design/SKILL.md` — stesse opzioni a-g]

---

## File generati dalla Skill

Tutti i file vengono creati in `design/` nella cartella root del progetto:

1. `design/.research-state.json` — stato macchina (aggiornato a ogni fase)
2. `design/protocollo_ricerca.md` — documento principale + Blocco STATO
3. `design/fase-[N]-*/` — output per fase
4. `design/fase-5-analisi/piano-analisi.json` — handoff verso data-analysis
5. `design/fase-6-preprint/preprint-bozza.md` — handoff verso pandoc-export

### Blocco STATO (in `design/protocollo_ricerca.md`)

```
<!-- STATO
Fase corrente: [N]
Paradigma: [paradigma]
Modulo: [MOD-XX]
Livello: [livello]
Profilo: [profilo]
Framework: [framework]
Design: [design]
N previsto: [N]
Criteri go/no-go: [sì/no — solo paradigmi quantitativi]
PRISMA: [nome file o "nessuno"]
RAG: [sì/no]
Dati raccolti: [sì/no]
Ultima modifica: [data]
-->
```

### Protocollo aggiornamento (regola ferrea)

| Momento | Azioni obbligatorie |
|---------|--------------------|
| Fine ogni fase | 1) `design/.research-state.json` 2) `project-log.md` 3) chiedi conferma |
| Fine skill | `.project-state.json`: `research-design → completata` |
| Interruzione | Appendi a `project-log.md`: stato corrente + prossimo passo + data |
```

- [ ] **Step 2: Aggiungi Fase 0 al file**

Appendi a `skills/research-design/SKILL.md`:

```markdown
---

## FASE 0 — Selezione Paradigma

### 0.0 — Inizializzazione design/

Se `design/` non esiste, crea la struttura:
```
design/
├── .research-state.json
├── protocollo_ricerca.md
├── fase-0-paradigma/
├── fase-1-framework/
├── fase-2-design/
├── fase-3-strumenti/
├── fase-4-procedura/
├── fase-5-analisi/
└── fase-6-preprint/
```

Inizializza `design/.research-state.json`:
```json
{
  "fase_corrente": 0,
  "fasi_completate": [],
  "paradigma": null,
  "modulo": null,
  "livello": null,
  "profilo": null,
  "framework": null,
  "n_previsto": null,
  "prisma_file": null,
  "rag_disponibile": false,
  "dati_raccolti": false,
  "preregistrazione_osf": null,
  "ultima_modifica": "[oggi]",
  "fasi": {}
}
```

Inizializza `design/protocollo_ricerca.md` con Blocco STATO vuoto e titolo `# Protocollo di Ricerca — [nome progetto]`.

### 0.1 — 5 domande di routing (una alla volta)

**D1 — Obiettivo principale:**
> "Cosa vuoi fare con questa ricerca?
> a) **Comprendere** — esplorare un fenomeno, capire significati, esperienze vissute
> b) **Misurare** — testare l'effetto di un intervento, quantificare un outcome
> c) **Migliorare** — cambiare una pratica educativa *attraverso* la ricerca stessa
> d) **Progettare** — creare e raffinare iterativamente uno strumento/ambiente didattico"

**D2 — Stato della conoscenza** *(salta se PRISMA disponibile)*:
> "Quanto è già noto questo fenomeno?
> a) Poco/nulla — fenomeno emergente
> b) Abbastanza — gap importanti
> c) Molto — voglio confermare in nuovo contesto"

**D3 — Natura dell'outcome:**
> "Cosa vuoi produrre?
> a) Numeri e misure
> b) Significati e interpretazioni
> c) Entrambi (triangolazione)"

**D4 — Vincoli pratici** *(solo se D1=b o D1=d)*:
> "N partecipanti e randomizzazione?
> a) N ≥ 20/gruppo + randomizzazione → RCT
> b) N ≥ 10/gruppo + classi naturali → Quasi-sperimentale
> c) N < 10 o singolo caso → Single-subject
> d) N grande, nessun intervento → Survey"

**D5 — Sequenza** *(solo se D3=c)*:
> "Come combini quantitativo e qualitativo?
> a) Prima misuro, poi capisco → Explanatory Sequential
> b) Prima comprendo, poi confermo → Exploratory Sequential
> c) In parallelo → Convergent Parallel"

**D-extra** *(solo se D1=a, D3=b, e non sei andato a Q1 o Q2)*:
> "Ti interessa:
> a) Pratiche collettive, cultura, vita di un contesto → Etnografia
> b) Storie individuali, biografie → Ricerca Narrativa"

### Tabella di routing

| D1 | D2 | D3 | D4 | D5 | Modulo |
|----|----|----|----|----|--------|
| b | * | a | a | — | MOD-QN2 (RCT) |
| b | * | a | b | — | MOD-QN1 (Quasi-sperimentale) |
| b | * | a | c | — | MOD-QN3 (Single-subject) |
| b | * | a | d | — | MOD-QN4 (Survey) |
| a | a | b | — | — | MOD-Q1 (Fenomenologia) |
| a | b | b | — | — | MOD-Q2 (Grounded Theory) |
| a | * | b+Dextra=a | — | — | MOD-Q3 (Etnografia) |
| a | * | b+Dextra=b | — | — | MOD-Q4 (Ricerca Narrativa) |
| * | * | c | — | a | MOD-MM Explanatory Sequential |
| * | * | c | — | b | MOD-MM Exploratory Sequential |
| * | * | c | — | c | MOD-MM Convergent Parallel |
| c | * | * | — | — | MOD-AR (Ricerca-Azione PAR) |
| d | * | * | — | — | MOD-DBR (Design-Based Research) |

### 0.2 — Output raccomandazione e salvataggio

```
RACCOMANDAZIONE DESIGN
───────────────────────────────────────────────────
Paradigma:    [nome completo]
Modulo:       [MOD-XX]
Motivazione:  [2-3 frasi: risposte D1-D5 + PRISMA]
Alternative:  [1-2 con trade-off]
Riferimento:  [Creswell & Creswell 2018 + specifico]
───────────────────────────────────────────────────
Confermi questo design?
```

Dopo conferma:
1. Scrivi `design/fase-0-paradigma/paradigma-selection.md` con rationale completo
2. Aggiorna `design/.research-state.json`: `paradigma`, `modulo`, `fase_corrente: 1`, `fasi_completate: [0]`
3. Aggiorna Blocco STATO in `design/protocollo_ricerca.md`
4. Appendi a `project-log.md`:
```markdown
---
## [data] [research-design] Fase 0 — Selezione paradigma
**Decisione:** [paradigma] ([modulo])
**Rationale:** [motivazione]
**Alternative scartate:** [con motivo]
```
5. Chiedi conferma prima di Fase 1
```

- [ ] **Step 3: Verifica struttura**

```bash
grep -n 'name: research-design' skills/research-design/SKILL.md
# Atteso: 2:name: research-design
grep -c 'MOD-QN' skills/research-design/SKILL.md
# Atteso: almeno 4
grep -n 'Tabella di routing' skills/research-design/SKILL.md
# Atteso: numero di riga > 0
```

- [ ] **Step 4: Commit**

```bash
git add skills/research-design/SKILL.md
git commit -m "feat: research-design SKILL.md — header, AVVIO, Fase 0 decision tree"
```

---

## Task 3: SKILL.md — Sezioni comuni (Etica, Preprint, Handoff)

**Files:**
- Modify: `skills/research-design/SKILL.md` (append)

- [ ] **Step 1: Aggiungi sezioni comuni**

Appendi a `skills/research-design/SKILL.md`:

```markdown
---

## §ETICA — Normativa e consenso (comune a tutti i paradigmi)

[Riusa integralmente la sezione "Fase 4 > 5. Vincoli normativi" da `skills/educational-pilot-design/SKILL.md`, inclusa la generazione del modulo di consenso informato per livello scolastico.]

Adattamenti per paradigmi specifici:
- **Etnografia:** rinegoziazione continua del consenso durante il campo; consenso è un processo, non un documento
- **PAR:** consenso della comunità (collettivo) oltre al consenso individuale; etica della reciprocità
- **DBR:** consenso per ogni iterazione; possibile modifica del design in corso d'opera
- **Log chatbot/AI:** vedi §log-chatbot da educational-pilot-design

---

## §PREPRINT — Scrittura e disseminazione (comune a tutti i paradigmi)

### Scelta template

Chiedi:
> "Il preprint sarà in: (a) italiano, (b) inglese?"
> "Che tipo di documento: (a) Protocol Paper (prima dei dati), (b) Results Paper (dopo)?"

Per **paradigmi quantitativi e mixed-methods**: leggi `imrad-protocol-paper.md` o `imrad-results-paper.md`.

Per **paradigmi qualitativi**: leggi sezione "Struttura alternativa — Paradigmi Qualitativi" in `imrad-protocol-paper.md`.

Per **PAR**: leggi sezione "Struttura alternativa — Ricerca-Azione" in `imrad-protocol-paper.md`.

Per **DBR**: leggi sezione "Struttura alternativa — Design-Based Research" in `imrad-protocol-paper.md`.

### Server preprint target

| Server | Disciplina | Note |
|--------|-----------|------|
| EdArXiv (edarxiv.org) | Educazione, didattica | Specifico per ricerca educativa |
| PsyArXiv (psyarxiv.com) | Psicologia, psicopedagogia | Per studi su apprendimento |
| OSF Preprints (osf.io) | Tutti | Integrato con pre-registrazione |
| SSRN (ssrn.com) | Scienze sociali | Ampia visibilità |
| Zenodo (zenodo.org) | Tutti | DOI immediato, Horizon Europe |

Chiedi: *"Su quale server vuoi pubblicare il preprint?"*

Ogni scelta genera `design/fase-6-preprint/preprint-target.md` con le specifiche di formattazione e submission della piattaforma scelta.

### Riviste target

[Riusa sezione "Fase 6 > 6d. Riviste target" da `skills/educational-pilot-design/SKILL.md`]

### Checklist qualità (comune a tutti i paradigmi)

- [ ] Titolo include: design, popolazione, intervento/fenomeno, outcome
- [ ] Abstract strutturato con tutte le sezioni
- [ ] Framework teorico con riferimenti primari
- [ ] Strumenti con riferimento originale e versione italiana
- [ ] Posizionalità del ricercatore dichiarata (per paradigmi qualitativi e PAR)
- [ ] Etica e GDPR dichiarati
- [ ] Link OSF se pre-registrato (paradigmi quantitativi)
- [ ] Roadmap post-studio inclusa nel protocollo

### Guardrail anti-allucinazione (obbligatorio)

Non inventare mai citazioni. Usa `[CITARE: autore/anno da verificare]` per ogni riferimento bibliografico — anche se sei quasi certo. Se RAG disponibile: usa `py hybrid_rag.py query "<costrutto>" --n 3` per ogni sezione.

### Handoff a pandoc-export

Al termine della scrittura:
> "Vuoi convertire il preprint in Word (.docx) o PDF? Invoco `pandoc-export`."

---

## §HANDOFF — Aggiornamento stato fine skill

Quando tutte le fasi sono completate:

1. Aggiorna `design/.research-state.json`: `fase_corrente: 6`, `fasi_completate: [0,1,2,3,4,5,6]`
2. Aggiorna `.project-state.json`: `research-design: { stato: "completata", data_completamento: "[oggi]" }`
3. Appendi a `project-log.md`:
```markdown
---
## [data] [research-design] Skill completata
**Output:** design/protocollo_ricerca.md, design/fase-5-analisi/piano-analisi.json, design/fase-6-preprint/preprint-bozza.md
**Prossimo passo:** instruments-admin per la raccolta dati
```
4. Informa: *"Design completato. File prodotti in `design/`. Prossimo passo: `instruments-admin` per la raccolta dati."*
```

- [ ] **Step 2: Commit**

```bash
git add skills/research-design/SKILL.md
git commit -m "feat: research-design — sezioni comuni etica, preprint, handoff"
```

---

## Task 4: MOD-QN1 — Quasi-sperimentale / Pilot

**Files:**
- Modify: `skills/research-design/SKILL.md` (append)

- [ ] **Step 1: Migra contenuto da educational-pilot-design**

Appendi a `skills/research-design/SKILL.md`:

```markdown
---

## MOD-QN1 — Quasi-sperimentale / Pilot

*Attivato quando: D1=b, D4=b (classi naturali, N ≥ 10/gruppo)*

**Riferimenti:** Creswell & Creswell (2018); Trinchero (2004); Julious (2005)

[Riusa integralmente le FASI 1-6 da `skills/educational-pilot-design/SKILL.md` con queste modifiche:

1. **Path dei file:** sostituisci tutti i riferimenti a `protocollo_ricerca.md` → `design/protocollo_ricerca.md`, `strumenti_valutazione.md` → `design/fase-3-strumenti/strumenti-valutazione.md`, `timeline_pilota.md` → `design/fase-4-procedura/timeline.md`, `preprint_bozza.md` → `design/fase-6-preprint/preprint-bozza.md`

2. **Blocco STATO:** sostituisci il formato con quello definito in §AVVIO di questa skill (include campo `Modulo: MOD-QN1`)

3. **Fase 5 — Aggiunta handoff data-analysis:** al termine della Fase 5 (Piano di Analisi), scrivi `design/fase-5-analisi/piano-analisi.json`:
```json
{
  "paradigma": "quasi-sperimentale",
  "modulo": "MOD-QN1",
  "variabili": {
    "dipendenti": ["[lista da Fase 3]"],
    "indipendente": "[intervento]",
    "covariate": ["pre-test", "[altre covariate]"] 
  },
  "test_previsti": ["ANCOVA", "Cohen-d", "IC-95"],
  "missing_data_strategy": "[da Fase 5]",
  "formato_dati": "CSV",
  "percorso_dati": "../raccolta-dati/dati/grezzi/",
  "alpha": 0.05,
  "software_consigliato": ["JASP", "R", "SPSS"]
}
```

4. **Fase 6 — Preprint:** sostituisci l'invocazione diretta di `pandoc-export` con il riferimento a §PREPRINT di questa skill.

5. **Rimozione:** elimina le sezioni "Avvio > Livello scolastico" e "Avvio > Profilo disciplinare" (ora in §AVVIO comune) e la sezione "Avvio > Verifica report PRISMA" (ora in Avvio comune). Non duplicare.
]
```

- [ ] **Step 2: Verifica**

```bash
grep -n 'MOD-QN1' skills/research-design/SKILL.md
# Atteso: almeno 2 righe
grep -n 'piano-analisi.json' skills/research-design/SKILL.md
# Atteso: almeno 1 riga
grep -n 'go/no-go' skills/research-design/SKILL.md
# Atteso: almeno 1 riga (dalla migrazione)
```

- [ ] **Step 3: Commit**

```bash
git add skills/research-design/SKILL.md
git commit -m "feat: research-design MOD-QN1 quasi-sperimentale (migrazione da educational-pilot-design)"
```

---

## Task 5: MOD-QN2, MOD-QN3, MOD-QN4

**Files:**
- Modify: `skills/research-design/SKILL.md` (append)

- [ ] **Step 1: Aggiungi MOD-QN2 (RCT)**

Appendi a `skills/research-design/SKILL.md`:

```markdown
---

## MOD-QN2 — RCT (Randomized Controlled Trial)

*Attivato quando: D1=b, D4=a (randomizzazione possibile)*

**Riferimenti:** CONSORT 2010 (Schulz et al.); Moher et al. (2010)

### FASE 1 — Ipotesi e RQ

[Stessa struttura di MOD-QN1 Fase 1 — H1/H0, effect size, RQ confermative]

**Aggiunta rispetto a MOD-QN1:** specifica il meccanismo di randomizzazione proposto (es. sorteggio classi, assegnazione casuale individuale, cluster randomization).

### FASE 2 — Design RCT

**2a. Procedura di randomizzazione:**
- **Sequence generation:** come viene generata la sequenza casuale (es. `random.org`, tabella numeri casuali, computer-generated)
- **Allocation concealment:** come si impedisce che il ricercatore conosca il gruppo prima dell'assegnazione (es. buste opache sigillate, centralizzato)
- **Blinding:** chi è cieco all'assegnazione? (partecipanti, docenti, valutatori) — in contesti educativi spesso il blinding dei partecipanti non è possibile; dichiararlo esplicitamente

**2b. CONSORT checklist (obbligatoria):**
Compila la checklist CONSORT 2010 (25 item) nella Fase 6 per il reporting. Scaricabile da equator-network.org/reporting-guidelines/consort/.

**2c. Power analysis:** [stessa di MOD-QN1 Fase 2d]

**2d. Criteri fattibilità e go/no-go:** [stessa di MOD-QN1 Fase 2e]

**2e. Stopping rules:** [stessa di MOD-QN1 Fase 2f]

**2f. Pre-registrazione OSF:** obbligatoria per RCT. Completa prima della raccolta dati includendo la sequenza di randomizzazione e il piano di analisi ITT.

### FASE 3 — Strumenti
[Stessa di MOD-QN1 Fase 3]

### FASE 4 — Procedura [→ §ETICA]
**Aggiunta:** documenta separatamente le procedure per gruppo sperimentale e gruppo di controllo. Il gruppo di controllo deve ricevere qualcosa (business-as-usual documentato, o wait-list).

**Analisi ITT vs per-protocol:** definisci a priori quale strategia usi:
- *Intention-to-treat (ITT):* analizza tutti i randomizzati nel gruppo assegnato, indipendentemente dall'adesione — preferita perché conserva i benefici della randomizzazione
- *Per-protocol:* analizza solo chi ha completato il protocollo — più ottimistica, meno robusta

### FASE 5 — Piano di analisi

[Stessa di MOD-QN1 Fase 5 + aggiunta:]

**Analisi per subgroup pre-specificata:** se prevista, definiscila ora. Le analisi per subgroup non pre-specificate devono essere dichiarate come esplorative.

**Verifica equivalenza baseline:** t-test o ANCOVA sul pre-test; se i gruppi non sono equivalenti nonostante la randomizzazione, usa ANCOVA con il pre-test come covariata.

Al termine, scrivi `design/fase-5-analisi/piano-analisi.json` con `"paradigma": "rct"`, `"modulo": "MOD-QN2"`, e `"analisi_itt": true`.

### FASE 6 — Preprint [→ §PREPRINT]

Usa struttura IMRAD standard. Includi:
- Flowchart CONSORT dei partecipanti (Numbers enrolled → randomized → allocated → analysed)
- Link alla pre-registrazione OSF
- CONSORT checklist come supplementary material

---

## MOD-QN3 — Single-Subject Research

*Attivato quando: D1=b, D4=c (N < 10 o singolo caso)*

**Riferimenti:** Horner & Baer (1978); Parker et al. (2011); Kratochwill et al. (2013); What Works Clearinghouse (2020)

**Cos'è:** metodologia per studiare l'effetto di un intervento su uno o pochi individui attraverso misure ripetute nel tempo. Particolarmente usata in psicopedagogia speciale, BES, logopedia.

### FASE 1 — Ipotesi e RQ

> "Qual è il comportamento/abilità target che vuoi modificare?"
> "Qual è la baseline attuale (misura preliminare)?"
> "Qual è il cambiamento atteso dopo l'intervento?"

Formula la RQ come: *"L'intervento [X] produce un cambiamento nel [comportamento Y] di [partecipante/i Z] rispetto alla baseline?"*

Non si formulano H1/H0 nel senso tradizionale — la valutazione è visiva e tramite effect size non parametrici.

### FASE 2 — Design Single-Subject

**2a. Scelta del design:**

| Design | Struttura | Quando usarlo |
|--------|-----------|---------------|
| A-B | Baseline → Intervento | Pilota, quando il withdrawal non è etico |
| A-B-A | Baseline → Intervento → Ritorno baseline | Verifica che il cambiamento sia dovuto all'intervento |
| A-B-A-B | Baseline → Int. → Baseline → Int. | Più robusto, replica interna |
| Multiple Baseline | A-B staggered su più partecipanti/comportamenti/contesti | Quando il withdrawal non è possibile |

**Raccomandazione:** A-B-A-B o Multiple Baseline sono i design più robusti (WWC standard). A-B da solo non dimostra causalità.

**2b. Criteri di stabilità della baseline (obbligatori prima di iniziare l'intervento):**
- Minimo 3-5 punti dati stabili
- Variabilità < 20% della media
- Nessun trend nella direzione attesa dall'intervento

**2c. Definizione operazionale del comportamento target:**
Definisci in modo preciso e misurabile: *"Il comportamento X è definito come [descrizione precisa]. Si misura come [frequenza/durata/latenza/accuratezza] in [contesto specifico] durante [periodo di osservazione]."*

### FASE 3 — Strumenti

**Misura del comportamento target:** osservazione diretta con griglia strutturata. Definisci:
- Frequenza di campionamento (es. ogni sessione di 30 min)
- Chi osserva (inter-rater: κ ≥ .70)
- Strumento di registrazione (griglia, app, video)

Crea `design/fase-3-strumenti/griglia-osservazione.md` con la griglia di registrazione.

### FASE 4 — Procedura [→ §ETICA]

**Durata baseline:** continua fino a stabilità (vedi 2b). Non iniziare l'intervento prima.

**Durata intervento:** pianifica minimo 5-8 sessioni per fase.

**Fidelity check:** registra ogni sessione se possibile; usa checklist fidelity per ogni sessione.

### FASE 5 — Piano di analisi

**Analisi visiva del grafico (primaria):**
- Livello (media per fase)
- Trend (direzione e pendenza)
- Variabilità (range e stabilità)
- Immediatezza del cambiamento (overlap tra fasi)
- Latenza dell'effetto

**Effect size non parametrici:**
- **Tau-U** (Parker et al., 2011): preferito, gestisce trend in baseline. Calcolabile su singlecaseresearch.org
- **PND** (Percentage Non-Overlapping Data): % punti intervento che superano il massimo della baseline. PND > 90% = effetto molto efficace; 70-90% = moderato; < 70% = questionabile
- **IRD** (Improvement Rate Difference): alternativa a PND

Crea il grafico A-B-A-B con il software di scelta (Excel, R, JASP) e salvalo in `design/fase-5-analisi/grafico-single-subject.png`.

Scrivi `design/fase-5-analisi/piano-analisi.json` con `"paradigma": "single-subject"`, `"modulo": "MOD-QN3"`, `"effect_size": ["Tau-U", "PND"]`.

### FASE 6 — Preprint [→ §PREPRINT]

Usa struttura IMRAD adattata. Includi il grafico A-B-A-B nel paper. Riferisci gli standard WWC (What Works Clearinghouse) per il reporting.

---

## MOD-QN4 — Survey / Correlazionale

*Attivato quando: D1=b, D4=d (N grande, nessun intervento)*

**Riferimenti:** Fowler (2014); Field (2018); Dillman et al. (2014)

### FASE 1 — Ipotesi e RQ

Distingui:
- **Descrittivo:** "Qual è la distribuzione di [variabile] in [popolazione]?"
- **Correlazionale:** "Esiste una relazione tra [X] e [Y]?"
- **Predittivo:** "[X] predice [Y] controllando per [Z]?"

### FASE 2 — Design Survey

**2a. Tipo di survey:**
- *Cross-sectional:* un solo momento temporale — fotografia della situazione
- *Longitudinal panel:* stessi partecipanti nel tempo — cambiamento
- *Longitudinal cohort:* gruppo definito seguito nel tempo — sviluppo

**2b. Campionamento:**

| Tipo | Descrizione | Quando |
|------|-------------|--------|
| Casuale semplice | Ogni membro ha uguale probabilità | Lista completa disponibile |
| Stratificato | Sottogruppi proporzionali (es. per livello) | Vuoi rappresentare sottogruppi |
| A grappolo | Unità naturali (classi, scuole) | Lista individuale impossibile |
| Convenience | Partecipanti disponibili | Pilot, esplorativo |

Per survey educativi italiani il campionamento a grappolo (classi) è il più realistico.

**2c. Dimensionamento campione:**
- Per correlazione: N = [(z_α/2 + z_β) / (0.5 × ln((1+r)/(1-r)))]² + 3 → per r = .30, α = .05, potenza = .80: N ≈ 84
- Per regressione multipla: N ≥ 50 + 8k (dove k = numero predittori) → con 5 predittori: N ≥ 90
- Calcola su G*Power: `F tests → Linear Multiple Regression`

**2d. Tasso di risposta target:** ≥ 60% per survey online, ≥ 70% per paper. Pianifica follow-up (reminder email a T+7, T+14).

### FASE 3 — Strumenti

**Design del questionario:**
- Usa scale validate quando disponibili (vedi `references/domini-disciplinari.md`)
- Massimo 20-25 minuti di completamento
- Ordine: demografici → strumenti principali → domande aperte (opzionali)
- Pre-testa su 5-10 persone prima della somministrazione

**Piloting obbligatorio:**
> "Hai testato il questionario su 5-10 persone del target? Chiedi: (1) tempo di completamento, (2) item confusi, (3) domande offensive o non applicabili."

Riporta le modifiche post-pilot in `design/fase-3-strumenti/strumenti-valutazione.md`.

### FASE 4 — Procedura [→ §ETICA]

Piattaforme consigliate: Google Forms (gratuito, GDPR con impostazioni corrette), LimeSurvey (open source, self-hosted per massimo controllo GDPR), Qualtrics (istituzionale).

Documenta in `design/fase-4-procedura/timeline.md` le date di apertura, reminder e chiusura.

### FASE 5 — Piano di analisi

**Sequenza standard:**
1. Verifica assunzioni: normalità (Shapiro-Wilk se N < 50, Kolmogorov-Smirnov se N ≥ 50), outlier multivariati (distanza di Mahalanobis)
2. Statistiche descrittive: M, SD, range, skewness, kurtosis per ogni variabile
3. Affidabilità scale: α di Cronbach ≥ .70
4. Correlazioni: matrice Pearson o Spearman (non-normali)
5. Regressione multipla: verifica multicollinearità (VIF < 10), omoschedasticità residui
6. Eventuale analisi fattoriale esplorativa (EFA) se scale non validate: Principal Axis Factoring, rotazione Oblimin

Scrivi `design/fase-5-analisi/piano-analisi.json` con `"paradigma": "survey"`, `"modulo": "MOD-QN4"`.

### FASE 6 — Preprint [→ §PREPRINT]
```

- [ ] **Step 2: Verifica**

```bash
grep -n 'MOD-QN2\|MOD-QN3\|MOD-QN4' skills/research-design/SKILL.md | wc -l
# Atteso: almeno 6 righe
grep -n 'CONSORT' skills/research-design/SKILL.md
# Atteso: almeno 2 righe
grep -n 'Tau-U' skills/research-design/SKILL.md
# Atteso: almeno 1 riga
```

- [ ] **Step 3: Commit**

```bash
git add skills/research-design/SKILL.md
git commit -m "feat: research-design MOD-QN2 RCT, MOD-QN3 single-subject, MOD-QN4 survey"
```
