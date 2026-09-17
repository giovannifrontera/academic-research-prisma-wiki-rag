"""
CORE MCP Server
Searches CORE (core.ac.uk) — the world's largest aggregator of open access
research. Provides direct access to full-text papers from Italian and
international institutional repositories.
API docs: https://api.core.ac.uk/docs/v3
Requires a free API key: https://core.ac.uk/services/api
"""

import json
from typing import Literal
import sys
import urllib.request
import urllib.parse
import urllib.error
import os
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("core")

BASE_URL = "https://api.core.ac.uk/v3"
DEFAULT_TIMEOUT = 30
API_KEY = os.environ.get("CORE_API_KEY", "")

if not API_KEY:
    print(
        "WARNING: CORE_API_KEY not set — severe rate limits will apply. "
        "Get a free key at https://core.ac.uk/services/api",
        file=sys.stderr,
    )


def _headers() -> dict:
    h = {
        "Content-Type": "application/json",
        "User-Agent": "academic-prisma-workflow/1.0 (research use)",
    }
    if API_KEY:
        h["Authorization"] = f"Bearer {API_KEY}"
    return h


def _post(endpoint: str, payload: dict) -> dict:
    url = f"{BASE_URL}/{endpoint}"
    data = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data, headers=_headers(), method="POST")
    try:
        with urllib.request.urlopen(req, timeout=DEFAULT_TIMEOUT) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"CORE API error: HTTP {e.code} ({e.reason})") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"CORE API unreachable: {e.reason}") from e
    except TimeoutError:
        raise RuntimeError(f"CORE API timeout after {DEFAULT_TIMEOUT}s") from None


def _format_results(results: list, label: str, total: int) -> str:
    if not results:
        return f"CORE — no results for: {label}"
    lines = [f"CORE — {total} results for '{label}' (showing {len(results)}):\n"]
    for i, r in enumerate(results, 1):
        authors = r.get("authors", [])
        if isinstance(authors, list):
            auth_names = [a.get("name", "") if isinstance(a, dict) else str(a) for a in authors[:3]]
            auth_str = ", ".join(filter(None, auth_names))
            if len(authors) > 3:
                auth_str += " et al."
        else:
            auth_str = ""

        year = r.get("yearPublished", "") or ""
        title = r.get("title", "(no title)") or "(no title)"
        abstract = r.get("abstract", "") or ""
        doi = r.get("doi", "") or ""
        url_link = r.get("sourceFulltextUrls", [None])[0] if r.get("sourceFulltextUrls") else ""
        journal = r.get("journals", [{}])[0].get("title", "") if r.get("journals") else ""
        core_id = r.get("id", "")

        line = f"{i}. **{title}**\n"
        line += f"   {auth_str or 'N/A'} ({year or 'n.d.'})\n"
        if journal:
            line += f"   Journal: {journal}\n"
        if doi:
            line += f"   DOI: {doi}\n"
        if core_id:
            line += f"   CORE: https://core.ac.uk/works/{core_id}\n"
        if url_link:
            line += f"   Fulltext: {url_link}\n"
        if abstract:
            line += f"   Abstract: {abstract[:300]}{'...' if len(abstract) > 300 else ''}\n"
        lines.append(line)
    return "\n".join(lines)


@mcp.tool()
def core_search(
    query: str,
    year_from: int = None,
    year_to: int = None,
    language: str = None,
    rows: int = 10,
    offset: int = 0,
    output_format: Literal["text", "json"] = "text",
) -> str:
    """
    Search CORE for open access full-text papers.
    CORE aggregates Italian institutional repositories (IRIS network) and
    thousands of global repositories. Ideal for finding full-text OA papers.
    Requires CORE_API_KEY environment variable (free at core.ac.uk/services/api).

    Args:
        query: Search terms (e.g. "artificial intelligence secondary school")
        year_from: Start year (e.g. 2015)
        year_to: End year (e.g. 2025)
        language: Language code (e.g. "it" for Italian, "en" for English)
        rows: Number of results (default 10, max 100)
        offset: Pagination offset (default 0)
        output_format: text preview or json envelope with complete records and total.
    """
    if output_format not in ("text", "json"):
        raise ValueError("output_format must be 'text' or 'json'")
    try:
        filters = []
        if year_from:
            filters.append({"field": "yearPublished", "value": year_from, "operation": "GREATER_OR_EQUAL"})
        if year_to:
            filters.append({"field": "yearPublished", "value": year_to, "operation": "LESS_OR_EQUAL"})
        if language:
            filters.append({"field": "language.code", "value": language, "operation": "EQUALS"})
        payload = {"q": query, "limit": rows, "offset": offset, "filters": filters}
        data = _post("search/works", payload)
        results = data.get("results", [])
        total = data.get("totalHits", 0)
        if output_format == "json":
            return json.dumps({"records": results, "total": total, "offset": offset, "limit": rows}, ensure_ascii=False)
        return _format_results(results, query, total)
    except RuntimeError as e:
        return f"Error: {e}"
    except Exception as e:
        return f"Unexpected error: {e}"


