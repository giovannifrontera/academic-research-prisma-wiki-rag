"""Wiki frontend server — FastAPI + WebSocket + file watcher + JWT auth."""

import asyncio
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Set

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse

sys.path.insert(0, str(Path(__file__).parent))
import wiki_graph  # noqa: E402
try:
    import wiki_lancedb as _wiki_lancedb
    from wiki_index import EXCLUDED_NAMES as _EXCLUDED_NAMES
    _LANCEDB_IMPORT_OK = True
except ImportError:
    _LANCEDB_IMPORT_OK = False
    _EXCLUDED_NAMES: set = set()

_workspace: str = ""
_cfg: dict = {}
_no_auth: bool = False
_secret_key: str = ""
_jwt_secret: str = ""  # derived at configure() — kept separate from login password
_session_days: int = 7
_lint_busy: bool = False
_server_start: float = 0.0

_ws_clients: Set[WebSocket] = set()
_embed_model = None  # SentenceTransformer — loaded once on first /api/context call
_embed_model_lock = asyncio.Lock()

app = FastAPI(docs_url=None, redoc_url=None)


def configure(workspace: str, cfg: dict, no_auth: bool) -> None:
    global _workspace, _cfg, _no_auth, _secret_key, _jwt_secret, _session_days
    import hmac
    _workspace = os.path.abspath(workspace)
    _cfg = cfg
    _no_auth = no_auth
    frontend = cfg.get("frontend", {})
    _secret_key = os.environ.get("WIKI_PASSWORD") or frontend.get("password", "changeme")
    # Derive a separate JWT signing secret so it is never the raw login password.
    _jwt_secret = hmac.digest(_secret_key.encode(), b"wiki-jwt-v1", "sha256").hex()
    _session_days = int(frontend.get("session_days", 7))
    global _server_start
    import time
    _server_start = time.time()


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if _no_auth:
            return await call_next(request)
        if request.url.path.startswith("/auth/") or request.url.path == "/api/context":
            return await call_next(request)
        token = request.cookies.get("wiki_session")
        if not token or not _verify_token(token):
            return JSONResponse({"error": "unauthorized"}, status_code=401)
        return await call_next(request)


app.add_middleware(AuthMiddleware)


def _make_token() -> str:
    from jose import jwt
    exp = datetime.now(timezone.utc) + timedelta(days=_session_days)
    return jwt.encode({"exp": exp}, _jwt_secret, algorithm="HS256")


def _verify_token(token: str) -> bool:
    from jose import jwt, JWTError
    try:
        jwt.decode(token, _jwt_secret, algorithms=["HS256"])
        return True
    except JWTError:
        return False


@app.post("/auth/login")
async def login(request: Request):
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "invalid_body"}, status_code=400)
    if body.get("password") != _secret_key:
        return JSONResponse({"error": "unauthorized"}, status_code=401)
    token = _make_token()
    resp = JSONResponse({"status": "ok"})
    resp.set_cookie(
        "wiki_session", token, httponly=True, samesite="lax",
        max_age=_session_days * 86400,
    )
    return resp


@app.post("/auth/logout")
async def logout():
    resp = JSONResponse({"status": "ok"})
    resp.delete_cookie("wiki_session")
    return resp


@app.get("/api/graph")
async def api_graph():
    data = wiki_graph.build_graph(_workspace, _cfg)
    data["agent_name"] = _cfg.get("frontend", {}).get("agent_name", "")
    return JSONResponse(data)


@app.get("/api/page/{path:path}")
async def api_page(path: str):
    detail = wiki_graph.get_page_detail(_workspace, path, _cfg)
    if detail is None:
        return JSONResponse({"error": "not_found"}, status_code=404)
    return JSONResponse(detail)


