---
name: prisma-review
description: Use when conducting a systematic literature review using the PRISMA methodology. Triggers on: systematic review, literature review, PRISMA, database search strategy, inclusion/exclusion criteria, deduplication, screening, evidence synthesis. Available MCP servers: semantic-scholar, arxiv, pubmed, eric, openaire, core, doaj, zenodo.
---

# PRISMA Systematic Review

## Overview

PRISMA (Preferred Reporting Items for Systematic Reviews and Meta-Analyses) è la metodologia standard per review sistematiche riproducibili. Questa skill guida l'intero workflow in modo **interattivo**: ogni fase richiede conferma dell'utente prima di procedere.

**Regola fondamentale:** non passare mai alla fase successiva senza approvazione esplicita dell'utente.

---

## Persistenza dello Stato — File Obbligatori

Per evitare perdita di contesto tra sessioni, mantieni **quattro file distinti** nella cartella di lavoro. Ogni file viene aggiornato alla fine della fase corrispondente, **prima** di procedere. Il report finale si genera leggendo questi file, non dalla memoria della sessione.

### 1. `prisma_state.json` — stato operativo della sessione
Tiene traccia di: query usate, numeri per fase, criteri, configurazione. Struttura:
```json
{
  "progetto": "nome_cartella",
  "data_avvio": "AAAA-MM-GG",
  "ricercatore": "nome",
  "pico": {"P": "", "I": "", "C": "", "O": ""},
  "configurazione": {"anni": "", "database": [], "lingua": [], "tipo_pub": "", "min_citazioni": null},
  "wiki_workspace": null,
  "fase_corrente": 0,
  "fase1": {"risultati_per_db": {}, "totale_lordo": 0, "stream2_pdf": 0},
  "fase2": {"totale_lordo": 0, "duplicati": 0, "esclusi_filtri": 0, "totale_screening": 0},
  "fase3": {"valutati": 0, "esclusi": {}, "inclusi": 0},
  "fase4": {"paper_inclusi": []}
}
```

### 2. `prisma_log.md` — log metodologico ufficiale
Alimenta la sezione metodologica del paper. Aggiornato progressivamente a ogni fase:
```markdown
# PRISMA Log — [nome_progetto]
**Data avvio**: AAAA-MM-GG  **Ricercatore**: [nome]

## Domanda di ricerca
[domanda principale + sub-domande]

## Framework PICO
| P | I | C | O |

## Configurazione ricerca
| Parametro | Valore |

## FASE 1 — IDENTIFICAZIONE
**Data**: AAAA-MM-GG
| Database | Query esatta | Risultati lordi |

## FASE 2 — SCREENING
| Totale lordo | Duplicati | Esclusi filtri | Dopo screening |

## FASE 3 — ELIGIBILITY
[criteri + ogni esclusione motivata]

## FASE 4 — INCLUSION
[tabella paper inclusi con campi estesi]

## Diagramma PRISMA
[diagramma di flusso con numeri reali]

## Note metodologiche
[limitazioni dei database, anomalie, decisioni non standard]
```

### 3. `prisma_synthesis.md` — note di sintesi tematica in costruzione
Creato alla Fase 4, aggiornato progressivamente man mano che si analizza ogni paper. Struttura:
```markdown
# Sintesi tematica — [nome_progetto]

## Temi emergenti
[tema 1, tema 2, ... aggiornati a ogni paper analizzato]

## Convergenze e divergenze
[cosa confermano più studi, cosa è controverso]

## Risposta provvisoria alle domande di ricerca
[aggiornata dopo ogni paper — anche parziale e non definitiva]

## Gap della letteratura
[cosa non è stato studiato, limitazioni trasversali]

## Note per la discussione
[osservazioni metodologiche, bias rilevati]

---
## OUTPUT PER PILOT STUDY — Sezione dedicata al handoff verso educational-pilot-design

### Effect size aggregati
| Outcome | N studi | Effect size medio (d/η²) | Range | IC 95% | Qualità evidenza |
|---|---|---|---|---|---|
| [outcome 1] | | | | | forte/moderata/debole |

> Usa questi valori come stima a priori nella power analysis del pilot (G*Power).
> Se la qualità è debole, usa d = 0.5 come valore conservativo.

### Framework teorici dominanti
[Elenca i framework più ricorrenti tra gli studi inclusi, con frequenza]
> Usa il framework più frequente come punto di partenza per la Fase 1 del pilot.

### Strumenti di misura più usati
| Strumento | N studi che lo usano | Outcome misurato | Note validazione italiana |
|---|---|---|---|
| [MSLQ / TAM / ...] | | | |

> Usa questa tabella nella Fase 3 del pilot per scegliere gli strumenti.

### RQ non ancora investigate nella letteratura
[Elenca le domande di ricerca che nessuno studio ha risposto, o che hanno ricevuto solo evidenza debole]
> Queste sono le RQ candidate per il pilot study.

### Gap di popolazione
[Es. "Nessuno studio su studenti di scuola secondaria italiana", "Studi solo su università USA"]
> Questo gap giustifica la scelta del campione nel pilot.

### Durata tipica degli interventi
[Range osservato: min–max settimane; mediana]
> Usa questo dato per pianificare la timeline realistica del pilot (Fase 4 educational-pilot-design).
```

### 4. `prisma_bibliography.md` — bibliografia annotata completa
Creato alla Fase 4, contiene per ogni paper incluso una scheda con annotazione critica:
```markdown
# Bibliografia annotata — [nome_progetto]

## [N]. Autore/i (Anno). Titolo. *Rivista/Fonte*. DOI/URL

**Tipo studio**: [RCT / quasi-sperimentale / qualitativo / review / ...]
**Campione**: [N partecipanti, contesto]
**Metodologia**: [metodo principale usato]
**Contributo principale**: [una o due frasi su cosa aggiunge alla letteratura]
**Limitazioni dichiarate**: [limitazioni riportate dagli autori]
**Rilevanza per la review**: [perché è stato incluso, quale domanda di ricerca aiuta a rispondere]
```

---

## Ripresa di sessione (priorità assoluta all'avvio)

**Prima di qualsiasi azione**, controlla se esiste già `prisma_state.json` nella cartella di lavoro:
- Se esiste → leggilo, identifica `fase_corrente` e l'ultimo paper processato in `fase4.paper_inclusi`
- Comunica all'utente: *"Ho riletto lo stato. Eravamo alla Fase [N], paper [X/Y]. Confermo di riprendere da lì?"*
- Non rieseguire mai fasi già completate senza esplicita richiesta
- Se `prisma_state.json` non esiste → è una sessione nuova, avvia Fase 0

