from __future__ import annotations

import hashlib
import json
import os
import socket
import tempfile
import unittest
from pathlib import Path

from s10.harness import (
    AdmissionError,
    DriverDiagnostics,
    FixtureDriver,
    NetworkGuard,
    load_fixture,
    marker_inventory,
    run_admission,
    tree_digest,
)


class HarnessTests(unittest.TestCase):
    def setUp(self) -> None:
        self.spike_root = Path(__file__).resolve().parents[1]
        self.manifest = self.spike_root / "fixtures" / "manifest.json"

    def test_fixture_is_bounded_and_digest_locked(self) -> None:
        fixture = load_fixture(self.manifest)
        self.assertEqual(len(fixture.records), 3)
        self.assertEqual(sum(record.status == "tombstoned" for record in fixture.records), 1)

    def test_tampered_fixture_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            fixture = root / "fixture.json"
            fixture.write_text('{"schema_version":1,"records":[]}\n', encoding="utf-8")
            manifest = root / "manifest.json"
            manifest.write_text(
                json.dumps(
                    {
                        "fixture": fixture.name,
                        "fixture_schema_version": 1,
                        "max_bytes": 100,
                        "max_records": 1,
                        "sha256": "0" * 64,
                    }
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(AdmissionError, "fixture_digest_mismatch"):
                load_fixture(manifest)

    def test_duplicate_canonical_id_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            original = json.loads((self.spike_root / "fixtures" / "canonical-v1.json").read_text())
            original["records"].append(dict(original["records"][0]))
            raw = (json.dumps(original, sort_keys=True) + "\n").encode()
            fixture = root / "fixture.json"
            fixture.write_bytes(raw)
            manifest = root / "manifest.json"
            manifest.write_text(
                json.dumps(
                    {
                        "fixture": fixture.name,
                        "fixture_schema_version": 1,
                        "max_bytes": 8192,
                        "max_records": 8,
                        "sha256": hashlib.sha256(raw).hexdigest(),
                    }
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(AdmissionError, "fixture_duplicate_id"):
                load_fixture(manifest)

    def test_tree_digest_changes_with_bytes_and_rejects_symlink(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "one").write_text("one", encoding="utf-8")
            before = tree_digest(root)
            (root / "one").write_text("two", encoding="utf-8")
            self.assertNotEqual(before, tree_digest(root))
            (root / "link").symlink_to(root / "one")
            with self.assertRaisesRegex(AdmissionError, "canonical_tree_contains_symlink"):
                tree_digest(root)

    def test_network_guard_denies_internet_and_restores_socket(self) -> None:
        original = socket.socket
        with NetworkGuard() as guard:
            internet = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            with self.assertRaisesRegex(AdmissionError, "s10_network_denied"):
                internet.connect(("192.0.2.1", 80))
            internet.close()
            datagram = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            with self.assertRaisesRegex(AdmissionError, "s10_network_denied"):
                datagram.sendto(b"probe", ("192.0.2.1", 9))
            if hasattr(datagram, "sendmsg"):
                with self.assertRaisesRegex(AdmissionError, "s10_network_denied"):
                    datagram.sendmsg([b"probe"], [], 0, ("192.0.2.1", 9))
            datagram.close()
            with self.assertRaisesRegex(AdmissionError, "s10_network_denied"):
                socket.getaddrinfo("example.invalid", 443)
            loopback = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.assertNotIsInstance(loopback.connect_ex(("127.0.0.1", 9)), AdmissionError)
            loopback.close()
            local = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            local.close()
        self.assertIs(socket.socket, original)
        self.assertGreaterEqual(guard.attempts, 4)

    def test_marker_inventory_rejects_symlink_escape(self) -> None:
        fixture = load_fixture(self.manifest)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "provider"
            root.mkdir()
            outside = Path(temporary) / "outside"
            outside.write_text(fixture.markers[0], encoding="utf-8")
            (root / "escape").symlink_to(outside)
            with self.assertRaisesRegex(AdmissionError, "path_outside_disposable_root"):
                marker_inventory(root, fixture.markers)

    def test_fixture_driver_admission_passes_without_marker_leak(self) -> None:
        fixture = load_fixture(self.manifest)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            result = run_admission(
                manifest_path=self.manifest,
                canonical_root=self.manifest.parent,
                provider_root=root / "provider",
                driver=FixtureDriver(root / "provider"),
            )
        encoded = json.dumps(result, sort_keys=True)
        self.assertEqual(result["verdict"], "FIXTURE_PASS")
        self.assertEqual(result["checks"]["network_attempts"], 0)
        self.assertGreater(result["checks"]["markers_found_before_reset"], 0)
        self.assertTrue(result["checks"]["restart_projection_matches"])
        self.assertTrue(result["checks"]["rebuild_projection_matches"])
        self.assertEqual(
            result["checks"]["lifecycle_event_counts"],
            {"ADD": 3, "DELETE": 1, "UPDATE": 1},
        )
        self.assertEqual(result["checks"]["files_after_reset"], 0)
        self.assertEqual(result["retention"]["required_delete_strategy"], "record_delete")
        self.assertFalse(result["export"]["lossless"])
        for marker in fixture.markers:
            self.assertNotIn(marker, encoded)

    def test_projection_content_corruption_is_rejected(self) -> None:
        class CorruptDriver(FixtureDriver):
            def enumerate_public(self):  # type: ignore[no-untyped-def]
                rows = super().enumerate_public()
                rows[0]["memory"] = "corrupt"
                return rows

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with self.assertRaisesRegex(AdmissionError, "projection_mismatch"):
                run_admission(
                    manifest_path=self.manifest,
                    canonical_root=self.manifest.parent,
                    provider_root=root / "provider",
                    driver=CorruptDriver(root / "provider"),
                )

    def test_telemetry_environment_is_restored(self) -> None:
        os.environ["MEM0_TELEMETRY"] = "original"
        os.environ.pop("MEM0_TELEMETRY_ENABLED", None)
        try:
            with tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                run_admission(
                    manifest_path=self.manifest,
                    canonical_root=self.manifest.parent,
                    provider_root=root / "provider",
                    driver=FixtureDriver(root / "provider"),
                )
            self.assertEqual(os.environ["MEM0_TELEMETRY"], "original")
            self.assertNotIn("MEM0_TELEMETRY_ENABLED", os.environ)
        finally:
            os.environ.pop("MEM0_TELEMETRY", None)

    def test_unknown_provider_copy_is_fail_closed(self) -> None:
        class UnknownCopyDriver(FixtureDriver):
            def project(self, record):  # type: ignore[no-untyped-def]
                super().project(record)
                (self.root / "unknown.bin").write_bytes(b"derived")

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with self.assertRaisesRegex(AdmissionError, "provider_unknown_copy"):
                run_admission(
                    manifest_path=self.manifest,
                    canonical_root=self.manifest.parent,
                    provider_root=root / "provider",
                    driver=UnknownCopyDriver(root / "provider"),
                )

    def test_declared_raw_interaction_copy_is_fail_closed(self) -> None:
        class RawCopyDriver(FixtureDriver):
            def diagnostics(self) -> DriverDiagnostics:
                base = super().diagnostics()
                return DriverDiagnostics(
                    file_classes=base.file_classes,
                    raw_interaction_files=("history.jsonl",),
                    event_counts=base.event_counts,
                )

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with self.assertRaisesRegex(AdmissionError, "raw_interaction_persisted"):
                run_admission(
                    manifest_path=self.manifest,
                    canonical_root=self.manifest.parent,
                    provider_root=root / "provider",
                    driver=RawCopyDriver(root / "provider"),
                )

    def test_injected_project_failure_is_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with self.assertRaisesRegex(AdmissionError, "fixture_injected_project_failure"):
                run_admission(
                    manifest_path=self.manifest,
                    canonical_root=self.manifest.parent,
                    provider_root=root / "provider",
                    driver=FixtureDriver(root / "provider", fail_operation="project"),
                )

    def test_injected_reset_failure_is_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with self.assertRaisesRegex(AdmissionError, "fixture_injected_reset_failure"):
                run_admission(
                    manifest_path=self.manifest,
                    canonical_root=self.manifest.parent,
                    provider_root=root / "provider",
                    driver=FixtureDriver(root / "provider", fail_operation="reset"),
                )


if __name__ == "__main__":
    unittest.main()
