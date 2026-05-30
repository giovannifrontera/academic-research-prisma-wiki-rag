import json
import sys
import pytest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from wiki_graph import build_graph


def _make_page(path: Path, title: str, description: str = "", body: str = "Content.") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"---\ntitle: {title}\ndescription: {description}\n---\n\n{body}",
        encoding="utf-8",
    )


@pytest.fixture(autouse=True)
def reset_graph_cache():
    import wiki_graph
    wiki_graph._CACHE = None
    wiki_graph._CACHE_TIME = 0.0
    wiki_graph._DIRTY = False
    yield


def test_build_graph_nodes(tmp_workspace):
    _make_page(tmp_workspace / "wiki" / "entities" / "openai.md", "OpenAI", "AI company")
    _make_page(tmp_workspace / "wiki" / "concepts" / "rag.md", "RAG")

    cfg = json.loads((tmp_workspace / "wiki.config.json").read_text())
    result = build_graph(str(tmp_workspace), cfg)

    ids = {n["id"] for n in result["nodes"]}
    assert "wiki/entities/openai" in ids
    assert "wiki/concepts/rag" in ids
    assert result["edges"] == []


def test_build_graph_excludes_index_log(tmp_workspace):
    _make_page(tmp_workspace / "wiki" / "index.md", "Index")
    _make_page(tmp_workspace / "wiki" / "log.md", "Log")
    _make_page(tmp_workspace / "wiki" / "concepts" / "rag.md", "RAG")

    cfg = json.loads((tmp_workspace / "wiki.config.json").read_text())
    result = build_graph(str(tmp_workspace), cfg)

    ids = {n["id"] for n in result["nodes"]}
    assert "wiki/index" not in ids
    assert "wiki/log" not in ids
    assert "wiki/concepts/rag" in ids


def test_build_graph_excludes_raw_dirs(tmp_workspace):
    (tmp_workspace / "wiki-works" / "test" / "raw").mkdir(parents=True, exist_ok=True)
    _make_page(tmp_workspace / "wiki-works" / "test" / "raw" / "source.md", "Source")
    _make_page(tmp_workspace / "wiki" / "concepts" / "rag.md", "RAG")

    cfg = json.loads((tmp_workspace / "wiki.config.json").read_text())
    result = build_graph(str(tmp_workspace), cfg)

    ids = {n["id"] for n in result["nodes"]}
    assert not any("raw" in nid for nid in ids)
    assert "wiki/concepts/rag" in ids


def test_node_has_required_fields(tmp_workspace):
    _make_page(tmp_workspace / "wiki" / "entities" / "openai.md", "OpenAI", "AI company")

    cfg = json.loads((tmp_workspace / "wiki.config.json").read_text())
    result = build_graph(str(tmp_workspace), cfg)

    node = next(n for n in result["nodes"] if n["id"] == "wiki/entities/openai")
    for field in ("id", "path", "title", "category", "project", "description", "last_modified"):
        assert field in node, f"Missing field: {field}"
    assert node["title"] == "OpenAI"
    assert node["description"] == "AI company"
    assert node["category"] == "entities"
    assert node["project"] == "wiki"


def test_build_graph_explicit_links(tmp_workspace):
    _make_page(
        tmp_workspace / "wiki" / "concepts" / "rag.md", "RAG",
        body="[[embedding]] is the core technique.",
    )
    _make_page(tmp_workspace / "wiki" / "concepts" / "embedding.md", "Embedding")

    cfg = json.loads((tmp_workspace / "wiki.config.json").read_text())
    result = build_graph(str(tmp_workspace), cfg)

    link_edges = [e for e in result["edges"] if e["type"] == "link"]
    assert len(link_edges) == 1
    assert link_edges[0]["source"] == "wiki/concepts/rag"
    assert link_edges[0]["target"] == "wiki/concepts/embedding"


