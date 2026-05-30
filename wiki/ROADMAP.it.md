# Roadmap — AI Longterm Wiki Memory

Idee di sviluppo future, non ancora pianificate. Ordinate per priorità stimata.

---

## [DONE] Dashboard Osservabilità — v2.2.0

**Stato:** Rilasciato in v2.2.0 (2026-05-23)

`GET /api/stats` aggrega tutti i dati di salute del wiki (copertura embedding, pagine stale, top-queried, stato lint, schedule auto-lint) in un unico endpoint JSON. Un tab `[Stats]` nel frontend mostra 4 KPI card, top-10 pagine più interrogate e un pulsante per avviare il lint. `POST /api/lint` esegue `wiki.py lint --full` on demand con guardia 409 contro esecuzioni concorrenti. Lo scheduler auto-lint legge `frontend.lint_interval_hours` da `wiki.config.json` e lancia il lint automaticamente in background.

---

## [DONE] Pre-prompt context injection — v1.1.0

**Stato:** Rilasciato in v1.1.0 (2026-05-21)

`wiki_context.py` esegue una ricerca vettoriale prima di ogni prompt utente e inietta le pagine rilevanti come blocco `<wiki-context>`. Collegato come pre-hook in OpenClaw via `plugins/wiki-context-plugin/`. Vedi `AGENTS_PATCH.md`.

---

## [PLANNED] MCP Scientific Database Integration

**Stato:** In valutazione  
**Effort:** Medio (solo skill + template, nessuna modifica agli script Python)

### Problema

Il workflow INGEST attuale usa `web_search` + `web_fetch` per recuperare contenuti. Per paper accademici questo produce HTML grezzo: formattazione inconsistente, metadati sparsi, nessuna struttura citazionale.

### Soluzione

Aggiungere un intent `RESEARCH_INGEST` nella skill `wiki-core.md` che usa i tool MCP per database scientifici quando disponibili:

| MCP Server | Database | Copertura |
|------------|----------|-----------|
| `mcp__pubmed` | PubMed / MEDLINE | Medicina, biologia, scienze della vita |
| `mcp__semantic-scholar` | Semantic Scholar | Computer science, AI, interdisciplinare |
| `mcp__eric` | ERIC | Educazione, pedagogia, psicologia scolastica |
| `mcp__ricerca-italia` | OpenAIRE | Ricerca europea, Open Access italiani |

### Come funzionerebbe

**Riconoscimento intent:**

| Segnale | Intent |
|---------|--------|
| DOI nudo (`10.xxxx/...`), PMID, "cerca su pubmed", "trova paper su", "studi su", titolo di articolo | RESEARCH_INGEST |

**Workflow `§research-ingest`:**

```
1. Identifica il database più appropriato dal contesto (argomento, tipo di fonte)
2. Chiama il tool MCP con query/DOI/PMID
3. Riceve metadati strutturati: titolo, autori, abstract, anno, DOI, citazioni
4. Opzionale: recupera full-text se disponibile (mcp__pubmed__get_paper_fulltext)
5. Scrive pagine .tmp con template accademico (vedi sotto)
6. Chiama wiki.py ingest come al solito (nessuna modifica agli script)
```

**Template pagina paper:**

```markdown
---
type: paper
doi: 10.xxxx/...
authors: [Cognome, Nome; ...]
year: 2024
journal: Nome rivista
keywords: [keyword1, keyword2]
source_db: pubmed | semantic-scholar | eric | openaire
---

# Titolo articolo

## Abstract
[abstract completo]

## Contributo principale
[sintesi del contributo — scritto dall'agente]

## Metodi
[se rilevante]

## Limitazioni
[se dichiarate]

## Citazioni chiave
- [[slug-paper-citato-1]]
- [[slug-paper-citato-2]]

## Link
- DOI: https://doi.org/10.xxxx/...
- Fonte: [database]
```

**Pagine collaterali generate automaticamente:**

- `entities/authors/<cognome-nome>.md` — profilo autore con lista paper wiki
- `entities/journals/<slug-rivista>.md` — rivista con impact factor e lista paper
- Link bidirezionali citazioni → create da LINT se mancanti

### Portabilità

I tool MCP sono disponibili solo se configurati in OpenClaw. La skill deve gestire il fallback:

```
Se mcp__pubmed non disponibile → usa web_search su pubmed.ncbi.nlm.nih.gov
Se mcp__semantic-scholar non disponibile → usa web_fetch su api.semanticscholar.org
```

Nessuna modifica agli script Python — `wiki.py ingest` rimane identico.

### File da modificare

- `skills/wiki-core.md` — aggiunta blocco `§research-ingest`
- `skills/wiki-research.md` *(nuovo)* — skill opzionale caricabile separatamente con workflow dettagliati per ogni database
- `SPEC.md` — aggiunta sezione §research-ingest
- `README.md` — sezione "Academic Research"

---

## [IDEA] Conflict resolution interattiva via chat

**Stato:** Idea grezza  
**Effort:** Alto

Oggi il Conflict Livello 3 (contraddizione semantica tra fonti) blocca il merge e aspetta input umano. L'agente potrebbe presentare le due versioni in chat con una UI strutturata (opzione A / opzione B / merge manuale) invece di un messaggio generico.

---

## [IDEA] Export PRISMA-ready

**Stato:** Idea grezza  
**Effort:** Medio

Per revisioni sistematiche: comando `wiki.py export --format prisma --workspace wiki-works/ricerca` che genera una tabella PRISMA da tutti i paper ingestionati, con campi: autore, anno, titolo, database fonte, criteri inclusione/esclusione (se taggati nelle pagine).

---

## [FATTO in v3] wiki-works → wiki promozione autonoma

**Stato:** Implementato in v3.0.0 come comportamento autonomo dell'agente.

L'agente promuove pagine da `wiki-works/<topic>/` a `wiki/` autonomamente quando la conoscenza è trasversale: rilevante in ≥2 argomenti e recuperata in ≥3 query distinte. Nessun comando manuale necessario — l'agente valuta i criteri di promozione dopo ogni INGEST e sintesi QUERY. Vedi `skills/wiki-core.it.md §promozione`.

---

*Aggiornato: 2026-05-23*
