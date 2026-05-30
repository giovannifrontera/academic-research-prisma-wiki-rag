# Wiki Frontend Design — ai-longterm-wiki-memory

**Date:** 2026-05-22
**Status:** Approved
**Scope:** Read-only web frontend per navigare il wiki generato dall'AI, con mappa grafo interattiva, pannello pagina, aggiornamenti automatici e animazione query hit.

---

## Problema

Il wiki cresce silenziosamente in directory markdown. Non esiste una vista navigabile che mostri le connessioni tra pagine, l'evoluzione della conoscenza nel tempo, o quali nodi sono stati interrogati dall'agente. L'unica navigazione disponibile è il filesystem.

---

## Vincolo fondamentale

**Il frontend non modifica mai il wiki.** È un osservatore puro: legge markdown, legge LanceDB, osserva file e log. I workflow INGEST/QUERY/LINT/SCAN-INBOX continuano a funzionare identicamente con o senza il server in esecuzione.

---

## Architettura

```
wiki.py serve --workspace <path> [--host 0.0.0.0] [--port 7331] [--no-auth]
       │
       ▼
scripts/wiki_server.py          ← FastAPI + WebSocket + file watcher + auth
scripts/wiki_graph.py           ← costruisce nodi + archi (sola lettura)
frontend/index.html             ← SPA: D3.js + Marked.js + WebSocket client
```

**Flusso dati:**

```
wiki/ e wiki-works/  ──── watchfiles ──────► WebSocket "graph_update" → browser ri-renderizza
LanceDB              ──── query similarity ──► wiki_graph.py → /api/graph
.wiki-query-log.jsonl ─── tail watcher ─────► WebSocket "query_hit" → nodo si illumina
```

---

## Componenti

### `scripts/wiki_graph.py`

Costruisce il grafo a partire dal filesystem e da LanceDB. Nessuna scrittura.

**Nodi** — uno per ogni file `.md` in `wiki/` e `wiki-works/` (esclusi `raw/`, `.archive/`, `index.md`, `log.md`):
```json
{
  "id": "wiki/concepts/rag",
  "path": "wiki/concepts/rag.md",
  "title": "RAG",
  "category": "concepts",
  "project": "wiki",
  "description": "Retrieval-augmented generation...",
  "last_modified": "2026-05-22T10:30:00"
}
```

**Archi espliciti** — regex `\[\[([^\]]+)\]\]` su ogni pagina:
```json
{ "source": "wiki/concepts/rag", "target": "wiki/concepts/embedding", "type": "link" }
```
Target mancante nel filesystem → arco ignorato silenziosamente.

**Archi semantici** — per ogni pagina, query LanceDB con il vettore medio dei suoi chunk; top-5 vicini con distanza coseno < 0.35 (similarità > 0.65); self-loop esclusi; archi duplicati deduplicati (A→B = B→A):
```json
{ "source": "wiki/concepts/rag", "target": "wiki/concepts/transformer",
  "type": "semantic", "weight": 0.82 }
```

**Cache:** il grafo è ricalcolato al massimo ogni 30 secondi. Un flag `dirty` viene alzato dal file watcher per forzare il ricalcolo alla prossima richiesta.

**Funzioni pubbliche:**
```python
build_graph(workspace: str, cfg: dict) -> dict          # {"nodes": [...], "edges": [...]}
get_page_detail(workspace: str, path: str, cfg: dict) -> dict
    # {"content": str, "metadata": dict, "similar": [...], "links_out": [...], "links_in": [...]}
```

---

### `scripts/wiki_server.py`

FastAPI app con quattro responsabilità: API REST, WebSocket, file watcher, autenticazione.

**Endpoints REST:**

| Method | Path | Risposta |
|--------|------|----------|
| `GET` | `/` | Serve `frontend/index.html` |
| `GET` | `/api/graph` | `{"nodes": [...], "edges": [...]}` |
| `GET` | `/api/page/{path:path}` | Dettaglio pagina (markdown + metadata + similar + links) |
| `POST` | `/auth/login` | Body: `{"password": "..."}` → setta cookie sessione |
| `POST` | `/auth/logout` | Cancella cookie |

**WebSocket:** `WS /ws`

Messaggi server → client:
```json
{ "type": "graph_update" }
{ "type": "query_hit", "paths": ["wiki/concepts/rag.md", "wiki/entities/openai.md"] }
```

Il client su `graph_update` refetcha `/api/graph` e aggiorna D3.
Il client su `query_hit` anima i nodi corrispondenti per 4 secondi.

**File watcher** (`watchfiles`): osserva `wiki/` e `wiki-works/` in un thread separato. Ogni modifica alza il flag `dirty` sul grafo e manda `graph_update` a tutti i client WebSocket connessi.

**Query log watcher**: thread separato che legge `.wiki-query-log.jsonl` dall'ultima posizione nota. Ogni nuova riga `{"ts": "...", "q": "...", "paths": [...]}` viene broadcast come `query_hit`.

**Autenticazione:** middleware JWT su tutte le route. Cookie `wiki_session` firmato con `python-jose`. Scadenza configurabile (default 7 giorni). Route `/auth/login` è l'unica non protetta.

**Avvio:**
```python
# Da wiki.py:
uvicorn.run("wiki_server:app", host=host, port=port, reload=False)
```

---

### `frontend/index.html`

Single-page app, nessun build step. Librerie da CDN:
- `D3.js v7` — grafo force-directed
- `Marked.js` — rendering markdown
- Nessuna altra dipendenza

