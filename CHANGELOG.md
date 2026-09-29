# Changelog / Registro delle modifiche

All notable plugin changes are documented here. Versions follow Semantic Versioning.

Tutte le modifiche rilevanti del plugin sono documentate qui. Le versioni seguono Semantic Versioning.

## [1.4.4] - 2026-09-29

### English

#### Added

- `core_export` and `semantic_scholar_export` download every matching record (Semantic Scholar: first 1,000) straight to a `raw_*.json` file and return only the counts, so bulk downloads use the configured API key (which reaches only the MCP server, not the shell) and records never pass through the conversation. Pages already downloaded are kept if a later page fails.

#### Changed

- CORE records drop `fullText` and `references` (~3-4k tokens each, unused for screening); CORE and Semantic Scholar retry `429` responses up to three times, honouring `Retry-After`.
- The review skill uses the export tools for CORE and Semantic Scholar and no longer writes scripts that call those APIs.

### Italiano

#### Aggiunto

- `core_export` e `semantic_scholar_export` scaricano tutti i record (Semantic Scholar: primi 1.000) direttamente in un file `raw_*.json` e restituiscono solo i conteggi: il download completo usa la chiave configurata (che arriva solo al server MCP, non alla shell) e i record non passano dalla conversazione. Le pagine già scaricate si conservano se una pagina successiva fallisce.

#### Modificato

- I record CORE non includono più `fullText` e `references` (~3-4k token ciascuno, inutili per lo screening); CORE e Semantic Scholar ritentano fino a tre volte le risposte `429`, rispettando `Retry-After`.
- La skill di revisione usa i tool di export per CORE e Semantic Scholar e non scrive più script che chiamano quelle API.

## [1.4.3] - 2026-09-29

### English

#### Added

- API keys are asked by Claude Code when the plugin is enabled (`userConfig`: CORE, Semantic Scholar, NCBI key and NCBI email) and stored in the system keychain; change them with `/plugin configure academic-research-prisma-wiki-rag`. Environment variables remain a fallback.
- A `429` from CORE, Semantic Scholar or PubMed without a key now says how to configure it, and the review skill stops to ask the user before excluding the database.

### Italiano

#### Aggiunto

- Le chiavi API vengono chieste da Claude Code all'abilitazione del plugin (`userConfig`: chiave CORE, Semantic Scholar, NCBI ed email NCBI) e salvate nel portachiavi di sistema; si cambiano con `/plugin configure academic-research-prisma-wiki-rag`. Le variabili d'ambiente restano un'alternativa.
- Un `429` da CORE, Semantic Scholar o PubMed senza chiave ora indica come configurarla, e la skill di revisione si ferma a chiedere all'utente prima di escludere la banca dati.

## [1.4.2] - 2026-09-28

### English

#### Fixed

- OpenAIRE MCP server timed out on every request: OpenAIRE retired the legacy Search API (`/search/publications`) on 2026-05-31 and it now answers `503` after 60 s. The server now uses the Graph API v2 (`/graph/v2/researchProducts`, ~1 s per request) with the same tools and parameters; plain terms are ANDed, abstracts are cleaned of JATS markup, API error messages are reported.
- DOAJ MCP server answered `404` to every search: the query was sent as `?q=` while DOAJ takes it in the path (`/api/v4/search/articles/<query>`). Also fixed the year filter (`bibjson.year`, explicit bounds: open `*` ranges are rejected), the article country filter (`bibjson.journal.country`) and removed `sort=score` (`400`).
- ERIC and Zenodo combined plain terms with OR: "artificial intelligence e-learning higher education" matched 1,711,212 ERIC and 1,410,648 Zenodo records instead of ~2,400. Plain queries are now ANDed (as for arXiv); explicit syntax (quotes, AND/OR/NOT, fields, `-term`) passes through unchanged.

### Italiano

#### Corretto

