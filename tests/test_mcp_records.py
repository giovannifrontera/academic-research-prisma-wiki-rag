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


def test_doaj_url_puts_query_in_path_with_explicit_year_bounds(monkeypatch):
    # DOAJ answers 404 to ?q=, 400 to sort=score and rejects open "*" ranges.
    module = load_server("doaj")
    urls = []
    class Response:
        def __enter__(self): return self
        def __exit__(self, *a): pass
        def read(self): return json.dumps({"results": [], "total": 0}).encode()
    monkeypatch.setattr(module.urllib.request, "urlopen",
                        lambda req, **k: urls.append(req.full_url) or Response())
    module.doaj_search_articles("ai elearning", year_from=2020, country_publisher="IT", output_format="json")
    url = module.urllib.parse.unquote(urls[0])
    assert url.startswith("https://doaj.org/api/v4/search/articles/ai elearning AND bibjson.year:[2020 TO 9999]")
    assert "bibjson.journal.country:IT" in url
    assert "?q=" not in url and "sort=" not in url and "*" not in url


@pytest.mark.parametrize("server", ["eric", "zenodo"])
def test_plain_queries_are_anded(server):
    # Both backends OR bare terms: "ai higher education" matched ~1.7M ERIC records.
    module = load_server(server)
    assert module._and_terms("ai higher education") == "ai AND higher AND education"
    assert module._and_terms("e-learning ai") == "e-learning AND ai"
    for explicit in ('"spaced repetition"', "ai OR ml", "title:chatbot", "ai -robots", "(a b)"):
        assert module._and_terms(explicit) == explicit


def test_eric_search_sends_anded_query(monkeypatch):
    module = load_server("eric")
    seen = []
    monkeypatch.setattr(module, "_search", lambda q, **k: seen.append(q) or {"response": {"docs": [], "numFound": 0}})
    module.eric_search("ai higher education")
    module.eric_advanced_search("ai higher education", year_from=2020)
    assert seen[0] == "ai AND higher AND education"
    assert seen[1].startswith("(ai AND higher AND education) AND publicationdateyear:[2020")


@pytest.mark.parametrize("server,plugin_var,env_var", [
    ("core", "CORE_API_KEY_PLUGIN", "CORE_API_KEY"),
    ("semantic-scholar", "SEMANTIC_SCHOLAR_API_KEY_PLUGIN", "SEMANTIC_SCHOLAR_API_KEY"),
    ("pubmed", "NCBI_API_KEY_PLUGIN", "NCBI_API_KEY"),
])
def test_api_key_from_plugin_dialog_then_env(monkeypatch, server, plugin_var, env_var):
    monkeypatch.setenv(plugin_var, "from-dialog")
    monkeypatch.setenv(env_var, "from-env")
    assert load_server(server).API_KEY == "from-dialog"
    monkeypatch.setenv(plugin_var, "${user_config.x}")  # placeholder left unsubstituted
    assert load_server(server).API_KEY == "from-env"
    monkeypatch.delenv(env_var)
    assert load_server(server).API_KEY == ""


def test_rate_limit_without_key_tells_how_to_configure(monkeypatch):
    import urllib.error
    monkeypatch.delenv("CORE_API_KEY_PLUGIN", raising=False)
    monkeypatch.delenv("CORE_API_KEY", raising=False)
    core = load_server("core")

    def too_many(*args, **kwargs):
        raise urllib.error.HTTPError("u", 429, "Too Many Requests", {}, None)
    monkeypatch.setattr(core.urllib.request, "urlopen", too_many)
    monkeypatch.setattr(core.time, "sleep", lambda s: None)
    with pytest.raises(RuntimeError, match="/plugin configure"):
        core._post("search/works", {})


def test_core_export_pages_to_file_without_heavy_fields(monkeypatch, tmp_path):
    core = load_server("core")
    heavy = dict(RECORD, fullText="x" * 10_000, references=[{"id": n} for n in range(50)])
    calls = []
    def fake_post(endpoint, payload):
        calls.append(payload["offset"])
        return {"results": [heavy] * min(payload["limit"], 250 - payload["offset"]), "totalHits": 250}
    monkeypatch.setattr(core, "_post", fake_post)
    out = tmp_path / "sub" / "raw_core.json"
    summary = json.loads(core.core_export("study", str(out), year_from=2020))
    saved = json.loads(out.read_text(encoding="utf-8"))
    assert calls == [0, 100, 200]
    assert summary["downloaded"] == len(saved) == 250 and summary["complete"]
    assert saved[0] == RECORD  # fullText/references dropped, rest intact
    assert summary["total"] == 250 and summary["filters"][0]["value"] == 2020


def test_core_export_keeps_partial_pages_on_error(monkeypatch, tmp_path):
    core = load_server("core")
    def fake_post(endpoint, payload):
        if payload["offset"] >= 200:
            raise RuntimeError("CORE API error: HTTP 500")
        return {"results": [RECORD] * payload["limit"], "totalHits": 300}
    monkeypatch.setattr(core, "_post", fake_post)
    out = tmp_path / "raw_core.json"
    summary = json.loads(core.core_export("study", str(out)))
    assert summary["downloaded"] == 200 and not summary["complete"] and "500" in summary["error"]
    assert len(json.loads(out.read_text(encoding="utf-8"))) == 200


def test_semantic_scholar_export_follows_next_until_cap(monkeypatch, tmp_path):
    s2 = load_server("semantic-scholar")
    def fake_get(endpoint, params):
        off = params["offset"]
        return {"data": [RECORD] * params["limit"], "total": 5000, "offset": off, "next": off + params["limit"]}
    monkeypatch.setattr(s2, "_get", fake_get)
    summary = json.loads(s2.semantic_scholar_export("study", str(tmp_path / "raw_s2.json")))
    assert summary["downloaded"] == 1000 and summary["capped"] and not summary["complete"]


def test_rate_limit_is_retried(monkeypatch):
    import urllib.error
    core = load_server("core")
    attempts = []
    class Response:
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass
        def read(self):
            return b'{"results": [], "totalHits": 0}'
    def flaky(*args, **kwargs):
        attempts.append(1)
        if len(attempts) < 3:
            raise urllib.error.HTTPError("u", 429, "Too Many Requests", {"Retry-After": "0"}, None)
        return Response()
    monkeypatch.setattr(core.urllib.request, "urlopen", flaky)
    monkeypatch.setattr(core.time, "sleep", lambda s: None)
    assert core._post("search/works", {}) == {"results": [], "totalHits": 0}
    assert len(attempts) == 3
