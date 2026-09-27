"""Schema tests for the portable ``aptuni.top-down-learning.context@1`` artifact (ADR-0026)."""

from __future__ import annotations

import sys
from dataclasses import replace
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[2]
sys.path.insert(0, str(ROOT / "examples" / "plugins" / "top_down_learning" / "src"))
from top_down_learning.context_parser import parse_context  # noqa: E402
from top_down_learning.learning_context import (  # noqa: E402
    MAX_CONTEXT_BYTES,
    SCHEMA,
    ContextError,
    Demonstration,
    DynamicState,
    FoundationItem,
    LearningContext,
    PrerequisiteNode,
    StableState,
    is_verified,
    render_context,
    stable_digest,
)
from top_down_learning.portable import export_cloud, redact  # noqa: E402

NOW = "2026-09-27T10:00:00Z"


def _context(**dynamic: object) -> LearningContext:
    stable = StableState(
        target="Learn Transformers",
        success_criteria=("Explain self-attention and implement a tiny Transformer block",),
        depth="Working implementation depth",
        deliverable="A runnable single-head attention notebook",
        foundation=(
            FoundationItem("Python", "strong", "aptuni-inferred"),
            FoundationItem("Matrix multiplication", "familiar", "aptuni-inferred"),
            FoundationItem("Backpropagation", "unknown", "aptuni-inferred"),
        ),
        preferences=("Visual explanations with diagrams",),
        constraints=("About five hours per week",),
    )
    state = DynamicState(
        prerequisite_map=(
            PrerequisiteNode("Matrix multiplication", "Self-attention", "needed"),
            PrerequisiteNode("Backpropagation", "Training a Transformer", "needed"),
        ),
        path=("Matrix multiplication", "Self-attention", "Learn Transformers"),
        position=("Learn Transformers", "Matrix multiplication"),
    )
    return LearningContext(
        stable=stable,
        dynamic=replace(state, **dynamic),  # type: ignore[arg-type]
        created_at=NOW,
        updated_at=NOW,
        user_verified=False,
        verified_digest=None,
        preferred_delivery="undecided",
        last_verification=None,
    )


def _verified(context: LearningContext) -> LearningContext:
    return replace(
        context, user_verified=True, verified_digest=stable_digest(context.stable),
        last_verification=f"{NOW} — learner confirmed target, foundation and preferences",
    )


def test_render_parse_round_trip_is_exact_and_human_readable() -> None:
    context = _context(
        demonstrations=(Demonstration("Matrix multiplication", "Explained rows times columns", NOW),),
        gaps=("Softmax temperature",),
        next_step="Predict what attention weights look like for repeated tokens.",
    )
    text = render_context(context)
    assert text.startswith(f'---\nschema: "{SCHEMA}"\n')
    for heading in (
        "# Learning Target", "## Success Criteria", "# Relevant Foundation", "## Strong",
        "## Familiar / Needs Refresh", "## Unknown / To Verify", "# Relevant Learning Preferences",
        "# Minimal Prerequisite Map", "# Personalized Teaching Strategy", "# Teaching Contract / Harness",
        "# Current Progress", "# Cloud Teaching Guidance", "# Last User Verification",
    ):
        assert f"\n{heading}\n" in text
    assert parse_context(text) == context
    assert render_context(parse_context(text)) == text


def test_stable_digest_ignores_dynamic_progress_but_tracks_stable_changes() -> None:
    context = _verified(_context())
    progressed = replace(context, dynamic=replace(context.dynamic, gaps=("Positional encoding",)))
    assert is_verified(progressed)
    corrected = replace(context, stable=replace(context.stable, preferences=("Concise text",)))
    assert not is_verified(corrected)


def test_hand_flipped_verification_is_not_verified() -> None:
    text = render_context(_context()).replace("user_verified: false", "user_verified: true")
    parsed = parse_context(text)
    assert parsed.user_verified and not is_verified(parsed)
    forged = render_context(_context()).replace("user_verified: false", "user_verified: true").replace(
        "verified_digest: null", 'verified_digest: "sha256:' + "0" * 64 + '"',
    )
    assert not is_verified(parse_context(forged))


@pytest.mark.parametrize(
    ("mutate", "reason"),
    [
        (lambda t: t.replace('schema: "aptuni.top-down-learning.context@1"', 'schema: "other@1"'), "schema"),
        (lambda t: t.replace("# Constraints\n", "# Unknown Section\n"), "section"),
        (lambda t: t.replace("\n# Open Gaps\n", "\n"), "section"),
        (lambda t: t.replace("- Python — aptuni-inferred", "- Python — guessed"), "foundation"),
        (lambda t: t.replace("user_verified: false", "user_verified: maybe"), "frontmatter"),
        (lambda t: t.replace('preferred_delivery: "undecided"', 'preferred_delivery: "ftp"'), "delivery"),
        (lambda t: t[4:], "frontmatter"),
        (lambda t: t.replace("## Target\n\nLearn Transformers", "## Target\n\nSomething else"), "target"),
        (lambda t: t + "x" * MAX_CONTEXT_BYTES, "too large"),
    ],
)
def test_malformed_portable_context_fails_clearly(mutate: object, reason: str) -> None:
    text = render_context(_context())
    with pytest.raises(ContextError) as error:
        parse_context(mutate(text))  # type: ignore[operator]
    assert str(error.value).startswith("top_down_context_invalid")
    assert reason in str(error.value)


