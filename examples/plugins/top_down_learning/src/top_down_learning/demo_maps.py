"""Reference prerequisite maps for demos and tests.

In real use the teaching Agent proposes the minimal prerequisite map for the learner's target; these
maps only make the flagship Transformer journey and the parking-system example reproducible.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PrerequisiteSpec:
    """One candidate prerequisite: a concept, 1-3 evidence search terms and what it unlocks."""

    concept: str
    evidence_terms: tuple[str, ...]
    required_for: str


TRANSFORMER_PREREQUISITES: tuple[PrerequisiteSpec, ...] = (
    PrerequisiteSpec("Python", ("python",), "Implementation"),
    PrerequisiteSpec("Matrix multiplication", ("matrix multiplication",), "Self-attention"),
    PrerequisiteSpec("Softmax", ("softmax",), "Self-attention"),
    PrerequisiteSpec("Backpropagation", ("backpropagation",), "Training a Transformer"),
    PrerequisiteSpec("Self-attention", ("self-attention", "attention mechanism"), "Transformer block"),
    PrerequisiteSpec("Positional encoding", ("positional encoding",), "Transformer block"),
)

PARKING_PREREQUISITES: tuple[PrerequisiteSpec, ...] = (
    PrerequisiteSpec("Python service basics", ("python",), "Parking service"),
    PrerequisiteSpec("Camera geometry", ("homography", "perspective"), "Space coordinates"),
    PrerequisiteSpec("Vehicle detection", ("object detection", "bounding box"), "Occupancy evidence"),
    PrerequisiteSpec("Temporal tracking", ("tracking",), "Stable occupancy"),
    PrerequisiteSpec("Occupancy state machine", ("state machine",), "Parking service"),
)