---

## PRISMA Flow

```
[SETUP]          →  Raccolta parametri + PDF manuali + wiki workspace → crea file di persistenza
       ↓
[Identification] →  Stream 1: Query MCP database → raw_*.json
                    Stream 2: extract_pdf_metadata.py → raw_pdf_manual.json (PRISMA 2020)
                    Pre-search: wiki query per conoscenza pre-esistente
       ↓
[Screening]      →  Script Python: legge tutti i raw_*.json (incluso pdf_manual) → dedup cross-stream → screening_prisma.json
       ↓
[Eligibility]    →  Criteri su abstract → esclusioni motivate → aggiorna file
       ↓
[Inclusion]      →  Estrazione dati → eligibility_prisma.json → checkpoint ogni 10
       ↓
[RAG Build]      →  hybrid_rag.py index-prisma + index-pdf pdf_manuali/
       ↓
[Report]         →  hybrid_rag.py query → scrive sezione per sezione → export wiki
```

---

## FASE 0 — Setup interattivo (OBBLIGATORIO)

**Prima di qualsiasi ricerca**, poni queste domande nell'ordine indicato.

### 0.0 — Cartella di lavoro
> "Come vuoi chiamare la cartella per questa ricerca PRISMA? (es. `review_chatbot_metacognizione`)"

Crea la cartella. Salva **tutti** i file generati al suo interno. Inizializza subito `prisma_state.json` con i valori vuoti e crea `prisma_log.md` con l'intestazione.

### 0.1 — Domanda di ricerca
> "Qual è la tua domanda di ricerca? Se vuoi, possiamo strutturarla con il framework PICO:
> - **P**opolazione/Problema
> - **I**ntervento/Fenomeno
> - **C**omparison (opzionale)
> - **O**utcome atteso"

Se la domanda è ampia, aiuta l'utente a scomporla in **sub-domande** (es. RQ1, RQ2). Queste guideranno le query e la sintesi.

### 0.2 — Parametri temporali
> "Quale range di anni vuoi coprire? (es. 2015–2025)"

### 0.3 — Ambito disciplinare
> "In quale ambito disciplinare ti muovi? (es. educazione, psicologia, informatica, neuroscienze, salute — o una combinazione)"

| Ambito | Database prioritari |
|--------|-------------------|
| Educazione / pedagogia | ERIC, Semantic Scholar, OpenAIRE |
| Psicologia / neuroscienze | PubMed, Semantic Scholar |
| AI / informatica / ed-tech | arXiv, Semantic Scholar |
| Fonti italiane / europee | `openaire` (IT filter), `core`, `doaj` |
| Preprint e dataset | `zenodo`, `arxiv` |
| Interdisciplinare | tutti |

### 0.4 — Tipo di pubblicazione
> "Vuoi includere solo articoli peer-reviewed, o anche preprint, report, tesi?"

### 0.5 — Lingua
> "Quali lingue accetti? (default: solo inglese)"

### 0.6 — Soglia citazioni (opzionale)
> "Vuoi escludere paper con poche citazioni? (es. min. 5 — lascia vuoto per nessun filtro)"

> ⚠️ **Recency bias:** La soglia citazioni introduce un bias sistematico verso paper più datati. Paper pubblicati negli ultimi 2 anni (es. post-2022) hanno meno tempo per accumular citazioni anche se di alta qualità. Se usi una soglia, avverti l'utente e documenta questa limitazione nelle "Note metodologiche" del report finale. Alternativa consigliata: usare la soglia solo per i paper con più di 3 anni dalla pubblicazione.

### 0.7 — PDF trovati manualmente (PRISMA 2020 Stream 2)

> "Hai trovato manualmente articoli rilevanti che vuoi includere nella review? (es. PDF scaricati da riviste, grey literature, referenze di altri paper, contatti personali con autori)"

Se sì:
1. Chiedi di creare la cartella `pdf_manuali/` nella cartella di lavoro e inserire i PDF
2. Leggi il file `skills/prisma-review/scripts/extract_pdf_metadata.py` con il tool **Read** e scrivilo nella cartella di lavoro con il tool **Write**
3. Esegui:
   ```bash
   py extract_pdf_metadata.py pdf_manuali/
   ```
4. Lo script crea `raw_pdf_manual.json` con titolo, DOI, anno, abstract per ogni PDF
5. Chiedi all'utente di **verificare e integrare** il file generato (autori mancanti, PDF scannerizzati senza testo, abstract non trovati)
6. Conta i record validi e aggiorna `prisma_state.json` con `fase1.stream2_pdf`

> ⚠️ **PDF scannerizzati (solo immagine):** pdfplumber non estrae testo. Lo script segnala questi file — i metadati vanno inseriti manualmente in `raw_pdf_manual.json`. Non escluderli silenziosamente.

> ⚠️ **Deduplicazione cross-stream:** un PDF manuale potrebbe duplicare un record già presente nei database. Lo script di Fase 2 gestirà questa deduplicazione automaticamente per DOI e titolo normalizzato.

### 0.8 — Wiki System (OpenClaw)

> ⚠️ **CWD per i comandi wiki:** tutti i comandi `py wiki/scripts/wiki.py` devono essere eseguiti dalla **radice del repo** `academic-research-prisma-wiki-rag/`, non dalla cartella di lavoro della review. Se necessario, usa il path assoluto: `py <path-assoluto-repo>/wiki/scripts/wiki.py ...`

> "Stai usando il sistema wiki OpenClaw per questa ricerca? Se sì, indica il percorso assoluto della cartella wiki workspace (es. `C:/Users/nome/wiki-data/ricerca` o il path configurato in `wiki.config.json`)"

Se sì:
- Salva il percorso in `prisma_state.json` come `wiki_workspace`
- Verifica che il path esista eseguendo: `py wiki/scripts/wiki.py query --workspace [path] --q "test" --k 1`
- Se funziona, informa: *"Wiki connesso. Lo userò per: (1) cercare conoscenza pre-esistente prima delle query PRISMA, (2) esportare i paper inclusi dopo la Fase 4, (3) esportare la sintesi dopo la Fase 6."*
- Se non funziona, documenta `wiki_workspace: null` e procedi senza integrazione wiki

