"""The synthetic harness must preserve retrieval, disclosure and experiment boundaries."""
from __future__ import annotations

import importlib.util
import json
import os
import sys
from pathlib import Path

import anyio
import pytest
from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client
from mcp.server.mcpserver.exceptions import ToolError

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("agent_e2e_mock", ROOT / "tools/agent_e2e_mock.py")
assert SPEC is not None and SPEC.loader is not None
mock = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = mock
SPEC.loader.exec_module(mock)
FIXTURE = ROOT / "docs/dev/b10-continuation/synthetic-discovery-probe.json"


def server(tmp_path, arm="baseline", case="synthetic-contribution-supported", fixture=None):
    return mock.create_server(fixture or FIXTURE, case, arm, tmp_path)


async def call(app, name="aptuni_search_context", **args):
    return (await app.call_tool(name, args)).structured_content


async def setup(app):
    return await call(app, "aptuni_activate_context", intent="aptuni.full", scope="session",
                      query="unmatched-setup", concepts=["unmatched-setup"], modules=["knowledge"], max_units=32)


def test_only_four_tools_and_production_like_baseline_signature(tmp_path):
    async def run():
        app = server(tmp_path)
        tools = {tool.name: tool for tool in await app.list_tools()}
        assert set(tools) == {"aptuni_activation_status", "aptuni_activate_context",
                              "aptuni_search_context", "aptuni_activation_disable"}
        fields = tools["aptuni_search_context"].input_schema["properties"]
        assert set(fields) == {"query", "modules", "max_units", "limit", "include_evidence", "concepts"}
        assert "mode" not in fields
        assert "synthetic-contribution-supported" not in str(tools)
    anyio.run(run)


def test_setup_is_empty_off_default_and_refused_attempts_count(tmp_path):
    async def run():
        app = server(tmp_path)
        assert (await call(app, "aptuni_activation_status"))["mode"] == "off"
        with pytest.raises(ToolError, match="aptuni_activation_required"):
            await call(app, query="packing", modules=["knowledge"])
        assert app.task_calls == 1
        # A setup-shaped call after task work cannot reset or become free setup.
        await setup(app)
        assert app.task_calls == 2
        with pytest.raises(ToolError, match="research_call_limit"):
            await call(app, query="packing", modules=["knowledge"])
        assert app.task_calls == 3
    anyio.run(run)


def test_setup_and_baseline_use_real_compound_alias_matching(tmp_path):
    async def run():
        app = server(tmp_path)
        initial = await setup(app)
        assert initial["context"]["items"] == []
        assert initial["context"]["used_units"] == 32
        assert app.task_calls == app.task_used_units == 0
        response = await call(app, query="my prior work", modules=["knowledge"],
                              concepts=["integer programming"], max_units=4000)
        assert [item["canonical_id"] for item in response["items"]] == ["ev-303"]
        assert "authorship-linked" in response["items"][0]["text"]
        assert response["used_units"] == 32 + sum(item["units"] for item in response["items"])
        assert app.task_used_units == response["used_units"]
    anyio.run(run)


def test_refusals_validation_disable_and_reactivation_never_reset_budget(tmp_path):
    async def run():
        app = server(tmp_path)
        await setup(app)
        with pytest.raises(ToolError, match="mcp_module_denied"):
            await call(app, query="SECRET_QUERY", modules=["projects"])
        with pytest.raises(ToolError):
            await call(app, query="packing", modules=["knowledge"], concepts=["x"] * 9)
        assert app.task_calls == 2
        await call(app, "aptuni_activation_disable")
        with pytest.raises(ToolError, match="research_call_limit"):
            await setup(app)
        assert (await call(app, "aptuni_activation_status"))["mode"] == "off"
    anyio.run(run)


def test_actual_shared_budget_caps_second_call_even_with_large_requests(tmp_path):
    async def run():
        app = server(tmp_path)
        await setup(app)
        first = await call(app, query="packing", modules=["knowledge"], max_units=100000,
                           concepts=["packing", "optimization", "application", "museum", "colour"])
        second = await call(app, query="packing", modules=["knowledge"], max_units=100000,
                            concepts=["packing", "optimization", "application", "museum", "colour"])
        assert first["used_units"] > 2000
        assert first["used_units"] + second["used_units"] <= 4000
        assert second["requested_units"] == 4000 - first["used_units"]
        assert second["truncated"]
        assert app.task_used_units == first["used_units"] + second["used_units"]
    anyio.run(run)


