"""Fail-closed Vault filesystem admission for explicitly proven local filesystems.

Darwin uses ``statfs(2)``. Linux resolves the nearest mount from ``/proc/self/mountinfo`` because
Python's ``os.statvfs`` does not expose the filesystem type. Unknown platforms and filesystems are
refused rather than guessed.
"""

from __future__ import annotations

import ctypes
import ctypes.util
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

MNT_LOCAL = 0x00001000
MFSTYPENAMELEN = 16
MAXPATHLEN = 1024
SYNC_ROOTS = ("Library/Mobile Documents", "Library/CloudStorage", "Dropbox")
ADMITTED_FS = {"darwin": ("apfs",), "linux": ("ext4",)}
REMOTE_LINUX_FS = {"9p", "afs", "ceph", "cifs", "nfs", "nfs4", "smb3", "sshfs"}


class UnsupportedFilesystemError(RuntimeError):
    """The Vault location is not an admitted local filesystem; refuse instead of guessing."""


@dataclass(frozen=True)
class FsInfo:
    fstypename: str
    is_local: bool


class _StatFs(ctypes.Structure):
    _fields_ = [
        ("f_bsize", ctypes.c_uint32), ("f_iosize", ctypes.c_int32),
        ("f_blocks", ctypes.c_uint64), ("f_bfree", ctypes.c_uint64), ("f_bavail", ctypes.c_uint64),
        ("f_files", ctypes.c_uint64), ("f_ffree", ctypes.c_uint64),
        ("f_fsid", ctypes.c_int32 * 2), ("f_owner", ctypes.c_uint32), ("f_type", ctypes.c_uint32),
        ("f_flags", ctypes.c_uint32), ("f_fssubtype", ctypes.c_uint32),
        ("f_fstypename", ctypes.c_char * MFSTYPENAMELEN),
        ("f_mntonname", ctypes.c_char * MAXPATHLEN), ("f_mntfromname", ctypes.c_char * MAXPATHLEN),
        ("f_flags_ext", ctypes.c_uint32), ("f_reserved", ctypes.c_uint32 * 7),
    ]


def _existing_ancestor(path: Path) -> Path:
    candidate = path.resolve()
    while not candidate.exists():
        candidate = candidate.parent
    return candidate


def _unescape_mount_field(value: str) -> str:
    for escaped, plain in (("\\040", " "), ("\\011", "\t"), ("\\012", "\n"),
                           ("\\134", "\\")):
        value = value.replace(escaped, plain)
    return value


def _linux_mount_info(path: Path, mountinfo: str) -> FsInfo:
    candidate = _existing_ancestor(path)
    matches: list[tuple[Path, str]] = []
    for line in mountinfo.splitlines():
        fields = line.split()
        try:
            separator = fields.index("-")
            mountpoint = Path(_unescape_mount_field(fields[4]))
            filesystem = fields[separator + 1]
        except (IndexError, ValueError):
            continue
        if candidate == mountpoint or mountpoint in candidate.parents:
            matches.append((mountpoint, filesystem))
    if not matches:
        raise UnsupportedFilesystemError("path has no entry in /proc/self/mountinfo")
    _mountpoint, filesystem = max(matches, key=lambda item: len(item[0].parts))
    return FsInfo(filesystem, filesystem not in REMOTE_LINUX_FS)


def statfs_info(path: Path) -> FsInfo:
    """Return filesystem type and local flag for ``path`` (or its nearest existing ancestor)."""
    if sys.platform == "linux":
        try:
            mountinfo = Path("/proc/self/mountinfo").read_text(encoding="utf-8")
        except OSError as error:
            raise UnsupportedFilesystemError("cannot read /proc/self/mountinfo") from error
        return _linux_mount_info(path, mountinfo)
    if sys.platform != "darwin":
        raise UnsupportedFilesystemError(f"platform {sys.platform} is not admitted")
    libc = ctypes.CDLL(ctypes.util.find_library("c"), use_errno=True)
    buf = _StatFs()
    target = str(_existing_ancestor(path)).encode("utf-8")
    if libc.statfs(target, ctypes.byref(buf)) != 0:
        raise UnsupportedFilesystemError(f"statfs failed with errno {ctypes.get_errno()}")
    return FsInfo(buf.f_fstypename.decode("ascii"), bool(buf.f_flags & MNT_LOCAL))


def check_vault_filesystem(path: Path, *, statfs: Callable[[Path], FsInfo] = statfs_info,
                           home: Path | None = None) -> FsInfo:
    """Admit only the platform's proven local filesystem outside known sync roots."""
    home_dir = home or Path.home()
    resolved = path if home is not None else path.resolve()
    for root in SYNC_ROOTS:
        if resolved == home_dir / root or (home_dir / root) in resolved.parents:
            raise UnsupportedFilesystemError(f"synchronized folder is not admitted: {root}")
    info = statfs(path)
    admitted = ADMITTED_FS.get(sys.platform, ())
    if info.fstypename not in admitted:
        raise UnsupportedFilesystemError(f"filesystem {info.fstypename!r} is not admitted")
    if not info.is_local:
        raise UnsupportedFilesystemError("non-local filesystem is not admitted")
    return info
