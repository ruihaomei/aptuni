"""Research discovery must retain explicit activation and current read boundaries."""
from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from contextlib import nullcontext
from dataclasses import asdict
from pathlib import Path
from types import SimpleNamespace as NS

import anyio
import pytest
from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client
from mcp.server.mcpserver.exceptions import ToolError

from aptuni.adapters.manager import AdapterGrant
from aptuni.application.context import pack_units, response_from
from aptuni.application.service import AptuniService, HostContextAccess
from aptuni.application.workspace import Workspace

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
SPEC = importlib.util.spec_from_file_location("agent_e2e_discovery", ROOT / "tools/agent_e2e_discovery.py")
assert SPEC is not None and SPEC.loader is not None
discovery = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(discovery)


def evidence(identifier="ev-1", *, exposed=True, text="A bounded synthetic modelling study.", module="knowledge"):
    return NS(id=identifier, record_type="evidence", module=module, exposed=exposed,
              excerpt=text, statement=None, subject="Study", trust="untrusted_source", signals=("exposure",),
              provenance=NS(source_id="source-fixture", locator=NS(extension=NS(
                  schema_name="github.locator", fields={"repository_id": 123, "owner_name": "invented/StudyRepo"}))))


class Service:
    def __init__(self, rows):
        self.rows = rows
        self.seq = 66

    def snapshot(self):
        return self.seq, NS(exposable=lambda: [row for row in self.rows if row.exposed])

    @staticmethod
    def policy_of(records):
        return NS(epoch=1)

    def context(self, query, **kwargs):
        return response_from(pack_units((), kwargs["budget"]), budget=kwargs["budget"],
                             vault_seq=self.seq, policy_epoch=1, audience="host_mcp")


def access(*, scopes=("context.read", "evidence.read"), egress=True):
    return HostContextAccess("research-host", frozenset(scopes), frozenset({"knowledge", "projects"}),
                             "remote_unknown", egress)


async def call(server, name="aptuni_search_context", **args):
    return (await server.call_tool(name, args)).structured_content


async def setup(server):
    return await call(server, "aptuni_activate_context", intent="aptuni.full", scope="session",
                      query="unmatched-setup", modules=["knowledge"], max_units=32)


def test_off_default_no_implicit_activation_and_four_tools():
    async def run():
        server = discovery.create_server(Service([evidence()]), access, nullcontext, expected_seq=66)
        assert len(await server.list_tools()) == 4
        assert (await call(server, "aptuni_activation_status"))["mode"] == "off"
        with pytest.raises(ToolError, match="aptuni_activation_required"):
            await call(server, query="prior work", modules=["knowledge"], mode="anchors")
        assert server.task_calls == 1 and not server.disclosed_anchors
    anyio.run(run)


def test_catalog_filters_non_evidence_credentials_hidden_and_unrequested_modules():
    async def run():
        rows = [evidence(), evidence("ev-hidden", exposed=False),
                evidence("ev-credential", text="API_KEY: sk-" + "test" + "1234567890" * 3),
                evidence("ev-other", module="identity"),
                NS(record_type="source_config", module="knowledge", exposed=True)]
        service = Service(rows)
        server = discovery.create_server(service, access, nullcontext, expected_seq=66)
        assert (await setup(server))["context"]["items"] == []
        catalog = await call(server, query="prior work", modules=["knowledge"], mode="anchors")
        selected = json.loads(catalog["items"][0]["text"])
        assert selected == [{"anchor": "a01", "label": "StudyRepo"}]
        response = await call(server, query="prior work", modules=["knowledge"], mode="evidence", anchor="a01")
        assert [item["canonical_id"] for item in response["items"]] == ["ev-1"]
        assert response["items"][0]["tainted"] and response["items"][0]["signals"] == ["exposure"]
        assert server.task_calls == 2 and server.task_used_units <= 4000
    anyio.run(run)


@pytest.mark.parametrize("scope", ["context.read", "evidence.read"])
def test_scope_revocation_after_catalog_refuses(scope):
    async def run():
        current = access()
        server = discovery.create_server(Service([evidence()]), lambda: current, nullcontext, expected_seq=66)
        await setup(server)
        await call(server, query="work", modules=["knowledge"], mode="anchors")
        current = access(scopes=(scope,))
        with pytest.raises(ToolError, match="mcp_scope_denied"):
            await call(server, query="work", modules=["knowledge"], mode="evidence", anchor="a01")
        assert server.task_calls == 2
    anyio.run(run)


def test_sequence_drift_and_withdrawal_are_rechecked_before_hydration():
    async def run():
        for drift in (False, True):
            row = evidence()
            service = Service([row])
            server = discovery.create_server(service, access, nullcontext, expected_seq=66)
            await setup(server)
            await call(server, query="work", modules=["knowledge"], mode="anchors")
            row.exposed = False
            if drift:
                service.seq += 1
                with pytest.raises(ToolError, match="research_snapshot_changed"):
                    await call(server, query="work", modules=["knowledge"], mode="evidence", anchor="a01")
            else:
                response = await call(server, query="work", modules=["knowledge"], mode="evidence", anchor="a01")
                assert response["items"] == []
    anyio.run(run)