def test_catalog_is_one_compact_unit_and_study_only_case_stays_study_only(tmp_path):
    async def run():
        app = server(tmp_path, "catalog", "synthetic-title-without-contribution")
        await setup(app)
        catalog = await call(app, query="prior work", modules=["knowledge"], mode="anchors", max_units=800)
        assert len(catalog["items"]) == 1
        assert len(catalog["items"][0]["text"].splitlines()) == 5
        assert catalog["used_units"] <= 800
        evidence = await call(app, query="prior work", modules=["knowledge"], mode="evidence",
                              anchor="repo-303", max_units=3200)
        assert len(evidence["items"]) == 1
        assert "third-party tutorial" in evidence["items"][0]["text"]
        assert "No owner-authored implementation" in evidence["items"][0]["text"]
        payload = json.dumps([catalog, evidence])
        for secret in ("evaluator_only", "evidence_interpretation", "synthetic-title-without-contribution",
                       "frozen_rubric", "Fixture ground truth"):
            assert secret not in payload
        assert app.task_used_units == catalog["used_units"] + evidence["used_units"]
    anyio.run(run)


def test_named_catalog_separates_lookup_anchor_from_evidence_citation(tmp_path):
    async def run():
        app = server(tmp_path, "catalog_named")
        await setup(app)
        catalog = await call(app, query="prior work", modules=["knowledge"], mode="anchors", max_units=800)
        rows = json.loads(catalog["items"][0]["text"])
        selected = next(row for row in rows if row["label"].startswith("WarehouseOpt"))
        assert selected["anchor"] == "repo-303"
        assert selected["evidence_ref"] == "ev-303"
        assert len(rows) == 5 and catalog["used_units"] <= 800 and not catalog["truncated"]
        evidence = await call(app, query="prior work", modules=["knowledge"], mode="evidence",
                              anchor=selected["anchor"], max_units=3200)
        assert evidence["items"][0]["canonical_id"] == selected["evidence_ref"]
        assert "authorship-linked" in evidence["items"][0]["text"]
        assert app.task_calls == 2 and app.task_used_units <= 4000
    anyio.run(run)


def test_compact_labels_fit_without_merging_colliding_prefixes():
    entries = [(f"repo-{i}", label, f"ev-{i}") for i, label in enumerate([
        "x" * 100 + "a", "x" * 100 + "b", "仓储优化" * 30, "namespace/repository", "short"])]
    serialized, mapping = mock.compact_catalog(entries)
    rows = json.loads(serialized)
    assert len(rows) == 5 and len(mapping) == 5
    assert all(set(row) == {"anchor", "label"} for row in rows)
    assert all(len(row["label"].encode("utf-8")) <= 48 for row in rows)
    assert rows[0]["label"] == rows[1]["label"] and rows[0]["label"].endswith("…")
    assert mapping[rows[0]["anchor"]] != mapping[rows[1]["anchor"]]
    assert rows[2]["label"].endswith("…")
    assert rows[3]["label"] == "namespace/repository"
    unit = mock.ContextUnit("L4", "anchors", None, "knowledge", serialized, None, None, True, ())
    packed = mock.pack_units((unit,), 800)
    assert packed.items and not packed.truncated and packed.used_units <= 800


@pytest.mark.parametrize("case", ["synthetic-contribution-supported", "synthetic-title-without-contribution"])
def test_compact_catalog_opaque_lookup_and_withdrawal(tmp_path, case):
    async def run():
        for index, withdraw in enumerate((False, True)):
            app = server(tmp_path / str(index), "catalog_compact", case)
            await setup(app)
            catalog = await call(app, query="work", modules=["knowledge"], mode="anchors", max_units=800)
            rows = json.loads(catalog["items"][0]["text"])
            selected = next(row for row in rows if row["label"].startswith("WarehouseOpt"))
            assert selected["anchor"] == "a03" and "evidence_ref" not in selected
            assert "repo-303" not in str(catalog) and "ev-303" not in str(catalog)
            if withdraw:
                app.records["ev-303"].exposed = False
            response = await call(app, query="work", modules=["knowledge"], mode="evidence",
                                  anchor=selected["anchor"], max_units=3200)
            assert app.task_calls == 2 and app.task_used_units <= 4000
            assert response["items"] == [] if withdraw else response["items"][0]["canonical_id"] == "ev-303"
    anyio.run(run)