### 0.8b — Riepilogo e conferma
```
CONFIGURAZIONE REVIEW
─────────────────────────────────────
Domanda:     [domanda + sub-domande RQ1/RQ2/...]
PICO:        P=[...] I=[...] C=[...] O=[...]
Anni:        [da] – [a]
Ambito:      [disciplina]
Database:    [lista]
Tipo pub.:   [peer-reviewed / preprint / tutti]
Lingua:      [lingue]
Min cit.:    [N o nessuna]
─────────────────────────────────────
```
Chiedi conferma. Poi aggiorna `prisma_state.json` e `prisma_log.md`.

---

## FASE 1 — Identification

### 1.0 — Pre-search wiki context (se wiki_workspace è configurato)

Prima di formulare le query per i database, interroga il wiki per surfaceare conoscenza già presente sul tema:

```bash
py wiki/scripts/wiki.py query --workspace [wiki_workspace] --q "[domanda di ricerca principale]" --k 5
```

Se il wiki restituisce pagine rilevanti (rilevanza > 0.4):
- Usa la conoscenza esistente per **affinare le stringhe di ricerca** (es. aggiungere sinonimi già noti, escludere termini già valutati)
- Annota in `prisma_log.md` sotto "Note metodologiche": *"Conoscenza pre-esistente nel wiki: [sintesi breve delle pagine trovate]"*
- Questo **non sostituisce** la ricerca sistematica — è solo un orientamento iniziale per costruire query più precise

Se il wiki non ha pagine rilevanti: procedi normalmente, il wiki verrà popolato al termine della review.

### 1.1 — Query database (Stream 1)

Costruisci le query adattando i parametri. Lancia le ricerche in parallelo.

| Database | Tool MCP | Parametri chiave |
|----------|----------|-----------------|
| `semantic-scholar` | `paper_relevance_search` | `year="AAAA-AAAA"`, `min_citation_count=N`, `fields_of_study=[...]` |
| `arxiv` | `search_papers` | `date_from="AAAA-MM-GG"`, `categories=[...]` — ⚠️ il nome del tool varia per versione; se la call fallisce, verificare il nome esatto con `claude mcp list --verbose` |
| `pubmed` | `search_pubmed` | `"AAAA:AAAA"[Date - Publication]`, `[MeSH Terms]` |
| `eric` | `eric_advanced_search` | `query`, `rows` (max 200), `start`, `year_from`, `year_to`, `education_level`, `pub_type`, `language`, `title_only` |
| `openaire` | `openaire_search` | `query`, `year_from`, `year_to`, `country="IT"` per fonti italiane |
| `core` | `core_search` | `query`, `year_from`, `year_to`, `language="it"` — richiede `CORE_API_KEY` (free) |
| `doaj` | `doaj_search_articles` | `query`, `year_from`, `year_to`, `country_publisher="IT"` per riviste italiane |
| `zenodo` | `zenodo_search` | `query`, `year_from`, `year_to`, `resource_type="publication"` |

### ⚠️ MCP server non disponibile — gestione errori

Se un tool MCP restituisce errore o non risponde durante FASE 1:
1. **Registra 0 risultati** per quel database nella tabella FASE 1
2. **Annota in `prisma_log.md`**: "Database [nome] non disponibile in questa sessione — escluso dal corpus"
3. **Continua con gli altri database** — non bloccare il workflow
4. **Caso speciale `arxiv`**: se fallisce, valuta se i paper arxiv rilevanti sono già stati recuperati da `semantic-scholar` (che indicizza preprint arxiv). Se no, nota l'esclusione nella sezione Limitazioni del report finale.

> `arxiv` è il server con maggiore instabilità storica. Se `claude mcp list` mostra `arxiv: ✗ Failed`, non avviare la query — documenta e prosegui.

### ⚠️ ERIC — Usare sempre `rows=200` + paginazione (non il default 10)

Il tool MCP `eric_advanced_search` ha default `rows=10`. **Usare sempre `rows=200`** e iterare con `start` per coprire il corpus completo.

**Parametri chiave del tool MCP:**
| Parametro | Valore consigliato | Note |
|-----------|-------------------|------|
| `rows` | 200 | Max per call — NON lasciare il default 10 |
| `start` | 0, 200, 400, ... | Paginazione per corpus > 200 |
| `year_from` / `year_to` | es. 2020 / 2026 | Range anni nativo — no workaround OR |
| `education_level` | `"Secondary Education"` | Filtro fondamentale per RQ su secondaria |
| `pub_type` | `"Journal Articles"` | Filtra per tipo di pubblicazione |
| `title_only` | `True` | Query molto precisa solo sul titolo |

**Sintassi query**: AND, OR, NOT (maiuscolo). Stemming automatico (no asterischi).

**Strategia operativa ERIC (segui questo ordine):**

1. **Prima call esplorativa**: lancia con `rows=200`, `education_level` dal PICO, `year_from`/`year_to` → annota il totale restituito
2. **Se corpus ≤ 1.000**: pagina con il MCP tool (`start=0`, `200`, `400`, ...) — completamente gestibile
3. **Se corpus > 1.000 e ≤ 2.000**: pagina con HTTP API diretta (`rows=2000`, una sola call)
4. **Se corpus > 2.000**: usa HTTP API con `rows=2000` + `start` iterativo, oppure aggiungi filtri (`education_level`, `pub_type`) per ridurre il corpus prima di scaricare

**Esempio call ottimale per review su secondaria:**
```python
# MCP tool — usa sempre questi parametri minimi
eric_advanced_search(
    query="chatbot metacognition self-regulated learning",
    education_level="Secondary Education",
    year_from=2020,
    year_to=2026,
    rows=200,
    start=0  # poi incrementa: 200, 400, ...
)
```

**API HTTP diretta** (alternativa per corpus > 2.000 risultati):
- Endpoint: `https://api.ies.ed.gov/eric/`
- `rows` max: **2000** per call (vs 200 del MCP)
- Parametri: `search=`, `format=json`, `rows=`, `start=`, `fields=`
- Nessuna API key richiesta
- **Limitazione**: range anni non supportato nativamente → usare `(pubyear:2020 OR pubyear:2021 OR ...)`
- Rate limit: max 2–3 req/sec → `time.sleep(0.5)` tra le pagine

**Fine paginazione ERIC:** continua a paginare con `start=0, 200, 400...` finché il tool restituisce **meno di `rows` elementi** — quel è il segnale che hai raggiunto la fine del corpus. Se ricevi esattamente `rows=200` risultati, pagina ancora.

