# AI Longterm Wiki Memory — Spec di Implementazione
> Revisionato da Claude Code — 2026-05-20

---

## 1. Architettura generale

```
<workspace>/
├── AGENTS.md                  ← istruzioni operative (da aggiornare con ref wiki)
├── SOUL.md                    ← persona Agent (invariata)
├── IDENTITY.md                ← nome, tono (invariato)
├── skills/
│   └── wiki-core.md           ← skill caricata a ogni sessione OpenClaw
├── wiki-session.md            ← stato sessione corrente (generato da wiki.py)
├── wiki.config.json           ← configurazione istanza
├── scripts/
│   ├── wiki.py                ← entry point unico
│   ├── wiki_embed.py          ← chunking + embedding bge-m3
│   ├── wiki_lancedb.py        ← operazioni LanceDB
│   └── wiki_index.py          ← generazione index.md
├── wiki/                      ← Livello 1: conoscenza permanente
│   ├── .schema.md
│   ├── log.md
│   ├── entities/
│   ├── concepts/
│   └── synthesis/
├── wiki-works/                ← Livello 2: ricerche attive
│   └── <progetto>/
│       ├── .schema.md
│       ├── log.md
│       ├── raw/
│       ├── entities/
│       ├── concepts/
│       └── synthesis/
└── memory/
    └── lancedb/               ← escluso da git, ricostruibile
```

**Invariante fondamentale:** Agent non scrive mai direttamente nel wiki. Tutto passa per `wiki.py`. La skill guida il *quando* e il *perché*, gli script gestiscono il *come*.

---

## 2. Integrazione OpenClaw

### Caricamento skill

`wiki-core.md` si trova in `<workspace>/skills/` — OpenClaw la carica automaticamente a ogni sessione secondo la gerarchia di precedenza delle skill.

`wiki-session.md` non è una skill tradizionale: è un file che Agent legge attivamente. Va aggiunta in `AGENTS.md`:

```
All'inizio di ogni sessione leggi <workspace>/wiki-session.md per il contesto wiki corrente.
Prima di qualsiasi operazione wiki, rileggi skills/wiki-core.md per verificare il protocollo.
```

La seconda riga forza Agent a ricaricare le regole prima di agire — non solo a sessione start — mitigando la perdita di peso delle istruzioni su context window lunghe.

### LanceDB separato dalla memoria personale

Il wiki usa `memory/lancedb/` **fisicamente separato** dalla memoria ibrida RAG esistente di Agent. I due sistemi non condividono directory né tabelle. Agent è il punto di integrazione: durante QUERY interroga entrambi i sistemi e sintetizza la risposta senza distinzione esplicita tra le fonti.

**Regola synthesis:** una pagina wiki viene creata solo se i criteri di threshold del DESIGN.md (§synthesis-threshold) sono soddisfatti usando fonti wiki. Il contributo della memoria personale alla risposta non conta ai fini della creazione di nuove pagine.

---

## 3. `wiki-core.md` — Skill permanente

### Struttura

```markdown
---
name: wiki-core
description: Protocollo wiki per AI Agent — classificazione intent, workflow, checklist
---

[Checklist obbligatoria, tabella classificazione intent, selezione workspace,
output di classificazione — come da §3 di questo spec]
```

Il file `wiki-core.md` reale conterrà il testo completo delle sezioni seguenti,
formattato come istruzioni dirette a Agent (seconda persona singolare).

### Checklist obbligatoria pre-azione

Agent esegue questa checklist per ogni messaggio prima di procedere:

```
1. Leggi wiki-session.md → verifica status (ok / in-progress / needs-repair)
2. Se status ≠ ok → avvisa l'utente prima di qualsiasi operazione
3. Classifica l'intent del messaggio (vedi §classificazione)
4. Il messaggio contiene più di un intent? Se sì, gestiscili in sequenza
5. Emetti riga di classificazione: [INTENT: X | WORKSPACE: Y | CERTEZZA: alta/media/bassa]
6. Se CERTEZZA = bassa → chiedi conferma all'utente prima di procedere
7. Esegui il workflow corrispondente all'intent
```

### Classificazione intent

| Pattern linguistico | Intent |
|--------------------|--------|
| "studia questo", "salva", "ho trovato", "leggi questo", URL nudo, allegato | INGEST |
| domanda diretta, "cosa sai di", "dimmi", "spiegami", "come funziona" | QUERY |
| "controlla il wiki", "pulizia", "lint", "manutenzione" | LINT |
| tutto il resto | AMBIGUO → chiedi conferma |

