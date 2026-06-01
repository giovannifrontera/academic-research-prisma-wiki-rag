# Design Spec — `research-design` skill

**Data:** 2026-06-01
**Sostituisce:** `skills/educational-pilot-design/SKILL.md`
**Stato:** Approvato — pronto per implementazione

---

## 1. Problema e motivazione

`educational-pilot-design` presuppone la risposta prima ancora che il ricercatore abbia formulato la domanda: guida direttamente verso un design quasi-sperimentale, ignorando tutti gli altri paradigmi delle scienze dell'educazione.

L'obiettivo è trasformarla in un **framework decisionale completo** che:
1. Guida il ricercatore nella scelta del paradigma più adatto alla sua domanda
2. Copre tutti i paradigmi rilevanti (qualitativo, quantitativo, misto, ricerca-azione, DBR)
3. Garantisce tracciabilità rigorosa su progetti che si estendono su settimane o mesi
4. Massimizza il contenuto esistente (buono) aggiungendo solo ciò che manca

---

## 2. Architettura generale

**Nome skill:** `research-design`
**File:** `skills/research-design/SKILL.md`
**Trigger description:**
> Usa quando occorre progettare uno studio di ricerca nelle scienze dell'educazione o in ambiti correlati. Guida la scelta del paradigma (qualitativo, quantitativo, misto, ricerca-azione, DBR) e la progettazione completa fino al preprint. Copre tutti i livelli scolastici italiani e contesti internazionali. NON usare per revisioni sistematiche (usa prisma-review).

### Struttura interna del file

```
SKILL.md
├── [AVVIO]              Ripresa sessione, lettura PRISMA, verifica RAG
├── [FASE 0]             Decision tree — selezione paradigma
├── [SEZIONI COMUNI]     Condivise da tutti i paradigmi
│   ├── Etica e normativa (MIUR, GDPR, BES/DSA)
│   ├── Preprint e disseminazione (IMRAD, riviste, template)
│   └── Handoff a data-analysis e pandoc-export
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

`educational-pilot-design` viene **rinominata** in `research-design`. Chi ha già `protocollo_ricerca.md` con Blocco STATO riprende automaticamente: il campo `paradigma` default a `quasi-sperimentale` se assente, caricando MOD-QN1 (contenuto attuale).

---

## 3. Sistema di tracciabilità e persistenza

### Principio guida
Ogni decisione ha una data, un motivo e non va mai persa. Il ricercatore può interrompere e riprendere dopo settimane senza perdere lavoro.

### Struttura cartella progetto

```
mio-progetto-ricerca/
├── .research-state.json          ← stato macchina (aggiornato ad ogni fase)
├── protocollo_ricerca.md         ← documento principale + Blocco STATO
├── research-log.md               ← diario decisioni (append-only, mai modificato)
├── fase-0-design/
│   └── paradigma-selection.md
├── fase-1-framework/
│   └── framework-ipotesi.md
├── fase-2-design/
│   ├── design-ricerca.md
│   └── power-analysis.md             (solo paradigmi quantitativi)
├── fase-3-strumenti/
│   └── strumenti-valutazione.md
├── fase-4-procedura/
│   ├── timeline.md
│   └── consenso-informato.md
├── fase-5-analisi/
│   ├── piano-analisi.md
│   └── piano-analisi.json            (handoff verso data-analysis)
├── fase-6-preprint/
│   ├── preprint-bozza.md
│   └── preprint-[osf|zenodo|preprints-org].md
├── dati/
│   ├── grezzi/                       (mai modificare)
│   ├── elaborati/
│   └── strumenti/
└── sessioni/
    ├── 2026-06-01-sessione.md
    └── 2026-06-08-sessione.md
