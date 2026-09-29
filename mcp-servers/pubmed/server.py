"""
PubMed MCP Server
Searches PubMed (pubmed.ncbi.nlm.nih.gov) — 35M+ biomedical and life sciences citations.
Also searches PubMed Central (PMC) for open-access full-text articles.
API docs: https://www.ncbi.nlm.nih.gov/books/NBK25501/
Optional free API key (3 -> 10 req/s): https://www.ncbi.nlm.nih.gov/account/
"""

import json
import os
import sys
from typing import Literal
import urllib.request
import urllib.parse
import urllib.error
import xml.etree.ElementTree as ET
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("pubmed")


def _env_key(*names: str) -> str:
    """First non-empty value: the plugin dialog (/plugin configure) wins over shell env vars."""
    for name in names:
        value = os.environ.get(name, "").strip()
        if value and not value.startswith("${"):  # unsubstituted manifest placeholder
            return value
    return ""

BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
DEFAULT_TIMEOUT = 30
API_KEY = _env_key("NCBI_API_KEY_PLUGIN", "NCBI_API_KEY")
EMAIL = _env_key("NCBI_EMAIL_PLUGIN", "NCBI_EMAIL")
CONFIGURE_HINT = (
    "set the key with `/plugin configure academic-research-prisma-wiki-rag` "
    "(or export NCBI_API_KEY) and restart Claude Code"
)

if not API_KEY:
    print(
        "INFO: NCBI_API_KEY not set — rate limited to 3 req/s. "
        "Get a free key at https://www.ncbi.nlm.nih.gov/account/",
        file=sys.stderr,
    )


def _params(db: str, **extra) -> dict:
    p = {"db": db, "tool": "academic-research-prisma-wiki-rag", **extra}
    if EMAIL:
        p["email"] = EMAIL
    if API_KEY:
        p["api_key"] = API_KEY
    return p


def _request(endpoint: str, params: dict) -> bytes:
    url = f"{BASE_URL}/{endpoint}?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": "academic-research-prisma-wiki-rag (research use)"})
    try:
        with urllib.request.urlopen(req, timeout=DEFAULT_TIMEOUT) as resp:
            return resp.read()
    except urllib.error.HTTPError as e:
        msg = f"PubMed API error: HTTP {e.code} ({e.reason})"
        if e.code == 429 and not API_KEY:
            msg += f" — no API key configured: {CONFIGURE_HINT}"
        raise RuntimeError(msg) from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"PubMed API unreachable: {e.reason}") from e
    except TimeoutError:
        raise RuntimeError(f"PubMed API timeout after {DEFAULT_TIMEOUT}s") from None


def _esearch(term: str, db: str = "pubmed", retmax: int = 10, retstart: int = 0) -> dict:
    data = json.loads(_request("esearch.fcgi", _params(db, term=term, retmode="json",
                                                      retmax=retmax, retstart=retstart)))
    return data.get("esearchresult") or {}


def _efetch(ids: list) -> ET.Element:
    """PubMed XML — the only E-utility that returns abstracts."""
    return ET.fromstring(_request("efetch.fcgi", _params("pubmed", id=",".join(ids), retmode="xml")))


def _esummary(ids: list, db: str) -> dict:
    data = json.loads(_request("esummary.fcgi", _params(db, id=",".join(ids), retmode="json")))
    return data.get("result") or {}


def _text(el) -> str:
    return " ".join("".join(el.itertext()).split()) if el is not None else ""


def _parse(article: ET.Element) -> dict:
    """Complete PubMed record from a <PubmedArticle> element."""
    cit = article.find("MedlineCitation")
    art = cit.find("Article") if cit is not None else None
    if cit is None or art is None:
        return {}
    pmid = _text(cit.find("PMID"))
    sections = []
    for ab in art.findall("Abstract/AbstractText"):
        label, body = ab.get("Label"), _text(ab)
        if body:
            sections.append(f"{label}: {body}" if label else body)
    pub_date = art.find("Journal/JournalIssue/PubDate")
    year = _text(pub_date.find("Year")) if pub_date is not None else ""
    if not year and pub_date is not None:
        year = _text(pub_date.find("MedlineDate"))[:4]
    authors = []
    for a in art.findall("AuthorList/Author"):
        name = " ".join(filter(None, [_text(a.find("LastName")), _text(a.find("Initials"))])) \
            or _text(a.find("CollectiveName"))
        if name:
            authors.append({"name": name, "affiliation": _text(a.find("AffiliationInfo/Affiliation"))})
    ids = {i.get("IdType"): _text(i) for i in article.findall("PubmedData/ArticleIdList/ArticleId")}
    doi = ids.get("doi") or next(
        (_text(e) for e in art.findall("ELocationID") if e.get("EIdType") == "doi"), "")
    pmcid = ids.get("pmc", "")
    issue = art.find("Journal/JournalIssue")
    return {
        "pmid": pmid,
        "title": _text(art.find("ArticleTitle")),
        "abstract": "\n".join(sections),
        "year": year,
        "doi": doi,
        "pmcid": pmcid,
        "journal": _text(art.find("Journal/Title")),
        "volume": _text(issue.find("Volume")) if issue is not None else "",
        "issue": _text(issue.find("Issue")) if issue is not None else "",
        "pages": _text(art.find("Pagination/MedlinePgn")),
        "language": _text(art.find("Language")),
        "authors": authors,
        "publication_types": [_text(p) for p in art.findall("PublicationTypeList/PublicationType")],
        "mesh_terms": [_text(m.find("DescriptorName")) for m in cit.findall("MeshHeadingList/MeshHeading")],
        "keywords": [_text(k) for k in cit.findall("KeywordList/Keyword")],
        "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" if pmid else "",
        "pmc_url": f"https://pmc.ncbi.nlm.nih.gov/articles/{pmcid}/" if pmcid else "",
    }


