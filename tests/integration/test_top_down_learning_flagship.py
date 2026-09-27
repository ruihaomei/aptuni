"""Flagship Top-Down Learning workflow: the maintainer brief's validation matrix (ADR-0026)."""

from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import replace
from pathlib import Path

import pytest

from aptuni.api.v1 import AptuniAPI, AptuniAPIError, connect, load_manifest
from aptuni.api.v1.grants import PluginGrantManager
from aptuni.application.service import AptuniService
from aptuni.application.workspace import Workspace

ROOT = Path(__file__).parents[2]
EXAMPLE_SRC = ROOT / "examples" / "plugins" / "top_down_learning" / "src"
MANIFEST = EXAMPLE_SRC / "top_down_learning" / "aptuni-plugin.toml"
sys.path.insert(0, str(EXAMPLE_SRC))
from top_down_learning.context_parser import parse_context  # noqa: E402
from top_down_learning.learning_context import (  # noqa: E402
    ContextError,
    LearningContext,
    is_verified,
    render_context,
)
from top_down_learning.portable import export_cloud  # noqa: E402
from top_down_learning.workflow import (  # noqa: E402
    TRANSFORMER_PREREQUISITES,
    PrerequisiteSpec,
    TopDownLearning,
)

TARGET = "Learn Transformers"
STRONG_FOUNDATION = (
    ("I have practical Python experience", "skills"),
    ("I write Python services every day", "skills"),
    ("I am comfortable with matrix multiplication", "knowledge"),
    ("I use matrix multiplication in linear algebra work", "knowledge"),
    ("I implemented backpropagation from scratch", "skills"),
    ("I trained networks with backpropagation in PyTorch", "knowledge"),
)
UNRELATED = (
    ("My home address is 12 Example Street", "knowledge"),
    ("I prefer aisle seats on long flights", "preferences"),
    ("My bank is ExampleBank and my card ends 4242", "knowledge"),
    ("I want to run a marathon next spring", "goals"),
)


def _api(tmp_path: Path, memories: tuple[tuple[str, str], ...], *, capabilities: tuple[str, ...] | None = None):
    workspace = Workspace(tmp_path / "state")
    service = AptuniService(workspace)
    service.init(tmp_path / "vault")
    for statement, module in memories:
        service.remember(statement, module)
    manifest = load_manifest(MANIFEST)
    manager = PluginGrantManager(workspace)
    plan = manager.plan(manifest, capabilities=capabilities) if capabilities else manager.plan(manifest)
    grant = manager.apply(plan.action_id)
    return service, manager, connect(manifest, grant.grant_id, workspace=workspace)


def _verified(learning: TopDownLearning, context: LearningContext, mode: str = "local") -> LearningContext:
    draft = learning.summarize(context)
    verified = learning.verify(context, draft.verification_digest, "Yes, that's accurate.")
    return learning.choose_delivery(verified, mode, "Short visual explanations, then learner prediction.")


def _foundation(context: LearningContext) -> dict[str, str]:
    return {item.concept: item.level for item in context.stable.foundation}


# 1. strong foundation skips known prerequisites --------------------------------------------------

def test_strong_foundation_learner_skips_known_prerequisites(tmp_path: Path) -> None:
    _, _, api = _api(tmp_path, STRONG_FOUNDATION)
    draft = TopDownLearning(api).prepare(TARGET, TRANSFORMER_PREREQUISITES)
    levels = _foundation(draft.context)
    assert levels["Python"] == levels["Matrix multiplication"] == levels["Backpropagation"] == "strong"
    path = draft.context.dynamic.path
    assert "Python" not in path and "Matrix multiplication" not in path and "Backpropagation" not in path
    assert TARGET not in path and draft.context.dynamic.position == (TARGET, path[0])
    assert not draft.context.user_verified
    assert "Backpropagation" not in draft.clarify


# 2. weaker learner receives just-in-time prerequisite drilling ----------------------------------

