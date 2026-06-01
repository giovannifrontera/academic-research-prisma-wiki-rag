"""
PubMed MCP Server
Searches PubMed (pubmed.ncbi.nlm.nih.gov) — 35M+ biomedical and life sciences citations.
Also searches PubMed Central (PMC) for open-access full-text articles.
API docs: https://www.ncbi.nlm.nih.gov/books/NBK25501/
Optional free API key: https://www.ncbi.nlm.nih.gov/account/
"""

import json
import os
import sys
import urllib.request
import urllib.parse
import urllib.error
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("pubmed")

BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
DEFAULT_TIMEOUT = 30
API_KEY = os.environ.get("NCBI_API_KEY", "")
EMAIL = os.environ.get("NCBI_EMAIL", "research@academic.edu")

if not API_KEY:
    print(
        "INFO: NCBI_API_KEY not set — rate limited to 3 req/s. "
        "Get a free key at https://www.ncbi.nlm.nih.gov/account/",
        file=sys.stderr,
    )


def _base_params(db: str, retmax: int = 1, retstart: int = 0) -> dict:
    p = {
        "retmode": "json",
        "db": db,
        "retmax": retmax,
        "retstart": retstart,
        "tool": "academic-prisma-workflow",
        "email": EMAIL,
    }
    if API_KEY:
        p["api_key"] = API_KEY
    return p


def _get(url: str) -> dict:
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "academic-prisma-workflow/1.0 (research use)"},
    )
    try:
        with urllib.request.urlopen(req, timeout=DEFAULT_TIMEOUT) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"PubMed API error: HTTP {e.code} ({e.reason})") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"PubMed API unreachable: {e.reason}") from e
    except TimeoutError:
        raise RuntimeError(f"PubMed API timeout after {DEFAULT_TIMEOUT}s") from None


def _esearch(term: str, db: str = "pubmed", retmax: int = 10, retstart: int = 0) -> dict:
    params = {**_base_params(db, retmax, retstart), "term": term}
    url = f"{BASE_URL}/esearch.fcgi?" + urllib.parse.urlencode(params)
    return _get(url)


def _esummary(ids: list, db: str = "pubmed") -> dict:
    params = {**_base_params(db), "id": ",".join(ids)}
    url = f"{BASE_URL}/esummary.fcgi?" + urllib.parse.urlencode(params)
    return _get(url)


def _extract_doi(article: dict) -> str:
    for aid in article.get("articleids") or []:
        if isinstance(aid, dict) and aid.get("idtype") == "doi":
            return aid.get("value", "")
    return ""


def _format_article(uid: str, article: dict, index: int = None) -> str:
    title = article.get("title") or "(no title)"
    authors = article.get("authors") or []
    auth_authors = [a for a in authors if isinstance(a, dict) and a.get("authtype") == "Author"]
    auth_str = ", ".join(a.get("name", "") for a in auth_authors[:3])
    if len(auth_authors) > 3:
        auth_str += " et al."
    year = (article.get("pubdate") or "")[:4] or "n.d."
    journal = article.get("fulljournalname") or article.get("source") or ""
    volume = article.get("volume") or ""
    issue = article.get("issue") or ""
    pages = article.get("pages") or ""
    doi = _extract_doi(article)

    prefix = f"{index}. " if index else ""
    line = f"{prefix}**{title}**\n"
    line += f"   {auth_str or 'N/A'} ({year})\n"
    if journal:
        ref = journal
        if volume:
            ref += f" {volume}"
        if issue:
            ref += f"({issue})"
        if pages:
            ref += f":{pages}"
        line += f"   Journal: {ref}\n"
    if doi:
        line += f"   DOI: {doi}\n"
    if uid:
        line += f"   PubMed: https://pubmed.ncbi.nlm.nih.gov/{uid}/\n"
    return line


@mcp.tool()
def pubmed_search(
    query: str,
    year_from: int = None,
    year_to: int = None,
    article_type: str = None,
    rows: int = 10,
    offset: int = 0,
) -> str:
    """
    Search PubMed for biomedical and life sciences literature (35M+ citations).
    Essential for clinical studies, health sciences, and evidence-based medicine.
    Supports PubMed query syntax with field tags for precise retrieval.

    PubMed field tags:
      [ti]  — title:            "e-learning[ti]"
      [au]  — author:           "Smith JA[au]"
      [mh]  — MeSH term:        "Education, Distance[mh]"
      [pt]  — publication type: "Systematic Review[pt]"
      [ta]  — journal:          "Lancet[ta]"
      [la]  — language:         "Italian[la]"

    Boolean: AND (default), OR, NOT
    Example: "e-learning[ti] AND \"higher education\"[mh] AND 2020:2025[dp]"

    Article type values: "Systematic Review", "Meta-Analysis",
      "Randomized Controlled Trial", "Clinical Trial", "Review", "Journal Article"

    Args:
        query: Search terms with optional PubMed field tags
        year_from: Start year (e.g. 2020)
        year_to: End year (e.g. 2025)
        article_type: Publication type filter (e.g. "Systematic Review")
        rows: Number of results (default 10, max 200)
        offset: Pagination offset (default 0)
    """
    try:
        term = query
        if year_from or year_to:
            y1 = str(year_from) if year_from else "1800"
            y2 = str(year_to) if year_to else "3000"
            term += f" AND {y1}:{y2}[dp]"
        if article_type:
            term += f' AND "{article_type}"[pt]'

        search_data = _esearch(term, retmax=min(rows, 200), retstart=offset)
        result = search_data.get("esearchresult") or {}
        id_list = result.get("idlist") or []
        total = int(result.get("count") or 0)

        if not id_list:
            return f"PubMed — no results for: {query}"

        summary_data = _esummary(id_list)
        articles = summary_data.get("result") or {}
        uid_order = [u for u in (articles.get("uids") or id_list) if u != "uids"]

        lines = [f"PubMed — {total} results for '{query}' (showing {len(id_list)}):\n"]
        for i, uid in enumerate(uid_order, 1):
            article = articles.get(uid) or {}
            lines.append(_format_article(uid, article, i))
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
) -> str:
    """
    Return total result count from PubMed without downloading records.
    Use at PRISMA Phase 1 to estimate volume before full retrieval.

    Args:
        query: PubMed search terms (supports field tags)
        year_from: Start year filter
        year_to: End year filter
    """
    try:
        term = query
        if year_from or year_to:
            y1 = str(year_from) if year_from else "1800"
            y2 = str(year_to) if year_to else "3000"
            term += f" AND {y1}:{y2}[dp]"

        search_data = _esearch(term, retmax=1)
        result = search_data.get("esearchresult") or {}
        total = int(result.get("count") or 0)
        parts = [f"PubMed — results for '{query}'"]
        if year_from or year_to:
            parts.append(f"[{year_from or ''}-{year_to or ''}]")
        return " ".join(parts) + f": **{total}**"
    except RuntimeError as e:
        return f"Error: {e}"
    except Exception as e:
        return f"Unexpected error: {e}"


