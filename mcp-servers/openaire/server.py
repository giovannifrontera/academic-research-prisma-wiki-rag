"""
OpenAIRE MCP Server
Searches the OpenAIRE Graph API for open access publications from
European and Italian institutional repositories.
API docs: https://graph.openaire.eu/develop/api.html
No API key required.
"""

import json
from typing import Literal
import urllib.request
import urllib.parse
import urllib.error
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("openaire")

SEARCH_API = "https://api.openaire.eu/search/publications"
DEFAULT_TIMEOUT = 30


def _request(params: dict) -> dict:
    url = SEARCH_API + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=DEFAULT_TIMEOUT) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"OpenAIRE API error: HTTP {e.code} ({e.reason})") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"OpenAIRE API unreachable: {e.reason}") from e
    except TimeoutError:
        raise RuntimeError(f"OpenAIRE API timeout after {DEFAULT_TIMEOUT}s") from None


def _get(obj, *keys):
    for k in keys:
        if not isinstance(obj, dict):
            return None
        obj = obj.get(k)
    return obj


def _parse(result: dict) -> dict:
    meta = _get(result, "metadata", "oaf:entity", "oaf:result") or {}

    title_obj = meta.get("title", {})
    if isinstance(title_obj, list):
        title = title_obj[0].get("$", "") if title_obj else ""
    elif isinstance(title_obj, dict):
        title = title_obj.get("$", "")
    else:
        title = str(title_obj) if title_obj else ""

    creators = meta.get("creator", [])
    if isinstance(creators, dict):
        creators = [creators]
    authors = [c.get("$", "") for c in creators if isinstance(c, dict)]

    date = meta.get("dateofacceptance", {})
    year = date.get("$", "")[:4] if isinstance(date, dict) else ""

    desc = meta.get("description", {})
    if isinstance(desc, list):
        abstract = desc[0].get("$", "") if desc else ""
    elif isinstance(desc, dict):
        abstract = desc.get("$", "")
    else:
        # FIX: preserve abstract when API returns a plain string
        abstract = str(desc) if desc else ""

    pid = meta.get("pid", [])
    if isinstance(pid, dict):
        pid = [pid]
    # FIX: case-insensitive classid comparison for DOI
    doi = next(
        (p.get("$", "") for p in (pid or [])
         if isinstance(p, dict) and p.get("@classid", "").lower() == "doi"),
        ""
    )

    source = meta.get("source", {})
    if isinstance(source, list):
        journal = source[0].get("$", "") if source else ""
    elif isinstance(source, dict):
        journal = source.get("$", "")
    else:
        journal = ""

    best = meta.get("bestaccessright", {})
    oa = best.get("@classid", "") == "OPEN" if isinstance(best, dict) else False

    header = result.get("header", {})
    oa_id = _get(header, "dri:objIdentifier", "$") or ""

    return {"title": title, "authors": authors, "year": year, "abstract": abstract,
            "doi": doi, "journal": journal, "open_access": oa, "openaire_id": oa_id}


def _format(data: dict, label: str) -> str:
    response = data.get("response", {})
    total = _get(response, "header", "total", "$") or "0"
    raw = _get(response, "results", "result") or []
    if isinstance(raw, dict):
        raw = [raw]
    if not raw:
        return f"OpenAIRE — no results for: {label}"

    lines = [f"OpenAIRE — {total} results for '{label}' (showing {len(raw)}):\n"]
    for i, r in enumerate(raw, 1):
        rec = _parse(r)
        auth = ", ".join(rec["authors"][:3]) + (" et al." if len(rec["authors"]) > 3 else "")
        line = f"{i}. **{rec['title'] or '(no title)'}**\n"
        line += f"   {auth or 'N/A'} ({rec['year'] or 'n.d.'})\n"
        if rec["journal"]:
            line += f"   Journal: {rec['journal']}\n"
        if rec["doi"]:
            line += f"   DOI: {rec['doi']}\n"
        if rec["openaire_id"]:
            line += f"   OpenAIRE: https://explore.openaire.eu/search/publication?articleId={rec['openaire_id']}\n"
        line += f"   Access: {'Open Access' if rec['open_access'] else 'Limited'}\n"
        if rec["abstract"]:
            line += f"   Abstract: {rec['abstract'][:300]}{'...' if len(rec['abstract']) > 300 else ''}\n"
        lines.append(line)
    return "\n".join(lines)


@mcp.tool()
def openaire_search(
    query: str,
    year_from: int = None,
    year_to: int = None,
    country: str = None,
    open_access: bool = None,
    rows: int = 10,
    page: int = 1,
    output_format: Literal["text", "json"] = "text",
) -> str:
    """
    Search OpenAIRE for open access publications (European + Italian repositories).
    Use for PRISMA database search step.

    Args:
        query: Search terms (e.g. "chatbot education metacognition")
        year_from: Start year (e.g. 2015)
        year_to: End year (e.g. 2025)
        country: ISO country code to filter (e.g. "IT", "FR")
        open_access: True = OA only, False = non-OA only, None = all
        rows: Results per page (default 10, max 100)
        page: Page number (default 1)
        output_format: text preview or json envelope with complete normalized records and total.
    """
    if output_format not in ("text", "json"):
        raise ValueError("output_format must be 'text' or 'json'")
    try:
        params = {"keywords": query, "format": "json", "page": page, "size": rows}
        if country:
            params["country"] = country
        if year_from:
            params["fromDateAccepted"] = f"{year_from}-01-01"
        if year_to:
            params["toDateAccepted"] = f"{year_to}-12-31"
        if open_access is True:
            params["OA"] = "true"
        elif open_access is False:
            params["OA"] = "false"
        data = _request(params)
        if output_format == "json":
            raw = _get(data, "response", "results", "result") or []
            if isinstance(raw, dict):
                raw = [raw]
            return json.dumps({"records": [_parse(r) for r in raw], "total": int(_get(data, "response", "header", "total", "$") or 0), "page": page, "size": rows}, ensure_ascii=False)
        return _format(data, query)
    except RuntimeError as e:
        return f"Error: {e}"
    except Exception as e:
        return f"Unexpected error: {e}"


@mcp.tool()
def openaire_count(
    query: str,
    year_from: int = None,
    year_to: int = None,
    country: str = None,
) -> str:
    """
    Return total result count without downloading records.
    Use at PRISMA Phase 1 to estimate volume before full retrieval.

    Args:
        query: Search terms
        year_from: Start year
        year_to: End year
        country: ISO country code (e.g. "IT")
    """
    try:
        params = {"keywords": query, "format": "json", "page": 1, "size": 1}
        if country:
            params["country"] = country
        if year_from:
            params["fromDateAccepted"] = f"{year_from}-01-01"
        if year_to:
            params["toDateAccepted"] = f"{year_to}-12-31"
        data = _request(params)
        total = _get(data, "response", "header", "total", "$") or "0"
        parts = [f"OpenAIRE — results for '{query}'"]
        if country:
            parts.append(f"[{country}]")
        if year_from or year_to:
            parts.append(f"[{year_from or ''}-{year_to or ''}]")
        return " ".join(parts) + f": **{total}**"
    except RuntimeError as e:
        return f"Error: {e}"
    except Exception as e:
        return f"Unexpected error: {e}"


if __name__ == "__main__":
    mcp.run(transport="stdio")
