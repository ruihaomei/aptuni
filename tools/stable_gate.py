#!/usr/bin/env python3
"""Evaluate Aptuni Stable readiness from content-free, commit-bound evidence."""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

PASS = "PASS"
FAIL = "FAIL"
INSUFFICIENT = "INSUFFICIENT REAL-WORLD DATA"
OWNER_ACTION = "OWNER ACTION REQUIRED"
EXACT_UX_PASS = "Aptuni User Experience Gate: PASS"

AUTOMATED_CHECKS: dict[str, tuple[str, ...]] = {
    "A": (
        "fresh_environment_install", "initialization", "guided_setup",
        "claude_connection", "codex_connection",
    ),
    "B": (
        "full_test_suite", "ruff", "strict_mypy", "contract_schema", "migrations",
    ),
    "C": (
        "canonical_validation", "crash_restart_recovery", "backup_restore",
        "correction_supersession", "no_known_data_loss_blocker",
    ),
    "D": (
        "zero_known_exposure_violations", "module_permissions", "task_scope_isolation",
        "grant_revocation", "purge_privacy", "aptuni_off_no_context",
    ),
    "E": (
        "claude_profile_memory_full", "codex_profile_memory_full", "task_scope_reset",
        "session_full_activation_disable",
    ),
    "F": (
        "scaffold_install_grant_invoke_revoke", "plugin_canonical_privacy_grant_boundaries",
        "top_down_learning",
    ),
    "G": (),
    "H": (),
    "I": (
        "install", "initialize", "connect_agent", "activate_profile_memory_full",
        "connect_source", "review_correct_context", "install_use_plugin", "disable_revoke",
    ),
    "J": (
        "wheel_sdist_install", "artifact_integrity", "dependency_license",
        "secret_private_data_scan", "release_workflow",
    ),
}

CATEGORY_NAMES = {
    "A": "Fresh Install",
    "B": "Core Correctness",
    "C": "Data Integrity",
    "D": "Privacy / Permission",
    "E": "Agent Integration",
    "F": "Plugin Platform",
    "G": "Retrieval / Context Quality",
    "H": "Longitudinal Stability",
    "I": "Documentation / New User Journey",
    "J": "Packaging / Supply Chain",
}
COMMIT_PATTERN = re.compile(r"[0-9a-f]{40}")
VERSION_PATTERN = re.compile(r"(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)(?:(?:a|b|rc)[0-9]+)?")


def _gate(status: str, reasons: list[str], metrics: dict[str, Any] | None = None) -> dict[str, Any]:
    value: dict[str, Any] = {"status": status, "reasons": reasons}
    if metrics is not None:
        value["metrics"] = metrics
    return value


def _boolean_gate(value: object, checks: tuple[str, ...]) -> dict[str, Any]:
    evidence = value if isinstance(value, dict) else {}
    reasons: list[str] = []
    for check in checks:
        result = evidence.get(check)
        if type(result) is not bool:
            reasons.append(f"{check}: missing or non-boolean evidence")
        elif not result:
            reasons.append(f"{check}: failed")
    return _gate(FAIL if reasons else PASS, reasons)


def _quality_failures(evidence: dict[str, Any]) -> list[str]:
    if evidence.get("exposure_violations", 0) > 0:
        return [f"exposure_violations={evidence['exposure_violations']} must be zero"]
    count_fields = ("returned_records", "useful_records", "noise_records")
    if not all(field in evidence for field in count_fields):
        return []
    returned = evidence["returned_records"]
    useful = evidence["useful_records"]
    noise = evidence["noise_records"]
    if useful + noise != returned:
        return ["useful_records + noise_records must equal returned_records"]
    if evidence.get("scored_trials", 0) < 30:
        return []
    precision = useful / returned if returned else 0.0
    noise_rate = noise / returned if returned else 0.0
    reasons = []
    if precision < 0.8:
        reasons.append(f"useful_precision={precision:.6f} is below 0.800000")
    if noise_rate > 0.2:
        reasons.append(f"noise_rate={noise_rate:.6f} exceeds 0.200000")
    return reasons


