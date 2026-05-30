"""Tests for wiki_selfreflect.py"""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))


def test_log_behavior_creates_file(tmp_path):
    from wiki_selfreflect import log_behavior
    log_behavior(str(tmp_path), "rispondo sempre in modo troppo verbose")
    log_path = tmp_path / ".wiki-behavior-log.jsonl"
    assert log_path.exists()
    entry = json.loads(log_path.read_text().strip())
    assert entry["event"] == "rispondo sempre in modo troppo verbose"
    assert "ts" in entry


def test_log_behavior_appends(tmp_path):
    from wiki_selfreflect import log_behavior
    log_behavior(str(tmp_path), "evento uno")
    log_behavior(str(tmp_path), "evento due")
    log_path = tmp_path / ".wiki-behavior-log.jsonl"
    lines = [l for l in log_path.read_text().splitlines() if l.strip()]
    assert len(lines) == 2


def test_self_reflect_no_patterns_below_threshold(tmp_path):
    from wiki_selfreflect import log_behavior, run_self_reflect
    cfg = {"self_reflection": {"enabled": True, "correction_threshold": 3}}
    log_behavior(str(tmp_path), "sono troppo verboso")
    log_behavior(str(tmp_path), "sono troppo verboso")
    result = run_self_reflect(str(tmp_path), cfg)
    assert result["patterns_found"] == 0
    assert result["updates"] == []


def test_self_reflect_creates_identity_page_at_threshold(tmp_path):
    from wiki_selfreflect import log_behavior, run_self_reflect
    cfg = {"self_reflection": {"enabled": True, "correction_threshold": 3}}
    for _ in range(3):
        log_behavior(str(tmp_path), "sono troppo verboso")
    result = run_self_reflect(str(tmp_path), cfg)
    assert result["patterns_found"] == 1
    assert len(result["updates"]) == 1
    assert result["updates"][0].startswith("wiki/identity/")
    page_path = tmp_path / result["updates"][0]
    assert page_path.exists()
    content = page_path.read_text(encoding="utf-8")
    assert "behavioral-pattern" in content


def test_self_reflect_disabled(tmp_path):
    from wiki_selfreflect import log_behavior, run_self_reflect
    cfg = {"self_reflection": {"enabled": False, "correction_threshold": 3}}
    for _ in range(5):
        log_behavior(str(tmp_path), "evento")
    result = run_self_reflect(str(tmp_path), cfg)
    assert result.get("skipped") is True


def test_self_reflect_logs_to_wiki_log(tmp_path):
    from wiki_selfreflect import log_behavior, run_self_reflect
    cfg = {"self_reflection": {"enabled": True, "correction_threshold": 2}}
    for _ in range(2):
        log_behavior(str(tmp_path), "non cito le fonti")
    run_self_reflect(str(tmp_path), cfg)
    log_path = tmp_path / "wiki" / "log.md"
    assert log_path.exists()
    assert "self-reflect" in log_path.read_text()
