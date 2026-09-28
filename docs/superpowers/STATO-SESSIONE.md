# Stato sessione

**Ultimo aggiornamento:** 2026-09-28 — release 1.4.2

## Stato

- Il piano "Isolated Study Workspace" (`plans/2026-09-17-isolated-study-workspace.md`, 12 task) è **completato** (commit `8300e77`, 2026-09-19).
- 1.3.0: corretto il server MCP Semantic Scholar, che usava l'API MCP 2.x incompatibile con `mcp<2`.
- 1.3.1: il rerank di `hybrid-rag query` valuta `n_results × 3` candidati RRF (prima riordinava solo i `n_results` già selezionati).
- 1.4.0: recuperati i server arXiv e PubMed dal ramo `origin/main` (mai unito a `master`, commit `1a02978`), adattati al contratto JSON e testati dal vivo. Su `origin/main` resta non unito anche il filone `research-design` (IMRaD): da valutare.
- 1.4.1: explorer web del wiki verificato in Chrome (login, grafo D3, dettaglio pagina, Stats, WebSocket live); corretti login bloccato, password predefinita `changeme` e frontmatter visibile.
- 1.4.1: `serve --project` apre l'explorer sullo studio sigillato e ne mostra il nome (spec/plan `2026-09-28-study-scoped-wiki-explorer`).
- 1.4.1: corretto `paths` in `.project-state.json` (`qdrant_rag`/`qdrant_wiki` invece della cartella inesistente `database/qdrant`).
- 1.4.2: server OpenAIRE migrato alla Graph API v2 (la vecchia Search API è stata dismessa il 31/05/2026 e rispondeva 503 dopo 60 s).
- Suite locale (Linux, Python 3.14, torch CPU): 200 test verdi con `python -m pytest wiki/tests tests skills`.
- `claude plugin validate --strict` supera la validazione di `plugin.json` e `marketplace.json`.

## Aperto

- Collaudo end-to-end su Windows pulito (installazione da marketplace + venv nel `PATH`), non ancora eseguito.
- I server MCP usano `python` dal `PATH`: Claude va avviato dal terminale con il venv attivo.
