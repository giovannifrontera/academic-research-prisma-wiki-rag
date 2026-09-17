"""Cross-encoder reranking per i risultati di ricerca vettoriale.

Secondo stadio opzionale: la ricerca vettoriale (bi-encoder BGE-M3) recupera
candidati veloci ma approssimati; il cross-encoder rilegge query e candidato
insieme e riordina per rilevanza reale. Stesso vendor BGE dell'embedder in
uso, per coerenza multilingue IT/EN.
"""

import os
import fnmatch
import logging

_model = None
_model_name = None

DEFAULT_MODEL = "BAAI/bge-reranker-v2-m3"


def _load_reranker(model_name: str = DEFAULT_MODEL):
    global _model, _model_name
    if _model is not None and _model_name == model_name:
        return _model
    os.environ.setdefault("TRANSFORMERS_VERBOSITY", "error")
    os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
    from sentence_transformers import CrossEncoder
    _model = CrossEncoder(model_name)
    _model_name = model_name
    return _model


def rerank(query: str, candidates: list[dict], top_k: int = None,
           text_key: str = "chunk_text", model_name: str = DEFAULT_MODEL) -> list[dict]:
    """Riordina candidates per rilevanza cross-encoder rispetto a query.

    candidates: lista di dict contenenti almeno text_key. Ritorna la stessa
    lista di dict con un campo aggiuntivo "_rerank_score", ordinata per
    score decrescente, troncata a top_k se specificato.
    """
    if not candidates:
        return []
    model = _load_reranker(model_name)
    pairs = [(query, c.get(text_key, "") or "") for c in candidates]
    scores = model.predict(pairs)
    reranked = []
    for c, s in zip(candidates, scores):
        item = dict(c)
        item["_rerank_score"] = float(s)
        reranked.append(item)
    reranked.sort(key=lambda x: x["_rerank_score"], reverse=True)
    return reranked[:top_k] if top_k else reranked


def rank_results(query: str, rows: list[dict], cfg: dict, k: int) -> list[dict]:
    """Shared CLI/HTTP ranking: full chunks, one result per page, safe fallback."""
    if k < 1:
        raise ValueError("k must be positive")
    seen = {}
    for row in sorted(rows, key=lambda r: r.get("_distance", 1.0)):
        path = row["path"]
        if not row.get("chunk_text") or any(
            fnmatch.fnmatchcase(path, p) for p in cfg.get("exclude_from_index", [])
        ):
            continue
        seen.setdefault(path, row)
    candidates = list(seen.values())
    settings = cfg.get("qdrant", {})
    if candidates and settings.get("rerank", True):
        try:
            return rerank(query, candidates, top_k=k,
                          model_name=settings.get("reranker_model", DEFAULT_MODEL))
        except Exception as exc:
            logging.getLogger(__name__).warning("Reranking failed; using vector ranking: %s", exc)
    return candidates[:k]
