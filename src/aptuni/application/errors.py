"""Public error model: stable machine codes plus a human message (never raw tracebacks)."""

from __future__ import annotations


class AptuniError(Exception):
    """An expected, user-facing failure with a stable ``code``."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
