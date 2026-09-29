from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import anyio
import pytest
from mcp import Client, StdioServerParameters
from mcp.server.mcpserver.exceptions import ToolError

from aptuni.api.v1 import connect, load_manifest, scaffold_plugin
from aptuni.api.v1.grants import PluginGrantManager
from aptuni.application.service import AptuniService
from aptuni.application.workspace import Workspace

ROOT = Path(__file__).parents[2]
TOOLS = (
    "top_down_prepare", "top_down_revise", "top_down_verify", "top_down_choose_delivery",
    "top_down_record_progress", "top_down_resume", "top_down_export_cloud", "top_down_propose_memory",
)
EXAMPLE = ROOT / "examples" / "plugins" / "top_down_learning"
MANIFEST = EXAMPLE / "src" / "top_down_learning" / "aptuni-plugin.toml"
sys.path.insert(0, str(EXAMPLE / "src"))
from top_down_learning.context_parser import parse_context  # noqa: E402
from top_down_learning.demo_maps import TRANSFORMER_PREREQUISITES  # noqa: E402


def _ready(tmp_path: Path):
    workspace = Workspace(tmp_path / "state")
    service = AptuniService(workspace)
    service.init(tmp_path / "vault")
    service.remember("My goal is to understand modern LLM papers", "goals")
    service.remember("I have practical Python experience", "skills")
    service.remember("I write Python services every day", "skills")
    service.remember("I prefer visual explanations with diagrams", "preferences")
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
    for tool in TOOLS:
        assert tool in skill, tool
    assert "top_down_learning_context.md" in skill
    assert skill.split("---", 2)[2] == claude_skill.split("---", 2)[2]


PREREQUISITES = [
    {"concept": spec.concept, "evidence_terms": list(spec.evidence_terms), "required_for": spec.required_for}
    for spec in TRANSFORMER_PREREQUISITES
]


async def _journey(call) -> dict[str, object]:
    """The first-run flagship journey shared by the in-process and STDIO host tests."""
    prepared = (await call("top_down_prepare", {
        "target": "Learn Transformers", "prerequisites": PREREQUISITES,
        "deliverable": "A runnable single-head attention notebook",
    })).structured_content
    assert prepared["user_verified"] is False and "Python (aptuni-inferred)" in prepared["verification_summary"]
    assert "Softmax" in prepared["clarify"]
    revised = (await call("top_down_revise", {
        "context_markdown": prepared["context_markdown"], "foundation": {"Softmax": "familiar"},
    })).structured_content
    verified = (await call("top_down_verify", {
        "context_markdown": revised["context_markdown"],
        "verification_digest": revised["verification_digest"],
        "learner_confirmation": "Yes, that's accurate.",
    })).structured_content
    chosen = (await call("top_down_choose_delivery", {
        "context_markdown": verified["context_markdown"], "mode": "local",
        "teaching_strategy": "Diagram first, then a two-token numeric example the learner predicts.",
    })).structured_content
    progressed = (await call("top_down_record_progress", {
        "context_markdown": chosen["context_markdown"], "concept": "Matrix multiplication",
        "diagnosis": "partial", "action": "descend", "prerequisite": "Dot product",
        "learner_output": "You multiply matching numbers?", "summary": "Unsure how rows meet columns",
    })).structured_content
    assert progressed["position"] == ["Learn Transformers", "Matrix multiplication", "Dot product"]
    return progressed


def test_manual_agent_plugin_first_run_journey_and_live_revoke(tmp_path: Path) -> None:
    from top_down_learning.mcp_server import create_server

    service, api = _ready(tmp_path)
    manager = PluginGrantManager(service.workspace)
    server = create_server(api)

    async def exercise() -> None:
        progressed = await _journey(server.call_tool)
        context = parse_context(progressed["context_markdown"])
        assert context.preferred_delivery == "local" and "Mermaid" in context.dynamic.teaching_contract
        exported = (await server.call_tool("top_down_export_cloud", {
            "context_markdown": progressed["context_markdown"],
        })).structured_content["cloud_context_markdown"]
        resumed = (await server.call_tool("top_down_resume", {"context_markdown": exported})).structured_content
        assert resumed["user_verified"] is True and resumed["delivery"] == "cloud"

        assert manager.revoke(api.grant.grant_id)
        with pytest.raises(ToolError, match="plugin_grant_not_found"):
            await server.call_tool("top_down_prepare", {"target": "Learn Transformers", "prerequisites": PREREQUISITES})
        still = await server.call_tool("top_down_resume", {"context_markdown": exported})
        assert still.structured_content["position"] == resumed["position"]

    anyio.run(exercise)


def test_tools_reject_unverified_or_malformed_context_clearly(tmp_path: Path) -> None:
    from top_down_learning.mcp_server import create_server

    _, api = _ready(tmp_path)
    server = create_server(api)

    async def exercise() -> None:
        prepared = (await server.call_tool("top_down_prepare", {
            "target": "Learn Transformers", "prerequisites": PREREQUISITES,
        })).structured_content
        with pytest.raises(ToolError, match="top_down_verification_required"):
            await server.call_tool("top_down_choose_delivery", {
                "context_markdown": prepared["context_markdown"].replace("user_verified: false", "user_verified: true"),
                "mode": "cloud", "teaching_strategy": "skip verification",
            })
        with pytest.raises(ToolError, match="top_down_context_invalid"):
            await server.call_tool("top_down_resume", {"context_markdown": "# not a context"})
        with pytest.raises(ToolError):
            await server.call_tool("top_down_resume", {"context_markdown": "x" * 70000})

    anyio.run(exercise)