@mcp.tool()
def core_count(
    query: str,
    year_from: int = None,
    year_to: int = None,
) -> str:
    """
    Return total result count from CORE without downloading records.
    Use at PRISMA Phase 1 to estimate volume.

    Args:
        query: Search terms
        year_from: Start year
        year_to: End year
    """
    try:
        filters = []
        if year_from:
            filters.append({"field": "yearPublished", "value": year_from, "operation": "GREATER_OR_EQUAL"})
        if year_to:
            filters.append({"field": "yearPublished", "value": year_to, "operation": "LESS_OR_EQUAL"})
        payload = {"q": query, "limit": 1, "offset": 0, "filters": filters}
        data = _post("search/works", payload)
        total = data.get("totalHits", 0)
        parts = [f"CORE — results for '{query}'"]
        if year_from or year_to:
            parts.append(f"[{year_from or ''}-{year_to or ''}]")
        return " ".join(parts) + f": **{total}**"
    except RuntimeError as e:
        return f"Error: {e}"
    except Exception as e:
        return f"Unexpected error: {e}"


@mcp.tool()
def core_get(work_id: str, output_format: Literal["text", "json"] = "text") -> str:
    """
    Retrieve full metadata for a specific CORE work by its ID.
    Use to get complete details (fulltext URL, affiliations) for a paper
    identified during screening.

    Args:
        work_id: CORE work ID (numeric, from core_search results)
        output_format: text details or json envelope with complete records and total.
    """
    if output_format not in ("text", "json"):
        raise ValueError("output_format must be 'text' or 'json'")
    try:
        safe_id = urllib.parse.quote(str(work_id), safe="")
        url = f"{BASE_URL}/works/{safe_id}"
        req = urllib.request.Request(url, headers=_headers())
        try:
            with urllib.request.urlopen(req, timeout=DEFAULT_TIMEOUT) as resp:
                r = json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            raise RuntimeError(f"CORE API error: HTTP {e.code} ({e.reason})") from e
        except urllib.error.URLError as e:
            raise RuntimeError(f"CORE API unreachable: {e.reason}") from e
        except TimeoutError:
            raise RuntimeError(f"CORE API timeout after {DEFAULT_TIMEOUT}s") from None

        if output_format == "json":
            return json.dumps({"records": [r], "total": 1}, ensure_ascii=False)
        authors = r.get("authors", [])
        auth_names = [a.get("name", "") if isinstance(a, dict) else str(a) for a in authors]
        abstract = r.get("abstract", "") or ""
        fulltext_urls = r.get("sourceFulltextUrls", []) or []
        affiliations = []
        for a in authors:
            if isinstance(a, dict):
                for aff in a.get("affiliations", []):
                    if isinstance(aff, dict) and aff.get("name"):
                        affiliations.append(aff["name"])

        lines = [
            f"**{r.get('title', 'N/A')}**",
            f"Authors: {', '.join(auth_names) or 'N/A'}",
            f"Year: {r.get('yearPublished', 'n.d.')}",
            f"DOI: {r.get('doi', 'N/A')}",
            f"CORE ID: {r.get('id', 'N/A')}",
            f"Language: {r.get('language', {}).get('name', 'N/A') if isinstance(r.get('language'), dict) else 'N/A'}",
        ]
        if affiliations:
            lines.append(f"Affiliations: {'; '.join(set(affiliations))}")
        if fulltext_urls:
            lines.append(f"Fulltext: {fulltext_urls[0]}")
        if abstract:
            lines.append(f"\nAbstract:\n{abstract}")
        return "\n".join(lines)
    except RuntimeError as e:
        return f"Error: {e}"
    except Exception as e:
        return f"Unexpected error: {e}"


if __name__ == "__main__":
    mcp.run(transport="stdio")
