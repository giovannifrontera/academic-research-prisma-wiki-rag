import asyncio
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))


@pytest.fixture(autouse=True)
def inline_executor(monkeypatch):
    async def run(_, __, func, *args):
        return func(*args)

    monkeypatch.setattr(asyncio.BaseEventLoop, "run_in_executor", run)


def test_rerank_orders_scores_without_changing_candidates(monkeypatch):
    import wiki_rerank
    from types import SimpleNamespace

    monkeypatch.setattr(wiki_rerank, "_load_reranker", lambda name: SimpleNamespace(
        predict=lambda pairs: np.array([0.1, 0.9])))
    candidates = [{"chunk_text": "unrelated"}, {"chunk_text": "relevant"}]
    assert wiki_rerank.rerank("query", candidates, top_k=1) == [
        {"chunk_text": "relevant", "_rerank_score": 0.9}]
    assert "_rerank_score" not in candidates[1]
    assert wiki_rerank.rerank("query", []) == []


@pytest.mark.parametrize("fails", [False, True])
def test_context_reranks_full_chunks_and_logs_failure(tmp_workspace, monkeypatch, caplog, fails):
    import json
    import wiki_rerank
    import wiki_server
    from starlette.requests import Request
    from types import SimpleNamespace

    cfg = json.loads((tmp_workspace / "wiki.config.json").read_text())
    cfg["qdrant"]["rerank"] = True
    wiki_server.configure(str(tmp_workspace), cfg, no_auth=True)
    monkeypatch.setattr(wiki_server, "_embed_model", SimpleNamespace(
        encode=lambda *a, **kw: np.zeros(1024)))
    monkeypatch.setattr(wiki_server._wiki_qdrant, "get_db", lambda path: object())
    monkeypatch.setattr(wiki_server._wiki_qdrant, "query_similar", lambda *a, **kw: [
        {"path": "unrelated.md", "chunk_text": "a" * 100, "_distance": 0.1},
        {"path": "relevant.md", "chunk_text": "b" * 100 + " answer", "_distance": 0.2},
    ])

    def predict(pairs):
        if fails:
            raise RuntimeError("model unavailable")
        return np.array([float("answer" in text) for _, text in pairs])

    monkeypatch.setattr(wiki_rerank, "_load_reranker", lambda name: SimpleNamespace(predict=predict))
    request = Request({"type": "http", "client": ("127.0.0.1", 12345)})
    response = asyncio.run(wiki_server.api_context(request, q="query", k=1, max_chars=20))
    assert response.status_code == 200
    body = response.body.decode()
    assert ("unrelated.md" if fails else "relevant.md") in body
    assert "b" * 21 not in body
    if fails:
        assert "model unavailable" in caplog.text


def test_server_reuses_embedding_model(monkeypatch):
    import wiki_embed
    import wiki_server
    from types import SimpleNamespace

    expected = SimpleNamespace(device="cuda:0")
    monkeypatch.setattr(wiki_embed, "_load_model", lambda name: (expected, None))
    monkeypatch.setattr(wiki_server, "_embed_model", None)
    assert asyncio.run(wiki_server._get_embed_model()) is expected
