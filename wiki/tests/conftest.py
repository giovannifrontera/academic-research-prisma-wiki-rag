import json
import pytest

@pytest.fixture
def tmp_workspace(tmp_path):
    (tmp_path / "wiki" / "entities").mkdir(parents=True)
    (tmp_path / "wiki" / "concepts").mkdir(parents=True)
    (tmp_path / "wiki" / "synthesis").mkdir(parents=True)
    (tmp_path / "wiki-works" / "test").mkdir(parents=True)
    (tmp_path / "wiki-works" / "test" / "raw").mkdir(parents=True)
    (tmp_path / "memory" / "lancedb").mkdir(parents=True)
    (tmp_path / "pdf-inbox").mkdir(parents=True)

    config = {
        "workspace": str(tmp_path),
        "projects": {
            "test": {"path": "wiki-works/test", "keywords": ["test", "prova", "esempio"]}
        },
        "pdf_inbox": {
            "project_default": "test"
        },
        "thresholds": {
            "index_token_budget": 4000,
            "staleness_days": 90,
            "similarity_merge": 0.95,
            "similarity_orphan": 0.50,
            "synthesis_min_tokens": 300,
            "synthesis_min_sources": 2,
            "chunk_size_tokens": 512,
            "chunk_overlap_tokens": 64,
            "page_chunk_threshold_tokens": 1500,
            "quality_filter_min_score": 6,
            "dedup_auto": 0.90,
            "dedup_warn": 0.75,
        },
        "self_reflection": {
            "enabled": True,
            "correction_threshold": 3,
        },
        "lancedb": {
            "path": "memory/lancedb",
            "embedding_model": "BAAI/bge-m3"
        }
    }
    (tmp_path / "wiki.config.json").write_text(json.dumps(config, indent=2))
    return tmp_path
