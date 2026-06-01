# Research-Design Skill MVP — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create `skills/research-design/` as a paradigm-agnostic replacement for `educational-pilot-design`, implementing Phase 0 (decision tree) and MOD-QN1 (quasi-experimental, migrated from existing skill), and updating pipeline integration.

**Architecture:** Single SKILL.md with unified Avvio section (session recovery, PRISMA check, RAG check), followed by Fase 0 decision tree, then the MOD-QN1 module containing 6 phases. Supporting files: `piano-analisi-schema.json` (JSON schema for handoff to data-analysis) and `references/normativa-it.md`. Two existing skills receive minimal updates: `educational-pilot-design` gets a deprecation notice and `pipeline-ricerca` gets Stage 3 updated.

**Tech Stack:** Markdown (skill files), JSON Schema (piano-analisi), PowerShell/Bash for file creation and verification, git for commits.

---

## File Map

| File | Action | Responsibility |
|------|--------|---------------|
| `skills/research-design/SKILL.md` | CREATE | Main skill — all phases, all content |
| `skills/research-design/piano-analisi-schema.json` | CREATE | JSON schema contract for data-analysis handoff |
| `skills/research-design/references/normativa-it.md` | CREATE | Italian regulatory references |
| `skills/educational-pilot-design/SKILL.md` | MODIFY line 1-4 | Add deprecation notice in frontmatter description |
| `skills/pipeline-ricerca/SKILL.md` | MODIFY lines 20-21, 82-98 | Replace `educational-pilot-design` refs with `research-design` |

---

### Task 1: Create directory structure and SKILL.md skeleton

**Files:**
- Create: `skills/research-design/SKILL.md`
- Create: `skills/research-design/references/` (directory)

- [ ] **Step 1: Create directory and skeleton file**

```powershell
New-Item -ItemType Directory -Force "skills/research-design/references"
```

Write `skills/research-design/SKILL.md` with this exact content:

```markdown
---
name: research-design
description: Usa quando occorre progettare uno studio di ricerca nell'ambito delle scienze dell'educazione. Supporta 11 paradigmi metodologici: quasi-sperimentale, RCT, single-subject, survey, fenomenologia, grounded theory, etnografia, narrativo, mixed-methods, action research, design-based research. Fase 0 guida la scelta del paradigma tramite decision tree. Contesto normativo italiano (MIUR, GDPR, L.104/92, L.170/2010). Non usare per revisioni sistematiche (usa prisma-review). Sostituisce educational-pilot-design.
---

# Progettazione della Ricerca — Scienze dell'Educazione

## Overview

Guida la progettazione rigorosa di studi di ricerca in tutti gli ambiti delle scienze dell'educazione. **A differenza di `educational-pilot-design`**, non presuppone alcun paradigma: la **Fase 0** identifica il paradigma appropriato tramite decision tree, poi attiva il modulo corrispondente.

**Paradigmi supportati (MVP):** MOD-QN1 (quasi-sperimentale). Gli altri moduli sono in sviluppo.

**Tipo di skill:** Rigida — segui le fasi nell'ordine indicato.

**Regola d'oro:** Non passare alla fase successiva senza conferma esplicita dell'utente. Conta come conferma: una risposta affermativa chiara, o la risposta completa alle domande della fase. Non conta: silenzio, risposta parziale, "capito". Se l'utente vuole saltare una fase, documenta la lacuna nel file e prosegui secondo la sua scelta.

---

## File generati dalla Skill

Tutti i file vengono creati all'interno della struttura di progetto unificata creata da `prisma-review` Fase 0.

```
{project-root}/
├── .project-state.json          ← master state pipeline (creato da prisma-review)
├── project-log.md               ← audit log append-only
└── design/
    ├── .research-state.json     ← state per-fase (creato da questa skill)
    ├── fase-0-paradigma/
    ├── fase-1-framework/
    ├── fase-2-design/
    ├── fase-3-strumenti/
    ├── fase-4-procedura/
    └── fase-5-analisi/
        └── piano-analisi.json   ← handoff → data-analysis
```

File prodotti da questa skill:
1. `design/.research-state.json` — stato machine-readable, aggiornato ad ogni fase
2. `project-log.md` — entry append-only per ogni decisione importante
3. `design/protocollo_ricerca.md` — protocollo completo (equiv. al vecchio protocollo_ricerca.md)
4. `design/strumenti_valutazione.md` — strumenti scelti con schede
5. `design/timeline_pilota.md` — cronoprogramma
6. `design/fase-5-analisi/piano-analisi.json` — piano analisi strutturato (handoff)
7. `design/preprint_bozza.md` — bozza paper IMRAD

<!-- PLACEHOLDER: Avvio section — Task 2 -->

<!-- PLACEHOLDER: Fase 0 — Task 3 -->

<!-- PLACEHOLDER: MOD-QN1 — Tasks 4-9 -->

<!-- PLACEHOLDER: Errori e Best Practices — Task 9 -->
```

- [ ] **Step 2: Verify file created**

```powershell
Test-Path "skills/research-design/SKILL.md"
(Get-Content "skills/research-design/SKILL.md" | Measure-Object -Line).Lines
```

Expected: `True` and line count > 50.

- [ ] **Step 3: Commit skeleton**

```bash
git add skills/research-design/
git commit -m "feat(research-design): create skill directory and SKILL.md skeleton"
```

---

### Task 2: Write Avvio section (session recovery, context setup)

**Files:**
- Modify: `skills/research-design/SKILL.md` — replace `<!-- PLACEHOLDER: Avvio section — Task 2 -->`

- [ ] **Step 1: Replace Avvio placeholder in SKILL.md**

Find `<!-- PLACEHOLDER: Avvio section — Task 2 -->` and replace with:

```markdown
---

## Avvio

### Ripresa di sessione (priorità assoluta)

**Prima di tutto**, controlla lo stato del progetto in questo ordine:

1. Esiste `.project-state.json` nella cartella corrente (o nella cartella padre)?
   - Sì → leggi `current_phase` e lo stato di ogni fase.
   - No ma esiste `prisma_state.json` (vecchia struttura) → auto-migra: crea `.project-state.json` con i campi inferiti, aggiungi entry `[AUTO-MIGRATED]` a `project-log.md`.
   - No → avvisa: *"Nessun progetto trovato. Questa skill richiede una struttura di progetto creata da `prisma-review`. Vuoi avviare un nuovo progetto?"* Se sì → crea la struttura manualmente.

2. Esiste `design/.research-state.json`?
   - Sì → leggi `current_phase` e `paradigm`. Dichiara: *"Ho trovato una sessione attiva. Paradigma: [MOD-XX]. Fase corrente: [N]/6. Confermo di riprendere da lì?"*
   - No → avvia da Fase 0.

**Non riformulare mai decisioni già prese** senza esplicita richiesta dell'utente.

### Livello scolastico e contesto

> "Lo studio si svolge in: (a) scuola dell'infanzia, (b) primaria, (c) secondaria I grado, (d) secondaria II grado, (e) università / alta formazione, (f) formazione professionale / IeFP, (g) contesto internazionale?"

| Livello | Implicazioni principali |
|---|---|
| Infanzia (0-6) | Consenso genitori, routine pedagogica, osservazione come metodo primario, no self-report |
| Primaria (6-11) | Consenso genitori, L.170/2010 se DSA, L.104/92 se disabilità, coordinamento team docenti |
| Secondaria I (11-14) | Consenso genitori (minori), PEI/PDP se BES, consiglio di classe |
| Secondaria II (14-19) | Consenso genitori (fino a 18), studenti coinvolti attivamente nel consenso |
| Università | GDPR adulti, eventuale Comitato Etico di Ateneo, consenso autonomo |
| Formazione prof. | Verifica minori/adulti, ente gestore (IeFP/CFP), normativa regionale |
| Internazionale | Applica normativa locale; documenta differenze rispetto al framework italiano |

Dichiara: *"Contesto identificato: [livello]. Adatto le raccomandazioni di conseguenza."*

### Profilo disciplinare

> "In quale ambito si colloca principalmente la ricerca?
> (a) Ed-Tech — tecnologie didattiche, AI, HCI per l'apprendimento
> (b) Psicopedagogia / Pedagogia speciale — BES, DSA, disabilità, inclusione
> (c) Didattica disciplinare — metodologie di insegnamento per una disciplina
> (d) Pedagogia generale / Teoria dell'educazione
> (e) Valutazione educativa — assessment, misurazione degli apprendimenti
> (f) Formazione docenti e sviluppo professionale
> (g) Misto o non classificabile — descrivi brevemente"

Registra in `.research-state.json` come `"profilo": "[lettera + etichetta]"`.

### Verifica report PRISMA

Cerca `prisma/prisma_synthesis.md` (struttura unificata) o `prisma_synthesis.md` (vecchia struttura). Se non esiste, chiedi: *"Hai già un report di revisione sistematica? Se sì, indicami nome o percorso del file."*

Se il file esiste:
- Verifica che la sezione **OUTPUT PER PILOT STUDY** sia compilata. Se è vuota → avvisa che la pre-compilazione automatica non è possibile.
- Se compilata → estrai: effect size aggregati, framework dominante, strumenti più usati, RQ aperte, gap di popolazione, durata tipica interventi. Comunica cosa hai trovato e chiedi conferma.

### Verifica RAG

Controlla se esiste `rag_db/` nella cartella di progetto. Se sì → informa che è disponibile `py hybrid_rag.py query "<costrutto>" --n 3` nelle fasi successive.

Presenta all'utente: il paradigma che verrà selezionato in Fase 0, la struttura cartelle che verrà usata, i file che verranno prodotti. Poi avvia la **Fase 0**.
```

