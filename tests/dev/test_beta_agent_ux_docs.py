"""Keep Beta Agent UX claims inside the maintainer-accepted host boundary."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONTRACT_DOCS = (
    ROOT / "docs/dev/DECISIONS/ADR-0025-explicit-agent-activation.md",
    ROOT / "docs/developer/AGENT_UX.md",
    ROOT / "CHANGELOG.md",
)


def test_beta_agent_ux_documents_the_enforceable_off_boundary() -> None:
    combined = "\n".join(path.read_text(encoding="utf-8") for path in CONTRACT_DOCS).lower()

    for required in (
        "no new profile, memory or evidence retrieval",
        "no new aptuni memory capture",
        "already delivered",
        "not a security boundary",
        "new host task, chat or session",
    ):
        assert required in combined

    for forbidden in (
        "erases the host transcript",
        "revokes information already delivered",
        "guarantees that a human initiated",
        "cross-task non-leak",
    ):
        assert forbidden not in combined
