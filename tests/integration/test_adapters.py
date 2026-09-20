"""Claude/Codex adapter grant, bundle, cancellation, and MCP integration tests."""

from __future__ import annotations

import json
import os
from pathlib import Path

import anyio
import pytest
from mcp import Client, StdioServerParameters

from aptuni.adapters.manager import AdapterManager
from aptuni.application.errors import AptuniError
from aptuni.application.service import AptuniService
from aptuni.application.workspace import Workspace
from aptuni.cli.main import run


def _ready(tmp_path: Path) -> tuple[Workspace, AptuniService, AdapterManager]:
    workspace = Workspace(tmp_path / "state")
    service = AptuniService(workspace)
    service.init(tmp_path / "vault")
    service.remember("Prefers concise answers", "identity")
    return workspace, service, AdapterManager(workspace)


@pytest.mark.parametrize("host", ["claude", "codex"])
def test_plan_apply_generates_deterministic_private_grant_and_bundle(tmp_path: Path, host: str) -> None:
    _, _, manager = _ready(tmp_path)
    with pytest.raises(AptuniError, match="informed host-model egress consent"):
        manager.plan(host, ("identity",), allow_host_model_egress=False)
    plan = manager.plan(host, ("identity", "knowledge", "identity"), allow_host_model_egress=True)
    assert "externally controlled" in manager.preview(plan)
    grant, bundle = manager.apply(plan.action_id)
    assert grant.host_class == "remote_unknown"
    assert grant.modules == ("identity", "knowledge")
    assert (manager.root / "grants" / f"{grant.grant_id}.json").stat().st_mode & 0o777 == 0o600
    again, again_bundle = manager.apply(plan.action_id)
    assert (again, again_bundle) == (grant, bundle)
    if host == "claude":
        config = json.loads((bundle / ".mcp.json").read_text())
        assert config["mcpServers"]["aptuni"]["args"][-1] == grant.grant_id
        hooks = json.loads((bundle / "hooks.json").read_text())
        assert "SessionStart" in hooks["hooks"]
    else:
        codex_config = (bundle / "config.toml").read_text()
        assert grant.grant_id in codex_config
        assert 'env_vars = ["APTUNI_STATE_DIR"]' in codex_config
        assert "required = true" in codex_config
        assert "quoted data" in (bundle / "AGENTS.md").read_text()


def test_cli_cancel_creates_no_grant_or_bundle(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _, service, manager = _ready(tmp_path)
    plan = manager.plan("claude", ("identity",), allow_host_model_egress=True)
    monkeypatch.setattr("builtins.input", lambda _: "NO")
    assert run(["adapter", "apply", plan.action_id], service) == 1
    assert not (manager.root / "grants").exists()
    assert not (manager.root / "bundles").exists()


def test_memory_proposal_scope_is_explicit_and_digest_bound(tmp_path: Path) -> None:
    _, _, manager = _ready(tmp_path)
    default = manager.plan("codex", ("preferences",), allow_host_model_egress=True)
    enabled = manager.plan("codex", ("preferences",), allow_host_model_egress=True,
                           allow_memory_proposals=True)
    assert "memory.propose" not in default.scopes
    assert "memory.propose" in enabled.scopes
    assert default.action_id != enabled.action_id and default.digest != enabled.digest
    assert "stay hidden until you accept" in manager.preview(enabled)
    grant, _ = manager.apply(enabled.action_id)
    assert "memory.propose" in manager.load_grant(grant.grant_id).scopes


def test_exact_ids_only_and_grant_drives_real_stdio(tmp_path: Path) -> None:
    workspace, _, manager = _ready(tmp_path)
    plan = manager.plan("codex", ("identity",), allow_host_model_egress=True)
    grant, _ = manager.apply(plan.action_id)
    with pytest.raises(AptuniError, match="exact core-generated"):
        manager.load_grant(grant.grant_id[:10])

    async def exercise() -> None:
        params = StdioServerParameters(
            command=os.fspath(Path(os.sys.executable)),
            args=["-m", "aptuni.mcp.server", "--grant", grant.grant_id],
            env={"APTUNI_STATE_DIR": str(workspace.state_dir)},
        )
        async with Client(params) as client:
            result = await client.call_tool("aptuni_get_identity_card", {"max_units": 700})
            assert not result.is_error
            assert result.structured_content["audience"] == "host_mcp"
            assert result.structured_content["items"][0]["text"] == "Prefers concise answers"

    anyio.run(exercise)


def test_revoke_removes_a_bundle_symlink_without_following_it(tmp_path: Path) -> None:
    workspace, _, manager = _ready(tmp_path)
    grant_id = "grant-" + "a" * 16
    outside = tmp_path / "outside"
    outside.mkdir()
    marker = outside / "keep.txt"
    marker.write_text("keep", encoding="utf-8")
    bundle = workspace.state_dir / "adapters" / "bundles" / grant_id
    bundle.parent.mkdir(parents=True)
    bundle.symlink_to(outside, target_is_directory=True)

    assert manager.revoke(grant_id)
    assert not bundle.is_symlink()
    assert marker.read_text(encoding="utf-8") == "keep"


def test_adapter_ids_are_ascii_lowercase_hex_only(tmp_path: Path) -> None:
    _, _, manager = _ready(tmp_path)
    for invalid in ("grant-" + "A" * 16, "grant-" + "٠" * 16, "grant-" + "g" * 16):
        with pytest.raises(AptuniError, match="exact core-generated"):
            manager.revoke(invalid)
