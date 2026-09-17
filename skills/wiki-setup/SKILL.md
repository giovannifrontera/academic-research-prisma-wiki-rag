---
name: wiki-setup
description: First-time setup of the wiki research memory system for Claude Code. Use when starting a new installation or when wiki commands return errors.
---

# Wiki Setup — Claude Code

**Skill rigida:** esegui ogni step nell'ordine indicato senza saltarne nessuno.

---

## Step 1 — Dipendenze Python

Dalla radice del repository, usa lo stesso interprete per installazione e comandi:

```bash
python -m pip install -r requirements.txt
```

---

## Step 2 — Configura `wiki/wiki.config.json`

Crea la directory dati e copia `wiki/wiki.config.json` al suo interno come
`<W>/wiki.config.json`. Modifica questa copia e imposta:

```json
{
  "workspace": "C:/Users/tuo-nome/Documents/wiki-data"
}
```

Il workspace è la **directory dati** dove vivranno i tuoi paper e la tua conoscenza di ricerca. Può essere qualsiasi path assoluto — non deve essere dentro il repo. Verrà creata automaticamente allo Step 3.

---

## Step 3 — Inizializza il sistema

```bash
python wiki/scripts/wiki.py rebuild --workspace C:/Users/tuo-nome/Documents/wiki-data
```

Prepara questa struttura; rebuild indicizza le pagine Markdown già presenti:

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
└── memory/qdrant/          ← indice vettoriale (non modificare manualmente)
```

---

## Step 4 — Verifica

```bash
python wiki/scripts/wiki.py query --workspace C:/Users/tuo-nome/Documents/wiki-data --q "test" --k 1
```

Output atteso: JSON con `"status": "ok"` e `"results": []` — l'indice è vuoto, è corretto.

---

## Step 5 — Collega a prisma-review

Quando avvii `prisma-review`, inserisci il path del workspace quando richiesto in **Fase 0.8**. Il path viene salvato in `prisma_state.json` come `wiki_workspace` per tutta la sessione.

---

Setup completato. Consulta `skills/wiki-core/SKILL.md` per i comandi di utilizzo.
