"""
Semantic Scholar MCP Server
Searches Semantic Scholar (semanticscholar.org) — 200M+ papers, all disciplines.
Provides citation counts, open-access PDF links, and citation graph traversal.
API docs: https://api.semanticscholar.org/graph/v1
Optional free API key: https://www.semanticscholar.org/product/api#api-key
"""

import json
import os
import sys
import urllib.request
import urllib.parse
import urllib.error
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("semantic-scholar")

BASE_URL = "https://api.semanticscholar.org/graph/v1"
DEFAULT_TIMEOUT = 30
API_KEY = os.environ.get("S2_API_KEY", "")

PAPER_FIELDS = (
    "title,authors,year,abstract,externalIds,"
    "openAccessPdf,venue,citationCount,publicationDate"
)

if not API_KEY:
    print(
        "INFO: S2_API_KEY not set — rate limited to 100 req/5 min. "
        "Get a free key at https://www.semanticscholar.org/product/api",
        file=sys.stderr,
    )


def _headers() -> dict:
    h = {"User-Agent": "academic-prisma-workflow/1.0 (research use)"}
    if API_KEY:
        h["x-api-key"] = API_KEY
    return h


def _get(url: str) -> dict:
    req = urllib.request.Request(url, headers=_headers())
    try:
        with urllib.request.urlopen(req, timeout=DEFAULT_TIMEOUT) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"Semantic Scholar API error: HTTP {e.code} ({e.reason})") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"Semantic Scholar API unreachable: {e.reason}") from e
    except TimeoutError:
        raise RuntimeError(f"Semantic Scholar API timeout after {DEFAULT_TIMEOUT}s") from None


def _format_paper(p: dict, index: int = None) -> str:
    title = p.get("title") or "(no title)"
    authors = p.get("authors") or []
    auth_names = [a.get("name", "") for a in authors[:3]]
    auth_str = ", ".join(filter(None, auth_names))
    if len(authors) > 3:
        auth_str += " et al."
    year = str(p.get("year") or "")
    if not year:
        pub_date = p.get("publicationDate") or ""
        year = pub_date[:4] if pub_date else "n.d."
    venue = p.get("venue") or ""
    citations = p.get("citationCount")
    ext_ids = p.get("externalIds") or {}
    doi = ext_ids.get("DOI") or ""
    arxiv_id = ext_ids.get("ArXiv") or ""
    oa_pdf = (p.get("openAccessPdf") or {}).get("url") or ""
    abstract = p.get("abstract") or ""
    paper_id = p.get("paperId") or ""

    prefix = f"{index}. " if index else ""
    line = f"{prefix}**{title}**\n"
    line += f"   {auth_str or 'N/A'} ({year})\n"
    if venue:
        line += f"   Venue: {venue}\n"
    if citations is not None:
        line += f"   Citations: {citations}\n"
    if doi:
        line += f"   DOI: {doi}\n"
    if arxiv_id:
        line += f"   arXiv: https://arxiv.org/abs/{arxiv_id}\n"
    if oa_pdf:
        line += f"   PDF: {oa_pdf}\n"
    if paper_id:
        line += f"   S2: https://www.semanticscholar.org/paper/{paper_id}\n"
    if abstract:
        line += f"   Abstract: {abstract[:300]}{'...' if len(abstract) > 300 else ''}\n"
    return line


@mcp.tool()
def semantic_scholar_search(
    query: str,
    year: str = None,
    fields_of_study: str = None,
    rows: int = 10,
    offset: int = 0,
) -> str:
    """
    Search Semantic Scholar for academic papers (200M+ papers, all disciplines).
    Strong for Computer Science, AI, interdisciplinary research, citation tracking.
    Provides citation counts and open-access PDF links.

    Year format examples:
      "2023"       -> only 2023
      "2020-2025"  -> range 2020 to 2025
      "2020-"      -> from 2020 onwards

    Fields of study examples:
      "Computer Science", "Education", "Medicine", "Psychology",
      "Mathematics", "Physics", "Biology", "Economics"

    Args:
        query: Search terms (e.g. "transformer architecture education")
        year: Year or range (e.g. "2020-2025") — optional
        fields_of_study: Comma-separated fields (e.g. "Computer Science,Education") — optional
        rows: Number of results (default 10, max 100)
        offset: Pagination offset (default 0)
    """
    try:
        params: dict = {
            "query": query,
            "fields": PAPER_FIELDS,
            "limit": min(rows, 100),
            "offset": offset,
        }
        if year:
            params["year"] = year
        if fields_of_study:
            params["fieldsOfStudy"] = fields_of_study

        url = f"{BASE_URL}/paper/search?" + urllib.parse.urlencode(params)
        data = _get(url)
        papers = data.get("data") or []
        total = data.get("total") or 0

        if not papers:
            return f"Semantic Scholar — no results for: {query}"

        lines = [f"Semantic Scholar — {total} results for '{query}' (showing {len(papers)}):\n"]
        for i, p in enumerate(papers, 1):
            lines.append(_format_paper(p, i))
        return "\n".join(lines)
    except RuntimeError as e:
        return f"Error: {e}"
    except Exception as e:
        return f"Unexpected error: {e}"


