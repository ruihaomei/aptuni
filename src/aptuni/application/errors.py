"""Public error model: stable machine codes plus a human message (never raw tracebacks)."""

from __future__ import annotations

from collections.abc import Iterable


class AptuniError(Exception):
    """An expected, user-facing failure with a stable ``code``."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def module_denied(requested: Iterable[str], granted: Iterable[str]) -> AptuniError:
    """Name the denied and granted module names (never content) so an Agent can retry correctly."""
    denied = sorted(set(requested) - set(granted))
    allowed = ", ".join(sorted(granted)) or "none"
    detail = f"not granted: {', '.join(denied)}" if denied else "no module was requested"
    return AptuniError(
        "mcp_module_denied",
        f"The configured MCP principal lacks module access ({detail}; granted: {allowed}). "
        "Retry with granted modules only.",
    )