def test_compact_prefix_collision_refuses_without_disclosing_anchors(tmp_path):
    fixture = json.loads(FIXTURE.read_text())
    fixture["fixed_catalog"]["entries"][0]["label"] = "x" * 100 + "a"
    fixture["fixed_catalog"]["entries"][1]["label"] = "x" * 100 + "b"
    path = tmp_path / "collision.json"
    path.write_text(json.dumps(fixture))

    async def run():
        app = server(tmp_path / "app", "catalog_compact", fixture=path)
        await setup(app)
        with pytest.raises(ToolError, match="research_label_ambiguity"):
            await call(app, query="work", modules=["knowledge"], mode="anchors")
        assert app.task_calls == 1 and not app.disclosed_anchors and not app.anchor_map
    anyio.run(run)


def test_compact_unknown_original_and_citation_identifiers_are_empty(tmp_path):
    async def run():
        responses = []
        for index, anchor in enumerate(("unknown", "repo-303", "ev-303")):
            app = server(tmp_path / str(index), "catalog_compact")
            await setup(app)
            await call(app, query="work", modules=["knowledge"], mode="anchors")
            responses.append(await call(app, query="work", modules=["knowledge"], mode="evidence", anchor=anchor))
        assert responses[0] == responses[1] == responses[2]
        assert not responses[0]["items"]
    anyio.run(run)


def test_catalog_rechecks_exposure_and_unknown_anchor_is_indistinguishable(tmp_path):
    fixture = json.loads(FIXTURE.read_text())
    fixture["cases"][0]["variable_evidence"][0]["expose_enabled"] = False
    path = tmp_path / "fixture.json"
    path.write_text(json.dumps(fixture))

    async def run():
        responses = []
        for index, anchor in enumerate(("repo-303", "repo-missing")):
            app = server(tmp_path / str(index), "catalog", fixture=path)
            await setup(app)
            catalog = await call(app, query="work", modules=["knowledge"], mode="anchors")
            assert "WarehouseOpt" not in str(catalog)
            responses.append(await call(app, query="work", modules=["knowledge"], mode="evidence", anchor=anchor))
        assert responses[0] == responses[1]
        assert responses[0]["items"] == []
    anyio.run(run)


def test_exact_anchor_requires_prior_catalog_and_cannot_be_used_twice(tmp_path):
    async def run():
        app = server(tmp_path, "catalog")
        await setup(app)
        with pytest.raises(ToolError, match="research_anchor_sequence"):
            await call(app, query="work", modules=["knowledge"], mode="evidence", anchor="repo-303")
        with pytest.raises(ToolError, match="research_anchor_sequence"):
            await call(app, query="work", modules=["knowledge"], mode="anchors")
        assert app.task_calls == 2
    anyio.run(run)


def test_exposure_is_rechecked_after_catalog_disclosure(tmp_path):
    async def run():
        app = server(tmp_path, "catalog")
        await setup(app)
        catalog = await call(app, query="work", modules=["knowledge"], mode="anchors")
        assert "WarehouseOpt" in str(catalog)
        app.records["ev-303"].exposed = False
        result = await call(app, query="work", modules=["knowledge"], mode="evidence", anchor="repo-303")
        assert result["items"] == []
        assert result["used_units"] == 32
    anyio.run(run)


def test_stdio_entry_point_and_disposable_sqlite_cleanup(tmp_path):
    async def run():
        params = StdioServerParameters(command=sys.executable, args=[
            str(ROOT / "tools/agent_e2e_mock.py"), "--fixture", str(FIXTURE),
            "--case", "synthetic-contribution-supported", "--arm", "baseline",
        ], env={**os.environ, "TMPDIR": str(tmp_path), "PYTHONDONTWRITEBYTECODE": "1"})
        with anyio.fail_after(10):
            async with stdio_client(params) as (read, write), ClientSession(read, write) as client:
                await client.initialize()
                assert len((await client.list_tools()).tools) == 4
                initial = await client.call_tool("aptuni_activation_status", {})
                assert initial.structured_content["mode"] == "off"
                await client.call_tool("aptuni_activate_context", {
                    "intent": "aptuni.full", "scope": "session", "query": "setup-unmatched",
                    "modules": ["knowledge"], "max_units": 32,
                })
                found = await client.call_tool("aptuni_search_context", {
                    "query": "prior work", "modules": ["knowledge"],
                    "concepts": ["integer programming"], "max_units": 4000,
                })
                assert not found.is_error
                assert found.structured_content["items"][0]["canonical_id"] == "ev-303"
        assert not list(tmp_path.glob("aptuni-synthetic-*"))
    anyio.run(run)
