"""Chunking boundary-aware + embedding bge-m3."""

import hashlib
import re

_model = None
_tokenizer = None


def _load_model(model_name: str = "BAAI/bge-m3"):
    global _model, _tokenizer
    if _model is None:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer(model_name)
        _tokenizer = _model.tokenizer
    return _model, _tokenizer


def count_tokens(text: str, model_name: str = "BAAI/bge-m3") -> int:
    _, tokenizer = _load_model(model_name)
    return len(tokenizer.encode(text, add_special_tokens=False))


def _split_on_headings(text: str) -> list[str]:
    """Splitta il testo sui boundary ## e ### mantenendo il testo prima del primo heading."""
    parts = re.split(r'(?=^#{2,3} )', text, flags=re.MULTILINE)
    return [p for p in parts if p.strip()]


def _tail_text(text: str, n_tokens: int, tokenizer) -> str:
    """Restituisce gli ultimi n_tokens del testo (per implementare l'overlap)."""
    if n_tokens <= 0 or not text.strip():
        return ""
    ids = tokenizer.encode(text, add_special_tokens=False)
    if len(ids) <= n_tokens:
        return text
    return tokenizer.decode(ids[-n_tokens:])


def _emit_chunk(chunks: list, current: str, overlap: int, tokenizer) -> tuple[str, int]:
    """Aggiunge current a chunks e restituisce il prefisso di overlap per il chunk successivo."""
    stripped = current.strip()
    if stripped:
        chunks.append(stripped)
    prefix = _tail_text(stripped, overlap, tokenizer) if overlap > 0 else ""
    prefix_with_sep = prefix + "\n\n" if prefix else ""
    return prefix_with_sep, len(tokenizer.encode(prefix_with_sep, add_special_tokens=False))


def chunk_text(
    text: str,
    chunk_size: int = 512,
    overlap: int = 64,
    threshold: int = 1500,
    model_name: str = "BAAI/bge-m3",
) -> list[str]:
    """Ritorna lista di chunk con overlap reale. Se il testo è sotto soglia, ritorna [text]."""
    _, tokenizer = _load_model(model_name)

    if count_tokens(text, model_name) <= threshold:
        return [text]

    sections = _split_on_headings(text)
    chunks: list[str] = []
    current: str = ""
    current_tokens: int = 0

    for section in sections:
        sec_tokens = count_tokens(section, model_name)

        if current_tokens + sec_tokens <= chunk_size:
            current += section
            current_tokens += sec_tokens
        else:
            current, current_tokens = _emit_chunk(chunks, current, overlap, tokenizer)

            if sec_tokens <= chunk_size:
                current += section
                current_tokens += sec_tokens
            else:
                # Sezione più grande del chunk_size: splitta per paragrafi
                paragraphs = section.split('\n\n')
                para_acc: str = current
                para_tokens: int = current_tokens
                for para in paragraphs:
                    pt = count_tokens(para, model_name)
                    if para_tokens + pt <= chunk_size:
                        para_acc += para + '\n\n'
                        para_tokens += pt
                    else:
                        para_acc, para_tokens = _emit_chunk(chunks, para_acc, overlap, tokenizer)
                        para_acc += para + '\n\n'
                        para_tokens += pt
                current = para_acc
                current_tokens = para_tokens

    _emit_chunk(chunks, current, 0, tokenizer)  # ultimo chunk: no overlap in coda

    return chunks if chunks else [text]


_MAX_CHARS = 30_000


def embed_file(
    path: str,
    chunk_size: int = 512,
    overlap: int = 64,
    threshold: int = 1500,
    model_name: str = "BAAI/bge-m3",
) -> list[dict]:
    """Legge un file .md e ritorna lista di chunk con vettori e hash."""
    with open(path, encoding="utf-8") as f:
        text = f.read()

    page_hash = hashlib.sha256(text.encode()).hexdigest()  # hash del file reale, prima del troncamento

    if len(text) > _MAX_CHARS:
        text = text[:_MAX_CHARS] + "\n\n[... file troncato per limite embedding]"
    chunks = chunk_text(text, chunk_size, overlap, threshold, model_name)
    model, _ = _load_model(model_name)

    result = []
    for i, chunk in enumerate(chunks):
        vector = model.encode(chunk, normalize_embeddings=True).tolist()
        content_hash = hashlib.sha256(chunk.encode()).hexdigest()
        result.append({
            "chunk_id": i,
            "chunk_text": chunk,
            "vector": vector,
            "content_hash": content_hash,
            "page_hash": page_hash,
        })
    return result
