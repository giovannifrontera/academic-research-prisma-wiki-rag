# Stato sessione

**Ultimo aggiornamento:** 2026-09-28 — release 1.3.0

## Stato

- Il piano "Isolated Study Workspace" (`plans/2026-09-17-isolated-study-workspace.md`, 12 task) è **completato** (commit `8300e77`, 2026-09-19).
- 1.3.0: corretto il server MCP Semantic Scholar, che usava l'API MCP 2.x incompatibile con `mcp<2`.
- Suite locale (Linux, Python 3.14, torch CPU): 184 test verdi con `python -m pytest wiki/tests tests skills`.
- `claude plugin validate --strict` supera la validazione di `plugin.json` e `marketplace.json`.

## Aperto

- Collaudo end-to-end su Windows pulito (installazione da marketplace + venv nel `PATH`), non ancora eseguito.
- I server MCP usano `python` dal `PATH`: Claude va avviato dal terminale con il venv attivo.
