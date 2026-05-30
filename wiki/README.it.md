# AI Longterm Wiki Memory — Plugin OpenClaw

[![Version](https://img.shields.io/badge/versione-3.1.2-informational)](CHANGELOG.md)
[![Tests](https://img.shields.io/badge/tests-124%20passati-brightgreen)](tests/)
[![OpenClaw](https://img.shields.io/badge/funziona%20con-OpenClaw-purple)](https://github.com/openclaw/openclaw)

**Memoria semantica a lungo termine per agenti AI**

Il tuo agente AI dimentica tutto tra una sessione e l'altra. Questo sistema gli dà una base di conoscenza strutturata e auto-gestita — ogni pagina è contemporaneamente un documento leggibile e un vettore interrogabile.

[Avvio rapido](#avvio-rapido) · [Funzionalità](#funzionalità) · [Ingestion PDF](#ingestion-pdf-multi-sorgente-v20) · [Interfaccia Web](#interfaccia-web-v21) · [Dashboard](#dashboard-osservabilità-v22) · [Integrazione](#integrazione) · [CLI Reference](#cli-reference)

---

## Il problema

Gli agenti AI dimenticano tutto tra una sessione e l'altra. I sistemi di memoria esistenti sono piatti — un mucchio di fatti con timestamp, non una base di conoscenza. Quando lavori su ricerche ricorrenti (letteratura accademica, analisi competitiva, trading, diritto), hai bisogno di conoscenza **organizzata, interconnessa e ricercabile semanticamente** — che cresce nel tempo senza bookkeeping manuale.

## Cosa fa

AI Longterm Wiki Memory dà al tuo agente una wiki a due livelli che gestisce autonomamente:

| Livello | Directory | Scopo |
|---------|-----------|-------|
| Permanente | `wiki/` | Conoscenza curata: entità, concetti, pagine di sintesi |
| Ricerca attiva | `wiki-works/<progetto>/` | Fonti grezze + pagine strutturate per dominio |

L'agente ingestisce pagine web, articoli e PDF; recupera per significato semantico (non per parole chiave); rileva conoscenza obsoleta o contraddittoria; sintetizza nuove pagine automaticamente quando più fonti supportano un'inferenza non ovvia — tutto senza corrompere la base di conoscenza anche se un processo crasha a metà operazione.

```
Utente: "studia questo paper sulle architetture RAG"

Agente: [INTENT: INGEST | WORKSPACE: ricerca | CERTEZZA: alta]
        → scrive pagine strutturate come file .tmp
        → wiki.py ingest: commit atomico staging → produzione
        → markdown + embedding scritti nella stessa operazione
        → "2 pagine scritte. Mini-lint: ok."

Utente: "cosa sai sul retrieval-augmented generation?"

Agente: [INTENT: QUERY | WORKSPACE: ricerca | CERTEZZA: alta]
        → ricerca vettoriale semantica, nessuna scansione di file
        → legge le pagine più rilevanti, sintetizza con citazioni
        → sintesi supera la soglia → salvata automaticamente come nuova pagina wiki
```

---

## L'idea centrale: wiki e vector DB come un'unica cosa

> **Il pattern wiki di Karpathy** ([gist](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)) prevede che l'LLM navighi la wiki *leggendo* i file markdown — ispezione visiva di una struttura di directory. Questo si rompe su larga scala: l'agente non può scansionare decine di pagine ad ogni query.

Questo progetto risolve il problema con un'**architettura a doppia rappresentazione**: ogni pagina esiste in due forme sincronizzate.

```
  Scrivi una pagina wiki
        │
        ▼
┌───────────────────┐     ┌──────────────────────────┐
│  File Markdown    │     │  LanceDB vector store     │
│  wiki/concepts/   │◄────►  embedding bge-m3         │
│  rag.md           │     │  (1024-dim, indice HNSW)  │
└───────────────────┘     └──────────────────────────┘
   gli umani sfogliano        l'LLM recupera
   l'LLM genera               semanticamente
```

Markdown e embedding sono **scritti atomicamente** e mantenuti sincronizzati. Il lint pass rileva e ripara qualsiasi deriva.

Una query su *"come gli LLM gestiscono il contesto lungo"* recupera pagine su *"positional encoding"* e *"sliding window attention"* — senza alcuna sovrapposizione di parole chiave — perché il significato è vicino nello spazio degli embedding.

---

## Funzionalità

### Ricerca vettoriale semantica
Embedding [bge-m3](https://huggingface.co/BAAI/bge-m3) — multilingua (100+ lingue), 1024 dim, indice HNSW. Le query recuperano per significato. Nessun passo di re-indicizzazione. Il vector DB è l'indice, mantenuto continuamente.

### Scritture atomiche — resistente ai crash
Ogni ingest segue un pattern `.tmp → staging LanceDB → promozione atomica`. Un crash lascia il sistema in uno stato rilevabile (`in-progress` in `wiki-session.md`). L'agente si recupera alla sessione successiva senza perdita di dati, senza corruzione silenziosa.

### Iniezione di contesto pre-prompt
`wiki_context.py` esegue una ricerca vettoriale **prima di ogni messaggio dell'utente** e aggiunge un blocco `<wiki-context>` con le pagine più rilevanti. Questo elimina il principale failure mode degli approcci basati su skill — l'agente ottiene contesto solo quando classifica un messaggio come QUERY:

```
L'utente invia un messaggio
        │
        ▼
wiki_context.py → ricerca vettoriale
        │
        ▼
Blocco <wiki-context> aggiunto al prompt
        │
        ▼
L'agente ha sempre il contesto rilevante — indipendente dalla classificazione dell'intent
```

Installazione con un comando (OpenClaw):
```bash
py scripts/setup_openclaw.py --workspace /path/al/workspace
```

### Routing multi-progetto
Definisci più domini di ricerca in `wiki.config.json` con liste di keyword. L'agente seleziona automaticamente il workspace corretto dal contenuto del messaggio — nessuna specifica manuale necessaria.

### Sintesi automatica
Quando una risposta a una query integra ≥2 fonti wiki, supera 300 token, e aggiunge inferenze non letterali, l'agente salva automaticamente una nuova pagina wiki con embedding. La conoscenza si accumula nel tempo.

### Lint auto-riparante
`wiki.py lint --full` rileva e ripara:
- **Link wiki rotti** (`[[pagina]]` senza file corrispondente)
- **Entry orfane LanceDB** (vettori per file eliminati — rimossi automaticamente)
- **Rename** (file spostato → aggiorna path nel DB senza re-embedding tramite `content_hash`)
- **Duplicati semantici** (cosine similarity > 0.95 tra pagine)

### Index con budget token
`index.md` rispetta un budget token configurabile (default 4000). Se superato, applica strategie di riduzione automaticamente — l'agente può navigare anche su context window limitate.

### Dashboard di osservabilità
Un tab `[Stats]` nel frontend web mostra lo stato di salute del wiki in tempo reale: pagine con/senza embedding, pagine stale, top-10 pagine più interrogate, stato del lint con timestamp e conteggio warning, schedule auto-lint. Il lint può anche essere avviato manualmente dal browser.

---

## Ingestion PDF multi-sorgente *(v2.0)*

Qualsiasi PDF da qualsiasi sorgente converge in `pdf-inbox/` e viene processato automaticamente.

```
┌──────────────────┐   ┌──────────────────┐   ┌───────────────────┐
│  Chat Telegram   │   │  CLI / URL       │   │  Drop manuale     │
│  (allegato)      │   │  (ingest-pdf)    │   │  (filesystem)     │
└────────┬─────────┘   └────────┬─────────┘   └────────┬──────────┘
         │                      │                       │
         └──────────────────────┼───────────────────────┘
                                ▼
                   workspace/pdf-inbox/
                      paper.pdf
                   .registry.json  ← hash SHA-256 per file
                                │
                   wiki.py scan-inbox
                                │
                   wiki_pdf_watcher.py
                      extract_text (pdfplumber)
                                │
                                ▼
             wiki-works/<progetto>/raw/paper.md
             (frontmatter: source: pdf, original, extracted_at)
                                │
                                ▼
                   L'agente struttura in pagine .tmp
                                │
                                ▼
                   wiki.py ingest → wiki/ + LanceDB
```

**Come funziona il rilevamento delle modifiche:** hash SHA-256 per file. Stesso hash + `deposited` → salta. Hash diverso → riprocessa. Lo stato `pending` viene scritto prima dell'estrazione — un crash lascia il registro recuperabile.

**Comandi:**
```bash
# File locale
wiki.py ingest-pdf --workspace <path> --file paper.pdf

# URL remoto (limite 50 MB)
wiki.py ingest-pdf --workspace <path> --file https://arxiv.org/pdf/2401.00001

# Scansiona l'intero inbox — idempotente, sicuro per cron
wiki.py scan-inbox --workspace <path>
```

**Telegram / OpenClaw:** nessun nuovo plugin necessario. La regola agente in `AGENTS_PATCH.md` gestisce tutto:
> Quando l'utente invia un PDF → chiama `wiki.py ingest-pdf --workspace <path> --file <attachment_path>`

**PDF scansionati** (senza testo selezionabile) vengono segnalati con `status: failed` nel registro e saltati nelle scansioni future — nessun loop infinito di retry.

---

## Interfaccia Web *(v2.1)*

Un frontend web read-only per esplorare il wiki nel browser — senza toccare nessun workflow.

```
py scripts/wiki.py serve --workspace /path/al/workspace [--port 7331] [--no-auth]
```

Apri `http://localhost:7331`.

```
┌──────────────────────────────────────────────────────────┐
│  AI Wiki Memory   [wiki] [ricerca] [tutti]   🔍  ● live  │
├───────────────────────────┬──────────────────────────────┤
│                           │  # Titolo pagina             │
│    GRAFO DELLA            │  concetto · ricerca · data   │
│    CONOSCENZA             │  ──────────────────────────  │
│    (D3 force-directed)    │  [markdown renderizzato]     │
│                           │                              │
│  ● entità (blu)           │  ── Link uscenti ──          │
│  ● concetti (verde)       │  ── Link entranti ──         │
│  ● sintesi (viola)        │  ── Pagine simili ──         │
│  ── link esplicito        │     embedding (87%)          │
│  ╌╌ similarità semantica  │                              │
└───────────────────────────┴──────────────────────────────┘
```

**Funzionalità:**
- **Grafo force-directed** — nodi dimensionati per grado di connessione, colorati per categoria (entità/concetti/sintesi), etichette su tutti i nodi
- **Archi espliciti** — riferimenti `[[wiki-link]]` come frecce solide
- **Archi semantici** — similarità coseno LanceDB ≥ 0.65 come linee tratteggiate
- **Aggiornamenti live** — WebSocket invia `graph_update` ad ogni modifica file; il grafo transiziona senza spostare i nodi
- **Animazione query hit** — quando `wiki.py query` viene eseguito, i nodi recuperati pulsano oro→rosso per 4 secondi
- **Pannello pagina** — click su un nodo → markdown renderizzato, link uscenti/entranti, pagine simili con barre di similarità
- **Tab per progetto** — filtra il grafo per workspace
- **Protezione con password** — auth JWT cookie (sessione 7 giorni); imposta tramite `wiki.config.json` o env `WIKI_PASSWORD`; bypass con `--no-auth` per uso locale

**Config (opzionale):**
```json
{
  "frontend": {
    "password": "la-tua-password",
    "session_days": 7
  }
}
```

**Il frontend è strettamente read-only per i contenuti wiki.** Tutti i workflow (ingest, query, lint) continuano a funzionare identicamente sia che il server sia in esecuzione o meno.

---

## Dashboard Osservabilità *(v2.2)*

Un tab `[Stats]` integrato nel server web mostra lo stato del wiki senza bisogno di comandi CLI.

```
┌──────────────────────────────────────────────────────────┐
│  AI Wiki Memory  [Graph] [Stats]          🔍  ● live     │
├──────────────────────────────────────────────────────────┤
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌─────────┐  │
│  │ 47 pagine│  │ 312 chunk│  │ 94% cop. │  │ 3 stale │  │
│  └──────────┘  └──────────┘  └──────────┘  └─────────┘  │
│                                                          │
│  Più interrogate              Stato lint                 │
│  ─────────────────            ─────────────────────────  │
│  rag.md           12q         Ultima esec.: 2026-05-23   │
│  openai.md         8q         0 errori · 2 avvisi        │
│                               [Esegui lint ora]          │
│  Auto-lint: ogni 24h · prossima: 2026-05-24 08:15        │
└──────────────────────────────────────────────────────────┘
```

**Cosa mostra:**
- **4 KPI card** — pagine totali, chunk totali, copertura embedding %, pagine stale
- **Più interrogate** — top-10 pagine per frequenza di query, aggregate da `.wiki-query-log.jsonl`
- **Pagine stale** — pagine non modificate da più di `thresholds.staleness_days` giorni (default 90)
- **Pagine senza embedding** — file presenti su disco ma assenti da LanceDB
- **Stato lint** — timestamp ultimo run, conteggio errori e warning (da `.wiki-lint-status.json`)
- **Schedule auto-lint** — prossima esecuzione pianificata se `frontend.lint_interval_hours` è configurato

**Trigger lint:** il pulsante "Esegui lint ora" chiama `POST /api/lint`. Risponde 409 se un lint è già in corso.

**Auto-lint:** aggiungere a `wiki.config.json` per eseguire lint automaticamente ogni N ore:
```json
{
  "frontend": {
    "lint_interval_hours": 24
  }
}
```

**Endpoint REST (protetti da auth):**
| Endpoint | Descrizione |
|----------|-------------|
| `GET /api/stats` | Snapshot completo di osservabilità in JSON |
| `POST /api/lint` | Avvia `wiki.py lint --full`; risponde 409 se occupato |

---

## Architettura

```
workspace/
├── skills/
│   └── wiki-core.md          ← skill permanente: classificazione intent, workflow
├── wiki-session.md           ← stato sessione live (generato da wiki.py)
├── wiki.config.json          ← configurazione
├── scripts/
│   ├── wiki.py               ← entry point CLI unificato (9 comandi)
│   ├── wiki_context.py       ← iniettore contesto pre-prompt (hook)
│   ├── wiki_pdf_watcher.py   ← scanner inbox PDF (hash detection + pdfplumber)
│   ├── wiki_embed.py         ← chunking boundary-aware + embedding bge-m3
│   ├── wiki_lancedb.py       ← operazioni LanceDB (upsert, staging, rename)
│   ├── wiki_index.py         ← generazione index.md con budget token
│   ├── wiki_graph.py         ← costruttore nodi/archi (filesystem + LanceDB, cache 30s)
│   └── wiki_server.py        ← server FastAPI: REST, WebSocket, JWT auth, endpoint stats/lint
├── frontend/
│   └── index.html            ← SPA: grafo D3.js + pannello pagina + client WebSocket
├── .wiki-lint-status.json    ← ultimo risultato lint (scritto atomicamente da cmd_lint)
├── pdf-inbox/                ← tutte le sorgenti PDF convergono qui
│   └── .registry.json        ← hash + status per PDF (scrittura atomica)
├── wiki/                     ← base di conoscenza permanente
│   ├── entities/             ← persone, strumenti, organizzazioni
│   ├── concepts/             ← teorie, strategie, definizioni
│   └── synthesis/            ← inferenze cross-fonte
├── wiki-works/               ← ricerche attive per progetto
│   └── <progetto>/
│       ├── raw/              ← fonti grezze e PDF estratti
│       ├── entities/
│       ├── concepts/
│       └── synthesis/
└── memory/
    └── lancedb/              ← database vettoriale (escluso da git, ricostruibile)
```

**Invariante fondamentale:** L'agente non scrive mai direttamente nel wiki. Tutto passa per `wiki.py`. La skill guida il *quando* e il *perché*; gli script gestiscono il *come*.

---

## Integrazione

Funziona con qualsiasi agente che può leggere file e chiamare bash. Questo repo fornisce supporto nativo per OpenClaw.

### Claude Code

Per l'integrazione nativa con MCP server (raccomandata), vedi il repo dedicato: [`ai-longterm-wiki-memory-ClaudeCode`](https://github.com/giovannifrontera/ai-longterm-wiki-memory-ClaudeCode).

> Questo repo si concentra sul plugin OpenClaw. Lo script `wiki_context.py` è condiviso — entrambe le integrazioni chiamano lo stesso backend Python.

### OpenClaw

[OpenClaw](https://github.com/openclaw/openclaw) connette Telegram, Discord e web ad agenti AI con accesso bash/file/browser sul filesystem locale.

**Setup guidato da agente (consigliato):** fornisci il link al repo in chat e chiedi all'agente OpenClaw di occuparsi dell'installazione. Legge `AGENTS.md` ed esegue:
```bash
py scripts/setup_openclaw.py --workspace /path/assoluto/al/workspace
```
Lo script rileva automaticamente il file di config OpenClaw e inietta l'entry del plugin. Passa `--config /path/al/config.json` se il rilevamento automatico fallisce.

**Setup manuale:**
```bash
cd plugins/wiki-context-plugin
npm install && npm run build
```

Aggiungi al config OpenClaw:
```json
{
  "plugins": [
    {
      "id": "wiki-context-plugin",
      "path": "/path/assoluto/ai-wiki-system/plugins/wiki-context-plugin",
      "config": {
        "workspace": "/path/assoluto/al/workspace",
        "wikiContextScript": "/path/assoluto/scripts/wiki_context.py",
        "pythonExecutable": "python",
        "k": 3
      }
    }
  ]
}

### Cosa fa l'agente automaticamente

| L'utente scrive | L'agente fa |
|-----------------|-------------|
| URL / "studia questo" / file allegato | INGEST: fetch → struttura → scrittura atomica + embedding |
| PDF via Telegram / CLI / URL | INGEST-PDF: inbox → estrai → deposita in raw/ → struttura |
| Domanda diretta / "spiegami" / "cosa sai di" | QUERY: ricerca vettoriale → legge pagine → sintetizza |
| "controlla il wiki" / "manutenzione" | LINT: link rotti, orfani, rename, duplicati semantici |
| Ambiguo | Fa una sola domanda di chiarimento, non azzarda mai |

L'agente emette sempre una riga di classificazione prima di agire — puoi correggerla prima dell'esecuzione:
```
[INTENT: INGEST | WORKSPACE: ricerca | CERTEZZA: alta]
```

### Stato sessione

`wiki-session.md` (gestito esclusivamente da `wiki.py`) traccia:
- Status: `ok` / `in-progress` / `needs-repair` / `partial-failure`
- Ultima operazione: tipo, timestamp, dettaglio
- Workspace attivo e conteggio pagine

Se l'agente trova `in-progress` all'inizio della sessione, avvisa prima di fare qualsiasi cosa.

---

## Avvio rapido

### Requisiti

- Python 3.10+
- ~2 GB disco (modello BAAI/bge-m3, scaricato automaticamente al primo avvio)

### Installazione

```bash
git clone https://github.com/giovannifrontera/ai-longterm-wiki-memory-OpenClaw
cd ai-longterm-wiki-memory-OpenClaw
pip install -r requirements.txt
```

### Configurazione

```bash
cp wiki.config.json my-workspace/wiki.config.json
# Modifica: imposta il path del workspace, aggiungi i tuoi progetti e le keyword
```

Config minimale:
```json
{
  "workspace": "/path/al/tuo/workspace",
  "pdf_inbox": {
    "project_default": "ricerca"
  },
  "projects": {
    "ricerca": {
      "path": "wiki-works/ricerca",
      "keywords": ["paper", "studio", "articolo", "revisione"]
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

> **`pdf_inbox.project_default`** — dove vanno i PDF quando il filename non corrisponde alle keyword di nessun progetto. Se omesso, usa il primo progetto definito nel config.

### Inizializza e testa

```bash
py scripts/wiki.py rebuild --workspace my-workspace/
pytest tests/ -v
# Atteso: 82 test passati
```

---

## CLI Reference

```
wiki.py <comando> [argomenti]

  ingest         --workspace <path> --pages <p1.tmp,p2.tmp,...> --log <str>
  query          --workspace <path> --q <stringa> [--k 5]
  lint           --workspace <path> [--full]
  index          --workspace <path>
  rebuild        --workspace <path>
  session-update --workspace <path> --op <tipo>
                   --status <ok|failed|in-progress|partial-failure> [--detail <json>]
  scan-inbox     --workspace <path>
  ingest-pdf     --workspace <path> --file <path-locale|url>
  serve          --workspace <path> [--host 127.0.0.1] [--port 7331] [--no-auth]

wiki_context.py  (hook — emette blocco <wiki-context> su stdout)
  --workspace <path>  --q <stringa>  [--k 3]  [--max-chars 600]
```

Ogni comando produce JSON su stdout:
```json
{ "status": "ok",   "op": "ingest",     "pages_written": 2, "mini_lint": "ok" }
{ "status": "ok",   "op": "scan-inbox", "processed": 1, "skipped": 0, "failed": 0,
  "deposited": ["wiki-works/ricerca/raw/paper.md"], "failures": [] }
{ "status": "error","code": "lock_exists", "message": "...", "recoverable": true }
```

---

## Documentazione

- [`AGENTS.md`](AGENTS.md) — istruzioni installazione per OpenClaw
- [`DESIGN.md`](DESIGN.md) — architettura completa, workflow, schema LanceDB, risoluzione conflitti
- [`SPEC.md`](SPEC.md) — spec implementativa, tabella stati di errore, dettagli integrazione
- [`skills/wiki-core.md`](skills/wiki-core.md) — skill da installare nell'agente
- [`AGENTS_PATCH.md`](AGENTS_PATCH.md) — *(legacy)* istruzioni d'uso — ora iniettate automaticamente dagli script di setup

---

## Changelog

### v3.1.2 — 2026-05-27

Refactor interno e miglioramenti ai test. Nessuna modifica funzionale al plugin OpenClaw.

### v3.0.1 — 2026-05-24

**Correzione architettura + fix animazione nodi + mockup UI**

- **Architettura corretta**: la v3.0.0 aveva erroneamente eliminato la promozione e limitato `wiki/` alla sola identità. Design corretto: `wiki-works/<topic>/` = conoscenza di dominio permanente; `wiki/` = conoscenza trasversale distillata (promossa autonomamente); `wiki/identity/` = pattern comportamentali (self-reflect). Tutti i layer indicizzati insieme in LanceDB.
- **fix: animazione nodi** — `wiki_context.py` (l'hook che gira ad ogni prompt) ora scrive i path delle pagine recuperate in `.wiki-query-log.jsonl`. Il watcher WebSocket del server li rileva e trasmette `query_hit` al frontend, che anima i nodi attivati in oro in tempo reale.
- **Mockup UI**: illustrazioni SVG del grafo (con animazione query-hit) e della tab Stats aggiunte al README.
- Tutti i file per umani (README, DESIGN, ROADMAP, AGENTS.md, skill) aggiornati per riflettere l'architettura corretta.

### v3.0.0 — 2026-05-24

**Cervello a tre layer + Promozione Autonoma + Deduplicazione Semantica + Auto-Riflessione**

- **Architettura a tre layer**: `wiki-works/<topic>/` contiene conoscenza profonda permanente per dominio. `wiki/` contiene conoscenza trasversale distillata, promossa autonomamente dall'agente. `wiki/identity/` contiene i pattern comportamentali appresi dalle correzioni. Tutti e tre i layer sono indicizzati insieme in LanceDB — un unico spazio vettoriale.
- **Promozione autonoma**: l'agente promuove pagine da `wiki-works/` a `wiki/` senza conferma dell'utente quando la conoscenza è trasversale (rilevante in ≥2 domini, recuperata in ≥3 query).
- **Deduplicazione semantica**: `lint --full` rileva duplicati semantici via cosine similarity. Similarity ≥ 0.90 → candidato auto-merge. 0.75–0.90 → warning. Configurabile via `thresholds.dedup_auto` e `thresholds.dedup_warn`.
- **Auto-riflessione autonoma**: `wiki.py behavior-log` logga correzioni comportamentali. `wiki.py self-reflect` aggiorna autonomamente `wiki/identity/` quando un pattern supera la soglia (`self_reflection.correction_threshold`, default 3). Nessuna approvazione umana richiesta.

### v2.3.0 — 2026-05-24

**Installazione guidata da agente**

- `AGENTS.md` — istruzioni di installazione e protocollo d'uso inline — nessun file patch separato necessario
- `scripts/setup_openclaw.py` — setup OpenClaw in un comando: rileva il config in 5 posizioni standard (Windows AppData, Linux XDG, home, locale), inietta l'entry del plugin atomicamente, idempotente
- `setup_openclaw.py` inietta automaticamente le istruzioni d'uso nel `AGENTS.md` del workspace dopo il setup — idempotente tramite sentinel `<!-- ai-wiki-system:usage-start -->`

**Miglioramenti lint**

- Supporto `exclude_from_index` in `cmd_lint`: le pagine che corrispondono ai pattern configurati vengono escluse dall'indicizzazione LanceDB; i pattern usano `fnmatch` (esplicito, non glob ricorsivo)
- Rilevamento filename duplicati in `cmd_lint --full`: avvisa quando due pagine condividono lo stesso basename in directory diverse
- `wiki_context.py`: legge `chunk_text` direttamente da LanceDB invece di rileggere i file ad ogni query — elimina I/O disco ridondante

**Test:** 92 test, tutti green (invariato)

---

### v2.2.0 — 2026-05-23

**Novità: Dashboard Osservabilità** (tab Stats)

- `GET /api/stats` — restituisce KPI: pagine totali, embedded, stale (≥7 gg), non indicizzate, top-10 pagine più interrogate, stato lint e schedule auto-lint
- `POST /api/lint` — avvia `wiki.py lint` in un subprocess; risponde 409 se un lint è già in corso
- Scheduler auto-lint asyncio: legge `frontend.lint_interval_hours` da `config.yaml`; esegue lint in background automaticamente; espone `next_run_iso` in `/api/stats`
- `cmd_lint` scrive `.wiki-lint-status.json` atomicamente (tmp → rename) dopo ogni run, registrando `timestamp`, `warnings`, `errors`, `exit_code`
- Tab `[Stats]` nel frontend: 4 KPI card (Pages, Embedded, Stale, Unembedded), lista top-queried (max 10), pulsante trigger lint con feedback 409

**Test:** 10 nuovi test — **92 totali, tutti green**

---

### v2.1.0 — 2026-05-22

**Novità: Interfaccia web** (`wiki.py serve`)

- `scripts/wiki_graph.py` — costruisce nodi + archi da filesystem e LanceDB; cache 30 secondi con dirty flag; `get_page_detail()` con protezione path traversal
- `scripts/wiki_server.py` — FastAPI: `/api/graph`, `/api/page/{path}`, WebSocket `/ws`, auth JWT cookie; file watcher asincrono (watchfiles) e tail watcher del query-log
- `frontend/index.html` — SPA zero-build: grafo D3.js force-directed, pannello pagina con markdown renderizzato (sanitizzato con DOMPurify), aggiornamenti live con posizioni nodi preservate, animazione pulse query-hit
- Nuovo comando CLI: `wiki.py serve --workspace <path> [--host] [--port 7331] [--no-auth]`
- `wiki.py query` ora appende a `.wiki-query-log.jsonl` — letto dal server per animare i nodi in tempo reale

**Fix robustezza (post-review)**
- `_query_log_watcher`: `pos = f.tell()` elimina race condition che causava query-hit mancati silenziosi
- Chiave firma JWT derivata via HMAC dalla password — mai la stringa grezza
- `httponly=True` sul cookie di sessione — riduce surface XSS
- `sys.path.insert` spostato a livello modulo in `wiki_server.py`
- `fetchGraph()` preserva `x/y/vx/vy` sui nodi esistenti — nessuno snap di posizione su aggiornamenti live

**Test:** 26 nuovi test (22 frontend + 2 path traversal + 2 WebSocket) — **82 totali, tutti green**

---

### v2.0 — 2026-05-22

**Novità: Ingestion PDF multi-sorgente**
- `scripts/wiki_pdf_watcher.py` — rilevamento modifiche SHA-256, estrazione pdfplumber, registro atomico, crash recovery tramite stato `pending`
- Nuovi CLI: `scan-inbox` e `ingest-pdf --file <path|url>` (limite 50 MB, sanitizzazione path)
- `pdf-inbox/` punto di convergenza — Telegram, CLI, URL e drop manuali unificati
- Nessun nuovo plugin OpenClaw per allegati Telegram
- `partial-failure` aggiunto come status valido in session-update

**Fix robustezza (revisione pre-release)**
- `cmd_ingest`: strip `.tmp` solo come suffisso; `sys.exit(1)` su lock failure
- `cmd_ingest_pdf`: limite 50 MB; protezione path traversal su filename
- `cmd_session_update`: errore strutturato su JSON `--detail` malformato
- Lista `deposited` ora contiene path relativi completi, non basename

**Test:** 21 nuovi unit test per `wiki_pdf_watcher` — 56 totali, tutti green

---

### v1.1.1 — 2026-05-21

**Bug fix — core Python**
- **[CRITICO]** `wiki_lancedb.py`: `table_names()` deprecato — corretto a `.list_tables().tables`
- **[ALTO]** `wiki_workflows.py` `cmd_ingest`: fallimento `shutil.move` a metà loop lasciava file senza vettori — tracciati e ripristinati su eccezione
- **[MEDIO]** `cmd_lint`: rilevamento rename limitato a `wiki/` e `wiki-works/`

**Bug fix — plugin OpenClaw**
- **[CRITICO]** `src/index.ts`: `api.getConfig()` non esiste — corretto a `api.config`
- **[ALTO]** Output build copiato alla root del plugin per risoluzione corretta da OpenClaw

---

### v1.1.0 — 2026-05-21

**Novità:** `scripts/wiki_context.py` — iniezione contesto pre-prompt. Esegue ricerca vettoriale prima di ogni messaggio e aggiunge `<wiki-context>`. Elimina l'instruction drift come failure mode.

**Bug fix**
- **[CRITICO]** `wiki_index.py`: `rebuild_index()` crashava con `NameError` ad ogni chiamata — `wiki_dir` aggiunto come parametro esplicito
- **[MEDIO]** `cmd_index`: `FileNotFoundError` su workspace vuoti — risolto con `os.makedirs`

---

## Licenza

AGPL-3.0 — chiunque distribuisca o esegua il software come servizio deve condividere il codice sorgente.

---

<div align="center">

Funziona con [OpenClaw](https://github.com/openclaw/openclaw) · Embedding da [BAAI/bge-m3](https://huggingface.co/BAAI/bge-m3) · Vector store da [LanceDB](https://lancedb.github.io/lancedb/)

</div>
