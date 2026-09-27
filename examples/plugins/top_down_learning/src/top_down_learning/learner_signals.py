"""Bounded, content-free checks on learner replies (no raw reply is ever stored)."""

from __future__ import annotations

import re

from top_down_learning.learning_context import ContextError

MAX_LEARNER_OUTPUT = 4000
AFFIRM_WORDS = {"yes", "yep", "yeah", "correct", "accurate", "right", "confirm", "confirmed", "agreed",
                "ok", "okay", "good", "exactly"}
CORRECTION_WORDS = {"no", "not", "nope", "but", "however", "except", "actually", "wrong", "incorrect",
                    "add", "missing", "change", "instead", "never"}
AFFIRM_CJK = ("是", "对", "没错", "正确", "确认", "可以", "好")
CORRECTION_CJK = ("不", "错了", "但", "补充", "修改", "没有")
TRIVIAL_OUTPUTS = {"ok", "okay", "yes", "no", "idk", "sure", "got it", "understood", "懂了", "明白", "好的", "知道了"}


def require_learner_output(learner_output: str) -> None:
    if not isinstance(learner_output, str) or len(learner_output) > MAX_LEARNER_OUTPUT:
        raise ContextError("top_down_learner_output_required")
    normalized = re.sub(r"[\s.!?。！？]+", " ", learner_output).strip().lower()
    if len(normalized) < 4 or normalized in TRIVIAL_OUTPUTS:
        raise ContextError("top_down_learner_output_required")


def is_affirmative(reply: str) -> bool:
    if not isinstance(reply, str) or len(reply) > 1000:
        return False
    lowered = reply.lower()
    words = set(re.findall(r"[a-z]+", lowered))
    if words & CORRECTION_WORDS or "n't" in lowered or any(cue in reply for cue in CORRECTION_CJK):
        return False
    return bool(words & AFFIRM_WORDS) or any(cue in reply for cue in AFFIRM_CJK)
