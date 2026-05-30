"""Operazioni LanceDB per il wiki system."""

import os
import time
import hashlib
import pyarrow as pa
import lancedb


def _q(s: str) -> str:
    """Escapa gli apici singoli per i filtri LanceDB (SQL injection prevention)."""
    return s.replace("'", "''")

SCHEMA = pa.schema([
    pa.field("path", pa.string()),
    pa.field("chunk_id", pa.int32()),
    pa.field("chunk_text", pa.string()),
    pa.field("content_hash", pa.string()),
    pa.field("page_hash", pa.string()),
    pa.field("vector", pa.list_(pa.float32(), 1024)),
    pa.field("last_embedded", pa.float64()),
])


def get_db(lancedb_path: str):
    return lancedb.connect(lancedb_path)


def ensure_table(db, table_name: str = "wiki_pages"):
    existing = db.list_tables().tables
    if table_name not in existing:
        db.create_table(table_name, schema=SCHEMA)
    return db.open_table(table_name)


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


def upsert(db, path: str, chunks: list[dict], table_name: str = "wiki_pages") -> None:
    """Cancella tutti i chunk esistenti per path, poi inserisce i nuovi."""
    table = ensure_table(db, table_name)
    try:
        table.delete(f"path = '{_q(path)}'")
    except Exception:
        pass
    rows = _chunks_to_rows(path, chunks)
    if rows:
        table.add(rows)


def promote_staging(db) -> None:
    """Promuove staging_wiki_pages → wiki_pages e svuota staging."""
    existing = db.list_tables().tables
    if "staging_wiki_pages" not in existing:
        return
    staging = db.open_table("staging_wiki_pages")
    df = staging.to_pandas()
    if df.empty:
        return
    # Seleziona solo le colonne dello schema canonico per evitare mismatch
    schema_cols = [field.name for field in SCHEMA]
    df = df[[c for c in schema_cols if c in df.columns]]
    wiki = ensure_table(db, "wiki_pages")
    for path in df["path"].unique():
        try:
            wiki.delete(f"path = '{_q(path)}'")
        except Exception:
            pass
    wiki.add(df.to_dict("records"))
    try:
        db.drop_table("staging_wiki_pages")
    except Exception:
        pass


def rollback_staging(db) -> None:
    """Svuota staging senza toccare wiki_pages."""
    existing = db.list_tables().tables
    if "staging_wiki_pages" not in existing:
        return
    try:
        db.drop_table("staging_wiki_pages")
    except Exception:
        pass


def query_similar(db, vector: list[float], k: int = 5, path_prefix: str = None) -> list[dict]:
    table = ensure_table(db, "wiki_pages")
    q = table.search(vector).limit(k)
    if path_prefix:
        q = q.where(f"path LIKE '{_q(path_prefix)}%'")
    return q.to_list()


def find_semantic_duplicates(
    db,
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

    table = ensure_table(db)
    df = table.to_pandas()
    if df.empty:
        return []

    df0 = df[df["chunk_id"] == 0].copy()
    df0 = df0[~df0["path"].str.startswith("wiki/")]
    df0 = df0.drop_duplicates(subset=["path"])
    if len(df0) < 2:
        return []

    paths = df0["path"].tolist()
    vectors = np.array(df0["vector"].tolist(), dtype=np.float32)

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


def detect_renames(db, filesystem_paths: set[str], workspace: str) -> list[dict]:
    """Confronta LanceDB vs filesystem per rilevare file rinominati.

    filesystem_paths: percorsi assoluti. Li converte in relativi per confrontarli
    con i path del DB (sempre relativi a workspace).
    """
    table = ensure_table(db, "wiki_pages")
    df = table.to_pandas()
    if df.empty:
        return []

    df0 = df[df["chunk_id"] == 0]
    db_paths = set(df0["path"].tolist())

    # Normalizza i path assoluti del filesystem in relativi
    abs_to_rel = {
        p: os.path.relpath(p, workspace).replace("\\", "/")
        for p in filesystem_paths
    }
    rel_fs_paths = set(abs_to_rel.values())

    only_in_db = db_paths - rel_fs_paths
    only_in_fs = rel_fs_paths - db_paths

    db_hash_to_path = {row["page_hash"]: row["path"]
                       for _, row in df0[df0["path"].isin(only_in_db)].iterrows()}

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