def _records(ids: list) -> list:
    if not ids:
        return []
    root = _efetch(ids)
    by_pmid = {r["pmid"]: r for r in (_parse(a) for a in root.findall("PubmedArticle")) if r}
    return [by_pmid[i] for i in ids if i in by_pmid]  # keep esearch relevance order


def _format(r: dict, index: int = None) -> str:
    names = [a["name"] for a in r["authors"]]
    auth_str = ", ".join(names[:3]) + (" et al." if len(names) > 3 else "")
    prefix = f"{index}. " if index else ""
    line = f"{prefix}**{r['title'] or '(no title)'}**\n"
    line += f"   {auth_str or 'N/A'} ({r['year'] or 'n.d.'})\n"
    if r["journal"]:
        ref = r["journal"] + (f" {r['volume']}" if r["volume"] else "") \
            + (f"({r['issue']})" if r["issue"] else "") + (f":{r['pages']}" if r["pages"] else "")
        line += f"   Journal: {ref}\n"
    if r["doi"]:
        line += f"   DOI: {r['doi']}\n"
    line += f"   PubMed: {r['url']}\n"
    if r["pmc_url"]:
        line += f"   PMC (open access): {r['pmc_url']}\n"
    if r["abstract"]:
        line += f"   Abstract: {r['abstract'][:300]}{'...' if len(r['abstract']) > 300 else ''}\n"
    return line


def _term(query: str, year_from: int = None, year_to: int = None, article_type: str = None) -> str:
    term = query
    if year_from or year_to:
        term += f" AND {year_from or 1800}:{year_to or 3000}[dp]"
    if article_type:
        term += f' AND "{article_type}"[pt]'
    return term


def _check_format(output_format: str):
    if output_format not in ("text", "json"):
        raise ValueError("output_format must be 'text' or 'json'")


@mcp.tool()
def pubmed_search(
    query: str,
    year_from: int = None,
    year_to: int = None,
    article_type: str = None,
    rows: int = 10,
    offset: int = 0,
    output_format: Literal["text", "json"] = "text",
) -> str:
    """
    Search PubMed for biomedical, health, psychology and life sciences literature.
    Returns complete records with abstracts. Supports PubMed field tags:
      [ti] title, [tiab] title/abstract, [au] author, [mh] MeSH term,
      [pt] publication type, [ta] journal, [la] language
    Boolean: AND (default), OR, NOT
    Example: "e-learning[tiab] AND \"Education, Medical\"[mh]"

    Article type values: "Systematic Review", "Meta-Analysis",
      "Randomized Controlled Trial", "Clinical Trial", "Review", "Journal Article"

    Args:
        query: Search terms with optional PubMed field tags
        year_from: Start publication year (e.g. 2020)
        year_to: End publication year (e.g. 2025)
        article_type: Publication type filter (e.g. "Systematic Review")
        rows: Number of results (default 10, max 200)
        offset: Pagination offset (default 0)
        output_format: text preview or json envelope with complete records and total.
    """
    _check_format(output_format)
    try:
        rows = max(1, min(rows, 200))
        result = _esearch(_term(query, year_from, year_to, article_type), retmax=rows, retstart=offset)
        total = int(result.get("count") or 0)
        records = _records(result.get("idlist") or [])
        if output_format == "json":
            return json.dumps({
                "records": records, "total": total, "offset": offset, "rows": rows,
                "query_translation": result.get("querytranslation", ""),
            }, ensure_ascii=False)
        if not records:
            return f"PubMed — no results for: {query}"
        lines = [f"PubMed — {total} results for '{query}' (showing {len(records)}):\n"]
        lines += [_format(r, i) for i, r in enumerate(records, 1)]
        return "\n".join(lines)
    except RuntimeError as e:
        return f"Error: {e}"
    except Exception as e:
        return f"Unexpected error: {e}"


