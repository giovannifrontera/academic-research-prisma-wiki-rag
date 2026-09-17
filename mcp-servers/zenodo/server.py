"""
Zenodo MCP Server
Searches Zenodo (zenodo.org) — CERN's open research repository.
Covers preprints, datasets, software, and publications from
Italian researchers and European projects (Horizon funding).
API docs: https://developers.zenodo.org/
No API key required for public records.
"""

import json
from typing import Literal
import re
import urllib.request
import urllib.parse
import urllib.error
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("zenodo")

BASE_URL = "https://zenodo.org/api"
DEFAULT_TIMEOUT = 30


def _get(params: dict) -> dict:
    url = f"{BASE_URL}/records?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=DEFAULT_TIMEOUT) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"Zenodo API error: HTTP {e.code} ({e.reason})") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"Zenodo API unreachable: {e.reason}") from e
    except TimeoutError:
        raise RuntimeError(f"Zenodo API timeout after {DEFAULT_TIMEOUT}s") from None


def _parse(hit: dict) -> dict:
    meta = hit.get("metadata", {})
    title = meta.get("title", "")
    resource_type = meta.get("resource_type", {}).get("type", "") if isinstance(meta.get("resource_type"), dict) else ""
    pub_date = meta.get("publication_date", "")[:4]
    creators = meta.get("creators", [])
    authors = [c.get("name", "") for c in creators if isinstance(c, dict)]
    description = meta.get("description", "") or ""
    description = re.sub(r"<[^>]+>", "", description)
    doi = meta.get("doi", "") or hit.get("doi", "")
    zenodo_id = hit.get("id", "")
    keywords = meta.get("keywords", []) or []
    journal_info = meta.get("journal", {})
    journal = journal_info.get("title", "") if isinstance(journal_info, dict) else ""
    communities = [c.get("id", "") for c in meta.get("communities", []) if isinstance(c, dict)]
    return {
        "title": title, "resource_type": resource_type, "year": pub_date,
        "authors": authors, "abstract": description, "doi": doi,
        "zenodo_id": zenodo_id, "keywords": keywords, "journal": journal,
        "communities": communities,
    }


def _format(hits: list, label: str, total: int) -> str:
    if not hits:
        return f"Zenodo — no results for: {label}"
    lines = [f"Zenodo — {total} results for '{label}' (showing {len(hits)}):\n"]
    for i, hit in enumerate(hits, 1):
        rec = _parse(hit)
        auth = ", ".join(rec["authors"][:3]) + (" et al." if len(rec["authors"]) > 3 else "")
        rtype = f" [{rec['resource_type']}]" if rec["resource_type"] else ""
        line = f"{i}. **{rec['title'] or '(no title)'}**{rtype}\n"
        line += f"   {auth or 'N/A'} ({rec['year'] or 'n.d.'})\n"
        if rec["journal"]:
            line += f"   Journal: {rec['journal']}\n"
        if rec["doi"]:
            line += f"   DOI: {rec['doi']}\n"
        if rec["zenodo_id"]:
            line += f"   Zenodo: https://zenodo.org/records/{rec['zenodo_id']}\n"
        if rec["keywords"]:
            line += f"   Keywords: {', '.join(rec['keywords'][:6])}\n"
        if rec["abstract"]:
            line += f"   Abstract: {rec['abstract'][:300]}{'...' if len(rec['abstract']) > 300 else ''}\n"
        lines.append(line)
    return "\n".join(lines)


def _parse_total(data: dict) -> int:
    """Handle Zenodo API v1 (int) and v3 (dict with 'value') total format."""
    raw = data.get("hits", {}).get("total", 0)
    if isinstance(raw, dict):
        return raw.get("value", 0)
    return int(raw or 0)


@mcp.tool()
def zenodo_search(
    query: str,
    year_from: int = None,
    year_to: int = None,
    resource_type: str = None,
    community: str = None,
    rows: int = 10,
    page: int = 1,
    output_format: Literal["text", "json"] = "text",
) -> str:
    """
    Search Zenodo for open research outputs (preprints, articles, datasets, software).
    Particularly useful for finding Italian Horizon Europe project outputs
    and preprints before formal journal publication.

    Args:
        query: Search terms (e.g. "machine learning education Italy")
        year_from: Start year (e.g. 2015)
        year_to: End year (e.g. 2025)
        resource_type: Filter by type: "publication", "dataset", "software",
                       "presentation", "poster" (default: all)
        community: Zenodo community ID to search within (e.g. "eu" for EU projects)
        rows: Results per page (default 10, max 100)
        page: Page number (default 1)
        output_format: text preview or json envelope with complete records and total.
    """
    if output_format not in ("text", "json"):
        raise ValueError("output_format must be 'text' or 'json'")
    try:
        q = query
        if year_from and year_to:
            q += f" AND publication_date:[{year_from}-01-01 TO {year_to}-12-31]"
        elif year_from:
            q += f" AND publication_date:[{year_from}-01-01 TO *]"
        elif year_to:
            q += f" AND publication_date:[* TO {year_to}-12-31]"
        if resource_type:
            q += f" AND resource_type.type:{resource_type}"
        if community:
            q += f" AND communities:{community}"

        params = {"q": q, "size": rows, "page": page, "sort": "bestmatch", "access_right": "open"}
        data = _get(params)
        hits = data.get("hits", {}).get("hits", [])
        total = _parse_total(data)
        if output_format == "json":
            raw_total = data.get("hits", {}).get("total", 0)
            return json.dumps({
                "records": hits, "total": total, "page": page, "size": rows,
                "links": data.get("links", {}),
                "total_relation": raw_total.get("relation", "eq") if isinstance(raw_total, dict) else "eq",
            }, ensure_ascii=False)
        return _format(hits, query, total)
    except RuntimeError as e:
        return f"Error: {e}"
    except Exception as e:
        return f"Unexpected error: {e}"


