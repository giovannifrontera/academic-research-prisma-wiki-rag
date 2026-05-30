"""PDF inbox watcher: estrae testo da PDF e deposita in wiki-works/raw/."""

import hashlib
import json
import os
import re
import tempfile
from datetime import datetime
from pathlib import Path

import pdfplumber

INBOX_DIR = "pdf-inbox"
REGISTRY_FILE = ".registry.json"


def compute_hash(pdf_path: str) -> str:
    """SHA-256 del file PDF."""
    h = hashlib.sha256()
    with open(pdf_path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return f"sha256:{h.hexdigest()}"


def load_registry(workspace: str) -> dict:
    """Legge pdf-inbox/.registry.json. Ritorna {} se non esiste."""
    path = Path(workspace) / INBOX_DIR / REGISTRY_FILE
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save_registry(workspace: str, data: dict) -> None:
    """Scrive .registry.json atomicamente via tempfile + os.replace."""
    inbox_dir = Path(workspace) / INBOX_DIR
    inbox_dir.mkdir(parents=True, exist_ok=True)
    target = inbox_dir / REGISTRY_FILE
    fd, tmp_path = tempfile.mkstemp(dir=str(inbox_dir), prefix=".registry.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, str(target))
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def extract_text(pdf_path: str) -> str:
    """Estrae testo da PDF. Ritorna stringa vuota se nessun testo selezionabile."""
    text_parts = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)
    return "\n\n".join(text_parts)


def deposit_raw(text: str, pdf_name: str, workspace: str, cfg: dict) -> str:
    """Salva testo estratto in wiki-works/<project>/raw/<stem>.md con frontmatter.
    Ritorna il path relativo al workspace (slash forward)."""
    project = cfg.get("pdf_inbox", {}).get("project_default", "")
    if not project:
        projects = cfg.get("projects", {})
        project = next(iter(projects), "default") if projects else "default"

    raw_dir = Path(workspace) / "wiki-works" / project / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    stem = re.sub(r"[^\w\-]", "_", Path(pdf_name).stem)
    out_path = raw_dir / f"{stem}.md"
    if not out_path.resolve().is_relative_to(raw_dir.resolve()):
        raise ValueError(f"Nome PDF non sicuro: {pdf_name}")

    now = datetime.now().isoformat(timespec="seconds")
    content = f"---\nsource: pdf\noriginal: {pdf_name}\nextracted_at: {now}\n---\n\n{text}"
    out_path.write_text(content, encoding="utf-8")

    return os.path.relpath(str(out_path), workspace).replace("\\", "/")


def scan_inbox(workspace: str, cfg: dict) -> dict:
    """Scansiona pdf-inbox/, processa PDF nuovi/modificati. Ritorna report JSON-serializzabile."""
    inbox_dir = Path(workspace) / INBOX_DIR
    inbox_dir.mkdir(parents=True, exist_ok=True)

    registry = load_registry(workspace)
    processed: list[str] = []
    skipped: list[str] = []
    failed: list[dict] = []

    for pdf_file in sorted(inbox_dir.glob("*.pdf")):
        name = pdf_file.name
        current_hash = compute_hash(str(pdf_file))
        entry = registry.get(name, {})

        # Salta se già processato o fallito con lo stesso hash
        if entry.get("hash") == current_hash and entry.get("status") in ("deposited", "failed"):
            skipped.append(name)
            continue

        # Marca pending prima di iniziare (crash recovery: pending → reprocessed al prossimo scan)
        registry[name] = {
            "hash": current_hash,
            "deposited_to": None,
            "processed_at": datetime.now().isoformat(timespec="seconds"),
            "status": "pending",
        }
        save_registry(workspace, registry)

        try:
            text = extract_text(str(pdf_file))
            if not text.strip():
                raise ValueError("no text extractable (scanned PDF)")

            rel_path = deposit_raw(text, name, workspace, cfg)

            registry[name] = {
                "hash": current_hash,
                "deposited_to": rel_path,
                "processed_at": datetime.now().isoformat(timespec="seconds"),
                "status": "deposited",
            }
            processed.append(rel_path)

        except Exception as e:
            registry[name] = {
                "hash": current_hash,
                "deposited_to": None,
                "processed_at": datetime.now().isoformat(timespec="seconds"),
                "status": "failed",
                "error": str(e),
            }
            failed.append({"name": name, "error": str(e)})

        save_registry(workspace, registry)

    return {
        "status": "ok",
        "op": "scan-inbox",
        "processed": len(processed),
        "skipped": len(skipped),
        "failed": len(failed),
        "deposited": processed,
        "failures": failed,
    }