def test_weaker_learner_descends_just_in_time_and_returns(tmp_path: Path) -> None:
    _, _, api = _api(tmp_path, (("I know a little Python", "skills"),))
    learning = TopDownLearning(api)
    draft = learning.prepare(TARGET, TRANSFORMER_PREREQUISITES)
    assert _foundation(draft.context)["Python"] == "familiar"
    assert draft.context.dynamic.path[0] == "Python"
    context = _verified(learning, draft.context)
    context = learning.record_progress(
        context, concept="Python", diagnosis="understood", action="advance",
        learner_output="A list comprehension builds a list from an iterable in one expression.",
        summary="Explained list comprehensions correctly",
    )
    assert context.dynamic.position == (TARGET, "Matrix multiplication")
    context = learning.record_progress(
        context, concept="Matrix multiplication", diagnosis="partial", action="descend",
        prerequisite="Vector geometry", learner_output="You multiply the numbers together somehow?",
        summary="Unsure why rows meet columns",
    )
    assert context.dynamic.position == (TARGET, "Matrix multiplication", "Vector geometry")
    node = next(n for n in context.dynamic.prerequisite_map if n.concept == "Vector geometry")
    assert node.required_for == "Matrix multiplication" and node.status == "needed"
    with pytest.raises(ContextError, match="top_down_return_required"):
        learning.record_progress(
            context, concept="Vector geometry", diagnosis="understood", action="advance",
            learner_output="The dot product measures alignment.", summary="ok",
        )
    context = learning.record_progress(
        context, concept="Vector geometry", diagnosis="understood", action="return",
        learner_output="A dot product sums element products and measures how aligned two vectors are.",
        summary="Explained dot product as alignment",
    )
    assert context.dynamic.position == (TARGET, "Matrix multiplication")
    assert [d.concept for d in context.dynamic.demonstrations] == ["Python", "Vector geometry"]


# 3. false inferred foundation is corrected during verification ---------------------------------

def test_false_inferred_foundation_is_corrected_before_verification(tmp_path: Path) -> None:
    _, _, api = _api(tmp_path, STRONG_FOUNDATION)
    learning = TopDownLearning(api)
    draft = learning.prepare(TARGET, TRANSFORMER_PREREQUISITES)
    stale_digest = draft.verification_digest
    revised = learning.revise(draft.context, foundation={"Backpropagation": "familiar"})
    item = next(i for i in revised.context.stable.foundation if i.concept == "Backpropagation")
    assert (item.level, item.basis) == ("familiar", "learner-stated")
    assert "Backpropagation" in revised.context.dynamic.path
    with pytest.raises(ContextError, match="top_down_verification_stale"):
        learning.verify(revised.context, stale_digest, "Yes, correct.")
    verified = learning.verify(revised.context, revised.verification_digest, "Yes, correct now.")
    assert is_verified(verified)


# 4. unrelated Profile/Memory never enters the learning context ----------------------------------

def test_unrelated_profile_and_memory_never_enter_the_context(tmp_path: Path) -> None:
    service, _, api = _api(tmp_path, (
        *STRONG_FOUNDATION, *UNRELATED, ("I prefer visual explanations with diagrams", "preferences"),
    ))
    learning = TopDownLearning(api)
    draft = learning.prepare(TARGET, TRANSFORMER_PREREQUISITES)
    context = _verified(learning, draft.context, "cloud")
    texts = draft.markdown + draft.summary + render_context(context) + export_cloud(context)
    for private in ("Example Street", "aisle", "ExampleBank", "4242", "marathon"):
        assert private not in texts
    _, records = service.snapshot()
    assert not [record_id for record_id in records.ids() if record_id in texts]
    assert context.stable.preferences == ("I prefer visual explanations with diagrams",)


# 5/6. preferences materially change teaching output --------------------------------------------

@pytest.mark.parametrize(
    ("preference", "present", "absent"),
    [
        ("I prefer visual explanations with diagrams", "Mermaid", "why it is needed"),
        ("I like first-principles learning: why before formulas", "why it is needed", "Mermaid"),
    ],
)
def test_preferences_change_the_teaching_contract(tmp_path: Path, preference: str, present: str, absent: str) -> None:
    _, _, api = _api(tmp_path, ((preference, "preferences"),))
    learning = TopDownLearning(api)
    context = _verified(learning, learning.prepare(TARGET, TRANSFORMER_PREREQUISITES).context)
    assert present in context.dynamic.teaching_contract and absent not in context.dynamic.teaching_contract
    assert present in context.dynamic.cloud_guidance


