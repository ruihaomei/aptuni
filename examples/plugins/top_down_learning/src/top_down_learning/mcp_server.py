"""STDIO tools for the manually invoked Top-Down Learning Agent plugin."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import socket
import sys
from dataclasses import asdict
from importlib.resources import as_file, files
from typing import Annotated


def _deny_network(event: str, args: tuple[object, ...]) -> None:
    if event == "socket.__new__" and len(args) > 1 and args[1] != socket.AF_UNIX:
        raise PermissionError("top_down_learning_network_denied")
    if event in {"socket.connect", "socket.bind"}:
        raise PermissionError("top_down_learning_network_denied")


sys.addaudithook(_deny_network)

from mcp.server import MCPServer  # noqa: E402
from mcp.server.mcpserver.exceptions import ToolError  # noqa: E402
from mcp.types import ToolAnnotations  # noqa: E402
from pydantic import Field  # noqa: E402

from aptuni.api.v1 import AptuniAPI, AptuniAPIError, connect, load_manifest  # noqa: E402
from top_down_learning.plugin import LearningSession, TopDownLearningPlugin  # noqa: E402

READ_ONLY = ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=False)
PROPOSE = ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=True, openWorldHint=False)
MAX_CONTINUATION_CHARS = 8192
MAX_CONTINUATION_PAYLOAD_BYTES = 4096


class _ContinuationCodec:
    def __init__(self) -> None:
        self.key = secrets.token_bytes(32)

    def issue(self, goal: str, completed_slugs: tuple[str, ...]) -> str:
        payload = json.dumps(
            {"goal": goal, "completed_slugs": list(completed_slugs)},
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode()
        signature = hmac.new(self.key, payload, hashlib.sha256).digest()
        return base64.urlsafe_b64encode(payload + signature).decode().rstrip("=")

    def read(self, value: str) -> tuple[str, tuple[str, ...]]:
        try:
            raw = base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))
            payload, signature = raw[:-32], raw[-32:]
            expected = hmac.new(self.key, payload, hashlib.sha256).digest()
            if len(payload) > MAX_CONTINUATION_PAYLOAD_BYTES or not hmac.compare_digest(signature, expected):
                raise ValueError
            data = json.loads(payload)
            goal = data["goal"]
            completed = data["completed_slugs"]
            if (
                not isinstance(goal, str)
                or not 1 <= len(goal) <= 500
                or not isinstance(completed, list)
                or len(completed) > 32
                or not all(isinstance(slug, str) for slug in completed)
            ):
                raise ValueError
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
            raise ValueError("top_down_progress_invalid") from error
        return goal, tuple(completed)


def _session(session: LearningSession, completed_slugs: tuple[str, ...]) -> dict[str, object]:
    return {
        "goal": session.goal,
        "completed_slugs": list(completed_slugs),
        "current_slug": session.current_slug,
        "remaining_count": sum(item.status == "needed" for item in session.prerequisites),
    }


def _turn(plugin: TopDownLearningPlugin, session: LearningSession) -> dict[str, object] | None:
    return asdict(plugin.teach(session)) if session.current_slug is not None else None


def create_server(api: AptuniAPI) -> MCPServer:
    plugin = TopDownLearningPlugin(api)
    continuations = _ContinuationCodec()
    server = MCPServer(
        "top-down-learning",
        version="1.0.0",
        instructions="Use only after explicit top-down-study invocation; require active learner output.",
    )

    @server.tool(name="top_down_start", annotations=READ_ONLY)
    def start(
        goal: Annotated[str, Field(min_length=1, max_length=500)],
    ) -> dict[str, object]:
        """Build a task-relevant prerequisite path and return only its first missing learning turn."""
        try:
            session = plugin.start(goal)
        except AptuniAPIError as error:
            raise ToolError(error.code) from error
        return {
            "schema_version": 1,
            "continuation": continuations.issue(goal, ()),
            "session": _session(session, ()),
            "turn": _turn(plugin, session),
        }

    @server.tool(name="top_down_check", annotations=READ_ONLY)
    def check(
        continuation: Annotated[str, Field(min_length=40, max_length=MAX_CONTINUATION_CHARS)],
        learner_output: Annotated[str, Field(min_length=1, max_length=4000)],
    ) -> dict[str, object]:
        """Check active learner output, then repeat or advance exactly one prerequisite."""
        try:
            goal, completed = continuations.read(continuation)
            session = plugin.resume(goal, completed)
            current = session.current_slug
            if current is None:
                raise ValueError("top_down_learning_complete")
            result = plugin.check(session, learner_output)
        except AptuniAPIError as error:
            raise ToolError(error.code) from error
        except ValueError as error:
            raise ToolError(str(error)) from error
        updated = completed + ((current,) if result.passed else ())
        return {
            "schema_version": 1,
            "continuation": continuations.issue(goal, updated),
            "check": asdict(result),
            "session": _session(session, updated),
            "turn": _turn(plugin, session),
        }

    @server.tool(name="top_down_record_gap", annotations=PROPOSE)
    def record_gap(
        continuation: Annotated[str, Field(min_length=40, max_length=MAX_CONTINUATION_CHARS)],
        learner_feedback: Annotated[str, Field(min_length=1, max_length=280)],
    ) -> dict[str, object]:
        """Explicitly propose one demonstrated gap; it remains quarantined for owner review."""
        try:
            goal, completed = continuations.read(continuation)
            session = plugin.resume(goal, completed)
            proposal = plugin.record_gap(session, learner_feedback)
        except AptuniAPIError as error:
            raise ToolError(error.code) from error
        except ValueError as error:
            raise ToolError(str(error)) from error
        return {
            "schema_version": 1,
            "candidate_id": proposal.candidate_id,
            "created": proposal.created,
            "status": proposal.status,
        }

    return server


def main() -> None:
    grant_id = os.environ.get("APTUNI_TOP_DOWN_GRANT_ID", "")
    if not grant_id:
        raise SystemExit("top_down_grant_required")
    manifest_resource = files("top_down_learning").joinpath("aptuni-plugin.toml")
    with as_file(manifest_resource) as manifest_path:
        api = connect(load_manifest(manifest_path), grant_id)
    create_server(api).run(transport="stdio")


if __name__ == "__main__":
    main()