**IMPORTANTE:** Registra i **totali lordi** senza pre-filtri. Il giudizio di pertinenza appartiene alle fasi successive.

```
FASE 1 — RISULTATI IDENTIFICAZIONE (totali lordi)
────────────────────────────────────────────────────
Database         | Query usata              | Risultati lordi
─────────────────|──────────────────────────|────────────────
semantic-scholar | [query]                  | N
arxiv            | [query]                  | N
pubmed           | [query]                  | N
eric             | [query]                  | N
openaire         | [query] [country=IT]     | N
core             | [query]                  | N
doaj             | [query] [IT]             | N
zenodo           | [query]                  | N
────────────────────────────────────────────────────────────
TOTALE LORDO                                | N
```

### 1.3 — Salvataggio JSON per database (OBBLIGATORIO — prima di proseguire)

**Subito dopo aver ricevuto i risultati da ogni database**, salva i record grezzi in file JSON separati nella cartella di lavoro:

```
raw_semantic_scholar.json   ← lista di oggetti dal MCP semantic-scholar
raw_arxiv.json              ← lista di oggetti dal MCP arxiv
raw_pubmed.json             ← lista di oggetti dal MCP pubmed
raw_eric.json               ← lista di oggetti dal MCP eric
raw_openaire.json           ← lista di oggetti dal MCP openaire
raw_core.json               ← lista di oggetti dal MCP core
raw_doaj.json               ← lista di oggetti dal MCP doaj
raw_zenodo.json             ← lista di oggetti dal MCP zenodo
```

**Perché è critico:** Lo script di deduplicazione in Fase 2 legge questi file. Se non esistono, la Fase 2 non può partire e il corpus andrà perso al termine della sessione.

> ⚠️ **Cosa salvare nei file raw_\*.json:** salva sempre i record **grezzi** restituiti dall'API, non l'output testuale formattato dal tool. In particolare:
> - **OpenAIRE**: `data['response']['results']['result']` (lista record grezzi)
> - **CORE**: `data['results']` (lista record grezzi)
> - **DOAJ**: `data['results']` (lista `bibjson` objects)
> - **Zenodo**: `data['hits']['hits']` (lista record grezzi)
> - **ERIC / Semantic Scholar / PubMed / arXiv**: vedi mappatura in Fase 2
>
> Se salvi l'output testuale del tool invece dei dict, lo script di Fase 2 non troverà i campi attesi e andrà in crash.

**Come salvare con Python:**
```python
import json
# Esempio per Semantic Scholar — ripeti per ogni DB
records_ss = [...]  # risultati dal MCP tool
with open("raw_semantic_scholar.json", "w", encoding="utf-8") as f:
    json.dump(records_ss, f, ensure_ascii=False, indent=2)
```

Aggiorna `prisma_state.json` (sezione `fase1`) e `prisma_log.md` (sezione FASE 1) con la tabella e le query esatte.

### 1.5 — Stream 2: record da fonti manuali (PRISMA 2020)

Se `raw_pdf_manual.json` esiste nella cartella di lavoro, riportalo nel log separatamente dal Stream 1:

```
FASE 1 — STREAM 2 (altre fonti)
────────────────────────────────────────────────────
Fonte                    | N record
─────────────────────────|──────────────────────────
PDF trovati manualmente  | N  ← da raw_pdf_manual.json
Grey literature          | N  ← se applicabile
Referenze di altri paper | N  ← se applicabile
────────────────────────────────────────────────────
TOTALE STREAM 2          | N
```

Aggiorna `prisma_state.json` con `fase1.stream2_pdf`. Il diagramma di flusso PRISMA 2020 nel report finale riporterà i due stream separatamente (Stream 1: database, Stream 2: altre fonti).

Chiedi:
> "I numeri ti sembrano ragionevoli? Vuoi affinare qualche query prima di procedere?"

---

## FASE 2 — Screening

### 2.1 — Script Python di deduplicazione

Scrivi `prisma_screening.py` nella cartella di lavoro. Lo script deve:

1. Leggere tutti i JSON estratti con questa mappatura per database (incluso `raw_pdf_manual.json`):
   - **Semantic Scholar**: `title`, `externalIds.DOI`, `year`, `abstract`, `authors[].name`
   - **arXiv**: `title`, `doi` (fallback: `id`), `published[:4]`, `summary`, `authors[].name`
   - **PubMed**: `Title`, `DOI`, `PubDate`, `Abstract`, `Authors[].name`
   - **ERIC**: `title`, `doi` (o `id` come fallback), `pubyear`, `description` (abstract), `author[]`, `subject[]`, `source` (rivista)
   - **OpenAIRE**: `title`, `doi`, `year`, `abstract`, `authors[]`
   - **CORE**: `title`, `doi`, `yearPublished`, `abstract`, `authors[].name`, `journals[0].title`
   - **DOAJ**: `bibjson.title`, `bibjson.identifier[doi]`, `bibjson.year`, `bibjson.abstract`, `bibjson.author[].name`
   - **Zenodo**: `metadata.title`, `metadata.doi`, `metadata.publication_date[:4]`, `metadata.description`, `metadata.creators[].name`
   - **PDF manuali**: `title`, `doi`, `year`, `abstract`, `authors[]`, `source_db: "pdf_manual"`, `file` — già normalizzati da `extract_pdf_metadata.py`
2. Normalizzare verso: `title`, `doi`, `year`, `abstract`, `authors`, `source_db`.
3. Deduplicare per DOI (lowercase) e poi per titolo normalizzato (alfanumerico, lowercase).
4. Applicare i filtri concordati (anno, lingua, tipo pub.).
5. Salvare in `screening_prisma.json`.
6. Stampare il riepilogo numerico.

```
FASE 2 — SCREENING
────────────────────────────────────────
Totale lordo scaricato:        N
- Duplicati rimossi:          -N
────────────────────────────────────────
TOTALE dopo deduplicazione:    N
- Esclusi per anno:           -N
- Esclusi per altri filtri:   -N
────────────────────────────────────────
TOTALE dopo screening:         N
```

Aggiorna `prisma_state.json` (sezione `fase2`) e `prisma_log.md` (sezione FASE 2).

> ⚠️ **Corpus zero:** se `TOTALE dopo screening = 0`, **interrompi il workflow**. Non procedere alla Fase 3 con corpus vuoto. Avvisa l'utente e chiedi di: (1) rivedere i criteri di esclusione applicati, (2) ampliare le query di ricerca, (3) estendere il range di anni. Documenta nel `prisma_log.md` il motivo dell'arresto.

