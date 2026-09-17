"""Operazioni Qdrant per il wiki system.

Stessa interfaccia pubblica di wiki_lancedb.py (che sostituisce): get_db,
ensure_table, upsert, promote_staging, rollback_staging, query_similar,
find_semantic_duplicates, detect_renames. I chiamanti (wiki_workflows,
wiki_graph, wiki_server, wiki_check_setup) non cambiano logica, solo import.

Qdrant gira in modalità embedded locale (client Python con path su disco,
nessun server esterno da installare) — stessa esperienza zero-setup di
LanceDB locale.
"""

import os
import time
import uuid
import hashlib
from qdrant_client import QdrantClient, models

VECTOR_SIZE = 1024  # BAAI/bge-m3
_ID_NAMESPACE = uuid.UUID("6f6a6f1e-6e62-4f2a-9b1a-2c9e6a7c9c11")


def _point_id(table_name: str, path: str, chunk_id: int) -> str:
    """Qdrant richiede id int o UUID; deriva un UUID deterministico da path+chunk_id
    così un upsert con lo stesso path/chunk_id sovrascrive il punto esistente."""
    return str(uuid.uuid5(_ID_NAMESPACE, f"{table_name}:{path}:{chunk_id}"))


def get_db(qdrant_path: str):
    os.makedirs(qdrant_path, exist_ok=True)
    return QdrantClient(path=qdrant_path)


class _Collection:
    """Wrapper minimale che replica la porzione di API lancedb.Table usata
    dal resto del codebase (.to_pandas(), .delete(filter_str))."""

    def __init__(self, db: QdrantClient, name: str):
        self.db = db
        self.name = name

    def to_pandas(self):
        import pandas as pd
        # ponytail: forza le stringhe object-dtype invece del backend pyarrow
        # (default pandas >= 3.0) — in questo stack, costruire un Index di
        # colonne stringa via pyarrow dopo che torch/sklearn hanno inizializzato
        # i loro runtime nativi causa una access violation su Windows (osservato
        # durante l'esecuzione della test suite completa). Nessun impatto
        # funzionale: qui servono solo confronti/filtri su stringhe Python.
        pd.set_option("future.infer_string", False)
        rows = _scroll_all(self.db, self.name)
        if not rows:
            return pd.DataFrame(columns=["path", "chunk_id", "chunk_text",
                                          "content_hash", "page_hash", "vector",
                                          "last_embedded"])
        return pd.DataFrame(rows)

    def delete(self, filter_str: str) -> None:
        """Supporta solo il pattern usato dal codebase: "path = '...'" """
        path = _parse_path_eq_filter(filter_str)
        self.db.delete(
            self.name,
            points_selector=models.FilterSelector(
                filter=models.Filter(must=[
                    models.FieldCondition(key="path", match=models.MatchValue(value=path))
                ])
            ),
        )

    def add(self, rows: list[dict]) -> None:
        _add_rows(self.db, self.name, rows)


def _parse_path_eq_filter(filter_str: str) -> str:
    # filter_str è sempre "path = '<valore con doppio apice escaped>'" (vedi wiki_lancedb._q)
    start = filter_str.index("'") + 1
    end = filter_str.rindex("'")
    return filter_str[start:end].replace("''", "'")


def _collection_exists(db: QdrantClient, name: str) -> bool:
    return db.collection_exists(name)


# Alias pubblico: usato da wiki_check_setup.py per verificare lo stato del DB
# senza crearlo implicitamente (a differenza di ensure_table).
collection_exists = _collection_exists


def count_rows(db: QdrantClient, table_name: str = "wiki_pages") -> int:
    if not _collection_exists(db, table_name):
        return 0
    return db.count(table_name, exact=True).count


class _TableList:
    def __init__(self, names: list[str]):
        self.tables = names


def list_tables(db: QdrantClient) -> _TableList:
    return _TableList([c.name for c in db.get_collections().collections])


