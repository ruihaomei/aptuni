"""Public facade of the draft common source contract (S05A)."""

from aptuni.sources.codec import delta_from_json, delta_to_json
from aptuni.sources.extensions import ExtensionRegistry, ExtensionSpec, default_registry
from aptuni.sources.records import (
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