def test_missing_link_ignored(tmp_workspace):
    _make_page(
        tmp_workspace / "wiki" / "concepts" / "rag.md", "RAG",
        body="[[nonexistent_page]] is referenced.",
    )

    cfg = json.loads((tmp_workspace / "wiki.config.json").read_text())
    result = build_graph(str(tmp_workspace), cfg)

    assert result["edges"] == []


def test_get_page_detail_links_out(tmp_workspace):
    from wiki_graph import get_page_detail
    _make_page(
        tmp_workspace / "wiki" / "concepts" / "rag.md", "RAG",
        description="Retrieval-Augmented Generation",
        body="[[embedding]] is the core technique.",
    )
    _make_page(tmp_workspace / "wiki" / "concepts" / "embedding.md", "Embedding")

    cfg = json.loads((tmp_workspace / "wiki.config.json").read_text())
    detail = get_page_detail(str(tmp_workspace), "wiki/concepts/rag.md", cfg)

    assert detail is not None
    assert "RAG" in detail["content"]
    assert detail["metadata"]["title"] == "RAG"
    assert "wiki/concepts/embedding" in detail["links_out"]
    assert detail["links_in"] == []


def test_get_page_detail_links_in(tmp_workspace):
    from wiki_graph import get_page_detail
    _make_page(
        tmp_workspace / "wiki" / "concepts" / "rag.md", "RAG",
        body="[[embedding]] is the core technique.",
    )
    _make_page(tmp_workspace / "wiki" / "concepts" / "embedding.md", "Embedding")

    cfg = json.loads((tmp_workspace / "wiki.config.json").read_text())
    detail = get_page_detail(str(tmp_workspace), "wiki/concepts/embedding.md", cfg)

    assert "wiki/concepts/rag" in detail["links_in"]
    assert detail["links_out"] == []


def test_build_graph_semantic_edges(tmp_workspace, monkeypatch):
    import numpy as np
    import pandas as pd
    import wiki_graph

    _make_page(tmp_workspace / "wiki" / "concepts" / "rag.md", "RAG")
    _make_page(tmp_workspace / "wiki" / "concepts" / "transformer.md", "Transformer")

    fake_df = pd.DataFrame([
        {"path": "wiki/concepts/rag.md", "chunk_id": 0,
         "vector": np.ones(1024).tolist(),
         "chunk_text": "rag", "content_hash": "a", "page_hash": "a", "last_embedded": 0.0},
        {"path": "wiki/concepts/transformer.md", "chunk_id": 0,
         "vector": np.ones(1024).tolist(),
         "chunk_text": "transformer", "content_hash": "b", "page_hash": "b", "last_embedded": 0.0},
    ])

    class FakeTable:
        def to_pandas(self):
            return fake_df

    monkeypatch.setattr(wiki_graph, "_LANCEDB_AVAILABLE", True)
    monkeypatch.setattr(wiki_graph, "_lancedb_get_db", lambda path: object())
    monkeypatch.setattr(wiki_graph, "_lancedb_ensure_table", lambda db, table_name="wiki_pages": FakeTable())
    monkeypatch.setattr(wiki_graph, "_lancedb_query_similar", lambda db, vec, k=5, path_prefix=None: [
        {"path": "wiki/concepts/transformer.md", "_distance": 0.1,
         "chunk_id": 0, "chunk_text": "transformer"},
    ])

    cfg = json.loads((tmp_workspace / "wiki.config.json").read_text())
    result = build_graph(str(tmp_workspace), cfg)

    sem_edges = [e for e in result["edges"] if e["type"] == "semantic"]
    assert len(sem_edges) == 1
    pair = {sem_edges[0]["source"], sem_edges[0]["target"]}
    assert pair == {"wiki/concepts/rag", "wiki/concepts/transformer"}
    assert sem_edges[0]["weight"] == pytest.approx(0.9, abs=0.01)