```

### `.research-state.json`

```json
{
  "progetto": "mio-progetto-ricerca",
  "ricercatore": "Nome Cognome",
  "data_avvio": "2026-06-01",
  "ultima_modifica": "2026-06-08",
  "paradigma": "quasi-sperimentale",
  "modulo": "MOD-QN1",
  "livello": "sec-II",
  "profilo": "Ed-Tech",
  "fase_corrente": 3,
  "fasi_completate": [0, 1, 2],
  "prisma_file": "prisma_synthesis.md",
  "rag_disponibile": true,
  "dati_raccolti": false,
  "preregistrazione_osf": null,
  "fasi": {
    "0": { "completata": true, "data": "2026-06-01", "paradigma_scelto": "quasi-sperimentale" },
    "1": { "completata": true, "data": "2026-06-01", "framework": "SRL/Zimmerman", "rq_count": 2 },
    "2": { "completata": true, "data": "2026-06-01", "design": "pre-post control group", "n_previsto": 40 },
    "3": { "completata": false, "data": null, "strumenti_scelti": [] }
  }
}
```

### `research-log.md` (append-only)

Ogni voce segue questo formato:
```markdown
---
## [AAAA-MM-GG] Fase N — [titolo fase]
**Decisione:** [cosa è stato deciso]
**Rationale:** [perché — dati, vincoli, preferenze]
**Alternative scartate:** [cosa non si è scelto e perché]
**Prossimo passo:** [cosa fare nella prossima sessione]
```

### Protocollo di aggiornamento (regola ferrea)

| Momento | Azione obbligatoria |
|---------|--------------------|
| Inizio fase | Leggi `.research-state.json`, dichiara fase corrente |
| Durante la fase | Aggiorna file fase in tempo reale |
| Fine fase | 1) Aggiorna `.research-state.json` 2) Appendi `research-log.md` 3) Chiedi conferma |
| Interruzione | Scrivi in `research-log.md`: stato + prossimo passo + data |
| Ripresa | Leggi `.research-state.json` → `fase_corrente` → mostra riepilogo all'utente |

### Ripresa di sessione (prima azione assoluta)

```
Ho trovato .research-state.json.
───────────────────────────────────────────
 Progetto:       mio-progetto-ricerca
 Paradigma:      quasi-sperimentale (MOD-QN1)
 Fase corrente:  3 — Strumenti e misure
 Completate:     0 ✓  1 ✓  2 ✓
 Ultima sessione: 2026-06-08
 Prossimo passo: [da research-log.md]
───────────────────────────────────────────
Vuoi riprendere dalla Fase 3?
```

---

## 4. Fase 0 — Decision tree

### Struttura Fase 0

**0.0 — Setup progetto**
- Chiede nome progetto e ricercatore
- Crea struttura cartelle
- Inizializza `.research-state.json`, `research-log.md`, `protocollo_ricerca.md`

**0.1 — Lettura contesto (automatica)**
- Cerca `prisma_synthesis.md` → estrae: stato conoscenza, gap, effect size, RQ aperte
- Cerca `.research-state.json` → ripresa se esiste
- Cerca `rag_db/` → annota disponibilità
- Dichiara il contesto trovato prima di procedere

**0.2 — Cinque domande di routing (una alla volta)**

D1 — Obiettivo principale:
> a) Comprendere (esplorare, significati, esperienze)
> b) Misurare (testare intervento, quantificare outcome)
> c) Migliorare (cambiare pratica attraverso la ricerca)
> d) Progettare (creare e raffinare strumento/ambiente)

D2 — Stato della conoscenza (saltata se PRISMA disponibile):
> a) Poco/nulla — fenomeno emergente
> b) Abbastanza — gap importanti
> c) Molto — voglio confermare in nuovo contesto

D3 — Natura dell'outcome:
> a) Numeri e misure
> b) Significati e interpretazioni
> c) Entrambi (triangolazione)

D4 — Vincoli pratici (solo se D1=b o D1=d):
> a) N ≥ 20/gruppo + randomizzazione possibile → RCT
> b) N ≥ 10/gruppo + classi naturali → Quasi-sperimentale
> c) N < 10 o singolo caso → Single-subject
> d) N grande, nessun intervento → Survey/correlazionale

D5 — Sequenza (solo se D3=c):
> a) Prima misuro, poi capisco → Explanatory Sequential
> b) Prima comprendo, poi confermo → Exploratory Sequential
> c) In parallelo → Convergent Parallel

**Tabella di routing completa:**

| D1 | D2 | D3 | D4 | D5 | Paradigma |
|----|----|----|----|----|----------|
| b | * | a | a | — | RCT (MOD-QN2) |
| b | * | a | b | — | Quasi-sperimentale (MOD-QN1) |
| b | * | a | c | — | Single-subject (MOD-QN3) |
| b | * | a | d | — | Survey (MOD-QN4) |
| a | a | b | — | — | Fenomenologia (MOD-Q1) |
| a | b | b | — | — | Grounded Theory (MOD-Q2) |
| a | * | b | — | — | Etnografia (MOD-Q3) † |
| a | * | b | — | — | Ricerca Narrativa (MOD-Q4) † |
| * | * | c | — | a | Mixed-Methods Explanatory (MOD-MM) |
| * | * | c | — | b | Mixed-Methods Exploratory (MOD-MM) |
| * | * | c | — | c | Mixed-Methods Convergent (MOD-MM) |
| c | * | * | — | — | Ricerca-Azione PAR (MOD-AR) |
| d | * | * | — | — | Design-Based Research (MOD-DBR) |

† Tra Etnografia e Ricerca Narrativa: domanda aggiuntiva sul focus
(pratiche collettive/contesto vs. storie individuali).

**0.3 — Output raccomandazione**
```
RACCOMANDAZIONE DESIGN
──────────────────────────────────────────────────
Paradigma consigliato:   [nome]
Modulo:                  [MOD-XX]
Motivazione:             [2-3 frasi basate sulle risposte D1-D5
                          + contesto PRISMA se disponibile]
