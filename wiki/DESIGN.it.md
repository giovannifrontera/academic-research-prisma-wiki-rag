# 🧠 AI Longterm Wiki Memory — Design Document v2

> Basato sul pattern di Andrej Karpathy (llm-wiki), adattato per CLI Linux, autonomo,
> con topologia semantica a embedding vettoriali bge-m3 e LanceDB.
> 2026-05-19.

---

## 📐 Architettura Generale

```
workspace/
├── wiki/                           ← Livello 1: Conoscenza Permanente
│   ├── .schema.md                  ← Convenzioni, regole, standard di questo wiki
│   ├── log.md                      ← Cronologia append-only
│   ├── entities/
│   ├── concepts/
│   └── synthesis/
│
├── wiki-works/                     ← Livello 2: Ricerche Attive
│   ├── log.md                      ← Cronologia globale ricerche
│   ├── trading/
│   │   ├── .schema.md
│   │   ├── log.md
│   │   ├── raw/                    ← Fonti grezze (escluse dai vettori — vedi §raw)
│   │   ├── entities/
│   │   ├── concepts/
│   │   └── synthesis/
│   └── .../
│
└── memory/
    └── lancedb/                    ← Escluso da git (ricostruibile — vedi §git)
```

**Nota su index.md**: Non esiste come file mantenuto a mano.
`index.md` è generato on-demand da filesystem scan (vedi §index-generation).
Questo elimina la classe intera di bug "index out of sync".

---

## 🗂️ Tre Strati di Conoscenza

