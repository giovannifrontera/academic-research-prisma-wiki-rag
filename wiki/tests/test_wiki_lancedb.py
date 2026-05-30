import sys, os, hashlib
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

import pytest
from wiki_lancedb import get_db, ensure_table, upsert, query_similar, promote_staging, rollback_staging, detect_renames

FAKE_VECTOR = [0.01] * 1024

def make_chunks(path, n=1):
    return [{"chunk_id": i, "chunk_text": f"testo chunk {i}", "content_hash": f"hash{i}",
             "page_hash": "pagehash", "vector": FAKE_VECTOR} for i in range(n)]

def test_ensure_table_creates_table(tmp_workspace):
    db = get_db(str(tmp_workspace / "memory" / "lancedb"))
    ensure_table(db)
    assert "wiki_pages" in db.list_tables().tables

def test_upsert_adds_rows(tmp_workspace):
    db = get_db(str(tmp_workspace / "memory" / "lancedb"))
    upsert(db, "wiki/concepts/test.md", make_chunks("test", 2))
    table = ensure_table(db)
    df = table.to_pandas()
    assert len(df[df["path"] == "wiki/concepts/test.md"]) == 2

def test_upsert_replaces_all_chunks(tmp_workspace):
    db = get_db(str(tmp_workspace / "memory" / "lancedb"))
    upsert(db, "wiki/concepts/test.md", make_chunks("test", 3))
    upsert(db, "wiki/concepts/test.md", make_chunks("test", 1))
    table = ensure_table(db)
    df = table.to_pandas()
    assert len(df[df["path"] == "wiki/concepts/test.md"]) == 1

def test_upsert_does_not_affect_other_paths(tmp_workspace):
    db = get_db(str(tmp_workspace / "memory" / "lancedb"))
    upsert(db, "wiki/concepts/a.md", make_chunks("a"))
    upsert(db, "wiki/concepts/b.md", make_chunks("b"))
    upsert(db, "wiki/concepts/a.md", make_chunks("a_new", 2))
    table = ensure_table(db)
    df = table.to_pandas()
    assert len(df[df["path"] == "wiki/concepts/b.md"]) == 1

def test_query_similar_returns_results(tmp_workspace):
    db = get_db(str(tmp_workspace / "memory" / "lancedb"))
    upsert(db, "wiki/concepts/test.md", make_chunks("test"))
    results = query_similar(db, FAKE_VECTOR, k=1)
    assert len(results) >= 1
    assert "path" in results[0]

def test_promote_staging_moves_to_wiki(tmp_workspace):
    db = get_db(str(tmp_workspace / "memory" / "lancedb"))
    upsert(db, "wiki/concepts/test.md", make_chunks("test"), table_name="staging_wiki_pages")
    promote_staging(db)
    wiki = ensure_table(db, "wiki_pages")
    df = wiki.to_pandas()
    assert len(df[df["path"] == "wiki/concepts/test.md"]) == 1
    staging = ensure_table(db, "staging_wiki_pages")
    assert staging.to_pandas().empty

def test_rollback_staging_clears_staging(tmp_workspace):
    db = get_db(str(tmp_workspace / "memory" / "lancedb"))
    upsert(db, "wiki/concepts/test.md", make_chunks("test"), table_name="staging_wiki_pages")
    rollback_staging(db)
    staging = ensure_table(db, "staging_wiki_pages")
    assert staging.to_pandas().empty
    wiki = ensure_table(db, "wiki_pages")
    assert wiki.to_pandas().empty

def test_detect_renames(tmp_workspace):
    db = get_db(str(tmp_workspace / "memory" / "lancedb"))
    content = "# Pagina rinominata\nContenuto."
    page_hash = hashlib.sha256(content.encode()).hexdigest()
    old_path = "wiki/concepts/old-name.md"
    # page_hash == sha256(file intero); detect_renames confronta su page_hash
    chunks = [{"chunk_id": 0, "chunk_text": content, "content_hash": "anychunkhash",
                "page_hash": page_hash, "vector": FAKE_VECTOR}]
    upsert(db, old_path, chunks)
    new_file = tmp_workspace / "wiki" / "concepts" / "new-name.md"
    new_file.write_text(content, encoding="utf-8")
    workspace = str(tmp_workspace)
    renames = detect_renames(db, {str(new_file)}, workspace)
    assert len(renames) == 1
    assert renames[0]["old_path"] == old_path
    # new_path è relativo al workspace, non assoluto
    assert renames[0]["new_path"] == "wiki/concepts/new-name.md"


