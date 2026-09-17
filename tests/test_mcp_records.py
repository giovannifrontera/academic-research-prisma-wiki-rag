"""Offline contract checks for complete bibliography exports and MCP schemas."""
import asyncio
import importlib.util
import json
from pathlib import Path

import pytest

pytest.importorskip("mcp.server.fastmcp")

ROOT = Path(__file__).resolve().parents[1]
ABSTRACT = "Complete abstract. " * 40
RECORD = {"id": "record-1", "title": "Study", "abstract": ABSTRACT,
          "authors": [{"name": f"Author {n}"} for n in range(5)]}
ERIC = {"id": "EJ1", "title": "Study", "description": ABSTRACT, "author": ["A", "B", "C", "D"]}
DOAJ = {"id": "doaj-1", "bibjson": {"title": "Study", "abstract": ABSTRACT, "author": [{"name": "A"}]}}
ZENODO = {"id": 1, "metadata": {"title": "Study", "description": ABSTRACT, "creators": [{"name": "A"}]}}
OPENAIRE = {"header": {"dri:objIdentifier": {"$": "oa-1"}}, "metadata": {"oaf:entity": {"oaf:result": {
    "title": {"$": "Study"}, "description": {"$": ABSTRACT}, "creator": [{"$": "A"}],
}}}}


def load_server(name):
    spec = importlib.util.spec_from_file_location("prisma_mcp_" + name.replace("-", "_"), ROOT / "mcp-servers" / name / "server.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("server,tool,helper,data,expected", [
    ("eric", "eric_search", "_search", {"response": {"docs": [ERIC], "numFound": 42, "start": 5}}, ERIC),
    ("eric", "eric_advanced_search", "_search", {"response": {"docs": [ERIC], "numFound": 42}}, ERIC),
    ("eric", "eric_search_by_descriptor", "_search", {"response": {"docs": [ERIC], "numFound": 42}}, ERIC),
    ("core", "core_search", "_post", {"results": [RECORD], "totalHits": 42}, RECORD),
    ("semantic-scholar", "semantic_scholar_search", "_get", {"data": [RECORD], "total": 42, "offset": 5, "next": 6}, RECORD),
    ("doaj", "doaj_search_articles", "_get", {"results": [DOAJ], "total": 42}, DOAJ),
    ("zenodo", "zenodo_search", "_get", {"hits": {"hits": [ZENODO], "total": {"value": 42, "relation": "eq"}}}, ZENODO),
    ("openaire", "openaire_search", "_request", {"response": {"header": {"total": {"$": "42"}}, "results": {"result": OPENAIRE}}}, None),
])
def test_search_complete_records_and_registered_schema(monkeypatch, server, tool, helper, data, expected):
    module = load_server(server)
    monkeypatch.setattr(module, helper, lambda *args, **kwargs: data)
    fn = getattr(module, tool)
    result = json.loads(fn("study", output_format="json"))
    assert result["total"] == 42
    assert result["records"] == [expected or module._parse(OPENAIRE)]
    assert ABSTRACT in json.dumps(result)
    assert ABSTRACT not in fn("study")  # Legacy text preview remains the default.
    with pytest.raises(ValueError, match="output_format"):
        fn("study", output_format="csv")
    tools = asyncio.run(module.mcp.list_tools())
    schema = next(t.inputSchema for t in tools if t.name == tool)
    assert schema["properties"]["output_format"]["enum"] == ["text", "json"]
    assert schema["properties"]["output_format"]["default"] == "text"


def test_semantic_scholar_pagination(monkeypatch):
    module = load_server("semantic-scholar")
    params = {}
    def fake_get(endpoint, query):
        params.update(query)
        return {"data": [RECORD], "total": 80, "offset": 20, "next": 30}
    monkeypatch.setattr(module, "_get", fake_get)
    result = json.loads(module.semantic_scholar_search("study", offset=20, output_format="json"))
    assert params["offset"] == result["offset"] == 20
    assert result["next"] == 30


@pytest.mark.parametrize("server,tool", [("core", "core_get"), ("zenodo", "zenodo_get"), ("semantic-scholar", "semantic_scholar_get_paper"), ("eric", "eric_get_record")])
def test_get_complete_record(monkeypatch, server, tool):
    module = load_server(server)
    class Response:
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass
        def read(self):
            return json.dumps(RECORD).encode()
    monkeypatch.setattr(module.urllib.request, "urlopen", lambda *args, **kwargs: Response())
    if server == "semantic-scholar":
        monkeypatch.setattr(module, "_get", lambda *args: RECORD)
    if server == "eric":
        monkeypatch.setattr(module, "_search", lambda *args, **kwargs: {"response": {"numFound": 1, "docs": [RECORD]}})
    fn = getattr(module, tool)
    result = json.loads(fn("1", output_format="json"))
    assert result["records"] == [RECORD]
    assert result["total"] == 1
    with pytest.raises(ValueError, match="output_format"):
        fn("1", output_format="csv")