| Strato | Descrizione | Natura |
|--------|-------------|--------|
| **Memoria Vettoriale** (LanceDB) | Retrieval semantico automatico — tutti i layer indicizzati insieme | Implicita, ricostruibile |
| **wiki-works/\<topic\>/** | Conoscenza di dominio profonda: concetti, ricerche, entità per argomento | Esplicita, permanente |
| **wiki/** | Conoscenza distillata trasversale: promossa autonomamente quando rilevante in più domini | Esplicita, permanente |
| **wiki/identity/** | Identità agente: valori, stile, pattern comportamentali appresi (solo self-reflect) | Esplicita, permanente |

---

## 🚀 Bootstrap e Inizializzazione

Prima sessione in un nuovo wiki:

```
1. Crea directory: wiki/ (o wiki-works/<progetto>/)
2. Crea .schema.md con regole del wiki specifico
3. Crea log.md vuoto con header:
   # Log — <nome wiki>
   <!-- formato: ## [YYYY-MM-DD] tipo | descrizione -->
4. LanceDB: crea tabella wiki_pages con schema §vettori se non esiste
5. Esegui rebuild-index per generare index.md iniziale (sarà vuoto/minimo)
6. Log entry: ## [DATA] init | Bootstrap wiki <nome>
```

Per `wiki/` principale, seed opzionale: crea `entities/Agent-nyx.md` e
`entities/gio.md` come pagine fondamentali prima di ogni ingest.

---

## 🔄 I 3 Workflow

### 1. INGEST — Acquisizione con atomicità

L'utente dice il **cosa**. Agent fa il **come**, in modo atomico e verificabile.

#### Fase A — Ricerca e Filtro (leggi-only, nessuna scrittura)

1. `web_search` per trovare 5–10 fonti candidate
2. **Filtro qualità** (vedi §quality-filter): scarta fonti sotto soglia
3. `web_fetch` sulle fonti promosse → salva in `raw/` con nome `YYYY-MM-DD-slug.md`
4. Leggi fonti, estrai punti chiave, identifica contraddizioni con wiki esistente

#### Fase B — Scrittura atomica

Staging: tutte le scritture avvengono su file `.tmp` prima di essere committate.

```
STAGING ATOMICO:
a) Scrivi nuove/aggiornate pagine in <path>.tmp
b) Scrivi nuovi embedding in tabella staging_wiki_pages di LanceDB
c) CHECKPOINT: verifica integrità (ogni .tmp leggibile, ogni embedding presente)
d) Se CHECKPOINT ok:
   - Rinomina tutti i .tmp → definitivi (operazione atomica per file)
   - Promuovi staging_wiki_pages → wiki_pages (upsert per path)
   - Rigenera index.md via rebuild-index
   - Append log.md
   - Esegui MINI-LINT (vedi §mini-lint)
e) Se CHECKPOINT fallisce:
   - Cancella tutti i .tmp
   - Cancella staging_wiki_pages
   - Log entry: ## [DATA] ingest-failed | <motivo>
   - Notifica l'utente con errore specifico
```

#### Fase C — Report

- Riassunto orale in chat: fonte, punti chiave, conflitti trovati e risolti
- Domande di validazione se necessario

---

### 2. QUERY — Risposta con compounding

1. Chiama `rebuild-index` (se index.md è assente o stale vs filesystem)
2. Leggi index.md → identifica pagine rilevanti per categoria
3. Query vettoriale su LanceDB per connessioni semantiche non ovvie
4. Leggi pagine selezionate → sintetizza risposta con riferimenti `[pagina](path)`
5. **Valuta soglia synthesis** (vedi §synthesis-threshold): se la sintesi supera la soglia → salvala come nuova pagina nel workflow INGEST (compounding)
6. Nessuna scrittura diretta fuori dal workflow INGEST — mantiene atomicità

---

### 3. LINT — Manutenzione (completo)

**Quando**: su richiesta dell'utente, o proattivamente ogni 2 settimane.
**Mini-lint automatico**: dopo ogni INGEST (sottoinsieme leggero — vedi §mini-lint).

```
LINT CHECKLIST COMPLETO:
□ DESYNC: rebuild-index → confronta con index.md su disco → diff
□ VETTORI STALE: per ogni file .md non-raw → SHA256(contenuto) ≠ content_hash in LanceDB?
□ PAGINE NON EMBEDDED: file .md in wiki senza entry in wiki_pages
□ ENTRY ORFANE: entry in wiki_pages con path che non esiste su filesystem
□ BROKEN LINKS: grep [[wikilink]] → verifica esiste il file target
□ DUPLICATI: per ogni coppia di pagine con cosine_similarity > 0.95 → segnala e proponi merge
□ ORFANI SEMANTICI: pagine con nessun vicino con similarity > 0.50 → segnala
□ CHUNK STALE: per ogni pagina chunked → hash chunk ≠ hash attuale → rechunka
□ STALENESS: pagine con last_modified > 90 giorni → segnala per revisione
□ GAP: concetti citati in ≥3 pagine senza pagina dedicata → segnala
□ LOG INTEGRITÀ: ogni entry log ha timestamp e tipo valido
```

Per ogni problema trovato, LINT non solo segnala — **risolve**:

| Problema | Azione automatica |
|---------|-------------------|
| Vettore stale | Re-embedda immediatamente |
| Pagina non embedded | Embedda |
| Entry LanceDB orfana | Cancella entry |
| Broken link | Segnala in log, propone fix all'utente |
| Duplicati (similarity > 0.95) | Propone merge con draft della pagina unificata |
| Orfani semantici | Aggiunge sezione "Vedi anche" con 3 vicini più prossimi |
| Chunk stale | Rechunka e re-embedda |

---

## 🔬 §mini-lint — Mini-Lint Automatico Post-Ingest

Eseguito automaticamente al termine di ogni INGEST riuscito. Leggero, < 30s.

```
MINI-LINT (sottoinsieme fast):
□ Le pagine appena scritte esistono su filesystem?
□ Le pagine appena scritte hanno entry in wiki_pages con hash corretto?
□ index.md è stato rigenerato (mtime > mtime delle pagine scritte)?
□ Log entry è presente?
□ Nessun .tmp rimasto su disco?
```

Se mini-lint fallisce → log entry `## [DATA] mini-lint-failed | <dettaglio>` e notifica l'utente.
Non fa rollback (l'ingest è già committato) ma marca lo stato come "da riparare".

---

## 🏷️ §synthesis-threshold — Criteri per Creare una Pagina Synthesis

Una risposta a una QUERY diventa pagina wiki se soddisfa **tutti** i criteri obbligatori
e almeno uno dei criteri opzionali:

**Criteri obbligatori:**
- Sintetizza ≥ 2 fonti distinte (pagine o raw diversi)
- Lunghezza ≥ 300 token (non banale)
- Aggiunge inferenza che non sta letteralmente in nessuna fonte singola

**Criteri opzionali (≥ 1):**
- Risponde a una domanda che l'utente ha posto esplicitamente
- Risolve una contraddizione tra pagine esistenti
- Connette concetti di domini diversi (cross-wiki)
- È probabile che venga riusata in future query (giudizio di Agent)

**Contro-indicatori (escludono automaticamente):**
- È un riassunto di una singola fonte (va in raw/, non synthesis/)
- Duplica una pagina esistente con similarity > 0.85
- Contiene affermazioni non verificate senza fonte esplicita

---

## 📦 §chunking — Strategia Chunking per Pagine Lunghe

Soglia: pagine > **1500 token** vengono chunked prima dell'embedding.

**Strategia di chunking:**
- Chunk size: 512 token con overlap 64 token
- Boundary-aware: i chunk non tagliano nel mezzo di una sezione markdown
  (rispetta le intestazioni `##` e `###`)
- Ogni chunk eredita i metadati della pagina madre

**Schema LanceDB per pagine chunked:**

```
wiki_pages:
├── path: string          ← path file (es. "wiki/concepts/strategie.md")
├── chunk_id: int         ← 0 per pagine non-chunked, 1..N per chunk
├── chunk_text: string    ← testo del chunk (non dell'intera pagina)
├── content_hash: string  ← SHA256(chunk_text) — hash del TESTO, non del path
├── page_hash: string     ← SHA256(intera pagina) — per rilevare se rechunkare
├── vector: float[1024]
└── last_embedded: float
```

**Recupero**: quando una query matcha un chunk, recupera la pagina intera per contesto.
Nei risultati, mostra sempre il path della pagina, non del chunk.

**Re-chunking**: se `page_hash` ≠ SHA256(file attuale) → rechunka tutto e re-embedda tutti i chunk.

---

## 🔐 §hash-semantics — Semantica Corretta degli Hash

**Regola fondamentale**: `content_hash = SHA256(testo_del_chunk_o_pagina)`.
Il path NON è incluso nell'hash. Path e hash sono campi separati e indipendenti.

Questo implica:

| Evento | Hash cambia? | Path cambia? | Azione |
|--------|-------------|-------------|--------|
| Edito il testo | Sì | No | Re-embedda, aggiorna entry esistente |
| Rinomino il file | No | Sì | Cerca entry col vecchio path → aggiorna path, nessun re-embedding |
| Sposto tra cartelle | No | Sì | Come rinomina |
| Git checkout stesso contenuto | No | No | Nessuna azione (hash matcha) |
| Cancello il file | — | — | LINT trova entry orfana → la cancella |

**Rilevamento rename**: LINT confronta `set(path in LanceDB)` con `set(file su filesystem)`.
Path solo in LanceDB → orfano. Path solo su filesystem → nuovo file.
Se un orfano e un nuovo file hanno lo stesso `content_hash` → è un rename → aggiorna path.
Se hash diversi → orfano cancellato, nuovo file embeddato separatamente.

---

## 📂 §raw — Trattamento delle Fonti Grezze

Le directory `raw/` contengono fonti scaricate via `web_fetch`. Sono escluse dai vettori.

**Razionale**: raw/ è materiale di input non elaborato. Includerlo nei vettori inquina il
retrieval semantico con duplicati e rumore. Il valore di raw/ è nell'accesso diretto
durante l'ingest, non nel retrieval semantico.

**Regola**: Nessun file in `raw/` ha entry in `wiki_pages`.
Il LINT verifica questa invariante: se trova entry con path contenente `/raw/` → le cancella.

**Naming convention raw**: `raw/YYYY-MM-DD-slug-fonte.md`

**Accesso**: durante l'ingest Agent legge raw/ direttamente con `read`.
Durante le QUERY, raw/ non è indicizzato né cercato semanticamente.

---

## 🔁 §index-generation — Index Generato da Filesystem

`index.md` è un file **derivato**, non una sorgente di verità. È generato da:

```
rebuild-index(wiki_dir):
  pagine = glob(wiki_dir + "/**/*.md") - escludi .schema.md, log.md, raw/**
  raggruppa per subdirectory (entities/, concepts/, synthesis/)
  per ogni pagina:
    - leggi YAML frontmatter se presente (title, description)
    - fallback: usa il filename come title, prima riga non-heading come description
  scrivi index.md con struttura:
    # Index — <nome wiki>
    _Generato: YYYY-MM-DD HH:MM — <N> pagine_
    ## Entities
    - [[slug]] — descrizione
    ## Concepts
    - [[slug]] — descrizione
    ## Synthesis
    - [[slug]] — descrizione
  se index.md supera TOKEN_BUDGET → vedi §token-budget
