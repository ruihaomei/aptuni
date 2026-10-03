#!/usr/bin/env python3
"""Content-free accounting for local, frozen ordinary-prompt Agent experiments.

Raw inputs and traces stay outside Git. This command reports observations, never
grades answer success or substitutes retrieval counts for an independent rubric.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

RETRIEVAL = {"aptuni_search_context", "aptuni_activate_context"}


def _claude_calls(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    calls: dict[str, dict[str, Any]] = {}
    results: dict[str, dict[str, Any]] = {}
    for event in events:
        blocks = event.get("message", {}).get("content", [])
        if not isinstance(blocks, list):
            continue
        for block in blocks:
            if block.get("type") == "tool_use":
                name = block.get("name", "").split("__")[-1]
                if name in RETRIEVAL:
                    calls[block["id"]] = {"name": name, "arguments": block.get("input", {})}
            elif block.get("type") == "tool_result":
                results[block["tool_use_id"]] = block
    for identifier, call in calls.items():
        result = results.get(identifier)
        call["refused"] = bool(result and (
            result.get("is_error") or str(result.get("content", "")).startswith("Error executing tool")
        ))
        call["returned"] = result is not None
    return list(calls.values())


def _codex_calls(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    calls: dict[str, dict[str, Any]] = {}
    for event in events:
        if event.get("method") not in {"item/started", "item/completed"}:
            continue
        item = event["params"]["item"]
        if item.get("type") == "mcpToolCall" and item.get("tool") in RETRIEVAL:
            calls[item["id"]] = {
                "name": item["tool"], "arguments": item.get("arguments", {}),
                "refused": bool(item.get("error") or item.get("status") == "failed"),
                "returned": item.get("result") is not None,
            }
    return list(calls.values())


def _codex_total(turn: dict[str, Any]) -> dict[str, int] | None:
    totals = [event["params"]["tokenUsage"].get("total")
              for event in turn.get("events", [])
              if event.get("method") == "thread/tokenUsage/updated"]
    return totals[-1] if totals else None


def _tokens(record: dict[str, Any], host: str) -> dict[str, int | None] | None:
    task = record.get("task", {})
    if host == "claude":
        usage = task.get("result", {}).get("usage")
        if usage is None:
            return None
        return {
            "input_uncached": usage.get("input_tokens"),
            "cache_creation": usage.get("cache_creation_input_tokens"),
            "input_cached": usage.get("cache_read_input_tokens"),
            "output": usage.get("output_tokens"),
            "reasoning_output": None,
        }
    total = _codex_total(task)
    setup = _codex_total(record.get("setup", {}))
    if total is None or setup is None:
        return None
    fields = {"input_total": "inputTokens", "input_cached": "cachedInputTokens",
              "cache_creation": "cacheWriteInputTokens", "output": "outputTokens",
              "reasoning_output": "reasoningOutputTokens"}
    result = {}
    for label, key in fields.items():
        value = total[key] - setup[key] if key in total and key in setup else None
        if value is not None and value < 0:
            raise ValueError("usage counters reset; cumulative subtraction is invalid")
        result[label] = value
    return result


def summarize_record(record: dict[str, Any], host: str) -> dict[str, Any]:
    """Return counters only: no prompt, answer, query, concept string or source id."""
    if host not in {"claude", "codex"}:
        raise ValueError("unsupported host")
    task = record.get("task", {})
    calls = (_claude_calls if host == "claude" else _codex_calls)(task.get("events", []))
    result = task.get("result", {})
    completed = (bool(result.get("result")) and not result.get("is_error", False)
                 if host == "claude" else result.get("status") == "completed")
    concepts = [call["arguments"].get("concepts", []) or [] for call in calls]
    return {
        "host_completed": completed,
        "retrieval_calls": len(calls),
        "refused_calls": sum(call["refused"] for call in calls),
        "unreturned_calls": sum(not call["returned"] for call in calls),
        "extra_calls": max(0, len(calls) - 1),
        "concept_counts": [len(group) for group in concepts],
        "plain_query_calls": sum(not group for group in concepts),
        "contains_cjk": [any(re.search(r"[\u4e00-\u9fff]", term) for term in group)
                         for group in concepts],
        "contains_latin": [any(re.search(r"[A-Za-z]", term) for term in group)
                           for group in concepts],
        "latency_s": task.get("elapsed_s"),
        "setup_latency_s": record.get("setup", {}).get("elapsed_s"),
        "tokens": _tokens(record, host),
        "answer_success": None,
    }


def summarize_dataset(dataset: Path, digest: str, runs: Path, host: str) -> dict[str, Any]:
    raw = dataset.read_bytes()
    if hashlib.sha256(raw).hexdigest() != digest:
        raise ValueError("frozen dataset digest mismatch")
    manifest = json.loads((runs / "manifest.json").read_text())
    if manifest.get("dataset_sha256") != digest or manifest.get("host") != host:
        raise ValueError("run manifest does not match frozen dataset and host")
    tasks = json.loads(raw)
    rows = []
    seen = set()
    for identifier, category, should_use, _prompt in tasks:
        if not re.fullmatch(r"[a-z][0-9]{2}", identifier) or identifier in seen:
            raise ValueError("invalid or duplicate opaque task id")
        seen.add(identifier)
        path = runs / f"{identifier}.json"
        row = {"id": identifier, "category": category, "expected_use": should_use}
        if path.exists():
            record = json.loads(path.read_text())
            if record.get("id") != identifier:
                raise ValueError("record identity does not match frozen task")
            record_digest = hashlib.sha256(path.read_bytes()).hexdigest()
            if manifest.get("experiment_sha256"):
                if record.get("experiment_sha256") != manifest["experiment_sha256"]:
                    raise ValueError("record identity does not match frozen experiment")
            elif manifest.get("record_sha256", {}).get(identifier) != record_digest:
                raise ValueError("legacy manifest does not bind the original record digest")
            row.update(summarize_record(record, host))
            row["record_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
        else:
            row.update({"host_completed": False, "missing_record": True, "answer_success": False})
        rows.append(row)
    return {"schema_version": 1, "dataset_sha256": digest, "host": host,
            "experiment_sha256": manifest.get("experiment_sha256"),
            "manifest_origin": manifest.get("manifest_origin", "frozen-before-execution"), "tasks": rows}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--sha256", required=True)
    parser.add_argument("--runs", type=Path, required=True)
    parser.add_argument("--host", choices=("claude", "codex"), required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = summarize_dataset(args.dataset, args.sha256, args.runs, args.host)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"Accounted for {len(report['tasks'])} frozen trials; independent answer grading still required.")


if __name__ == "__main__":
    main()
