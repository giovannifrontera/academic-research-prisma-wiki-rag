# Stato sessione — Isolated Study Workspace

**Ultimo aggiornamento:** 2026-09-17

## Cosa è pronto (non ancora implementato, solo design)

- Spec aggiornata: `docs/superpowers/specs/2026-09-17-isolated-study-workspace-design.md`
- Piano di implementazione TDD completo (12 task): `docs/superpowers/plans/2026-09-17-isolated-study-workspace.md`
- Fix minore già applicato: `.claude-plugin/plugin.json` → `defaultEnabled: true` (era `false`, il plugin non si attivava da solo dopo l'installazione)

**Working tree non committato** (lasciato apposta per continuare domani):
```
modificato:  .claude-plugin/plugin.json
modificato:  docs/superpowers/specs/2026-09-17-isolated-study-workspace-design.md
non tracciato: docs/superpowers/plans/2026-09-17-isolated-study-workspace.md
```

## Decisioni prese in questa sessione (confermate dall'utente)

1. **Due Qdrant separati per study**, non uno condiviso: `database/qdrant-rag/` (papers PRISMA + PDF inclusi) e `database/qdrant-wiki/` (pagine wiki + staging). Motivo: un DB unico con 4 collection avrebbe introdotto un errore `database_in_use` per lock a singolo writer tra RAG e wiki — non necessario, l'isolamento tra study si ottiene comunque con due cartelle separate sotto la stessa study root sigillata.
2. **Export wiki obbligatorio, non opzionale**, prima dell'indicizzazione RAG: ogni paper indicizzato deve avere una pagina wiki Markdown umanamente consultabile che lo "legittima" (funge da prova citabile dietro ogni hit RAG). Override esplicito `--skip-wiki-export` se serve bypassare.
3. **Reranking cross-encoder anche su `hybrid-rag query`**: oggi solo il wiki fa rerank con `BAAI/bge-reranker-v2-m3`; il RAG dei paper PRISMA restituiva solo risultati RRF grezzi. Aggiunto stesso modello, stesso comportamento del wiki.
4. **Download automatico full-text quando disponibile open-access**: oggi la ricerca automatica sulle basi dati (core/doaj/eric/openaire/zenodo/semantic-scholar) lavora solo su abstract — nessun full-text viene mai scaricato in automatico, solo i PDF caricati manualmente dall'utente (Stream 2) vengono salvati per intero. Aggiunta acquisizione automatica: se un record espone un URL full-text (es. `sourceFulltextUrls` di CORE) che supera i controlli SSRF/dimensione/content-type, viene scaricato in `sources/pdf-inbox/` durante lo Stream 1; se non disponibile o bocciato dai controlli, si procede solo-abstract come oggi (nessun blocco, best-effort).

## Struttura directory per-study concordata (finale)

```
<study-slug>/
├── .project-state.json
├── prisma/
├── sources/{pdf-inbox,pdf-inclusi}/
├── database/{qdrant-rag,qdrant-wiki}/
├── wiki-memory/{wiki.config.json, wiki/, wiki-works/<slug>/}
├── synthesis/ design/ preprint/ export/
```

## Piano di implementazione — 12 task (in ordine)

1. Slug algorithm (`scripts/study_workspace.py::slugify`)
2. Contratto di stato `.project-state.json` (`build_state`/`read_state`)
3. Creazione atomica directory + regole di collisione (`create_study`)
4. CLI `study_workspace.py create|inspect`
5. Helper di containment path (`scripts/study_paths.py`)
6. `hybrid_rag_template.py` in modalità study (`--project`, path `qdrant-rag`, rinomina collection)
7. **6b** — Cross-encoder rerank + gate export-wiki-obbligatorio su hybrid-rag
8. Allineamento nomi collection wiki (`wiki_pages`/`staging_wiki_pages`) — verifica, possibile no-op
9. Bootstrap genera `wiki.config.json` per-study (punta a `qdrant-wiki`)
10. Aggiornamento doc skill (`pipeline-ricerca`, `prisma-review`, README, PROJECT-SPEC)
11. **9b** — Acquisizione automatica full-text (`fetch_fulltext.py`, guardie SSRF/size/content-type)
12. Test di integrazione cross-study + verifica CI Windows/Ubuntu

Dettagli completi (codice, test, comandi esatti) nel file del piano — non riassunti qui per evitare divergenza dalla fonte.

## Non ancora deciso

- **Modalità di esecuzione del piano**: subagent-driven (un subagent fresco per task, review tra un task e l'altro) vs esecuzione inline in sessione con `executing-plans`. Da decidere alla ripresa.

## Prossimo passo alla ripresa

Chiedere all'utente quale modalità di esecuzione preferisce, poi eseguire il piano task per task (TDD, commit ad ogni task come da piano).
