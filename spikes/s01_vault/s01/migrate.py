"""Deterministic v0 -> v1 migration for the early ``facts.yaml`` shape (S01 spike).

v0 is the design-history format: a fact with ``evidence_level``, free-form ``evidence`` items,
text confidence and ``last_verified``. Migration derives ids from content so re-running it is
idempotent, and it never invents a stronger evidence signal than v0 recorded.
"""

from __future__ import annotations

import json
from typing import Any

from s01.records import SIGNALS, SchemaVersionError, deterministic_id, parse_record, sha256_text

CONFIDENCE = {"high": 0.9, "medium": 0.6, "low": 0.3}


def _timestamp(day: str) -> str:
    return f"{day}T00:00:00+00:00"


def _migrate_v0_fact(raw: dict[str, Any]) -> list[Any]:
    legacy_id = raw["id"]
    module = raw["type"]
    level = raw["evidence_level"]
    stamp = _timestamp(raw.get("last_verified") or raw["valid_from"])
    signals = ["exposure", level] if level in SIGNALS and level != "exposure" else ["exposure"]
    envelope = {
        "schema_version": 1, "recorded_at": stamp, "valid_from": None, "valid_until": None,
        "module": module, "trust": "untrusted_source", "policy_epoch": 0, "confidence": None,
        "review_status": "auto_derived", "supersedes": [], "change_kind": "assert",
        "retention": {"retention_class": "canonical", "purpose": "profile_evidence",
                      "expires_at": None, "full_content": False},
    }
    evidence = []
    for index, item in enumerate(raw.get("evidence", [])):
        evidence.append(envelope | {
            "record_type": "evidence",
            "id": deterministic_id("evd", f"v0:{legacy_id}:{index}"),
            "provenance": {"source_id": None, "episode": f"migration:v0:{item['source']}",
                           "locator": {"kind": "opml_node", "node_path": item.get("path", [])}},
            "subject": "concept:" + legacy_id.rsplit(".", 1)[-1],
            "signals": signals,
            "excerpt": None,
            "content_hash": sha256_text(json.dumps(item, sort_keys=True, ensure_ascii=False)),
            "observed_at": stamp,
        })
    fact = envelope | {
        "record_type": "fact",
        "id": deterministic_id("fct", f"v0:{legacy_id}"),
        "valid_from": raw.get("valid_from"),
        "valid_until": raw.get("valid_until"),
        "provenance": {"source_id": None, "episode": "migration:v0", "locator": None},
        "confidence": CONFIDENCE.get(str(raw.get("confidence")), None),
        "type": f"{module}.concept_state",
        "subject": "concept:" + legacy_id.rsplit(".", 1)[-1],
        "predicate": level,
        "object": True,
        "statement": raw["statement"],
        "evidence_ids": [e["id"] for e in evidence],
        "memory_ids": [],
        "observed_at": stamp,
        "ingested_at": None,
    }
    return [parse_record(item) for item in [*evidence, fact]]


def load_any(raw: dict[str, Any]) -> list[Any]:
    """Load a record of any supported version, migrating v0; refuse unknown future versions."""
    version = raw.get("schema_version", 0)
    if version == 0:
        return _migrate_v0_fact(raw)
    if version == 1:
        return [parse_record(raw)]
    raise SchemaVersionError(
        f"schema_version {version} is newer than this build supports; upgrade before migration"
    )
