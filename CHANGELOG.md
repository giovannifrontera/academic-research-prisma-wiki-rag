# Changelog / Registro delle modifiche

All notable plugin changes are documented here. Versions follow Semantic Versioning.

Tutte le modifiche rilevanti del plugin sono documentate qui. Le versioni seguono Semantic Versioning.

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

[1.2.0]: https://github.com/giovannifrontera/academic-research-prisma-wiki-rag/releases/tag/v1.2.0
