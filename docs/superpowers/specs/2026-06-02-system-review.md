# System Review — Rigore Scientifico, Logica e Stabilità

**Data:** 2026-06-02  
**Scope:** Intera pipeline (architettura, skill esistenti, spec nuove skill)  
**Metodo:** Lettura codice + analisi metodologica + analisi architetturale

---

## SINTESI ESECUTIVA

| Categoria | Critici | Medi | Minori |
|-----------|---------|------|--------|
| Stabilità codice | 4 | 5 | 3 |
| Coerenza logica | 3 | 5 | 2 |
| Rigore scientifico | 1 | 6 | 4 |
| **Totale** | **8** | **16** | **9** |

---

## 1. PROBLEMI CRITICI (bloccanti)

### C1 — Script Python dichiarati ma non esistenti
**File:** `skills/prisma-review/SKILL.md` righe 226-233, 439  
**Problema:** La skill fa riferimento a due script esterni che non esistono nel repository:
- `extract_pdf_metadata.py` (Fase 0.7 — ingestion PDF manuali)
- `prisma_screening.py` (Fase 2 — deduplicazione cross-database)

Senza questi script, Fase 2 e lo Stream 2 PRISMA 2020 non sono eseguibili. Il ricercatore si blocca.

**Soluzione:** Creare entrambi gli script. `prisma_screening.py` è il più urgente — deve leggere i `raw_*.json` da tutti i database, deduplicare per DOI/titolo, e produrre `screening_prisma.json`.

---

### C2 — Output server ERIC è Markdown, non JSON
**File:** `mcp-servers/eric/server.py` righe 62-97  
**Problema:** Il tool `eric_advanced_search()` restituisce testo Markdown formattato per la conversazione:
```
1. **Titolo Paper**
   Authors: Smith, J. (2022)
   Abstract: [300 chars]...
```
La skill PRISMA (Fase 1.3) chiede di salvare i "record grezzi" in `raw_eric.json` — ma il tool non espone i raw dict. Il file JSON conterrà Markdown, rendendo `prisma_screening.py` incapace di estrarre i campi strutturati (titolo, DOI, anno, autori).

Stesso problema, in misura variabile, per tutti i server MCP esistenti (CORE, DOAJ, OpenAIRE, Zenodo) — va verificato caso per caso.

**Soluzione:** Refactoring di tutti i server MCP per restituire JSON strutturato con schema consistente:
```json
{
  "results": [
    {
      "title": "...",
      "doi": "...",
      "year": 2022,
      "authors": ["Smith J.", "Brown A."],
      "abstract": "...",
      "source_db": "eric",
      "url": "...",
      "id": "EJ1234567"
    }
  ],
  "total": 150,
  "query": "..."
}
```
L'abstract NON deve essere troncato nel JSON raw — il troncamento può avvenire nella presentazione all'utente, non nel dato grezzo.

---

### C3 — Fallback RAG su screening_prisma.json viola il guardrail anti-allucinazione
**File:** `skills/hybrid-rag/SKILL.md` riga 115; `skills/prisma-review/SKILL.md` riga 651  
**Problema:** Se `eligibility_prisma.json` non esiste, la skill permette di usare `screening_prisma.json` come fallback per `hybrid_rag.py index-prisma`. Ma `screening_prisma.json` contiene paper che hanno superato solo lo screening titolo/abstract — non la valutazione completa di eleggibilità. Il RAG potrebbe recuperare paper esclusi dallo studio, che verrebbero poi citati nel report violando il principio "cita solo paper inclusi".

**Soluzione:** Rimuovere il fallback. Se `eligibility_prisma.json` non esiste, bloccare con messaggio chiaro: *"RAG non può essere costruito: Fase 4 non completata. Completa la valutazione di eleggibilità prima di indicizzare."*

---

### C4 — Percorsi file: conflict tra prisma-review (flat) e architettura (sottocartella)
**Problema:** La skill `prisma-review` scrive tutti i file nella cartella di lavoro corrente (flat):
```
<cwd>/prisma_state.json
<cwd>/eligibility_prisma.json
<cwd>/prisma_synthesis.md
```
La nuova architettura prevede una struttura:
```
{project-root}/prisma/prisma_state.json
{project-root}/prisma/eligibility_prisma.json
```
Questa è un'incompatibilità strutturale. O la skill viene aggiornata per scrivere in `prisma/`, o la nuova architettura adotta il flat layout per PRISMA.