def test_graph_cache_reused(tmp_workspace):
    _make_page(tmp_workspace / "wiki" / "concepts" / "rag.md", "RAG")
    cfg = json.loads((tmp_workspace / "wiki.config.json").read_text())
    r1 = build_graph(str(tmp_workspace), cfg)
    r2 = build_graph(str(tmp_workspace), cfg)
    # Cache returns same content — both calls should have identical nodes
    assert r1["nodes"] == r2["nodes"]
    assert r1["edges"] == r2["edges"]


def test_mark_dirty_forces_rebuild(tmp_workspace):
    import wiki_graph
    _make_page(tmp_workspace / "wiki" / "concepts" / "rag.md", "RAG")
    cfg = json.loads((tmp_workspace / "wiki.config.json").read_text())
    r1 = build_graph(str(tmp_workspace), cfg)

    _make_page(tmp_workspace / "wiki" / "concepts" / "embedding.md", "Embedding")
    wiki_graph.mark_dirty()
    r2 = build_graph(str(tmp_workspace), cfg)

    ids = {n["id"] for n in r2["nodes"]}
    assert "wiki/concepts/embedding" in ids
    assert len(r2["nodes"]) > len(r1["nodes"])


def test_query_log_written(tmp_workspace, monkeypatch):
    import wiki_workflows
    import wiki_lancedb
    import wiki_embed

    def fake_query_similar(db, vector, k=5, path_prefix=None):
        return [{"path": "wiki/concepts/rag.md", "chunk_id": 0,
                 "_distance": 0.1, "chunk_text": "rag chunk"}]

    class FakeModel:
        def encode(self, text, normalize_embeddings=True):
            import numpy as np
            return np.zeros(1024)

    monkeypatch.setattr(wiki_lancedb, "query_similar", fake_query_similar)
    monkeypatch.setattr(wiki_lancedb, "get_db", lambda path: object())
    monkeypatch.setattr(wiki_embed, "_load_model", lambda name: (FakeModel(), None))
    # wiki_workflows imports these names directly at module level, so patch there too
    monkeypatch.setattr(wiki_workflows, "query_similar", fake_query_similar)
    monkeypatch.setattr(wiki_workflows, "get_db", lambda path: object())
    monkeypatch.setattr(wiki_workflows, "_load_model", lambda name: (FakeModel(), None))

    cfg = json.loads((tmp_workspace / "wiki.config.json").read_text())

    class Args:
        workspace = str(tmp_workspace)
        q = "what is RAG?"
        k = 5

    wiki_workflows.cmd_query(Args(), cfg)

    log_path = tmp_workspace / ".wiki-query-log.jsonl"
    assert log_path.exists(), ".wiki-query-log.jsonl not created"
    entry = json.loads(log_path.read_text().strip())
    assert entry["q"] == "what is RAG?"
    assert "wiki/concepts/rag.md" in entry["paths"]
    assert "ts" in entry


def test_get_page_detail_path_traversal(tmp_workspace):
    """Path traversal attempts outside workspace must return None."""
    from wiki_graph import get_page_detail
    cfg = json.loads((tmp_workspace / "wiki.config.json").read_text())

    assert get_page_detail(str(tmp_workspace), "../../etc/passwd", cfg) is None
    assert get_page_detail(str(tmp_workspace), "../../../Windows/System32/drivers/etc/hosts", cfg) is None


def test_build_graph_excludes_raw_dir_directly_under_wiki(tmp_workspace):
    """Files in wiki/raw/ (raw directly under wiki, not under a project) must be excluded."""
    _make_page(tmp_workspace / "wiki" / "raw" / "source.md", "Source")
    _make_page(tmp_workspace / "wiki" / "concepts" / "rag.md", "RAG")

    cfg = json.loads((tmp_workspace / "wiki.config.json").read_text())
    result = build_graph(str(tmp_workspace), cfg)

    ids = {n["id"] for n in result["nodes"]}
    assert "wiki/raw/source" not in ids
    assert "wiki/concepts/rag" in ids
