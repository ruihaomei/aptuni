"""MarginNote 4 local source: read-only store access, knowledge digest, identity-exact deltas."""

from aptuni.sources.marginnote4.digest import Concept, Digest, build_digest
from aptuni.sources.marginnote4.scan import PARSER, MarginNoteScan, scan_marginnote
from aptuni.sources.marginnote4.store import MarginNoteStoreError, Probe, StoreSnapshot, probe, read_snapshot

__all__ = [
    "PARSER",
    "Concept",
    "Digest",
    "MarginNoteScan",
    "MarginNoteStoreError",
    "Probe",
    "StoreSnapshot",
    "build_digest",
    "probe",
    "read_snapshot",
    "scan_marginnote",
]
