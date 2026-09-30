"""Bulk download of a server's JSON search pages to a raw_*.json file.

Shared by the servers without a native bulk endpoint (ERIC, OpenAIRE, DOAJ,
Zenodo, arXiv): records go straight to disk and only the counts come back,
so a PRISMA harvest never passes thousands of records through the conversation.
"""
import json
import time
from datetime import datetime, timezone
from pathlib import Path


def export_pages(fetch_page, output_path: str, query: str, max_records: int, page_size: int,
                 delay_s: float = 0.0) -> str:
    """fetch_page(page_index, offset, size) returns the search tool's JSON envelope string."""
    records, total, error, index = [], None, None, 0
    while total is None or len(records) < min(total, max_records):
        size = min(page_size, max_records - len(records))
        if index and delay_s:
            time.sleep(delay_s)
        out = fetch_page(index, len(records), size)
        if not out.startswith("{"):  # the tools return "Error: ..." strings
            if total is None:
                return out
            error = out  # keep the pages already downloaded
            break
        data = json.loads(out)
        total = int(data.get("total") or 0)
        page = data.get("records") or []
        records.extend(page)
        if not page:
            break
        index += 1
    records = records[:max_records]
    path = Path(output_path).expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(records, ensure_ascii=False, indent=1), encoding="utf-8")
    return json.dumps({
        "total": total, "downloaded": len(records), "query": query,
        "retrieved_at": datetime.now(timezone.utc).isoformat(), "error": error,
        "path": str(path.resolve()), "complete": len(records) >= total,
    }, ensure_ascii=False)
