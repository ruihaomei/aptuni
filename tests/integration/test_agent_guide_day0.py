"""Agent guide lessons from Beta Day 0 (2026-09-29).

The Agent put a placeholder token in a runnable shell block and the owner ran it; private
repositories needed a token nobody had mentioned; and a command the owner ran through the chat's
shell did not see a variable exported in their terminal tab.
"""

from __future__ import annotations

import pytest

from aptuni.cli.guide_cli import agent_guide


@pytest.mark.parametrize("locale", ["en", "zh-CN"])
def test_the_guide_forbids_runnable_placeholders_and_explains_tokens(locale: str) -> None:
    text = agent_guide(locale)
    assert "Never put a placeholder in a command the user can run" in text
    assert "--github-token-env APTUNI_GITHUB_TOKEN" in text
    assert "Contents: Read-only" in text
    assert "never ask for, read or print the token" in text
    assert "the same terminal" in text and "does not share variables" in text


def test_the_guide_mentions_that_unreadable_sources_do_not_block_setup() -> None:
    text = agent_guide("en")
    assert "aptuni sync SOURCE_ID" in text