@mcp.tool()
def zenodo_count(
    query: str,
    year_from: int = None,
    year_to: int = None,
    resource_type: str = None,
) -> str:
    """
    Return total result count from Zenodo without downloading records.
    Use at PRISMA Phase 1 to estimate volume.

    Args:
        query: Search terms
        year_from: Start year
        year_to: End year
        resource_type: "publication", "dataset", "software", etc.
    """
    try:
        q = query
        if year_from and year_to:
            q += f" AND publication_date:[{year_from}-01-01 TO {year_to}-12-31]"
        elif year_from:
            q += f" AND publication_date:[{year_from}-01-01 TO *]"
        elif year_to:
            q += f" AND publication_date:[* TO {year_to}-12-31]"
        if resource_type:
            q += f" AND resource_type.type:{resource_type}"

        params = {"q": q, "size": 1, "page": 1, "access_right": "open"}
        data = _get(params)
        total = _parse_total(data)
        parts = [f"Zenodo — results for '{query}'"]
        if resource_type:
            parts.append(f"[{resource_type}]")
        if year_from or year_to:
            parts.append(f"[{year_from or ''}-{year_to or ''}]")
        return " ".join(parts) + f": **{total}**"
    except RuntimeError as e:
        return f"Error: {e}"
    except Exception as e:
        return f"Unexpected error: {e}"


@mcp.tool()
def zenodo_get(record_id: str, output_format: Literal["text", "json"] = "text") -> str:
    """
    Retrieve full metadata for a specific Zenodo record.
    Use to get download links, license, and full author affiliations
    for a paper identified during screening.

    Args:
        record_id: Zenodo record ID (numeric, from zenodo_search results)
        output_format: text details or json envelope with complete records and total.
    """
    if output_format not in ("text", "json"):
        raise ValueError("output_format must be 'text' or 'json'")
    try:
        safe_id = urllib.parse.quote(str(record_id), safe="")
        url = f"{BASE_URL}/records/{safe_id}"
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=DEFAULT_TIMEOUT) as resp:
                r = json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            raise RuntimeError(f"Zenodo API error: HTTP {e.code} ({e.reason})") from e
        except urllib.error.URLError as e:
            raise RuntimeError(f"Zenodo API unreachable: {e.reason}") from e
        except TimeoutError:
            raise RuntimeError(f"Zenodo API timeout after {DEFAULT_TIMEOUT}s") from None

        if output_format == "json":
            return json.dumps({"records": [r], "total": 1}, ensure_ascii=False)
        rec = _parse(r)
        files = r.get("files", []) or []
        file_links = [f.get("links", {}).get("self", "") for f in files if isinstance(f, dict)]
        license_info = r.get("metadata", {}).get("license", {})
        license_id = license_info.get("id", "") if isinstance(license_info, dict) else ""

        lines = [
            f"**{rec['title'] or 'N/A'}**",
            f"Type: {rec['resource_type'] or 'N/A'}",
            f"Authors: {', '.join(rec['authors']) or 'N/A'}",
            f"Year: {rec['year'] or 'n.d.'}",
            f"DOI: {rec['doi'] or 'N/A'}",
            f"License: {license_id or 'N/A'}",
            f"Zenodo: https://zenodo.org/records/{rec['zenodo_id']}",
        ]
        if rec["keywords"]:
            lines.append(f"Keywords: {', '.join(rec['keywords'])}")
        if file_links:
            lines.append(f"File: {file_links[0]}")
        if rec["abstract"]:
            lines.append(f"\nAbstract:\n{rec['abstract']}")
        return "\n".join(lines)
    except RuntimeError as e:
        return f"Error: {e}"
    except Exception as e:
        return f"Unexpected error: {e}"


if __name__ == "__main__":
    mcp.run(transport="stdio")
