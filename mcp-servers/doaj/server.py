"""
DOAJ MCP Server
Searches the Directory of Open Access Journals (doaj.org).
Covers peer-reviewed OA journals worldwide, filterable by country.
Particularly useful for finding Italian OA journals and verifying
journal quality during PRISMA eligibility assessment.
API docs: https://doaj.org/api/docs
No API key required.
"""

import json
from typing import Literal
import urllib.request
import urllib.parse
import urllib.error
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("doaj")

BASE_URL = "https://doaj.org/api/v3"
DEFAULT_TIMEOUT = 30


def _get(endpoint: str, params: dict) -> dict:
    url = f"{BASE_URL}/{endpoint}?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=DEFAULT_TIMEOUT) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"DOAJ API error: HTTP {e.code} ({e.reason})") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"DOAJ API unreachable: {e.reason}") from e
    except TimeoutError:
        raise RuntimeError(f"DOAJ API timeout after {DEFAULT_TIMEOUT}s") from None


def _parse_article(hit: dict) -> dict:
    src = hit.get("bibjson", {})
    title = src.get("title", "")
    abstract = src.get("abstract", "")
    year = src.get("year", "")
    # FIX: handle journal as list or dict
    journal_obj = src.get("journal", {})
    if isinstance(journal_obj, dict):
        journal = journal_obj.get("title", "")
    elif isinstance(journal_obj, list):
        journal = journal_obj[0].get("title", "") if journal_obj else ""
    else:
        journal = ""
    authors = [a.get("name", "") for a in src.get("author", []) if isinstance(a, dict)]
    identifiers = src.get("identifier", [])
    doi = next((i.get("id", "") for i in identifiers if isinstance(i, dict) and i.get("type") == "doi"), "")
    doaj_id = hit.get("id", "")
    return {"title": title, "abstract": abstract, "year": year, "journal": journal,
            "authors": authors, "doi": doi, "doaj_id": doaj_id}


def _format_articles(results: list, label: str, total: int) -> str:
    if not results:
        return f"DOAJ — no results for: {label}"
    lines = [f"DOAJ — {total} results for '{label}' (showing {len(results)}):\n"]
    for i, hit in enumerate(results, 1):
        rec = _parse_article(hit)
        auth = ", ".join(rec["authors"][:3]) + (" et al." if len(rec["authors"]) > 3 else "")
        line = f"{i}. **{rec['title'] or '(no title)'}**\n"
        line += f"   {auth or 'N/A'} ({rec['year'] or 'n.d.'})\n"
        if rec["journal"]:
            line += f"   Journal: {rec['journal']}\n"
        if rec["doi"]:
            line += f"   DOI: {rec['doi']}\n"
        if rec["doaj_id"]:
            line += f"   DOAJ: https://doaj.org/article/{rec['doaj_id']}\n"
        if rec["abstract"]:
            line += f"   Abstract: {rec['abstract'][:300]}{'...' if len(rec['abstract']) > 300 else ''}\n"
        lines.append(line)
    return "\n".join(lines)


@mcp.tool()
def doaj_search_articles(
    query: str,
    year_from: int = None,
    year_to: int = None,
    country_publisher: str = None,
    rows: int = 10,
    page: int = 1,
    output_format: Literal["text", "json"] = "text",
) -> str:
    """
    Search DOAJ for peer-reviewed open access journal articles.
    Use for PRISMA database search, especially for OA journals.
    Filterable by publisher country to find Italian OA publications.

    Args:
        query: Search terms (e.g. "adaptive learning artificial intelligence")
        year_from: Start year (e.g. 2015)
        year_to: End year (e.g. 2025)
        country_publisher: ISO country code for journal publisher (e.g. "IT" for Italy)
        rows: Results per page (default 10, max 100)
        page: Page number (default 1)
        output_format: text preview or json envelope with complete records and total.
    """
    if output_format not in ("text", "json"):
        raise ValueError("output_format must be 'text' or 'json'")
    try:
        q_parts = [query]
        if year_from and year_to:
            q_parts.append(f"year:[{year_from} TO {year_to}]")
        elif year_from:
            q_parts.append(f"year:[{year_from} TO *]")
        elif year_to:
            q_parts.append(f"year:[* TO {year_to}]")
        if country_publisher:
            # FIX: quote country value in Lucene query
            q_parts.append(f'index.country_code:"{country_publisher}"')

        params = {"q": " AND ".join(q_parts), "pageSize": rows, "page": page, "sort": "score"}
        data = _get("search/articles", params)
        results = data.get("results", [])
        total = data.get("total", 0)
        if output_format == "json":
            return json.dumps({"records": results, "total": total, "page": data.get("page", page), "pageSize": data.get("pageSize", rows)}, ensure_ascii=False)
        return _format_articles(results, query, total)
    except RuntimeError as e:
        return f"Error: {e}"
    except Exception as e:
        return f"Unexpected error: {e}"


