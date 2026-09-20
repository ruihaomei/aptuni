#!/usr/bin/env python3
"""Run Aptuni's frozen production retrieval evaluation and emit a reproducible manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aptuni import __version__  # noqa: E402
from aptuni.retrieval.lexical import LEXEME_VERSION  # noqa: E402
from aptuni.retrieval.sqlite import PROJECTION_SCHEMA, ProjectionDocument, SqliteProjection  # noqa: E402

EVALUATOR_VERSION = 1
CORPUS_ROOT = ROOT / "spikes" / "s03_fts"
NOISE_FIXTURE = ROOT / "tests" / "fixtures" / "eval" / "context-noise-example-v1.json"


class EvaluationInputError(RuntimeError):
    """Frozen evaluation input is missing, changed, or malformed."""


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_freeze(root: Path = CORPUS_ROOT) -> dict[str, str]:
    manifest_path = root / "FREEZE.json"
    try:
        value = json.loads(manifest_path.read_text(encoding="utf-8"))
        expected = value["sha256"]
    except (OSError, KeyError, TypeError, json.JSONDecodeError) as error:
        raise EvaluationInputError("retrieval FREEZE.json is missing or invalid") from error
    if not isinstance(expected, dict) or not expected:
        raise EvaluationInputError("retrieval FREEZE.json has no checksums")
    actual: dict[str, str] = {}
    for relative, digest in sorted(expected.items()):
        path = root / relative
        if not path.is_file():
            raise EvaluationInputError(f"frozen retrieval input is missing: {relative}")
        actual[str(relative)] = sha256(path)
        if actual[str(relative)] != digest:
            raise EvaluationInputError(f"frozen retrieval input changed: {relative}")
    return actual


def verify_companion_checksum(path: Path) -> str:
    companion = path.with_suffix(".sha256")
    try:
        fields = companion.read_text(encoding="utf-8").split()
    except OSError as error:
        raise EvaluationInputError(f"checksum companion is missing: {companion.name}") from error
    if len(fields) != 2 or fields[1] != path.name or fields[0] != sha256(path):
        raise EvaluationInputError(f"checksum mismatch: {path.name}")
    return fields[0]


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    try:
        return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
    except (OSError, json.JSONDecodeError) as error:
        raise EvaluationInputError(f"invalid JSONL input: {path.name}") from error


def summarize(queries: list[dict[str, Any]], ranked: dict[str, list[str]]) -> dict[str, float | int]:
    positive = [query for query in queries if query["relevant"]]
    negative = [query for query in queries if not query["relevant"]]
    two_char = [query for query in positive if query["kind"] == "zh_two_char"]

    def recall(query: dict[str, Any]) -> float:
        relevant = set(query["relevant"])
        return len(set(ranked[query["id"]][:5]) & relevant) / min(len(relevant), 5)

    def reciprocal_rank(query: dict[str, Any]) -> float:
        relevant = set(query["relevant"])
        return next((1.0 / rank for rank, item in enumerate(ranked[query["id"]][:10], 1)
                     if item in relevant), 0.0)

    return {
        "queries": len(queries),
        "positive_queries": len(positive),
        "negative_queries": len(negative),
        "recall_at_5": sum(recall(query) for query in positive) / len(positive),
        "mrr": sum(reciprocal_rank(query) for query in positive) / len(positive),
        "two_char_found_rate": (
            sum(bool(set(ranked[query["id"]][:5]) & set(query["relevant"])) for query in two_char)
            / len(two_char)
        ) if two_char else 1.0,
        "false_positive_rate": (
            sum(bool(ranked[query["id"]]) for query in negative) / len(negative)
        ) if negative else 0.0,
    }


def threshold_failures(split: str, summary: dict[str, float | int], thresholds: dict[str, float]) -> list[str]:
    failures: list[str] = []
    for key, bound in sorted(thresholds.items()):
        if key.endswith("_min"):
            metric, passed = key[:-4], float(summary[key[:-4]]) >= bound
        elif key.endswith("_max"):
            metric, passed = key[:-4], float(summary[key[:-4]]) <= bound
        else:
            raise EvaluationInputError(f"threshold has no _min/_max suffix: {key}")
        if not passed:
            failures.append(f"{split}.{metric}={float(summary[metric]):.6f} misses {key}={bound}")
    return failures


def evaluate_context_noise(path: Path = NOISE_FIXTURE) -> dict[str, float | int]:
    verify_companion_checksum(path)
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        overhead = int(value["fixed_overhead_per_unit"])
        units = value["units"]
        expected = value["worked_result"]
        total = sum(int(unit["payload_bytes"]) + overhead for unit in units)
        irrelevant = sum(int(unit["payload_bytes"]) + overhead for unit in units if not unit["relevant"])
        result = {
            "total_units": total,
            "irrelevant_units": irrelevant,
            "noise_ratio": irrelevant / total if total else 0.0,
        }
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
        raise EvaluationInputError("context-noise example is invalid") from error
    if result != expected:
        raise EvaluationInputError("context-noise worked result does not reproduce")
    return result


def git_state(root: Path = ROOT) -> tuple[str | None, bool | None]:
    try:
        commit = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=root, check=True, capture_output=True, text=True,
        ).stdout.strip()
        dirty = bool(subprocess.run(
            ["git", "status", "--porcelain", "--untracked-files=no"],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout)
        return commit, dirty
    except (OSError, subprocess.CalledProcessError):
        return None, None


def evaluate(
    *,
    sbom: Path | None = None,
    corpus_root: Path = CORPUS_ROOT,
    noise_fixture: Path = NOISE_FIXTURE,
) -> dict[str, Any]:
    if sbom is not None and not sbom.is_file():
        raise EvaluationInputError(f"SBOM is missing: {sbom}")
    frozen = verify_freeze(corpus_root)
    corpus = load_jsonl(corpus_root / "frozen" / "corpus.jsonl")
    queries = load_jsonl(corpus_root / "frozen" / "queries.jsonl")
    try:
        thresholds = json.loads((corpus_root / "frozen" / "thresholds.json").read_text(encoding="utf-8"))
        per_split = thresholds["per_split"]
    except (OSError, KeyError, TypeError, json.JSONDecodeError) as error:
        raise EvaluationInputError("retrieval thresholds are invalid") from error

    documents = [
        ProjectionDocument(item["id"], "fact", "knowledge", None, item["text"])
        for item in corpus
    ]
    summaries: dict[str, dict[str, float | int]] = {}
    outputs: dict[str, dict[str, list[str]]] = {}
    failures: list[str] = []
    with tempfile.TemporaryDirectory(prefix="aptuni-eval-") as raw:
        projection = SqliteProjection(Path(raw))
        projection.rebuild(documents, vault_seq=1)
        for split in ("dev", "holdout"):
            split_queries = [query for query in queries if query["split"] == split]
            ranked = {
                query["id"]: [row.record_id for row in projection.search(query["text"], limit=5)]
                for query in split_queries
            }
            summaries[split] = summarize(split_queries, ranked)
            outputs[split] = ranked
            failures.extend(threshold_failures(split, summaries[split], per_split))

    commit, dirty = git_state()
    noise = evaluate_context_noise(noise_fixture)
    return {
        "schema_version": 1,
        "evaluator_version": EVALUATOR_VERSION,
        "passed": not failures,
        "failures": failures,
        "project": {"name": "aptuni", "version": __version__, "commit": commit, "dirty": dirty},
        "runtime": {
            "os": platform.platform(),
            "python": platform.python_version(),
            "sqlite": sqlite3.sqlite_version,
            "host_versions": {},
        },
        "run": {"seed": 0, "locales": ["en", "zh-CN", "mixed"]},
        "contracts": {"projection_schema": PROJECTION_SCHEMA, "lexeme_version": LEXEME_VERSION},
        "inputs": {
            "freeze_sha256": sha256(corpus_root / "FREEZE.json"),
            "frozen_files": frozen,
            "context_noise_sha256": verify_companion_checksum(noise_fixture),
            "evaluator_sha256": sha256(Path(__file__)),
            "uv_lock_sha256": sha256(ROOT / "uv.lock"),
            "sbom_sha256": sha256(sbom) if sbom is not None else None,
        },
        "thresholds": per_split,
        "metrics": {"retrieval": summaries, "context_noise_example": noise},
        "outputs": {"ranked_results": outputs},
    }


def write_manifest(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, raw = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(raw, path)
    finally:
        Path(raw).unlink(missing_ok=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="write the complete JSON run manifest")
    parser.add_argument("--sbom", type=Path, help="include the SHA-256 of this generated SBOM")
    args = parser.parse_args(argv)
    try:
        result = evaluate(sbom=args.sbom)
    except EvaluationInputError as error:
        print(f"evaluation blocked: {error}", file=sys.stderr)
        return 2
    if args.output is not None:
        write_manifest(args.output, result)
    print(json.dumps({
        "passed": result["passed"],
        "failures": result["failures"],
        "metrics": result["metrics"],
        "output": str(args.output) if args.output is not None else None,
    }, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