**Layout:**
```
┌─────────────────────────────────────────────────────────┐
│  AI Wiki Memory  [wiki] [ricerca] [trading] [tutti]  🔍 │  ← header
├───────────────────────────┬─────────────────────────────┤
│                           │  PANNELLO PAGINA            │
│    MAPPA GRAFO            │  ─────────────────          │
│    (D3 force-directed)    │  # Titolo                   │
│                           │  categoria · data           │
│                           │  ─────────────────          │
│                           │  [markdown renderizzato]    │
│                           │                             │
│                           │  ── Link uscenti ──         │
│                           │  ── Link entranti ──        │
│                           │  ── Pagine simili ──        │
│                           │     slug (0.87)             │
└───────────────────────────┴─────────────────────────────┘
```

**Nodi:**
- Colore per categoria: entities=`#4A90D9` (blu), concepts=`#5CB85C` (verde), synthesis=`#9B59B6` (viola), raw=`#AAAAAA` (grigio)
- Dimensione proporzionale al numero di connessioni (grado del nodo)
- Label con il titolo della pagina
- Hover: tooltip con descrizione

**Archi:**
- Link espliciti: linea solida, opacità 0.6
- Similarità semantica: linea tratteggiata, opacità proporzionale al peso (0.65–1.0 → 0.2–0.5)

**Interattività:**
- Click nodo → apre pannello laterale (fetch `/api/page/{path}`)
- Doppio click nodo → centra e zooma sul nodo
- Drag nodi → riposizionamento manuale
- Scroll → zoom
- Filtro progetto (tab header) → mostra solo nodi del progetto selezionato, archi tra progetti visibili ma attenuati
- Cerca (input header) → highlight nodi matching per titolo/descrizione

**Animazione query hit:**
1. Nodo riceve classe CSS `query-hit`
2. CSS keyframe: glow giallo-arancio (`box-shadow` / SVG `filter: drop-shadow`) pulsante per 4 secondi
3. Forza D3 temporanea: attrazione verso il centro (alpha bump) per 1 secondo
4. Transizione fluida di ritorno allo stato normale

**Aggiornamento grafo automatico:**
Su `graph_update` WebSocket → refetch `/api/graph` → D3 `join()` con transizione `duration(600ms)` per nodi e archi nuovi/rimossi.

**Login:**
Se assente il cookie `wiki_session`, mostra form centrato con campo password e pulsante. POST a `/auth/login`. Su successo, reload della pagina principale. Stile minimalista coerente con il tema.

---

## Modifica a `wiki.py` (minima)

**Subcommand `serve`:**
```python
p_serve = sub.add_parser("serve")
p_serve.add_argument("--workspace", required=True)
p_serve.add_argument("--host", default="127.0.0.1")
p_serve.add_argument("--port", type=int, default=7331)
p_serve.add_argument("--no-auth", action="store_true")
```

**`cmd_query` — append al log:**
```python
log_path = Path(workspace) / ".wiki-query-log.jsonl"
entry = {"ts": datetime.now().isoformat(), "q": args.q, "paths": [r["path"] for r in results]}
with open(log_path, "a", encoding="utf-8") as f:
    f.write(json.dumps(entry) + "\n")
```
Effetto: nessuno se il server non gira. Stdout invariato. `wiki-session.md` invariato.

---

## Configurazione

Campo opzionale in `wiki.config.json`:
```json
{
  "frontend": {
    "password": "la-tua-password",
    "session_days": 7
  }
}
```

Variabile d'ambiente `WIKI_PASSWORD` ha priorità sul config (utile su VPS senza esporre la password nel file).

---

## Deploy

**Locale (default):**
```bash
py scripts/wiki.py serve --workspace /path/to/workspace
# → http://localhost:7331
```

**Pubblico con ngrok:**
```bash
py scripts/wiki.py serve --workspace /path/to/workspace --host 0.0.0.0
ngrok http 7331
# → https://abc123.ngrok.io
```

**VPS permanente (Nginx + systemd):**
```nginx
location / {
    proxy_pass http://127.0.0.1:7331;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";  # necessario per WebSocket
}
```

---

## Dipendenze nuove

```
fastapi>=0.111.0
uvicorn[standard]>=0.29.0
watchfiles>=0.21.0
python-jose[cryptography]>=3.3.0
```

---

## File prodotti

```
scripts/
  wiki_server.py     ← ~220 righe
  wiki_graph.py      ← ~130 righe
frontend/
  index.html         ← ~520 righe
```

Modifiche a file esistenti:
- `scripts/wiki.py`: +subcommand `serve`, +5 righe in `cmd_query`
- `requirements.txt`: +4 dipendenze
- `wiki.config.json`: +campo `frontend` (opzionale)

---

## Testing

| Test | Cosa verifica |
|------|---------------|
| `test_build_graph_nodes` | Nodi corretti da filesystem mock |
| `test_build_graph_explicit_links` | Archi da `[[slug]]` |
| `test_build_graph_semantic_edges` | Archi da LanceDB (mocked) |
| `test_missing_link_ignored` | Target `[[slug]]` inesistente → nessun arco |
| `test_query_log_written` | `cmd_query` scrive `.wiki-query-log.jsonl` |
| `test_api_graph_endpoint` | `/api/graph` restituisce JSON valido |
| `test_api_page_endpoint` | `/api/page/{path}` restituisce markdown |
| `test_auth_required` | Route protette senza cookie → 401 |
| `test_auth_login` | Password corretta → cookie sessione |
| `test_auth_wrong_password` | Password errata → 401 |
