"""Goal-first adaptive learning plugin built exclusively on ``aptuni.api.v1``."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, replace
from typing import Literal

from aptuni.api.v1 import AptuniAPI, MemoryProposal


@dataclass(frozen=True)
class PrerequisiteTemplate:
    slug: str
    title: str
    explanation: str
    project_step: str
    learner_prompt: str
    foundation_terms: tuple[str, ...]
    check_terms: tuple[str, ...]


@dataclass(frozen=True)
class PersonalizedPrerequisite:
    slug: str
    title: str
    status: Literal["known", "needed", "completed"]
    canonical_ids: tuple[str, ...]


@dataclass
class LearningSession:
    goal: str
    prerequisites: tuple[PersonalizedPrerequisite, ...]
    teaching_preference: str
    current_index: int

    @property
    def current_slug(self) -> str | None:
        if self.current_index >= len(self.prerequisites):
            return None
        return self.prerequisites[self.current_index].slug


@dataclass(frozen=True)
class TeachingTurn:
    prerequisite_slug: str
    explanation: str
    project_step: str
    learner_prompt: str
    delivery_style: Literal["concise_project_first", "short_explain_apply"]


@dataclass(frozen=True)
class CheckResult:
    passed: bool
    missing_terms: tuple[str, ...]
    next_slug: str | None


PARKING_SYSTEM: tuple[PrerequisiteTemplate, ...] = (
    PrerequisiteTemplate(
        "python_service", "Python service basics",
        "Use a small Python service to turn camera observations into explicit parking-space state.",
        "Create one typed function that accepts detections and returns occupied space identifiers.",
        "Explain why a typed boundary helps you test the vision pipeline independently.",
        ("python",), ("typed", "test"),
    ),
    PrerequisiteTemplate(
        "camera_geometry", "Camera geometry",
        "Perspective makes equal parking spaces appear different; a homography maps the camera plane "
        "to a usable top-down plane.",
        "Mark four lot reference points and transform one frame into a top-down view.",
        "In your own words, explain how perspective and a homography affect space coordinates.",
        ("perspective", "homography"), ("perspective", "homography"),
    ),
    PrerequisiteTemplate(
        "vehicle_detection", "Vehicle detection",
        "An object detector produces vehicle bounding boxes and confidence, which are observations "
        "rather than occupancy truth.",
        "Run a detector on five representative frames and inspect false positives and misses.",
        "Explain the difference between a bounding box and an occupied-space decision.",
        ("object detection", "bounding box"), ("bounding", "occupancy"),
    ),
    PrerequisiteTemplate(
        "tracking", "Temporal tracking",
        "Tracking connects detections across frames so brief misses do not flip the parking state.",
        "Assign track IDs and add a short persistence window before changing occupancy.",
        "Describe how tracking reduces flicker without hiding a real departure.",
        ("tracking", "track id"), ("tracking", "flicker"),
    ),
    PrerequisiteTemplate(
        "occupancy_logic", "Occupancy logic",
        "Geometry and temporal evidence combine in a small state machine with explicit transition rules.",
        "Implement free, candidate-occupied and occupied states for one parking polygon.",
        "Teach the transition rules back and name one failure case.",
        ("state machine", "parking occupancy"), ("transition", "failure"),
    ),
    PrerequisiteTemplate(
        "system_validation", "System integration and validation",
        "A useful system measures end-to-end errors and exposes uncertainty instead of reporting only model accuracy.",
        "Build a replay test from short clips and report space-level precision, recall and transition delay.",
        "Explain why space-level evaluation can disagree with detector accuracy.",
        ("precision", "recall", "deployment"), ("space", "detector"),
    ),
)


class TopDownLearningPlugin:
    def __init__(self, api: AptuniAPI, catalog: tuple[PrerequisiteTemplate, ...] = PARKING_SYSTEM) -> None:
        self.api = api
        self.catalog = catalog

    def start(self, goal: str) -> LearningSession:
        personalized: list[PersonalizedPrerequisite] = []
        for prerequisite in self.catalog:
            query = " ".join(prerequisite.foundation_terms)
            context = self.api.query_context(
                query, modules=("knowledge", "skills"), max_units=2200,
            )
            matching = tuple(
                item.canonical_id for item in context.items
                if item.canonical_id and self._supports_foundation(item.text, prerequisite.foundation_terms)
            )
            personalized.append(PersonalizedPrerequisite(
                prerequisite.slug, prerequisite.title, "known" if matching else "needed", matching,
            ))
        preference = self.api.query_context(
            "concise project-first",
            modules=("preferences",), max_units=1200,
        )
        preference_text = next(
            (item.text for item in preference.items if item.canonical_id),
            "Use short explanations followed by immediate application.",
        )
        current = next((index for index, item in enumerate(personalized) if item.status == "needed"), len(personalized))
        return LearningSession(goal, tuple(personalized), preference_text, current)

    def teach(self, session: LearningSession) -> TeachingTurn:
        template = self._current(session)
        preference = session.teaching_preference.lower()
        style: Literal["concise_project_first", "short_explain_apply"] = (
            "concise_project_first" if "concise" in preference and "project-first" in preference
            else "short_explain_apply"
        )
        return TeachingTurn(
            template.slug, template.explanation, template.project_step, template.learner_prompt, style,
        )

    def check(self, session: LearningSession, learner_output: str) -> CheckResult:
        template = self._current(session)
        normalized = learner_output.lower()
        missing = tuple(term for term in template.check_terms if term not in normalized)
        if missing:
            return CheckResult(False, missing, template.slug)
        self._complete_current(session)
        return CheckResult(True, (), session.current_slug)

    def resume(self, goal: str, completed_slugs: tuple[str, ...]) -> LearningSession:
        """Rebuild bounded task state and replay only the exact completed prerequisite prefix."""
        session = self.start(goal)
        for slug in completed_slugs:
            if session.current_slug != slug:
                raise ValueError("top_down_progress_invalid")
            self._complete_current(session)
        return session

    @staticmethod
    def _complete_current(session: LearningSession) -> None:
        values = list(session.prerequisites)
        values[session.current_index] = replace(values[session.current_index], status="completed")
        session.prerequisites = tuple(values)
        session.current_index = next(
            (index for index in range(session.current_index + 1, len(values)) if values[index].status == "needed"),
            len(values),
        )

    def record_gap(self, session: LearningSession, learner_feedback: str) -> MemoryProposal:
        template = self._current(session)
        payload = f"{session.goal}\0{template.slug}\0{learner_feedback}".encode()
        key = "top-down-gap:" + hashlib.sha256(payload).hexdigest()
        return self.api.propose_memory(learner_feedback, module="knowledge", idempotency_key=key)

    def _current(self, session: LearningSession) -> PrerequisiteTemplate:
        slug = session.current_slug
        if slug is None:
            raise ValueError("the learning plan is complete")
        return next(item for item in self.catalog if item.slug == slug)

    @staticmethod
    def _supports_foundation(text: str, terms: tuple[str, ...]) -> bool:
        normalized = text.lower()
        negations = ("no experience", "do not know", "don't know", "not familiar", "never used", "lack ")
        return not any(marker in normalized for marker in negations) and any(term in normalized for term in terms)


def create_plugin(api: AptuniAPI) -> TopDownLearningPlugin:
    return TopDownLearningPlugin(api)
