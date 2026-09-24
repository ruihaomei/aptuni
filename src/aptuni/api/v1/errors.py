"""Stable public API error envelope."""

from __future__ import annotations

from aptuni.application.errors import AptuniError


class AptuniAPIError(AptuniError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(code, message)