**Protocollo conferma (ambiguo):** una sola riga, mai verbose:
> "Vuoi che salvi questo nel wiki o stai solo condividendo?"

### Selezione workspace automatica

1. Leggi `wiki.config.json` → lista progetti con keywords
2. Conta match tra parole chiave del messaggio e keywords di ogni progetto
3. Se un progetto ha chiaramente più match → selezionalo
4. Se pareggio tra due progetti → chiedi all'utente
5. Se nessun match → usa `wiki/` principale

### Output di classificazione (sempre visibile prima di agire)

```
[INTENT: INGEST | WORKSPACE: trading | CERTEZZA: alta]
```

L'utente può correggere questa riga prima che Agent esegua qualsiasi operazione.

---

## 4. `wiki-session.md` — Stato sessione

Generato esclusivamente da `wiki.py session-update`. Agent non lo modifica mai direttamente.

```markdown
# Wiki Session — YYYY-MM-DD HH:MM

## Status
status: ok | in-progress | needs-repair

## Workspace attivo
Progetto: <nome>
Path: <path relativo>

## Ultima operazione
Tipo: ingest | query | lint | rebuild | nessuna
Completata: YYYY-MM-DD HH:MM
Dettaglio: <output sintetico>

## Wiki principale
Pagine totali: N | Ultimo lint: YYYY-MM-DD
```

**Robustezza:** il campo `status: in-progress` viene scritto all'inizio di ogni operazione, `status: ok` solo al termine. Un crash lascia `in-progress` → Agent lo rileva alla sessione successiva e avvisa l'utente.

---

## 5. `wiki.py` — Entry point

### Interfaccia

```
wiki.py <comando> [argomenti]

  ingest         --workspace <path> --source <url|file> --title <str>
  query          --workspace <path> --q <stringa>
  lint           --workspace <path> [--full]
  index          --workspace <path>
  rebuild        --workspace <path>
  session-update --workspace <path> --op <tipo> --status <ok|failed|in-progress> [--detail <json>]
```

### Output JSON

Ogni comando produce JSON su stdout:

```json
{ "status": "ok", "op": "ingest", "pages_written": 3, "conflicts": [], "mini_lint": "ok" }
{ "status": "error", "code": "checkpoint_failed", "message": "...", "recoverable": true }
{ "status": "conflict", "level": 3, "page": "...", "detail": "..." }
```

Agent legge questo output e lo presenta all'utente in linguaggio naturale.

### Lock file

All'avvio ogni comando scrive `<workspace>/.wiki-lock`. Lo rimuove al termine (ok o error).

Se `.wiki-lock` esiste all'avvio → output:
```json
{ "status": "error", "code": "lock_exists", "message": "Operazione precedente non conclusa", "recoverable": true }
```
Agent avvisa l'utente e non procede.

### Validazione config

`wiki.py` valida `wiki.config.json` all'avvio di ogni comando. Se manca un campo obbligatorio:
```json
{ "status": "error", "code": "invalid_config", "missing_field": "thresholds.staleness_days" }
```

---

## 6. Moduli Python

### `wiki_embed.py`

- Usa il tokenizer nativo di bge-m3 per contare i token (risolve ambiguità §chunking)
- Chunking boundary-aware: non taglia mai nel mezzo di sezioni `##` o `###`
- Chunk size: 512 token, overlap: 64 token
- Soglia pagina intera vs chunked: 1500 token (tokenizer bge-m3)
- Output: `List[{chunk_id, chunk_text, vector, content_hash, page_hash}]`

### `wiki_lancedb.py`

Tabelle: `wiki_pages`, `staging_wiki_pages` (schema identico).

Schema:
```
path          string   — path relativo da workspace root
chunk_id      int      — 0 = pagina intera, 1..N = chunk
chunk_text    string   — testo embeddato
content_hash  string   — SHA256(chunk_text)
page_hash     string   — SHA256(intera pagina) per rilevare rechunk
vector        float[1024]
last_embedded float    — unix timestamp
```

Index: `(path, chunk_id) UNIQUE`, `vector ANN (HNSW)`.

**Upsert corretto:** `upsert(path, chunks)` cancella *tutti* i chunk con quel path, poi inserisce i nuovi. Questo elimina chunk orfani quando una pagina cambia numero di chunk.

**Detect rename:** confronta `set(path in LanceDB)` vs `set(file su filesystem)`. Se un path solo-LanceDB e un path solo-filesystem hanno lo stesso `content_hash` → rename → aggiorna path senza re-embedding.