def test_real_plugin_stdio_entrypoint_runs_the_journey_with_the_exact_grant(tmp_path: Path) -> None:
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
            assert tuple(tool.name for tool in tools.tools) == TOOLS

            async def call(name: str, arguments: dict[str, object]):
                result = await client.call_tool(name, arguments)
                assert not result.is_error, result
                return result

            await _journey(call)

    anyio.run(exercise)

    missing = subprocess.run(
        [sys.executable, "-m", "top_down_learning.mcp_server"],
        env={
            "APTUNI_STATE_DIR": str(tmp_path / "no-grant-state"),
            "PYTHONPATH": str(EXAMPLE / "src"),
        },
        capture_output=True,
        text=True,
        check=False,
    )
    assert missing.returncode != 0 and "top_down_grant_required" in missing.stderr


def test_host_bundles_share_one_server_and_one_workflow_body() -> None:
    codex_mcp = json.loads((EXAMPLE / ".mcp.json").read_text(encoding="utf-8"))
    claude_mcp = json.loads((EXAMPLE / "claude" / ".mcp.json").read_text(encoding="utf-8"))
    assert codex_mcp == claude_mcp
    server = codex_mcp["mcpServers"]["top_down_study"]
    assert server["env_vars"] == ["APTUNI_STATE_DIR", "APTUNI_TOP_DOWN_GRANT_ID"]
    codex = (EXAMPLE / "skills" / "top-down-study" / "SKILL.md").read_text(encoding="utf-8")
    claude = (EXAMPLE / "claude" / "skills" / "top-down-study" / "SKILL.md").read_text(encoding="utf-8")
    assert codex.split("---", 2)[2] == claude.split("---", 2)[2]
    assert "No separate Aptuni Profile, Memory or Full activation" in codex


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


def test_plugin_distribution_declares_apache_license_and_ships_legal_files() -> None:
    import tomllib

    project = tomllib.loads((EXAMPLE / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    assert project["license"] == "Apache-2.0"
    assert project["license-files"] == ["LICENSE", "NOTICE"]
    for name in ("LICENSE", "NOTICE"):
        assert (EXAMPLE / name).read_bytes() == (ROOT / name).read_bytes()


def test_host_manifests_and_server_report_the_package_version() -> None:
    import tomllib

    version = tomllib.loads((EXAMPLE / "pyproject.toml").read_text(encoding="utf-8"))["project"]["version"]
    assert load_manifest(MANIFEST).version == version
    for path in (EXAMPLE / ".codex-plugin" / "plugin.json", EXAMPLE / "claude" / ".claude-plugin" / "plugin.json"):
        assert json.loads(path.read_text(encoding="utf-8"))["version"] == version
    assert f'version="{version}"' in (EXAMPLE / "src" / "top_down_learning" / "mcp_server.py").read_text()


def _grant_row(grant_id: str, digest: str, created_at: str, plugin_id: str = "dev.aptuni.top_down_learning") -> dict:
    return {"grant_id": grant_id, "plugin_id": plugin_id, "manifest_digest": digest, "created_at": created_at}


def test_plugin_picks_its_own_newest_matching_grant_without_an_environment_variable() -> None:
    from top_down_learning.grant_lookup import GrantLookupError, resolve_grant_id

    manifest = load_manifest(MANIFEST)
    digest = manifest.digest()
    rows = [
        _grant_row("grant-old", digest, "2026-09-28T10:00:00Z"),
        _grant_row("grant-new", digest, "2026-09-28T11:00:00Z"),
        _grant_row("grant-stale", "sha256:" + "0" * 64, "2026-09-28T12:00:00Z"),
        _grant_row("grant-other", digest, "2026-09-28T13:00:00Z", plugin_id="dev.example.other"),
    ]
    assert resolve_grant_id(manifest, {}, lambda: rows) == "grant-new"
    assert resolve_grant_id(manifest, {"APTUNI_TOP_DOWN_GRANT_ID": "grant-pinned"}, lambda: rows) == "grant-pinned"
    with pytest.raises(GrantLookupError) as error:
        resolve_grant_id(manifest, {}, lambda: rows[2:])
    assert "aptuni developer grant plan" in str(error.value)


def test_real_stdio_server_finds_the_owner_grant_on_its_own(tmp_path: Path) -> None:
    service, _ = _ready(tmp_path)

    async def exercise() -> None:
        params = StdioServerParameters(
            command=sys.executable,
            args=["-m", "top_down_learning.mcp_server"],
            env={"APTUNI_STATE_DIR": str(service.workspace.state_dir), "PYTHONPATH": str(EXAMPLE / "src"),
                 "HOME": str(tmp_path)},
        )
        async with Client(params) as client:
            tools = await client.list_tools()
            assert tuple(tool.name for tool in tools.tools) == TOOLS

    anyio.run(exercise)
