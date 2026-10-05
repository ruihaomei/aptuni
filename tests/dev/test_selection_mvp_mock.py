"""The disposable selection seam must retain activation and bounded disclosure."""
from __future__ import annotations

import sys
from pathlib import Path

import anyio
import pytest
from mcp.server.mcpserver.exceptions import ToolError

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
from selection_mvp_mock import create_server

FIXTURE = Path(__file__).resolve().parents[2] / "docs/dev/b10-continuation/selection-mvp-fixture.json"


async def call(app, name="aptuni_search_context", **args):
    return (await app.call_tool(name, args)).structured_content


def test_off_denies_and_setup_has_no_context(tmp_path):
    async def run():
        app = create_server(FIXTURE, "s01", "directed", tmp_path)
        with pytest.raises(ToolError, match="aptuni_activation_required"):
            await call(app, query="all candidates", modules=["knowledge"], mode="coverage")
        assert app.task_calls == 1
        # A late setup cannot erase an attempted retrieval or turn on Full for free.
        with pytest.raises(ToolError, match="research_setup_only"):
            await call(app, "aptuni_activate_context", intent="aptuni.full", query="setup",
                       modules=["knowledge"], scope="session", max_units=32)
        assert (await call(app, "aptuni_activation_status"))["mode"] == "off"
    anyio.run(run)


def test_coverage_get_only_discloses_permitted_listed_ids(tmp_path):
    async def run():
        app = create_server(FIXTURE, "s01", "directed", tmp_path)
        setup = await call(app, "aptuni_activate_context", intent="aptuni.full", query="setup",
                           modules=["knowledge"], scope="session", max_units=32)
        assert setup["context"]["items"] == []
        assert app.task_calls == app.task_used_units == 0
        with pytest.raises(ToolError, match="mcp_module_denied"):
            await call(app, query="all candidates", modules=["projects"], mode="coverage")
        index = await call(app, query="all candidates", modules=["knowledge"], mode="coverage",
                           max_units=1000)
        assert len(index["items"]) == 1
        assert "hidden" not in index["items"][0]["text"]
        unknown = await call(app, query="get", modules=["knowledge"], mode="get",
                             ids=["project-hidden", "made-up"], max_units=2000)
        assert unknown["items"] == []
        with pytest.raises(ToolError, match="research_call_limit"):
            await call(app, query="get", modules=["knowledge"], mode="get",
                       ids=["project-a"], max_units=2000)
        assert app.task_used_units <= 4000
    anyio.run(run)


def test_baseline_has_no_navigation_fields(tmp_path):
    async def run():
        app = create_server(FIXTURE, "s01", "baseline", tmp_path)
        tools = {tool.name: tool for tool in await app.list_tools()}
        assert set(tools["aptuni_search_context"].input_schema["properties"]) == {
            "query", "modules", "max_units", "limit", "include_evidence", "concepts",
        }
    anyio.run(run)
