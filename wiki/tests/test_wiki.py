import json
import subprocess
import pytest
import sys
import os
from pathlib import Path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

import wiki
from wiki import load_config, ConfigError, acquire_lock, release_lock


@pytest.mark.parametrize(("win_error", "expected"), [(5, True), (87, False), (999, True)])
def test_windows_pid_probe_handles_open_process_errors(monkeypatch, win_error, expected):
    import ctypes

    class WinFunction:
        def __init__(self, result):
            self.result = result

        def __call__(self, *_):
            return self.result

    kernel32 = type("Kernel32", (), {
        "OpenProcess": WinFunction(None),
        "GetExitCodeProcess": WinFunction(False),
        "CloseHandle": WinFunction(True),
    })()
    monkeypatch.setattr(ctypes, "WinDLL", lambda *_args, **_kwargs: kernel32, raising=False)
    monkeypatch.setattr(ctypes, "get_last_error", lambda: win_error, raising=False)
    assert wiki._pid_alive_windows(123) is expected


def test_pid_probe_uses_windows_safe_probe(monkeypatch):
    monkeypatch.setattr(wiki.os, "name", "nt")
    monkeypatch.setattr(wiki, "_pid_alive_windows", lambda pid: pid == 123)
    monkeypatch.setattr(wiki.os, "kill", lambda *_: pytest.fail("os.kill is unsafe on Windows"))
    assert wiki._pid_alive(123)
    assert not wiki._pid_alive(456)


def test_pid_probe_preserves_live_process_and_detects_exit():
    # Isolate the probe: a regression must not terminate pytest itself on Windows.
    script = """
import os
import subprocess
import sys
from wiki import _pid_alive
assert _pid_alive(os.getpid())
child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(30)'])
try:
    assert _pid_alive(child.pid)
    assert child.poll() is None
finally:
    child.terminate()
    child.wait(timeout=10)
assert not _pid_alive(child.pid)
print('PID_PROBE_OK')
"""
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=Path(__file__).parent.parent / "scripts",
        capture_output=True, text=True, timeout=20,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "PID_PROBE_OK"

def test_load_config_ok(tmp_workspace):
    cfg = load_config(str(tmp_workspace / "wiki.config.json"))
    assert cfg["qdrant"]["embedding_model"] == "BAAI/bge-m3"
    assert "thresholds" in cfg

def test_load_config_missing_field(tmp_workspace):
    path = tmp_workspace / "wiki.config.json"
    cfg = json.loads(path.read_text())
    del cfg["thresholds"]["staleness_days"]
    path.write_text(json.dumps(cfg))
    with pytest.raises(ConfigError) as exc:
        load_config(str(path))
    assert "staleness_days" in str(exc.value)

def test_load_config_file_not_found(tmp_workspace):
    with pytest.raises(ConfigError):
        load_config(str(tmp_workspace / "nonexistent.json"))

def test_lock_acquire_and_release(tmp_workspace):
    lock_path = str(tmp_workspace / ".wiki-lock")
    acquire_lock(lock_path)
    assert os.path.exists(lock_path)
    release_lock(lock_path)
    assert not os.path.exists(lock_path)

def test_lock_already_exists(tmp_workspace):
    lock_path = str(tmp_workspace / ".wiki-lock")
    acquire_lock(lock_path)
    with pytest.raises(RuntimeError) as exc:
        acquire_lock(lock_path)
    assert "lock_exists" in str(exc.value)
    release_lock(lock_path)


def run_wiki(tmp_workspace, *args):
    """Helper: chiama wiki.py come subprocess, ritorna dict parsed da JSON stdout."""
    scripts_dir = Path(__file__).parent.parent / "scripts"
    result = subprocess.run(
        [sys.executable, str(scripts_dir / "wiki.py"), *args,
         "--workspace", str(tmp_workspace)],
        capture_output=True, text=True
    )
    try:
        return json.loads(result.stdout)
    except Exception:
        return {"raw_stdout": result.stdout, "raw_stderr": result.stderr}


def test_ingest_workflow_ok(tmp_workspace):
    tmp_page = tmp_workspace / "wiki" / "concepts" / "test-concept.md.tmp"
    tmp_page.write_text("# Test Concept\nContenuto del concetto.", encoding="utf-8")
    result = run_wiki(tmp_workspace, "ingest",
                      "--pages", str(tmp_page),
                      "--log", "ingest | Test Concept")
    assert result["status"] == "ok"
    assert result["pages_written"] == 1
    assert result["mini_lint"] == "ok"
    final = tmp_workspace / "wiki" / "concepts" / "test-concept.md"
    assert final.exists()
    assert not tmp_page.exists()
    assert not (tmp_workspace / ".wiki-lock").exists()


def test_ingest_fails_if_lock_exists(tmp_workspace):
    # Must write the current process's PID — acquire_lock treats non-alive PIDs as stale
    (tmp_workspace / ".wiki-lock").write_text(str(os.getpid()))
    tmp_page = tmp_workspace / "wiki" / "concepts" / "x.md.tmp"
    tmp_page.write_text("# X\n")
    result = run_wiki(tmp_workspace, "ingest",
                      "--pages", str(tmp_page),
                      "--log", "ingest | X")
    assert result["status"] == "error"
    assert result["code"] == "lock_exists"


def test_ingest_rollback_on_missing_tmp(tmp_workspace):
    result = run_wiki(tmp_workspace, "ingest",
                      "--pages", str(tmp_workspace / "wiki" / "concepts" / "nonexistent.md.tmp"),
                      "--log", "ingest | Missing")
    assert result["status"] == "error"
    assert not (tmp_workspace / ".wiki-lock").exists()


def test_query_returns_results(tmp_workspace):
    tmp_page = tmp_workspace / "wiki" / "concepts" / "query-test.md.tmp"
    tmp_page.write_text("# Mean Reversion\nStrategia di trading basata sul ritorno alla media.", encoding="utf-8")
    run_wiki(tmp_workspace, "ingest", "--pages", str(tmp_page), "--log", "ingest | Query Test")
    result = run_wiki(tmp_workspace, "query", "--q", "strategie di trading")
    assert result["status"] == "ok"
    assert isinstance(result["results"], list)
    assert len(result["results"]) >= 1
    assert "path" in result["results"][0]


def test_lint_mini_no_issues(tmp_workspace):
    result = run_wiki(tmp_workspace, "lint")
    assert result["status"] == "ok"
    assert result["issues_count"] == 0


def test_lint_full_detects_orphan(tmp_workspace):
    tmp_page = tmp_workspace / "wiki" / "concepts" / "orphan.md.tmp"
    tmp_page.write_text("# Orphan\nPagina che verrà cancellata.", encoding="utf-8")
    run_wiki(tmp_workspace, "ingest", "--pages", str(tmp_page), "--log", "ingest | Orphan")
    (tmp_workspace / "wiki" / "concepts" / "orphan.md").unlink()
    result = run_wiki(tmp_workspace, "lint", "--full")
    assert result["status"] == "ok"
    orphan_issues = [i for i in result["issues"] if i["type"] == "orphan_entry"]
    assert len(orphan_issues) >= 1


def test_session_update(tmp_workspace):
    result = run_wiki(tmp_workspace, "session-update",
                      "--op", "query", "--status", "ok", "--detail", '{"q":"test"}')
    assert result["status"] == "ok"
    session_file = tmp_workspace / "wiki-session.md"
    assert session_file.exists()
    content = session_file.read_text()
    assert "status: ok" in content