@mcp.tool()
def semantic_scholar_count(
    query: str,
    year: str = None,
    fields_of_study: str = None,
) -> str:
    """
    Return total result count from Semantic Scholar without downloading records.
    Use at PRISMA Phase 1 to estimate volume before full retrieval.

    Args:
        query: Search terms
        year: Year or range (e.g. "2020-2025") — optional
        fields_of_study: Field filter (e.g. "Computer Science") — optional
    """
    try:
        params: dict = {"query": query, "fields": "title", "limit": 1, "offset": 0}
        if year:
            params["year"] = year
        if fields_of_study:
            params["fieldsOfStudy"] = fields_of_study

        url = f"{BASE_URL}/paper/search?" + urllib.parse.urlencode(params)
        data = _get(url)
        total = data.get("total") or 0
        parts = [f"Semantic Scholar — results for '{query}'"]
        if year:
            parts.append(f"[{year}]")
        if fields_of_study:
            parts.append(f"[{fields_of_study}]")
        return " ".join(parts) + f": **{total}**"
    except RuntimeError as e:
        return f"Error: {e}"
    except Exception as e:
        return f"Unexpected error: {e}"


@mcp.tool()
def semantic_scholar_get(paper_id: str) -> str:
    """
    Retrieve full metadata for a specific paper.
    Use to get complete details (all authors, references) for a paper
    identified during screening.

    Accepts multiple identifier formats:
      - Semantic Scholar paper ID (alphanumeric)
      - "DOI:10.xxxx/xxxx"   -> DOI lookup
      - "ARXIV:2301.00001"   -> arXiv lookup
      - "PMID:12345678"      -> PubMed lookup

    Args:
        paper_id: Paper identifier (see formats above)
    """
    try:
        safe_id = urllib.parse.quote(str(paper_id), safe=":")
        extended_fields = PAPER_FIELDS + ",references,fieldsOfStudy,publicationTypes"
        url = f"{BASE_URL}/paper/{safe_id}?fields={extended_fields}"
        p = _get(url)
        refs = p.get("references") or []
        fields = p.get("fieldsOfStudy") or []
        pub_types = p.get("publicationTypes") or []

        lines = [_format_paper(p)]
        if fields:
            lines.append(f"Fields of Study: {', '.join(fields)}")
        if pub_types:
            lines.append(f"Publication Types: {', '.join(pub_types)}")
        if refs:
            lines.append(f"References: {len(refs)} total")
        return "\n".join(lines)
    except RuntimeError as e:
        return f"Error: {e}"
    except Exception as e:
        return f"Unexpected error: {e}"


@mcp.tool()
def semantic_scholar_get_citations(
    paper_id: str,
    rows: int = 10,
    offset: int = 0,
) -> str:
    """
    Retrieve papers that cite a given paper (forward citations).
    Useful for snowballing search and forward citation tracking in PRISMA reviews.

    Args:
        paper_id: Semantic Scholar ID (or DOI:... / ARXIV:... / PMID:... prefix)
        rows: Number of citing papers to return (default 10, max 500)
        offset: Pagination offset (default 0)
    """
    try:
        safe_id = urllib.parse.quote(str(paper_id), safe=":")
        params = {
            "fields": "title,authors,year,externalIds,venue,citationCount",
            "limit": min(rows, 500),
            "offset": offset,
        }
        url = f"{BASE_URL}/paper/{safe_id}/citations?" + urllib.parse.urlencode(params)
        data = _get(url)
        items = data.get("data") or []

        if not items:
            return f"No citations found for paper: {paper_id}"

        lines = [f"Semantic Scholar — citing papers for {paper_id} (showing {len(items)}):\n"]
        for i, item in enumerate(items, 1):
            citing = item.get("citingPaper") or {}
            lines.append(_format_paper(citing, i))
        return "\n".join(lines)
    except RuntimeError as e:
        return f"Error: {e}"
    except Exception as e:
        return f"Unexpected error: {e}"


if __name__ == "__main__":
    mcp.run(transport="stdio")
