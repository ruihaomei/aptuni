"""Small cross-process locks shared by Vault and application operations."""

from __future__ import annotations

import fcntl
import os
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path


@contextmanager
def source_operations_lock(state_dir: Path) -> Iterator[None]:
    """Serialize source sync with purge/restore state invalidation.

    Lock order is ``privacy -> source_operations -> per-source -> Vault writer`` and every caller
    must keep it. Callers also open the Vault *before* taking this lock, so ``Vault.open()`` ->
    ``recover()`` cannot re-enter it on a second descriptor and deadlock.
    """
    state_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    path = state_dir / "source-operations.lock"
    with open(path, "a+b") as handle:
        os.chmod(path, 0o600)
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
