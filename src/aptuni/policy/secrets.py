"""High-precision detection of credentials in text that could enter or leave Context (ADR-0031).

The boundary is credentials and secrets — passwords, API keys, access/refresh tokens, private keys
and credentials embedded in URLs — not personal information in general. Every rule prefers
missing an unusual secret over flagging an ordinary note: a note that *discusses* passwords
("use a password manager", "密码学") is not a credential, and a labelled field only counts when
its value itself looks like a secret rather than a word, a placeholder or prose.
"""

from __future__ import annotations

import re

CredentialKind = str

_PRIVATE_KEY = re.compile(r"-----BEGIN (?:[A-Z0-9]+ )*PRIVATE KEY(?: BLOCK)?-----")
_PROVIDER_TOKEN = re.compile(
    r"(?<![A-Za-z0-9_-])(?:"
    r"sk-ant-[A-Za-z0-9_-]{20,}"
    r"|sk-(?:proj-|svcacct-)?[A-Za-z0-9_-]{24,}"
    r"|gh[pousr]_[A-Za-z0-9]{36,}"
    r"|github_pat_[A-Za-z0-9_]{22,}"
    r"|(?:AKIA|ASIA)[0-9A-Z]{16}"
    r"|AIza[0-9A-Za-z_-]{35}"
    r"|xox[abprs]-[A-Za-z0-9-]{10,}"
    r"|hf_[A-Za-z0-9]{30,}"
    r"|glpat-[A-Za-z0-9_-]{20,}"
    r"|(?:sk|rk)_live_[A-Za-z0-9]{16,}"
    r"|npm_[A-Za-z0-9]{36}"
    r")(?![A-Za-z0-9_-])"
    r"|\bBearer\s+[A-Za-z0-9._~+/-]{24,}=*",
)
_JWT = re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}")
_URL_CREDENTIALS = re.compile(r"\b[a-z][a-z0-9+.-]*://([^\s:/@]+):([^\s@/]{3,})@[^\s/]+", re.IGNORECASE)
_FIELD = re.compile(
    r"(?i)(?:登录密码|支付密码|密码|口令|password|passwd|passcode|pwd|api[ _-]?key|secret[ _-]?key"
    r"|client[ _-]?secret|access[ _-]?token|refresh[ _-]?token|auth[ _-]?token)"
    r"\s*[:：=]\s*(\S+)",
)
_PLACEHOLDER_WORDS = ("your", "example", "placeholder", "changeme", "password", "passwd", "secret", "redacted",
                      "xxxx", "dummy", "sample", "test123", "none", "null", "todo")
_SYMBOLS = set("!@#$%^&*_-+=?.~/")
_CJK = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff]")


def _looks_like_secret_value(raw: str) -> bool:
    """A labelled value counts only if it is a single, non-placeholder, secret-shaped token."""
    value = raw.strip("；;，,。.、)）]】\"'“”‘’")
    if not 6 <= len(value) <= 200 or _CJK.search(value):
        return False
    lowered = value.lower()
    if len(set(value)) <= 2 or value[0] in "<{[(" or any(word in lowered for word in _PLACEHOLDER_WORDS):
        return False
    has_digit = any(char.isdigit() for char in value)
    has_symbol = any(char in _SYMBOLS for char in value)
    mixed_case = any(char.islower() for char in value) and any(char.isupper() for char in value)
    return has_digit or has_symbol or mixed_case or len(value) >= 16


def _url_has_real_password(match: re.Match[str]) -> bool:
    password = match.group(2).lower()
    return not any(word in password for word in _PLACEHOLDER_WORDS) and password not in {"pass", "pwd", "***"}


def credential_kinds(text: str) -> tuple[CredentialKind, ...]:
    """Return the kinds of obvious credentials found in ``text`` (empty when none)."""
    if not text:
        return ()
    kinds: list[CredentialKind] = []
    if _PRIVATE_KEY.search(text):
        kinds.append("private_key")
    if _PROVIDER_TOKEN.search(text):
        kinds.append("provider_token")
    if _JWT.search(text):
        kinds.append("jwt")
    if any(_url_has_real_password(match) for match in _URL_CREDENTIALS.finditer(text)):
        kinds.append("url_credentials")
    if any(_looks_like_secret_value(match.group(1)) for match in _FIELD.finditer(text)):
        kinds.append("credential_field")
    return tuple(kinds)


def contains_credential(text: str | None) -> bool:
    return bool(text) and bool(credential_kinds(text or ""))