def test_find_semantic_duplicates_empty(tmp_path):
    from wiki_lancedb import get_db, find_semantic_duplicates
    db = get_db(str(tmp_path / "lancedb"))
    result = find_semantic_duplicates(db)
    assert result == []


def test_find_semantic_duplicates_detects_near_identical(tmp_path):
    import numpy as np
    from wiki_lancedb import get_db, upsert, find_semantic_duplicates

    db = get_db(str(tmp_path / "lancedb"))

    base = np.random.rand(1024).astype(np.float32)
    base /= np.linalg.norm(base)
    near = base + np.random.rand(1024).astype(np.float32) * 0.01
    near /= np.linalg.norm(near)

    chunks_a = [{"chunk_id": 0, "chunk_text": "a", "content_hash": "ha", "page_hash": "pha", "vector": base.tolist()}]
    chunks_b = [{"chunk_id": 0, "chunk_text": "b", "content_hash": "hb", "page_hash": "phb", "vector": near.tolist()}]
    upsert(db, "wiki-works/test/page_a.md", chunks_a)
    upsert(db, "wiki-works/test/page_b.md", chunks_b)

    result = find_semantic_duplicates(db, auto_threshold=0.90, warn_threshold=0.75)
    assert len(result) == 1
    assert result[0]["action"] == "auto_merge"
    assert result[0]["page_a"] in ("wiki-works/test/page_a.md", "wiki-works/test/page_b.md")


def test_find_semantic_duplicates_warn_range(tmp_path):
    import numpy as np
    from wiki_lancedb import get_db, upsert, find_semantic_duplicates

    db = get_db(str(tmp_path / "lancedb"))

    base = np.random.rand(1024).astype(np.float32)
    base /= np.linalg.norm(base)
    perp = np.random.rand(1024).astype(np.float32)
    perp -= perp.dot(base) * base
    perp /= np.linalg.norm(perp)
    similar = 0.80 * base + 0.60 * perp
    similar /= np.linalg.norm(similar)

    chunks_a = [{"chunk_id": 0, "chunk_text": "a", "content_hash": "ha", "page_hash": "pha", "vector": base.tolist()}]
    chunks_b = [{"chunk_id": 0, "chunk_text": "b", "content_hash": "hb", "page_hash": "phb", "vector": similar.tolist()}]
    upsert(db, "wiki-works/test/page_a.md", chunks_a)
    upsert(db, "wiki-works/test/page_b.md", chunks_b)

    result = find_semantic_duplicates(db, auto_threshold=0.90, warn_threshold=0.75)
    assert len(result) == 1
    assert result[0]["action"] == "warn"


def test_find_semantic_duplicates_skips_wiki_identity(tmp_path):
    import numpy as np
    from wiki_lancedb import get_db, upsert, find_semantic_duplicates

    db = get_db(str(tmp_path / "lancedb"))
    base = np.random.rand(1024).astype(np.float32)
    base /= np.linalg.norm(base)
    near = base + np.random.rand(1024).astype(np.float32) * 0.001
    near /= np.linalg.norm(near)

    chunks_id = [{"chunk_id": 0, "chunk_text": "identity", "content_hash": "hi", "page_hash": "phi", "vector": base.tolist()}]
    chunks_k = [{"chunk_id": 0, "chunk_text": "knowledge", "content_hash": "hk", "page_hash": "phk", "vector": near.tolist()}]
    upsert(db, "wiki/identity/style.md", chunks_id)
    upsert(db, "wiki-works/test/concept.md", chunks_k)

    result = find_semantic_duplicates(db, auto_threshold=0.90, warn_threshold=0.75)
    assert result == [], "wiki/ identity pages must not be compared with wiki-works/ pages"


def test_find_semantic_duplicates_single_page(tmp_path):
    import numpy as np
    from wiki_lancedb import get_db, upsert, find_semantic_duplicates

    db = get_db(str(tmp_path / "lancedb"))
    vec = np.random.rand(1024).astype(np.float32)
    vec /= np.linalg.norm(vec)
    chunks = [{"chunk_id": 0, "chunk_text": "solo", "content_hash": "h", "page_hash": "ph", "vector": vec.tolist()}]
    upsert(db, "wiki-works/test/only_page.md", chunks)

    result = find_semantic_duplicates(db)
    assert result == []
