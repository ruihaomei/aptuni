"""Top-Down Learning workflow over ``aptuni.api.v1`` and the portable learning context.

Only ``prepare`` and ``propose_memory`` touch Aptuni. Every other step is a pure transformation of
the learner-owned context, so a delivery-mode choice or cloud export can never widen authority.
"""

from __future__ import annotations

import hashlib
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from typing import Literal

from aptuni.api.v1 import AptuniAPI, MemoryProposal
from top_down_learning import guidance
from top_down_learning.context_parser import parse_context
from top_down_learning.demo_maps import PARKING_PREREQUISITES, TRANSFORMER_PREREQUISITES, PrerequisiteSpec
from top_down_learning.learner_signals import is_affirmative, require_learner_output
from top_down_learning.learning_context import (
    MAX_DEPTH,
    POSITION_SEP,
    SEP,
    ConceptNote,
    ContextError,
    Demonstration,
    DynamicState,
    FoundationItem,
    LearningContext,
    Level,
    PrerequisiteNode,
    StableState,
    canonical_foundation,
    is_verified,
    render_context,
    stable_digest,
)
from top_down_learning.portable import redact

__all__ = [
    "PARKING_PREREQUISITES", "TRANSFORMER_PREREQUISITES", "Draft", "PrerequisiteSpec", "ResumeStatus",
    "TopDownLearning",
]

Diagnosis = Literal["understood", "partial", "misconception", "unknown"]
Action = Literal["advance", "reinforce", "descend", "return"]
ProposalKind = Literal["learning_gap", "demonstrated_understanding", "teaching_preference"]
MAX_PREREQUISITES = 12
MAX_TERMS = 3
MAX_CLARIFY = 3
PREFERENCE_QUERIES = ("prefer", "like", "learn", "learning", "explanations", "examples", "学习", "喜欢")
MAX_PREFERENCES = 6
NEGATIONS = ("no experience", "do not know", "don't know", "not familiar", "never used", "never learned", "lack ")
TARGET_LABEL = "Target"


@dataclass(frozen=True)
class Draft:
    """A context awaiting learner verification, with the summary the learner must check."""

    context: LearningContext
    markdown: str
    summary: str
    verification_digest: str
    clarify: tuple[str, ...]


@dataclass(frozen=True)
class ResumeStatus:
    context: LearningContext
    verified: bool
    stale_verification: bool
    position: tuple[str, ...]
    next_step: str
    delivery: str


def _now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _clean(value: str) -> str:
    """Trim, redact and neutralize the portable format's separators in Agent-supplied text."""
    if not isinstance(value, str) or len(value) > 500:
        raise ContextError("top_down_context_invalid: text values must be strings of at most 500 characters")
    return redact(value.strip()).replace(SEP, " - ").replace(POSITION_SEP, " > ")


