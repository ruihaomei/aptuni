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
_URL_CREDENTIALS = re.compile(r"\b[a-z][a-z0-9+.-]{0,31}://([^\s:/@]+):([^\s@/]{3,})@[^\s/]+", re.IGNORECASE)
# A label, optionally env-style (DB_PASSWORD) or decorated by Markdown/code/quotes (**密码**, `api_key`,
# "password", **Password:**), then ":" "：" "=" or a table "|", then an optionally quoted value. A bare
# `token`/`secret` label is common in ML and code notes, so it needs a longer value (_BARE_MIN).
_LABEL = (r"(?:登录密码|支付密码|密码|口令|(?<![A-Za-z0-9_])(?:[A-Za-z0-9]{1,32}_){0,4}"
          r"(?:password|passwd|passcode|pwd|api[ _-]?key|secret[ _-]?(?:access[ _-]?)?key|client[ _-]?secret"
          r"|access[ _-]?token|refresh[ _-]?token|auth[ _-]?token|(?P<bare>token|secret)))")
# The env-style prefix is bounded and anchored at a word start, so matching stays linear (Review 93 N6).
_FIELD = re.compile(_LABEL + r"[*_`\"'\]]{0,3}\s*[:：=|][*_`]{0,3}\s*[\"'`]?(?P<value>\S+)", re.IGNORECASE)
_LABEL_CELL = re.compile(r"[*_`\"'\s]*" + _LABEL + r"[*_`\"'\s:：]*", re.IGNORECASE)
_BARE_MIN = 12
_TABLE_COLUMNS = 16
_PLACEHOLDER_WORDS = ("your", "example", "placeholder", "changeme", "password", "passwd", "secret", "redacted",
                      "xxxx", "dummy", "sample", "test123", "none", "null", "todo")
_SYMBOLS = set("!@#$%^&*+=?~")
_CODE_PREFIXES = ("os.", "self.", "$", "%", "{{", "/", "~", "./", "../")
_CJK = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff]")
_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")
_COUNTED_WORD = re.compile(r"\d+-[a-z]+")  # "6-digit", "8-character"
_VERSION = re.compile(r"v?\d+(?:\.\d+)+")
_ATTRIBUTE = re.compile(r"[A-Za-z_]\w*\.[A-Za-z_]\w*")  # tokenizer.eos_token


def _looks_like_secret_value(raw: str) -> bool:
    """A labelled value counts only if it is a single, non-placeholder, secret-shaped token.

    Code (calls, indexing, environment lookups, template variables), paths, dates and counted words
    are not secrets; title-case words are not "mixed case".
    """
    value = raw.strip("；;，,。.、)）]】}\"'“”‘’`")
    if not 6 <= len(value) <= 200 or _CJK.search(value):
        return False
    lowered = value.lower()
    if len(set(value)) <= 2 or value[0] in "<{[(" or any(word in lowered for word in _PLACEHOLDER_WORDS):
        return False
    if any(char in value for char in "()[]{}") or value.startswith(_CODE_PREFIXES) \
            or "getenv" in lowered or "environ" in lowered:
        return False
    if _DATE.match(value) or _COUNTED_WORD.fullmatch(lowered) or _VERSION.fullmatch(lowered) \
            or _ATTRIBUTE.fullmatch(value):
        return False
    has_digit = any(char.isdigit() for char in value)
    has_symbol = any(char in _SYMBOLS for char in value)
    mixed_case = any(char.isupper() for char in value[1:]) and any(char.islower() for char in value)
    return has_digit or has_symbol or mixed_case or len(value) >= 16


def _url_has_real_password(match: re.Match[str]) -> bool:
    password = match.group(2).lower()
    return not any(word in password for word in _PLACEHOLDER_WORDS) and password not in {"pass", "pwd", "***"}


def _cells(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def _field_has_secret(match: re.Match[str]) -> bool:
    value = match.group("value")
    return _looks_like_secret_value(value) and (match.group("bare") is None or len(value.strip("\"'`")) >= _BARE_MIN)


def _table_has_secret(text: str) -> bool:
    """A Markdown table whose header names a credential column holding a secret-shaped value.

    Sources flatten whitespace before the guard runs, so rows are split on newlines and on the
    "| |" boundary between two rows. At most ``_TABLE_COLUMNS`` columns are checked per row (linear)."""
    columns: list[tuple[int, bool]] = []
    for line in re.split(r"\n|(?<=\|)[ \t]+(?=\|)", text):
        start = line.find("|")  # flattened text may carry a heading or file name before the table
        if start < 0:
            columns = []
            continue
        cells = _cells(line[start:])
        if all(set(cell) <= set("-: ") for cell in cells):
            continue  # the |---|---| separator row
        for index, bare in columns:
            value = cells[index] if index < len(cells) else ""
            if _looks_like_secret_value(value) and (not bare or len(value) >= _BARE_MIN):
                return True
        if not columns:
            for index, cell in enumerate(cells[:64]):
                label = _LABEL_CELL.fullmatch(cell)
                if label:
                    columns.append((index, label.group("bare") is not None))
            columns = columns[:_TABLE_COLUMNS]
    return False


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
    if any(_field_has_secret(match) for match in _FIELD.finditer(text)) \
            or ("|" in text and _table_has_secret(text)):
        kinds.append("credential_field")
    return tuple(kinds)


def contains_credential(text: str | None) -> bool:
    return bool(text) and bool(credential_kinds(text or ""))
