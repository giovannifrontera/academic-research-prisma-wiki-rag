# Installazione — OpenClaw

Il plugin TypeScript `wiki-context-plugin` inietta il contesto wiki via hook `before_prompt_build`.

## Prerequisiti

- OpenClaw installato
- Node.js >= 18
- Python (`py` su Windows, `python3` su macOS/Linux)
- Repository `ai-wiki-system` clonato
- Workspace wiki configurato con `wiki.config.json`

## Build del plugin

```bash
cd plugins/wiki-context-plugin
npm install
npm run build
```

## Configurazione in OpenClaw

Aggiungi al file di configurazione di OpenClaw:

```json
{
  "plugins": [
    {
      "id": "wiki-context-plugin",
      "path": "/path/to/ai-wiki-system/plugins/wiki-context-plugin",
      "config": {
        "workspace": "/path/assoluto/al/workspace",
        "wikiContextScript": "/path/to/ai-wiki-system/scripts/wiki_context.py",
        "pythonExecutable": "py",
        "k": 3,
        "timeoutMs": 15000
      }
    }
  ]
}
```

> **Su Windows** usa `"pythonExecutable": "py"` come mostrato sopra. Se ottieni `ModuleNotFoundError`, vedi la sezione Troubleshooting per il percorso assoluto.

### Parametri di configurazione

| Parametro | Obbligatorio | Default | Descrizione |
|-----------|-------------|---------|-------------|
| `workspace` | si | — | Path assoluto al workspace wiki |
| `wikiContextScript` | si | — | Path a `wiki_context.py` |
| `pythonExecutable` | no | `python` | Eseguibile Python. **Su Windows Store Python usa il percorso assoluto** (vedi Troubleshooting) |
| `k` | no | 3 | Chunk wiki da iniettare per prompt |
| `timeoutMs` | no | 15000 | Timeout per `wiki_context.py` in ms |

## Come funziona

Ad ogni prompt, OpenClaw esegue `wiki_context.py` via `before_prompt_build`. Lo script cerca i chunk semanticamente rilevanti in LanceDB e li prepende come blocco `<wiki-context>`.

## Troubleshooting

### Windows Store Python: `ModuleNotFoundError: No module named 'pyarrow'`

Il launcher `py` non trova i pacchetti nativi nel contesto di esecuzione di OpenClaw. Sostituisci con il percorso assoluto:

```bash
# Trova il percorso corretto
py -c "import sys; print(sys.executable)"
```

Poi nella config OpenClaw:

```json
{
  "pythonExecutable": "C:\\Users\\<utente>\\AppData\\Local\\...\\python.exe"
}
```

### Verificare che il plugin stia funzionando

Attiva `"debug": true` nella configurazione — il plugin scriverà un log in `<workspace>/.wiki-plugin-debug.log` ad ogni prompt. In alternativa usa il tool `wiki_process_raw` dalla chat: se risponde con JSON è segno che il plugin è attivo e Python funziona.

## Tool disponibili dalla chat

### `wiki_process_raw`

Promuove i file estratti dai PDF (in `raw/`) all'indice wiki. Da usare dopo `scan-inbox` o un import PDF in bulk.

Esempio di invocazione in chat:
> "usa wiki_process_raw per indicizzare i paper che ho appena ingestato"

Parametri:
| Parametro | Tipo | Default | Descrizione |
|-----------|------|---------|-------------|
| `project` | string | (tutti) | Limita a un progetto specifico (es. `"ricerca"`) |

Output atteso (esempio):
```json
{"status": "ok", "op": "process-raw", "promoted": 2, "message": "2 files promoted from raw/"}
```

Se non ci sono file da promuovere:
```json
{"status": "ok", "op": "process-raw", "promoted": 0, "message": "no raw files found"}
```
