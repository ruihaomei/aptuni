"""Filesystem fail-closed gate with injected negative probes."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

from aptuni.vault.fsgate import FsInfo, UnsupportedFilesystemError, check_vault_filesystem, statfs_info


class FsGateTests(unittest.TestCase):
    def test_real_baseline_volume_is_admitted(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            info = statfs_info(Path(raw))
            self.assertEqual("apfs" if sys.platform == "darwin" else "ext4", info.fstypename)
            self.assertTrue(info.is_local)
            check_vault_filesystem(Path(raw))

    def test_injected_unadmitted_filesystem_is_refused(self) -> None:
        with self.assertRaises(UnsupportedFilesystemError):
            check_vault_filesystem(Path("/tmp/x"), statfs=lambda _p: FsInfo("msdos", True))

    def test_injected_non_local_is_refused(self) -> None:
        with self.assertRaises(UnsupportedFilesystemError):
            check_vault_filesystem(Path("/tmp/x"), statfs=lambda _p: FsInfo("apfs", False))

    def test_sync_roots_are_refused(self) -> None:
        home = Path("/Users/example")
        admitted = "apfs" if sys.platform == "darwin" else "ext4"
        for root in ("Library/Mobile Documents/com~apple~CloudDocs/v",
                     "Library/CloudStorage/GoogleDrive-a/v", "Dropbox/v"):
            with self.subTest(root=root), self.assertRaises(UnsupportedFilesystemError):
                check_vault_filesystem(home / root, statfs=lambda _p: FsInfo(admitted, True),
                                       home=home)

    def test_linux_mountinfo_prefers_deepest_mount_and_decodes_spaces(self) -> None:
        from aptuni.vault.fsgate import _linux_mount_info

        with tempfile.TemporaryDirectory(prefix="aptuni mount ") as raw:
            path = Path(raw)
            escaped = str(path.resolve()).replace(" ", "\\040")
            mountinfo = f"1 0 8:1 / / rw - ext4 /dev/root rw\n2 1 8:2 / {escaped} rw - nfs host:/x rw\n"
            self.assertEqual(FsInfo("nfs", False), _linux_mount_info(path, mountinfo))


if __name__ == "__main__":
    unittest.main()