def _build_stats() -> dict:
    from collections import Counter

    # top_queried: aggregate .wiki-query-log.jsonl
    log_path = Path(_workspace) / ".wiki-query-log.jsonl"
    path_counts: Counter = Counter()
    if log_path.exists():
        try:
            for line in log_path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    for p in entry.get("paths", []):
                        path_counts[p] += 1
                except json.JSONDecodeError:
                    pass
        except OSError:
            pass

    graph_data = wiki_graph.build_graph(_workspace, _cfg)
    node_title: dict = {
        n["path"]: n.get("title", n["path"]) for n in graph_data.get("nodes", [])
    }
    top_queried = [
        {"path": p, "title": node_title.get(p, p), "query_count": c}
        for p, c in path_counts.most_common(10)
    ]

    # stale_pages
    staleness_days = _cfg.get("thresholds", {}).get("staleness_days", 90)
    now_ts = datetime.now(timezone.utc).timestamp()
    stale_pages = []
    for node in graph_data.get("nodes", []):
        lm = node.get("last_modified")
        if lm and (now_ts - lm) > staleness_days * 86400:
            age_days = int((now_ts - lm) / 86400)
            stale_pages.append({
                "path": node["path"],
                "title": node.get("title", node["path"]),
                "age_days": age_days,
            })
    stale_pages.sort(key=lambda x: x["age_days"], reverse=True)

    # unembedded_pages + summary chunk counts
    unembedded_pages: list = []
    total_chunks = 0
    embedding_coverage_pct = 0.0
    if _LANCEDB_IMPORT_OK:
        try:
            lancedb_path = os.path.join(
                _workspace, _cfg.get("lancedb", {}).get("path", "memory/lancedb")
            )
            db = _wiki_lancedb.get_db(lancedb_path)
            table = _wiki_lancedb.ensure_table(db)
            df = table.to_pandas()
            total_chunks = len(df)
            embedded_paths = set(df["path"].unique())
            total_pages = len(graph_data.get("nodes", []))
            if total_pages > 0:
                embedding_coverage_pct = round(len(embedded_paths) / total_pages * 100, 1)
            for root_name in ("wiki", "wiki-works"):
                root = Path(_workspace) / root_name
                if not root.is_dir():
                    continue
                for md_file in root.rglob("*.md"):
                    if md_file.name in _EXCLUDED_NAMES:
                        continue
                    if "raw" in md_file.parts or ".archive" in md_file.parts:
                        continue
                    rel = os.path.relpath(str(md_file), _workspace).replace("\\", "/")
                    if rel not in embedded_paths:
                        unembedded_pages.append({"path": rel, "title": rel})
        except Exception:
            pass

    # lint_status
    lint_status = None
    lint_file = Path(_workspace) / ".wiki-lint-status.json"
    if lint_file.exists():
        try:
            lint_status = json.loads(lint_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            pass

    # auto_lint config
    interval = _cfg.get("frontend", {}).get("lint_interval_hours")
    next_run_iso = None
    if interval and _server_start:
        import time
        next_run_ts = _server_start + float(interval) * 3600
        elapsed = time.time() - _server_start
        periods_elapsed = int(elapsed / (float(interval) * 3600))
        next_run_ts = _server_start + (periods_elapsed + 1) * float(interval) * 3600
        next_run_iso = datetime.fromtimestamp(next_run_ts, tz=timezone.utc).isoformat(timespec="seconds")
    auto_lint: dict = {"enabled": bool(interval), "interval_hours": interval, "next_run_iso": next_run_iso}

    total_pages = len(graph_data.get("nodes", []))
    return {
        "summary": {
            "total_pages": total_pages,
            "total_chunks": total_chunks,
            "embedding_coverage_pct": embedding_coverage_pct,
            "stale_pages_count": len(stale_pages),
        },
        "top_queried": top_queried,
        "stale_pages": stale_pages,
        "unembedded_pages": unembedded_pages[:10],
        "lint_status": lint_status,
        "auto_lint": auto_lint,
    }


@app.get("/api/stats")
async def api_stats():
    return JSONResponse(_build_stats())


async def _get_embed_model():
    """Load SentenceTransformer once, keep it in memory for the server lifetime."""
    global _embed_model
    if _embed_model is not None:
        return _embed_model
    async with _embed_model_lock:
        if _embed_model is None:
            import os as _os
            _os.environ.setdefault("TRANSFORMERS_VERBOSITY", "error")
            _os.environ.setdefault("HF_HUB_VERBOSITY", "error")
            _os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
            import logging as _logging
            for _name in ("sentence_transformers", "transformers", "huggingface_hub"):
                _logging.getLogger(_name).setLevel(_logging.ERROR)
            from sentence_transformers import SentenceTransformer
            model_name = _cfg.get("lancedb", {}).get("embedding_model", "BAAI/bge-m3")
            loop = asyncio.get_event_loop()
            _embed_model = await loop.run_in_executor(
                None, lambda: SentenceTransformer(model_name, device="cpu")
            )
    return _embed_model


_LOCALHOST_ADDRS = {"127.0.0.1", "::1", "::ffff:127.0.0.1"}


@app.get("/api/context")
async def api_context(request: Request, q: str = "", k: int = 3, max_chars: int = 600):
    """Vector search endpoint for the plugin hot path — restricted to loopback callers."""
    from fastapi.responses import PlainTextResponse
    peer = (request.client.host if request.client else None)
    if peer not in _LOCALHOST_ADDRS:
        return PlainTextResponse("", status_code=403)
    if not q.strip() or not _LANCEDB_IMPORT_OK or not _workspace:
        return PlainTextResponse("", status_code=200)

    import fnmatch as _fnmatch
    try:
        model = await _get_embed_model()
        vector = await asyncio.get_event_loop().run_in_executor(
            None, lambda: model.encode(q, normalize_embeddings=True).tolist()
        )
        lancedb_path = os.path.join(_workspace, _cfg.get("lancedb", {}).get("path", "memory/lancedb"))
        db = _wiki_lancedb.get_db(lancedb_path)
        existing_tables = getattr(db.list_tables(), "tables", None) or list(db.list_tables())
        if "wiki_pages" not in existing_tables:
            return PlainTextResponse("", status_code=200)
        table = db.open_table("wiki_pages")
        raw = table.search(vector).limit(k * 4).to_list()

        exclude_patterns = _cfg.get("exclude_from_index", [])
        seen: dict = {}
        for r in raw:
            chunk = r.get("chunk_text") or ""
            if not chunk:
                continue
            path = r["path"]
            if any(_fnmatch.fnmatch(path, p) for p in exclude_patterns):
                continue
            dist = float(r.get("_distance", 1.0))
            if path not in seen or dist < seen[path]["dist"]:
                seen[path] = {"dist": dist, "chunk_text": chunk[:max_chars]}

        top = sorted(seen.items(), key=lambda x: x[1]["dist"])[:k]

        # Stale .tmp check — surfaced regardless of search results
        stale_tmp = []
        for root_name in ("wiki", "wiki-works"):
            root = Path(_workspace) / root_name
            if root.is_dir():
                stale_tmp.extend(
                    os.path.relpath(str(p), _workspace).replace("\\", "/")
                    for p in root.rglob("*.tmp")
                )

        if not top and not stale_tmp:
            return PlainTextResponse("", status_code=200)

        # Log query hits for dashboard WebSocket animation
        if top:
            try:
                log_path = Path(_workspace) / ".wiki-query-log.jsonl"
                entry = {"ts": datetime.now(timezone.utc).isoformat(), "q": q,
                         "paths": [p for p, _ in top]}
                with open(log_path, "a", encoding="utf-8") as f:
                    f.write(json.dumps(entry) + "\n")
            except Exception:
                pass

        lines = ["<wiki-context>"]
        if stale_tmp:
            lines.append(
                f"⚠️ STALE .TMP FILES: {len(stale_tmp)} unprocessed staging file(s) found — "
                f"run `wiki.py ingest` or remove them: {', '.join(stale_tmp[:5])}"
            )
            lines.append("")
        if top:
            lines.append(f"Pre-loaded wiki context (top {len(top)} pages by semantic relevance):\n")
            for path, info in top:
                score = round(1.0 - info["dist"], 3)
                lines.append(f"### {path}  [relevance: {score}]")
                lines.append(info["chunk_text"])
                lines.append("")
        lines.append(
            "</wiki-context>\n"
            "Use the context above to inform your response, detect conflicts during INGEST, "
            "or disambiguate uncertain intents. Do not run wiki.py query if this context is already sufficient."
        )

        return PlainTextResponse("\n".join(lines), status_code=200)

    except Exception:
        return PlainTextResponse("", status_code=200)


@app.post("/api/lint")
async def api_lint():
    global _lint_busy
    if _lint_busy:
        return JSONResponse({"error": "lint already running"}, status_code=409)
    _lint_busy = True
    try:
        import subprocess
        wiki_py = Path(__file__).parent / "wiki.py"
        result = subprocess.run(
            [sys.executable, str(wiki_py), "lint", "--workspace", _workspace, "--full"],
            capture_output=True, text=True, timeout=60,
        )
        output = (result.stdout + result.stderr).strip()
        status = "ok" if result.returncode == 0 else "error"
        return JSONResponse({"status": status, "output": output})
    except subprocess.TimeoutExpired:
        return JSONResponse({"status": "error", "output": "lint timed out"}, status_code=500)
    except Exception as e:
        return JSONResponse({"status": "error", "output": str(e)}, status_code=500)
    finally:
        _lint_busy = False


@app.get("/")
async def index():
    html_path = Path(__file__).parent.parent / "frontend" / "index.html"
    if html_path.exists():
        return FileResponse(str(html_path))
    return HTMLResponse("<h1>Frontend not found</h1>", status_code=404)


@app.websocket("/ws")
async def ws_endpoint(websocket: WebSocket):
    if not _no_auth:
        token = websocket.cookies.get("wiki_session")
        if not token or not _verify_token(token):
            await websocket.close(code=1008)
            return
    await websocket.accept()
    _ws_clients.add(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        _ws_clients.discard(websocket)


async def _broadcast(message: dict) -> None:
    dead: Set[WebSocket] = set()
    payload = json.dumps(message)
    for ws in list(_ws_clients):
        try:
            await ws.send_text(payload)
        except Exception:
            dead.add(ws)
    _ws_clients.difference_update(dead)


@app.on_event("startup")
async def startup():
    asyncio.create_task(_file_watcher())
    asyncio.create_task(_query_log_watcher())
    asyncio.create_task(_auto_lint_task())


async def _file_watcher():
    try:
        from watchfiles import awatch
    except ImportError:
        return
    import wiki_graph
    ws = Path(_workspace)
    watch_dirs = [str(d) for d in (ws / "wiki", ws / "wiki-works") if d.exists()]
    if not watch_dirs:
        return
    async for _changes in awatch(*watch_dirs):
        wiki_graph.mark_dirty()
        await _broadcast({"type": "graph_update"})


async def _query_log_watcher():
    log_path = Path(_workspace) / ".wiki-query-log.jsonl"
    pos = log_path.stat().st_size if log_path.exists() else 0
    while True:
        await asyncio.sleep(0.5)
        if not log_path.exists():
            continue
        size = log_path.stat().st_size
        if size <= pos:
            continue
        with open(log_path, encoding="utf-8") as f:
            f.seek(pos)
            new_content = f.read()
            pos = f.tell()  # use actual read position — avoids skipping bytes if file grew during read
        for line in new_content.splitlines():
            if not line.strip():
                continue
            try:
                entry = json.loads(line)
                paths = entry.get("paths", [])
                if paths:
                    await _broadcast({"type": "query_hit", "paths": paths})
            except json.JSONDecodeError:
                pass


async def _auto_lint_task():
    interval = _cfg.get("frontend", {}).get("lint_interval_hours")
    if not interval:
        return
    while True:
        await asyncio.sleep(float(interval) * 3600)
        import subprocess
        wiki_py = Path(__file__).parent / "wiki.py"
        try:
            subprocess.run(
                [sys.executable, str(wiki_py), "lint", "--workspace", _workspace, "--full"],
                capture_output=True, text=True, timeout=120,
            )
        except Exception:
            pass
