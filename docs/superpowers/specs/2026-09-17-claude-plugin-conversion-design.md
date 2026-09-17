# Design: conversione a plugin Claude Code CLI + server Semantic Scholar

Data: 2026-09-17

## Contesto

`academic-research-prisma-wiki-rag` oggi è distribuito come "copia manuale":
skill Markdown sciolte da copiare in `~/.claude/skills/` e 5 server MCP
Python da registrare uno a uno con `claude mcp add`. Non esiste nessun
manifest `.claude-plugin/plugin.json`, quindi il progetto non è installabile
come plugin Claude Code CLI (`/plugin marketplace add`, `claude plugin
install`) — nonostante il nome "OpenClaw plugin" usato per un progetto
correlato, che è un concetto diverso (plugin per il sistema OpenClaw, non per
Claude Code).

Questo è il primo di due lavori in sequenza:
1. **Questo documento** — trasformare il repo in un plugin Claude Code CLI
   valido, e completare la lista di 6 server MCP promessa dal README
   implementando quello mancante (Semantic Scholar).
2. Successivo (spec separata) — migrare `wiki/` da LanceDB a Qdrant e
   aggiungere il cross-encoder reranking, dentro la nuova struttura plugin.

## Problema riscontrato: disallineamento MCP servers

Il README documenta e configura 6 server MCP (tabella "Academic MCP
Servers" + comandi `claude mcp add` nel Quick Start): ERIC, OpenAIRE, CORE,
DOAJ, Zenodo, Semantic Scholar. Nel filesystem esistono solo 5 directory in
`mcp-servers/`: `core`, `doaj`, `eric`, `openaire`, `zenodo`.
`mcp-servers/semantic-scholar/` non esiste. Va implementato prima di
dichiarare il manifest plugin, altrimenti il plugin dichiarerebbe un server
inesistente.

## Struttura plugin target

```
academic-research-prisma-wiki-rag/
├── .claude-plugin/
│   └── plugin.json
├── skills/
│   ├── educational-pilot-design/SKILL.md   # già a directory, invariato
│   ├── hybrid-rag/SKILL.md                 # invariato
│   ├── pandoc-export/SKILL.md              # invariato
│   ├── pipeline-ricerca/SKILL.md           # invariato
│   ├── prisma-review/SKILL.md              # invariato
│   ├── wiki-core/SKILL.md                  # NUOVO: da skills/wiki-core.md
│   │   └── wiki-core.it.md                 # variante IT come file di supporto
│   └── wiki-setup/SKILL.md                 # NUOVO: da skills/wiki-setup.md
├── mcp-servers/
│   ├── core/server.py
│   ├── doaj/server.py
│   ├── eric/server.py
│   ├── openaire/server.py
│   ├── semantic-scholar/server.py          # NUOVO
│   └── zenodo/server.py
├── wiki/                                    # invariato in questa fase
├── README.md / LICENSE / requirements.txt
```

Regola plugin: solo `plugin.json` dentro `.claude-plugin/`, tutto il resto
in radice del plugin (come oggi).

## plugin.json

```json
{
  "name": "academic-research-prisma-wiki-rag",
  "displayName": "Academic PRISMA Research Workflow",
  "version": "1.0.0",
  "description": "AI-powered systematic review, pilot study design, and preprint publication — with persistent knowledge memory",
  "author": { "name": "Giovanni Frontera" },
  "repository": "https://github.com/giovannifrontera/academic-research-prisma-wiki-rag",
  "license": "AGPL-3.0",
  "keywords": ["prisma", "systematic-review", "academic-research", "rag"],
  "defaultEnabled": false,
  "skills": "./skills/",
  "mcpServers": {
    "eric": {
      "command": "python",
      "args": ["${CLAUDE_PLUGIN_ROOT}/mcp-servers/eric/server.py"]
    },
    "openaire": {
      "command": "python",
      "args": ["${CLAUDE_PLUGIN_ROOT}/mcp-servers/openaire/server.py"]
    },
    "core": {
      "command": "python",
      "args": ["${CLAUDE_PLUGIN_ROOT}/mcp-servers/core/server.py"],
      "env": { "CORE_API_KEY": "${CORE_API_KEY:-}" }
    },
    "doaj": {
      "command": "python",
      "args": ["${CLAUDE_PLUGIN_ROOT}/mcp-servers/doaj/server.py"]
    },
    "zenodo": {
      "command": "python",
      "args": ["${CLAUDE_PLUGIN_ROOT}/mcp-servers/zenodo/server.py"]
    },
    "semantic-scholar": {
      "command": "python",
      "args": ["${CLAUDE_PLUGIN_ROOT}/mcp-servers/semantic-scholar/server.py"],
      "env": { "SEMANTIC_SCHOLAR_API_KEY": "${SEMANTIC_SCHOLAR_API_KEY:-}" }
    }
  }
}
```

Nessun campo `hooks`, `commands`, `agents`: non richiesti oggi, non li
aggiungo (YAGNI). Le skill già in formato directory con `SKILL.md` restano
model-invocabili come oggi (nessun `disable-model-invocation`), coerente col
comportamento attuale (`/prisma-review` invocato dall'utente ma anche
richiamabile dal modello quando pertinente).

## Skill flat → directory

`skills/wiki-core.md`, `skills/wiki-core.it.md`, `skills/wiki-setup.md` sono
oggi file sciolti in `skills/`, incompatibili con la convenzione plugin
(`skills/<nome>/SKILL.md`). Diventano:
- `skills/wiki-core/SKILL.md` (contenuto di `wiki-core.md`) +
  `skills/wiki-core/wiki-core.it.md` come file di supporto referenziato
- `skills/wiki-setup/SKILL.md` (contenuto di `wiki-setup.md`)

Nessuna modifica al contenuto delle skill, solo riposizionamento file.

## Nuovo server: `mcp-servers/semantic-scholar/server.py`

Stesso pattern stilistico di `mcp-servers/core/server.py` (FastMCP, solo
stdlib `urllib`, nessuna nuova dipendenza):

- Base URL: `https://api.semanticscholar.org/graph/v1/`
- `SEMANTIC_SCHOLAR_API_KEY` opzionale via env var; se assente, warning su
  stderr all'avvio (stesso messaggio pattern di `core`) e richieste senza
  header `x-api-key` (rate limit basso ma funzionante, a differenza di CORE
  che richiede la key). Se presente, header `x-api-key: <key>`.
- Tool esposti:
  - `semantic_scholar_search(query, year_from=None, year_to=None, fields_of_study=None, limit=10)`
    → ricerca bibliografica, usa `/paper/search`
  - `semantic_scholar_get_paper(paper_id)` → metadati completi di un paper
    (`/paper/{paper_id}`), inclusi abstract, autori, venue
  - `semantic_scholar_citations(paper_id, limit=20)` → paper che citano
    quello dato (`/paper/{paper_id}/citations`)
  - `semantic_scholar_references(paper_id, limit=20)` → paper citati da
    quello dato (`/paper/{paper_id}/references`)
- Formattazione output human-readable coerente con `_format_results` di
  `core/server.py` (titolo, autori troncati a 3 + "et al.", anno, venue,
  DOI/paperId, abstract troncato a 300 char)
- Gestione errori identica al pattern esistente:
  `HTTPError`/`URLError`/`TimeoutError` → `RuntimeError` con messaggio
  descrittivo, catturato nel tool e restituito come stringa `"Error: ..."`

## README

- Riga tabella "Semantic Scholar" resta invariata (già corretta)
- Sezione Quick Start "Configure MCP servers" con `claude mcp add` viene
  sostituita dalla singola istruzione di installazione plugin:
  `/plugin marketplace add giovannifrontera/academic-research-prisma-wiki-rag`
  (o `claude --plugin-dir .` per test locale) — i server MCP non richiedono
  più registrazione manuale, sono dichiarati nel manifest
- Nota su `CORE_API_KEY` e `SEMANTIC_SCHOLAR_API_KEY` come variabili
  d'ambiente opzionali da esportare prima di avviare Claude Code

## Validazione

`claude plugin validate .` come step finale prima del commit, per
verificare che il manifest sia conforme.

## Testing

Non esistono test automatici per i server MCP oggi (nessun `tests/` sotto
`mcp-servers/`); non ne aggiungo per gli esistenti (fuori scope), ma per il
nuovo `semantic-scholar/server.py`, essendo logica non triviale (parsing
query, formattazione risultati, gestione errori), aggiungo un self-check
minimo: uno script `mcp-servers/semantic-scholar/test_server.py` con
`assert`-based smoke test sulle funzioni di formattazione/costruzione URL
(no rete, mockando la risposta), eseguibile standalone.

## Fuori scope (rimandato alla spec successiva)

- Migrazione `wiki/` da LanceDB a Qdrant
- Cross-encoder reranking
- Hook, comandi slash dedicati, agenti custom