Chiedi:
> "Vuoi rivedere qualche categoria di esclusione o possiamo passare alla Fase 3?"

---

## FASE 3 — Eligibility

> ⚠️ **Limite pratico importante:** In questa fase si lavora esclusivamente sugli **abstract** disponibili nel JSON prodotto dalla Fase 2. Non vi è accesso automatico ai full-text dei paper. L'etichetta "full-text" nella terminologia PRISMA si riferisce allo standard metodologico (idealmente dovresti leggere il testo completo); nella pratica di questa skill, la valutazione avviene sull'abstract. Documenta questa limitazione nella sezione "Note metodologiche" del `prisma_log.md`.

### 3.1 — Definizione criteri (PRIMA di leggere)

```
CRITERI DI INCLUSIONE:
- [ ] Studia specificamente [popolazione da PICO]
- [ ] Misura [outcome da PICO]
- [ ] Periodo: [anni]  Lingua: [lingue]
- [ ] [criteri aggiuntivi]

CRITERI DI ESCLUSIONE:
- [ ] Solo abstract senza full-text
- [ ] Campione N < [soglia]
- [ ] Non misura l'outcome di interesse
- [ ] [criteri aggiuntivi]
```

### 3.2 — Revisione paper con annotazione

> ⚠️ **Paper senza abstract:** Per atti di convegno, paper pre-2000 o record incompleti, l'abstract può essere assente. In questo caso: (1) valuta su titolo + autori + rivista/contesto; (2) se l'informazione è insufficiente per decidere, classifica come "abstract non disponibile — escluso per impossibilità di verifica criteri" e documenta nel `prisma_log.md`; (3) per il RAG, indicizza comunque usando titolo + tutti i campi estratti disponibili — un chunk parziale è meglio di nessun chunk.

> ⚠️ **Confirmation bias:** Applica i criteri in modo simmetrico. Non escludere paper che contraddicono l'ipotesi iniziale applicando criteri più severi rispetto ai paper che la confermano. Per ogni esclusione, documenta il criterio specifico violato — questo rende la decisione verificabile.

Per ogni paper **escluso** documenta il motivo nel `prisma_log.md` con il criterio esatto violato (es. "escluso: campione N < 20, criterio C3"). Per ogni paper **incluso**, annota già qui i punti salienti (metodologia, campione, risultati chiave) — serviranno per il RAG e la sintesi.

```
FASE 3 — ELIGIBILITY
────────────────────────────────────────
Full-text valutati:            N
- Esclusi (no full-text):     -N
- Esclusi (popolazione):      -N
- Esclusi (outcome):          -N
- Esclusi (altro: [motivo]):  -N
────────────────────────────────────────
TOTALE paper eleggibili:       N
```

Aggiorna `prisma_state.json` (sezione `fase3`) e `prisma_log.md` (sezione FASE 3).

Chiedi:
> "Vuoi procedere con l'estrazione dati da questi N paper?"

---

## FASE 4 — Inclusion ed Estrazione Dati

### 4.1 — Tabella di estrazione

Chiedi all'utente quali campi aggiuntivi vuole, poi costruisci la tabella con questi campi obbligatori:

```
| # | Autore/Anno | Titolo | DOI | N campione | Paese/Contesto | Livello scolastico | Design studio | Framework teorico | Tipo tecnologia | Durata intervento | Strumenti di misura | Outcome misurato | Effect Size (d/η²/r) | IC 95% | p-value | Risultati chiave | Qualità studio | Limitazioni | RQ risposta |
```

**Campi critici per il pilot study — non omettere:**
- **Framework teorico**: es. SRL/Zimmerman, SDT, TAM/UTAUT, Cognitive Load Theory
- **Tipo tecnologia**: es. chatbot, ITS, app mobile, LMS, VR
- **Durata intervento**: in settimane o ore totali
- **Strumenti di misura**: elenca tutti gli strumenti usati (es. MSLQ, TAM, NASA-TLX, test ad hoc)
- **Effect Size**: estrai d di Cohen, η², r o Hedges' g — se non riportato esplicitamente, calcola da F, t o χ² quando possibile
- **IC 95%**: intervalli di confidenza dell'effect size se disponibili
- **Qualità studio**: valuta con un punteggio sintetico (vedi 4.1b)

Il campo **RQ risposta** indica quale sub-domanda (RQ1, RQ2...) il paper aiuta a rispondere.

### 4.1b — Quality Assessment (obbligatorio)

Per ogni paper incluso, assegna un punteggio di qualità sintetico usando questi criteri:

| Criterio | Sì (1) | No (0) |
|---|---|---|
| Campione randomizzato o gruppi equivalenti al baseline | | |
| N ≥ 30 per gruppo | | |
| Misure validate (non ad hoc) | | |
| Effect size riportato | | |
| Follow-up o misure ripetute | | |
| Limitazioni dichiarate dagli autori | | |

