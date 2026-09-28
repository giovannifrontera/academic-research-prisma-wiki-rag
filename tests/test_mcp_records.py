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
OPENAIRE = {"id": "oa-1", "mainTitle": "Study", "descriptions": [f"<jats:p>{ABSTRACT}</jats:p>"],
            "authors": [{"fullName": "A"}], "publicationDate": "2024-05-01",
            "pids": [{"scheme": "doi", "value": "10.1/oa"}], "bestAccessRight": {"label": "OPEN"}}


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
    ("openaire", "openaire_search", "_request", {"header": {"numFound": 42}, "results": [OPENAIRE]}, None),
])
def test_search_complete_records_and_registered_schema(monkeypatch, server, tool, helper, data, expected):
    module = load_server(server)
    monkeypatch.setattr(module, helper, lambda *args, **kwargs: data)
    fn = getattr(module, tool)
    result = json.loads(fn("study", output_format="json"))
    assert result["total"] == 42
    assert result["records"] == [expected or module._parse(OPENAIRE)]
    assert ABSTRACT.strip() in json.dumps(result)  # complete, not truncated
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


ARXIV_FEED = f"""<feed xmlns="http://www.w3.org/2005/Atom" xmlns:opensearch="http://a9.com/-/spec/opensearch/1.1/"
 xmlns:arxiv="http://arxiv.org/schemas/atom"><opensearch:totalResults>42</opensearch:totalResults>
<entry><id>http://arxiv.org/abs/2301.00001v1</id><published>2023-01-01T00:00:00Z</published>
<title>Study</title><summary>{ABSTRACT}</summary><author><name>A</name></author><arxiv:doi>10.1/x</arxiv:doi>
<link title="pdf" href="http://arxiv.org/pdf/2301.00001v1"/><arxiv:primary_category term="cs.CY"/></entry></feed>"""

PUBMED_ARTICLE = """<PubmedArticle><MedlineCitation><PMID>{p}</PMID><Article>
<Journal><JournalIssue><PubDate><Year>2024</Year></PubDate></JournalIssue><Title>J</Title></Journal>
<ArticleTitle>Study {p}</ArticleTitle><Abstract><AbstractText Label="METHODS">{abstract}</AbstractText></Abstract>
<AuthorList><Author><LastName>Rossi</LastName><Initials>M</Initials></Author></AuthorList></Article></MedlineCitation>
<PubmedData><ArticleIdList><ArticleId IdType="doi">10.1/{p}</ArticleId><ArticleId IdType="pmc">PMC{p}</ArticleId>
</ArticleIdList></PubmedData></PubmedArticle>"""
PUBMED_XML = "<PubmedArticleSet>" + "".join(
    PUBMED_ARTICLE.format(p=p, abstract=ABSTRACT) for p in ("2", "1")) + "</PubmedArticleSet>"


def _check_json_contract(module, fn, tool):
    assert ABSTRACT not in fn("study")  # text preview stays the default
    with pytest.raises(ValueError, match="output_format"):
        fn("study", output_format="csv")
    schema = next(t.inputSchema for t in asyncio.run(module.mcp.list_tools()) if t.name == tool)
    assert schema["properties"]["output_format"]["enum"] == ["text", "json"]
    assert schema["properties"]["output_format"]["default"] == "text"


def test_arxiv_search_complete_records(monkeypatch):
    import xml.etree.ElementTree as ET
    module = load_server("arxiv")
    seen = {}
    def fake_fetch(params):
        seen.update(params)
        return ET.fromstring(ARXIV_FEED)
    monkeypatch.setattr(module, "_fetch", fake_fetch)
    result = json.loads(module.arxiv_search("spaced repetition", year_from=2020, output_format="json"))
    assert seen["search_query"].startswith("all:spaced AND all:repetition AND submittedDate:[202001010000")
    assert result["total"] == 42
    rec = result["records"][0]
    assert rec["abstract"] == ABSTRACT.strip() and rec["year"] == "2023" and rec["doi"] == "10.1/x"
    assert rec["authors"] == [{"name": "A"}] and rec["fulltext_url"].endswith("2301.00001v1")
    assert json.loads(module.arxiv_get("2301.00001", output_format="json"))["total"] == 1
    _check_json_contract(module, module.arxiv_search, "arxiv_search")
    _check_json_contract(module, module.arxiv_get, "arxiv_get")


def test_arxiv_explicit_syntax_passes_through():
    module = load_server("arxiv")
    assert module._build_query('ti:"spaced repetition" OR abs:retrieval') == 'ti:"spaced repetition" OR abs:retrieval'
    assert module._build_query("memory", category="cs.CY") == "cat:cs.CY AND (all:memory)"


def test_pubmed_search_complete_records_in_relevance_order(monkeypatch):
    import xml.etree.ElementTree as ET
    module = load_server("pubmed")
    monkeypatch.setattr(module, "_esearch", lambda *a, **k: {"count": "42", "idlist": ["1", "2"]})
    monkeypatch.setattr(module, "_efetch", lambda ids: ET.fromstring(PUBMED_XML))
    result = json.loads(module.pubmed_search("study", output_format="json"))
    assert result["total"] == 42
    assert [r["pmid"] for r in result["records"]] == ["1", "2"]  # esearch order, not efetch order
    rec = result["records"][0]
    assert rec["abstract"] == "METHODS: " + ABSTRACT.strip()
    assert rec["doi"] == "10.1/1" and rec["pmcid"] == "PMC1" and rec["year"] == "2024"
    assert rec["authors"][0]["name"] == "Rossi M"
    assert json.loads(module.pubmed_get("PMID:1", output_format="json"))["records"][0]["pmid"] == "1"
    _check_json_contract(module, module.pubmed_search, "pubmed_search")
    _check_json_contract(module, module.pubmed_get, "pubmed_get")


def test_openaire_graph_api_params_and_normalization(monkeypatch):
    # The legacy /search/publications API was retired on 2026-05-31.
    module = load_server("openaire")
    assert "/graph/" in module.SEARCH_API
    seen = {}
    monkeypatch.setattr(module, "_request", lambda params: seen.update(params) or
                        {"header": {"numFound": 1}, "results": [OPENAIRE]})
    rec = json.loads(module.openaire_search("ai elearning", year_from=2020, year_to=2026, country="IT",
                                            open_access=True, output_format="json"))["records"][0]
    assert seen["search"] == "ai elearning" and seen["type"] == "publication"
    assert seen["fromPublicationDate"] == "2020" and seen["toPublicationDate"] == "2026"
    assert seen["countryCode"] == "IT" and seen["bestOpenAccessRightLabel"] == "OPEN"
    assert rec["abstract"] == ABSTRACT.strip() and "<" not in rec["abstract"]
    assert rec["doi"] == "10.1/oa" and rec["year"] == "2024" and rec["open_access"] is True
    module.openaire_search("x", open_access=False)
    assert "OPEN" not in seen["bestOpenAccessRightLabel"]
