#!/usr/bin/env python3
"""Regenerate the Top-Down Learning flagship demo contexts from a synthetic learner.

Run from the repository root: ``.tools/bin/uv run python tools/regenerate_top_down_demo.py``.
The learner is synthetic and the clock is fixed, so the output is deterministic.
"""

from __future__ import annotations

import sys
import tempfile
from collections.abc import Iterator
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "examples" / "plugins" / "top_down_learning"
sys.path.insert(0, str(PLUGIN / "src"))

from aptuni.api.v1 import connect, load_manifest  # noqa: E402
from aptuni.api.v1.grants import PluginGrantManager  # noqa: E402
from aptuni.application.service import AptuniService  # noqa: E402
from aptuni.application.workspace import Workspace  # noqa: E402
from top_down_learning.learning_context import render_context  # noqa: E402
from top_down_learning.portable import export_cloud  # noqa: E402
from top_down_learning.workflow import TRANSFORMER_PREREQUISITES, TopDownLearning  # noqa: E402

SYNTHETIC_LEARNER = (
    ("I have practical Python experience", "skills"),
    ("I write Python services every day", "skills"),
    ("I am comfortable with matrix multiplication", "knowledge"),
    ("I use matrix multiplication in linear algebra work", "knowledge"),
    ("I know a little about backpropagation", "knowledge"),
    ("I prefer visual explanations with diagrams", "preferences"),
    ("I like first-principles learning: why before formulas", "preferences"),
    ("I prefer aisle seats on long flights", "preferences"),
)


def _ticks() -> Iterator[str]:
    return iter(f"2026-09-27T10:{minute:02d}:00Z" for minute in range(60))


def main() -> None:
    with tempfile.TemporaryDirectory() as temporary:
        workspace = Workspace(Path(temporary) / "state")
        service = AptuniService(workspace)
        service.init(Path(temporary) / "vault")
        for statement, module in SYNTHETIC_LEARNER:
            service.remember(statement, module)
        manifest = load_manifest(PLUGIN / "src" / "top_down_learning" / "aptuni-plugin.toml")
        manager = PluginGrantManager(workspace)
        api = connect(manifest, manager.apply(manager.plan(manifest).action_id).grant_id, workspace=workspace)
        ticks = _ticks()
        learning = TopDownLearning(api, clock=lambda: next(ticks))
        draft = learning.prepare(
            "Learn Transformers well enough to implement and explain one", TRANSFORMER_PREREQUISITES,
            success_criteria=(
                "Explain self-attention from first principles", "Implement a single Transformer block in PyTorch",
            ),
            depth="Working implementation depth", deliverable="A runnable single-head attention notebook",
            constraints=("About five hours per week",),
        )
        draft = learning.revise(draft.context, foundation={"Softmax": "familiar", "Backpropagation": "familiar"})
        context = learning.verify(draft.context, draft.verification_digest, "Yes, that's accurate.")
        context = learning.choose_delivery(
            context, "local",
            "Start each concept with a diagram of the data flow, ask the learner to predict the result for a "
            "two-token example, then derive why the mechanism is needed before writing the PyTorch code into "
            "the notebook.",
        )
        for concept, output, summary in (
            ("Softmax", "Softmax exponentiates the scores and divides by their sum, so every weight is positive "
             "and they add up to one.", "Explained softmax as positive normalized weights"),
            ("Backpropagation", "Gradients flow backwards through the chain rule; each layer multiplies the "
             "upstream gradient by its local derivative.", "Explained backpropagation via the chain rule"),
        ):
            context = learning.record_progress(
                context, concept=concept, diagnosis="understood", action="advance", learner_output=output,
                summary=summary,
            )
        context = learning.record_progress(
            context, concept="Self-attention", diagnosis="partial", action="descend",
            prerequisite="Dot product as similarity",
            learner_output="Queries and keys are multiplied but I am not sure why that measures relevance.",
            summary="Unsure why a query-key dot product measures relevance",
        )
        context = learning.record_progress(
            context, concept="Dot product as similarity", diagnosis="understood", action="return",
            learner_output="A dot product is large when two vectors point the same way, so it scores how aligned "
            "a query is with each key.",
            summary="Explained dot product as directional alignment",
            next_step="Back to self-attention: ask the learner to predict the attention weights for two tokens "
            "with aligned keys.",
        )
    out = PLUGIN / "examples"
    (out / "transformer_local_context.md").write_text(render_context(context), encoding="utf-8")
    (out / "transformer_cloud_context.md").write_text(export_cloud(context), encoding="utf-8")


if __name__ == "__main__":
    main()
