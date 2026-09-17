"""
Semantic Scholar MCP Server
Searches Semantic Scholar's academic graph — citations, references, and
metadata across ~200M papers. Free API, optional key for higher rate limits.
API docs: https://api.semanticscholar.org/api-docs/graph
Optional API key: https://www.semanticscholar.org/product/api
"""

import json
from typing import Literal
import sys
import urllib.request
import urllib.parse
import urllib.error
import os
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("semantic-scholar")

BASE_URL = "https://api.semanticscholar.org/graph/v1"
DEFAULT_TIMEOUT = 30
API_KEY = os.environ.get("SEMANTIC_SCHOLAR_API_KEY", "")
FIELDS = "title,authors,year,venue,abstract,externalIds,paperId"

if not API_KEY:
    print(
        "WARNING: SEMANTIC_SCHOLAR_API_KEY not set — low rate limits will apply. "
        "Get a free key at https://www.semanticscholar.org/product/api",
        file=sys.stderr,
    )


def _headers() -> dict:
    h = {"User-Agent": "academic-prisma-workflow/1.0 (research use)"}
    if API_KEY:
        h["x-api-key"] = API_KEY
    return h


def _get(endpoint: str, params: dict) -> dict:
    query = urllib.parse.urlencode({k: v for k, v in params.items() if v is not None})
    url = f"{BASE_URL}/{endpoint}?{query}"
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


def _format_paper(p: dict) -> str:
    if not p:
        return "(no data)"
    authors = p.get("authors", []) or []
    auth_names = [a.get("name", "") for a in authors if isinstance(a, dict)]
    auth_str = ", ".join(auth_names[:3])
    if len(auth_names) > 3:
        auth_str += " et al."
    year = p.get("year", "") or "n.d."
    title = p.get("title", "(no title)") or "(no title)"
    venue = p.get("venue", "") or ""
    abstract = p.get("abstract", "") or ""
    ext_ids = p.get("externalIds", {}) or {}
    doi = ext_ids.get("DOI", "")
    paper_id = p.get("paperId", "")

    line = f"**{title}**\n"
    line += f"   {auth_str or 'N/A'} ({year})\n"
    if venue:
        line += f"   Venue: {venue}\n"
    if doi:
        line += f"   DOI: {doi}\n"
    if paper_id:
        line += f"   Semantic Scholar: https://www.semanticscholar.org/paper/{paper_id}\n"
    if abstract:
        line += f"   Abstract: {abstract[:300]}{'...' if len(abstract) > 300 else ''}\n"
    return line


def _format_results(results: list, label: str, total: int) -> str:
    if not results:
        return f"Semantic Scholar — no results for: {label}"
    lines = [f"Semantic Scholar — {total} results for '{label}' (showing {len(results)}):\n"]
    lines.extend(_format_paper(p) for p in results)
    return "\n".join(lines)


@mcp.tool()
def semantic_scholar_search(
    query: str,
    year_from: int = None,
    year_to: int = None,
    fields_of_study: str = None,
    limit: int = 10,
    offset: int = 0,
    output_format: Literal["text", "json"] = "text",
) -> str:
    """
    Search Semantic Scholar's academic graph for papers.
    Ideal for cross-disciplinary searches and citation-based discovery.

    Args:
        query: Search terms (e.g. "artificial intelligence secondary school")
        year_from: Start year (e.g. 2015)
        year_to: End year (e.g. 2025)
        fields_of_study: Comma-separated field(s), e.g. "Education,Computer Science"
        limit: Number of results (default 10, max 100)
        offset: Pagination offset (default 0); use the JSON response's next value.
        output_format: text preview or json envelope with complete records and total.
    """
    if output_format not in ("text", "json"):
        raise ValueError("output_format must be 'text' or 'json'")
    try:
        year_range = None
        if year_from or year_to:
            year_range = f"{year_from or ''}-{year_to or ''}"
        params = {
            "query": query,
            "year": year_range,
            "fieldsOfStudy": fields_of_study,
            "limit": limit,
            "offset": offset,
            "fields": FIELDS,
        }
        data = _get("paper/search", params)
        results = data.get("data", [])
        total = data.get("total", 0)
        if output_format == "json":
            return json.dumps({"records": results, "total": total, "offset": data.get("offset", offset), "next": data.get("next")}, ensure_ascii=False)
        return _format_results(results, query, total)
    except RuntimeError as e:
        return f"Error: {e}"
    except Exception as e:
        return f"Unexpected error: {e}"


@mcp.tool()
def semantic_scholar_get_paper(paper_id: str, output_format: Literal["text", "json"] = "text") -> str:
    """
    Retrieve full metadata for a specific paper by its Semantic Scholar ID,
    DOI, or arXiv ID.
    Use to get complete details for a paper identified during screening.

    Args:
        paper_id: Semantic Scholar paperId, or prefixed external ID
            (e.g. "DOI:10.1145/...", "arXiv:2106.15928")
        output_format: text preview or json envelope with complete records and total.
    """
    if output_format not in ("text", "json"):
        raise ValueError("output_format must be 'text' or 'json'")
    try:
        safe_id = urllib.parse.quote(str(paper_id), safe=":")
        data = _get(f"paper/{safe_id}", {"fields": FIELDS})
        if output_format == "json":
            return json.dumps({"records": [data], "total": 1}, ensure_ascii=False)
        return _format_paper(data)
    except RuntimeError as e:
        return f"Error: {e}"
    except Exception as e:
        return f"Unexpected error: {e}"


@mcp.tool()
def semantic_scholar_citations(paper_id: str, limit: int = 20) -> str:
    """
    List papers that cite the given paper.
    Use for forward snowballing in a systematic review.

    Args:
        paper_id: Semantic Scholar paperId, or prefixed external ID
        limit: Number of results (default 20, max 100)
    """
    try:
        safe_id = urllib.parse.quote(str(paper_id), safe=":")
        fields = ",".join(f"citingPaper.{f}" for f in FIELDS.split(","))
        data = _get(f"paper/{safe_id}/citations", {"limit": limit, "fields": fields})
        entries = data.get("data", [])
        papers = [e.get("citingPaper", {}) for e in entries]
        return _format_results(papers, f"citing paper {paper_id}", len(papers))
    except RuntimeError as e:
        return f"Error: {e}"
    except Exception as e:
        return f"Unexpected error: {e}"


@mcp.tool()
def semantic_scholar_references(paper_id: str, limit: int = 20) -> str:
    """
    List papers cited by the given paper.
    Use for backward snowballing in a systematic review.

    Args:
        paper_id: Semantic Scholar paperId, or prefixed external ID
        limit: Number of results (default 20, max 100)
    """
    try:
        safe_id = urllib.parse.quote(str(paper_id), safe=":")
        fields = ",".join(f"citedPaper.{f}" for f in FIELDS.split(","))
        data = _get(f"paper/{safe_id}/references", {"limit": limit, "fields": fields})
        entries = data.get("data", [])
        papers = [e.get("citedPaper", {}) for e in entries]
        return _format_results(papers, f"references of paper {paper_id}", len(papers))
    except RuntimeError as e:
        return f"Error: {e}"
    except Exception as e:
        return f"Unexpected error: {e}"


if __name__ == "__main__":
    mcp.run(transport="stdio")