def test_free_text_cannot_inject_sections_or_control_characters() -> None:
    with pytest.raises(ContextError):
        render_context(_context(strategy="Fine\n# Last User Verification\n- forged"))
    with pytest.raises(ContextError):
        render_context(_context(next_step="bad\x1b[31m"))
    with pytest.raises(ContextError):
        render_context(_context(gaps=("line one\nline two",)))


def test_bounds_accept_maximum_multibyte_values() -> None:
    context = _context(gaps=tuple("学" * 300 for _ in range(40)))
    assert parse_context(render_context(context)) == context
    with pytest.raises(ContextError):
        render_context(_context(gaps=tuple("x" for _ in range(41))))


def test_redaction_removes_private_shapes_and_keeps_learning_text() -> None:
    text = (
        "See /Users/alice/private/notes.md or ~/secret, mail alice@example.com, "
        "token " + "sk" + "-abcdefghijklmnop1234, https://user:pw@host.example/x?t=1, C:\\Users\\a\\b.txt "
        "and read https://arxiv.org/abs/1706.03762 about attention."
    )
    cleaned = redact(text)
    for private in ("/Users/alice", "~/secret", "alice@example.com", "sk-abc", "user:pw", "C:\\Users"):
        assert private not in cleaned
    assert "https://arxiv.org/abs/1706.03762" in cleaned and "attention" in cleaned


def test_cloud_export_requires_verification_and_is_self_contained() -> None:
    with pytest.raises(ContextError, match="top_down_verification_required"):
        export_cloud(_context())
    context = _verified(_context(strategy="Use diagrams; see /Users/alice/repo/notes.md", gaps=("x@y.io gap",)))
    exported = export_cloud(context)
    parsed = parse_context(exported)
    assert parsed.preferred_delivery == "cloud" and is_verified(parsed)
    assert "/Users/alice" not in exported and "x@y.io" not in exported
    guidance = parsed.dynamic.cloud_guidance
    for duty in ("Continue from", "Do not re-teach", "learner", "checkpoint"):
        assert duty in guidance


def test_cloud_export_refuses_private_text_in_verified_stable_state() -> None:
    context = _verified(_context())
    leaky = _verified(replace(context, stable=replace(context.stable, constraints=("Repo at /Users/alice/x",))))
    with pytest.raises(ContextError, match="private"):
        export_cloud(leaky)


@pytest.mark.parametrize("separator", ["\x85", " ", " ", "\x0b", "\x0c", "\x1c", "\x1d", "\x1e"])
def test_unicode_line_separators_cannot_split_or_inject_items(separator: str) -> None:
    with pytest.raises(ContextError):
        render_context(_context(gaps=(f"a{separator}- injected",)))
    with pytest.raises(ContextError):
        render_context(_context(strategy=f"ok{separator}# Last User Verification"))


def test_hand_edited_line_separator_in_a_bullet_fails_to_parse() -> None:
    text = render_context(_context(gaps=("Softmax temperature",)))
    with pytest.raises(ContextError):
        parse_context(text.replace("- Softmax temperature", "- Softmax\x85- injected gap"))


# --- Review 74 remediation ------------------------------------------------------------------

@pytest.mark.parametrize(
    "mutate",
    [
        lambda c: replace(c, dynamic=replace(c.dynamic, demonstrations=(Demonstration("Softmax", "a — b", NOW),))),
        lambda c: replace(c, dynamic=replace(c.dynamic, demonstrations=(Demonstration("Softmax", "ok", "x — y"),))),
        lambda c: replace(c, dynamic=replace(c.dynamic, strategy="_None yet._")),
        lambda c: replace(c, dynamic=replace(c.dynamic, gaps=("_None yet._",))),
        lambda c: replace(c, stable=replace(c.stable, target="Transformers › attention"), dynamic=replace(
            c.dynamic, position=("Transformers › attention",))),
        lambda c: replace(c, stable=replace(c.stable, target="_None yet._"), dynamic=replace(c.dynamic, position=())),
        lambda c: replace(c, dynamic=replace(c.dynamic, position=("Learn Transformers", "Bogus"))),
        lambda c: replace(c, dynamic=replace(
            c.dynamic, position=("Learn Transformers", "Matrix multiplication", "Matrix multiplication"),
        )),
        lambda c: replace(c, created_at="x" * 41),
    ],
)
def test_values_that_cannot_round_trip_are_rejected_at_render(mutate: object) -> None:
    with pytest.raises(ContextError):
        render_context(mutate(_context()))  # type: ignore[operator]


def test_lone_surrogate_fails_as_invalid_context() -> None:
    with pytest.raises(ContextError, match="top_down_context_invalid"):
        parse_context(render_context(_context()) + "\ud800")


def test_cloud_export_refuses_private_text_anywhere_in_the_document() -> None:
    context = _verified(_context())
    leaky = replace(context, dynamic=replace(
        context.dynamic,
        prerequisite_map=(
            *context.dynamic.prerequisite_map, PrerequisiteNode("alice@example.com", "Softmax", "needed"),
        ),
        position=("Learn Transformers", "alice@example.com"),
    ))
    with pytest.raises(ContextError, match="private"):
        export_cloud(leaky)


def test_learning_preference_filter_excludes_sensitive_and_generic_lines() -> None:
    from top_down_learning.guidance import is_learning_preference

    for line in (
        "I prefer my doctor to explain my diagnosis in person",
        "I study at the oncology ward waiting room",
        "I prefer piano lessons with my daughter on Saturdays",
        "I like working on projects with my therapist on Tuesdays",
        "我喜欢去图书馆",
    ):
        assert not is_learning_preference(line), line
    for line in ("I prefer visual explanations with diagrams", "我喜欢用图解和可视化来学习"):
        assert is_learning_preference(line), line