**Punteggio totale /6** → registra nella colonna "Qualità studio" della tabella.
- 5–6: evidenza forte
- 3–4: evidenza moderata
- 0–2: evidenza debole (segnala all'utente — peso ridotto nella sintesi)

**Per studi qualitativi** (interviste, focus group, etnografia): usa i criteri CASP (Critical Appraisal Skills Programme) semplificati:

| Criterio CASP | Sì (1) | No (0) |
|---|---|---|
| Obiettivo chiaramente formulato | | |
| Metodo qualitativo appropriato alla domanda | | |
| Partecipanti selezionati in modo giustificato | | |
| Raccolta dati sistematica (es. traccia intervista documentata) | | |
| Analisi rigorosa (es. saturazione tematica, triangolazione) | | |
| Riflessività del ricercatore dichiarata | | |

**Punteggio CASP /6** → stessa scala (5–6 forte, 3–4 moderata, 0–2 debole). Registra nella stessa colonna "Qualità studio" con indicazione *(CASP)*.

### 4.2 — Aggiornamento progressivo dei file (dopo OGNI paper)

Per **ogni paper incluso**, aggiorna subito (non alla fine):

1. **`prisma_state.json`** — aggiungi l'oggetto paper nella lista `fase4.paper_inclusi`:
   ```json
   { "n": 1, "autore_anno": "Smith 2022", "doi": "...", "qualita": 4, "rq": "RQ1" }
   ```
2. **`prisma_synthesis.md`** — aggiungi il contributo del paper ai temi emergenti e alla risposta provvisoria
3. **`prisma_bibliography.md`** — aggiungi la scheda bibliografica annotata

### 4.2b — Checkpoint ogni 10 paper (anti-saturazione contesto)

Dopo ogni 10 paper processati, esegui questo controllo:
```
CHECKPOINT Fase 4 — Paper [N1]–[N2]
─────────────────────────────────────────────
Paper processati finora: [N]
File aggiornati: prisma_state.json ✓ / prisma_synthesis.md ✓ / prisma_bibliography.md ✓
Sezione "OUTPUT PER PILOT STUDY" aggiornata: ✓
  → Effect size aggregati: [ultimo valore calcolato o "in accumulo"]
  → Framework dominante finora: [es. SRL/Zimmerman]
  → Strumenti più usati finora: [lista parziale]
Temi emergenti finora: [lista breve]
Risposta provvisoria RQ1: [frase]
Risposta provvisoria RQ2: [frase]
─────────────────────────────────────────────
Confermi di proseguire con i prossimi 10 paper?
```
Aspetta conferma utente prima di continuare.

> ⚠️ **La sezione "OUTPUT PER PILOT STUDY" di `prisma_synthesis.md` è il meccanismo di handoff verso `educational-pilot-design`.** Aggiornarla paper per paper (o almeno a ogni checkpoint) è obbligatorio — se viene lasciata vuota, la skill `educational-pilot-design` non riceve le informazioni bibliografiche e deve chiederle manualmente. Questo garantisce che i file siano salvati anche se la sessione si interrompe.

### 4.3 — Salvataggio finale ed export `eligibility_prisma.json`

Aggiorna `prisma_state.json` (sezione `fase4`) e `prisma_log.md` (sezione FASE 4) con la tabella completa.

**Crea `eligibility_prisma.json`** (o `extraction_table.json` — entrambi i nomi sono accettati da `hybrid-rag`) — lista JSON con i record completi dei soli paper inclusi. Questo è il file ottimale per il RAG (ha abstract + tutti i campi estratti). Struttura di ogni oggetto:

```json
{
  "titolo": "...", "autori": "...", "anno": "2022", "doi": "...", "source_db": "...",
  "abstract": "...",
  "design_studio": "...", "framework_teorico": "...", "tipo_tecnologia": "...",
  "campione": "...", "durata_intervento": "...", "strumenti_misura": "...",
  "outcome": "...", "effect_size": "d=0.61", "ic_95": "[0.23, 0.99]",
  "qualita_studio": "4", "risultati_chiave": "...", "limitazioni": "...",
  "rq_risposta": "RQ1", "annotazione": "..."
}
```

Per l'abstract: recuperalo da `screening_prisma.json` cercando per DOI o titolo normalizzato. Se non disponibile, usa quello annotato in `prisma_bibliography.md`.

Chiedi:
> "L'estrazione è completa. Vuoi procedere con la costruzione del database RAG per generare il report finale?"

---

## FASE 5 — Costruzione del Database RAG (OBBLIGATORIO)

Il RAG è il meccanismo principale per generare il report finale senza saturare il contesto. **Non è opzionale**: con più di 10 paper inclusi è indispensabile.

**Usa la skill `hybrid-rag`** tramite il tool `Skill` di Claude Code (sostituisce il vecchio `build_rag_db.py`):

1. Invoca la skill `hybrid-rag`.
2. Se `hybrid_rag.py` non esiste nella cartella corrente, la skill richiede di usare il tool **Read** su `~/.claude/skills/hybrid-rag/hybrid_rag_template.py` e il tool **Write** per creare `./hybrid_rag.py` — seguire quella procedura.
3. I comandi da eseguire sono:
   ```bash
   py hybrid_rag.py init
   py hybrid_rag.py index-prisma eligibility_prisma.json
   ```
   `eligibility_prisma.json` (creato in Fase 4) contiene i record completi con abstract — è il file ottimale per il RAG. Se non esiste ancora, usa `screening_prisma.json` come fallback (ha abstracts ma include anche paper esclusi).

   > ⚠️ **Fallback su `screening_prisma.json`:** questo file include i paper non eleggibili (esclusi in Fase 3). Se indicizzato nel RAG, il modello potrebbe recuperarli e citarli nel report finale, violando il guardrail anti-allucinazione della Fase 6. Segnala esplicitamente all'utente che si sta usando il fallback e valuta se filtrare il file prima dell'indicizzazione (rimuovendo i record con `included: false` se presenti).

4. Se esiste `pdf_manuali/` nella cartella di lavoro (Fase 0.7), indicizzala:
   ```bash
   py hybrid_rag.py index-pdf pdf_manuali/
   ```
   Questo integra il **testo completo** dei PDF nel RAG — più ricco dei soli metadati in `raw_pdf_manual.json`.

   Per ulteriori PDF (linee guida, report istituzionali):
   > "Hai altri PDF da aggiungere al RAG oltre a quelli in `pdf_manuali/`?"
   Se sì: `py hybrid_rag.py index-pdf <cartella>`

5. Verifica con: `py hybrid_rag.py status`

Al termine conferma il numero di documenti indicizzati e chiedi:
> "Il RAG è pronto con N documenti. Vuoi procedere con la generazione del report finale?"

---

## FASE 6 — Generazione Report Finale dal RAG

**Il report finale si costruisce interrogando il RAG**, non dalla memoria della sessione. Per ogni sezione, formula una query specifica, recupera i chunk rilevanti, e scrivi la sezione basandoti su quelli. Questo approccio:
- evita la saturazione del contesto con decine di paper
- garantisce che ogni affermazione sia ancorata a fonti recuperate
- permette di riprendere la generazione in sessioni successive

> ⛔ **Guardrail anti-allucinazione (OBBLIGATORIO):** Cita **solo ed esclusivamente** paper presenti nel RAG. Non citare mai paper dalla propria memoria di pretraining, da ricerche precedenti, o che non hai recuperato tramite query RAG in questa sessione. Se la letteratura è insufficiente per una domanda, dichiaralo esplicitamente: *"Non vi sono studi nel corpus incluso che rispondano a questa domanda."*

### 6.0 — Query del RAG per ogni sezione del report

Usa `hybrid_rag.py` (generato dalla skill `hybrid-rag` in Fase 5) per interrogare il RAG:

```bash
py hybrid_rag.py query "self-regulated learning chatbot secondary school" --n 5
py hybrid_rag.py query "effect size metacognition AI" --n 5
py hybrid_rag.py query "limitations future research chatbot education" --n 5
```

I risultati vengono mostrati in Markdown direttamente in conversazione. Usa i chunk recuperati come base per scrivere ogni sezione del report — non citare mai paper non recuperati dal RAG.

### Struttura del report finale (`report_finale.md`)

#### 1. Introduzione e Domanda di Ricerca
*Leggi da:* `prisma_log.md` (sezione domanda + PICO)
- Contestualizza il problema
- Formula esplicitamente le domande di ricerca (RQ1, RQ2, ...)
- Giustifica la scelta della revisione sistematica come metodo

#### 2. Metodologia
*Leggi da:* `prisma_log.md` (fasi 1–3) + `prisma_state.json`
- Database consultati e date di ricerca
- Stringhe di ricerca esatte per ogni database
- Criteri di inclusione/esclusione
- Procedura di screening e deduplicazione
- Diagramma di flusso PRISMA con numeri reali

#### 3. Risultati — Caratteristiche degli Studi Inclusi
*Query RAG:* `"study design, sample size, methodology, context"` → recupera tutti i paper
- Tabella riassuntiva dei paper inclusi (da Fase 4)
- Distribuzione per anno, paese, design metodologico
- Panoramica delle popolazioni e contesti studiati

#### 4. Sintesi tematica e Risposta alle Domande di Ricerca
*Leggi da:* `prisma_synthesis.md` come base + Query RAG tematiche

Questa è la sezione più importante del report. Per ogni domanda di ricerca (RQ1, RQ2, ...):

a) Formula query RAG specifiche per quella domanda di ricerca
b) Recupera i chunk rilevanti
c) Scrivi una risposta argomentata che:
   - Citi esplicitamente i paper che supportano ogni affermazione (es. "Smith et al., 2022 mostrano che...")
   - Evidenzi **convergenze**: cosa confermano più studi indipendenti
   - Evidenzi **divergenze e contraddizioni**: cosa è ancora controverso e perché
   - Formuli la risposta in modo onesto, anche quando non è univoca: "I risultati suggeriscono X, ma con importanti limitazioni..."
   - Distingua tra evidenze forti (più studi convergenti, campioni ampi) ed evidenze deboli (studi singoli, campioni ridotti)
   - Non ometta i risultati negativi o i fallimenti degli interventi studiati