- [ ] **Step 2: Verify section added**

```powershell
Select-String -Path "skills/research-design/SKILL.md" -Pattern "## Avvio"
Select-String -Path "skills/research-design/SKILL.md" -Pattern "Ripresa di sessione"
Select-String -Path "skills/research-design/SKILL.md" -Pattern "Verifica RAG"
```

Expected: 3 matches found.

- [ ] **Step 3: Commit**

```bash
git add skills/research-design/SKILL.md
git commit -m "feat(research-design): add Avvio section with session recovery and context setup"
```

---

### Task 3: Write Fase 0 — Decision Tree

**Files:**
- Modify: `skills/research-design/SKILL.md` — replace `<!-- PLACEHOLDER: Fase 0 — Task 3 -->`

- [ ] **Step 1: Replace Fase 0 placeholder**

Find `<!-- PLACEHOLDER: Fase 0 — Task 3 -->` and replace with:

```markdown
---

## FASE 0: Selezione del Paradigma

**Obiettivo:** Identificare il paradigma di ricerca più appropriato tramite 5 domande di routing. Poni le domande **una alla volta**, attendi la risposta.

### Q1 — Qual è il tuo obiettivo primario?

> "Cosa vuoi ottenere con questa ricerca?"
> (a) **Comprendere** — esplorare esperienze, significati, processi soggettivi
> (b) **Misurare** — quantificare un effetto, confrontare gruppi, stimare grandezze
> (c) **Migliorare** — risolvere un problema pratico in collaborazione con i partecipanti
> (d) **Progettare** — creare e testare iterativamente un artefatto educativo (app, curricolo, metodologia)

### Q2 — Qual è lo stato della conoscenza nell'area?

> "Quanto è consolidata la letteratura su questo fenomeno?"
> (a) **Consolidata** — esistono meta-analisi, studi RCT, framework teorici condivisi
> (b) **Emergente** — esistono studi preliminari, teorie parziali, descrizioni fenomenologiche
> (c) **Inesistente** — fenomeno poco esplorato, nessuna teoria di riferimento

### Q3 — Che tipo di outcome ti aspetti?

> "Come prevedi di rappresentare i risultati?"
> (a) **Quantitativo** — numeri, statistiche, misure, confronti tra gruppi
> (b) **Qualitativo** — descrizioni, temi, narrazioni, significati
> (c) **Entrambi** — integrazione di dati numerici e testuali

### Q4 — Hai vincoli pratici?

> "Ci sono limitazioni che condizionano il design?"
> (a) **No randomizzazione** — non puoi assegnare casualmente i partecipanti ai gruppi
> (b) **N piccolo** — meno di 10 partecipanti per gruppo
> (c) **N grande** — più di 100 partecipanti
> (d) **Nessun vincolo rilevante**

### Q5 — Hai bisogno di sequenza temporale?

> "Come si svolge lo studio nel tempo?"
> (a) **Cross-sectional** — misure in un unico punto temporale
> (b) **Longitudinale** — misure ripetute nel tempo sugli stessi soggetti
> (c) **Iterativo** — cicli ripetuti di intervento/revisione/intervento

---

### Routing Table

| Q1 | Q2 | Q3 | Q4 | Q5 | Paradigma → Modulo |
|----|----|----|----|----|---------------------|
| misurare | qualsiasi | quantitativo | no rand. | qualsiasi | **MOD-QN1** Quasi-sperimentale ✅ |
| misurare | qualsiasi | quantitativo | nessuno | qualsiasi | **MOD-QN2** RCT 🚧 |
| misurare | qualsiasi | quantitativo | N piccolo | qualsiasi | **MOD-QN3** Single-Subject 🚧 |
| misurare | qualsiasi | quantitativo | N grande | cross | **MOD-QN4** Survey 🚧 |
| comprendere | emergente | qualitativo | qualsiasi | qualsiasi | **MOD-Q1** Fenomenologia 🚧 |
| comprendere | inesistente | qualitativo | qualsiasi | qualsiasi | **MOD-Q2** Grounded Theory 🚧 |
| comprendere | qualsiasi | qualitativo | qualsiasi | longitudinale | **MOD-Q3** Etnografia 🚧 |
| comprendere | qualsiasi | qualitativo | qualsiasi | qualsiasi | **MOD-Q4** Narrativo 🚧 |
| qualsiasi | qualsiasi | entrambi | qualsiasi | qualsiasi | **MOD-MM** Mixed-Methods 🚧 |
| migliorare | qualsiasi | qualsiasi | qualsiasi | iterativo | **MOD-AR** Action Research 🚧 |
| progettare | qualsiasi | qualsiasi | qualsiasi | iterativo | **MOD-DBR** Design-Based 🚧 |

**Legenda:** ✅ Implementato | 🚧 In sviluppo (non ancora disponibile)

Se il paradigma raccomandato ha 🚧, avvisa l'utente e chiedi se:
- Vuole usare MOD-QN1 come approssimazione (solo se il contesto lo permette)
- Preferisce attendere l'implementazione del modulo
- Vuole descrivere il suo caso perché tu possa guidarlo manualmente

---

### Azione Fase 0

Dopo il routing, prima di procedere al modulo:

1. **Presenta il risultato:** *"In base alle tue risposte, il paradigma raccomandato è [MOD-XX] — [nome]. Vuoi procedere con questo paradigma, o esaminare le alternative?"*

2. **Aggiorna `design/.research-state.json`** (crealo se non esiste):

```json
{
  "current_phase": 0,
  "completed_phases": [0],
  "paradigm": "MOD-QN1",
  "paradigm_label": "Quasi-sperimentale",
  "routing_answers": {
    "q1_obiettivo": "misurare",
    "q2_conoscenza": "consolidata",
    "q3_outcome": "quantitativo",
    "q4_vincoli": "no_randomizzazione",
    "q5_sequenza": "cross-sectional"
  },
  "livello": null,
  "profilo": null,
  "sample_size": null,
  "framework_selected": null,
  "last_updated": "[ISO8601]"
}
```

3. **Aggiungi entry a `project-log.md`**:

```markdown
## [ISO8601] research-design | Fase 0 — Paradigma selezionato
**Paradigma:** MOD-QN1 — Quasi-sperimentale
**Rationale:** [sintesi delle risposte Q1-Q5]
**Alternative considerate:** [se l'utente ha discusso alternative]
```

4. **Aggiorna `.project-state.json`**: imposta `"research-design": {"status": "in_progress", "started_at": "[ISO8601]"}`.

5. Avvia **MOD-QN1 — Fase 1**.
```

- [ ] **Step 2: Verify Fase 0 section**

```powershell
Select-String -Path "skills/research-design/SKILL.md" -Pattern "FASE 0"
Select-String -Path "skills/research-design/SKILL.md" -Pattern "Routing Table"
Select-String -Path "skills/research-design/SKILL.md" -Pattern "research-state.json"
```

Expected: 3 matches found.

- [ ] **Step 3: Commit**

```bash
git add skills/research-design/SKILL.md
git commit -m "feat(research-design): add Fase 0 decision tree with routing table and state update"
```

---

### Task 4: Write MOD-QN1 — Fase 1 (Framework e Ipotesi)

**Files:**
- Modify: `skills/research-design/SKILL.md` — replace `<!-- PLACEHOLDER: MOD-QN1 — Tasks 4-9 -->`

- [ ] **Step 1: Replace MOD-QN1 placeholder with header + Fase 1**

Find `<!-- PLACEHOLDER: MOD-QN1 — Tasks 4-9 -->` and replace with:

```markdown
---

## MOD-QN1: Studio Quasi-Sperimentale

> **Attivato quando:** Q1=misurare, Q3=quantitativo, Q4=no randomizzazione.
>
> Copre studi quasi-sperimentali pre-test/post-test con gruppo di controllo non equivalente, within-subjects, e wait-list design. Contesto: tutti i livelli scolastici italiani.

---

### MOD-QN1 — FASE 1: Framework e Ipotesi

Poni le domande **una alla volta**, attendi la risposta prima di passare alla successiva.

1. **Obiettivo principale** — Distingui obiettivi di *fattibilità* (es. "verificare che lo strumento funzioni con studenti BES") da obiettivi di *efficacia* (es. "migliorare il punteggio MSLQ"). Nel pilot, la fattibilità è primaria.

2. **Framework teorico** — Se non sa come scegliere, proponi i 2-3 framework più usati nel suo dominio con il razionale:

   | Profilo | Framework consigliati |
   |---------|----------------------|
   | Ed-Tech | TPACK (Mishra & Koehler), TAM (Davis), SRL/Zimmerman |
   | Psicopedagogia speciale | UDL (CAST), ICF-CY, Bronfenbrenner |
   | Didattica disciplinare | Inquiry-based learning, Bloom's Taxonomy, CLT (Sweller) |
   | Valutazione | Assessment for Learning, Hattie Visible Learning |
   | Formazione docenti | PCK (Shulman), Reflexive Practice (Schön) |

3. **Domande di ricerca (RQ) e ipotesi** — Template:
   ```
   RQ1: [Variabile dipendente] dei/delle [partecipanti] che ricevono [intervento]
        differisce significativamente rispetto al gruppo di controllo dopo [N] settimane?
   H1:  Il gruppo sperimentale mostrerà [outcome] significativamente maggiore (d ≥ [valore]).
   H0:  Non vi è differenza significativa tra i gruppi (d ≈ 0).
   ```
   Usa l'effect size da PRISMA se disponibile; altrimenti d = 0.5 (dichiara che è stima conservativa).

4. **Popolazione e campione previsto** — es. 2 classi terze di liceo, N = 40.

Se è disponibile `prisma/prisma_synthesis.md`, estrai e usa: gap identificato (→ motivazione), framework emergente (→ integra punto 2), RQ aperte (→ affina ipotesi), durata interventi (→ orienta Fase 4).

**Azione:** Crea `design/protocollo_ricerca.md` con sezioni: Introduzione, Framework Teorico, Obiettivi, Ipotesi, Partecipanti. Aggiorna `.research-state.json`: `"current_phase": 1, "completed_phases": [0, 1], "framework_selected": "[nome]"`. Aggiungi entry a `project-log.md`. Chiedi conferma.

<!-- PLACEHOLDER: Fase 2 — Task 5 -->
<!-- PLACEHOLDER: Fase 3 — Task 6 -->
<!-- PLACEHOLDER: Fase 4 — Task 7 -->
<!-- PLACEHOLDER: Fase 5 — Task 8 -->
<!-- PLACEHOLDER: Fase 6 — Task 9 -->
```

- [ ] **Step 2: Verify**

```powershell
Select-String -Path "skills/research-design/SKILL.md" -Pattern "MOD-QN1"
Select-String -Path "skills/research-design/SKILL.md" -Pattern "FASE 1: Framework"
Select-String -Path "skills/research-design/SKILL.md" -Pattern "Variabile dipendente"
```

Expected: 3 matches.

- [ ] **Step 3: Commit**

```bash
git add skills/research-design/SKILL.md
git commit -m "feat(research-design): add MOD-QN1 header and Fase 1 framework/ipotesi"
```

---

### Task 5: Write MOD-QN1 — Fase 2 (Design della Ricerca)

**Files:**
- Modify: `skills/research-design/SKILL.md` — replace `<!-- PLACEHOLDER: Fase 2 — Task 5 -->`

- [ ] **Step 1: Replace Fase 2 placeholder**

Find `<!-- PLACEHOLDER: Fase 2 — Task 5 -->` and replace with:

```markdown

---

### MOD-QN1 — FASE 2: Design della Ricerca

**2a. Tipo di Design**

- *Quasi-sperimentale Pre-test/Post-test con Gruppo di Controllo* (se 2+ classi/gruppi)
- *Within-subjects* (un solo gruppo, crossover o misure ripetute)
- *Wait-list* (se privare il controllo dell'intervento è eticamente problematico)

Avvisi metodologici:
- **Non-equivalenza gruppi:** verifica equivalenza baseline (t-test o ANCOVA sul pre-test).
- **Testing effect:** il pre-test può sensibilizzare i partecipanti — valuta design Solomon a 4 gruppi.
- **Attrition differenziale:** il dropout non casuale invalida i confronti — pianifica strategia a priori (intention-to-treat vs per-protocol).
- **Wait-list design:** se privare il controllo è eticamente problematico (frequente in inclusione/BES), usa wait-list — il controllo riceve lo stesso intervento in un secondo momento.

**2b. Componente Qualitativa Opzionale**

Se il ricercatore vuole spiegare risultati inattesi, proponi *Explanatory Sequential*: prima quantitativo, poi qualitativo per interpretare. Documenta nel protocollo ma rimani in MOD-QN1 (non passare a MOD-MM a meno che la componente qualitativa non sia primaria).

**2c. Variabili**
- **Variabile Indipendente (VI):** l'intervento (approccio didattico, tecnologia, programma)
- **Variabili Dipendenti (VD):** outcome misurabili coerenti con il framework teorico
- **Covariate:** sesso, background socioeconomico, conoscenze pregresse, diagnosi BES/DSA se rilevante

**2d. Power Analysis**

Nel pilot, la power analysis stima l'effect size per lo studio completo — non garantisce potenza del pilot stesso.

- **Dimensionamento pilot:** N = 12–15 per arm è sufficiente (Julious, 2005). Se inferiore, dichiara esplicitamente che la potenza è insufficiente per conclusioni sull'efficacia.
- **Dimensionamento studio completo:** G*Power → `F tests` → ANOVA: inserisci d da PRISMA (o 0.5), α = .05, potenza = .80 → ottieni N per gruppo.
- Riporta: *"Per rilevare d = [X] con α = .05 e potenza = .80, lo studio completo richiede N = [Y] per gruppo (G*Power 3.1)."*

**2e. Criteri di Fattibilità e Go/No-Go (OBBLIGATORIO)**

| Criterio | Soglia suggerita | Soglia scelta |
|---|---|---|
| Tasso di reclutamento | ≥ 70% dei partecipanti invitati | |
| Tasso di ritenzione | ≥ 80% completa lo studio | |
| Completezza dati | ≥ 85% dei questionari validi | |
| Fidelity dell'intervento | ≥ 75% delle sessioni completate | |
| Accettabilità strumenti | ≥ 80% completa senza problemi segnalati | |

Definisci quanti criteri devono essere soddisfatti per procedere. Registra in `.research-state.json`: `"go_nogo_defined": true`.

**2f. Stopping Rules (OBBLIGATORIO)**

- Dropout > [X]% nella prima settimana → revisione protocollo
- α Cronbach < .50 al pre-test → strumento inutilizzabile
- Evento avverso: malessere psicologico riportato dai partecipanti
- Per BES/inclusione: rifiuto del PEI di supportare l'intervento, ritiro da parte della famiglia
- [Condizione specifica per il contesto — definita con l'utente]

**Azione:** Aggiorna `design/protocollo_ricerca.md` sezioni: Research Design, Variabili, Power Analysis, Criteri Fattibilità, Stopping Rules. Aggiorna `.research-state.json`: `"current_phase": 2`. Aggiungi entry `project-log.md`. Chiedi conferma.

<!-- PLACEHOLDER: Fase 3 — Task 6 -->
```

- [ ] **Step 2: Verify**

```powershell
Select-String -Path "skills/research-design/SKILL.md" -Pattern "FASE 2: Design"
Select-String -Path "skills/research-design/SKILL.md" -Pattern "Go/No-Go"
Select-String -Path "skills/research-design/SKILL.md" -Pattern "Stopping Rules"
```

Expected: 3 matches.

- [ ] **Step 3: Commit**

```bash
git add skills/research-design/SKILL.md
git commit -m "feat(research-design): add MOD-QN1 Fase 2 design/power analysis/go-nogo"
```

---

### Task 6: Write MOD-QN1 — Fase 3 (Strumenti e Misure)

**Files:**
- Modify: `skills/research-design/SKILL.md` — replace `<!-- PLACEHOLDER: Fase 3 — Task 6 -->`

- [ ] **Step 1: Replace Fase 3 placeholder**

Find `<!-- PLACEHOLDER: Fase 3 — Task 6 -->` and replace with:

```markdown

---

### MOD-QN1 — FASE 3: Strumenti e Misure

**3a. Misure Quantitative**

Per ogni strumento: dichiara *"verificare item, sottoscale e disponibilità versione italiana validata dalla fonte primaria."* Non affidarti alla memoria del modello per i dettagli psicometrici.

**REGOLA:** Non affermare mai che esiste una versione italiana validata senza conferma dell'utente.

Per ogni strumento scelto, verifica:
- **Affidabilità:** α di Cronbach ≥ .70 — da verificare sui propri dati
- **Validità di costrutto** (convergente e discriminante)
- Preferisci versioni tradotte e validate in italiano

**3b. Misure Qualitative (se presente componente Explanatory Sequential)**

Adatta all'età e al livello:
- Infanzia / primaria bassa: osservazione strutturata, colloqui con docenti (no self-report)
- Primaria alta / secondaria I: focus group con domande concrete e brevi
- Secondaria II / università: interviste semi-strutturate standard

Prevedi inter-rater agreement (Cohen's κ ≥ .70) se il coding è svolto da più ricercatori.

**3c. Learning Analytics e Log di Sistema (se applicabile)**

Per studi Ed-Tech con chatbot o piattaforme AI:
- Definisci a priori cosa conservi: solo metadati (N prompt, durata sessioni) o contenuto conversazioni
- Se conservi il contenuto: anonimizzazione obbligatoria; base giuridica esplicita nel consenso
- Per minori: la scelta va dichiarata in modo comprensibile nel modulo consenso ai genitori

**Azione:** Crea `design/strumenti_valutazione.md` con una scheda per ogni strumento (nome, riferimento, N item, scoring, versione italiana, α atteso, note). Aggiorna `.research-state.json`: `"current_phase": 3`. Aggiungi entry `project-log.md`. Chiedi conferma.

<!-- PLACEHOLDER: Fase 4 — Task 7 -->
```

- [ ] **Step 2: Verify**

```powershell
Select-String -Path "skills/research-design/SKILL.md" -Pattern "FASE 3: Strumenti"
Select-String -Path "skills/research-design/SKILL.md" -Pattern "Learning Analytics"
Select-String -Path "skills/research-design/SKILL.md" -Pattern "strumenti_valutazione"
```

Expected: 3 matches.

- [ ] **Step 3: Commit**

```bash
git add skills/research-design/SKILL.md
git commit -m "feat(research-design): add MOD-QN1 Fase 3 strumenti e misure"
```

---

### Task 7: Write MOD-QN1 — Fase 4 (Procedura e Intervento)

**Files:**
- Modify: `skills/research-design/SKILL.md` — replace `<!-- PLACEHOLDER: Fase 4 — Task 7 -->`

- [ ] **Step 1: Replace Fase 4 placeholder**

Find `<!-- PLACEHOLDER: Fase 4 — Task 7 -->` and replace with:

```markdown

---

### MOD-QN1 — FASE 4: Procedura e Intervento

1. **Ruolo del ricercatore e del docente** — chi somministra, chi osserva, chi supporta l'intervento?

2. **Durata e calendario** — adatta al contesto:
   - Scuola secondaria: evita scrutini (febbraio, giugno), orientamento, settimane pre-esame. Pilot realistico: 3–5 settimane effettive.
   - Università: evita sessioni d'esame. Pilot realistico: 4–6 settimane in periodo didattico.
   - Infanzia / primaria: coordina con programmazione annuale; festività e uscite scolastiche.
   - Contesti inclusivi: coordina con le ore di sostegno, PEI, GLI.

3. **Gruppo di controllo** — cosa fa mentre il gruppo sperimentale riceve l'intervento? Se privarlo è eticamente problematico → usa wait-list design.

4. **Fidelity check** — come verifichi che l'intervento sia somministrato come previsto? (log di accesso, checklist docente, osservazione in classe, registrazione audio con consenso)

5. **Vincoli normativi** — vedi `references/normativa-it.md` per la lista completa di autorizzazioni richieste per il livello identificato.

   Chiedi: *"Vuoi che generi un modulo di consenso informato per [genitori / partecipanti adulti]?"* Se sì, genera il documento includendo: intestazione istituto, descrizione in linguaggio non tecnico, dati raccolti e finalità, diritti del partecipante (art. 15-22 GDPR), firma + data. Avvisa che il testo va verificato dal DPO o legale dell'istituto prima dell'uso.

**Azione:** Crea `design/timeline_pilota.md` con cronoprogramma settimanale:
```
Settimana 1: Pre-test + Onboarding
Settimane 2–[N]: Intervento (fidelity check a metà)
Ultima settimana: Post-test + Interviste/Focus group (se previsti)
```
Aggiorna `design/protocollo_ricerca.md`. Aggiorna `.research-state.json`: `"current_phase": 4`. Aggiungi entry `project-log.md`. Chiedi conferma.

<!-- PLACEHOLDER: Fase 5 — Task 8 -->
```

- [ ] **Step 2: Verify**

```powershell
Select-String -Path "skills/research-design/SKILL.md" -Pattern "FASE 4: Procedura"
Select-String -Path "skills/research-design/SKILL.md" -Pattern "Fidelity check"
Select-String -Path "skills/research-design/SKILL.md" -Pattern "timeline_pilota"
```

Expected: 3 matches.

- [ ] **Step 3: Commit**

```bash
git add skills/research-design/SKILL.md
git commit -m "feat(research-design): add MOD-QN1 Fase 4 procedura e intervento"
```

---

### Task 8: Write MOD-QN1 — Fase 5 (Piano di Analisi + piano-analisi.json)

**Files:**
- Modify: `skills/research-design/SKILL.md` — replace `<!-- PLACEHOLDER: Fase 5 — Task 8 -->`

- [ ] **Step 1: Replace Fase 5 placeholder**

Find `<!-- PLACEHOLDER: Fase 5 — Task 8 -->` and replace with:

```markdown

---

### MOD-QN1 — FASE 5: Piano di Analisi

**5a. Analisi Quantitativa**
- ANCOVA (controllando pre-test e covariate) per confronto tra gruppi
- t-test appaiati per within-subjects
- Riporta sempre effect size (Cohen's d o η²) e IC 95%
- **Missing data:** definisci strategia a priori (listwise deletion solo se MCAR verificato; altrimenti multiple imputation o FIML)
- Verifica assunzioni ANCOVA: normalità residui, omoschedasticità, omogeneità dei pendii di regressione
- Per campioni piccoli (tipici dei pilot): valuta test non parametrici (Mann-Whitney U, Wilcoxon)

**5b. Analisi Qualitativa (se presente componente Explanatory Sequential)**

Thematic Analysis Riflessiva (Braun & Clarke, 2006; 2021) — 6 step:

1. **Familiarizzazione** — Trascrivi verbatim. Leggi il corpus più volte. Note iniziali.
2. **Coding** — Etichetta ogni estratto rilevante. Rifletti su come il tuo background influenza i codici.
3. **Generazione temi** — Raggruppa codici in temi potenziali che catturano qualcosa di significativo.
4. **Revisione temi** — Verifica coerenza interna e distinzione tra temi.
5. **Definizione e denominazione** — Scrivi una definizione chiara per ogni tema.
6. **Scrittura** — Narrativa per ogni tema con 2-3 citazioni esemplificative.

Inter-rater agreement: Cohen's κ ≥ .70 dopo step 2 (se disponibile secondo codificatore).

**5c. Pre-registrazione OSF (OBBLIGATORIO)**

Pre-registra su osf.io → Registrations → New Registration **prima** della raccolta dati. Campi minimi:
- Titolo, autori, ipotesi (H1/H0 per ogni RQ)
- Design, N previsto, criteri inclusione/esclusione
- Variabili IV/DV/covariate
- Piano di analisi (test, soglia α, strategia missing data)
- Criteri go/no-go + stopping rules (da Fase 2e-2f)

Include il link OSF nel paper. Le analisi esplorative non pre-registrate vanno dichiarate come tali.

**5d. Considerazioni Etiche**
- Consenso informato (genitori per minori, partecipanti per adulti, tutori legali per disabilità grave)
- Approvazione Dirigente Scolastico / Comitato Etico di Ateneo
- GDPR: anonimizzazione, finalità limitata, conservazione temporanea definita
- Per contesti inclusivi: coordinamento con PEI/PDP, équipe multidisciplinare, famiglia

**5e. Generazione piano-analisi.json (OBBLIGATORIO — Handoff a data-analysis)**

Al termine di questa fase, genera `design/fase-5-analisi/piano-analisi.json`:

```json
{
  "paradigm": "MOD-QN1",
  "paradigm_label": "Quasi-sperimentale",
  "research_questions": [
    {
      "id": "RQ1",
      "text": "[testo RQ dall'utente]",
      "h1": "[H1 dall'utente]",
      "h0": "[H0 dall'utente]"
    }
  ],
  "variables": {
    "independent": [
      {"name": "[nome VI]", "description": "[descrizione intervento]", "levels": ["sperimentale", "controllo"]}
    ],
    "dependent": [
      {"name": "[nome VD]", "scale": "interval", "instrument": "[strumento da Fase 3]", "cronbach_expected": 0.75}
    ],
    "covariates": [
      {"name": "[covariata]", "rationale": "[perché inclusa]"}
    ]
  },
  "tests": [
    {
      "test": "ANCOVA",
      "software": "JASP",
      "assumptions": ["normality", "homogeneity_of_variance", "homogeneity_of_regression_slopes"],
      "effect_size": "partial_eta_squared",
      "report_format": "F(df1, df2) = X, p = .XX, η²p = .XX, IC 95%"
    }
  ],
  "missing_data_strategy": "FIML",
  "osf_preregistration_url": "[link OSF o null]",
  "data_format": "XLSX",
  "go_nogo_criteria": {
    "recruitment_rate": 0.70,
    "retention_rate": 0.80,
    "data_completeness": 0.85,
    "fidelity": 0.75,
    "instrument_acceptability": 0.80,
    "min_criteria_met": 5
  }
}
```

Compila tutti i campi con i valori reali raccolti nelle fasi precedenti. Non lasciare campi nulli se il dato è disponibile.

**Azione:** Completa `design/protocollo_ricerca.md`. Crea `design/fase-5-analisi/piano-analisi.json`. Aggiorna `.research-state.json`: `"current_phase": 5`. Aggiungi entry `project-log.md`. Chiedi conferma.

<!-- PLACEHOLDER: Fase 6 — Task 9 -->
```

- [ ] **Step 2: Verify**

```powershell
Select-String -Path "skills/research-design/SKILL.md" -Pattern "FASE 5: Piano"
Select-String -Path "skills/research-design/SKILL.md" -Pattern "piano-analisi.json"
Select-String -Path "skills/research-design/SKILL.md" -Pattern "Pre-registrazione OSF"
```

Expected: 3 matches.

- [ ] **Step 3: Commit**

```bash
git add skills/research-design/SKILL.md
git commit -m "feat(research-design): add MOD-QN1 Fase 5 piano analisi e piano-analisi.json handoff"
```

---

### Task 9: Write MOD-QN1 — Fase 6, Errori Comuni, Best Practices

**Files:**
- Modify: `skills/research-design/SKILL.md` — replace Fase 6 + Errori placeholders, remove Errori placeholder

- [ ] **Step 1: Replace Fase 6 placeholder**

Find `<!-- PLACEHOLDER: Fase 6 — Task 9 -->` and replace with:

```markdown

---

### MOD-QN1 — FASE 6: Preprint e Roadmap Post-Pilot

**Recap di coerenza (obbligatorio prima di scrivere)**

Leggi tutti i file prodotti e verifica:
- Il framework teorico (Fase 1) è coerente con gli strumenti scelti (Fase 3)?
- Le RQ (Fase 1) sono coperte dal piano di analisi (Fase 5)?
- La procedura (Fase 4) è compatibile con la timeline prodotta?
- I criteri go/no-go e le stopping rules (Fase 2e-2f) sono nel protocollo?

Se trovi incoerenze, segnalale prima di procedere.

**Decisioni obbligatorie:**
1. *"Il preprint sarà in italiano o in inglese?"*
2. *"Che tipo di documento: Protocol Paper (prima dei dati), Results Paper (dopo), o Registered Report?"*

| Tipo | File di struttura |
|---|---|
| Protocol paper | `imrad-protocol-paper.md` nella vecchia skill (clona da `skills/educational-pilot-design/`) |
| Results paper | `imrad-results-paper.md` nella vecchia skill |

Per il **Results Paper** (guida statistiche):
- Descrittive: M, SD, range per ogni variabile e gruppo
- Test equivalenza baseline tra i gruppi
- ANCOVA: F(df1, df2) = X, p = .XX, η²p = .XX, IC 95%; Cohen's d = 2t/√(df)
- α Cronbach dai propri dati (confronta con valori attesi)
- Thematic Analysis: N temi, N codici, κ inter-rater (se disponibile)

**Guardrail anti-allucinazione:** usa `py hybrid_rag.py query "<costrutto>" --n 3` per ogni sezione che cita letteratura (se RAG disponibile). Usa `[CITARE: autore/anno da verificare]` per tutte le citazioni.

**Roadmap Post-Pilot (OBBLIGATORIO)**

Aggiungi in `design/protocollo_ricerca.md` sezione finale:

```markdown
## Roadmap Post-Pilot

### Criteri per procedere allo studio completo
[Lista criteri go/no-go con soglie da Fase 2e]

### Modifiche previste in base ai risultati del pilot
- Se [criterio X non soddisfatto] → [modifica prevista]
- Se [strumento Y: α < .70] → [sostituzione / adattamento]
- Se [fidelity < 75%] → [revisione procedura]

### Dimensionamento studio completo
N = [Y] per gruppo (G*Power, d = [X], α = .05, potenza = .80)
Da aggiornare con effect size reale osservato nel pilot.

### Timeline orientativa studio completo
[Stima: es. 12–18 mesi dalla conclusione del pilot]

### Prossimi passi per finanziamento
[es. bando PRIN, fondi europei Horizon, accordo scuola-ateneo]
```

**Preprint servers:**

| Server | Disciplina | Note |
|---|---|---|
| EdArXiv (edarxiv.org) | Educazione, didattica | Specifico per ricerca educativa |
| PsyArXiv (psyarxiv.com) | Psicologia, psicopedagogia | Per apprendimento e sviluppo |
| OSF Preprints (osf.io) | Tutti | Integrato con pre-registrazione |

**Checklist qualità:**
- [ ] Titolo include: design, popolazione, intervento, outcome
- [ ] Abstract strutturato con tutte le sezioni
- [ ] Framework teorico citato con riferimenti primari
- [ ] Strumenti citati con riferimento originale
- [ ] Power analysis con parametri espliciti e distinzione pilot/studio completo
- [ ] Criteri go/no-go e stopping rules dichiarati
- [ ] Piano analisi pre-specificato (no HARKing)
- [ ] Etica e GDPR dichiarati; link OSF se pre-registrato
- [ ] Roadmap post-pilot inclusa nel protocollo

**Azione:** Genera `design/preprint_bozza.md`. Aggiorna `.research-state.json`: `"current_phase": 6, "completed_phases": [0,1,2,3,4,5,6]`. Aggiorna `.project-state.json`: `"research-design": {"status": "completed", "completed_at": "[ISO8601]"}`. Aggiungi entry finale a `project-log.md`. Chiedi se esportare in Word → suggerisci: `pandoc design/preprint_bozza.md -o design/preprint_bozza.docx --toc --toc-depth=3`
```

- [ ] **Step 2: Replace Errori + Best Practices placeholder**

Find `<!-- PLACEHOLDER: Errori e Best Practices — Task 9 -->` and replace with:

```markdown

---

## Errori Comuni

| Errore | Correzione |
|---|---|
| Trattare il pilot come studio definitivo sull'efficacia | Il pilot verifica la fattibilità; l'efficacia va confermata nello studio completo |
| Non definire criteri go/no-go prima della raccolta | Senza di essi non è un feasibility study — definire in Fase 2e |
| N ≥ 30 per gruppo come obiettivo del pilot | Per il pilot: N = 12–15 per arm è sufficiente (Julious, 2005) |
| Non specificare il framework teorico | Senza teoria, la scelta degli strumenti è arbitraria |
| Riportare solo p-value | Aggiungere sempre effect size e IC 95% |
| Non pianificare i missing data a priori | Decidere la strategia prima della raccolta |
| Citare Braun & Clarke solo 2006 | Aggiungere Braun & Clarke, 2021 per approccio riflessivo |
| Non dichiarare posizionalità del ricercatore in MM | Richiesta dalla maggior parte delle riviste qualitative e MM |
| Strumenti scelti senza verifica versione italiana | Verificare sempre dalla fonte primaria |
| Log chatbot trattati come dato generico | Le conversazioni AI con minori sono categoria sensibile — vedi Fase 3c |
| Roadmap post-pilot assente | Obbligatoria: include criteri go/no-go, dimensionamento, timeline studio completo |

---

## Best Practices per l'Assistente

**Comportamento generale**
- Sii un mentore metodologico, non un esecutore passivo.
- Non procedere alla fase successiva senza conferma esplicita dell'utente.
- Per design eticamente problematici, suggerisci sempre il wait-list design.
- Tono accademico, chiaro, strutturato.

**Guardrail anti-allucinazione**
- Non inventare mai citazioni. Usa `[CITARE: autore/anno da verificare]` sempre.
- Versioni italiane degli strumenti: non affermare che esiste una versione validata senza conferma.
- Effect size "tipici": se l'utente non fornisce dati reali, usa d = 0.5 e dichiara che è stima conservativa.

**Guardrail anti-bias**
- *Bias deficit model:* non inquadrare BES/disabilità solo come deficit — includi misure di risorse e partecipazione.
- *Bias medicalizzazione:* non ridurre l'inclusione a categorizzazione diagnostica.
- *Bias ottimismo intervento:* nella Discussion/Expected Outcomes, includi almeno un riferimento a studi con risultati nulli.
- *Bias SES:* i campioni convenience nelle scuole italiane tendono a sovra-rappresentare contesti medi — documenta.
- *Bias strumenti anglosassoni:* verifica sempre le norme italiane o europee prima di usarli.
```

- [ ] **Step 3: Verify all sections present**

```powershell
$sections = @("FASE 6", "Roadmap Post-Pilot", "Errori Comuni", "Best Practices", "Guardrail anti-allucinazione", "piano-analisi.json")
foreach ($s in $sections) {
    $match = Select-String -Path "skills/research-design/SKILL.md" -Pattern $s
    if ($match) { Write-Host "OK: $s" } else { Write-Host "MISSING: $s" }
}
```

Expected: all 6 lines print `OK:`.

- [ ] **Step 4: Verify no PLACEHOLDER comments remain**

```powershell
Select-String -Path "skills/research-design/SKILL.md" -Pattern "PLACEHOLDER"
```

Expected: no output (no remaining placeholders).

- [ ] **Step 5: Commit**

```bash
git add skills/research-design/SKILL.md
git commit -m "feat(research-design): add MOD-QN1 Fase 6, Errori Comuni, Best Practices - skill complete"
```

---

### Task 10: Create piano-analisi-schema.json

**Files:**
- Create: `skills/research-design/piano-analisi-schema.json`

- [ ] **Step 1: Write JSON Schema file**

Write `skills/research-design/piano-analisi-schema.json`:

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "$id": "piano-analisi-schema",
  "title": "Piano di Analisi — research-design handoff contract",
  "description": "Schema del file piano-analisi.json prodotto da research-design e consumato da data-analysis",
  "type": "object",
  "required": ["paradigm", "research_questions", "variables", "tests", "missing_data_strategy"],
  "properties": {
    "paradigm": {
      "type": "string",
      "enum": ["MOD-QN1", "MOD-QN2", "MOD-QN3", "MOD-QN4", "MOD-Q1", "MOD-Q2", "MOD-Q3", "MOD-Q4", "MOD-MM", "MOD-AR", "MOD-DBR"]
    },
    "paradigm_label": { "type": "string" },
    "research_questions": {
      "type": "array",
      "minItems": 1,
      "items": {
        "type": "object",
        "required": ["id", "text", "h1", "h0"],
        "properties": {
          "id": { "type": "string", "pattern": "^RQ[0-9]+$" },
          "text": { "type": "string", "minLength": 10 },
          "h1": { "type": "string" },
          "h0": { "type": "string" }
        }
      }
    },
    "variables": {
      "type": "object",
      "required": ["independent", "dependent"],
      "properties": {
        "independent": {
          "type": "array",
          "items": {
            "type": "object",
            "required": ["name", "levels"],
            "properties": {
              "name": { "type": "string" },
              "description": { "type": "string" },
              "levels": { "type": "array", "items": { "type": "string" } }
            }
          }
        },
        "dependent": {
          "type": "array",
          "items": {
            "type": "object",
            "required": ["name", "scale", "instrument"],
            "properties": {
              "name": { "type": "string" },
              "scale": { "type": "string", "enum": ["nominal", "ordinal", "interval", "ratio"] },
              "instrument": { "type": "string" },
              "cronbach_expected": { "type": "number", "minimum": 0, "maximum": 1 }
            }
          }
        },
        "covariates": {
          "type": "array",
          "items": {
            "type": "object",
            "required": ["name", "rationale"],
            "properties": {
              "name": { "type": "string" },
              "rationale": { "type": "string" }
            }
          }
        }
      }
    },
    "tests": {
      "type": "array",
      "minItems": 1,
      "items": {
        "type": "object",
        "required": ["test", "software"],
        "properties": {
          "test": { "type": "string" },
          "software": { "type": "string", "enum": ["JASP", "R", "SPSS", "Python", "other"] },
          "assumptions": { "type": "array", "items": { "type": "string" } },
          "effect_size": { "type": "string" },
          "report_format": { "type": "string" }
        }
      }
    },
    "missing_data_strategy": {
      "type": "string",
      "enum": ["FIML", "multiple_imputation", "listwise", "pairwise"]
    },
    "osf_preregistration_url": { "type": ["string", "null"] },
    "data_format": { "type": "string", "enum": ["XLSX", "CSV", "SPSS_sav", "R_rda"] },
    "go_nogo_criteria": {
      "type": "object",
      "properties": {
        "recruitment_rate": { "type": "number", "minimum": 0, "maximum": 1 },
        "retention_rate": { "type": "number", "minimum": 0, "maximum": 1 },
        "data_completeness": { "type": "number", "minimum": 0, "maximum": 1 },
        "fidelity": { "type": "number", "minimum": 0, "maximum": 1 },
        "instrument_acceptability": { "type": "number", "minimum": 0, "maximum": 1 },
        "min_criteria_met": { "type": "integer", "minimum": 1, "maximum": 5 }
      }
    }
  }
}
```

- [ ] **Step 2: Validate JSON is parseable**

```powershell
$content = Get-Content "skills/research-design/piano-analisi-schema.json" -Raw
try {
    $null = ConvertFrom-Json $content
    Write-Host "JSON valid"
} catch {
    Write-Host "JSON INVALID: $_"
}
```

Expected: `JSON valid`.

- [ ] **Step 3: Commit**

```bash
git add skills/research-design/piano-analisi-schema.json
git commit -m "feat(research-design): add piano-analisi JSON schema for data-analysis handoff"
```

---

### Task 11: Create references/normativa-it.md

**Files:**
- Create: `skills/research-design/references/normativa-it.md`

- [ ] **Step 1: Write normativa-it.md**

Write `skills/research-design/references/normativa-it.md`:

```markdown
# Normativa Italiana — Ricerca in Ambito Educativo

