import json
import sys
import pytest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))


def _make_page(path: Path, title: str, body: str = "Content.") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"---\ntitle: {title}\n---\n\n{body}", encoding="utf-8")


@pytest.fixture
def server_client(tmp_workspace):
    import wiki_graph
    wiki_graph._CACHE = None
    wiki_graph._CACHE_TIME = 0.0
    wiki_graph._DIRTY = False
    _make_page(tmp_workspace / "wiki" / "concepts" / "rag.md", "RAG")

    import wiki_server
    cfg = json.loads((tmp_workspace / "wiki.config.json").read_text())
    wiki_server.configure(str(tmp_workspace), cfg, no_auth=True)

    from fastapi.testclient import TestClient
    return TestClient(wiki_server.app)


@pytest.fixture
def auth_client(tmp_workspace):
    import wiki_graph
    wiki_graph._CACHE = None

    import wiki_server
    cfg = json.loads((tmp_workspace / "wiki.config.json").read_text())
    cfg.setdefault("frontend", {})["password"] = "testpass"
    wiki_server.configure(str(tmp_workspace), cfg, no_auth=False)

    from fastapi.testclient import TestClient
    return TestClient(wiki_server.app, raise_server_exceptions=True)


def test_api_graph_endpoint(server_client):
    resp = server_client.get("/api/graph")
    assert resp.status_code == 200
    data = resp.json()
    assert "nodes" in data
    assert "edges" in data
    assert any(n["id"] == "wiki/concepts/rag" for n in data["nodes"])


def test_api_page_endpoint(server_client, tmp_workspace):
    resp = server_client.get("/api/page/wiki/concepts/rag.md")
    assert resp.status_code == 200
    data = resp.json()
    assert "content" in data
    assert "RAG" in data["content"]
    assert "metadata" in data


def test_api_page_not_found(server_client):
    resp = server_client.get("/api/page/wiki/concepts/nonexistent.md")
    assert resp.status_code == 404


def test_auth_required(auth_client):
    resp = auth_client.get("/api/graph", cookies={})
    assert resp.status_code == 401


def test_auth_login(auth_client):
    resp = auth_client.post("/auth/login", json={"password": "testpass"})
    assert resp.status_code == 200
    assert "wiki_session" in resp.cookies


def test_auth_wrong_password(auth_client):
    resp = auth_client.post("/auth/login", json={"password": "wrongpass"})
    assert resp.status_code == 401


def test_auth_cookie_grants_access(auth_client):
    login = auth_client.post("/auth/login", json={"password": "testpass"})
    assert login.status_code == 200
    token = login.cookies["wiki_session"]
    resp = auth_client.get("/api/graph", cookies={"wiki_session": token})
    assert resp.status_code == 200


def test_auth_logout(auth_client):
    login = auth_client.post("/auth/login", json={"password": "testpass"})
    token = login.cookies["wiki_session"]
    logout = auth_client.post("/auth/logout", cookies={"wiki_session": token})
    assert logout.status_code == 200


def test_websocket_connects_no_auth(server_client):
    import wiki_server
    with server_client.websocket_connect("/ws") as ws:
        assert len(wiki_server._ws_clients) == 1


def test_websocket_auth_rejected_without_cookie(auth_client):
    try:
        with auth_client.websocket_connect("/ws", cookies={}) as ws:
            ws.receive_text()
        rejected = False
    except Exception:
        rejected = True
    assert rejected, "Expected WebSocket to be rejected without valid cookie"


def test_api_stats_endpoint(server_client, tmp_workspace):
    resp = server_client.get("/api/stats")
    assert resp.status_code == 200
    data = resp.json()
    for key in ("summary", "top_queried", "stale_pages", "unembedded_pages",
                "lint_status", "auto_lint"):
        assert key in data, f"Missing key: {key}"
    assert "total_pages" in data["summary"]
    assert "total_chunks" in data["summary"]
    assert "embedding_coverage_pct" in data["summary"]
    assert "stale_pages_count" in data["summary"]
    assert isinstance(data["top_queried"], list)
    assert isinstance(data["stale_pages"], list)


def test_api_stats_top_queried(server_client, tmp_workspace):
    import json as _json
    log_path = tmp_workspace / ".wiki-query-log.jsonl"
    entries = [
        {"ts": "2026-05-20T10:00:00", "q": "what is RAG?", "paths": ["wiki/concepts/rag.md"]},
        {"ts": "2026-05-20T10:01:00", "q": "explain RAG", "paths": ["wiki/concepts/rag.md"]},
        {"ts": "2026-05-20T10:02:00", "q": "openai models", "paths": ["wiki/entities/openai.md"]},
    ]
    log_path.write_text("\n".join(_json.dumps(e) for e in entries), encoding="utf-8")

    resp = server_client.get("/api/stats")
    assert resp.status_code == 200
    top = resp.json()["top_queried"]
    assert len(top) >= 1
    paths_in_top = [item["path"] for item in top]
    assert "wiki/concepts/rag.md" in paths_in_top
    rag_item = next(i for i in top if i["path"] == "wiki/concepts/rag.md")
    assert rag_item["query_count"] == 2


def test_api_stats_unembedded(server_client, tmp_workspace, monkeypatch):
    import pandas as pd
    import wiki_lancedb

    (tmp_workspace / "wiki" / "concepts" / "embedding.md").write_text(
        "---\ntitle: Embedding\n---\n\nContent.", encoding="utf-8"
    )

    class FakeTable:
        def to_pandas(self):
            # Solo rag.md e' embedded
            return pd.DataFrame({"path": ["wiki/concepts/rag.md"]})

    monkeypatch.setattr(wiki_lancedb, "get_db", lambda path: object())
    monkeypatch.setattr(wiki_lancedb, "ensure_table",
                        lambda *args, **kwargs: FakeTable())

    resp = server_client.get("/api/stats")
    assert resp.status_code == 200
    unembedded = resp.json()["unembedded_pages"]
    unembedded_paths = [u["path"] for u in unembedded]
    assert "wiki/concepts/embedding.md" in unembedded_paths
    assert "wiki/concepts/rag.md" not in unembedded_paths


def test_api_stats_lint_status(server_client, tmp_workspace):
    import json
    status_data = {
        "last_run": "2026-05-20T14:32:00",
        "errors": 0,
        "warnings": 2,
        "detail": "2 orphan vectors removed",
    }
    (tmp_workspace / ".wiki-lint-status.json").write_text(
        json.dumps(status_data), encoding="utf-8"
    )

    resp = server_client.get("/api/stats")
    assert resp.status_code == 200
    lint = resp.json()["lint_status"]
    assert lint is not None
    assert lint["last_run"] == "2026-05-20T14:32:00"
    assert lint["errors"] == 0
    assert lint["warnings"] == 2
    assert "detail" in lint, "Missing 'detail' field in lint_status"


def test_api_lint_trigger(server_client, tmp_workspace, monkeypatch):
    import subprocess
    fake_result = subprocess.CompletedProcess(
        args=[], returncode=0,
        stdout="Lint complete. 0 errors, 0 warnings.", stderr=""
    )
    monkeypatch.setattr(subprocess, "run", lambda *a, **kw: fake_result)

    resp = server_client.post("/api/lint")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "output" in data


def test_api_lint_conflict(server_client, monkeypatch):
    import wiki_server
    wiki_server._lint_busy = True
    try:
        resp = server_client.post("/api/lint")
        assert resp.status_code == 409
    finally:
        wiki_server._lint_busy = False
