"""Evidence-only prototype for ADR-0013 host confinement status.

This module deliberately cannot produce a ``confined`` result. It models only
unsafe facts the core can observe and the absence of such proof.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Iterable, Mapping, Sequence


class ProfileState(StrEnum):
    INSTALLED = "installed"
    MISSING = "missing"
    DRIFTED = "drifted"
    UNVERIFIED = "unverified"


class ConfinementEvidence(StrEnum):
    CANARY_WRITE_SUCCEEDED = "canary_write_succeeded"
    SOCKET_CONNECT_SUCCEEDED = "socket_connect_succeeded"
    APPLE_EVENT_SUCCEEDED = "apple_event_succeeded"
    ESCAPE_SETTING_VISIBLE = "escape_setting_visible"
    PROTECTED_PATH_WRITABLE = "protected_path_writable"
    UNBUNDLED_ENTRY_VISIBLE = "unbundled_entry_visible"
    HOST_ESCALATION_AVAILABLE = "host_escalation_available"
    PROBE_SKIPPED = "probe_skipped"
    PROBE_MISDIRECTED = "probe_misdirected"
    AGENT_REPORTED_ONLY = "agent_reported_only"
    CLONE_PROVENANCE_UNOBSERVABLE = "clone_provenance_unobservable"


_POSITIVE_UNSAFE = frozenset(
    {
        ConfinementEvidence.CANARY_WRITE_SUCCEEDED,
        ConfinementEvidence.SOCKET_CONNECT_SUCCEEDED,
        ConfinementEvidence.APPLE_EVENT_SUCCEEDED,
        ConfinementEvidence.ESCAPE_SETTING_VISIBLE,
        ConfinementEvidence.PROTECTED_PATH_WRITABLE,
        ConfinementEvidence.UNBUNDLED_ENTRY_VISIBLE,
        ConfinementEvidence.HOST_ESCALATION_AVAILABLE,
    }
)


@dataclass(frozen=True, slots=True)
class HostStatus:
    profile: ProfileState
    confinement: str
    reason_codes: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.confinement not in {"not_in_effect", "unverified"}:
            raise ValueError("invalid_confinement_status")

    def to_host_payload(self) -> dict[str, object]:
        """Return the complete host-visible payload; never include evidence detail."""
        return {
            "profile": self.profile.value,
            "confinement": self.confinement,
            "reason_codes": list(self.reason_codes),
        }


@dataclass(frozen=True, slots=True)
class HostProfileSpec:
    """Security-relevant values expected in a host's effective settings."""

    required: Mapping[str, object]
    exact_sequences: frozenset[str] = frozenset()


@dataclass(frozen=True, slots=True)
class ProfileObservation:
    profile: ProfileState
    reason_codes: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class EffectiveSettingsSnapshot:
    """A settings projection plus proof that every normative source was merged."""

    settings: Mapping[str, object] | None
    complete: bool


_MISSING = object()


def _dotted_value(settings: Mapping[str, object], dotted_key: str) -> object:
    current: object = settings
    for part in dotted_key.split("."):
        if not isinstance(current, Mapping) or part not in current:
            return _MISSING
        current = current[part]
    return current


def _is_sequence(value: object) -> bool:
    return isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray))


def evaluate_profile(
    spec: HostProfileSpec,
    snapshot: EffectiveSettingsSnapshot,
) -> ProfileObservation:
    """Compare trusted effective settings with the bundled security profile.

    Details and values never enter the returned reason codes. Unknown settings
    are ignored; only required security keys participate in the verdict.
    """
    if not snapshot.complete:
        return ProfileObservation(
            ProfileState.UNVERIFIED, ("effective_settings_unobservable",)
        )
    if snapshot.settings is None:
        return ProfileObservation(ProfileState.MISSING, ("profile_missing",))
    effective_settings = snapshot.settings

    reasons: set[str] = set()
    for key, expected in spec.required.items():
        actual = _dotted_value(effective_settings, key)
        if actual is _MISSING:
            reasons.add("required_key_missing")
            continue
        if _is_sequence(expected):
            if not _is_sequence(actual):
                reasons.add("required_value_mismatch")
                continue
            expected_items = tuple(expected)  # type: ignore[arg-type]
            actual_items = tuple(actual)  # type: ignore[arg-type]
            if key in spec.exact_sequences:
                matches = actual_items == expected_items
            else:
                matches = all(item in actual_items for item in expected_items)
            if not matches:
                reasons.add("required_value_mismatch")
        elif actual != expected:
            reasons.add("required_value_mismatch")

    if reasons:
        return ProfileObservation(ProfileState.DRIFTED, tuple(sorted(reasons)))
    return ProfileObservation(ProfileState.INSTALLED, ())


