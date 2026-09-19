"""Best-effort automatic full-text acquisition for Stream 1 search records.

See docs/superpowers/specs/2026-09-17-isolated-study-workspace-design.md
("Automatic Full-Text Acquisition"). A failed/rejected download is not an
error: callers keep working from the abstract, exactly as before this file
existed.
"""
import ipaddress
import re
import socket
from pathlib import Path
from urllib.parse import urlparse

import requests

_MAX_BYTES_DEFAULT = 50_000_000
_TIMEOUT_S = 15


def is_safe_url(url: str) -> bool:
    parsed = urlparse(url)
    if parsed.scheme != "https":
        return False
    try:
        infos = socket.getaddrinfo(parsed.hostname, None)
    except socket.gaierror:
        return False
    for info in infos:
        addr = info[4][0]
        ip = ipaddress.ip_address(addr)
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
            return False
    return True


def _slugify_record_id(record_id: str) -> str:
    return re.sub(r"[^a-zA-Z0-9._-]+", "-", record_id).strip("-") or "paper"


def download_fulltext(url: str, dest_dir: Path, record_id: str,
                       max_bytes: int = _MAX_BYTES_DEFAULT) -> Path | None:
    if not is_safe_url(url):
        return None
    dest_dir = Path(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_path = dest_dir / f"{_slugify_record_id(record_id)}.pdf"
    try:
        with requests.get(url, stream=True, timeout=_TIMEOUT_S,
                           allow_redirects=False) as resp:
            resp.raise_for_status()
            if 300 <= resp.status_code < 400:
                return None
            content_type = resp.headers.get("Content-Type", "")
            if "pdf" not in content_type.lower():
                return None
            written = 0
            with open(dest_path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    written += len(chunk)
                    if written > max_bytes:
                        f.close()
                        dest_path.unlink(missing_ok=True)
                        return None
                    f.write(chunk)
    except (requests.RequestException, OSError):
        dest_path.unlink(missing_ok=True)
        return None
    return dest_path


def enrich_records_with_fulltext(records: list, dest_dir) -> list:
    for record in records:
        url = record.get("fulltext_url")
        record_id = str(record.get("id") or record.get("doi") or record.get("title", "paper"))
        path = download_fulltext(url, dest_dir, record_id) if url else None
        record["local_pdf_path"] = str(path) if path else None
    return records
