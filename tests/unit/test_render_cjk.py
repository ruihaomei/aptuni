"""Chinese, Japanese and Korean names render readably; confusable characters stay escaped.

Beta Day 0 (2026-09-29): a Chinese folder path appeared as ``\\u7533\\u8bf7/\\u7533\\u7814``, which
a Chinese owner cannot check before typing APPLY. Ideographs, kana and Hangul cannot imitate ASCII
structure, so they are shown as-is. Everything ADR-0013 item 2 guards against still is escaped and
flagged: controls, bidi and zero-width format characters, look-alike letters from other scripts,
fullwidth forms and unusual spaces.
"""

from __future__ import annotations

import pytest

from aptuni.cli.render import delimited_untrusted


@pytest.mark.parametrize("name", ["/Users/me/申请/申研", "ノート", "메모", "資料 2026"])
def test_cjk_names_render_readably_without_a_flag(name: str) -> None:
    assert delimited_untrusted(name) == f'"{name}"'


@pytest.mark.parametrize(("name", "escaped"), [
    ("p\u0430ypal", "\\u0430"),        # Cyrillic a imitating Latin a
    ("evil\u202etxt", "\\u202e"),      # right-to-left override
    ("a\u200bb", "\\u200b"),           # zero-width space
    ("x\u3000y", "\\u3000"),           # ideographic space can hide a word boundary
    ("\uff21PPLY", "\\uff21"),         # fullwidth A imitating APPLY
    ("笔记\u0301", "\\u0301"),          # a combining mark stacked on an ideograph
])
def test_confusable_characters_stay_escaped_and_flagged(name: str, escaped: str) -> None:
    rendered = delimited_untrusted(name)
    assert escaped in rendered
    assert rendered.endswith("[non-ascii/confusable-escaped]")


def test_a_mixed_name_keeps_the_ideographs_and_escapes_only_the_confusable_part() -> None:
    rendered = delimited_untrusted("申请\u202e/x")
    assert rendered.startswith('"申请\\u202e/x"')


def test_quotes_and_controls_still_cannot_break_the_delimiters() -> None:
    rendered = delimited_untrusted('申"\n')
    assert rendered.startswith('"申\\"\\n"') and "control-escaped" in rendered