def derive_status(
    profile: ProfileState,
    evidence: Iterable[ConfinementEvidence],
    *,
    untrusted_metadata: Mapping[str, object] | None = None,
) -> HostStatus:
    """Derive status from core evidence only.

    ``untrusted_metadata`` exists to make the trust boundary explicit and
    testable. Labels, environment values and adapter claims are ignored.
    """
    del untrusted_metadata
    observed = frozenset(evidence)
    unsafe = {item.value for item in observed & _POSITIVE_UNSAFE}
    profile_reasons: set[str] = set()
    if profile is ProfileState.UNVERIFIED:
        profile_reasons.add("effective_settings_unobservable")
    if profile is ProfileState.MISSING:
        profile_reasons.add("profile_missing")
    if profile is ProfileState.DRIFTED:
        profile_reasons.add("profile_drifted")

    if unsafe or profile in {ProfileState.MISSING, ProfileState.DRIFTED}:
        return HostStatus(
            profile, "not_in_effect", tuple(sorted(unsafe | profile_reasons))
        )
    if profile is ProfileState.UNVERIFIED:
        return HostStatus(profile, "unverified", tuple(sorted(profile_reasons)))
    incomplete = tuple(sorted(item.value for item in observed))
    return HostStatus(
        profile,
        "unverified",
        incomplete if incomplete else ("positive_evidence_absent",),
    )


class HostEvidenceStore:
    """In-memory spike store whose evidence lifetime is one host session."""

    def __init__(self) -> None:
        self._sessions: dict[str, tuple[ProfileState, set[ConfinementEvidence]]] = {}

    def start(self, session_key: str, profile: ProfileState) -> None:
        if not session_key:
            raise ValueError("empty_session_key")
        self._sessions[session_key] = (profile, set())

    def record(self, session_key: str, evidence: ConfinementEvidence) -> None:
        try:
            self._sessions[session_key][1].add(evidence)
        except KeyError as error:
            raise KeyError("unknown_session") from error

    def status(self, session_key: str) -> HostStatus:
        try:
            profile, evidence = self._sessions[session_key]
        except KeyError as error:
            raise KeyError("unknown_session") from error
        return derive_status(profile, evidence)


@dataclass(frozen=True, slots=True)
class PathIdentity:
    """Observable identity for one protected filesystem object."""

    real_path: Path
    device: int
    inode: int

    @classmethod
    def capture(cls, path: Path) -> "PathIdentity":
        real_path = path.resolve(strict=True)
        stat = real_path.stat()
        return cls(real_path, stat.st_dev, stat.st_ino)

    def matches(self, candidate: Path) -> bool:
        real_candidate = candidate.resolve(strict=True)
        stat = real_candidate.stat()
        return real_candidate == self.real_path or (
            stat.st_dev == self.device and stat.st_ino == self.inode
        )

    def unverifiable_copy_evidence(self, candidate: Path) -> ConfinementEvidence:
        """Classify copy/clone provenance conservatively when identity differs.

        APFS does not expose clone ancestry through portable stat metadata. An
        independent copy and a copy-on-write clone therefore cannot be safely
        distinguished here; both remain unverified.
        """
        if self.matches(candidate):
            raise ValueError("candidate_is_same_object")
        os.stat(candidate)
        return ConfinementEvidence.CLONE_PROVENANCE_UNOBSERVABLE
