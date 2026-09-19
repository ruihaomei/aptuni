"""Public facade of the draft common source contract (S05A)."""

from s05a.codec import delta_from_json, delta_to_json
from s05a.extensions import ExtensionRegistry, ExtensionSpec, default_registry
from s05a.records import (
    CandidateDelta,
    ContractError,
    Extension,
    Operation,
    Snapshot,
    SnapshotItem,
    SourceLocator,
    canonical_json,
)

__all__ = [
    "CandidateDelta",
    "ContractError",
    "Extension",
    "ExtensionRegistry",
    "ExtensionSpec",
    "Operation",
    "Snapshot",
    "SnapshotItem",
    "SourceLocator",
    "canonical_json",
    "default_registry",
    "delta_from_json",
    "delta_to_json",
]