@mcp.tool()
def pubmed_get(pmid: str) -> str:
    """
    Retrieve full metadata for a specific PubMed article by its PMID.
    Returns all authors, MeSH terms, DOI, journal details, and PubMed link.

    Args:
        pmid: PubMed ID — numeric, e.g. "12345678" or "PMID:12345678"
    """
    try:
        clean_id = pmid.strip()
        if clean_id.upper().startswith("PMID:"):
            clean_id = clean_id[5:].strip()

        data = _esummary([clean_id])
        articles = data.get("result") or {}
        article = articles.get(clean_id) or {}
        if not article:
            return f"Article not found: PMID {pmid}"

        authors = article.get("authors") or []
        all_authors = [
            a.get("name", "") for a in authors
            if isinstance(a, dict) and a.get("authtype") == "Author"
        ]
        doi = _extract_doi(article)
        journal = article.get("fulljournalname") or article.get("source") or ""
        volume = article.get("volume") or ""
        issue = article.get("issue") or ""
        pages = article.get("pages") or ""
        issn = article.get("issn") or ""
        essn = article.get("essn") or ""
        pub_types = article.get("pubtype") or []

        lines = [
            f"**{article.get('title') or 'N/A'}**",
            f"Authors: {', '.join(all_authors) or 'N/A'}",
            f"Year: {(article.get('pubdate') or '')[:4] or 'n.d.'}",
            f"Journal: {journal}",
        ]
        if volume or issue or pages:
            lines.append(f"Vol/Issue/Pages: {volume}({issue}):{pages}")
        if doi:
            lines.append(f"DOI: {doi}")
        if issn:
            lines.append(f"ISSN: {issn}" + (f" / eISSN: {essn}" if essn else ""))
        if pub_types:
            lines.append(f"Publication Types: {', '.join(pub_types)}")
        lines.append(f"PubMed: https://pubmed.ncbi.nlm.nih.gov/{clean_id}/")
        mesh = article.get("meshheadinglist") or []
        if mesh:
            terms = [m.get("name", "") for m in mesh[:8] if isinstance(m, dict)]
            lines.append(f"MeSH Terms: {', '.join(filter(None, terms))}")
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
    PMC provides free access to millions of biomedical full texts.

    Args:
        query: Search terms (same syntax as pubmed_search)
        year_from: Start year
        year_to: End year
        rows: Number of results (default 10, max 200)
        offset: Pagination offset
    """
    try:
        term = query
        if year_from or year_to:
            y1 = str(year_from) if year_from else "1800"
            y2 = str(year_to) if year_to else "3000"
            term += f" AND {y1}:{y2}[dp]"

        search_data = _esearch(term, db="pmc", retmax=min(rows, 200), retstart=offset)
        result = search_data.get("esearchresult") or {}
        id_list = result.get("idlist") or []
        total = int(result.get("count") or 0)

        if not id_list:
            return f"PMC — no results for: {query}"

        summary_data = _esummary(id_list, db="pmc")
        articles = summary_data.get("result") or {}
        uid_order = [u for u in (articles.get("uids") or id_list) if u != "uids"]

        lines = [f"PMC — {total} open-access results for '{query}' (showing {len(id_list)}):\n"]
        for i, uid in enumerate(uid_order, 1):
            article = articles.get(uid) or {}
            title = article.get("title") or "(no title)"
            authors_list = article.get("authors") or []
            auth_names = [a.get("name", "") for a in authors_list[:3] if isinstance(a, dict)]
            auth_str = ", ".join(filter(None, auth_names))
            if len(authors_list) > 3:
                auth_str += " et al."
            year = (article.get("pubdate") or "")[:4] or "n.d."
            journal = article.get("fulljournalname") or article.get("source") or ""
            doi = _extract_doi(article)

            line = f"{i}. **{title}**\n"
            line += f"   {auth_str or 'N/A'} ({year})\n"
            if journal:
                line += f"   Journal: {journal}\n"
            if doi:
                line += f"   DOI: {doi}\n"
            line += f"   PMC: https://www.ncbi.nlm.nih.gov/pmc/articles/PMC{uid}/\n"
            lines.append(line)
        return "\n".join(lines)
    except RuntimeError as e:
        return f"Error: {e}"
    except Exception as e:
        return f"Unexpected error: {e}"


if __name__ == "__main__":
    mcp.run(transport="stdio")
