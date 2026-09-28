# Changelog / Registro delle modifiche

All notable plugin changes are documented here. Versions follow Semantic Versioning.

Tutte le modifiche rilevanti del plugin sono documentate qui. Le versioni seguono Semantic Versioning.

## [1.4.1] - 2026-09-28

### English

#### Fixed

- Wiki web explorer (`wiki.py serve`) was unusable with authentication on: the auth middleware also blocked `GET /`, so the browser received `{"error":"unauthorized"}` instead of the login form. The static page is now public; graph, page, stats, lint and WebSocket routes stay protected.
- Removed the shared default password `changeme`: without `WIKI_PASSWORD` or a configured password, a random password is generated per run and printed to the terminal. Password check is now constant-time.
- The page detail panel no longer renders YAML frontmatter as body text.

#### Documentation

- Documented the wiki web explorer (start, login, graph, page detail, stats, API and security) with screenshots in `wiki/README.md`, and linked it from the main README.

### Italiano

#### Corretto

- L'explorer web del wiki (`wiki.py serve`) era inutilizzabile con l'autenticazione attiva: il middleware bloccava anche `GET /` e il browser riceveva `{"error":"unauthorized"}` invece del form di login. La pagina statica è ora pubblica; grafo, pagine, statistiche, lint e WebSocket restano protetti.
- Eliminata la password predefinita condivisa `changeme`: senza `WIKI_PASSWORD` o password configurata, a ogni avvio ne viene generata una casuale stampata nel terminale. Confronto password a tempo costante.
- Il pannello di dettaglio non mostra più il frontmatter YAML come testo della pagina.

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

[1.4.1]: https://github.com/giovannifrontera/academic-research-prisma-wiki-rag/releases/tag/v1.4.1
[1.4.0]: https://github.com/giovannifrontera/academic-research-prisma-wiki-rag/releases/tag/v1.4.0
[1.3.0]: https://github.com/giovannifrontera/academic-research-prisma-wiki-rag/releases/tag/v1.3.0
[1.2.0]: https://github.com/giovannifrontera/academic-research-prisma-wiki-rag/releases/tag/v1.2.0
