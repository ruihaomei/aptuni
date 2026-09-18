#!/usr/bin/env python3
"""Run S03 in two stages so holdout is never used for variant selection."""

from __future__ import annotations

import argparse
import json
import platform
import sqlite3
import sys
from pathlib import Path
from typing import Any

from s03.evaluate import as_documents, evaluate_variant, load_jsonl, measure_scaled, select_variant
from s03.freeze import verify_freeze
from s03.metrics import check_thresholds
from s03.retrieval import VARIANTS


ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / "results"


def _write(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8")


def run_dev() -> int:
    if (RESULTS / "holdout.json").exists():
        raise RuntimeError("holdout is already open; delete no evidence and do not rerun selection")
    verify_freeze(ROOT)
    corpus = load_jsonl(ROOT / "frozen/corpus.jsonl")
    queries = load_jsonl(ROOT / "frozen/queries.jsonl")
    thresholds = json.loads((ROOT / "frozen/thresholds.json").read_text(encoding="utf-8"))
    documents = as_documents(corpus)
    dev_queries = [query for query in queries if query["split"] == "dev"]
    summaries: dict[str, dict[str, float]] = {}
    ranked: dict[str, dict[str, list[str]]] = {}
    scaled: dict[str, dict[str, float]] = {}
    for variant in VARIANTS:
        summaries[variant], ranked[variant] = evaluate_variant(variant, documents, dev_queries)
        scaled[variant] = measure_scaled(
            variant, documents, dev_queries, int(thresholds["scaled_corpus_copies"])
        )
    chosen, misses = select_variant(
        summaries, scaled, thresholds["per_split"], thresholds["scaled"]
    )
    result = {
        "stage": "dev",
        "runtime": {"python": platform.python_version(), "sqlite": sqlite3.sqlite_version},
        "summaries": summaries,
        "scaled": scaled,
        "threshold_misses": misses,
        "chosen": chosen,
        "ranked_results": ranked,
    }
    _write(RESULTS / "dev.json", result)
    _write(RESULTS / "SELECTION.json", {"chosen": chosen, "basis": "results/dev.json"})
    print(json.dumps({"chosen": chosen, "summaries": summaries, "scaled": scaled}, indent=2))
    return 0


def run_holdout() -> int:
    verify_freeze(ROOT)
    selection_path = RESULTS / "SELECTION.json"
    if not selection_path.is_file():
        raise RuntimeError("run the dev stage before opening holdout")
    chosen = str(json.loads(selection_path.read_text(encoding="utf-8"))["chosen"])
    if chosen not in VARIANTS:
        raise RuntimeError("selection names an unknown variant")
    corpus = load_jsonl(ROOT / "frozen/corpus.jsonl")
    queries = load_jsonl(ROOT / "frozen/queries.jsonl")
    thresholds = json.loads((ROOT / "frozen/thresholds.json").read_text(encoding="utf-8"))
    holdout = [query for query in queries if query["split"] == "holdout"]
    summary, ranked = evaluate_variant(chosen, as_documents(corpus), holdout)
    misses = check_thresholds(summary, thresholds["per_split"])
    result = {"stage": "holdout", "chosen": chosen, "summary": summary,
              "threshold_misses": misses, "ranked_results": ranked}
    _write(RESULTS / "holdout.json", result)
    print(json.dumps(result, indent=2))
    return 1 if misses else 0


def verify_recorded() -> int:
    """Recompute deterministic relevance evidence without changing the recorded selection."""
    verify_freeze(ROOT)
    dev = json.loads((RESULTS / "dev.json").read_text(encoding="utf-8"))
    holdout = json.loads((RESULTS / "holdout.json").read_text(encoding="utf-8"))
    selection = json.loads((RESULTS / "SELECTION.json").read_text(encoding="utf-8"))
    chosen = str(selection["chosen"])
    if chosen != dev["chosen"] or chosen != holdout["chosen"]:
        raise RuntimeError("recorded selection disagrees across S03 result files")
    if dev["runtime"] != {"python": platform.python_version(), "sqlite": sqlite3.sqlite_version}:
        raise RuntimeError("current runtime differs from the recorded S03 baseline")
    thresholds = json.loads((ROOT / "frozen/thresholds.json").read_text(encoding="utf-8"))
    if check_thresholds(dev["summaries"][chosen], thresholds["per_split"]):
        raise RuntimeError("recorded chosen dev summary misses current frozen thresholds")
    if check_thresholds(dev["scaled"][chosen], thresholds["scaled"]):
        raise RuntimeError("recorded chosen scale summary misses current frozen thresholds")
    if check_thresholds(holdout["summary"], thresholds["per_split"]):
        raise RuntimeError("recorded holdout summary misses current frozen thresholds")

    corpus = load_jsonl(ROOT / "frozen/corpus.jsonl")
    queries = load_jsonl(ROOT / "frozen/queries.jsonl")
    documents = as_documents(corpus)
    for split, recorded_summary, recorded_ranked in (
        ("dev", dev["summaries"][chosen], dev["ranked_results"][chosen]),
        ("holdout", holdout["summary"], holdout["ranked_results"]),
    ):
        subset = [query for query in queries if query["split"] == split]
        summary, ranked = evaluate_variant(chosen, documents, subset)
        if summary != recorded_summary or ranked != recorded_ranked:
            raise RuntimeError(f"recorded {split} relevance evidence is not reproducible")
    print("S03 recorded evidence verified")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("stage", choices=("dev", "holdout", "verify"))
    args = parser.parse_args()
    if args.stage == "dev":
        return run_dev()
    if args.stage == "holdout":
        return run_holdout()
    return verify_recorded()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RuntimeError, ValueError) as error:
        print(f"S03 blocked: {error}", file=sys.stderr)
        raise SystemExit(2) from error