def _clear_collection(db: QdrantClient, table_name: str) -> None:
    """Svuota una collection lasciandola esistente (schema invariato).

    Preferito a delete_collection: in modalità embedded locale su Windows
    il file storage.sqlite della collection a volte resta lockato e non
    viene rimosso, per cui una create_collection successiva con lo stesso
    nome ririaggancia i dati vecchi invece di ripartire vuota.
    """
    if _collection_exists(db, table_name):
        db.delete(table_name, points_selector=models.FilterSelector(filter=models.Filter()))


def drop_table(db: QdrantClient, table_name: str) -> None:
    _clear_collection(db, table_name)


def ensure_table(db: QdrantClient, table_name: str = "wiki_pages") -> _Collection:
    if not _collection_exists(db, table_name):
        db.create_collection(
            table_name,
            vectors_config=models.VectorParams(size=VECTOR_SIZE, distance=models.Distance.COSINE),
        )
    return _Collection(db, table_name)


def _scroll_all(db: QdrantClient, table_name: str) -> list[dict]:
    if not _collection_exists(db, table_name):
        return []
    rows = []
    offset = None
    while True:
        points, offset = db.scroll(table_name, limit=1000, offset=offset, with_vectors=True)
        for p in points:
            row = dict(p.payload)
            row["vector"] = p.vector
            rows.append(row)
        if offset is None:
            break
    return rows


def _add_rows(db: QdrantClient, table_name: str, rows: list[dict]) -> None:
    if not rows:
        return
    if not _collection_exists(db, table_name):
        db.create_collection(
            table_name,
            vectors_config=models.VectorParams(size=VECTOR_SIZE, distance=models.Distance.COSINE),
        )
    points = []
    for r in rows:
        payload = {k: v for k, v in r.items() if k != "vector"}
        points.append(models.PointStruct(
            id=_point_id(table_name, r["path"], r["chunk_id"]),
            vector=r["vector"],
            payload=payload,
        ))
    db.upsert(table_name, points=points)


def _chunks_to_rows(path: str, chunks: list[dict]) -> list[dict]:
    return [{
        "path": path,
        "chunk_id": c["chunk_id"],
        "chunk_text": c["chunk_text"],
        "content_hash": c["content_hash"],
        "page_hash": c["page_hash"],
        "vector": [float(v) for v in c["vector"]],
        "last_embedded": time.time(),
    } for c in chunks]


def upsert(db: QdrantClient, path: str, chunks: list[dict], table_name: str = "wiki_pages") -> None:
    """Cancella tutti i chunk esistenti per path, poi inserisce i nuovi."""
    if _collection_exists(db, table_name):
        db.delete(
            table_name,
            points_selector=models.FilterSelector(
                filter=models.Filter(must=[
                    models.FieldCondition(key="path", match=models.MatchValue(value=path))
                ])
            ),
        )
    rows = _chunks_to_rows(path, chunks)
    _add_rows(db, table_name, rows)


def promote_staging(db: QdrantClient) -> None:
    """Promuove staging_wiki_pages → wiki_pages e svuota staging."""
    if not _collection_exists(db, "staging_wiki_pages"):
        return
    rows = _scroll_all(db, "staging_wiki_pages")
    if not rows:
        _clear_collection(db, "staging_wiki_pages")
        return
    paths = {r["path"] for r in rows}
    if _collection_exists(db, "wiki_pages"):
        for path in paths:
            db.delete(
                "wiki_pages",
                points_selector=models.FilterSelector(
                    filter=models.Filter(must=[
                        models.FieldCondition(key="path", match=models.MatchValue(value=path))
                    ])
                ),
            )
    _add_rows(db, "wiki_pages", rows)
    _clear_collection(db, "staging_wiki_pages")


def rollback_staging(db: QdrantClient) -> None:
    """Svuota staging senza toccare wiki_pages."""
    _clear_collection(db, "staging_wiki_pages")