## GDPR e Privacy

**Reg. UE 2016/679 (GDPR)** — applicabile a tutti i livelli scolastici.

Articoli rilevanti:
- Art. 6: basi giuridiche per il trattamento (consenso, interesse legittimo, adempimento contratto)
- Art. 9: categorie particolari (dati sanitari, disabilità, diagnosi DSA — trattamento richiede consenso esplicito)
- Art. 12-14: informativa chiara e comprensibile
- Art. 15-22: diritti dell'interessato (accesso, rettifica, cancellazione, portabilità)
- Art. 35: DPIA (valutazione d'impatto) obbligatoria per trattamento sistematico di dati su larga scala o di categorie particolari

**D.Lgs. 196/2003 + D.Lgs. 101/2018 (Codice Privacy IT)** — adattamento italiano del GDPR.

Per i **minori**: il consenso al trattamento dei dati deve essere fornito dai genitori o tutori legali. In Italia, la soglia per il consenso autonomo ai servizi online è 14 anni (art. 2-quinquies D.Lgs. 196/2003).

---

## Inclusione e BES

**L. 104/1992 (Legge-quadro sulla disabilità)**
- Garantisce integrazione scolastica delle persone con disabilità
- Richiede Piano Educativo Individualizzato (PEI)
- Ricerca che coinvolge studenti con disabilità: coordinare con il Consiglio di Classe, la famiglia e il GLH (Gruppo di Lavoro sull'Handicap)
- Non usare terminologia deficit-centrica nel protocollo — vedi ICF-CY per framework inclusivo

**L. 170/2010 (DSA)**
- Dislessia, disgrafia, disortografia, discalculia
- Richiede Piano Didattico Personalizzato (PDP) approvato dal Consiglio di Classe
- Misure compensative e dispensative: vanno mantenute durante la raccolta dati
- Strumenti di ricerca: verifica che siano accessibili (es. font leggibilità, tempo esteso)

**D.Lgs. 66/2017 (Inclusione scolastica)** — riforma del PEI, introduce il Progetto Individuale.

---

## Autorizzazioni per Livello Scolastico

### Scuola dell'Infanzia, Primaria, Secondaria I e II

**Autorizzazioni necessarie:**
1. **Dirigente Scolastico** — approvazione formale del protocollo di ricerca
2. **Consiglio di Classe / Collegio Docenti** — per studi che modificano la didattica ordinaria
3. **Genitori/tutori legali** — consenso informato scritto (minori di 18 anni)
4. **USR (Ufficio Scolastico Regionale)** — per studi che coinvolgono più istituti o hanno carattere sperimentale formale; non sempre obbligatorio per ricerca accademica standard

**Documenti da preparare:**
- Modulo consenso informato genitori (linguaggio semplice, finalità non tecniche)
- Informativa GDPR per i genitori
- Lettera di presentazione per il Dirigente
- Protocollo sintetico (max 2 pagine) per la scuola

### Università / Alta Formazione

**Autorizzazioni necessarie:**
1. **Comitato Etico di Ateneo** — obbligatorio per ricerche su soggetti umani con raccolta dati; verifica se il tuo ateneo richiede approvazione preventiva o solo notifica
2. **Partecipanti adulti** — consenso informato scritto autonomo (≥ 18 anni)
3. **DPO di Ateneo** — per trattamento dati su larga scala o categorie particolari

### Formazione Professionale / IeFP

- Verifica la natura dell'ente gestore (pubblico, privato, paritario)
- Autorizzazione del Coordinatore del corso o del Direttore dell'ente
- Per minori (< 18): consenso genitori come per scuola secondaria
- Normativa regionale specifica: l'IeFP è di competenza regionale

---

## MIUR — Sperimentazione Didattica

**DPR 275/1999 (Regolamento Autonomia Scolastica)** — le scuole possono adottare percorsi didattici sperimentali nell'autonomia.

**CM 179/1999 e successive** — sperimentazioni che modificano orari, programmi o struttura devono essere approvate a livello di Collegio Docenti e, per le più rilevanti, dall'USR.

Per ricerca accademica standard (non modifica strutturale del curricolo): in genere basta il consenso del Dirigente + Consiglio di Classe.

---

## Template Modulo Consenso Informato

### Per genitori / tutori (minori)

```
MODULO DI CONSENSO INFORMATO PER I GENITORI / TUTORI LEGALI

Titolo dello studio: [titolo]
Responsabile della ricerca: [nome, istituzione, email]

Gentile genitore/tutore,
le chiediamo di autorizzare la partecipazione di suo/a figlio/a a uno studio di ricerca condotto da [istituzione].
Lo studio si svolgerà presso [scuola] nel periodo [date].

Cosa chiederemo a suo/a figlio/a:
[descrizione semplice, senza tecnicismi — max 3-4 punti]

Dati raccolti:
[lista dati: questionari, punteggi test, osservazioni — specificare se audio/video]

Come verranno usati i dati:
I dati saranno analizzati in forma anonima. Non saranno condivisi con terzi. Saranno conservati per [N anni] e poi eliminati.

Diritti del partecipante (ai sensi del GDPR):
Può ritirare il consenso in qualsiasi momento senza conseguenze. Può richiedere l'accesso, la rettifica o la cancellazione dei dati.

Contatti: [email DPO o responsabile dello studio]

□ AUTORIZZO la partecipazione di mio/a figlio/a
□ NON autorizzo la partecipazione

Firma del genitore/tutore: __________________ Data: __________
Nome e cognome (leggibile): __________________
```

### Per partecipanti adulti (≥ 18 anni)

```
MODULO DI CONSENSO INFORMATO

Titolo dello studio: [titolo]
Responsabile: [nome, istituzione, email]

La invito a partecipare a uno studio di ricerca su [argomento — linguaggio non tecnico].

Cosa le chiediamo:
[descrizione attività — max 3-4 punti]

Dati raccolti: [lista]
Trattamento: anonimo, finalità esclusivamente di ricerca, conservazione [N anni].

Diritti (GDPR art. 15-22): può ritirare il consenso in qualsiasi momento senza conseguenze.

□ Acconsento a partecipare

Firma: __________________ Data: __________
```
```

- [ ] **Step 2: Verify file created**

```powershell
Test-Path "skills/research-design/references/normativa-it.md"
Select-String -Path "skills/research-design/references/normativa-it.md" -Pattern "GDPR"
Select-String -Path "skills/research-design/references/normativa-it.md" -Pattern "L. 104"
Select-String -Path "skills/research-design/references/normativa-it.md" -Pattern "Consenso Informato"
```

Expected: `True` and 3 matches.

- [ ] **Step 3: Commit**

```bash
git add skills/research-design/references/normativa-it.md
git commit -m "feat(research-design): add Italian regulatory reference doc with consent templates"
```

---

### Task 12: Deprecate educational-pilot-design

**Files:**
- Modify: `skills/educational-pilot-design/SKILL.md` — update frontmatter description

- [ ] **Step 1: Read current frontmatter**

Open `skills/educational-pilot-design/SKILL.md` and locate lines 1-4 (the frontmatter block):

```yaml
---
name: educational-pilot-design
description: Usa quando occorre progettare uno studio pilota o quasi-sperimentale nell'ambito delle scienze dell'educazione: ...
---
```

- [ ] **Step 2: Replace description in frontmatter**

Replace the `description:` line with:

```yaml
description: "⚠️ DEPRECATO — usa research-design al posto di questo skill. Questo skill supporta solo il paradigma quasi-sperimentale. research-design supporta 11 paradigmi con decision tree. Mantenuto per backward compatibility: i progetti con protocollo_ricerca.md esistente possono continuare qui, ma i nuovi progetti devono usare research-design."
```

The result should be:
```yaml
---
name: educational-pilot-design
description: "⚠️ DEPRECATO — usa research-design al posto di questo skill. Questo skill supporta solo il paradigma quasi-sperimentale. research-design supporta 11 paradigmi con decision tree. Mantenuto per backward compatibility: i progetti con protocollo_ricerca.md esistente possono continuare qui, ma i nuovi progetti devono usare research-design."
---
```

- [ ] **Step 3: Add deprecation banner at top of Overview section**

After `## Overview` (line ~8), insert:

```markdown
> **⚠️ DEPRECATO:** Questo skill è stato sostituito da `research-design`, che supporta 11 paradigmi metodologici con decision tree. Usa `research-design` per nuovi progetti. Questo skill rimane disponibile per progetti con `protocollo_ricerca.md` esistente.
```

- [ ] **Step 4: Verify**

```powershell
Select-String -Path "skills/educational-pilot-design/SKILL.md" -Pattern "DEPRECATO"
```

Expected: at least 2 matches (frontmatter + banner).

- [ ] **Step 5: Commit**

```bash
git add skills/educational-pilot-design/SKILL.md
git commit -m "feat(educational-pilot-design): add deprecation notice, redirect to research-design"
```

---

### Task 13: Update pipeline-ricerca

**Files:**
- Modify: `skills/pipeline-ricerca/SKILL.md` — update Stage 3 and flow diagram

- [ ] **Step 1: Update flow diagram (lines 10-24)**

Find:
```
[educational-pilot-design]    → protocollo_ricerca.md + preprint_bozza.md
```

Replace with:
```
[research-design]             → design/protocollo_ricerca.md + design/fase-5-analisi/piano-analisi.json + design/preprint_bozza.md
```

- [ ] **Step 2: Update Stage 3 header and description (lines 81-98)**

Find:
```markdown
## Stage 3 — `educational-pilot-design`

**Quando:** dopo `prisma-review` (e opzionalmente `hybrid-rag`), per progettare lo studio pilota. Copre tutti i livelli scolastici (infanzia, primaria, secondaria I e II, università, formazione professionale) e tutti i profili disciplinari delle scienze dell'educazione (Ed-Tech, psicopedagogia, pedagogia speciale, didattica, valutazione, formazione docenti).
```

Replace with:
```markdown
## Stage 3 — `research-design`

**Quando:** dopo `prisma-review` (e opzionalmente `hybrid-rag`), per progettare lo studio. Supporta 11 paradigmi metodologici: la Fase 0 del skill guida la selezione tramite decision tree. Copre tutti i livelli scolastici (infanzia, primaria, secondaria I e II, università, formazione professionale) e tutti i profili disciplinari.
```

- [ ] **Step 3: Update file table in Stage 3**

Find:
```markdown
| File | Contenuto | Consumato da |
|---|---|---|
| `protocollo_ricerca.md` | Protocollo completo (Blocco STATO + sezioni) | `pandoc-export` (opzionale) |
| `strumenti_valutazione.md` | Questionari, tracce intervista, LA | — |
| `timeline_pilota.md` | Cronoprogramma settimanale | — |
| `preprint_bozza.md` | Paper IMRAD (Protocol o Results) | `pandoc-export` |
```

Replace with:
```markdown
| File | Contenuto | Consumato da |
|---|---|---|
| `design/protocollo_ricerca.md` | Protocollo completo + Blocco STATO | `pandoc-export` (opzionale) |
| `design/strumenti_valutazione.md` | Questionari, tracce intervista, LA | — |
| `design/timeline_pilota.md` | Cronoprogramma settimanale | — |
| `design/fase-5-analisi/piano-analisi.json` | Piano analisi strutturato (schema tipizzato) | `data-analysis` skill |
| `design/preprint_bozza.md` | Paper IMRAD (Protocol o Results) | `pandoc-export` |
```

- [ ] **Step 4: Update Entry point alternativi table**

Find:
```
| `protocollo_ricerca.md` esiste | `educational-pilot-design` — legge Blocco STATO e riprende |
```

Replace with:
```
| `design/.research-state.json` esiste | `research-design` — legge state e riprende |
| `protocollo_ricerca.md` esiste (vecchia struttura) | `educational-pilot-design` — legge Blocco STATO e riprende (deprecated) |
```

- [ ] **Step 5: Update Handoff section title**

Find:
```markdown
## Handoff critico: prisma-review → educational-pilot-design
```

Replace with:
```markdown
## Handoff critico: prisma-review → research-design
```

- [ ] **Step 6: Verify**

```powershell
Select-String -Path "skills/pipeline-ricerca/SKILL.md" -Pattern "research-design"
Select-String -Path "skills/pipeline-ricerca/SKILL.md" -Pattern "piano-analisi.json"
```

Expected: multiple matches for each.

- [ ] **Step 7: Commit**

```bash
git add skills/pipeline-ricerca/SKILL.md
git commit -m "feat(pipeline-ricerca): update Stage 3 from educational-pilot-design to research-design"
```

---

### Task 14: Push to remote and verify

- [ ] **Step 1: Check all commits in this plan**

```bash
git log --oneline -15
```

Expected: see commits for Tasks 1-13.

- [ ] **Step 2: Verify file count in research-design/**

```powershell
Get-ChildItem -Recurse "skills/research-design/" | Measure-Object
```

Expected: at least 3 files (SKILL.md, piano-analisi-schema.json, references/normativa-it.md).

- [ ] **Step 3: Final SKILL.md integrity check**

```powershell
$required = @(
    "name: research-design",
    "## Avvio",
    "## FASE 0",
    "Routing Table",
    "## MOD-QN1",
    "FASE 1: Framework",
    "FASE 2: Design",
    "FASE 3: Strumenti",
    "FASE 4: Procedura",
    "FASE 5: Piano",
    "FASE 6: Preprint",
    "piano-analisi.json",
    "## Errori Comuni",
    "## Best Practices"
)
foreach ($s in $required) {
    $match = Select-String -Path "skills/research-design/SKILL.md" -Pattern $s
    if ($match) { Write-Host "OK: $s" } else { Write-Host "MISSING: $s" }
}
```

Expected: all 14 lines print `OK:`.

- [ ] **Step 4: Push to remote**

```bash
git push origin master
```

---

## Self-Review: Spec Coverage

| Spec Section | Covered by Task | Status |
|---|---|---|
| Unified workspace architecture | Task 1 (file structure), Task 2 (session recovery) | ✅ |
| `.project-state.json` format | Task 3 (Fase 0 action) | ✅ |
| `design/.research-state.json` format | Task 3 (Fase 0 action) | ✅ |
| `project-log.md` append pattern | Tasks 3-9 (every Fase Azione) | ✅ |
| Backward compatibility (old prisma_state.json) | Task 2 (Avvio) | ✅ |
| Fase 0 decision tree (5 questions) | Task 3 | ✅ |
| Routing table (11 paradigms) | Task 3 | ✅ |
| MOD-QN1 Fase 1-6 | Tasks 4-9 | ✅ |
| piano-analisi.json generation | Task 8 (Fase 5e) | ✅ |
| piano-analisi-schema.json | Task 10 | ✅ |
| references/normativa-it.md | Task 11 | ✅ |
| educational-pilot-design deprecation | Task 12 | ✅ |
| pipeline-ricerca Stage 3 update | Task 13 | ✅ |
| MOD-QN2-4 (Priorità Media) | ❌ — Piano 2 separato | 🔜 |
| MOD-Q1-Q4 (Priorità Media/Bassa) | ❌ — Piano 2 separato | 🔜 |
| MOD-MM, MOD-AR, MOD-DBR | ❌ — Piano 3 separato | 🔜 |
