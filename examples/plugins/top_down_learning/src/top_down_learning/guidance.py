"""Pedagogical primitives for Top-Down Learning.

The plugin supplies principles, preference-derived affordances and a safe checkpoint protocol. It
does not fix a teaching method: the teaching Agent writes the personalized strategy into the
portable context, where it stays transparent and can evolve with learner feedback.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from top_down_learning.learning_context import LearningContext

Platform = Literal["local", "cloud"]

CUES: dict[str, tuple[str, ...]] = {
    "visual": ("visual", "diagram", "picture", "animation", "animated", "plot", "geometric", "图解", "图示", "可视化"),
    "first_principles": (
        "first principles", "first-principles", "why", "derivation", "derive", "mechanism", "原理", "第一性",
    ),
    "project": ("project", "hands-on", "build", "apply", "项目", "实战"),
    "code": ("code", "runnable", "notebook", "implement", "代码"),
    "concise": ("concise", "brief", "short explanation", "简洁", "简短"),
    "detailed": ("detailed", "thorough", "in depth", "in-depth", "详细", "深入"),
    "questions": ("question", "socratic", "follow-up", "提问", "追问"),
}
# A preference is admitted only when it is explicitly about learning or teaching. Generic style words
# ("project", "practice", "build") alone are not enough: they also describe unrelated personal life.
LEARNING_WORDS = (
    "learn", "learning", "learner", "teach", "teaching", "taught", "explain", "explanation", "tutorial",
    "lesson", "lecture", "study", "studying", "instruction", "学习", "讲解", "教学", "解释", "课程",
)

PRINCIPLES = """Top-down, just in time: start from the target and teach only what this learner needs next.
- Continue from the recorded position; never restart or re-teach verified strong foundation.
- When a required concept rests on a missing prerequisite, descend briefly, verify it, then return upward.
- Keep each step small: explain, visualize when useful, ask for a prediction or question, apply.
- Require learner output (prediction, explanation back, code, derivation or debugging) before advancing.
- Diagnose each output as understood, partial, misconception or unknown; only understood advances.
- Record demonstrations, misconceptions, gaps and the next step in this context after meaningful progress.
- Ask targeted questions only when the answer would change the path."""


def _mentions(text: str, cue: str) -> bool:
    """Whole-word (plural-tolerant) match for ASCII cues; substring match for CJK cues."""
    if cue.isascii():
        return re.search(rf"(?<![a-z]){re.escape(cue)}(?:s|es)?(?![a-z])", text) is not None
    return cue in text


def preference_signals(preferences: tuple[str, ...]) -> tuple[str, ...]:
    """Return the named learning signals present in verified preferences, in a stable order."""
    joined = " ".join(preferences).lower()
    return tuple(name for name, cues in CUES.items() if any(_mentions(joined, cue) for cue in cues))


# Lines that touch health, family, money or faith stay out even when they mention learning; the learner
# can still add such a preference explicitly during verification.
SENSITIVE_WORDS = (
    "doctor", "diagnosis", "therapist", "therapy", "hospital", "ward", "oncology", "medical", "medication",
    "health", "illness", "injury", "clinic", "patient", "daughter", "son", "wife", "husband", "partner",
    "child", "children", "family", "pregnant", "bank", "salary", "debt", "religion", "church", "mosque",
    "temple", "医院", "医生", "诊断", "治疗", "病", "家人", "孩子", "女儿", "儿子", "妻子", "丈夫", "工资", "宗教",
)


def is_learning_preference(text: str) -> bool:
    lowered = text.lower()
    if any(_mentions(lowered, word) for word in SENSITIVE_WORDS):
        return False
    return any(_mentions(lowered, word) for word in LEARNING_WORDS)


def affordances(context: LearningContext, platform: Platform) -> tuple[str, ...]:
    """Preference-derived teaching affordances for one platform; empty when nothing is signalled."""
    signals = preference_signals(context.stable.preferences)
    deliverable = context.stable.deliverable or context.stable.target
    lines: list[str] = []
    if "visual" in signals:
        lines.append(
            "Visual: generate Mermaid diagrams, plots or a small local HTML visualization when it clarifies "
            "a mechanism."
            if platform == "local" else
            "Visual: use Mermaid, ASCII sketches or clearly described figures; the learner may not run local files."
        )
    if "first_principles" in signals:
        lines.append(
            "First principles: order each concept as why it is needed, mechanism or derivation, implementation, "
            "then abstraction; state the problem before the formula."
        )
    if "project" in signals:
        lines.append(f"Project-first: apply each concept immediately to the deliverable ({deliverable}).")
    if "code" in signals:
        lines.append(
            "Code: write small runnable examples and execute them locally with the learner."
            if platform == "local" else
            "Code: give short self-contained snippets the learner can paste and run."
        )
    if "concise" in signals:
        lines.append("Concise: keep explanations short and move to learner output quickly.")
    if "detailed" in signals:
        lines.append("Detailed: offer depth and invite follow-up questions before moving on.")
    if "questions" in signals:
        lines.append("Questions: welcome deep follow-up questions; answer them before resuming the path.")
    return tuple(lines)


def teaching_contract(context: LearningContext, platform: Platform) -> str:
    lines = [PRINCIPLES]
    derived = affordances(context, platform)
    if derived:
        lines += ["", "Preference-derived affordances:", *(f"- {line}" for line in derived)]
    return "\n".join(lines)


def cloud_guidance(context: LearningContext) -> str:
    """Self-contained instructions that let a cloud Agent continue without Aptuni installed."""
    position = " › ".join(context.dynamic.position) or context.stable.target
    strong = [item.concept for item in context.stable.foundation if item.level == "strong"]
    lines = [
        "This guidance was generated for this learner. You may not have Aptuni, their files or their history;",
        "this document is the complete learner model.",
        f"- Continue from the current position ({position}); do not restart the course.",
        "- Do not re-teach verified strong foundation"
        + (f" ({', '.join(strong)})." if strong else "."),
        "- Ask a targeted question only when the answer would change the path.",
        "- Use the learner's preferred instructional forms listed in Relevant Learning Preferences.",
        "- Require active learner output before marking any concept understood; diagnose it as understood,",
        "  partial, misconception or unknown.",
        "- If a missing prerequisite blocks progress, descend briefly, verify it, then return to the target path.",
        "- After meaningful progress, reply with a refreshed checkpoint: this whole document with updated",
        "  Current Progress, Demonstrated Understanding, Misconceptions, Open Gaps and Next Recommended Step.",
        "  Keep the frontmatter, section order and stable sections unchanged so verification remains valid.",
    ]
    derived = affordances(context, "cloud")
    if derived:
        lines += ["", "Preference-derived affordances:", *(f"- {line}" for line in derived)]
    return "\n".join(lines)
