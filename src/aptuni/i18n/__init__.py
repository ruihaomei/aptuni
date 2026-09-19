"""User-facing message catalogs (PRD §24): English and Simplified Chinese are officially maintained.

Messages live in ``messages/<locale>.toml`` as flat quoted keys. Both locales must carry identical
keys and placeholders (enforced by tests), so logic is never duplicated per language. Community
locales can be added as further files once they pass the same parity checks.
"""

from __future__ import annotations

import string
import tomllib
from functools import cache
from importlib import resources

LOCALES: tuple[str, ...] = ("en", "zh-CN")
DEFAULT_LOCALE = "en"

_ALIASES = {
    "en": "en", "english": "en", "1": "en",
    "zh": "zh-CN", "zh-cn": "zh-CN", "zh-hans": "zh-CN", "zh-sg": "zh-CN", "2": "zh-CN",
    "简体中文": "zh-CN", "中文": "zh-CN", "chinese": "zh-CN",
}

_TRADITIONAL = ("tw", "hk", "mo", "hant")  # never silently convert Traditional Chinese to Simplified

__all__ = ["DEFAULT_LOCALE", "LOCALES", "I18nError", "has_message", "message_keys", "normalize_locale", "t"]


class I18nError(ValueError):
    """Unknown locale, missing message, or missing formatting parameter."""


def normalize_locale(value: str | None, *, strict: bool = False) -> str:
    """Map user input such as ``zh_CN``, ``2`` or ``简体中文`` to a supported locale."""
    if value is None or not value.strip():
        return DEFAULT_LOCALE
    raw = value.strip().replace("_", "-").lower()
    traditional = raw.split("-")[0] == "zh" and any(tag in raw.split("-")[1:] for tag in _TRADITIONAL)
    locale = None if traditional else (_ALIASES.get(raw) or _ALIASES.get(raw.split("-")[0]))
    if locale is None:
        if strict:
            raise I18nError("unsupported_locale")
        return DEFAULT_LOCALE
    return locale


@cache
def _messages(locale: str) -> dict[str, str]:
    if locale not in LOCALES:
        raise I18nError("unsupported_locale")
    text = resources.files("aptuni.i18n").joinpath("messages", f"{locale}.toml").read_text(encoding="utf-8")
    data = tomllib.loads(text)
    if not all(isinstance(key, str) and isinstance(value, str) for key, value in data.items()):
        raise I18nError("catalog_invalid")
    return dict(data)


def message_keys(locale: str) -> frozenset[str]:
    return frozenset(_messages(locale))


def has_message(key: str, locale: str) -> bool:
    return key in _messages(locale)


def t(key: str, locale: str = DEFAULT_LOCALE, *, raw: bool = False, **params: object) -> str:
    """Translate ``key``; every placeholder must be supplied (no silent ``{name}`` leaks)."""
    try:
        template = _messages(locale)[key]
    except KeyError as error:
        raise I18nError(f"missing_message:{key}") from error
    if raw:
        return template
    needed = {name for _, name, _, _ in string.Formatter().parse(template) if name}
    missing = needed - set(params)
    if missing:
        raise I18nError(f"missing_parameter:{key}:{','.join(sorted(missing))}")
    return template.format(**params)
