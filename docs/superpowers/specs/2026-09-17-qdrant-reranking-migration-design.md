# Design: migrazione wiki da LanceDB a Qdrant + cross-encoder reranking

Data: 2026-09-17

## Contesto

Seconda fase annunciata in `2026-09-17-claude-plugin-conversion-design.md`
("Fuori scope (rimandato alla spec successiva)"): migrare `wiki/` (il layer
di memoria a lungo termine) da LanceDB a Qdrant e aggiungere reranking
cross-encoder come secondo stadio di ricerca.

## Perché Qdrant embedded, non un server esterno

Stessa esperienza zero-setup di LanceDB locale: `qdrant-client` supporta una
modalità locale (`QdrantClient(path=...)`) che persiste su disco senza
processo server separato. Nessun docker-compose, nessuna porta da aprire.

## Modulo nuovo: `wiki_qdrant.py`

Sostituisce `wiki_lancedb.py` (rimosso) con la stessa interfaccia pubblica:
`get_db`, `ensure_table`, `upsert`, `promote_staging`, `rollback_staging`,
`query_similar`, `find_semantic_duplicates`, `detect_renames`, più
`list_tables`/`drop_table`/`collection_exists`/`count_rows` per i chiamanti
che usavano l'API diretta di lancedb (`db.list_tables()`, `db.drop_table()`,
`db.open_table().count_rows()`).

`ensure_table()` ritorna un wrapper `_Collection` con `.to_pandas()` e
`.delete(filter_str)` — la porzione di API `lancedb.Table` effettivamente
usata dal resto del codebase — così i chiamanti (`wiki_workflows.py`,
`wiki_graph.py`) non cambiano logica, solo import e la chiave di config
`"lancedb"` → `"qdrant"`.

Punti id: Qdrant richiede id int o UUID, non stringhe libere come i `path`
LanceDB. Uso `uuid5(namespace, f"{collection}:{path}:{chunk_id}")` —
deterministico, così un upsert con lo stesso path/chunk_id sovrascrive lo
stesso punto invece di duplicarlo.

### Bug scoperto in corso d'opera: `delete_collection` su Windows

`promote_staging`/`rollback_staging` inizialmente facevano
drop+recreate della collection di staging (come l'originale LanceDB
drop_table). Su Windows, in modalità embedded locale, il file
`storage.sqlite` della collection a volte resta lockato e
`delete_collection` non lo rimuove dal disco; una `create_collection`
successiva con lo stesso nome riaggancia i dati vecchi invece di ripartire
vuota — scoperto da un test che falliva in modo riproducibile
(`test_promote_staging_moves_to_wiki`, `test_rollback_staging_clears_staging`).

Fix: invece di droppare la collection, la svuoto cancellando tutti i punti
con un filtro vuoto (`db.delete(name, points_selector=FilterSelector(filter=Filter()))`),
lasciando la collection (e il suo file su disco) intatta. Stesso pattern
usato anche da `drop_table()` per coerenza — evita la classe di bug
interamente invece di limitarla al solo staging.

### Secondo bug scoperto: crash pandas/pyarrow su Windows nella test suite completa

Eseguendo l'intera `pytest tests/` (non i singoli file), `_Collection.to_pandas()`
causava una access violation nativa dentro `pandas.core.arrays.string_arrow`
durante la costruzione dell'Index delle colonne — riproducibile solo dopo che
altri test avevano già importato `sentence-transformers`/`torch`/`sklearn`
nello stesso processo (conflitto tra i runtime nativi di questi pacchetti e
il backend stringhe pyarrow, default in pandas ≥ 3.0). Non riproducibile
eseguendo i singoli file di test in isolamento.
Fix: `pd.set_option("future.infer_string", False)` in `to_pandas()`, che
forza le colonne stringa a dtype `object` invece che pyarrow-backed — nessun
impatto funzionale (qui servono solo confronti/filtri su stringhe Python).

## Reranking cross-encoder: `wiki_rerank.py`

Nuovo modulo, una funzione `rerank(query, candidates, top_k, text_key,
model_name)`: rilegge query+candidato con `sentence-transformers.CrossEncoder`
e riordina. Modello di default `BAAI/bge-reranker-v2-m3` — stesso vendor
dell'embedder `BAAI/bge-m3` già in uso, coerenza multilingue IT/EN.

