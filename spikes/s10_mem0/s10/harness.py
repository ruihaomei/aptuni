from __future__ import annotations

import hashlib
import ipaddress
import json
import os
import shutil
import socket
import sys
from contextlib import AbstractContextManager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

MAX_FIELD_CHARS = 512
MAX_SCAN_FILES = 128
MAX_SCAN_BYTES = 1_048_576
REQUIRED_RECORD_KEYS = {
    "canonical_id",
    "scope",
    "status",
    "current_text",
    "revisions",
    "updated_at",
}


class AdmissionError(RuntimeError):
    """A fail-closed S10 admission error."""


@dataclass(frozen=True)
class CanonicalRecord:
    canonical_id: str
    scope: str
    status: str
    current_text: str
    revisions: tuple[str, ...]
    updated_at: str


@dataclass(frozen=True)
class Fixture:
    path: Path
    sha256: str
    records: tuple[CanonicalRecord, ...]

    @property
    def markers(self) -> tuple[str, ...]:
        values: list[str] = []
        for record in self.records:
            values.append(record.current_text)
            values.extend(record.revisions)
        return tuple(values)


@dataclass(frozen=True)
class DriverDiagnostics:
    file_classes: dict[str, str]
    raw_interaction_files: tuple[str, ...]
    event_counts: dict[str, int]


class ProjectionDriver(Protocol):
    name: str
    version: str

    def initialize(self) -> None: ...

    def project(self, record: CanonicalRecord) -> None: ...

    def search(self, query: str, *, limit: int) -> list[dict[str, Any]]: ...

    def enumerate_public(self) -> list[dict[str, Any]]: ...

    def restart(self) -> ProjectionDriver: ...

    def fresh(self, root: Path) -> ProjectionDriver: ...

    def diagnostics(self) -> DriverDiagnostics: ...

    def reset(self) -> None: ...


class NetworkGuard(AbstractContextManager["NetworkGuard"]):
    """Deny non-loopback Internet traffic while allowing local runtime plumbing."""

    def __init__(self) -> None:
        self.attempts = 0
        self._original_socket = socket.socket
        self._original_getaddrinfo = socket.getaddrinfo

    def __enter__(self) -> NetworkGuard:
        original = self._original_socket
        original_getaddrinfo = self._original_getaddrinfo
        guard = self

        def deny_non_loopback(address: Any) -> None:
            if not isinstance(address, tuple) or not address:
                return
            host = str(address[0]).split("%", 1)[0]
            try:
                is_loopback = ipaddress.ip_address(host).is_loopback
            except ValueError:
                is_loopback = host.casefold() == "localhost"
            if not is_loopback:
                guard.attempts += 1
                raise AdmissionError("s10_network_denied")

        class GuardedSocket(original):  # type: ignore[misc, valid-type]
            @staticmethod
            def _deny_non_loopback(address: Any) -> None:
                deny_non_loopback(address)

            def connect(self, address: Any) -> None:
                self._deny_non_loopback(address)
                return super().connect(address)

            def connect_ex(self, address: Any) -> int:
                self._deny_non_loopback(address)
                return super().connect_ex(address)

            def bind(self, address: Any) -> None:
                self._deny_non_loopback(address)
                return super().bind(address)

            def send(self, data: bytes, flags: int = 0) -> int:
                self._deny_connected_peer()
                return super().send(data, flags)

            def sendall(self, data: bytes, flags: int = 0) -> None:
                self._deny_connected_peer()
                return super().sendall(data, flags)

            def sendto(self, data: bytes, *args: Any) -> int:
                if args:
                    self._deny_non_loopback(args[-1])
                return super().sendto(data, *args)

            def sendmsg(self, buffers: Any, *args: Any) -> int:
                if args and isinstance(args[-1], tuple):
                    self._deny_non_loopback(args[-1])
                return super().sendmsg(buffers, *args)

            def _deny_connected_peer(self) -> None:
                try:
                    peer = self.getpeername()
                except OSError:
                    return
                self._deny_non_loopback(peer)

        socket.socket = GuardedSocket

        def guarded_getaddrinfo(host: Any, *args: Any, **kwargs: Any) -> Any:
            if host is not None:
                deny_non_loopback((host, 0))
            return original_getaddrinfo(host, *args, **kwargs)

        socket.getaddrinfo = guarded_getaddrinfo
        return self

    def __exit__(self, *exc: object) -> None:
        socket.socket = self._original_socket
        socket.getaddrinfo = self._original_getaddrinfo


