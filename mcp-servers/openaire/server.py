"""
OpenAIRE MCP Server
Searches the OpenAIRE Graph for publications from European and Italian
institutional repositories, aggregated and deduplicated by OpenAIRE.
API docs: https://graph.openaire.eu/docs/apis/graph-api/
(The legacy Search API at /search/publications was retired on 2026-05-31.)
No API key required.
"""

import json
import re
from typing import Literal
import urllib.request
import urllib.parse
import urllib.error
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("openaire")

SEARCH_API = "https://api.openaire.eu/graph/v2/researchProducts"
DEFAULT_TIMEOUT = 30
_NOT_OPEN = ["EMBARGO", "CLOSED", "RESTRICTED", "UNKNOWN"]


def _request(params: dict) -> dict:
    url = SEARCH_API + "?" + urllib.parse.urlencode(params, doseq=True)
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=DEFAULT_TIMEOUT) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        detail = ""
        try:
            detail = json.loads(e.read().decode()).get("message", "")
        except Exception:
            pass
        raise RuntimeError(f"OpenAIRE API error: HTTP {e.code} ({detail or e.reason})") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"OpenAIRE API unreachable: {e.reason}") from e
    except TimeoutError:
        raise RuntimeError(f"OpenAIRE API timeout after {DEFAULT_TIMEOUT}s") from None


def _params(query: str, year_from=None, year_to=None, country=None, open_access=None) -> dict:
    params = {"search": query, "type": "publication"}
    if year_from:
        params["fromPublicationDate"] = str(year_from)
    if year_to:
        params["toPublicationDate"] = str(year_to)
    if country:
        params["countryCode"] = country
    if open_access is True:
        params["bestOpenAccessRightLabel"] = "OPEN"
    elif open_access is False:
        params["bestOpenAccessRightLabel"] = _NOT_OPEN
    return params


def _clean(text: str) -> str:
    # Abstracts often carry JATS/HTML markup ("<jats:p>...").
    return " ".join(re.sub(r"<[^>]+>", " ", text or "").split())


def _parse(result: dict) -> dict:
    """Normalized record from a Graph API research product."""
    pids = result.get("pids") or []
    doi = next((p.get("value", "") for p in pids
                if isinstance(p, dict) and (p.get("scheme") or "").lower() == "doi"), "")
    descriptions = result.get("descriptions") or []
    best = result.get("bestAccessRight") or {}
    container = result.get("container") or {}
    language = result.get("language") or {}
    return {
        "title": result.get("mainTitle") or "",
        "authors": [a.get("fullName", "") for a in (result.get("authors") or []) if isinstance(a, dict)],
        "year": (result.get("publicationDate") or "")[:4],
        "abstract": _clean(descriptions[0]) if descriptions else "",
        "doi": doi,
        "journal": container.get("name", "") if isinstance(container, dict) else "",
        "publisher": result.get("publisher") or "",
        "language": language.get("label", "") if isinstance(language, dict) else "",
        "open_access": best.get("label") == "OPEN" if isinstance(best, dict) else False,
        "openaire_id": result.get("id") or "",
    }


def _format(records: list, label: str, total: int) -> str:
    if not records:
        return f"OpenAIRE — no results for: {label}"
    lines = [f"OpenAIRE — {total} results for '{label}' (showing {len(records)}):\n"]
    for i, rec in enumerate(records, 1):
        auth = ", ".join(rec["authors"][:3]) + (" et al." if len(rec["authors"]) > 3 else "")
        line = f"{i}. **{rec['title'] or '(no title)'}**\n"
        line += f"   {auth or 'N/A'} ({rec['year'] or 'n.d.'})\n"
        if rec["journal"]:
            line += f"   Journal: {rec['journal']}\n"
        if rec["doi"]:
            line += f"   DOI: {rec['doi']}\n"
        if rec["openaire_id"]:
            line += f"   OpenAIRE: https://explore.openaire.eu/search/result?id={rec['openaire_id']}\n"
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
    Search OpenAIRE for publications (European + Italian repositories).
    Use for PRISMA database search step. Plain terms are combined with AND;
    "exact phrase", OR, NOT and parentheses are supported.

    Args:
        query: Search terms (e.g. "chatbot education metacognition")
        year_from: Start publication year (e.g. 2015)
        year_to: End publication year (e.g. 2025)
        country: ISO country code to filter (e.g. "IT", "FR")
        open_access: True = OA only, False = non-OA only, None = all
        rows: Results per page (default 10, max 100)
        page: Page number (default 1)
        output_format: text preview or json envelope with complete normalized records and total.
    """
    if output_format not in ("text", "json"):
        raise ValueError("output_format must be 'text' or 'json'")
    try:
        rows = max(1, min(rows, 100))
        params = {**_params(query, year_from, year_to, country, open_access), "page": page, "pageSize": rows}
        data = _request(params)
        records = [_parse(r) for r in (data.get("results") or [])]
        total = int((data.get("header") or {}).get("numFound") or 0)
        if output_format == "json":
            return json.dumps({"records": records, "total": total, "page": page, "size": rows}, ensure_ascii=False)
        return _format(records, query, total)
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
        data = _request({**_params(query, year_from, year_to, country), "page": 1, "pageSize": 1})
        total = int((data.get("header") or {}).get("numFound") or 0)
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
