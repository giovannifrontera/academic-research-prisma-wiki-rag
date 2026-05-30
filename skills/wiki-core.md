---
name: wiki-core
description: Long-term research memory for Claude Code. Persists academic knowledge (papers, syntheses, notes) across sessions in a LanceDB vector index. Use to query existing knowledge before a new PRISMA review, ingest papers and syntheses after a review, and retrieve evidence during pilot study design. Integrates with prisma-review and educational-pilot-design. Trigger whenever the user wants to save, search or consult the research knowledge base.
---

# Wiki Core — Research Memory

> **Nota:** Accedi con `Read skills/wiki-core.md`. Non usare il tool `Skill` — wiki-core è un documento di riferimento, non una skill invocabile.
>
> I comandi usano il path relativo `wiki/scripts/wiki.py` dalla radice del repo.
> Su Linux/macOS sostituisci `py` con `python3`.

---

## Architettura

Due layer, un unico indice vettoriale LanceDB:

| Layer | Path (relativo al workspace) | Contenuto |
|---|---|---|
| **Conoscenza di progetto** | `wiki-works/ricerca/` | Paper, sintesi, note per specifici progetti PRISMA |
| **Conoscenza distillata** | `wiki/concepts/`, `wiki/synthesis/` | Conoscenza cross-progetto, promossa autonomamente |

**Workspace** = directory assoluta configurata in `wiki/wiki.config.json → "workspace"`.
Tutti i comandi ricevono questo path via `--workspace`.

---

## Comandi di riferimento

```bash
# Interroga la memoria
py wiki/scripts/wiki.py query --workspace <W> --q "<domanda>" --k 5

# Ingest (pages già scritte come .tmp)
py wiki/scripts/wiki.py ingest --workspace <W> --pages <f1.tmp,f2.tmp,...> --log "<etichetta>"

# Ingest PDF (estrae testo — poi segui §ingest per creare le pagine strutturate)
py wiki/scripts/wiki.py ingest-pdf --workspace <W> --file <percorso-o-url>

# Lint (trova duplicati, link rotti)
py wiki/scripts/wiki.py lint --workspace <W> --full

# Rebuild indice da zero (dopo import massivo o corruzione)
py wiki/scripts/wiki.py rebuild --workspace <W>

# Dashboard web opzionale (http://localhost:7331)
py wiki/scripts/wiki.py serve --workspace <W> --no-auth
```

`<W>` = path assoluto al wiki workspace (es. `C:/Users/nome/Documents/wiki-data`).

---

## §query — Interrogare la memoria

1. Esegui: `py wiki/scripts/wiki.py query --workspace <W> --q "<domanda>" --k 5`
2. Leggi le pagine restituite
3. Sintetizza con riferimenti `[titolo-pagina](path)`
4. Se la sintesi supera 300 token, aggiunge inferenza non letterale e attinge da ≥2 fonti → salva come nuova pagina via §ingest, poi valuta §promotion

---

## §ingest — Salvare conoscenza

**Fase A — Scrivi le pagine come file `.tmp`:**

| Tipo pagina | Path |
|---|---|
| Paper singolo / entità | `wiki-works/ricerca/entities/<slug>.md.tmp` |
| Sintesi di più paper | `wiki-works/ricerca/synthesis/<slug>.md.tmp` |
| Concetto / framework | `wiki-works/ricerca/concepts/<slug>.md.tmp` |

**Fase B — Ingest:**
```bash
py wiki/scripts/wiki.py ingest \
  --workspace <W> \
  --pages <p1.tmp,p2.tmp,...> \
  --log "ingest | <titolo>"
```

`ingest` usa upsert — è sempre sicuro rieseguirlo su pagine già esistenti.

**Fase C — Report:** fonti usate, pagine create, conflitti rilevati.
Dopo l'ingest, valuta §promotion per ogni pagina nuova.

---

## §pdf-inbox — Ingest da PDF

```bash
py wiki/scripts/wiki.py ingest-pdf --workspace <W> --file <percorso>
```

1. Estrae testo via pdfplumber
2. Salva il testo grezzo in `wiki-works/ricerca/raw/YYYY-MM-DD-slug.md`
3. **Scrivi le pagine strutturate `.tmp` e chiama §ingest** — `ingest-pdf` estrae solo il testo, non crea pagine automaticamente

> ⚠️ `process-raw` reindicizza solo file già in `raw/` — non crea pagine strutturate. Usa sempre il workflow §ingest completo per nuova conoscenza.

---

## §promotion — Quando promuovere a `wiki/`

Promuovi una pagina da `wiki-works/ricerca/` a `wiki/` quando vale tutte e tre:
- Rilevante in ≥2 progetti o contesti di ricerca diversi
- Recuperata in ≥3 query distinte
- Contiene inferenza che va oltre una singola fonte

Come promuovere:
1. Scrivi la pagina distillata come `.tmp` in `wiki/concepts/<slug>.md.tmp` o `wiki/synthesis/<slug>.md.tmp`
2. Chiama §ingest sul file `.tmp`
3. Mantieni l'originale in `wiki-works/ricerca/` se contiene dettagli specifici della fonte

---

## §lint — Manutenzione

```bash
py wiki/scripts/wiki.py lint --workspace <W> --full
```

Output include `semantic_duplicates`:
- similarità ≥ 0.90 → merge: leggi entrambe, scrivi `.tmp` unificata, chiama ingest, elimina originali
- 0.75 ≤ similarità < 0.90 → mostra le prime 2 righe di ciascuna, chiedi all'utente se unire

---

## Integrazione con il workflow PRISMA

| Momento | Azione | Riferimento |
|---|---|---|
| Prima di PRISMA Fase 1 | Query per conoscenza pre-esistente | `prisma-review` § 1.0 |
| Dopo PRISMA Fase 4 | Ingest paper inclusi come entity pages | `prisma-review` § Export wiki — A |
| Dopo PRISMA Fase 6 | Ingest sintesi | `prisma-review` § Export wiki — B |
| Durante `educational-pilot-design` | Query per evidenze cross-progetto | wiki query + `hybrid_rag.py` per RAG locale |

---

## Configurazione workspace

Modifica `wiki/wiki.config.json`:
- `"workspace"` → path assoluto alla directory dati wiki (es. `C:/Users/nome/Documents/wiki-data`)
- `"projects.ricerca.path"` → sottocartella conoscenza ricerca (default: `wiki-works/ricerca`)
- `"lancedb.path"` → sottocartella indice vettoriale (default: `memory/lancedb`)

Tutti i path in `wiki.config.json` sono **relativi a `workspace`**.
