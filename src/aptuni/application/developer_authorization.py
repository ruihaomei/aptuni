"""Cross-process lock for public developer authorization use and mutation."""

from __future__ import annotations

import fcntl
import os
from collections.abc import Iterator
from contextlib import contextmanager, suppress
from pathlib import Path


@contextmanager
def developer_authorization_lock(state_dir: Path) -> Iterator[None]:
    """Serialize SDK calls, grant changes and privacy cleanup without following symlinks."""
    if state_dir.is_symlink():
        raise OSError("developer_authorization_state_unsafe")
    state_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    state_fd = os.open(state_dir, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        with suppress(FileExistsError):
            os.mkdir("developer", mode=0o700, dir_fd=state_fd)
        developer_fd = os.open(
            "developer",
            os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
            dir_fd=state_fd,
        )
        try:
            try:
                lock_fd = os.open(
                    "authorization.lock",
                    os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                    0o600,
                    dir_fd=developer_fd,
                )
            except FileExistsError:
                lock_fd = os.open(
                    "authorization.lock",
                    os.O_RDWR | os.O_NOFOLLOW,
                    dir_fd=developer_fd,
                )
            try:
                fcntl.flock(lock_fd, fcntl.LOCK_EX)
                yield
            finally:
                fcntl.flock(lock_fd, fcntl.LOCK_UN)
                os.close(lock_fd)
        finally:
            os.close(developer_fd)
    finally:
        os.close(state_fd)