**Operazioni atomiche:**
- `promote_staging()` → upsert da staging a wiki_pages, svuota staging
- `rollback_staging()` → svuota staging, nessuna modifica a wiki_pages

### `wiki_index.py`

- "Stale" definito: `mtime(index.md) < max(mtime(*.md))` nella directory wiki
- Legge `index_token_budget` da `wiki.config.json`
- Strategia riduzione a tre livelli se budget superato:
  1. Rimuovi descrizioni → solo `- [[slug]]`
  2. Indici separati per categoria
  3. Split alfabetico per categorie enormi

---

## 7. `wiki.config.json`

```json
{
  "workspace": "/path/to/workspace",
  "projects": {
    "trading": {
      "path": "wiki-works/trading",
      "keywords": ["mercati", "indicatori", "trading", "borsa", "azioni"]
    },
    "ricerca": {
      "path": "wiki-works/ricerca",
      "keywords": ["paper", "studio", "PRISMA", "articolo", "ricerca"]
    }
  },
  "thresholds": {
    "index_token_budget": 4000,
    "staleness_days": 90,
    "similarity_merge": 0.95,
    "similarity_orphan": 0.50,
    "synthesis_min_tokens": 300,
    "synthesis_min_sources": 2,
    "chunk_size_tokens": 512,
    "chunk_overlap_tokens": 64,
    "page_chunk_threshold_tokens": 1500,
    "quality_filter_min_score": 6
  },
  "lancedb": {
    "path": "memory/lancedb",
    "embedding_model": "BAAI/bge-m3"
  }
}
```

---

## 8. §error-states — Stati invalidi e recovery

| Stato | Segnale | Azione automatica | Intervento utente |
|-------|---------|-------------------|----------------|
| `.wiki-lock` presente | Lock file esiste | Agent avvisa, non procede | Conferma se procedere |
| `.tmp` su disco senza lock | Ingest interrotto | `wiki.py` cancella `.tmp`, rollback staging, log `ingest-failed` | No |
| `wiki-session.md` status `in-progress` | Sessione precedente non conclusa | Agent avvisa prima di qualsiasi operazione | Conferma recovery o reset |
| LanceDB assente o corrotta | Errore apertura DB | Propone `wiki.py rebuild` | Conferma (operazione distruttiva) |
| Config mancante o malformato | Errore validazione | Agent avvisa con campo specifico | Correggere config |
| `staging_wiki_pages` non vuota all'avvio | Staging residuo | `wiki.py` svuota silenziosamente, log entry | No |
| Mini-lint fallito | `mini_lint: failed` nel JSON | Agent avvisa, `wiki-session.md` → `needs-repair` | Eseguire `wiki.py lint` |
| Conflitto Livello 3 | `conflicts: [{level: 3}]` | Agent presenta conflitto, blocca merge pagina specifica | Decide versione canonica |
| Skill `wiki-core.md` non caricata | Agent non emette riga `[INTENT:]` | — | Verificare `<workspace>/skills/` |

**Principio:** `wiki.py` non lascia mai il sistema in uno stato silenziosamente corrotto. Ogni anomalia produce un codice errore JSON specifico. Agent non inventa recovery — segue questa tabella o chiede all'utente.

---

## 9. Tipi di log aggiuntivi rispetto a DESIGN.md v2

Aggiungere ai tipi esistenti in `log.md`:

| Tipo | Quando |
|------|--------|
| `rebuild-lancedb` | Dopo `wiki.py rebuild` |
| `promote` | Fusione pagina da wiki-works → wiki/ |
| `rename` | Rilevamento rename durante LINT |
| `session-repair` | Recovery da stato `in-progress` |

---

## 10. Regole di coerenza con DESIGN.md v2

Questo spec **estende** DESIGN.md v2, non lo sostituisce. Le sezioni del DESIGN.md restano valide. Le sezioni qui presenti hanno precedenza in caso di conflitto.

Correzioni specifiche al DESIGN.md v2 incorporate in questo spec:
- §chunking: "token" = tokenizer bge-m3 (non approssimazione a caratteri)
- §index-generation: "stale" definito con confronto mtime
- §lancedb-schema: upsert opera su tutti i chunk del path, non solo chunk_id=0
- §mini-lint: aggiunto campo `status` in wiki-session.md per rilevamento crash
- Log: aggiunti tipi `rebuild-lancedb`, `promote`, `rename`, `session-repair`
- Conflict Livello 3: il blocco parziale avviene trattenendo la pagina in staging (non promossa) fino a risposta dell'utente

---

*Spec v1 — 2026-05-20 — Redatto da Claude Code*
