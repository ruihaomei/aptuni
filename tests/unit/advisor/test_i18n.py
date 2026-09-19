"""English and Simplified Chinese are both first-class: identical keys and placeholders."""

from __future__ import annotations

import re

import pytest

from aptuni.i18n import LOCALES, I18nError, message_keys, normalize_locale, t

PLACEHOLDER = re.compile(r"\{([a-z_]+)\}")


def test_locales_have_identical_keys() -> None:
    assert message_keys("en") == message_keys("zh-CN")


def test_locales_have_identical_placeholders() -> None:
    for key in message_keys("en"):
        english = set(PLACEHOLDER.findall(t(key, "en", raw=True)))
        chinese = set(PLACEHOLDER.findall(t(key, "zh-CN", raw=True)))
        assert english == chinese, key


def test_chinese_messages_are_translated() -> None:
    def words(key: str) -> str:
        return PLACEHOLDER.sub("", t(key, "en", raw=True))

    untranslated = [key for key in message_keys("en")
                    if t(key, "en", raw=True) == t(key, "zh-CN", raw=True) and re.search("[a-z]{4}", words(key))]
    assert untranslated == []


def test_formatting_and_missing_parameters() -> None:
    assert "3" in t("advisor.preview.setup_minutes", "en", low=3, high=5)
    with pytest.raises(I18nError):
        t("advisor.preview.setup_minutes", "en", low=3)
    with pytest.raises(I18nError):
        t("no.such.key", "en")


@pytest.mark.parametrize(("raw", "expected"), [
    ("en", "en"), ("EN_us", "en"), ("zh", "zh-CN"), ("zh_CN", "zh-CN"), ("zh-Hans", "zh-CN"),
    ("2", "zh-CN"), ("1", "en"), ("简体中文", "zh-CN"), ("中文", "zh-CN"), (None, "en"),
    ("zh-TW", "en"), ("zh-Hant", "en"), ("zh_HK", "en"),  # never silently convert Traditional to Simplified
])
def test_normalize_locale(raw: str | None, expected: str) -> None:
    assert normalize_locale(raw) == expected


def test_unknown_locale_is_an_error() -> None:
    with pytest.raises(I18nError):
        normalize_locale("fr", strict=True)
    assert set(LOCALES) == {"en", "zh-CN"}