**Regola critica:** non affermare nulla di non supportato dai paper recuperati. Se la letteratura non fornisce una risposta chiara, dichiararlo esplicitamente come gap.

#### 5. Discussione
*Query RAG:* `"limitations, future research, implications"` + `prisma_synthesis.md`
- Interpretazione complessiva dei risultati
- Implicazioni teoriche e pratiche
- Limitazioni della review (bias di pubblicazione, copertura dei database, lingue escluse)
- Direzioni per la ricerca futura

#### 6. Conclusioni
- Risposta sintetica alle domande di ricerca originali
- Contributo della review alla letteratura
- Raccomandazioni operative (se pertinenti)

#### 7. Implicazioni per la ricerca futura e handoff al pilot study
*Leggi da:* sezione "OUTPUT PER PILOT STUDY" di `prisma_synthesis.md`

Questa sezione trasforma la review in input operativo per un futuro studio empirico. Struttura:

- **Effect size atteso:** riporta il valore medio ponderato dagli studi inclusi (o d = 0.5 se evidenza debole), con motivazione. Questo è l'input diretto per la power analysis del pilot.
- **Framework teorico raccomandato:** il framework più supportato dalla letteratura inclusa.
- **Strumenti di misura raccomandati:** i 2-3 strumenti più usati negli studi di qualità ≥ 3/6, con nota sulla disponibilità di versioni italiane validate.
- **RQ candidate per il pilot:** le domande ancora aperte o coperte solo da evidenza debole.
- **Campione raccomandato:** fascia d'età, livello scolastico e contesto geografico meno studiati.
- **Durata realistica dell'intervento:** basata sulla mediana degli studi inclusi.

> **Nota:** Se si prevede di proseguire con la skill `educational-pilot-design`, questa sezione è il documento di handoff. Condividerla nella Fase 1 di quella skill permette di saltare la raccolta manuale delle informazioni bibliografiche.

#### 8. Riferimenti bibliografici annotati
*Leggi da:* `prisma_bibliography.md`