- Il server MCP OpenAIRE andava in timeout a ogni richiesta: OpenAIRE ha dismesso la vecchia Search API (`/search/publications`) il 31/05/2026, che ora risponde `503` dopo 60 s. Il server usa ora la Graph API v2 (`/graph/v2/researchProducts`, ~1 s a richiesta) con gli stessi tool e parametri; i termini semplici sono in AND, gli abstract sono ripuliti dal markup JATS e i messaggi d'errore dell'API vengono riportati.
- Il server MCP DOAJ rispondeva `404` a ogni ricerca: la query veniva inviata come `?q=` mentre DOAJ la vuole nel percorso (`/api/v4/search/articles/<query>`). Corretti anche il filtro anno (`bibjson.year`, con limiti espliciti: gli intervalli aperti `*` sono rifiutati), il filtro paese degli articoli (`bibjson.journal.country`) ed eliminato `sort=score` (`400`).
- ERIC e Zenodo univano i termini semplici in OR: "artificial intelligence e-learning higher education" dava 1.711.212 record su ERIC e 1.410.648 su Zenodo invece di ~2.400. Ora le query semplici sono in AND (come per arXiv); la sintassi esplicita (virgolette, AND/OR/NOT, campi, `-termine`) resta invariata.

## [1.4.1] - 2026-09-28

### English

#### Fixed

- Wiki web explorer (`wiki.py serve`) was unusable with authentication on: the auth middleware also blocked `GET /`, so the browser received `{"error":"unauthorized"}` instead of the login form. The static page is now public; graph, page, stats, lint and WebSocket routes stay protected.
- Removed the shared default password `changeme`: without `WIKI_PASSWORD` or a configured password, a random password is generated per run and printed to the terminal. Password check is now constant-time.
- The page detail panel no longer renders YAML frontmatter as body text.
- `.project-state.json` advertised `paths.qdrant = database/qdrant`, a directory that is never created. New studies now record `paths.qdrant_rag` and `paths.qdrant_wiki`, as the isolated study workspace spec requires. No code read the old key, so existing studies keep working.

#### Documentation

- Documented the wiki web explorer (start, login, graph, page detail, stats, API and security) with screenshots in `wiki/README.md`, and linked it from the main README.

#### Added

- `wiki.py serve --project <study>` opens the explorer on a sealed study (study root or any subfolder), resolving `wiki-memory` from `.project-state.json` with containment checks; the header and browser tab show the study name (`study` field in `/api/graph`). One server per study.

### Italiano

#### Aggiunto

- `wiki.py serve --project <studio>` apre l'explorer su uno studio sigillato (cartella dello studio o sottocartella), ricavando `wiki-memory` da `.project-state.json` con controllo di containment; intestazione e scheda del browser mostrano il nome dello studio (campo `study` in `/api/graph`). Un server per studio.

#### Corretto

- L'explorer web del wiki (`wiki.py serve`) era inutilizzabile con l'autenticazione attiva: il middleware bloccava anche `GET /` e il browser riceveva `{"error":"unauthorized"}` invece del form di login. La pagina statica è ora pubblica; grafo, pagine, statistiche, lint e WebSocket restano protetti.
- Eliminata la password predefinita condivisa `changeme`: senza `WIKI_PASSWORD` o password configurata, a ogni avvio ne viene generata una casuale stampata nel terminale. Confronto password a tempo costante.
- Il pannello di dettaglio non mostra più il frontmatter YAML come testo della pagina.
- `.project-state.json` indicava `paths.qdrant = database/qdrant`, cartella mai creata. I nuovi studi registrano `paths.qdrant_rag` e `paths.qdrant_wiki`, come prevede la spec dello study workspace isolato. Nessun codice leggeva la vecchia chiave: gli studi esistenti continuano a funzionare.

#### Documentazione

- Documentato l'explorer web del wiki (avvio, accesso, grafo, dettaglio pagina, statistiche, API e sicurezza) con screenshot in `wiki/README.it.md`, con rimando dal README principale.

