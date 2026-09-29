"""
CORE MCP Server
Searches CORE (core.ac.uk) — the world's largest aggregator of open access
research. Provides direct access to full-text papers from Italian and
international institutional repositories.
API docs: https://api.core.ac.uk/docs/v3
Requires a free API key: https://core.ac.uk/services/api
"""

import json
import re
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

mcp = FastMCP("core")


def _env_key(*names: str) -> str:
    """First non-empty value: the plugin dialog (/plugin configure) wins over shell env vars."""
    for name in names:
        value = os.environ.get(name, "").strip()
        if value and not value.startswith("${"):  # unsubstituted manifest placeholder
            return value
    return ""

BASE_URL = "https://api.core.ac.uk/v3"
DEFAULT_TIMEOUT = 30
RETRIES = 3
PAGE_SIZE = 100
HEAVY_FIELDS = ("fullText", "references")
API_KEY = _env_key("CORE_API_KEY_PLUGIN", "CORE_API_KEY")
CONFIGURE_HINT = (
    "set the key with `/plugin configure academic-research-prisma-wiki-rag` "
    "(or export CORE_API_KEY) and restart Claude Code"
)

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
        for attempt in range(RETRIES + 1):
            try:
                with urllib.request.urlopen(req, timeout=DEFAULT_TIMEOUT) as resp:
                    return json.loads(resp.read().decode())
            except urllib.error.HTTPError as e:
                if e.code != 429 or attempt == RETRIES:
                    raise
                time.sleep(_retry_after(e, attempt))
    except urllib.error.HTTPError as e:
        msg = f"CORE API error: HTTP {e.code} ({e.reason})"
        if e.code == 429 and not API_KEY:
            msg += f" — no API key configured: {CONFIGURE_HINT}"
        raise RuntimeError(msg) from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"CORE API unreachable: {e.reason}") from e
    except TimeoutError:
        raise RuntimeError(f"CORE API timeout after {DEFAULT_TIMEOUT}s") from None


def _retry_after(e: urllib.error.HTTPError, attempt: int) -> float:
    try:
        return min(float(e.headers.get("Retry-After", "")), 60.0)
    except (TypeError, ValueError, AttributeError):
        return 5.0 * (attempt + 1)


def _slim(record: dict) -> dict:
    """Drop fields that are huge and unused for screening (~3-4k tokens per record)."""
    return {k: v for k, v in record.items() if k not in HEAVY_FIELDS}


# CORE v3 ignores the "filters" body field (same count with or without it) and ORs
# bare terms ("learning analytics" -> 6.3M hits). Filters go into q; plain queries are ANDed.
_SYNTAX = re.compile(r'[:"()*<>=]|\b(AND|OR|NOT)\b|(^|\s)[-+]\S')


def _build_query(query: str, year_from=None, year_to=None, language=None) -> str:
    q = (query or "").strip()
    if not _SYNTAX.search(q):
        q = " AND ".join(q.split())
    parts = [f"({q})"] if q else []
    if year_from:
        parts.append(f"yearPublished>={int(year_from)}")
    if year_to:
        parts.append(f"yearPublished<={int(year_to)}")
    if language:
        parts.append(f"language.code:{re.sub(r'[^A-Za-z-]', '', language)}")
    return " AND ".join(parts)


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
    Needs a free CORE API key (core.ac.uk/services/api): `/plugin configure` or CORE_API_KEY.

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
        payload = {"q": _build_query(query, year_from, year_to, language), "limit": rows, "offset": offset}
        data = _post("search/works", payload)
        results = [_slim(r) for r in data.get("results", [])]
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
        payload = {"q": _build_query(query, year_from, year_to), "limit": 1, "offset": 0}
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
def core_export(
    query: str,
    output_path: str,
    year_from: int = None,
    year_to: int = None,
    language: str = None,
    max_records: int = 5000,
) -> str:
    """
    Download ALL matching CORE records to a JSON file and return only the counts.
    Use this for the PRISMA Phase 1 bulk download instead of paging core_search
    or calling the CORE API from scripts: the configured API key reaches only
    this server, and records never pass through the conversation.
    The file holds the list of records (same contract as raw_*.json);
    fullText and references are dropped from each record. Log the returned
    total/downloaded/query/retrieved_at in prisma_log.md.

    Args:
        query: Search terms, same syntax as core_search
        output_path: JSON file to write (e.g. raw_core.json in the review folder)
        year_from: Start year
        year_to: End year
        language: Language code (e.g. "it")
        max_records: Safety cap on downloaded records (default 5000)
    """
    try:
        q = _build_query(query, year_from, year_to, language)
        records, total, offset, error = [], None, 0, None
        while total is None or (offset < total and len(records) < max_records):
            limit = min(PAGE_SIZE, max_records - len(records))
            try:
                data = _post("search/works", {"q": q, "limit": limit, "offset": offset})
            except RuntimeError as e:
                if total is None:
                    raise
                error = str(e)  # keep the pages already downloaded
                break
            page = data.get("results", [])
            total = data.get("totalHits", 0)
            records.extend(_slim(r) for r in page)
            if not page:
                break
            offset += len(page)
        path = Path(output_path).expanduser()
        path.parent.mkdir(parents=True, exist_ok=True)
        summary = {"total": total, "downloaded": len(records), "query": query,
                    "core_query": q, "retrieved_at": datetime.now(timezone.utc).isoformat(), "error": error}
        path.write_text(json.dumps(records, ensure_ascii=False, indent=1), encoding="utf-8")
        summary.update(path=str(path.resolve()), complete=len(records) >= total)
        return json.dumps(summary, ensure_ascii=False)
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
            msg = f"CORE API error: HTTP {e.code} ({e.reason})"
            if e.code == 429 and not API_KEY:
                msg += f" — no API key configured: {CONFIGURE_HINT}"
            raise RuntimeError(msg) from e
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
