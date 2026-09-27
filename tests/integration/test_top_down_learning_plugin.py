from __future__ import annotations

import ast
import importlib.util
import sys
from pathlib import Path

import pytest

from aptuni.api.v1 import AptuniAPIError, connect, load_manifest, scaffold_plugin
from aptuni.api.v1.grants import PluginGrantManager
from aptuni.application.service import AptuniService
from aptuni.application.workspace import Workspace

ROOT = Path(__file__).parents[2]
EXAMPLE = ROOT / "examples" / "plugins" / "top_down_learning"
_SPEC = importlib.util.spec_from_file_location("top_down_learning_example", EXAMPLE / "plugin.py")
assert _SPEC is not None and _SPEC.loader is not None
_MODULE = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = _MODULE
_SPEC.loader.exec_module(_MODULE)
TopDownLearningPlugin = _MODULE.TopDownLearningPlugin


def _ready(tmp_path: Path):
    workspace = Workspace(tmp_path / "state")
    service = AptuniService(workspace)
    service.init(tmp_path / "vault")
    service.remember("My goal is to build an intelligent parking system", "goals")
    service.remember("I have practical Python experience", "skills")
    service.remember("I prefer concise project-first explanations", "preferences")
    manifest = load_manifest(EXAMPLE / "aptuni-plugin.toml")
    manager = PluginGrantManager(workspace)
    grant = manager.apply(manager.plan(manifest).action_id)
    return service, connect(manifest, grant.grant_id, workspace=workspace)


def test_manifest_declares_context_dependency_and_optional_gap_capture() -> None:
    manifest = load_manifest(EXAMPLE / "aptuni-plugin.toml")
    assert manifest.required_capabilities == ("context.read",)
    assert manifest.optional_capabilities == ("memory.propose",)


def test_complete_personalized_learning_loop_uses_only_public_api(tmp_path: Path) -> None:
    _, api = _ready(tmp_path)
    plugin = TopDownLearningPlugin(api)
    session = plugin.start("Build an intelligent parking system")
    assert session.goal == "Build an intelligent parking system"
    assert session.prerequisites[0].status == "known"
    assert session.prerequisites[0].canonical_ids
    assert session.prerequisites[1].status == "needed"
    assert session.current_slug == "camera_geometry"
    assert "project-first" in session.teaching_preference.lower()

    turn = plugin.teach(session)
    assert turn.prerequisite_slug == "camera_geometry"
    assert turn.explanation and turn.project_step and turn.learner_prompt
    assert turn.delivery_style == "concise_project_first"
    weak = plugin.check(session, "A camera sends images.")
    assert not weak.passed and weak.next_slug == "camera_geometry"
    passed = plugin.check(session, "Perspective distortion can be corrected with a homography.")
    assert passed.passed and passed.next_slug == "vehicle_detection"


def test_gap_submission_is_explicit_quarantined_and_idempotent(tmp_path: Path) -> None:
    _, api = _ready(tmp_path)
    plugin = TopDownLearningPlugin(api)
    session = plugin.start("Build an intelligent parking system")
    first = plugin.record_gap(session, "I need more practice explaining homography.")
    second = plugin.record_gap(session, "I need more practice explaining homography.")
    assert first.status == "pending_owner_review"
    assert first.candidate_id == second.candidate_id
    assert first.created and not second.created


def test_learning_journey_works_when_optional_gap_capture_is_not_granted(tmp_path: Path) -> None:
    workspace = Workspace(tmp_path / "state")
    service = AptuniService(workspace)
    service.init(tmp_path / "vault")
    service.remember("I have practical Python experience", "skills")
    manifest = load_manifest(EXAMPLE / "aptuni-plugin.toml")
    manager = PluginGrantManager(workspace)
    grant = manager.apply(manager.plan(
        manifest,
        capabilities=("context.read",),
        modules=("knowledge", "skills", "preferences"),
    ).action_id)
    plugin = TopDownLearningPlugin(connect(manifest, grant.grant_id, workspace=workspace))
    session = plugin.start("Build an intelligent parking system")
    assert session.prerequisites[0].status == "known"
    with pytest.raises(AptuniAPIError) as denied:
        plugin.record_gap(session, "I need more practice explaining homography.")
    assert denied.value.code == "plugin_capability_denied"


def test_long_goal_gap_keys_preserve_distinct_feedback(tmp_path: Path) -> None:
    _, api = _ready(tmp_path)
    plugin = TopDownLearningPlugin(api)
    session = plugin.start("Build an intelligent parking system " + "safely " * 40)
    first = plugin.record_gap(session, "I need practice explaining homography.")
    second = plugin.record_gap(session, "I need practice applying homography.")
    assert first.candidate_id != second.candidate_id


def test_goal_mentions_and_negated_skills_do_not_prove_a_foundation(tmp_path: Path) -> None:
    workspace = Workspace(tmp_path / "state")
    service = AptuniService(workspace)
    service.init(tmp_path / "vault")
    service.remember("My goal is to build the intelligent parking system in Python", "goals")
    service.remember("I do not know Python yet", "skills")
    manifest = load_manifest(EXAMPLE / "aptuni-plugin.toml")
    manager = PluginGrantManager(workspace)
    grant = manager.apply(manager.plan(manifest).action_id)
    session = TopDownLearningPlugin(connect(manifest, grant.grant_id, workspace=workspace)).start(
        "Build an intelligent parking system",
    )
    assert session.prerequisites[0].status == "needed"


def test_example_has_no_internal_aptuni_imports() -> None:
    tree = ast.parse((EXAMPLE / "plugin.py").read_text(encoding="utf-8"))
    imported = [node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)]
    assert imported == ["__future__", "dataclasses", "typing", "aptuni.api.v1"]


def test_scaffold_is_public_only_and_creates_no_grant(tmp_path: Path) -> None:
    target = tmp_path / "plugin"
    files = scaffold_plugin(target, plugin_id="dev.example.study_coach", name="Study Coach")
    assert {path.relative_to(target).as_posix() for path in files} == {
        "README.md", "aptuni-plugin.toml", "pyproject.toml", "src/study_coach/__init__.py",
        "src/study_coach/plugin.py", "tests/test_plugin.py",
    }
    assert load_manifest(target / "aptuni-plugin.toml").id == "dev.example.study_coach"
    assert "from aptuni.api.v1 import AptuniAPI" in (target / "src/study_coach/plugin.py").read_text()
    assert not (tmp_path / "state").exists()


def test_scaffold_quotes_untrusted_display_name_as_toml_data(tmp_path: Path) -> None:
    target = tmp_path / "quoted"
    name = 'Coach"\ninjected = true'
    scaffold_plugin(target, plugin_id="dev.example.quoted", name=name)
    manifest = load_manifest(target / "aptuni-plugin.toml")
    assert manifest.name == name
