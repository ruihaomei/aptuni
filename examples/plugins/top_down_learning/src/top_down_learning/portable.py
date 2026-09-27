"""Privacy-minimized portability: redaction and cloud export of a verified learning context."""

from __future__ import annotations

import json
import re
from dataclasses import asdict, replace

from top_down_learning.guidance import cloud_guidance, teaching_contract
from top_down_learning.learning_context import ContextError, LearningContext, is_verified, render_context

_PRIVATE_PATTERNS = (
    re.compile(r"(?<![\w/])(?:/(?:Users|home|private|var|tmp|etc|opt|Volumes|root)|~)/\S+"),
    re.compile(r"\b[A-Za-z]:\\\S+"),
    re.compile(r"file://\S+"),
    re.compile(r"https?://[^\s/]*@\S+"),
    re.compile(r"https?://[^\s?]+\?\S+"),
    re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+"),
    re.compile(r"\b(?:sk-|ghp_|gho_|github_pat_|xox[abpr]-|AKIA)[A-Za-z0-9_-]{8,}"),
    re.compile(r"\b[A-Za-z0-9_-]{32,}\b"),
)


def redact(text: str) -> str:
    """Replace path-, email-, credential- and token-shaped text with ``[redacted]``."""
    for pattern in _PRIVATE_PATTERNS:
        text = pattern.sub("[redacted]", text)
    return text


def has_private_text(text: str) -> bool:
    return redact(text) != text



def export_cloud(context: LearningContext) -> str:
    """Return a cloud-safe copy of a verified context; never calls Aptuni or widens any grant."""
    if not is_verified(context):
        raise ContextError("top_down_verification_required")
    stable_text = json.dumps(asdict(context.stable), ensure_ascii=False)
    if has_private_text(stable_text):
        raise ContextError("top_down_context_contains_private_text: correct the verified stable sections first")
    dynamic = context.dynamic
    cleaned = replace(
        dynamic,
        diagnostics=tuple(redact(value) for value in dynamic.diagnostics),
        strategy=redact(dynamic.strategy),
        demonstrations=tuple(replace(demo, summary=redact(demo.summary)) for demo in dynamic.demonstrations),
        misconceptions=tuple(replace(note, summary=redact(note.summary)) for note in dynamic.misconceptions),
        gaps=tuple(redact(value) for value in dynamic.gaps),
        next_step=redact(dynamic.next_step),
    )
    exported = replace(context, dynamic=cleaned, preferred_delivery="cloud")
    exported = replace(exported, dynamic=replace(
        cleaned, teaching_contract=teaching_contract(exported, "cloud"), cloud_guidance=cloud_guidance(exported),
    ))
    text = render_context(exported)
    if has_private_text(text.split("\n---\n", 1)[1]):
        raise ContextError("top_down_context_contains_private_text: correct the flagged sections first")
    return text