@mcp.tool()
def pubmed_count(
    query: str,
    year_from: int = None,
    year_to: int = None,
    article_type: str = None,
) -> str:
    """
    Return total result count from PubMed without downloading records.
    Use at PRISMA Phase 1 to estimate volume before full retrieval.

    Args:
        query: PubMed search terms (supports field tags)
        year_from: Start year filter
        year_to: End year filter
        article_type: Publication type filter
    """
    try:
        result = _esearch(_term(query, year_from, year_to, article_type), retmax=0)
        parts = [f"PubMed — results for '{query}'"]
        if article_type:
            parts.append(f"[{article_type}]")
        if year_from or year_to:
            parts.append(f"[{year_from or ''}-{year_to or ''}]")
        return " ".join(parts) + f": **{int(result.get('count') or 0)}**"
    except RuntimeError as e:
        return f"Error: {e}"
    except Exception as e:
        return f"Unexpected error: {e}"


@mcp.tool()
def pubmed_get(pmid: str, output_format: Literal["text", "json"] = "text") -> str:
    """
    Retrieve the complete record of a PubMed article: all authors, abstract,
    MeSH terms, DOI, PMC ID and journal details.

    Args:
        pmid: PubMed ID — numeric, e.g. "12345678" or "PMID:12345678"
        output_format: text details or json envelope with complete records and total.
    """
    _check_format(output_format)
    try:
        clean_id = pmid.strip()
        if clean_id.upper().startswith("PMID:"):
            clean_id = clean_id[5:].strip()
        records = _records([clean_id])
        if output_format == "json":
            return json.dumps({"records": records, "total": len(records)}, ensure_ascii=False)
        if not records:
            return f"Article not found: PMID {pmid}"
        r = records[0]
        lines = [_format({**r, "abstract": ""}).rstrip()]
        lines.append(f"Authors: {', '.join(a['name'] for a in r['authors']) or 'N/A'}")
        if r["publication_types"]:
            lines.append(f"Publication Types: {', '.join(r['publication_types'])}")
        if r["mesh_terms"]:
            lines.append(f"MeSH Terms: {', '.join(r['mesh_terms'])}")
        if r["abstract"]:
            lines.append(f"\nAbstract:\n{r['abstract']}")
        return "\n".join(lines)
    except RuntimeError as e:
        return f"Error: {e}"
    except Exception as e:
        return f"Unexpected error: {e}"


@mcp.tool()
def pubmed_search_pmc(
    query: str,
    year_from: int = None,
    year_to: int = None,
    rows: int = 10,
    offset: int = 0,
) -> str:
    """
    Search PubMed Central (PMC) for open-access full-text articles.
    Use when full-text eligibility screening requires the complete article.

    Args:
        query: Search terms (same syntax as pubmed_search)
        year_from: Start year
        year_to: End year
        rows: Number of results (default 10, max 200)
        offset: Pagination offset
    """
    try:
        result = _esearch(_term(query, year_from, year_to), db="pmc",
                          retmax=max(1, min(rows, 200)), retstart=offset)
        id_list = result.get("idlist") or []
        total = int(result.get("count") or 0)
        if not id_list:
            return f"PMC — no results for: {query}"
        articles = _esummary(id_list, db="pmc")
        lines = [f"PMC — {total} open-access results for '{query}' (showing {len(id_list)}):\n"]
        for i, uid in enumerate(id_list, 1):
            a = articles.get(uid) or {}
            names = [x.get("name", "") for x in (a.get("authors") or []) if isinstance(x, dict)]
            auth_str = ", ".join(filter(None, names[:3])) + (" et al." if len(names) > 3 else "")
            doi = next((x.get("value", "") for x in (a.get("articleids") or [])
                        if isinstance(x, dict) and x.get("idtype") == "doi"), "")
            line = f"{i}. **{a.get('title') or '(no title)'}**\n"
            line += f"   {auth_str or 'N/A'} ({(a.get('pubdate') or '')[:4] or 'n.d.'})\n"
            if a.get("fulljournalname") or a.get("source"):
                line += f"   Journal: {a.get('fulljournalname') or a.get('source')}\n"
            if doi:
                line += f"   DOI: {doi}\n"
            line += f"   PMC: https://pmc.ncbi.nlm.nih.gov/articles/PMC{uid}/\n"
            lines.append(line)
        return "\n".join(lines)
    except RuntimeError as e:
        return f"Error: {e}"
    except Exception as e:
        return f"Unexpected error: {e}"


if __name__ == "__main__":
    mcp.run(transport="stdio")