def _canonical_json(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode()


def _bounded_text(value: Any, *, field: str) -> str:
    if not isinstance(value, str) or not value or len(value) > MAX_FIELD_CHARS:
        raise AdmissionError(f"fixture_invalid_{field}")
    return value


def _safe_child(root: Path, child: Path) -> Path:
    resolved_root = root.resolve()
    resolved_child = child.resolve()
    if resolved_child != resolved_root and resolved_root not in resolved_child.parents:
        raise AdmissionError("path_outside_disposable_root")
    cursor = child
    while cursor != root:
        if cursor.is_symlink():
            raise AdmissionError("symlink_in_disposable_root")
        cursor = cursor.parent
    return resolved_child


def load_fixture(manifest_path: Path) -> Fixture:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("fixture_schema_version") != 1:
        raise AdmissionError("fixture_manifest_schema_unknown")
    fixture_name = manifest.get("fixture")
    if not isinstance(fixture_name, str) or Path(fixture_name).name != fixture_name:
        raise AdmissionError("fixture_path_invalid")
    fixture_path = manifest_path.parent / fixture_name
    raw = fixture_path.read_bytes()
    if len(raw) > int(manifest.get("max_bytes", 0)):
        raise AdmissionError("fixture_too_large")
    digest = hashlib.sha256(raw).hexdigest()
    if digest != manifest.get("sha256"):
        raise AdmissionError("fixture_digest_mismatch")
    payload = json.loads(raw)
    if payload.get("schema_version") != 1 or not isinstance(payload.get("records"), list):
        raise AdmissionError("fixture_schema_unknown")
    rows = payload["records"]
    if len(rows) > int(manifest.get("max_records", 0)):
        raise AdmissionError("fixture_record_limit")
    records: list[CanonicalRecord] = []
    seen: set[str] = set()
    for row in rows:
        if not isinstance(row, dict) or set(row) != REQUIRED_RECORD_KEYS:
            raise AdmissionError("fixture_record_shape")
        canonical_id = _bounded_text(row["canonical_id"], field="canonical_id")
        if canonical_id in seen:
            raise AdmissionError("fixture_duplicate_id")
        seen.add(canonical_id)
        status = _bounded_text(row["status"], field="status")
        if status not in {"active", "tombstoned"}:
            raise AdmissionError("fixture_invalid_status")
        revisions_value = row["revisions"]
        if not isinstance(revisions_value, list) or len(revisions_value) > 4:
            raise AdmissionError("fixture_invalid_revisions")
        records.append(
            CanonicalRecord(
                canonical_id=canonical_id,
                scope=_bounded_text(row["scope"], field="scope"),
                status=status,
                current_text=_bounded_text(row["current_text"], field="current_text"),
                revisions=tuple(_bounded_text(item, field="revision") for item in revisions_value),
                updated_at=_bounded_text(row["updated_at"], field="updated_at"),
            )
        )
    return Fixture(path=fixture_path, sha256=digest, records=tuple(records))


def tree_digest(root: Path) -> str:
    entries: list[dict[str, str]] = []
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise AdmissionError("canonical_tree_contains_symlink")
        if path.is_file():
            entries.append(
                {
                    "path": path.relative_to(root).as_posix(),
                    "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                }
            )
    return hashlib.sha256(_canonical_json(entries)).hexdigest()


def marker_inventory(root: Path, markers: tuple[str, ...]) -> dict[str, int]:
    marker_bytes = tuple(marker.encode() for marker in markers)
    counts = {hashlib.sha256(marker).hexdigest()[:16]: 0 for marker in marker_bytes}
    files = 0
    scanned_bytes = 0
    for path in sorted(root.rglob("*")):
        _safe_child(root, path)
        if not path.is_file():
            continue
        files += 1
        if files > MAX_SCAN_FILES:
            raise AdmissionError("inventory_file_limit")
        raw = path.read_bytes()
        scanned_bytes += len(raw)
        if scanned_bytes > MAX_SCAN_BYTES:
            raise AdmissionError("inventory_byte_limit")
        for marker in marker_bytes:
            counts[hashlib.sha256(marker).hexdigest()[:16]] += raw.count(marker)
    return counts


def classified_marker_inventory(
    root: Path,
    markers: tuple[str, ...],
    file_classes: dict[str, str],
) -> dict[str, dict[str, int]]:
    inventory = {hashlib.sha256(marker.encode()).hexdigest()[:16]: {} for marker in markers}
    scanned_bytes = 0
    for relative, storage_class in sorted(file_classes.items()):
        path = _safe_child(root, root / relative)
        if not path.is_file():
            raise AdmissionError("classified_inventory_file_missing")
        raw = path.read_bytes()
        scanned_bytes += len(raw)
        if scanned_bytes > MAX_SCAN_BYTES:
            raise AdmissionError("inventory_byte_limit")
        for marker in markers:
            marker_key = hashlib.sha256(marker.encode()).hexdigest()[:16]
            count = raw.count(marker.encode())
            if count:
                inventory[marker_key][storage_class] = inventory[marker_key].get(storage_class, 0) + count
    return inventory


def inventory_files(root: Path) -> tuple[str, ...]:
    files: list[str] = []
    for path in sorted(root.rglob("*")):
        _safe_child(root, path)
        if path.is_file():
            files.append(path.relative_to(root).as_posix())
            if len(files) > MAX_SCAN_FILES:
                raise AdmissionError("inventory_file_limit")
    return tuple(files)


class FixtureDriver:
    name = "fixture"
    version = "1"

    def __init__(self, root: Path, *, fail_operation: str | None = None) -> None:
        self.root = _safe_child(root, root)
        self.fail_operation = fail_operation
        self.state_path = self.root / "projection.json"
        self.history_path = self.root / "history.jsonl"

    def initialize(self) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        os.chmod(self.root, 0o700)
        if not self.state_path.exists():
            self.state_path.write_bytes(_canonical_json({"items": {}}))
            os.chmod(self.state_path, 0o600)

    def _state(self) -> dict[str, Any]:
        return json.loads(self.state_path.read_text(encoding="utf-8"))

    def project(self, record: CanonicalRecord) -> None:
        if self.fail_operation == "project":
            raise AdmissionError("fixture_injected_project_failure")
        state = self._state()
        items = state["items"]
        previous = items.get(record.canonical_id)
        if record.status == "tombstoned":
            items.pop(record.canonical_id, None)
            event = "DELETE"
        else:
            items[record.canonical_id] = {
                "memory": record.current_text,
                "metadata": {
                    "aptuni_canonical_id": record.canonical_id,
                    "aptuni_scope": record.scope,
                    "aptuni_schema_version": 1,
                },
            }
            event = "UPDATE" if previous else "ADD"
        self.state_path.write_bytes(_canonical_json(state))
        with self.history_path.open("ab") as stream:
            stream.write(_canonical_json({"canonical_id": record.canonical_id, "event": event}))
        os.chmod(self.history_path, 0o600)

    def search(self, query: str, *, limit: int) -> list[dict[str, Any]]:
        query_terms = query.casefold().split()
        values = list(self._state()["items"].values())
        matches = [item for item in values if any(term in item["memory"].casefold() for term in query_terms)]
        return matches[:limit]

    def enumerate_public(self) -> list[dict[str, Any]]:
        return list(self._state()["items"].values())

    def restart(self) -> FixtureDriver:
        restarted = type(self)(self.root, fail_operation=self.fail_operation)
        restarted.initialize()
        return restarted

    def fresh(self, root: Path) -> FixtureDriver:
        return type(self)(root, fail_operation=self.fail_operation)

    def diagnostics(self) -> DriverDiagnostics:
        event_counts: dict[str, int] = {}
        if self.history_path.exists():
            for line in self.history_path.read_text(encoding="utf-8").splitlines():
                event = str(json.loads(line)["event"])
                event_counts[event] = event_counts.get(event, 0) + 1
        return DriverDiagnostics(
            file_classes={
                self.history_path.name: "history",
                self.state_path.name: "current_projection",
            },
            raw_interaction_files=(),
            event_counts=event_counts,
        )

    def reset(self) -> None:
        if self.fail_operation == "reset":
            raise AdmissionError("fixture_injected_reset_failure")
        shutil.rmtree(self.root)
        self.root.mkdir(mode=0o700)


def _assert_projection(records: tuple[CanonicalRecord, ...], rows: list[dict[str, Any]]) -> None:
    expected = {
        record.canonical_id: {
            "memory": record.current_text,
            "scope": record.scope,
            "schema_version": 1,
        }
        for record in records
        if record.status == "active"
    }
    actual: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get("metadata"), dict):
            raise AdmissionError("projection_shape_invalid")
        metadata = row["metadata"]
        canonical_id = metadata.get("aptuni_canonical_id")
        if not isinstance(canonical_id, str) or canonical_id in actual:
            raise AdmissionError("projection_identity_invalid")
        actual[canonical_id] = {
            "memory": row.get("memory"),
            "scope": metadata.get("aptuni_scope"),
            "schema_version": metadata.get("aptuni_schema_version"),
        }
    if actual != expected:
        raise AdmissionError("projection_mismatch")


def _projection_sequence(record: CanonicalRecord) -> tuple[CanonicalRecord, ...]:
    operations: list[CanonicalRecord] = []
    for revision in record.revisions:
        operations.append(
            CanonicalRecord(
                canonical_id=record.canonical_id,
                scope=record.scope,
                status="active",
                current_text=revision,
                revisions=(),
                updated_at=record.updated_at,
            )
        )
    if record.status == "tombstoned" and not record.revisions:
        operations.append(
            CanonicalRecord(
                canonical_id=record.canonical_id,
                scope=record.scope,
                status="active",
                current_text=record.current_text,
                revisions=(),
                updated_at=record.updated_at,
            )
        )
    operations.append(record)
    return tuple(operations)


def run_admission(
    *,
    manifest_path: Path,
    canonical_root: Path,
    provider_root: Path,
    driver: ProjectionDriver,
) -> dict[str, Any]:
    fixture = load_fixture(manifest_path)
    corrected = next(record for record in fixture.records if record.revisions)
    tombstoned = next(record for record in fixture.records if record.status == "tombstoned")
    canonical_before = tree_digest(canonical_root)
    telemetry_names = ("MEM0_TELEMETRY", "MEM0_TELEMETRY_ENABLED")
    previous_telemetry = {name: os.environ.get(name) for name in telemetry_names}
    provider_prefixes = ("mem0", "posthog", "qdrant_client")
    provider_preloaded = driver.name == "mem0" and any(
        name == prefix or name.startswith(f"{prefix}.")
        for name in sys.modules
        for prefix in provider_prefixes
    )
    if provider_preloaded:
        raise AdmissionError("provider_preloaded_before_network_guard")
    try:
        for name in telemetry_names:
            os.environ[name] = "False"
        with NetworkGuard() as guard:
            driver.initialize()
            after_correction: dict[str, dict[str, int]] = {}
            after_tombstone: dict[str, dict[str, int]] = {}
            for record in fixture.records:
                for operation in _projection_sequence(record):
                    driver.project(operation)
                diagnostics_at_record = driver.diagnostics()
                classified = classified_marker_inventory(
                    provider_root,
                    fixture.markers,
                    diagnostics_at_record.file_classes,
                )
                if record.revisions:
                    after_correction = classified
                if record.status == "tombstoned":
                    after_tombstone = classified
            restarted = driver.restart()
            projected = restarted.enumerate_public()
            _assert_projection(fixture.records, projected)
            if not restarted.search("compact review", limit=4):
                raise AdmissionError("search_empty")
            before_reset = marker_inventory(provider_root, fixture.markers)
            files_before_reset = inventory_files(provider_root)
            diagnostics = restarted.diagnostics()
            unknown_files = sorted(set(files_before_reset) - set(diagnostics.file_classes))
            if unknown_files:
                raise AdmissionError("provider_unknown_copy")
            if diagnostics.raw_interaction_files:
                raise AdmissionError("raw_interaction_persisted")
            required_events = {"ADD", "UPDATE", "DELETE"}
            if not required_events.issubset(diagnostics.event_counts):
                raise AdmissionError("provider_lifecycle_event_missing")
            restarted.reset()
            after_reset = marker_inventory(provider_root, fixture.markers)
            files_after_reset = inventory_files(provider_root)
            rebuild_root = provider_root.parent / f"{provider_root.name}-rebuild"
            rebuild = restarted.fresh(rebuild_root)
            rebuild.initialize()
            for record in fixture.records:
                rebuild.project(record)
            rebuilt_rows = rebuild.enumerate_public()
            _assert_projection(fixture.records, rebuilt_rows)
            rebuild_diagnostics = rebuild.diagnostics()
            rebuild_files = inventory_files(rebuild_root)
            rebuild_unknown = sorted(set(rebuild_files) - set(rebuild_diagnostics.file_classes))
            if rebuild_unknown:
                raise AdmissionError("rebuild_unknown_copy")
            after_rebuild = classified_marker_inventory(
                rebuild_root,
                fixture.markers,
                rebuild_diagnostics.file_classes,
            )
            rebuild.reset()
    finally:
        for name, value in previous_telemetry.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value
    if any(after_reset.values()):
        raise AdmissionError("marker_remains_after_reset")
    canonical_after = tree_digest(canonical_root)
    if canonical_after != canonical_before:
        raise AdmissionError("canonical_tree_changed")
    corrected_old_key = hashlib.sha256(corrected.revisions[0].encode()).hexdigest()[:16]
    corrected_current_key = hashlib.sha256(corrected.current_text.encode()).hexdigest()[:16]
    tombstoned_key = hashlib.sha256(tombstoned.current_text.encode()).hexdigest()[:16]
    record_delete_removes_all_copies = not after_tombstone[tombstoned_key]
    if after_rebuild[corrected_old_key] or after_rebuild[tombstoned_key]:
        raise AdmissionError("rebuild_resurrected_historical_marker")
    if not after_rebuild[corrected_current_key]:
        raise AdmissionError("rebuild_missing_current_marker")
    missing_export_fields = ["canonical_revision_history", "tombstones", "embedding_rebuild_instructions"]
    return {
        "schema_version": 1,
        "driver": {"name": driver.name, "version": driver.version},
        "fixture": {
            "sha256": fixture.sha256,
            "record_count": len(fixture.records),
            "active_count": sum(record.status == "active" for record in fixture.records),
            "tombstone_count": sum(record.status == "tombstoned" for record in fixture.records),
        },
        "checks": {
            "canonical_unchanged": True,
            "network_attempts": guard.attempts,
            "raw_interaction_persisted": bool(diagnostics.raw_interaction_files),
            "restart_projection_matches": True,
            "rebuild_projection_matches": True,
            "lifecycle_event_counts": diagnostics.event_counts,
            "markers_found_before_reset": sum(before_reset.values()),
            "markers_found_after_reset": 0,
            "files_before_reset": len(files_before_reset),
            "files_after_reset": len(files_after_reset),
            "unknown_copies": len(unknown_files),
            "telemetry_disabled_before_initialize": True,
            "network_guard_paths": [
                "bind",
                "connect",
                "connect_ex",
                "getaddrinfo",
                "send",
                "sendall",
                "sendmsg",
                "sendto",
            ],
            "provider_preloaded_before_network_guard": provider_preloaded,
        },
        "retention": {
            "after_correction": {
                "corrected_old": after_correction[corrected_old_key],
                "corrected_current": after_correction[corrected_current_key],
            },
            "after_tombstone": {"tombstoned": after_tombstone[tombstoned_key]},
            "after_fresh_rebuild": {
                "corrected_old": after_rebuild[corrected_old_key],
                "corrected_current": after_rebuild[corrected_current_key],
                "tombstoned": after_rebuild[tombstoned_key],
            },
            "record_delete_removes_all_copies": record_delete_removes_all_copies,
            "required_delete_strategy": (
                "record_delete" if record_delete_removes_all_copies else "whole_store_rebuild"
            ),
        },
        "export": {
            "public_count": len(projected),
            "lossless": False,
            "missing_fields": missing_export_fields,
        },
        "verdict": "FIXTURE_PASS" if driver.name == "fixture" else "PROJECTION_PATH_PASS",
    }