Punto di integrazione: `wiki_server.py` → `/api/context` (l'hot path usato
dal plugin per il pre-prompt injection). Prima: `table.search(vector).limit(k*4)`
diretto su LanceDB, poi dedup per path e troncamento a `k` per sola distanza
vettoriale. Ora: `wiki_qdrant.query_similar(db, vector, k=k*4)`, dedup per
path, poi — se `cfg["qdrant"]["rerank"]` è vero (default) — un secondo
stadio di rerank sui candidati deduplicati, prima del troncamento a `k`.

Se il modello reranker non è scaricabile (rete assente, primo avvio
offline) il rerank fallisce silenziosamente e si degrada all'ordinamento
per sola similarità vettoriale — la ricerca resta sempre funzionante,
solo meno accurata.

Non un'astrazione a plugin/factory: una funzione, un parametro on/off in
config (`qdrant.rerank`), niente di più (YAGNI).

## Config (`wiki.config.json`)

```json
"qdrant": {
  "path": "memory/qdrant",
  "embedding_model": "BAAI/bge-m3",
  "reranker_model": "BAAI/bge-reranker-v2-m3",
  "rerank": true
}
```

Sostituisce la sezione `"lancedb"`.

## requirements.txt

Rimossi `lancedb`, `pyarrow` (non più necessari per il wiki system — restano
solo nella sezione `hybrid-rag`, skill indipendente che li installa
dinamicamente per un uso diverso, fuori scope). Aggiunto `qdrant-client`.
`sentence-transformers` copre già sia l'embedder (`SentenceTransformer`)
sia il reranker (`CrossEncoder`), nessuna dipendenza nuova per il reranking.

## File toccati

- Nuovo: `wiki/scripts/wiki_qdrant.py`, `wiki/scripts/wiki_rerank.py`
- Rimosso: `wiki/scripts/wiki_lancedb.py`
- Adattati (import + chiave config, minimo indispensabile):
  `wiki_workflows.py`, `wiki_graph.py`, `wiki_server.py`, `wiki_check_setup.py`,
  `wiki.py` (REQUIRED_CONFIG_FIELDS)
- Config: `wiki.config.json`, `requirements.txt`
- Test: `test_wiki_lancedb.py` → `test_wiki_qdrant.py` (stessa copertura),
  `test_wiki_graph.py`, `test_wiki_server.py`, `test_wiki.py`,
  `test_wiki_workflows.py`, `conftest.py` adattati agli import/chiavi nuovi
- Documentazione: `wiki/README.md`, `wiki/README.it.md`, `wiki/SPEC.md`,
  `wiki/SPEC.it.md`, `wiki/DESIGN.md`, `wiki/DESIGN.it.md` — sostituito
  "LanceDB" → "Qdrant" nelle sezioni di stato corrente, changelog storici
  lasciati intatti (descrivono cosa è successo quando lancedb era in uso)

## Regressione preesistente scoperta (non di questa migrazione)

`wiki/tests/test_wiki_core_sync.py` puntava ancora a `skills/wiki-core.md`,
percorso spostato in `skills/wiki-core/SKILL.md` dalla fase 1 (plugin
conversion). Corretto qui perché bloccava la verifica di questa fase, ma non
è un effetto della migrazione Qdrant.

`wiki/tests/test_wiki_workflows.py::test_lint_full_reports_semantic_duplicates`
fallisce per un'asserzione (`output["patterns_found"]`) che non corrisponde
a nessuna chiave mai restituita da `cmd_lint` — bug preesistente indipendente
da questa migrazione, non toccato (fuori scope, richiede capire l'intento
originale del test). Confermato preesistente: `git diff` sul file mostra che
l'unica riga toccata da questa migrazione è un commento.

## Fuori scope

- Hook, comandi slash dedicati, agenti custom (esclusi anche in fase 1)
- Riscrittura degli alberi di directory/changelog storici nei doc (drift
  preesistente, non introdotto da questa migrazione)
- Fix del test `patterns_found` preesistente (bug scoperto, non causato qui)