```

**Quando chiamare rebuild-index**:
- Fine di ogni INGEST riuscito (già nel workflow atomico)
- Inizio di ogni QUERY (controllo mtime: se index.md più vecchio di qualsiasi .md → rigenera)
- Durante LINT completo

**Mai**: non aggiornare index.md a mano riga per riga. Sempre rebuild completo.

---

## 💰 §token-budget — Token Budget per index.md

Limite massimo: **4000 token** per index.md (compatibile con context window di DeepSeek V4).

Se il wiki supera questa soglia durante rebuild-index:

```
Strategia di riduzione (in ordine):
1. Rimuovi la colonna "descrizione" → solo link: - [[slug]]
   (risparmio ~50%)
2. Se ancora > 4000 token: genera un indice per categoria separato
   index.md → solo lista categorie con conteggio pagine
   index-entities.md, index-concepts.md, index-synthesis.md → indici parziali
3. Se una singola categoria > 4000 token (wiki enorme):
   index-concepts-A-M.md, index-concepts-N-Z.md (split alfabetico)
```

Soglia di warning in `.schema.md`: `index_token_budget: 4000`.
Configurabile per wiki (wiki-works piccoli possono usare budget maggiore).

---

## 🎯 §quality-filter — Criteri di Qualità per le Fonti

Prima del `web_fetch`, ogni fonte candidata è valutata. Promozione solo se supera la soglia.

**Criteri di esclusione automatica (qualsiasi → scarta):**
- Dominio in blacklist: SEO farm, aggregatori di bassa qualità, wiki spam
- Paywall senza abstract (web_fetch ritorna < 200 token di contenuto)
- Contenuto prevalentemente pubblicitario (> 30% markup commerciale)
- Data non rilevabile e contenuto chiaramente datato (es. prezzi, statistiche senza anno)

**Score di qualità (0–10, soglia minima: 6):**

| Criterio | Punti |
|---------|-------|
| Autore identificabile con credenziali verificabili | +2 |
| Fonte primaria (paper, documentazione ufficiale, dati grezzi) | +3 |
| Fonte secondaria autorevole (rivista peer-reviewed, istituzione) | +2 |
| Data pubblicazione ≤ 2 anni (per topic time-sensitive) | +1 |
| Citazioni/riferimenti presenti | +1 |
| Concordanza con fonti già nel wiki | +1 |
| Discordanza con fonti nel wiki (valore informativo) | +1 |

**Score massimo**: 11 (capped a 10). Soglia 6 per promozione.
Per topic storici o fondamentali (matematica, fisica, storia), il criterio data è ignorato.

Documenta il processo di filtro nel log:
```
## [DATA] ingest | Titolo
Fonti candidate: 7 | Promosse: 3 | Scartate: 4
Scartate: [dominio-spam.com (SEO farm), altro.com (paywall), ...]
```

---

## ⚔️ §conflict-resolution — Risoluzione Conflitti (non solo segnalazione)

Quando l'ingest trova un'affermazione P in una nuova fonte che contraddice
l'affermazione ¬P in una pagina esistente:

**Livelli di conflitto e risoluzione:**

**Livello 1 — Conflitto datato** (una fonte è più recente):
- Azione: aggiorna la pagina wiki con l'informazione più recente
- Mantieni nota: `> ⚠️ Aggiornato: [vecchia affermazione] → [nuova]. Fonte: [link]. Data: YYYY-MM-DD`
- Nessun intervento dell'utente necessario

**Livello 2 — Conflitto di interpretazione** (entrambe le fonti sono valide ma in disaccordo):
- Azione: crea sezione `## Prospettive in conflitto` nella pagina
- Presenta entrambe le posizioni con fonte e score qualità
- Aggiungi alla pagina il tag frontmatter `status: contested`
- Nessun intervento dell'utente necessario