class TopDownLearning:
    def __init__(self, api: AptuniAPI, *, clock: Callable[[], str] = _now) -> None:
        self.api = api
        self.clock = clock

    # --- drafting -------------------------------------------------------------------------

    def prepare(
        self,
        target: str,
        prerequisites: Sequence[PrerequisiteSpec],
        *,
        success_criteria: Sequence[str] = (),
        depth: str = "",
        deliverable: str = "",
        constraints: Sequence[str] = (),
    ) -> Draft:
        """Retrieve only task-relevant Aptuni context and build an unverified draft."""
        if not isinstance(target, str) or not target.strip() or len(target) > 500:
            raise ContextError("top_down_context_invalid: target must be 1-500 characters")
        specs = self._specs(prerequisites)
        target = _clean(target)
        foundation = canonical_foundation(tuple(
            FoundationItem(spec.concept, self._inferred_level(spec), "aptuni-inferred") for spec in specs
        ))
        levels = {item.concept: item.level for item in foundation}
        nodes = tuple(
            PrerequisiteNode(spec.concept, spec.required_for, "known" if levels[spec.concept] == "strong" else "needed")
            for spec in specs
        )
        path = tuple(node.concept for node in nodes if node.status == "needed")
        counts = {
            level: sum(1 for item in foundation if item.level == level) for level in ("strong", "familiar", "unknown")
        }
        now = self.clock()
        context = LearningContext(
            stable=StableState(
                target=target,
                success_criteria=tuple(_clean(value) for value in success_criteria),
                depth=_clean(depth),
                deliverable=_clean(deliverable),
                foundation=foundation,
                preferences=self._preferences(),
                constraints=tuple(_clean(value) for value in constraints),
            ),
            dynamic=DynamicState(
                diagnostics=(
                    f"Aptuni evidence suggests {counts['strong']} strong, {counts['familiar']} familiar and "
                    f"{counts['unknown']} unevidenced prerequisites; inferred until the learner verifies.",
                ),
                prerequisite_map=nodes,
                path=path,
                teaching_contract=guidance.PRINCIPLES,
                position=(target, path[0]) if path else (target,),
            ),
            created_at=now,
            updated_at=now,
        )
        return self.summarize(context)

    def summarize(self, context: LearningContext) -> Draft:
        """Render the verification summary for the exact current stable state."""
        stable = context.stable
        by_level = {
            level: [f"{i.concept} ({i.basis})" for i in stable.foundation if i.level == level]
            for level in ("strong", "familiar", "unknown")
        }
        lines = [
            f"Target: {stable.target}",
            "Success: " + ("; ".join(stable.success_criteria) or "not yet stated"),
            "Already strong: " + (", ".join(by_level["strong"]) or "none"),
            "Familiar, may need a refresh: " + (", ".join(by_level["familiar"]) or "none"),
            "No evidence yet: " + (", ".join(by_level["unknown"]) or "none"),
            "Learning preferences: " + ("; ".join(stable.preferences) or "none found"),
            "Constraints: " + ("; ".join(stable.constraints) or "none stated"),
            "Proposed path: " + " → ".join((*context.dynamic.path, stable.target)),
            "Is this accurate? Please correct anything wrong or add anything missing.",
        ]
        clarify = tuple(i.concept for i in stable.foundation if i.level == "unknown")[:MAX_CLARIFY]
        return Draft(context, render_context(context), "\n".join(lines), stable_digest(stable), clarify)

    def revise(
        self,
        context: LearningContext,
        *,
        foundation: Mapping[str, Level] | None = None,
        add_preferences: Sequence[str] = (),
        remove_preferences: Sequence[str] = (),
        add_constraints: Sequence[str] = (),
        remove_constraints: Sequence[str] = (),
        success_criteria: Sequence[str] | None = None,
        depth: str | None = None,
        deliverable: str | None = None,
    ) -> Draft:
        """Apply learner corrections; learner statements override inference and clear verification."""
        stable = context.stable
        items = {item.concept: item for item in stable.foundation}
        for raw_concept, level in (foundation or {}).items():
            concept = _clean(raw_concept)
            if level not in ("strong", "familiar", "unknown"):
                raise ContextError("top_down_context_invalid: foundation level is unknown")
            items[concept] = FoundationItem(concept, level, "learner-stated")
        stable = replace(
            stable,
            foundation=canonical_foundation(tuple(items.values())),
            preferences=self._edit(stable.preferences, add_preferences, remove_preferences),
            constraints=self._edit(stable.constraints, add_constraints, remove_constraints),
            success_criteria=(
                tuple(_clean(v) for v in success_criteria) if success_criteria is not None else stable.success_criteria
            ),
            depth=_clean(depth) if depth is not None else stable.depth,
            deliverable=_clean(deliverable) if deliverable is not None else stable.deliverable,
        )
        dynamic = self._replan(context.dynamic, stable)
        revised = replace(
            context, stable=stable, dynamic=dynamic, user_verified=False, verified_digest=None,
            updated_at=self.clock(),
        )
        if revised.preferred_delivery != "undecided":
            revised = replace(revised, dynamic=replace(dynamic, cloud_guidance=guidance.cloud_guidance(revised)))
        return self.summarize(revised)

    def verify(self, context: LearningContext, verification_digest: str, learner_confirmation: str) -> LearningContext:
        """Mark verified only for the exact summarized state and an affirmative learner reply."""
        if verification_digest != stable_digest(context.stable):
            raise ContextError("top_down_verification_stale")
        if not is_affirmative(learner_confirmation):
            raise ContextError("top_down_confirmation_required")
        now = self.clock()
        return replace(
            context, user_verified=True, verified_digest=stable_digest(context.stable), updated_at=now,
            last_verification=f"{now} — learner confirmed the target, foundation, preferences, constraints and path",
        )

    # --- teaching -------------------------------------------------------------------------

    def choose_delivery(
        self, context: LearningContext, mode: str, strategy: str, next_step: str = "",
    ) -> LearningContext:
        self._require_verified(context)
        if mode not in ("local", "cloud"):
            raise ContextError("top_down_context_invalid: delivery mode must be local or cloud")
        if not isinstance(strategy, str) or not strategy.strip():
            raise ContextError("top_down_strategy_required")
        platform: guidance.Platform = "local" if mode == "local" else "cloud"
        chosen = replace(context, preferred_delivery=platform, updated_at=self.clock())
        focus = context.dynamic.position[-1]
        dynamic = replace(
            context.dynamic,
            strategy=_clean(strategy),
            teaching_contract=guidance.teaching_contract(chosen, platform),
            next_step=_clean(next_step) or f"Start with {focus}: ask for a prediction before explaining.",
        )
        chosen = replace(chosen, dynamic=dynamic)
        chosen = replace(chosen, dynamic=replace(dynamic, cloud_guidance=guidance.cloud_guidance(chosen)))
        render_context(chosen)
        return chosen

    def record_progress(
        self,
        context: LearningContext,
        *,
        concept: str,
        diagnosis: Diagnosis,
        action: Action,
        learner_output: str,
        summary: str,
        prerequisite: str | None = None,
        next_step: str = "",
    ) -> LearningContext:
        """Update dynamic state from one diagnosed learner output; stable state never changes here."""
        self._require_verified(context)
        if context.preferred_delivery == "undecided":
            raise ContextError("top_down_delivery_required")
        require_learner_output(learner_output)
        if diagnosis not in ("understood", "partial", "misconception", "unknown"):
            raise ContextError("top_down_context_invalid: diagnosis is unknown")
        position = context.dynamic.position
        focus = position[-1] if len(position) > 1 else TARGET_LABEL
        if concept not in (position[-1], focus):
            raise ContextError("top_down_not_current_concept")
        summary = _clean(summary)
        on_path = len(position) == 1 or (len(position) == 2 and position[1] in context.dynamic.path)
        dynamic = context.dynamic
        if action in ("advance", "return") and diagnosis != "understood":
            raise ContextError("top_down_understanding_required")
        if action == "advance":
            if not on_path:
                raise ContextError("top_down_return_required")
            dynamic = self._demonstrate(dynamic, focus, summary)
            done = {d.concept for d in dynamic.demonstrations}
            remaining = [c for c in dynamic.path if c not in done]
            dynamic = replace(dynamic, position=(position[0], remaining[0]) if remaining else (position[0],))
            if len(position) == 1:
                next_step = next_step or "Target reached: review the success criteria with the learner."
        elif action == "return":
            if on_path:
                raise ContextError("top_down_not_in_prerequisite")
            dynamic = replace(self._demonstrate(dynamic, focus, summary), position=position[:-1])
        elif action == "descend":
            dynamic = self._descend(dynamic, focus, diagnosis, summary, prerequisite)
        elif action == "reinforce":
            dynamic = self._note(dynamic, focus, diagnosis, summary)
        else:
            raise ContextError("top_down_context_invalid: action is unknown")
        dynamic = replace(dynamic, next_step=_clean(next_step) or dynamic.next_step)
        updated = replace(context, dynamic=dynamic, updated_at=self.clock())
        updated = replace(updated, dynamic=replace(dynamic, cloud_guidance=guidance.cloud_guidance(updated)))
        render_context(updated)
        return updated

    def resume(self, markdown: str) -> ResumeStatus:
        context = parse_context(markdown)
        verified = is_verified(context)
        return ResumeStatus(
            context, verified, context.user_verified and not verified, context.dynamic.position,
            context.dynamic.next_step, context.preferred_delivery,
        )

    def propose_memory(self, context: LearningContext, kind: ProposalKind, subject: str) -> MemoryProposal:
        """Explicitly propose one durable learning fact; it stays quarantined for owner review."""
        self._require_verified(context)
        subject = _clean(subject)
        target = context.stable.target
        if kind == "demonstrated_understanding":
            count = len({d.at for d in context.dynamic.demonstrations if d.concept == subject})
            if count < 2:
                raise ContextError("top_down_evidence_insufficient")
            statement = (
                f"The teaching Agent recorded {count} demonstrations of understanding of {subject} "
                f"while learning {target}"
            )
            module = "knowledge"
        elif kind == "learning_gap":
            gaps = {n.concept for n in context.dynamic.misconceptions}
            gaps |= {gap.split(": ", 1)[0] for gap in context.dynamic.gaps}
            if subject not in gaps:
                raise ContextError("top_down_evidence_insufficient")
            statement, module = f"Needs more practice with {subject} while learning {target}", "knowledge"
        elif kind == "teaching_preference":
            if subject not in context.stable.preferences:
                raise ContextError("top_down_evidence_insufficient")
            statement, module = subject, "preferences"
        else:
            raise ContextError("top_down_context_invalid: proposal kind is unknown")
        key = "top-down:" + hashlib.sha256(f"{kind}\0{target}\0{subject}".encode()).hexdigest()
        return self.api.propose_memory(statement[:500], module=module, idempotency_key=key)  # type: ignore[arg-type]

    # --- helpers --------------------------------------------------------------------------

    @staticmethod
    def _specs(prerequisites: Sequence[PrerequisiteSpec]) -> tuple[PrerequisiteSpec, ...]:
        if len(prerequisites) > MAX_PREREQUISITES:
            raise ContextError(f"top_down_context_invalid: at most {MAX_PREREQUISITES} prerequisites")
        specs = []
        for spec in prerequisites:
            terms = tuple(_clean(term).lower() for term in spec.evidence_terms)
            if not 1 <= len(terms) <= MAX_TERMS or not all(0 < len(term) <= 40 for term in terms):
                raise ContextError("top_down_context_invalid: each prerequisite needs 1-3 short evidence terms")
            specs.append(PrerequisiteSpec(_clean(spec.concept), terms, _clean(spec.required_for)))
        if len({spec.concept for spec in specs}) != len(specs):
            raise ContextError("top_down_context_invalid: prerequisite concepts must be unique")
        return tuple(specs)

    def _inferred_level(self, spec: PrerequisiteSpec) -> Level:
        supporting: set[str] = set()
        for term in spec.evidence_terms:
            result = self.api.query_context(term, modules=("knowledge", "skills"), max_units=1200, limit=10)
            for item in result.items:
                text = item.text.lower()
                if (
                    item.canonical_id and item.module in ("knowledge", "skills") and term in text
                    and not any(negation in text for negation in NEGATIONS)
                ):
                    supporting.add(item.canonical_id)
        return "strong" if len(supporting) >= 2 else "familiar" if supporting else "unknown"

    def _preferences(self) -> tuple[str, ...]:
        found: dict[str, str] = {}
        for query in PREFERENCE_QUERIES:
            result = self.api.query_context(query, modules=("preferences",), max_units=800, limit=10)
            for item in result.items:
                text = " ".join(item.text.split())
                if (
                    item.canonical_id and item.module == "preferences" and len(text) <= 300
                    and guidance.is_learning_preference(text) and redact(text) == text
                ):
                    found.setdefault(item.canonical_id, text)
        return tuple(sorted(set(found.values())))[:MAX_PREFERENCES]

    @staticmethod
    def _edit(values: tuple[str, ...], add: Sequence[str], remove: Sequence[str]) -> tuple[str, ...]:
        removed = {_clean(value) for value in remove}
        kept = [value for value in values if value not in removed]
        for value in add:
            if _clean(value) not in kept:
                kept.append(_clean(value))
        return tuple(kept)

    @staticmethod
    def _replan(dynamic: DynamicState, stable: StableState) -> DynamicState:
        levels = {item.concept: item.level for item in stable.foundation}
        nodes = tuple(
            replace(node, status="known") if levels.get(node.concept) == "strong" and node.status == "needed"
            else replace(node, status="needed") if node.status == "known" and levels.get(node.concept) != "strong"
            else node
            for node in dynamic.prerequisite_map
        )
        planned = set(dynamic.path) | {n.concept for n in nodes if n.status == "needed" and n.concept in levels}
        path = tuple(n.concept for n in nodes if n.concept in planned and n.status == "needed")
        position = dynamic.position
        if len(position) <= 2 and (len(position) == 1 or position[1] not in path):
            position = (stable.target, path[0]) if path else (stable.target,)
        return replace(dynamic, prerequisite_map=nodes, path=path, position=position)

    def _demonstrate(self, dynamic: DynamicState, concept: str, summary: str) -> DynamicState:
        demos = (*dynamic.demonstrations, Demonstration(concept, summary, self.clock()))[-40:]
        return replace(
            dynamic,
            demonstrations=demos,
            prerequisite_map=tuple(
                replace(node, status="demonstrated") if node.concept == concept else node
                for node in dynamic.prerequisite_map
            ),
            misconceptions=tuple(n for n in dynamic.misconceptions if n.concept != concept),
            gaps=tuple(gap for gap in dynamic.gaps if not gap.startswith(f"{concept}: ")),
        )

    @staticmethod
    def _note(dynamic: DynamicState, concept: str, diagnosis: Diagnosis, summary: str) -> DynamicState:
        if diagnosis == "misconception":
            return replace(dynamic, misconceptions=(*dynamic.misconceptions, ConceptNote(concept, summary))[-40:])
        if diagnosis in ("partial", "unknown"):
            gap = f"{concept}: {summary}"
            return replace(dynamic, gaps=dynamic.gaps if gap in dynamic.gaps else (*dynamic.gaps, gap)[-40:])
        return dynamic

    def _descend(
        self, dynamic: DynamicState, concept: str, diagnosis: Diagnosis, summary: str, prerequisite: str | None,
    ) -> DynamicState:
        if diagnosis == "understood":
            raise ContextError("top_down_descend_requires_gap")
        if not prerequisite or not prerequisite.strip():
            raise ContextError("top_down_prerequisite_required")
        prerequisite = _clean(prerequisite)
        if len(dynamic.position) >= MAX_DEPTH:
            raise ContextError("top_down_descent_too_deep")
        if prerequisite in dynamic.position:
            raise ContextError("top_down_context_invalid: prerequisite is already on the current stack")
        dynamic = self._note(dynamic, concept, diagnosis, summary)
        nodes = dynamic.prerequisite_map
        if not any(node.concept == prerequisite for node in nodes):
            nodes = (*nodes, PrerequisiteNode(prerequisite, concept, "needed"))
        return replace(dynamic, prerequisite_map=nodes, position=(*dynamic.position, prerequisite))

    @staticmethod
    def _require_verified(context: LearningContext) -> None:
        if not is_verified(context):
            raise ContextError("top_down_verification_required")
