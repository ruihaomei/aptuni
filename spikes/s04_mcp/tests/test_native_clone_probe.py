"""Adversarial tests for the macOS native full-clone mapping bridge."""

from __future__ import annotations

import json
import os
import platform
import shutil
import socket
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "native_clone_probe.c"


@unittest.skipUnless(platform.system() == "Darwin", "macOS native probe")
class NativeCloneProbeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.build = tempfile.TemporaryDirectory()
        cls.binary = Path(cls.build.name) / "native-clone-probe"
        subprocess.run(
            [
                "/usr/bin/clang",
                "-std=c11",
                "-Wall",
                "-Wextra",
                "-Werror",
                str(SOURCE),
                "-o",
                str(cls.binary),
            ],
            check=True,
            capture_output=True,
            text=True,
        )

    @classmethod
    def tearDownClass(cls) -> None:
        cls.build.cleanup()

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.source = self.root / "source"
        self.source.write_bytes(b"synthetic-clone-probe\n" * 4096)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def invoke(self, *arguments: object, check: bool = True) -> tuple[int, dict[str, object]]:
        completed = subprocess.run(
            [str(self.binary), *(str(argument) for argument in arguments)],
            check=False,
            capture_output=True,
            text=True,
        )
        if check:
            self.assertEqual(0, completed.returncode, completed.stderr)
        return completed.returncode, json.loads(completed.stdout)

    def clone(self, destination: Path) -> None:
        _, result = self.invoke("clone-for-test", self.source, destination)
        self.assertEqual("clone_created", result["reason_code"])

    def require_mapping(self, result: dict[str, object]) -> None:
        if result["status"] == "unverified" and result["reason_code"] in {
            "volume_clone_mapping_capability_invalid",
            "volume_clone_mapping_unsupported",
        }:
            self.skipTest(str(result["reason_code"]))

    def test_distinct_full_clone_has_positive_three_part_mapping(self) -> None:
        clone = self.root / "clone"
        self.clone(clone)

        _, result = self.invoke("compare", self.source, clone)

        self.require_mapping(result)
        self.assertEqual("ok", result["status"], result)
        self.assertFalse(result["same_object"])
        self.assertTrue(result["same_clone_id"])
        self.assertTrue(result["both_share_all_blocks"])
        self.assertTrue(result["refcounts_confirm"])
        self.assertTrue(result["full_clone_family"])
        self.assertEqual("full_clone_mapping_positive", result["reason_code"])

    def test_native_predicate_self_test_covers_every_required_condition(self) -> None:
        _, result = self.invoke("self-test")
        self.assertEqual(
            {"status": "ok", "reason_code": "self_test_passed"}, result
        )

    def test_real_host_clone_is_positive_or_fails_closed_on_capability(self) -> None:
        clone = self.root / "clone"
        self.clone(clone)

        _, result = self.invoke("compare", self.source, clone)

        if result["status"] == "ok":
            self.assertTrue(result["full_clone_family"])
            self.assertEqual("full_clone_mapping_positive", result["reason_code"])
        else:
            self.assertEqual("unverified", result["status"])
            self.assertIn(
                result["reason_code"],
                {
                    "native_attributes_incomplete",
                    "volume_clone_mapping_capability_invalid",
                    "volume_clone_mapping_unsupported",
                },
            )

    def test_independent_equal_content_copy_is_not_a_clone_mapping(self) -> None:
        independent = self.root / "independent"
        shutil.copyfile(self.source, independent)

        _, result = self.invoke("compare", self.source, independent)

        self.require_mapping(result)
        self.assertEqual("ok", result["status"], result)
        self.assertFalse(result["full_clone_family"])
        self.assertEqual("full_clone_mapping_absent", result["reason_code"])

    def test_rename_preserves_positive_mapping(self) -> None:
        clone = self.root / "clone"
        renamed = self.root / "renamed"
        self.clone(clone)
        clone.rename(renamed)

        _, result = self.invoke("compare", self.source, renamed)

        self.require_mapping(result)
        self.assertTrue(result["full_clone_family"])

    def test_partial_write_removes_full_clone_mapping(self) -> None:
        clone = self.root / "clone"
        self.clone(clone)
        with clone.open("r+b") as stream:
            stream.seek(0)
            stream.write(b"changed")
            stream.flush()

        _, result = self.invoke("compare", self.source, clone)

        self.require_mapping(result)
        self.assertFalse(result["full_clone_family"])
        self.assertEqual("full_clone_mapping_absent", result["reason_code"])

    def test_hardlink_is_same_object_not_clone_family(self) -> None:
        hardlink = self.root / "hardlink"
        os.link(self.source, hardlink)

        _, result = self.invoke("compare", self.source, hardlink)

        self.require_mapping(result)
        self.assertTrue(result["same_object"])
        self.assertFalse(result["full_clone_family"])
        self.assertEqual("same_object", result["reason_code"])

    def test_symlink_is_rejected_without_following(self) -> None:
        symlink = self.root / "symlink"
        symlink.symlink_to(self.source)

        returncode, result = self.invoke(
            "compare", self.source, symlink, check=False
        )

        self.assertEqual(2, returncode)
        self.assertEqual("unverified", result["status"])
        self.assertEqual("file_open_failed", result["reason_code"])

    def test_missing_or_unreadable_input_is_unverified_and_content_free(self) -> None:
        private_marker = self.root / "PRIVATE-MARKER-do-not-emit"

        returncode, result = self.invoke(
            "compare", self.source, private_marker, check=False
        )

        self.assertEqual(2, returncode)
        self.assertEqual(
            {"status": "unverified", "reason_code": "file_open_failed"}, result
        )
        self.assertNotIn(private_marker.name, json.dumps(result))

    def test_nonregular_input_cannot_create_positive_evidence(self) -> None:
        returncode, result = self.invoke(
            "compare", self.source, Path("/dev/null"), check=False
        )

        self.assertEqual(0, returncode)
        self.assertEqual(
            {"status": "unverified", "reason_code": "native_attributes_incomplete"},
            result,
        )

    def test_fifo_is_opened_nonblocking_and_rejected(self) -> None:
        fifo = self.root / "fifo"
        os.mkfifo(fifo)

        returncode, result = self.invoke(
            "compare", self.source, fifo, check=False
        )

        self.assertEqual(0, returncode)
        self.assertEqual(
            {"status": "unverified", "reason_code": "native_attributes_incomplete"},
            result,
        )

    def test_unix_socket_input_is_rejected_without_identifier_leak(self) -> None:
        socket_path = self.root / "private-socket-name"
        listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        listener.bind(str(socket_path))
        try:
            returncode, result = self.invoke(
                "compare", self.source, socket_path, check=False
            )
        finally:
            listener.close()

        self.assertEqual(2, returncode)
        self.assertEqual(
            {"status": "unverified", "reason_code": "file_open_failed"}, result
        )
        self.assertNotIn(socket_path.name, json.dumps(result))


if __name__ == "__main__":
    unittest.main()