**Livello 3 — Conflitto fondamentale** (impossibile riconciliare, impatto alto):
- Azione: crea synthesis page dedicata `conflicts/titolo-conflitto.md`
- Riassumi entrambe le posizioni, analizza le implicazioni
- Segnala all'utente nel report finale con domanda specifica: "Quale versione consideri canonica?"
- Blocca il merge della nuova affermazione nelle pagine di riferimento fino a risposta

**Rilevamento**: durante l'ingest, dopo aver letto la nuova fonte e prima di scrivere,
Agent cerca le 5 pagine più simili vettorialmente + grep per entità/concetti chiave.
Per ogni pagina trovata, confronta le affermazioni chiave. Classifica il livello di conflitto.

---

## 🧭 Tre Sistemi di Navigazione

### A. Index generato (index.md)
Navigazione per categoria. Generato da filesystem (§index-generation).

### B. Link espliciti (markdown [[wikilink]])
Backlink trovabili con `grep -rl "nome-pagina" wiki/`.

### C. Topologia semantica (vettori)
Embedding bge-m3 (1024-dim), chunk-aware, per ogni pagina non-raw.

- **Vicinato**: query `search(embedding, k=5, filter="chunk_id=0")` su LanceDB
- **Cluster**: ricalcolato durante LINT completo (k-means su tutti i vettori chunk_id=0)
- **Ponti**: pagine con vicini in cluster diversi
- **Orfani semantici**: pagine senza vicini con similarity > 0.50

