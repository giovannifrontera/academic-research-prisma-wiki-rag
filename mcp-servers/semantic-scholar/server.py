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
import time
from datetime import datetime, timezone
from pathlib import Path
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("semantic-scholar")


def _env_key(*names: str) -> str:
    """First non-empty value: the plugin dialog (/plugin configure) wins over shell env vars."""
    for name in names:
        value = os.environ.get(name, "").strip()
        if value and not value.startswith("${"):  # unsubstituted manifest placeholder
            return value
    return ""

BASE_URL = "https://api.semanticscholar.org/graph/v1"
DEFAULT_TIMEOUT = 30
RETRIES = 3
PAGE_SIZE = 100
API_KEY = _env_key("SEMANTIC_SCHOLAR_API_KEY_PLUGIN", "SEMANTIC_SCHOLAR_API_KEY")
CONFIGURE_HINT = (
    "set the key with `/plugin configure academic-research-prisma-wiki-rag` "
    "(or export SEMANTIC_SCHOLAR_API_KEY) and restart Claude Code"
)
FIELDS = "title,authors,year,venue,abstract,externalIds,paperId"
EXPORT_FIELDS = FIELDS + ",publicationTypes,openAccessPdf,journal"

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
        for attempt in range(RETRIES + 1):
            try:
                with urllib.request.urlopen(req, timeout=DEFAULT_TIMEOUT) as resp:
                    return json.loads(resp.read().decode())
            except urllib.error.HTTPError as e:
                if e.code != 429 or attempt == RETRIES:
                    raise
                time.sleep(_retry_after(e, attempt))
    except urllib.error.HTTPError as e:
        msg = f"Semantic Scholar API error: HTTP {e.code} ({e.reason})"
        if e.code == 429 and not API_KEY:
            msg += f" — no API key configured: {CONFIGURE_HINT}"
        raise RuntimeError(msg) from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"Semantic Scholar API unreachable: {e.reason}") from e
    except TimeoutError:
        raise RuntimeError(f"Semantic Scholar API timeout after {DEFAULT_TIMEOUT}s") from None


def _retry_after(e: urllib.error.HTTPError, attempt: int) -> float:
    try:
        return min(float(e.headers.get("Retry-After", "")), 60.0)
    except (TypeError, ValueError, AttributeError):
        return 5.0 * (attempt + 1)


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
def semantic_scholar_export(
    query: str,
    output_path: str,
    year_from: int = None,
    year_to: int = None,
    fields_of_study: str = None,
    max_records: int = 10000,
) -> str:
    """
    Download ALL records matching a boolean query to a JSON file and return only
    the counts. Uses the bulk search endpoint, which (unlike semantic_scholar_search,
    a relevance search capped at 1,000) understands boolean syntax and has no
    1,000 cap, so the PRISMA download is complete and reproducible.
    Use it instead of paging semantic_scholar_search or calling the API from
    scripts: the configured API key reaches only this server, and records never
    pass through the conversation. The file holds the list of records (same
    contract as raw_*.json). Log the returned total/downloaded/query/retrieved_at.

    Query syntax (bulk): "phrase", + (AND), | (OR), - (NOT), ( ) grouping,
    e.g. ("generative AI" | chatbot) + ("higher education" | university)

    Args:
        query: Boolean query in bulk syntax
        output_path: JSON file to write (e.g. raw_semantic_scholar.json in the review folder)
        year_from: Start year
        year_to: End year
        fields_of_study: Comma-separated field(s), e.g. "Education,Computer Science"
        max_records: Safety cap on downloaded records (default 10000)
    """
    try:
        year_range = f"{year_from or ''}-{year_to or ''}" if (year_from or year_to) else None
        records, total, token, error = [], None, None, None
        while total is None or (token and len(records) < max_records):
            params = {"query": query, "year": year_range, "fieldsOfStudy": fields_of_study,
                      "fields": EXPORT_FIELDS, "token": token}
            try:
                data = _get("paper/search/bulk", params)
            except RuntimeError as e:
                if total is None:
                    raise
                error = str(e)  # keep the pages already downloaded
                break
            total = data.get("total", 0)
            records.extend((data.get("data") or [])[: max_records - len(records)])
            token = data.get("token")
        path = Path(output_path).expanduser()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(records, ensure_ascii=False, indent=1), encoding="utf-8")
        return json.dumps({
            "total": total, "downloaded": len(records), "query": query,
            "retrieved_at": datetime.now(timezone.utc).isoformat(), "error": error,
            "path": str(path.resolve()), "complete": len(records) >= total,
        }, ensure_ascii=False)
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
