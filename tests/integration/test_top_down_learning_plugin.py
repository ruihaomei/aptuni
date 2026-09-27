from __future__ import annotations

import ast
import json
import subprocess
import sys
from pathlib import Path

import anyio
import pytest
from mcp import Client, StdioServerParameters
from mcp.server.mcpserver.exceptions import ToolError

from aptuni.api.v1 import AptuniAPIError, connect, load_manifest, scaffold_plugin
from aptuni.api.v1.grants import PluginGrantManager
from aptuni.application.service import AptuniService
from aptuni.application.workspace import Workspace

ROOT = Path(__file__).parents[2]
EXAMPLE = ROOT / "examples" / "plugins" / "top_down_learning"
MANIFEST = EXAMPLE / "src" / "top_down_learning" / "aptuni-plugin.toml"
sys.path.insert(0, str(EXAMPLE / "src"))
from top_down_learning.plugin import TopDownLearningPlugin  # noqa: E402


def _ready(tmp_path: Path):
    workspace = Workspace(tmp_path / "state")
    service = AptuniService(workspace)
    service.init(tmp_path / "vault")
    service.remember("My goal is to build an intelligent parking system", "goals")
    service.remember("I have practical Python experience", "skills")
    service.remember("I prefer concise project-first explanations", "preferences")
    manifest = load_manifest(MANIFEST)
    manager = PluginGrantManager(workspace)
    grant = manager.apply(manager.plan(manifest).action_id)
    return service, connect(manifest, grant.grant_id, workspace=workspace)


def test_manifest_declares_context_dependency_and_optional_gap_capture() -> None:
    manifest = load_manifest(MANIFEST)
    assert manifest.required_capabilities == ("context.read",)
    assert manifest.optional_capabilities == ("memory.propose",)