**Soluzione consigliata:** Adottare il layout flat per PRISMA (mantenere la skill così com'è) e aggiornare la spec architetturale di conseguenza. Riduce il rischio di rompere una skill già funzionante.

Schema rivisto per `{project-root}/`:
```
{project-root}/
├── .project-state.json
├── project-log.md
├── prisma_state.json          ← flat (prisma-review invariata)
├── prisma_log.md
├── raw_*.json                 ← flat
├── eligibility_prisma.json    ← flat
├── prisma_synthesis.md        ← flat
├── prisma_bibliography.md     ← flat
├── hybrid_rag.py              ← copiato da template
├── rag_db/
├── design/                    ← research-design
├── raccolta-dati/             ← data-collection
├── analisi/                   ← data-analysis
└── preprint/                  ← preprint skill
```

---

## 2. PROBLEMI DI RIGORE SCIENTIFICO

### S1 — "d=0.5 conservativo" è terminologicamente impreciso
**File:** `skills/educational-pilot-design/SKILL.md` riga 137; `skills/research-design/SKILL.md`  
**Problema:** d=0.5 è un effect size *medio* secondo la convenzione Cohen (1988), non *conservativo*. Un approccio conservativo userebbe d=0.2 (piccolo) o d=0.3. Usare "conservativo" per d=0.5 è un errore metodologico che porta a sottostimare il campione necessario.

**Soluzione:** Sostituire con: *"d = 0.5 (effect size medio, Cohen 1988) — usato come stima in assenza di dati. Se la letteratura suggerisce effetti più piccoli, usare il valore osservato."*

---

### S2 — Hedges' g non menzionato per campioni diseguali
**File:** Spec research-design, sezione Fase 5  
**Problema:** In studi quasi-sperimentali con classi di dimensione diversa (frequente nelle scuole italiane), Cohen's d sovrastima l'effect size. Hedges' g corregge il bias per campioni piccoli e diseguali ed è preferibile.

**Soluzione:** Aggiungere: *"Per campioni diseguali (n₁ ≠ n₂) o piccoli (< 20 per gruppo), preferire Hedges' g a Cohen's d. JASP calcola entrambi."*

---

### S3 — Decision tree non copre tutti i casi (gaps e overlaps)
**File:** `docs/superpowers/specs/2026-06-01-research-design-skill-design.md`  
**Problema:** La routing table presenta:
- **Gap:** Q1=comprendere + Q5=cross-sectional non ha routing esplicito (potrebbe essere fenomenologia, grounded theory, etnografia o narrativo — ambiguo)
- **Overlap:** Q1=migliorare + Q3=entrambi → mappa a MOD-MM, ma MOD-AR è più appropriato
- **Mancanza di ordine di priorità:** se più righe corrispondono, quale paradigma viene scelto?

**Soluzione:** Aggiungere una sesta domanda per i casi qualitativi (Q6: "Qual è il focus epistemologico: esperienza vissuta / teoria emergente / contesto culturale / narrazione?") e specificare che le righe vanno valutate in ordine top-down con "prima corrispondenza vince".

---

### S4 — Pre-registrazione OSF: timing non abbastanza esplicito
**File:** `skills/research-design/SKILL.md` sezione Fase 5c  
**Problema:** La spec dice "pre-registra PRIMA della raccolta dati" ma non specifica che ciò deve avvenire PRIMA della Fase 4 (procedura e intervento). Un ricercatore potrebbe interpretare "prima della raccolta" come "prima di analizzare", non "prima di iniziare la raccolta".

**Soluzione:** Aggiungere warning esplicito: *"⚠️ La pre-registrazione OSF deve avvenire PRIMA di somministrare qualsiasi strumento. Una volta raccolto anche un solo dato, la pre-registrazione perde validità per gli standard Open Science. Confermi di non aver ancora avviato la raccolta?"*

---

### S5 — α Cronbach < .50 come soglia assoluta è contestabile
**File:** `skills/research-design/SKILL.md` Fase 5, sezione stopping rules  
**Problema:** La soglia α < .50 come "strumento inutilizzabile" è corretta per scale con ≥ 10 item. Per scale brevi (3-5 item), comuni in Ed-Tech (es. scale di accettabilità, usabilità), α è atteso più basso per costruzione matematica (Cronbach 1951). La soglia assoluta può portare a scartare strumenti validi.

**Soluzione:** *"α < .50: strumento inutilizzabile (per scale ≥ 6 item). Per scale brevi (< 6 item): valutare ω di McDonald o affidabilità split-half. Segnalare come limitazione se α < .70."*

---

### S6 — FIML come strategia missing data per ANCOVA non è direttamente applicabile
**File:** `skills/research-design/SKILL.md` Fase 5a; `piano-analisi-schema.json`  
**Problema:** FIML (Full Information Maximum Likelihood) è implementato nei modelli SEM e nei software come Mplus o lavaan, non direttamente in ANCOVA. Per ANCOVA con missing data, la strategia corretta è Multiple Imputation (MI) con mice/JASP, poi pooling degli estimati secondo Rubin's Rules.

**Soluzione:**
```
Strategia missing data per ANCOVA:
- MCAR verificato (Little's test): listwise deletion accettabile
- MAR (più comune): Multiple Imputation (mice in R, o JASP 0.19+)
  poi pooling con Rubin's Rules
- MNAR: sensitiviy analysis (selection model o pattern mixture)
FIML: usare per SEM o path analysis, non per ANCOVA classica
```

---

### S7 — CONSORT e STROBE non menzionati per il preprint
**File:** `docs/superpowers/specs/2026-06-01-pipeline-architecture.md` sezione preprint  
**Problema:** I preprint quantitativi devono seguire reporting standards:
- **CONSORT** per RCT (MOD-QN2)
- **STROBE** per studi osservazionali/survey (MOD-QN4)
- **COREQ** per studi qualitativi (interviste/focus group)
- **SRQR** per qualitative research in generale
- **SQUIRE** per quality improvement (MOD-AR)

La skill preprint non fa riferimento a nessun reporting checklist standardizzato.

**Soluzione:** Aggiungere alla skill preprint una sezione "Reporting Standards" che mappa paradigma → checklist da allegare.

---

## 3. PROBLEMI DI COERENZA LOGICA

### L1 — eligibility_prisma.json vs extraction_table.json: ambiguità non risolta
**File:** `skills/prisma-review/SKILL.md` righe 456, 619  
**Problema:** La skill usa entrambi i nomi in modo apparentemente intercambiabile. `eligibility_prisma.json` è il file canonico in Fase 4; `extraction_table.json` compare in alcuni punti come alternativa. Il server `hybrid-rag` menziona entrambi. Quale file esiste effettivamente?

**Soluzione:** Canonicalizzare a `eligibility_prisma.json` ovunque. Rimuovere `extraction_table.json` da tutta la documentazione o esplicitare che sono due file distinti con contenuto diverso (eleggibilità vs estrazione dati estesa).

---

### L2 — wiki.py richiede CWD diversa dalla cartella progetto
**File:** `skills/wiki-core.md` riga 11  
**Problema:** La nota dice "I comandi usano il path relativo `wiki/scripts/wiki.py` dalla radice del repo". Il progetto si trova in `{project-root}/`, mentre `wiki/` è nella radice del repository `academic-research-prisma-wiki-rag/`. Il ricercatore deve cambiare directory tra un'operazione e l'altra.

**Soluzione:** Usare path assoluto ovunque nella documentazione delle skill:
```bash
py /path/to/repo/wiki/scripts/wiki.py query --workspace {wiki_workspace} --q "..."
```
Oppure: aggiungere un `wiki-path` in `.project-state.json` che punta all'installazione del sistema.

---

### L3 — hybrid_rag.py deployment non specificato
**File:** `skills/hybrid-rag/SKILL.md` riga 77; pipeline-ricerca  
**Problema:** La skill dice "se non esiste: leggi `~/.claude/skills/hybrid-rag/hybrid_rag_template.py` e scrivilo con Write tool". Ma nella nuova architettura `{project-root}/` è la cartella di lavoro. Il ricercatore deve copiare 48KB di codice Python nella sua cartella di progetto ad ogni nuovo progetto. Non è scalabile.

**Soluzione:** Referenziare `hybrid_rag.py` tramite path assoluto alla sua posizione nel repo, oppure creare un wrapper leggero `run_rag.py` che importa dal template senza copiarlo.

---

### L4 — pipeline-regista: nessuna gestione del caso wiki non inizializzato
**File:** `docs/superpowers/specs/2026-06-01-pipeline-architecture.md` §7.5  
**Problema:** Il flusso di inizializzazione chiede il `wiki_workspace` ma non prevede il caso in cui l'utente non abbia ancora un wiki. La wiki richiede setup (LanceDB, bge-m3 download ~2.3GB, configurazione). Un ricercatore che parte da zero non può iniziare immediatamente.

**Soluzione:** Aggiungere percorso "no-wiki":
```
wiki_workspace disponibile? 
  SÌ → configurare, procedere normalmente
  NO → "La wiki non è necessaria per iniziare. 
        Puoi avviarla successivamente con `wiki_check_setup.py`.
        Vuoi procedere senza memoria cross-progetto per ora?"
        → .project-state.json: wiki.status = "not_configured"
        → Le skill saltano le query wiki, funzionano senza
```

---

### L5 — Atomic write per state file non specificato
**File:** Architettura spec §5; tutti i state file  
**Problema:** Se il processo viene interrotto durante la scrittura di `.project-state.json` (crash, quota esaurita, interruzione utente), il file rimane parzialmente scritto → JSON invalido → il progetto è irrecuperabile senza intervento manuale.

**Soluzione:** Specificare in tutti i state file il pattern write-atomico:
```python
import json, tempfile, os
def write_state(path, data):
    dir_ = os.path.dirname(path)
    with tempfile.NamedTemporaryFile('w', dir=dir_, delete=False, suffix='.tmp') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        tmp = f.name
    os.replace(tmp, path)  # atomic on POSIX; near-atomic on Windows
```
Documentarlo come pattern obbligatorio per tutte le skill.

---

## 4. PROBLEMI DI STABILITÀ CODICE

### ST1 — Rate limiting assente nei server MCP
**File:** `mcp-servers/eric/server.py` (e presumibilmente gli altri)  
**Problema:** Nessun delay tra richieste. Per corpus grandi (> 500 paper), la paginazione ERIC può fare 5-10 chiamate in rapida successione → throttling o ban IP temporaneo.

**Soluzione:** Aggiungere in tutti i server:
```python
import time
RATE_LIMIT_DELAY = 0.5  # secondi tra richieste

def search(query, limit=200, ...):
    results = []
    for page in paginate(...):
        results.extend(page)
        time.sleep(RATE_LIMIT_DELAY)
    return results
```

---

### ST2 — Abstract troncato a 300 caratteri nel server ERIC
**File:** `mcp-servers/eric/server.py` riga 74  
**Problema:** L'abstract viene troncato nella funzione di formattazione. Se il JSON raw viene costruito da questo output, i record avranno abstract incompleti. Il RAG viene indicizzato con metà dell'abstract → qualità retrieval degradata.

**Soluzione:** Separare la funzione di formattazione per l'utente dalla funzione di export JSON. Il JSON raw deve contenere l'abstract completo; solo la presentazione in chat può troncare.

---

### ST3 — Validazione piano-analisi.json non integrata
**File:** `skills/research-design/piano-analisi-schema.json`  
**Problema:** Lo schema JSON è stato creato ma nessuna skill lo usa per validare il file prima di scriverlo. Un errore nella compilazione di `piano-analisi.json` (es. tipo sbagliato, campo mancante) passerà silenzioso e causerà errori in `data-analysis` a distanza di giorni.

**Soluzione:** Aggiungere snippet di validazione in Fase 5e di research-design:
```python
import json, jsonschema
schema = json.loads(open("skills/research-design/piano-analisi-schema.json").read())
instance = json.loads(open("design/fase-5-analisi/piano-analisi.json").read())
jsonschema.validate(instance, schema)  # lancia ValidationError se invalido
```

---

### ST4 — matrice_dati.xlsx: metodo di creazione non specificato
**File:** `docs/superpowers/specs/2026-06-01-pipeline-architecture.md` §8  
**Problema:** La spec prevede `raccolta-dati/matrice_dati.xlsx` ma non specifica come viene creato. Claude Code non può creare file Excel binari natively. Opzioni: (a) creare CSV e convertire, (b) usare openpyxl, (c) creare template XLSX precompilato.

**Soluzione:** Specificare il metodo: la skill `data-collection` crea `matrice_dati.csv` (plain text, creabile con Write tool) con header pre-compilati da `piano-analisi.json`. Il CSV viene poi convertito in XLSX tramite script:
```python
import pandas as pd
df = pd.read_csv("raccolta-dati/matrice_dati.csv")
df.to_excel("raccolta-dati/matrice_dati.xlsx", index=False)
```

---

## 5. MODIFICHE MIGLIORATIVE (non critiche)

### M1 — CRediT taxonomy per authorship nel preprint
Aggiungere sezione nella skill `preprint` per la dichiarazione dei contributi autoriali secondo CRediT (Contributor Roles Taxonomy). Richiesta da molte riviste e da Open Research Europe.

### M2 — FAIR data statement
Per submission su Open Research Europe o Zenodo con dati aperti, aggiungere template FAIR data statement nella checklist pre-submission.

### M3 — Registered Report come tipo di submission
La skill preprint menziona "Registered Report" una volta ma non sviluppa il flusso. Aggiungere come opzione distinta con timeline diversa (si prepara PRIMA della raccolta dati, viene inviato in Fase 1 a una rivista partner).

### M4 — Versioning delle entity pages wiki
Quando un paper viene ingestito due volte (aggiornamento di metadati), la wiki fa upsert silenzioso. Aggiungere nel project-log.md una entry per ogni aggiornamento di entity page.

### M5 — Timeout per le chiamate MCP
Aggiungere timeout espliciti (es. 30 secondi) in tutti i server MCP. Senza timeout, una chiamata bloccata può appendere l'intera sessione.

### M6 — Lingua del preprint: inglese per arXiv/SSRN, italiano accettato per ORE
Specificare nella skill `preprint` che arXiv, SSRN e PsyArXiv richiedono inglese, mentre Open Research Europe accetta anche italiano (per progetti Horizon italiani) e EdArXiv accetta entrambe le lingue.

### M7 — IRB tracking nel master state
Aggiungere campo `ethics_approval` in `.project-state.json`:
```json
"ethics_approval": {
  "status": "pending | approved | exempt | not_required",
  "committee": "Comitato Etico Ateneo X",
  "protocol_id": "CE-2026-001",
  "approved_at": "ISO8601"
}
```

### M8 — Conflict of interest declaration nel preprint
La skill preprint dovrebbe chiedere: *"Ci sono conflitti di interesse da dichiarare (finanziamenti, affiliazioni, interesse commerciale)?"* e includere la risposta nel documento.

### M9 — File .gitignore per il project-root
La cartella `{project-root}/` contiene dati sensibili (trascrizioni, dati personali). La skill `pipeline-regista` dovrebbe creare un `.gitignore` di default che esclude `raccolta-dati/trascrizioni/`, `raccolta-dati/matrice_dati.*`, e `rag_db/`.

---

## 6. ROADMAP CORREZIONI PRIORITIZZATA

### Sprint 1 — Bloccanti (prima di qualsiasi altra implementazione)
1. Refactoring output JSON tutti i server MCP (C2) — 3-4 ore per server
2. Creare `prisma_screening.py` (C1) — 2-3 ore
3. Rimuovere fallback RAG su screening_prisma.json (C3) — 30 min
4. Aggiornare architettura spec: layout flat per PRISMA (C4) — 1 ora

### Sprint 2 — Rigore scientifico (prima del testing con utenti reali)
5. Fix terminologia d=0.5 (S1) — 15 min
6. Aggiungere Hedges' g (S2) — 30 min
7. Fix decision tree Q6 per casi qualitativi (S3) — 1 ora
8. Fix FIML→Multiple Imputation (S6) — 30 min
9. Aggiungere reporting standards CONSORT/STROBE/COREQ (S7) — 2 ore

### Sprint 3 — Stabilità (prima del rilascio)
10. Atomic write pattern per tutti gli state file (L5) — 1 ora (snippet riusabile)
11. Rate limiting in tutti i server MCP (ST1) — 30 min per server
12. Fix abstract troncato in ERIC server (ST2) — 1 ora
13. Integrazione validazione piano-analisi.json (ST3) — 1 ora
14. CSV invece di XLSX per matrice dati (ST4) — 15 min spec

### Sprint 4 — Coerenza e miglioramenti
15. Canonicalizzare eligibility vs extraction_table (L1)
16. Path assoluti per wiki.py (L2)
17. Soluzione hybrid_rag.py deployment (L3)
18. Percorso no-wiki per pipeline-regista (L4)
19. Miglioramenti M1-M9 selezionati