Alternative possibili:   [1-2 alternative con trade-off sintetico]
Riferimento:             [Creswell & Creswell 2018; Trinchero 2004;
                          riferimento specifico per paradigma]
──────────────────────────────────────────────────
Confermi questo design o vuoi esplorare un'alternativa?
```

---

## 5. Moduli paradigma

### Schema uniforme fasi 1-6 per tutti i moduli

Ogni modulo segue la stessa struttura di fasi. Il contenuto varia, la struttura no.

```
FASE 1 — Framework e ipotesi/domande
FASE 2 — Design specifico del paradigma
FASE 3 — Strumenti e raccolta dati
FASE 4 — Procedura, timeline, etica [COMUNE]
FASE 5 — Piano di analisi
FASE 6 — Preprint e disseminazione [COMUNE]
```

### Contenuto distintivo per modulo

**MOD-QN1 — Quasi-sperimentale / Pilot** (contenuto attuale — ~90% riusato)
- Fase 1: H1/H0, RQ confermative, effect size da PRISMA
- Fase 2: Pre-post, gruppi naturali, go/no-go, stopping rules, power analysis G*Power
- Fase 3: Strumenti validati, α Cronbach, learning analytics
- Fase 5: ANCOVA, Cohen's d, IC 95%, missing data strategy
- Ref: Creswell (2018); Trinchero (2004); Julious (2005)

**MOD-QN2 — RCT**
- Fase 2: Randomizzazione (sequence generation, allocation concealment), blinding, CONSORT checklist
- Fase 5: ITT vs per-protocol, analisi per subgroup pre-specificata
- Ref: CONSORT 2010; Schulz et al. (2010)

**MOD-QN3 — Single-subject**
- Fase 2: Design A-B, A-B-A, A-B-A-B, Multiple Baseline; criteri stabilità baseline
- Fase 5: Analisi visiva grafico, Tau-U, PND (Percentage Non-Overlapping Data)
- Ref: Horner & Baer (1978); Parker et al. (2011); Kratochwill et al. (2013)

**MOD-QN4 — Survey / Correlazionale**
- Fase 2: Campionamento (probabilistico/non), calcolo margine d'errore, tasso risposta
- Fase 3: Design questionario, scale Likert, piloting dello strumento
- Fase 5: Correlazione, regressione multipla, analisi fattoriale esplorativa
- Ref: Fowler (2014); Field (2018)

**MOD-Q1 — Fenomenologia**
- Fase 1: Domande esplorative, posizionamento epistemologico, bracketing (epoché)
- Fase 2: IPA (Smith et al.) o fenomenologia descrittiva (Giorgi); N=6-12 purposive
- Fase 3: Traccia intervista semi-strutturata, durata 60-90 min, trascrizione verbatim
- Fase 5: IPA 6 steps; clustering temi esperienziali; gestione idiographic-nomothetic
- Ref: Smith, Flowers & Larkin (2009); Giorgi (2009)

**MOD-Q2 — Grounded Theory**
- Fase 1: Research question aperta ("Come/Cosa accade quando...")
- Fase 2: Glaser & Strauss classica vs. Charmaz costruttivista; theoretical sampling; saturazione
- Fase 3: Interviste, osservazione, documenti; memo writing sin dall'inizio
- Fase 5: Coding open → axial → selective; comparazione costante; core category; diagramma categorie
- Ref: Glaser & Strauss (1967); Charmaz (2014)

**MOD-Q3 — Etnografia**
- Fase 2: Negoziazione accesso al campo; ruolo osservatore (partecipante completo → osservatore puro); durata minima 3-6 mesi
- Fase 3: Note di campo strutturate (descrittive + riflessive), interviste key informant, analisi documenti istituzionali
- Fase 4: Ethics ongoing (rinegoziazione continua del consenso)
- Fase 5: Thick description (Geertz); analisi tematica del campo; triangolazione fonti
- Ref: Geertz (1973); Hammersley & Atkinson (2007); Spradley (1980)

**MOD-Q4 — Ricerca Narrativa**
- Fase 2: Selezione narratori (purposive); tipo racconto (life history, episodico, story completion)
- Fase 3: Intervista narrativa non direttiva; documenti biografici; diari
- Fase 5: Analisi narrativa (struttura — Labov; contenuto — tematica; performance — dialogica); Riessman approach
- Ref: Riessman (2008); Clandinin & Connelly (2000); Labov & Waletzky (1967)

**MOD-MM — Mixed-Methods**
- Fase 2: Scelta design (Explanatory/Exploratory/Convergent); punto di integrazione; priority quantitativa vs. qualitativa
- Fase 5: Joint display; gestione divergenze (divergenze = risultati, non errori); meta-inferenze
- Ref: Creswell & Plano Clark (2018); Teddlie & Tashakkori (2009)

**MOD-AR — Ricerca-Azione (PAR)**
- Fase 1: Problema pratico + comunità coinvolta + obiettivo trasformativo; ruolo co-ricercatori
- Fase 2: Cicli PAR (pianifica → agisci → osserva → rifletti); N cicli da definire
- Fase 3: Strumenti partecipativi (focus group, world cafè, photovoice); osservazione e documenti
- Fase 4: Consenso della comunità (non solo individuale); etica della reciprocità
- Fase 5: Analisi per ciclo; spiral reflection; validazione collaborativa con i co-ricercatori
- Fase 6: Report riflessivo; artefatti come output primario; disseminazione alla comunità
- Ref: Lewin (1946); Kemmis & McTaggart (1988); Reason & Bradbury (2008)

**MOD-DBR — Design-Based Research**
- Fase 1: Problema di design + utenti target + contesto implementativo; teoria dell'intervento iniziale
- Fase 2: Iterazioni micro (sessione singola) e macro (ciclo completo); criteri revisione tra iterazioni
- Fase 3: Usability data, log di sistema, interviste post-sessione, osservazione implementazione
- Fase 5: Analisi comparativa tra iterazioni; principi di design emergenti; raffinamento teoria intervento
- Fase 6: Design principles come output primario; changelog strumento documentato
- Ref: van den Akker et al. (2006); Reeves (2006); McKenney & Reeves (2012)

### Struttura dati per paradigma (`dati/` directory)

| Paradigma | `dati/grezzi/` | `dati/elaborati/` |
|-----------|---------------|------------------|
| QN1/QN2 | `pre-test.csv`, `post-test.csv`, `covariate.csv`, `dropout-log.md` | `ancova-output.csv`, `effect-size.json`, `figures/` |
| QN3 | `misure-ripetute.csv`, `sessione-log.md` | `grafico-AB.png`, `tau-u.json` |
| QN4 | `risposte.csv`, `metadata-campione.csv` | `correlazioni.csv`, `regressione.json` |
| Q1/Q2/Q4 | `trascrizioni/`, `note-campo.md`, `memo.md` | `codebook.md`, `temi/`, `diagramma-categorie.md` |
| Q3 | `note-osservazione/`, `documenti-istituzionali/` | `cronologia-eventi.md`, `mappa-relazioni.md` |
| AR | `cicli/ciclo-N/` (planning+acting+observing+reflecting) | `sintesi-cicli.md`, `azioni-implementate.md` |
| DBR | `iterazioni/iter-N/` (design+implement+analyze+redesign) | `principi-design.md`, `changelog-strumento.md` |

Struttura interna di ogni ciclo AR e iterazione DBR:
```
ciclo-1/
├── 01-pianificazione.md
├── 02-attuazione-log.md
├── 03-osservazioni.md
└── 04-riflessione.md
```

---

## 6. Elementi trasversali (tutti i moduli)

| Elemento | Implementazione |
|----------|-----------------|
| Aggiornamento `.research-state.json` | Fine di ogni fase, automatico |
| Append `research-log.md` | Ogni decisione con data e rationale |
| Checkpoint utente | Prima di avanzare alla fase successiva |
| Guardrail anti-allucinazione | `[CITARE: da verificare]` per ogni riferimento |
| Handoff a `data-analysis` | Fase 5 produce `piano-analisi.json` |
| Handoff a `pandoc-export` | Fase 6 produce `preprint-bozza.md` |
| Pre-registrazione OSF | Fase 2 per quantitativi (prima della raccolta dati) |
| Normativa italiana | MIUR, GDPR, L.104/92, L.170/2010 per tutti i livelli |

---

## 7. Handoff con altre skill

**IN — da `prisma-review`:**
- `prisma_synthesis.md` sezione OUTPUT PER PILOT STUDY → pre-compila framework, effect size, strumenti, RQ

**OUT — verso `data-analysis`** (skill da creare):
- `piano-analisi.json` con: paradigma, variabili, test previsti, formato dati, path cartella dati

**OUT — verso `pandoc-export`:**
- `preprint-bozza.md` con template adattato al paradigma e alla piattaforma target

**IN/OUT — `hybrid-rag`:**
- Disponibile in qualsiasi fase per query su evidenze dalla letteratura

---

## 8. Aggiornamento `pipeline-ricerca`

La skill `pipeline-ricerca` va aggiornata per:
1. Sostituire `educational-pilot-design` con `research-design`
2. Aggiungere i nuovi entry point per ogni paradigma
3. Documentare il file `piano-analisi.json` come handoff verso `data-analysis`

---

## 9. File da creare/modificare (implementazione)

| Azione | File | Note |
|--------|------|------|
| CREA | `skills/research-design/SKILL.md` | File principale (~70KB stimati) |
| CREA | `skills/research-design/references/` | Cartella riferimenti (riusa da educational-pilot-design) |
| CREA | `skills/research-design/imrad-protocol-paper.md` | Riusa da educational-pilot-design |
| CREA | `skills/research-design/imrad-results-paper.md` | Riusa da educational-pilot-design |
| MODIFICA | `skills/pipeline-ricerca/SKILL.md` | Aggiorna riferimenti e handoff |
| DEPRECA | `skills/educational-pilot-design/` | Lascia con nota di deprecazione che punta a research-design |

---

*Spec approvata dal ricercatore — 2026-06-01*
*Prossimo step: writing-plans per piano di implementazione dettagliato*
