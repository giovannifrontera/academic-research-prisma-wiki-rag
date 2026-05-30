---
name: wiki-setup
description: First-time setup of the wiki research memory system for Claude Code. Use when starting a new installation or when wiki commands return errors.
---

# Wiki Setup — Claude Code

**Skill rigida:** esegui ogni step nell'ordine indicato senza saltarne nessuno.

---

## Step 1 — Dipendenze Python

```bash
pip install lancedb sentence-transformers pdfplumber pyyaml fastapi uvicorn watchfiles
```

Oppure dalla radice del repo (installa tutto inclusi i componenti PRISMA):
```bash
pip install -r requirements.txt
```

---

## Step 2 — Configura `wiki/wiki.config.json`

Apri `wiki/wiki.config.json` e imposta:

```json
{
  "workspace": "C:/Users/tuo-nome/Documents/wiki-data"
}
```

Il workspace è la **directory dati** dove vivranno i tuoi paper e la tua conoscenza di ricerca. Può essere qualsiasi path assoluto — non deve essere dentro il repo. Verrà creata automaticamente allo Step 3.

---

## Step 3 — Inizializza il sistema

```bash
py wiki/scripts/wiki.py rebuild --workspace C:/Users/tuo-nome/Documents/wiki-data
```

Questo crea la struttura delle cartelle e l'indice LanceDB:

```
wiki-data/
├── wiki-works/ricerca/     ← paper e conoscenza PRISMA (per progetto)
│   ├── entities/           ← entity pages: un paper = una pagina
│   ├── synthesis/          ← sintesi tematiche
│   ├── concepts/           ← framework teorici, concetti chiave
│   └── raw/                ← testo grezzo estratto da PDF
├── wiki/                   ← conoscenza distillata cross-progetto
│   ├── concepts/
│   └── synthesis/
└── memory/lancedb/         ← indice vettoriale (non modificare manualmente)
```

---

## Step 4 — Verifica

```bash
py wiki/scripts/wiki.py query --workspace C:/Users/tuo-nome/Documents/wiki-data --q "test" --k 1
```

Output atteso: `No results found` — l'indice è vuoto, è corretto.

---

## Step 5 — Collega a prisma-review

Quando avvii `prisma-review`, inserisci il path del workspace quando richiesto in **Fase 0.8**. Il path viene salvato in `prisma_state.json` come `wiki_workspace` per tutta la sessione.

---

Setup completato. Consulta `skills/wiki-core.md` per i comandi di utilizzo.