```
Pagina: strategie-mean-reversion.md
├── 0.92 → backtesting-fondamenti.md
├── 0.87 → indicatori-tecnici.md
├── 0.81 → gestione-rischio.md
└── 0.74 → psicologia-trading.md
```

Nessun PNG, nessuna graph view. Solo distanze testuali on-demand.

---

## 🛠️ Stack Tecnologico

| Componente | Tool | Note |
|-----------|------|------|
| File system | Directory markdown | Già esistente |
| Index | Generato da filesystem | Mai mantenuto a mano |
| Log | `log.md` append-only | Formato parseabile |
| Link espliciti | `[[wikilink]]` + `grep` | Backlink con `grep -rl` |
| Embedding | bge-m3 (già installato) | 1024-dim, chunk-aware |
| DB vettoriale | LanceDB (già installato) | Tabella `wiki_pages` |
| Search testuale | `grep` | Fallback per link e testo |
| Ricerca web | `web_search` | Autonomo |
| Fetch pagine | `web_fetch` | Markdown pulito → raw/ |
| Versionamento | `git` | Esclude lancedb/ (§git) |

---

## 📋 File Speciali

### .schema.md
Definisce per ogni wiki:
- Struttura cartelle attiva
- Formato YAML frontmatter richiesto
- Soglie lint (es. `staleness_days: 90`, `similarity_merge_threshold: 0.95`)
- `index_token_budget: 4000`
- Stile link e naming convention

