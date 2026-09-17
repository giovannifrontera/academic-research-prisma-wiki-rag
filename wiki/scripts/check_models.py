"""Verify actual model devices and inference in the active Python environment."""

import argparse
import json
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", help="Optional wiki workspace configuration")
    parser.add_argument("--require-cuda", action="store_true", help="Fail if either model runs on CPU")
    args = parser.parse_args()
    import torch
    from pathlib import Path
    from wiki import load_config
    from wiki_embed import _load_model
    from wiki_rerank import _load_reranker, DEFAULT_MODEL

    cfg = load_config(str(Path(args.workspace) / "wiki.config.json")) if args.workspace else {}
    settings = cfg.get("qdrant", {})
    report = {"python": sys.executable, "torch": torch.__version__,
              "cuda_available": torch.cuda.is_available(), "torch_cuda": torch.version.cuda}
    if args.require_cuda and not report["cuda_available"]:
        report["error"] = "CUDA unavailable in this interpreter; check the driver and PyTorch build"
        print(json.dumps(report, indent=2))
        return 1
    embedder, _ = _load_model(settings.get("embedding_model", "BAAI/bge-m3"))
    vector = embedder.encode("Evidence for learning and memory", normalize_embeddings=True)
    reranker = _load_reranker(settings.get("reranker_model", DEFAULT_MODEL))
    scores = reranker.predict([("learning", "Evidence for learning and memory")])
    report.update(embedding_device=str(embedder.device), reranker_device=str(reranker.model.device),
                  vector_size=len(vector), rerank_score=float(scores[0]))
    print(json.dumps(report, indent=2))
    return int(args.require_cuda and not all(report[key].startswith("cuda")
                                            for key in ("embedding_device", "reranker_device")))


if __name__ == "__main__":
    sys.exit(main())
