"""Primitives shared by every digest-bound owner confirmation (ADR-0013).

Purge (`privacy.py`) and restore (`restore.py`) both ask the owner to approve one exact, expiring,
single-use action. They share the same four mechanics, and one implementation keeps them from
drifting apart: a private atomic write, an exclusive per-family lock, an action-id shape, and a
digest over the exact fields the owner was shown.
"""

from __future__ import annotations

import fcntl
import json
import os
import re
import secrets
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from aptuni.application.errors import AptuniError
from aptuni.domain.ids import sha256_text

ACTION_RE = re.compile(r"^act-[0-9a-f]{16}$")


def new_action_id() -> str:
    """A core-generated id the owner must quote back; never derived from user input."""
    return "act-" + secrets.token_hex(8)


def new_nonce() -> str:
    return secrets.token_hex(16)


def preview_digest(fields: dict[str, Any]) -> str:
    """Digest the exact fields the owner was shown, so a later confirmation binds to that text."""
    body = json.dumps(fields, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=_plain)
    return sha256_text(body)


def _plain(value: Any) -> Any:
    if isinstance(value, tuple):
        return list(value)
    raise TypeError(f"{type(value).__name__} is not a confirmation field type")


def validate_action_id(action_id: str, code: str, message: str) -> None:
    if not ACTION_RE.fullmatch(action_id):
        raise AptuniError(code, message)


def write_private_json(path: Path, value: object) -> None:
    """Owner-only, atomic, durable: mode 0700 parent, mode 0600 file, fsync before and after rename."""
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(path.parent, 0o700)
    body = (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=1) + "\n").encode("utf-8")
    tmp = path.with_name(f".{path.name}.{os.getpid()}.{secrets.token_hex(4)}.tmp")
    descriptor = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        remaining = memoryview(body)
        while remaining:
            written = os.write(descriptor, remaining)
            if written <= 0:
                raise OSError("confirmation_state_write_failed")
            remaining = remaining[written:]
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    os.replace(tmp, path)
    fsync_dir(path.parent)


def fsync_dir(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def unlink_durable(path: Path) -> None:
    try:
        path.unlink()
    except FileNotFoundError:
        return
    fsync_dir(path.parent)


@contextmanager
def action_lock(state_dir: Path, family: str) -> Iterator[None]:
    """Serialize one action family (``privacy``, ``backup``) across processes."""
    root = state_dir / family
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(root, 0o700)
    lock = root / f"{family}.lock"
    with open(lock, "a+b") as handle:
        os.chmod(lock, 0o600)
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