def _quality_gate(value: object) -> dict[str, Any]:
    evidence = value if isinstance(value, dict) else {}
    fields = (
        "scored_trials", "returned_records", "useful_records", "noise_records", "exposure_violations",
    )
    present = [field for field in fields if field in evidence]
    if any(type(evidence[field]) is not int or evidence[field] < 0 for field in present):
        return _gate(FAIL, ["owner-labelled metrics must be non-negative integers"])
    failures = _quality_failures(evidence)
    if failures:
        return _gate(FAIL, failures)
    missing = [field for field in fields if field not in evidence]
    if missing:
        return _gate(INSUFFICIENT, ["missing owner-labelled metrics: " + ", ".join(missing)])
    scored = evidence["scored_trials"]
    returned = evidence["returned_records"]
    useful = evidence["useful_records"]
    noise = evidence["noise_records"]
    violations = evidence["exposure_violations"]
    precision = useful / returned if returned else 0.0
    noise_rate = noise / returned if returned else 0.0
    metrics = {
        "scored_trials": scored,
        "returned_records": returned,
        "useful_precision": precision,
        "noise_rate": noise_rate,
        "exposure_violations": violations,
        "thresholds": {
            "minimum_scored_trials": 30,
            "minimum_useful_precision": 0.8,
            "maximum_noise_rate": 0.2,
            "maximum_exposure_violations": 0,
        },
    }
    if scored < 30:
        return _gate(INSUFFICIENT, [f"only {scored} of 30 real owner-labelled trials"], metrics)
    return _gate(PASS, [], metrics)


def _longitudinal_gate(value: object) -> dict[str, Any]:
    evidence = value if isinstance(value, dict) else {}
    fields = ("dogfood_days", "final_7_day_p0_p1_blockers", "privacy_data_integrity_blockers")
    present = [field for field in fields if field in evidence]
    if any(type(evidence[field]) is not int or evidence[field] < 0 for field in present):
        return _gate(FAIL, ["longitudinal metrics must be non-negative integers"])
    reasons = []
    if evidence.get("final_7_day_p0_p1_blockers", 0):
        reasons.append("final seven days contain unresolved P0/P1 blockers")
    if evidence.get("privacy_data_integrity_blockers", 0):
        reasons.append("privacy or data-integrity blockers remain")
    if reasons:
        return _gate(FAIL, reasons)
    missing = [field for field in fields if field not in evidence]
    if missing:
        return _gate(INSUFFICIENT, ["missing longitudinal metrics: " + ", ".join(missing)])
    metrics = {field: evidence[field] for field in fields}
    if evidence["dogfood_days"] < 14:
        return _gate(
            INSUFFICIENT,
            [f"only {evidence['dogfood_days']} of 14 required dogfood days"],
            metrics,
        )
    return _gate(PASS, [], metrics)


def _digest(value: dict[str, Any]) -> str:
    payload = json.dumps(value, ensure_ascii=True, separators=(",", ":"), sort_keys=True).encode()
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def _valid_commit(value: object) -> str | None:
    return value if isinstance(value, str) and COMMIT_PATTERN.fullmatch(value) else None


def _valid_version(value: object) -> str | None:
    return (
        value if isinstance(value, str) and len(value) <= 32 and VERSION_PATTERN.fullmatch(value)
        else None
    )


def _owner_sequence(
    evidence: dict[str, object],
    gates: dict[str, dict[str, Any]],
    automated_status: str,
    current_commit: str | None,
    evidence_commit: str | None,
    evidence_version: str | None,
) -> tuple[str | None, str | None, str]:
    ux = evidence.get("ux_gate")
    ux_value = ux if isinstance(ux, dict) else {}
    ux_passed = (
        current_commit is not None
        and ux_value.get("statement") == EXACT_UX_PASS
        and ux_value.get("commit") == current_commit
    )
    gates["UX"] = _gate(
        PASS if ux_passed else OWNER_ACTION,
        [] if ux_passed else ["exact UX Gate PASS is not bound to this candidate commit"],
    )
    clean_room_request = (
        _digest({
            "kind": "clean-room-audit",
            "commit": evidence_commit,
            "version": evidence_version,
            "automated": {category: gates[category] for category in AUTOMATED_CHECKS},
            "ux_gate": PASS,
        })
        if automated_status == PASS and ux_passed else None
    )
    audit = evidence.get("clean_room_audit")
    audit_value = audit if isinstance(audit, dict) else {}
    audit_passed = bool(
        clean_room_request
        and audit_value.get("passed") is True
        and audit_value.get("commit") == current_commit
        and audit_value.get("prerequisite_digest") == clean_room_request
    )
    if automated_status != PASS:
        gates["CLEAN_ROOM_AUDIT"] = _gate(automated_status, ["clean-room audit waits for Automated PASS"])
    elif not ux_passed:
        gates["CLEAN_ROOM_AUDIT"] = _gate(OWNER_ACTION, ["clean-room audit waits for the UX Gate"])
    elif audit_passed:
        gates["CLEAN_ROOM_AUDIT"] = _gate(PASS, [])
    elif audit_value.get("passed") is None:
        gates["CLEAN_ROOM_AUDIT"] = _gate(OWNER_ACTION, ["clean-room audit has not been recorded"])
    else:
        gates["CLEAN_ROOM_AUDIT"] = _gate(FAIL, ["clean-room audit is not bound to the current prerequisite digest"])
    publication_request = (
        _digest({
            "kind": "stable-publication",
            "commit": evidence_commit,
            "version": evidence_version,
            "clean_room_audit_request_digest": clean_room_request,
        }) if audit_passed else None
    )
    publication = evidence.get("stable_publication")
    publication_value = publication if isinstance(publication, dict) else {}
    publication_passed = bool(
        publication_request
        and publication_value.get("authorized") is True
        and publication_value.get("commit") == current_commit
        and publication_value.get("request_digest") == publication_request
    )
    if not audit_passed:
        gates["STABLE_PUBLICATION"] = _gate(
            gates["CLEAN_ROOM_AUDIT"]["status"],
            ["Stable publication authorization waits for all prior gates"],
        )
    else:
        gates["STABLE_PUBLICATION"] = _gate(
            PASS if publication_passed else OWNER_ACTION,
            [] if publication_passed else ["explicit Stable publication authorization is absent"],
        )
    if automated_status != PASS:
        release_status = automated_status
    elif not ux_passed:
        release_status = OWNER_ACTION
    elif not audit_passed:
        release_status = gates["CLEAN_ROOM_AUDIT"]["status"]
    else:
        release_status = PASS if publication_passed else OWNER_ACTION
    return clean_room_request, publication_request, release_status