# 7/8. local state updates and required learner output -------------------------------------------

def test_local_progress_requires_learner_output_and_understood_diagnosis(tmp_path: Path) -> None:
    _, _, api = _api(tmp_path, STRONG_FOUNDATION)
    learning = TopDownLearning(api)
    context = _verified(learning, learning.prepare(TARGET, TRANSFORMER_PREREQUISITES).context)
    current = context.dynamic.position[-1]
    for output in ("", "   ", "ok"):
        with pytest.raises(ContextError, match="top_down_learner_output_required"):
            learning.record_progress(
                context, concept=current, diagnosis="understood", action="advance", learner_output=output, summary="s",
            )
    with pytest.raises(ContextError, match="top_down_understanding_required"):
        learning.record_progress(
            context, concept=current, diagnosis="partial", action="advance",
            learner_output="I think it normalizes something", summary="Partly right",
        )
    with pytest.raises(ContextError, match="top_down_not_current_concept"):
        learning.record_progress(
            context, concept="Positional encoding", diagnosis="understood", action="advance",
            learner_output="Sinusoids encode positions", summary="skip attempt",
        )
    updated = learning.record_progress(
        context, concept=current, diagnosis="misconception", action="reinforce",
        learner_output="Softmax picks the single largest value", summary="Treats softmax as argmax",
    )
    assert updated.dynamic.misconceptions[-1].concept == current
    assert updated.dynamic.position == context.dynamic.position
    advanced = learning.record_progress(
        updated, concept=current, diagnosis="understood", action="advance",
        learner_output="Softmax exponentiates and normalizes so weights are positive and sum to one",
        summary="Explained softmax normalization", next_step="Predict attention weights for two tokens.",
    )
    assert not [n for n in advanced.dynamic.misconceptions if n.concept == current]
    assert advanced.dynamic.next_step == "Predict attention weights for two tokens."
    assert parse_context(render_context(advanced)) == advanced


# 9-11. cloud export, bootstrap without Aptuni, refreshed checkpoint --------------------------------

