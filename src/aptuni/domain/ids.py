"""Record identifiers and digests."""

from __future__ import annotations

import hashlib
import os
import time

CROCKFORD = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
ID_PREFIXES = ("fct", "evd", "obs", "cnd", "mem", "rev", "src", "pol", "rcp", "led")
ID_PATTERN = r"^(fct|evd|obs|cnd|mem|rev|src|pol|rcp|led)_[0-9A-HJKMNP-TV-Z]{26}$"
DIGEST_PATTERN = r"^sha256:[0-9a-f]{64}$"


def new_id(prefix: str) -> str:
    """Return a time-sortable Crockford-base32 id (ULID-like, 26 characters)."""
    if prefix not in ID_PREFIXES:
        raise ValueError(f"unknown id prefix: {prefix!r}")
    value = (int(time.time() * 1000) << 80) | int.from_bytes(os.urandom(10), "big")
    chars = []
    for _ in range(26):
        chars.append(CROCKFORD[value & 31])
        value >>= 5
    return f"{prefix}_{''.join(reversed(chars))}"


def deterministic_id(prefix: str, seed: str) -> str:
    """Return a stable id derived from ``seed`` (idempotent imports and migrations)."""
    if prefix not in ID_PREFIXES:
        raise ValueError(f"unknown id prefix: {prefix!r}")
    value = int.from_bytes(hashlib.sha256(seed.encode("utf-8")).digest(), "big")
    return f"{prefix}_{''.join(CROCKFORD[(value >> (5 * i)) & 31] for i in range(26))}"


def sha256_text(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_bytes(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()