def evaluate(
    evidence: dict[str, object], *, current_commit: str, worktree_clean: bool = True,
) -> dict[str, Any]:
    automated = evidence.get("automated")
    automated_values = automated if isinstance(automated, dict) else {}
    gates = {
        category: (
            _quality_gate(automated_values.get(category)) if category == "G"
            else _longitudinal_gate(automated_values.get(category)) if category == "H"
            else _boolean_gate(automated_values.get(category), checks)
        )
        for category, checks in AUTOMATED_CHECKS.items()
    }
    for category, name in CATEGORY_NAMES.items():
        gates[category]["name"] = name

    candidate = evidence.get("candidate")
    candidate_value = candidate if isinstance(candidate, dict) else {}
    evidence_commit = _valid_commit(candidate_value.get("commit"))
    evidence_version = _valid_version(candidate_value.get("version"))
    safe_current_commit = _valid_commit(current_commit)
    commit_matches = (
        evidence_commit is not None and evidence_commit == safe_current_commit and evidence_version is not None
    )
    candidate_reasons = [] if commit_matches else ["evidence is not bound to the current candidate commit"]
    if worktree_clean is not True:
        candidate_reasons.append("working tree has uncommitted changes; the candidate is not the commit")

    automated_statuses = [gate["status"] for gate in gates.values()]
    if candidate_reasons or FAIL in automated_statuses:
        automated_status = FAIL
    elif INSUFFICIENT in automated_statuses:
        automated_status = INSUFFICIENT
    else:
        automated_status = PASS

    automated_gate = _gate(automated_status, candidate_reasons)
    clean_room_request, publication_request, release_status = _owner_sequence(
        evidence, gates, automated_status, safe_current_commit, evidence_commit, evidence_version,
    )
    return {
        "schema_version": 1,
        "candidate": {
            "commit": evidence_commit,
            "version": evidence_version,
            "current_commit": safe_current_commit,
            "commit_matches": commit_matches,
            "worktree_clean": worktree_clean is True,
        },
        "automated_stable_gate": automated_gate,
        "release_readiness": _gate(release_status, []),
        "clean_room_audit_request_digest": clean_room_request,
        "stable_publication_request_digest": publication_request,
        "gates": gates,
    }


def _current_commit(root: Path) -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=root, check=True, capture_output=True, text=True,
    ).stdout.strip()


def _worktree_clean(root: Path, output: Path | None) -> bool:
    status = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=normal"],
        cwd=root, check=True, capture_output=True, text=True,
    ).stdout
    ignored_output = output.relative_to(root).as_posix() if output and output.is_relative_to(root) else None
    return all(line[:3] == "?? " and line[3:] == ignored_output for line in status.splitlines())


def _write_atomic(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except BaseException:
        with contextlib.suppress(FileNotFoundError):
            os.unlink(temporary)
        raise


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args(argv)
    try:
        evidence: dict[str, object] = (
            json.loads(args.evidence.read_text(encoding="utf-8")) if args.evidence else {"schema_version": 1}
        )
        version = evidence.get("schema_version") if isinstance(evidence, dict) else None
        if type(version) is not int or version != 1:
            raise ValueError("evidence must be a schema_version 1 JSON object")
        root = args.root.resolve()
        output = args.output.resolve() if args.output else None
        report = evaluate(
            evidence,
            current_commit=_current_commit(root),
            worktree_clean=_worktree_clean(root, output),
        )
        if output is not None:
            _write_atomic(output, report)
        else:
            print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    except (OSError, ValueError, RecursionError, subprocess.CalledProcessError) as error:
        print(f"stable_gate_invalid: {error}", file=sys.stderr)
        return 2
    return 0 if report["release_readiness"]["status"] == PASS else 1


if __name__ == "__main__":
    raise SystemExit(main())