def test_no_model_egress_and_ungranted_modules_fail_closed():
    async def run():
        for provider, modules, code in [(lambda: access(egress=False), ["knowledge"], "host_model_egress_denied"),
                                        (access, ["experience"], "mcp_module_denied")]:
            server = discovery.create_server(Service([evidence()]), provider, nullcontext, expected_seq=66)
            with pytest.raises(ToolError, match=code):
                await call(server, "aptuni_activate_context", intent="aptuni.full", scope="session",
                           query="setup", modules=modules, max_units=32)
            assert (await call(server, "aptuni_activation_status"))["mode"] == "off"
    anyio.run(run)


def ready_fixture(tmp_path):
    service = AptuniService(Workspace(tmp_path / "state"))
    service.init(tmp_path / "vault")
    service.remember("A synthetic learning record.", "knowledge")
    service.rebuild_index()
    scratch = tmp_path / "private"
    scratch.mkdir(mode=0o700)
    authorization = service.workspace.state_dir / "developer"
    authorization.mkdir(mode=0o700)
    (authorization / "authorization.lock").touch(mode=0o600)
    # A disposable fixture grant, not an owner confirmation or host installation.
    grants = service.workspace.state_dir / "adapters" / "grants"
    grants.mkdir(parents=True, mode=0o700)
    identifier = "grant-" + "a" * 16
    grant = AdapterGrant(identifier, "codex", "fixture-host", ("knowledge",),
                         ("context.read", "evidence.read"), "remote_unknown", True,
                         "fixture", "fixture", "fixture")
    path = grants / f"{identifier}.json"
    path.write_text(json.dumps(asdict(grant)))
    path.chmod(0o600)
    return service, scratch, identifier


def test_guard_denies_protected_effects_in_isolated_process(tmp_path):
    service, scratch, _ = ready_fixture(tmp_path)
    script = f"""
import sys, sqlite3, os, json
from pathlib import Path
sys.path.insert(0, {str(ROOT / 'tools')!r})
from agent_e2e_discovery import install_guard
from aptuni.application.workspace import Workspace
scratch=Path({str(scratch)!r}); forbidden=Path({str(tmp_path / 'forbidden')!r})
regular=Path({str(tmp_path / 'existing-file')!r});regular.write_text('unchanged')
descriptor=os.open(regular,os.O_RDWR)
install_guard(Workspace(Path({str(service.workspace.state_dir)!r})), scratch)
source=scratch/'marker';source.write_text('invented')
operations=(lambda:forbidden.write_text('denied'), lambda:sqlite3.connect(str(forbidden)),
            lambda:os.rename(source,forbidden),lambda:subprocess(),lambda:os.fdopen(descriptor,'wb'))
def subprocess():
 import subprocess
 subprocess.run([sys.executable,'-c','pass'],check=True)
for operation in operations:
 try:operation()
 except PermissionError:pass
 else:raise RuntimeError('guard failed')
source.unlink()
os.close(descriptor)
assert regular.read_text()=='unchanged'
print(json.dumps({{'denied_effects':5,'canonical_read':False}}))
"""
    result = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True,
                            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}, timeout=15, check=False)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == {"denied_effects": 5, "canonical_read": False}
    assert not (tmp_path / "forbidden").exists()


def test_actual_stdio_guard_and_empty_full_setup_do_not_change_fixture(tmp_path):
    service, scratch, grant = ready_fixture(tmp_path)
    sequence = service.snapshot()[0]
    async def run():
        parameters = StdioServerParameters(command=sys.executable, args=[
            str(ROOT / "tools/agent_e2e_discovery.py"), "--grant", grant,
            "--expected-seq", str(sequence), "--private-root", str(scratch),
        ], env={**os.environ, "APTUNI_STATE_DIR": str(service.workspace.state_dir),
                "PYTHONDONTWRITEBYTECODE": "1"})
        with anyio.fail_after(20):
            async with stdio_client(parameters) as (read, write), ClientSession(read, write) as client:
                await client.initialize()
                assert len((await client.list_tools()).tools) == 4
                assert (await client.call_tool("aptuni_activation_status", {})).structured_content["mode"] == "off"
                full = await client.call_tool("aptuni_activate_context", {
                    "intent": "aptuni.full", "scope": "session", "query": "unmatched-setup",
                    "concepts": ["unmatched-setup"], "modules": ["knowledge"], "max_units": 32,
                })
                assert not full.is_error and full.structured_content["context"]["items"] == []
                catalog = await client.call_tool("aptuni_search_context", {
                    "query": "prior work", "modules": ["knowledge"], "mode": "anchors", "max_units": 800,
                })
                assert not catalog.is_error and catalog.structured_content["items"] == []
                await client.call_tool("aptuni_activation_disable", {})
                denied = await client.call_tool("aptuni_search_context", {
                    "query": "work", "modules": ["knowledge"], "mode": "anchors", "max_units": 800,
                })
                assert denied.is_error
    anyio.run(run)
    assert service.snapshot()[0] == sequence