def test_cloud_export_bootstraps_without_aptuni_and_checkpoint_resumes(tmp_path: Path) -> None:
    _, _, api = _api(tmp_path, (*STRONG_FOUNDATION, ("I prefer visual explanations with diagrams", "preferences")))
    learning = TopDownLearning(api)
    context = _verified(learning, learning.prepare(TARGET, TRANSFORMER_PREREQUISITES).context, "cloud")
    exported = export_cloud(context)
    exported_path = tmp_path / "top_down_learning_context.md"
    exported_path.write_text(exported, encoding="utf-8")
    script = (
        f"import sys; sys.modules['aptuni'] = None; sys.path.insert(0, {str(EXAMPLE_SRC)!r})\n"
        "from top_down_learning.context_parser import parse_context\n"
        "from top_down_learning.learning_context import is_verified\n"
        f"c = parse_context(open({str(exported_path)!r}, encoding='utf-8').read())\n"
        "print(is_verified(c), c.preferred_delivery, ' > '.join(c.dynamic.position))\n"
    )
    result = subprocess.run(
        [sys.executable, "-I", "-c", script], env=_minimal_env(),
        capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.startswith("True cloud Learn Transformers > ")

    current = context.dynamic.position[-1]
    refreshed = exported.replace(
        "# Open Gaps\n\n_None yet._", "# Open Gaps\n\n- Scaling by square root of key dimension",
    ).replace(f"Position: {TARGET} › {current}", f"Position: {TARGET} › Self-attention")
    status = learning.resume(refreshed)
    assert status.verified and status.position == (TARGET, "Self-attention")
    assert status.context.dynamic.gaps == ("Scaling by square root of key dimension",)

    tampered = refreshed.replace("- I prefer visual explanations with diagrams", "- I prefer long lectures")
    stale = learning.resume(tampered)
    assert not stale.verified and stale.stale_verification
    with pytest.raises(ContextError, match="top_down_verification_required"):
        learning.record_progress(
            stale.context, concept="Self-attention", diagnosis="understood", action="advance",
            learner_output="Queries match keys to weight values", summary="ok",
        )


def _minimal_env() -> dict[str, str]:
    return {key: os.environ[key] for key in ("PATH", "HOME") if key in os.environ}


# 12. stable vs dynamic ----------------------------------------------------------------------------

def test_dynamic_progress_keeps_verification_but_stable_edits_do_not(tmp_path: Path) -> None:
    _, _, api = _api(tmp_path, STRONG_FOUNDATION)
    learning = TopDownLearning(api)
    context = _verified(learning, learning.prepare(TARGET, TRANSFORMER_PREREQUISITES).context)
    progressed = learning.record_progress(
        context, concept=context.dynamic.position[-1], diagnosis="partial", action="reinforce",
        learner_output="It rescales the scores somehow", summary="Partial",
    )
    assert is_verified(progressed)
    revised = learning.revise(progressed, add_constraints=("Only weekends",))
    assert not is_verified(revised.context)
    assert revised.context.dynamic.demonstrations == progressed.dynamic.demonstrations


# 13/20. grants and privacy boundaries; delivery mode does not broaden authority --------------------

def test_revoked_grant_stops_retrieval_and_delivery_mode_needs_no_new_authority(tmp_path: Path) -> None:
    _, manager, api = _api(tmp_path, STRONG_FOUNDATION)
    learning = TopDownLearning(api)
    context = _verified(learning, learning.prepare(TARGET, TRANSFORMER_PREREQUISITES).context, "cloud")
    capabilities = api.grant.capabilities
    export_cloud(context)
    assert api.grant.capabilities == capabilities
    assert manager.revoke(api.grant.grant_id)
    with pytest.raises(AptuniAPIError) as revoked:
        learning.prepare(TARGET, TRANSFORMER_PREREQUISITES)
    assert revoked.value.code == "plugin_grant_not_found"
    assert export_cloud(context)


# 14. no silent promotion ----------------------------------------------------------------------------

def test_learning_journey_writes_nothing_canonical_without_explicit_proposal(tmp_path: Path) -> None:
    service, _, api = _api(tmp_path, STRONG_FOUNDATION)
    before, _ = service.snapshot()
    learning = TopDownLearning(api)
    context = _verified(learning, learning.prepare(TARGET, TRANSFORMER_PREREQUISITES).context)
    current = context.dynamic.position[-1]
    context = learning.record_progress(
        context, concept=current, diagnosis="understood", action="advance",
        learner_output="Softmax normalizes scores into positive weights summing to one", summary="Explained",
    )
    after, _ = service.snapshot()
    assert after == before
    with pytest.raises(ContextError, match="top_down_evidence_insufficient"):
        learning.propose_memory(context, "demonstrated_understanding", current)
    gap = learning.propose_memory(
        learning.record_progress(
            context, concept=context.dynamic.position[-1], diagnosis="misconception", action="reinforce",
            learner_output="Attention picks one token only", summary="Treats attention as hard selection",
        ),
        "learning_gap", context.dynamic.position[-1],
    )
    assert gap.status == "pending_owner_review"


def test_explicit_proposal_fails_closed_when_optional_capability_is_withheld(tmp_path: Path) -> None:
    _, _, api = _api(
        tmp_path, (("I prefer visual explanations with diagrams", "preferences"),), capabilities=("context.read",),
    )
    learning = TopDownLearning(api)
    context = _verified(learning, learning.prepare(TARGET, TRANSFORMER_PREREQUISITES).context)
    with pytest.raises(AptuniAPIError) as denied:
        learning.propose_memory(context, "teaching_preference", "I prefer visual explanations with diagrams")
    assert denied.value.code == "plugin_capability_denied"


# 17. bounded input -----------------------------------------------------------------------------------

def test_maximum_and_oversized_inputs_are_bounded(tmp_path: Path) -> None:
    _, _, api = _api(tmp_path, ())
    learning = TopDownLearning(api)
    specs = tuple(PrerequisiteSpec("概" * 80, ("学" * 40,), "目" * 80) for _ in range(1))
    draft = learning.prepare("学" * 500, specs, success_criteria=("成" * 300,))
    assert parse_context(draft.markdown).stable.target == "学" * 500
    with pytest.raises(ContextError):
        learning.prepare("x" * 501, TRANSFORMER_PREREQUISITES)
    with pytest.raises(ContextError):
        learning.prepare(TARGET, TRANSFORMER_PREREQUISITES * 3)
    with pytest.raises(ContextError):
        learning.resume("x" * 70000)


def test_agent_supplied_private_text_is_redacted_on_input(tmp_path: Path) -> None:
    _, _, api = _api(tmp_path, ())
    draft = TopDownLearning(api).prepare(
        TARGET, TRANSFORMER_PREREQUISITES, constraints=("Code lives in /Users/alice/secret-repo",),
    )
    assert "/Users/alice" not in draft.markdown and "[redacted]" in draft.markdown


# 19. verification gate cannot be skipped or forged ----------------------------------------------------

def test_verification_gate_cannot_be_skipped_or_forged(tmp_path: Path) -> None:
    _, _, api = _api(tmp_path, STRONG_FOUNDATION)
    learning = TopDownLearning(api)
    draft = learning.prepare(TARGET, TRANSFORMER_PREREQUISITES)
    with pytest.raises(ContextError, match="top_down_verification_required"):
        learning.choose_delivery(draft.context, "local", "strategy")
    with pytest.raises(ContextError, match="top_down_verification_required"):
        export_cloud(draft.context)
    for reply in ("No, I have never trained a network", "Yes, but add that I know CUDA", "", "maybe"):
        with pytest.raises(ContextError, match="top_down_confirmation_required"):
            learning.verify(draft.context, draft.verification_digest, reply)
    flipped = draft.markdown.replace("user_verified: false", "user_verified: true")
    with pytest.raises(ContextError, match="top_down_verification_required"):
        learning.choose_delivery(learning.resume(flipped).context, "local", "strategy")
    with pytest.raises(ContextError, match="top_down_verification_stale"):
        learning.verify(draft.context, "sha256:" + "0" * 64, "Yes")
    assert is_verified(learning.verify(draft.context, draft.verification_digest, "是的，没错"))


def test_verification_record_contains_no_raw_confirmation_text(tmp_path: Path) -> None:
    _, _, api = _api(tmp_path, STRONG_FOUNDATION)
    learning = TopDownLearning(api)
    draft = learning.prepare(TARGET, TRANSFORMER_PREREQUISITES)
    verified = learning.verify(draft.context, draft.verification_digest, "Yes, correct — secret phrase 991")
    assert "991" not in render_context(verified)
    assert replace(verified, last_verification=None).user_verified


def test_workflow_imports_only_the_public_api() -> None:
    import ast

    for path in sorted((EXAMPLE_SRC / "top_down_learning").glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        modules = [node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)]
        assert not [m for m in modules if m and m.startswith("aptuni") and m != "aptuni.api.v1"], path


def test_type_contract_accepts_the_public_api_object(tmp_path: Path) -> None:
    _, _, api = _api(tmp_path, ())
    assert isinstance(TopDownLearning(api).api, AptuniAPI)


def test_cloud_guidance_tracks_the_current_position_after_progress(tmp_path: Path) -> None:
    _, _, api = _api(tmp_path, STRONG_FOUNDATION)
    learning = TopDownLearning(api)
    context = _verified(learning, learning.prepare(TARGET, TRANSFORMER_PREREQUISITES).context)
    first = context.dynamic.position[-1]
    advanced = learning.record_progress(
        context, concept=first, diagnosis="understood", action="advance",
        learner_output="Softmax turns scores into positive weights that sum to one", summary="Explained",
    )
    current = advanced.dynamic.position[-1]
    assert current != first
    assert f"› {current})" in advanced.dynamic.cloud_guidance


def test_cloud_guidance_tracks_corrected_strong_foundation(tmp_path: Path) -> None:
    _, _, api = _api(tmp_path, STRONG_FOUNDATION)
    learning = TopDownLearning(api)
    context = _verified(learning, learning.prepare(TARGET, TRANSFORMER_PREREQUISITES).context)
    revised = learning.revise(context, foundation={"Softmax": "strong"}).context
    assert "Softmax" in revised.dynamic.cloud_guidance.split("Do not re-teach", 1)[1].split("\n", 1)[0]


def test_committed_flagship_demo_contexts_are_valid_verified_and_private() -> None:
    demo = EXAMPLE_SRC.parent / "examples"
    local = parse_context((demo / "transformer_local_context.md").read_text(encoding="utf-8"))
    cloud_text = (demo / "transformer_cloud_context.md").read_text(encoding="utf-8")
    cloud = parse_context(cloud_text)
    assert is_verified(local) and is_verified(cloud)
    assert (local.preferred_delivery, cloud.preferred_delivery) == ("local", "cloud")
    assert cloud.dynamic.position == local.dynamic.position
    assert "aisle" not in cloud_text and "/Users/" not in cloud_text
    assert "local HTML" in local.dynamic.teaching_contract
    assert "local HTML" not in cloud.dynamic.teaching_contract and "Mermaid" in cloud.dynamic.teaching_contract


# --- Review 74 remediation ------------------------------------------------------------------

@pytest.mark.parametrize(
    "preference",
    [
        "I like working on projects with my therapist on Tuesdays",
        "I like to practice yoga before my physiotherapy sessions for my back injury",
        "我喜欢去图书馆",
        "I prefer to build furniture on weekends",
        "I prefer my doctor to explain my diagnosis in person",
        "I study at the oncology ward waiting room",
        "I prefer piano lessons with my daughter on Saturdays",
        "我喜欢在医院候诊时学习",
    ],
)
def test_generic_cue_words_do_not_admit_unrelated_preferences(tmp_path: Path, preference: str) -> None:
    _, _, api = _api(tmp_path, (*STRONG_FOUNDATION, (preference, "preferences"),
                                ("I prefer visual explanations with diagrams", "preferences")))
    learning = TopDownLearning(api)
    draft = learning.prepare(TARGET, TRANSFORMER_PREREQUISITES)
    assert draft.context.stable.preferences == ("I prefer visual explanations with diagrams",)
    exported = export_cloud(_verified(learning, draft.context, "cloud"))
    assert preference not in exported


def test_agent_text_with_separators_round_trips_through_the_tool_path(tmp_path: Path) -> None:
    _, _, api = _api(tmp_path, STRONG_FOUNDATION)
    learning = TopDownLearning(api)
    draft = learning.prepare("Transformers › attention", TRANSFORMER_PREREQUISITES)
    assert parse_context(draft.markdown) == draft.context
    context = _verified(learning, draft.context)
    current = context.dynamic.position[-1]
    for diagnosis, action in (("misconception", "reinforce"), ("understood", "advance")):
        context = learning.record_progress(
            context, concept=current, diagnosis=diagnosis, action=action,  # type: ignore[arg-type]
            learner_output="Softmax exponentiates and normalizes the scores", summary="explained Q/K/V — correctly",
        )
        assert parse_context(render_context(context)) == context
    with pytest.raises(ContextError):
        learning.prepare("_None yet._", TRANSFORMER_PREREQUISITES)


def test_demonstrated_understanding_needs_two_distinct_recorded_checks(tmp_path: Path) -> None:
    _, _, api = _api(tmp_path, STRONG_FOUNDATION)
    learning = TopDownLearning(api, clock=lambda: "2026-09-27T10:00:00Z")
    context = _verified(learning, learning.prepare(TARGET, TRANSFORMER_PREREQUISITES).context)
    current = context.dynamic.position[-1]
    for _ in range(2):
        context = learning.record_progress(
            context, concept=current, diagnosis="understood", action="reinforce",
            learner_output="Softmax exponentiates and normalizes the scores", summary="Explained",
        )
    doubled = replace(context, dynamic=replace(context.dynamic, demonstrations=(
        *context.dynamic.demonstrations,
        *(replace(d, concept=current) for d in context.dynamic.demonstrations),
    )))
    with pytest.raises(ContextError, match="top_down_evidence_insufficient"):
        learning.propose_memory(doubled, "demonstrated_understanding", current)
