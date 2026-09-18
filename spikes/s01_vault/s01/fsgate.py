"""Fail-closed filesystem admission for the Gate 0 baseline (macOS 26.2, local APFS).

Python's ``os.statvfs`` does not expose the filesystem type, so this calls ``statfs(2)`` via
ctypes using the 64-bit-inode ``struct statfs`` layout from ``<sys/mount.h>``.
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
ADMITTED_FS = ("apfs",)


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


def statfs_info(path: Path) -> FsInfo:
    """Return filesystem type and local flag for ``path`` (or its nearest existing ancestor)."""
    if sys.platform != "darwin":
        raise UnsupportedFilesystemError(f"platform {sys.platform} is not admitted at Gate 0")
    libc = ctypes.CDLL(ctypes.util.find_library("c"), use_errno=True)
    buf = _StatFs()
    target = str(_existing_ancestor(path)).encode("utf-8")
    if libc.statfs(target, ctypes.byref(buf)) != 0:
        raise UnsupportedFilesystemError(f"statfs failed with errno {ctypes.get_errno()}")
    return FsInfo(buf.f_fstypename.decode("ascii"), bool(buf.f_flags & MNT_LOCAL))


def check_vault_filesystem(path: Path, *, statfs: Callable[[Path], FsInfo] = statfs_info,
                           home: Path | None = None) -> FsInfo:
    """Admit only local APFS outside known sync roots; everything else fails closed."""
    home_dir = home or Path.home()
    resolved = path if home is not None else path.resolve()
    for root in SYNC_ROOTS:
        if resolved == home_dir / root or (home_dir / root) in resolved.parents:
            raise UnsupportedFilesystemError(f"synchronized folder is not admitted: {root}")
    info = statfs(path)
    if info.fstypename not in ADMITTED_FS:
        raise UnsupportedFilesystemError(f"filesystem {info.fstypename!r} is not admitted")
    if not info.is_local:
        raise UnsupportedFilesystemError("non-local filesystem is not admitted")
    return info