@mcp.tool()
def doaj_count(
    query: str,
    year_from: int = None,
    year_to: int = None,
    country_publisher: str = None,
) -> str:
    """
    Return total article count from DOAJ without downloading records.
    Use at PRISMA Phase 1 to estimate volume.

    Args:
        query: Search terms
        year_from: Start year
        year_to: End year
        country_publisher: ISO country code for journal publisher (e.g. "IT")
    """
    try:
        q_parts = [query]
        if year_from and year_to:
            q_parts.append(f"year:[{year_from} TO {year_to}]")
        elif year_from:
            q_parts.append(f"year:[{year_from} TO *]")
        elif year_to:
            q_parts.append(f"year:[* TO {year_to}]")
        if country_publisher:
            q_parts.append(f'index.country_code:"{country_publisher}"')

        params = {"q": " AND ".join(q_parts), "pageSize": 1, "page": 1}
        data = _get("search/articles", params)
        total = data.get("total", 0)
        parts = [f"DOAJ — results for '{query}'"]
        if country_publisher:
            parts.append(f"[publisher country: {country_publisher}]")
        if year_from or year_to:
            parts.append(f"[{year_from or ''}-{year_to or ''}]")
        return " ".join(parts) + f": **{total}**"
    except RuntimeError as e:
        return f"Error: {e}"
    except Exception as e:
        return f"Unexpected error: {e}"


@mcp.tool()
def doaj_search_journals(
    query: str,
    country: str = None,
    rows: int = 10,
    page: int = 1,
) -> str:
    """
    Search DOAJ for open access journals (not articles).
    Use during PRISMA eligibility to verify if a journal is truly OA
    and peer-reviewed, or to find Italian OA journals in a specific field.

    Args:
        query: Journal name or subject (e.g. "educational technology")
        country: ISO country code for journal country (e.g. "IT")
        rows: Results (default 10)
        page: Page (default 1)
    """
    try:
        q_parts = [query]
        if country:
            q_parts.append(f'bibjson.publisher.country:"{country}"')

        params = {"q": " AND ".join(q_parts), "pageSize": rows, "page": page}
        data = _get("search/journals", params)
        results = data.get("results", [])
        total = data.get("total", 0)

        if not results:
            return f"DOAJ Journals — no results for: {query}"
        lines = [f"DOAJ Journals — {total} results for '{query}' (showing {len(results)}):\n"]
        for i, hit in enumerate(results, 1):
            bib = hit.get("bibjson", {})
            title = bib.get("title", "N/A")
            publisher = bib.get("publisher", {}).get("name", "") if isinstance(bib.get("publisher"), dict) else ""
            country_val = bib.get("publisher", {}).get("country", "") if isinstance(bib.get("publisher"), dict) else ""
            apc = "Yes" if bib.get("apc", {}).get("has_apc") else "No"
            subjects = [s.get("term", "") for s in bib.get("subject", []) if isinstance(s, dict)]
            doaj_id = hit.get("id", "")
            line = f"{i}. **{title}**\n"
            if publisher:
                line += f"   Publisher: {publisher} ({country_val})\n"
            line += f"   APC: {apc}\n"
            if subjects:
                line += f"   Subjects: {', '.join(subjects[:5])}\n"
            if doaj_id:
                line += f"   DOAJ: https://doaj.org/toc/{doaj_id}\n"
            lines.append(line)
        return "\n".join(lines)
    except RuntimeError as e:
        return f"Error: {e}"
    except Exception as e:
        return f"Unexpected error: {e}"


if __name__ == "__main__":
    mcp.run(transport="stdio")