Includi la lista completa di tutti i paper inclusi, in formato bibliografico standard (APA o quello richiesto dall'utente), ciascuno seguito dalla propria annotazione critica breve. Esempio:

```
Smith, J., Brown, A., & Lee, K. (2022). Effects of chatbots on student metacognition.
*Computers & Education*, 180, 104423. https://doi.org/10.1016/j.compedu.2022.104423

> **Tipo**: quasi-sperimentale | **Campione**: 120 studenti scuola secondaria (USA)
> **Contributo**: Prima valutazione controllata dell'impatto di chatbot conversazionali
> sulla metacognizione degli studenti; effetti positivi sul self-monitoring.
> **Limitazioni**: campione convenience, durata intervento breve (4 settimane).
```

---

## Export in Word

Al termine, proponi:
> "Vuoi convertire il report in un file Word (.docx)? Posso farlo con pandoc."

Se l'utente accetta, invoca la skill **`pandoc-export`** tramite il tool `Skill` di Claude Code.

---

## Export al Wiki OpenClaw (se wiki_workspace è configurato)

Dopo la generazione del report finale, esporta la conoscenza nel wiki per **persistenza a lungo termine**: le sessioni future potranno interrogare il wiki prima di avviare una nuova ricerca (Fase 1.0), trovando già sintetizzato il lavoro svolto.

### A — Paper inclusi → Entity pages (esegui dopo Fase 4)

Per ogni paper in `eligibility_prisma.json`, crea un file `.tmp` in `wiki-works/ricerca/entities/`. Template:

```markdown
# [Autore/i Cognome (Anno)] — [Titolo breve]

**Tipo studio:** [RCT / quasi-sperimentale / qualitativo / review]
**Campione:** [N partecipanti, contesto, paese]
**Framework teorico:** [es. SRL, TAM, UDL]
**Outcome principale:** [variabile dipendente e risultato]
**Effect size:** [d/η²/r = X, IC 95%]
**Qualità studio:** [N/6 — forte/moderata/debole]
**DOI:** [doi]
**Fonte PRISMA:** [nome_progetto]
**RQ risposta:** [RQ1 / RQ2 / ...]

## Contributo principale
[2-3 frasi: cosa aggiunge alla letteratura]

## Limitazioni
[limitazioni dichiarate dagli autori]

## Annotazione critica
[perché è stato incluso, rilevanza per la review]
```

Poi esegui:
```bash
py wiki/scripts/wiki.py ingest \
  --workspace [wiki_workspace] \
  --pages [lista file .tmp separati da virgola] \
  --log "prisma-entities | [nome_progetto]"
```

> ⚠️ **Batch processing:** con molti paper, raggruppa in batch da 10 file per evitare argomenti troppo lunghi nella command line.

### B — Sintesi → Synthesis page (esegui dopo Fase 6)

Crea `wiki_synthesis_[nome_progetto].tmp` da `prisma_synthesis.md`:

```markdown
# Sintesi PRISMA — [Domanda di ricerca principale]

**Progetto:** [nome_progetto]  **Data:** [AAAA-MM-GG]  **N paper inclusi:** [N]
**Database:** [lista]  **Anni coperti:** [da–a]

## Risposta alle domande di ricerca
[RQ1: ...] [RQ2: ...]

## Convergenze principali (≥3 studi)
[temi supportati da più studi indipendenti]

## Divergenze e gap
[cosa è ancora controverso, cosa non è stato studiato]

## Effect size aggregati
| Outcome | N studi | ES medio | Qualità evidenza |

## Framework teorici dominanti
[lista con frequenza]

## Implicazioni per ricerca futura
[RQ candidate per pilot, campioni sotto-studiati, strumenti consigliati]
```

Poi esegui:
```bash
py wiki/scripts/wiki.py ingest \
  --workspace [wiki_workspace] \
  --pages wiki_synthesis_[nome_progetto].tmp \
  --log "prisma-synthesis | [nome_progetto]"
```

**Valuta §promotion:** se la sintesi è cross-dominio o citabile in ≥2 contesti diversi, promuovila da `wiki-works/ricerca/` a `wiki/` secondo i criteri del `wiki-core`.

---

## Errori da evitare

| Errore | Fix |
|--------|-----|
| PDF manuali non contati nel diagramma PRISMA | Usare sempre lo Stream 2 separato (Fase 1.5) — PRISMA 2020 richiede due stream distinti |
| PDF scannerizzati ignorati silenziosamente | Lo script segnala i file senza testo — compilare manualmente in `raw_pdf_manual.json` |
| Wiki export saltato per mancanza di tempo | Anche un batch parziale di entity pages ha valore — ogni paper esportato è conoscenza persistente |
| Wiki export fatto senza verifica del path | Testare sempre `wiki_workspace` con una query di prova prima di procedere con l'ingest |
| Saltare il Setup | Completare sempre Fase 0 prima |
| Non creare i file di persistenza subito | Creare `prisma_state.json` e `prisma_log.md` dopo la Fase 0 |
| Criteri di inclusione definiti dopo la lettura | Definire PRIMA di Fase 3 — evita bias di conferma |
| Pre-filtrare in Fase 1 come "rilevante" | Fase 1 = totali lordi; screening è Fase 2 |
| Non aggiornare i file a ogni fase | Aggiornamento progressivo — non a posteriori |
| Aggiornare `prisma_synthesis.md` solo alla fine | Aggiornare paper per paper durante la Fase 4 |
| RAG con solo abstract | Il RAG deve avere documenti ricchi (tutti i campi estratti) |
| Usare `prisma_state.json` per index-prisma | Ha solo dati minimi (no abstract) — usare `eligibility_prisma.json` (Fase 4) o `screening_prisma.json` come fallback |
| Generare il report dalla memoria della sessione | Usare sempre il RAG + i file di persistenza |
| Affermare risposte univoche non supportate | Dichiarare convergenze, divergenze e gap in modo onesto |
| Omettere la bibliografia annotata | Ogni paper incluso ha la sua scheda in `prisma_bibliography.md` |
| Ignorare duplicati cross-database | Controlla DOI e titolo normalizzato |
| Non estrarre effect size | Estrarre sempre d/η²/r dalla tabella risultati; se mancante, calcolare da F o t |
| Omettere quality assessment | Ogni paper incluso deve avere punteggio /6 — distingue evidenza forte da debole |
| Non compilare la sezione "OUTPUT PER PILOT STUDY" | Questa sezione è il handoff verso educational-pilot-design — deve essere completa prima di avviare il pilot |
| Effect size medio calcolato senza pesare la qualità | Calcola media ponderata escludendo gli studi con qualità ≤ 2/6 |
| Usare ERIC con `rows` default (10) | Specificare sempre `rows=200` + paginazione con `start` per coprire il corpus |
| Non sapere quando fermare la paginazione ERIC | Fermati quando il tool restituisce < `rows` elementi — quella è la fine del corpus |
| Non filtrare per `education_level` in ERIC | Usare `"Secondary Education"` (o altro livello da PICO) per ridurre il corpus fin dalla Fase 1 |
| Paper senza abstract esclusi senza documentazione | Classifica come "abstract non disponibile" e documenta nel log — non ignorare silenziosamente |
| Range anni in ERIC API HTTP con trattino | L'API HTTP non supporta range: usare `(pubyear:2020 OR pubyear:2021 OR ...)` — il tool MCP supporta `year_from`/`year_to` nativamente |
| Passare alla fase successiva senza ok utente | Aspetta sempre conferma esplicita |
| Non salvare JSON grezzi dopo Fase 1 | Salva immediatamente `raw_*.json` per ogni DB — lo script Fase 2 li richiede |
| MCP server non risponde durante Fase 1 | Registra 0 risultati, annota in `prisma_log.md`, continua con gli altri DB — non bloccare il workflow |
| Usare arxiv senza verificare la connessione | Arxiv ha instabilità storica — controlla `claude mcp list` prima; se ✗ Failed, documenta e usa semantic-scholar come fallback (indicizza anche i preprint arxiv) |
| Citare paper non nel RAG nel report finale | Solo paper recuperati tramite `py hybrid_rag.py query "..."` possono essere citati — mai dalla memoria del modello |
| Soglia citazioni senza disclaimer recency | Avverti sempre che paper post-2022 sono penalizzati ingiustamente; documenta nella metodologia |
| Esclusioni Fase 3 senza criterio esplicito | Ogni esclusione deve citare il criterio violato per nome (es. "C3: campione < 20") |
| Aggiornare `prisma_state.json` solo alla fine Fase 4 | Aggiornare dopo ogni singolo paper — il checkpoint ogni 10 paper garantisce la persistenza |
