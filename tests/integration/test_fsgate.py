"""Filesystem fail-closed gate with injected negative probes."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from aptuni.vault.fsgate import FsInfo, UnsupportedFilesystemError, check_vault_filesystem, statfs_info


class FsGateTests(unittest.TestCase):
    def test_real_baseline_volume_is_admitted(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            info = statfs_info(Path(raw))
            self.assertEqual("apfs", info.fstypename)
            self.assertTrue(info.is_local)
            check_vault_filesystem(Path(raw))

    def test_injected_non_apfs_is_refused(self) -> None:
        with self.assertRaises(UnsupportedFilesystemError):
            check_vault_filesystem(Path("/tmp/x"), statfs=lambda _p: FsInfo("msdos", True))

    def test_injected_non_local_is_refused(self) -> None:
        with self.assertRaises(UnsupportedFilesystemError):
            check_vault_filesystem(Path("/tmp/x"), statfs=lambda _p: FsInfo("apfs", False))

    def test_sync_roots_are_refused(self) -> None:
        home = Path("/Users/example")
        for root in ("Library/Mobile Documents/com~apple~CloudDocs/v",
                     "Library/CloudStorage/GoogleDrive-a/v", "Dropbox/v"):
            with self.subTest(root=root), self.assertRaises(UnsupportedFilesystemError):
                check_vault_filesystem(home / root, statfs=lambda _p: FsInfo("apfs", True),
                                       home=home)


if __name__ == "__main__":
    unittest.main()
