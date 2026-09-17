import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))


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


@pytest.mark.parametrize("enabled,fails,expected", [(True, False, "relevant.md"), (True, True, "first.md"), (False, False, "first.md")])
def test_cli_ranks_full_chunks_and_honors_config(tmp_workspace, monkeypatch, capsys, enabled, fails, expected):
    import json
    import wiki_workflows
    import wiki_rerank
    from types import SimpleNamespace

    cfg = json.loads((tmp_workspace / "wiki.config.json").read_text())
    cfg["qdrant"]["rerank"] = enabled
    cfg["exclude_from_index"] = ["private/*"]
    monkeypatch.setattr(wiki_workflows, "get_db", lambda *_: SimpleNamespace(close=lambda: None))
    monkeypatch.setattr(wiki_workflows, "_load_model", lambda *_: (SimpleNamespace(encode=lambda *a, **kw: np.zeros(1024)), None))
    monkeypatch.setattr(wiki_workflows, "query_similar", lambda *a, **kw: [
        {"path": "private/secret.md", "chunk_id": 0, "chunk_text": "secret", "_distance": 0.0},
        {"path": "first.md", "chunk_id": 0, "chunk_text": "a" * 300, "_distance": 0.1},
        {"path": "relevant.md", "chunk_id": 0, "chunk_text": "b" * 300 + " answer", "_distance": 0.2},
    ])
    def predict(pairs):
        if fails:
            raise RuntimeError("offline")
        return np.array([float("answer" in text) for _, text in pairs])
    monkeypatch.setattr(wiki_rerank, "_load_reranker", lambda *_: SimpleNamespace(predict=predict))
    wiki_workflows.cmd_query(SimpleNamespace(workspace=str(tmp_workspace), q="question", k=1), cfg)
    result = json.loads(capsys.readouterr().out)
    assert [r["path"] for r in result["results"]] == [expected]
    assert len(result["results"][0]["excerpt"]) <= 200