def test_agent_plugin_assets_are_manual_only_and_reference_real_surfaces() -> None:
    codex = json.loads((EXAMPLE / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8"))
    claude = json.loads((EXAMPLE / "claude" / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
    mcp = json.loads((EXAMPLE / ".mcp.json").read_text(encoding="utf-8"))
    skill = (EXAMPLE / "skills" / "top-down-study" / "SKILL.md").read_text(encoding="utf-8")
    metadata = (EXAMPLE / "skills" / "top-down-study" / "agents" / "openai.yaml").read_text(encoding="utf-8")

    assert codex["skills"] == "./skills/" and codex["mcpServers"] == "./.mcp.json"
    assert claude["name"] == "top-down-learning"
    assert mcp["mcpServers"]["top_down_study"]["command"] == "top-down-study-mcp"
    claude_skill = (EXAMPLE / "claude" / "skills" / "top-down-study" / "SKILL.md").read_text(encoding="utf-8")
    assert "name: top-down-study" in skill
    assert "disable-model-invocation: true" in claude_skill and "user-invocable: true" in claude_skill
    assert "allow_implicit_invocation: false" in metadata
    assert "top_down_start" in skill and "top_down_check" in skill
    assert skill.split("---", 2)[2] == claude_skill.split("---", 2)[2]


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


def test_manual_agent_plugin_start_check_and_live_revoke(tmp_path: Path) -> None:
    from top_down_learning.mcp_server import create_server

    service, api = _ready(tmp_path)
    manager = PluginGrantManager(service.workspace)
    server = create_server(api)

    async def exercise() -> None:
        started = await server.call_tool(
            "top_down_start", {"goal": "Build an intelligent parking system"},
        )
        payload = started.structured_content
        assert payload["session"]["current_slug"] == "camera_geometry"
        assert payload["session"]["completed_slugs"] == []
        assert payload["session"]["remaining_count"] == 5
        assert "prerequisites" not in payload["session"]
        assert "teaching_preference" not in payload["session"]
        assert payload["continuation"]
        assert payload["turn"]["learner_prompt"]

        weak = await server.call_tool(
            "top_down_check",
            {
                "continuation": payload["continuation"],
                "learner_output": "A camera sends images.",
            },
        )
        assert weak.structured_content["check"]["passed"] is False
        assert weak.structured_content["session"]["current_slug"] == "camera_geometry"

        passed = await server.call_tool(
            "top_down_check",
            {
                "continuation": weak.structured_content["continuation"],
                "learner_output": "Perspective distortion is corrected with a homography.",
            },
        )
        assert passed.structured_content["check"]["passed"] is True
        assert passed.structured_content["session"]["completed_slugs"] == ["camera_geometry"]
        assert passed.structured_content["session"]["current_slug"] == "vehicle_detection"

        assert manager.revoke(api.grant.grant_id)
        with pytest.raises(ToolError, match="plugin_grant_not_found"):
            await server.call_tool(
                "top_down_start", {"goal": "Build an intelligent parking system"},
            )

    anyio.run(exercise)


def test_progress_cannot_forge_a_valid_completed_prefix(tmp_path: Path) -> None:
    from top_down_learning.mcp_server import create_server

    _, api = _ready(tmp_path)
    server = create_server(api)

    async def exercise() -> None:
        with pytest.raises(ToolError, match="top_down_progress_invalid"):
            await server.call_tool(
                "top_down_check",
                {
                    "continuation": "camera_geometry".ljust(40, "x"),
                    "learner_output": "Bounding boxes are observations, not occupancy.",
                },
            )

    anyio.run(exercise)


def test_maximum_multibyte_goal_continuation_round_trips(tmp_path: Path) -> None:
    from top_down_learning.mcp_server import create_server

    _, api = _ready(tmp_path)
    server = create_server(api)

    async def exercise() -> None:
        started = await server.call_tool("top_down_start", {"goal": "学" * 500})
        checked = await server.call_tool(
            "top_down_check",
            {
                "continuation": started.structured_content["continuation"],
                "learner_output": "A camera sends images.",
            },
        )
        assert checked.structured_content["session"]["current_slug"] == "camera_geometry"

    anyio.run(exercise)


def test_real_plugin_stdio_entrypoint_uses_the_exact_configured_grant(tmp_path: Path) -> None:
    service, api = _ready(tmp_path)

    async def exercise() -> None:
        params = StdioServerParameters(
            command=sys.executable,
            args=["-m", "top_down_learning.mcp_server"],
            env={
                "APTUNI_STATE_DIR": str(service.workspace.state_dir),
                "APTUNI_TOP_DOWN_GRANT_ID": api.grant.grant_id,
                "PYTHONPATH": str(EXAMPLE / "src"),
            },
        )
        async with Client(params) as client:
            tools = await client.list_tools()
            assert [tool.name for tool in tools.tools] == [
                "top_down_start", "top_down_check", "top_down_record_gap",
            ]
            started = await client.call_tool(
                "top_down_start", {"goal": "Build an intelligent parking system"},
            )
            assert not started.is_error
            assert started.structured_content["session"]["current_slug"] == "camera_geometry"

    anyio.run(exercise)

    missing = subprocess.run(
        [sys.executable, "-m", "top_down_learning.mcp_server"],
        env={"PYTHONPATH": str(EXAMPLE / "src")},
        capture_output=True,
        text=True,
        check=False,
    )
    assert missing.returncode != 0 and "top_down_grant_required" in missing.stderr


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
    manifest = load_manifest(MANIFEST)
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
    manifest = load_manifest(MANIFEST)
    manager = PluginGrantManager(workspace)
    grant = manager.apply(manager.plan(manifest).action_id)
    session = TopDownLearningPlugin(connect(manifest, grant.grant_id, workspace=workspace)).start(
        "Build an intelligent parking system",
    )
    assert session.prerequisites[0].status == "needed"


def test_example_has_no_internal_aptuni_imports() -> None:
    imported: list[str | None] = []
    for path in sorted((EXAMPLE / "src" / "top_down_learning").glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imported.extend(node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom))
    assert not [module for module in imported if module and module.startswith("aptuni.") and module != "aptuni.api.v1"]


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