## [1.4.0] - 2026-09-28

### English

#### Added

- arXiv MCP server (`arxiv_search`, `arxiv_count`, `arxiv_get`) recovered from the unmerged `main` branch and aligned with the others: `output_format="json"` with complete records, `fulltext_url` to the open PDF (used by automatic full-text acquisition).
- PubMed MCP server (`pubmed_search`, `pubmed_count`, `pubmed_get`, `pubmed_search_pmc`) recovered and rewritten on `efetch` XML so records include full abstracts, MeSH terms, DOI and PMC ID. Optional `NCBI_API_KEY` / `NCBI_EMAIL`.

#### Fixed

- arXiv plain queries were ORed by the API ("spaced repetition" returned ~460,000 hits instead of ~900): plain terms are now ANDed, explicit arXiv syntax is passed through.

- `hybrid-rag query` cross-encoder reranking now scores the top `n_results × 3` RRF candidates instead of only the top `n_results`, so it can recover relevant papers ranked below the cut-off rather than just reordering them. Result ranks are renumbered after reranking.

### Italiano

#### Aggiunto

- Server MCP arXiv (`arxiv_search`, `arxiv_count`, `arxiv_get`) recuperato dal ramo `main` mai unito e allineato agli altri: `output_format="json"` con record completi e `fulltext_url` al PDF aperto (usato dall'acquisizione automatica del full-text).
- Server MCP PubMed (`pubmed_search`, `pubmed_count`, `pubmed_get`, `pubmed_search_pmc`) recuperato e riscritto su `efetch` XML: i record includono abstract completi, MeSH, DOI e PMC ID. `NCBI_API_KEY` / `NCBI_EMAIL` opzionali.

#### Corretto

- Le query arXiv semplici venivano interpretate in OR ("spaced repetition" dava ~460.000 risultati invece di ~900): ora i termini sono uniti in AND e la sintassi arXiv esplicita resta invariata.
- Il reranking cross-encoder di `hybrid-rag query` valuta ora i primi `n_results × 3` candidati RRF invece dei soli `n_results`: può recuperare paper rilevanti sotto la soglia invece di limitarsi a riordinarli. I rank vengono rinumerati dopo il reranking.

## [1.3.0] - 2026-09-28

### English

#### Added

- Isolated study workspace: `scripts/study_workspace.py create|inspect` creates a sealed `<study-slug>/` with its own `.project-state.json` and separate Qdrant stores (`database/qdrant-rag/`, `database/qdrant-wiki/`).
- Mandatory wiki export before Hybrid RAG indexing (explicit `--skip-wiki-export` override).
- `BAAI/bge-reranker-v2-m3` cross-encoder reranking on `hybrid-rag query`, matching the wiki.
- Best-effort open-access full-text acquisition (`skills/prisma-review/scripts/fetch_fulltext.py`) with SSRF, size and content-type guards.

#### Fixed

- Semantic Scholar MCP server imported the MCP 2.x `MCPServer` API while `requirements.txt` pins `mcp<2`: the server failed to start. Restored `FastMCP`, like the other five servers.

### Italiano

#### Aggiunto

- Study workspace isolato: `scripts/study_workspace.py create|inspect` crea una `<study-slug>/` sigillata con `.project-state.json` e Qdrant separati (`database/qdrant-rag/`, `database/qdrant-wiki/`).
- Export wiki obbligatorio prima dell'indicizzazione Hybrid RAG (override esplicito `--skip-wiki-export`).
- Reranking cross-encoder `BAAI/bge-reranker-v2-m3` anche su `hybrid-rag query`, come nel wiki.
- Acquisizione best-effort del full-text open-access (`skills/prisma-review/scripts/fetch_fulltext.py`) con controlli SSRF, dimensione e content-type.

#### Corretto

- Il server MCP Semantic Scholar importava l'API MCP 2.x `MCPServer` mentre `requirements.txt` richiede `mcp<2`: il server non partiva. Ripristinato `FastMCP`, come negli altri cinque server.

## [1.2.0] - 2026-09-17

### English

#### Added

- Real embedding/reranker diagnostic with Python, Torch/CUDA, actual devices, vector size and inference score.
- Windows and Ubuntu GitHub Actions matrix with Python 3.11 and CPU PyTorch.
- Complete MCP JSON records and pagination through `output_format="json"`, preserving text output.
- Regression tests for Qdrant, eligibility boundaries, stale deletion, BM25/RRF, reranking and MCP schemas.
- Windows/Linux environment, GPU and portable-path documentation.

#### Changed

- Migrated wiki memory from LanceDB to embedded Qdrant.
- Added `BAAI/bge-reranker-v2-m3` after BGE-M3 candidate retrieval.
- Unified CLI and HTTP ranking: exclusions, page deduplication, full-chunk reranking and vector fallback.
- Made Qdrant the default Hybrid RAG backend; ChromaDB and LanceDB remain optional.
- Pinned MCP to compatible FastMCP 1.x and declared BM25 explicitly.
- Reconciled Italian and English docs with the current Claude Code plugin.

#### Fixed

- Current `qdrant-client` API compatibility and paginated scroll.
- Zero BM25 scores no longer create false sparse ranks.
- `index-prisma` enforces the documented eligibility filename/shape contracts, rejects explicit exclusion markers and removes records absent from the current export, including an empty export.
- Windows-safe process locking, interpreter/path guidance and LF normalization.
- Consistent database closure and non-blocking FastAPI model/retrieval work.

### Italiano

#### Aggiunto

- Diagnostica reale di embedding/reranker con Python, Torch/CUDA, device, dimensione e score.
- CI su Windows e Ubuntu con Python 3.11 e PyTorch CPU.
- Record MCP JSON completi con `output_format="json"`, mantenendo il testo.
- Test per Qdrant, eligibility, record obsoleti, BM25/RRF, reranking e schemi MCP.
- Documentazione per ambiente Windows/Linux, GPU e path portabili.

#### Modificato

- Memoria wiki migrata da LanceDB a Qdrant embedded.
- Reranking `BAAI/bge-reranker-v2-m3` dopo il recupero BGE-M3.
- Ranking CLI/HTTP unificato con esclusioni, dedup pagina e fallback vettoriale.
- Qdrant predefinito nel Hybrid RAG; ChromaDB e LanceDB restano opzionali.
- MCP vincolato alla serie FastMCP 1.x compatibile e BM25 dichiarato.
- Documentazione italiana e inglese riallineata al plugin Claude Code.

#### Corretto

- Compatibilità con `qdrant-client` corrente e scroll paginato.
- I punteggi BM25 nulli non generano ranking fittizi.
- `index-prisma` applica i contratti di nome/struttura eligibility, rifiuta marker espliciti di esclusione e rimuove record fuori dall'export corrente, anche vuoto.
- Locking Windows, interprete/path, LF, chiusura database e lavoro FastAPI non bloccante.

## [1.1.2] - previous local tag / tag locale precedente

- Pre-plugin development baseline; this tag was not present on the remote when 1.2.0 was prepared.
- Baseline precedente alla conversione completa; il tag non risultava sul remoto durante la preparazione di 1.2.0.

[1.4.2]: https://github.com/giovannifrontera/academic-research-prisma-wiki-rag/releases/tag/v1.4.2
[1.4.1]: https://github.com/giovannifrontera/academic-research-prisma-wiki-rag/releases/tag/v1.4.1
[1.4.0]: https://github.com/giovannifrontera/academic-research-prisma-wiki-rag/releases/tag/v1.4.0
[1.3.0]: https://github.com/giovannifrontera/academic-research-prisma-wiki-rag/releases/tag/v1.3.0
[1.2.0]: https://github.com/giovannifrontera/academic-research-prisma-wiki-rag/releases/tag/v1.2.0
