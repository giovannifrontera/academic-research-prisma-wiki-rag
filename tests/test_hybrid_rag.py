"""Offline regression checks with a real local Qdrant index."""
import importlib.util
import json
from pathlib import Path

import pytest


@pytest.fixture
def rag(tmp_path, monkeypatch):
    source = Path(__file__).parents[1] / "skills/hybrid-rag/hybrid_rag_template.py"
    spec = importlib.util.spec_from_file_location("hybrid_rag", source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(module, "_embed_query", lambda *_: [1.0, 0.0])
    monkeypatch.setattr(module, "_embed_docs", lambda texts, _: [[1.0, 0.0] for _ in texts])
    module._backend_instance = module._QdrantBackend()
    module._backend_instance.init_collections(2)
    yield module
    module._backend_instance._client.close()


def test_qdrant_dense_sparse_filters_and_empty_match(rag, capsys):
    backend = rag._get_backend()
    backend.upsert(rag.COLLECTION_PRISMA,
                   ["eligible learning study", "excluded learning study"],
                   [[1.0, 0.0], [1.0, 0.0]], ["included", "excluded"],
                   [{"year": 2024, "source_db": "eric"}, {"year": 2010, "source_db": "other"}])
    assert len(backend.search(rag.COLLECTION_PRISMA, [1.0, 0.0], 5)) == 2
    for expression in ("year>=2020,source_db=eric", "year=2024"):
        query_filter = rag._parse_qdrant_filter(expression)
        assert [x["id"] for x in backend.search(rag.COLLECTION_PRISMA, [1.0, 0.0], 5, query_filter)] == ["included"]
        assert [x["id"] for x in backend.get_all(rag.COLLECTION_PRISMA, query_filter)] == ["included"]
        rag.op_query("learning", use_pdf=False, filter_str=expression)
        output = capsys.readouterr().out
        assert "eligible learning" in output
        assert "excluded learning" not in output
    rag.op_query("learning", use_pdf=False, filter_str="year>2050")
    assert "0 risultati" in capsys.readouterr().out
    with pytest.raises(RuntimeError, match="dense search"):
        backend.search(rag.COLLECTION_PRISMA, [1.0, 0.0, 0.0], 5)


def test_qdrant_scroll_reads_every_page(rag):
    backend = rag._get_backend()
    count = 10001
    backend.upsert(rag.COLLECTION_PRISMA, ["learning"] * count,
                   [[1.0, 0.0]] * count, [str(i) for i in range(count)],
                   [{"year": 2024}] * count)
    assert len(backend.get_all(rag.COLLECTION_PRISMA)) == count


@pytest.mark.parametrize("invalid", [
    {"metadata": {"version": 1}},
    {"unknown": [{"title": "Unknown wrapper"}]},
    {"fase4": {}},
    [{"title": "Excluded", "included": False}],
    [{"title": "Valid"}, {"title": "Excluded", "included": False}],
])
def test_invalid_corpus_preserves_existing_index(rag, invalid):
    path = Path("eligibility_prisma.json")
    path.write_text(json.dumps([{"title": "Existing", "doi": "10.1/existing"}]))
    rag.op_index_prisma(str(path))
    before = rag._get_backend().get_all(rag.COLLECTION_PRISMA)
    path.write_text(json.dumps(invalid))
    with pytest.raises(ValueError):
        rag.op_index_prisma(str(path))
    assert rag._get_backend().get_all(rag.COLLECTION_PRISMA) == before


@pytest.mark.parametrize("records", [
    [{"title": "Included", "included": True}],
    {"paper1": {"titolo": "Included"}},
    {"fase4": {"paper_inclusi": [{"title": "Included"}]}},
])
def test_known_prisma_formats(rag, records):
    path = Path("eligibility_prisma.json")
    path.write_text(json.dumps(records))
    rag.op_index_prisma(str(path))
    assert rag._get_backend().count(rag.COLLECTION_PRISMA) == 1
    assert rag._load_config()["backend"] == "qdrant"


def test_screening_without_inclusion_proof_is_rejected(rag):
    path = Path("screening_prisma.json")
    path.write_text(json.dumps([{"title": "Unreviewed"}]))
    with pytest.raises(ValueError, match="inclusione non verificabile"):
        rag.op_index_prisma(str(path))


def test_reindex_removes_records_no_longer_in_eligibility(rag):
    path = Path("eligibility_prisma.json")
    path.write_text(json.dumps([
        {"title": "Keep", "id": "keep"},
        {"title": "Remove", "id": "remove"},
    ]))
    rag.op_index_prisma(str(path))
    path.write_text(json.dumps([{"title": "Keep", "id": "keep"}]))
    rag.op_index_prisma(str(path))
    assert [row["id"] for row in rag._get_backend().get_all(rag.COLLECTION_PRISMA)] == ["keep"]
    path.write_text("[]")
    rag.op_index_prisma(str(path))
    assert rag._get_backend().count(rag.COLLECTION_PRISMA) == 0


def test_zero_bm25_scores_do_not_change_dense_order(rag, monkeypatch, capsys):
    from types import SimpleNamespace

    backend = SimpleNamespace(
        _client=SimpleNamespace(close=lambda: None),
        count=lambda _: 2,
        search=lambda *_: [
            {"id": "dense-first", "text": "alpha", "meta": {}, "score": 0.9, "collection": "papers"},
            {"id": "dense-second", "text": "beta", "meta": {}, "score": 0.8, "collection": "papers"},
        ],
        get_all=lambda *_: [
            {"id": "dense-second", "text": "beta", "meta": {}, "collection": "papers"},
            {"id": "dense-first", "text": "alpha", "meta": {}, "collection": "papers"},
        ],
        name=lambda: "fake",
    )
    monkeypatch.setattr(rag, "_backend_instance", backend)
    rag.op_query("no-token-match", n_results=2, use_pdf=False)
    output = capsys.readouterr().out
    assert output.index("alpha") < output.index("beta")


def test_invalid_filter_fails_closed(rag):
    with pytest.raises(ValueError, match="Filtro"):
        rag._parse_qdrant_filter("year>=2020,invalid")
    with pytest.raises(ValueError, match="Filtro"):
        rag._parse_lance_filter("year>=2020,invalid")


def test_rag_dir_resolves_under_study_project(tmp_path, rag):
    from scripts.study_workspace import create_study
    result = create_study("My Study", tmp_path)
    project_root = result["project_root"]
    rag_dir = rag._resolve_rag_dir(project=project_root)
    assert str(rag_dir) == str(Path(project_root) / "database" / "qdrant-rag")


def test_rag_dir_defaults_to_cwd_rag_db_without_project(tmp_path, monkeypatch, rag):
    monkeypatch.chdir(tmp_path)
    rag_dir = rag._resolve_rag_dir(project=None)
    assert str(rag_dir) == str(tmp_path / "rag_db")


def test_collection_pdf_name_switches_in_study_mode(tmp_path, rag):
    from scripts.study_workspace import create_study
    result = create_study("My Study", tmp_path)
    assert rag._collection_pdf_name(project=result["project_root"]) == "included_pdf_chunks"
    assert rag._collection_pdf_name(project=None) == "pdf_manual"


def test_optional_backend_metadata_and_chroma_query(rag):
    from types import SimpleNamespace

    def query(**kwargs):
        assert kwargs["include"] == ["documents", "metadatas", "distances"]
        return {"documents": [["paper"]], "metadatas": [[{}]],
                "distances": [[0.0]], "ids": [["p1"]]}

    backend = rag._ChromaBackend.__new__(rag._ChromaBackend)
    backend._client = SimpleNamespace(get_collection=lambda _: SimpleNamespace(count=lambda: 1, query=query))
    assert backend.search("papers", [1.0, 0.0], 5)[0]["id"] == "p1"
    lance = rag._LanceBackend.__new__(rag._LanceBackend)
    meta = lance._metadata({"filename": "included.pdf", "page": 3, "chunk_index": 2}, rag.COLLECTION_PDF)
    assert meta["source_type"] == rag.SOURCE_PDF
    assert meta["chunk_index"] + 1 == 3
    assert meta["page"] == 3