### log.md
- Append-only, mai editato retroattivamente
- Formato: `## [YYYY-MM-DD] tipo | descrizione`
- Tipi: `init`, `ingest`, `ingest-failed`, `query`, `lint`, `mini-lint-failed`, `sync`, `archive`, `conflict-resolved`
- Query rapida: `grep "^\#\# \[" log.md | tail -10`

---

## 🔁 Flusso di Vita di un Progetto (Livello 2)

```
  ATTIVO → DORMIENTE → ARCHIVIATO
```

- **Attivo**: riceve ingest e query
- **Dormiente**: non si tocca, accessibile in lettura
- **Archiviato**: `wiki-works/.archive/nome-progetto/` — LanceDB entries cancellate

**Nota (v3):** La promozione da wiki-works/ a wiki/ è autonoma — l'agente promuove quando la conoscenza è trasversale (rilevante in ≥2 domini, recuperata in ≥3 query). `wiki/identity/` è aggiornato solo tramite `wiki.py self-reflect`.

---

## 🗄️ §git — Strategia Git / LanceDB

**LanceDB è esclusa da git.**

```
# .gitignore (aggiungi):
memory/lancedb/
```

**Razionale**: LanceDB è interamente ricostruibile dal filesystem markdown.
Non contiene informazione che non sia derivabile dalle pagine. Committarla
causerebbe commit enormi, conflitti binari irrisolvibili, e falsa sicurezza.

**Procedura di ricostruzione**:
```
rebuild-lancedb(wiki_dir):
  cancella tabella wiki_pages
  per ogni .md non in raw/ e non in .archive/:
    chunka se > 1500 token (§chunking)
    per ogni chunk: embedda con bge-m3, inserisci in wiki_pages
  log entry: ## [DATA] sync | LanceDB ricostruito da filesystem
```

**Quando ricostruire**: dopo `git clone`, `git reset --hard`, o se LanceDB è corrotta.
Tempo stimato: ~2 min per 1000 pagine su hardware standard.

**Git traccia**: tutti i file `.md`, `.schema.md`, `log.md`. Non traccia: `lancedb/`, `*.tmp`.

---

## 🔑 §lancedb-schema — Schema Completo LanceDB

```
Tabella: wiki_pages
├── path         string       ← path relativo da workspace root
├── chunk_id     int          ← 0 = pagina intera (< 1500 tok); 1..N = chunk
├── chunk_text   string       ← testo embeddato (chunk o intera pagina)
├── content_hash string       ← SHA256(chunk_text) — solo testo, mai path
├── page_hash    string       ← SHA256(intera pagina) — per rilevare rechunk
├── vector       float[1024]  ← bge-m3 embedding di chunk_text
└── last_embedded float       ← unix timestamp

Tabella: staging_wiki_pages  ← identico schema, usata per ingest atomico
                                cancellata/svuotata dopo ogni ingest (ok o failed)

Index: (path, chunk_id) UNIQUE
Index: vector ANN (HNSW)
```

---

## 🚦 Regole di Implementazione

1. **Non si tocca il sistema esistente** (LanceDB memorie, daily notes, MEMORY.md)
2. Il wiki si **aggiunge** alla memoria, non la sostituisce
3. `index.md` è sempre generato, mai scritto a mano
4. Ogni write passa per staging atomico — nessuna pagina parziale su disco
5. Mini-lint dopo ogni ingest — sempre
6. LanceDB fuori da git — sempre ricostruibile
7. `raw/` non nei vettori — invariante verificata dal lint
8. Conflitti risolti (non solo segnalati) secondo §conflict-resolution
9. Nessuna dipendenza nuova da installare

---

*v2 — 2026-05-19 — Revisionato da Claude Code*