def query_similar(db: QdrantClient, vector: list[float], k: int = 5, path_prefix: str = None) -> list[dict]:
    if not _collection_exists(db, "wiki_pages"):
        return []
    limit = k * 5 if path_prefix else k
    result = db.query_points("wiki_pages", query=vector, limit=limit, with_payload=True)
    rows = []
    for p in result.points:
        if path_prefix and not p.payload.get("path", "").startswith(path_prefix):
            continue
        row = dict(p.payload)
        row["_distance"] = 1.0 - p.score  # coerente con la convenzione LanceDB (0=identico)
        rows.append(row)
        if len(rows) >= k:
            break
    return rows


def find_semantic_duplicates(
    db: QdrantClient,
    auto_threshold: float = 0.90,
    warn_threshold: float = 0.75,
) -> list[dict]:
    """
    Trova coppie di pagine semanticamente simili confrontando i vettori chunk_id==0.
    Esclude le pagine wiki/ (identity layer) dal confronto.
    Ritorna lista ordinata per similarity decrescente con campo action:
      'auto_merge' se similarity >= auto_threshold
      'warn'       se warn_threshold <= similarity < auto_threshold
    """
    import numpy as np

    rows = _scroll_all(db, "wiki_pages")
    if not rows:
        return []

    seen_paths = set()
    paths = []
    vectors = []
    for r in rows:
        if r["chunk_id"] != 0:
            continue
        if r["path"].startswith("wiki/"):
            continue
        if r["path"] in seen_paths:
            continue
        seen_paths.add(r["path"])
        paths.append(r["path"])
        vectors.append(r["vector"])

    if len(paths) < 2:
        return []

    vectors = np.array(vectors, dtype=np.float32)
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    norms = np.where(norms == 0, 1.0, norms)
    vectors = vectors / norms

    sim_matrix = vectors @ vectors.T

    results = []
    n = len(paths)
    for i in range(n):
        for j in range(i + 1, n):
            sim = float(sim_matrix[i, j])
            if sim >= auto_threshold:
                results.append({
                    "page_a": paths[i],
                    "page_b": paths[j],
                    "similarity": round(sim, 4),
                    "action": "auto_merge",
                })
            elif sim >= warn_threshold:
                results.append({
                    "page_a": paths[i],
                    "page_b": paths[j],
                    "similarity": round(sim, 4),
                    "action": "warn",
                })

    return sorted(results, key=lambda x: x["similarity"], reverse=True)


def detect_renames(db: QdrantClient, filesystem_paths: set[str], workspace: str) -> list[dict]:
    """Confronta Qdrant vs filesystem per rilevare file rinominati.

    filesystem_paths: percorsi assoluti. Li converte in relativi per confrontarli
    con i path del DB (sempre relativi a workspace).
    """
    rows = _scroll_all(db, "wiki_pages")
    if not rows:
        return []

    df0 = [r for r in rows if r["chunk_id"] == 0]
    db_paths = {r["path"] for r in df0}

    abs_to_rel = {
        p: os.path.relpath(p, workspace).replace("\\", "/")
        for p in filesystem_paths
    }
    rel_fs_paths = set(abs_to_rel.values())

    only_in_db = db_paths - rel_fs_paths
    only_in_fs = rel_fs_paths - db_paths

    db_hash_to_path = {r["page_hash"]: r["path"] for r in df0 if r["path"] in only_in_db}

    rel_to_abs = {v: k for k, v in abs_to_rel.items()}
    renames = []
    for rel_path in only_in_fs:
        abs_path = rel_to_abs.get(rel_path, rel_path)
        try:
            with open(abs_path, encoding="utf-8") as f:
                content = f.read()
            h = hashlib.sha256(content.encode()).hexdigest()
            if h in db_hash_to_path:
                renames.append({"old_path": db_hash_to_path[h], "new_path": rel_path})
        except OSError:
            pass
    return renames
