from __future__ import annotations

import base64
import hashlib
import json
from collections.abc import Mapping
from typing import Any

import pytest

from aptuni.sources.github import (
    GitHubApi,
    GitHubApiError,
    GitHubSourceSpec,
    HttpResult,
    SourceIdentityError,
    scan_github,
)


class RouteTransport:
    def __init__(self, routes: dict[str, list[tuple[int, dict[str, str], Any]]]) -> None:
        self.routes = routes
        self.calls: list[tuple[str, Mapping[str, str], int]] = []

    def get(self, url: str, headers: Mapping[str, str], max_bytes: int) -> HttpResult:
        self.calls.append((url, headers, max_bytes))
        status, response_headers, value = self.routes[url].pop(0)
        body = value if isinstance(value, bytes) else json.dumps(value).encode()
        return HttpResult(status, url, {"content-type": "application/json", **response_headers}, body)


def spec(**kwargs: Any) -> GitHubSourceSpec:
    return GitHubSourceSpec.build("https://github.com/o/r", **kwargs)


def git_blob_sha(body: bytes) -> str:
    return hashlib.sha1(f"blob {len(body)}\0".encode() + body, usedforsecurity=False).hexdigest()


def test_source_spec_keeps_only_a_credential_reference() -> None:
    value = spec(ref="main", token_env="APTUNI_GITHUB_TOKEN")
    assert value.roots() == (
        "https://github.com/o/r",
        "api:https://api.github.com",
        "ref:main",
        "env:APTUNI_GITHUB_TOKEN",
    )
    assert GitHubSourceSpec.from_roots(value.roots()) == value


def test_official_and_enterprise_origins_are_bound_to_the_repository() -> None:
    with pytest.raises(SourceIdentityError, match="github_api_origin_mismatch"):
        GitHubSourceSpec.build("https://github.com/o/r", api_origin="https://evil.example/api/v3")
    enterprise = GitHubSourceSpec.build(
        "https://git.example/o/r", api_origin="https://git.example/api/v3"
    )
    assert enterprise.api_origin == "https://git.example/api/v3"


def test_userinfo_and_explicit_ports_are_never_persisted_as_origins() -> None:
    with pytest.raises(SourceIdentityError, match="github_repository_url_invalid"):
        GitHubSourceSpec.build(
            "https://user:secret@git.example/o/r", api_origin="https://user:secret@git.example/api/v3"
        )
    with pytest.raises(SourceIdentityError, match="github_repository_url_invalid"):
        GitHubSourceSpec.build("https://git.example:8443/o/r", api_origin="https://git.example:8443/api/v3")
    with pytest.raises(SourceIdentityError, match="github_origin_port_invalid"):
        GitHubSourceSpec.build("https://git.example:notaport/o/r", api_origin="https://git.example/api/v3")


def test_cross_origin_redirect_is_denied_before_following() -> None:
    url = "https://api.github.com/repos/o/r"
    transport = RouteTransport({url: [(301, {"location": "https://evil.example/repos/o/r"}, {})]})
    with pytest.raises(GitHubApiError, match="github_redirect_origin_denied"):
        GitHubApi(spec(), transport)._json("/repos/o/r")
    assert len(transport.calls) == 1


def test_transport_cannot_hide_a_cross_origin_final_response() -> None:
    class LyingTransport:
        def get(self, url: str, headers: Mapping[str, str], max_bytes: int) -> HttpResult:
            return HttpResult(200, "https://evil.example/repos/o/r", {"content-type": "application/json"}, b"{}")

    with pytest.raises(GitHubApiError, match="github_response_origin_denied"):
        GitHubApi(spec(), LyingTransport())._json("/repos/o/r")


@pytest.mark.parametrize(
    ("headers", "code"),
    [
        ({"retry-after": "60"}, "github_rate_limited_retry_after"),
        ({"x-ratelimit-remaining": "0", "x-ratelimit-reset": "1"}, "github_rate_limited_reset"),
    ],
)
def test_rate_limit_signals_stop_without_retry(headers: dict[str, str], code: str) -> None:
    url = "https://api.github.com/repos/o/r"
    transport = RouteTransport({url: [(403, headers, {})]})
    with pytest.raises(GitHubApiError, match=code):
        GitHubApi(spec(), transport)._json("/repos/o/r")
    assert len(transport.calls) == 1


def test_truncated_recursive_tree_is_recovered_by_bounded_subtree_walk() -> None:
    origin = "https://api.github.com"
    commit = "1" * 40
    root = "2" * 40
    child = "3" * 40
    blob = "4" * 40
    routes = {
        f"{origin}/repos/o/r": [(200, {}, {"id": 7, "full_name": "o/r", "default_branch": "main"})],
        f"{origin}/repos/o/r/commits/main": [(200, {}, {"sha": commit})],
        f"{origin}/repos/o/r/git/trees/{commit}?recursive=1": [
            (200, {}, {"sha": root, "truncated": True, "tree": []})
        ],
        f"{origin}/repos/o/r/git/trees/{commit}": [
            (200, {}, {"truncated": False, "tree": [{"path": "src", "type": "tree", "sha": child}]})
        ],
        f"{origin}/repos/o/r/git/trees/{child}": [
            (200, {}, {"truncated": False, "tree": [{"path": "main.py", "type": "blob", "sha": blob}]})
        ],
    }
    tree = GitHubApi(spec(), RouteTransport(routes)).fetch_tree()
    assert tree.data["truncated"] is False
    assert tree.data["tree"] == [{"path": "src/main.py", "type": "blob", "sha": blob}]
    assert tree.notes == ("recursive_tree_recovered", "recursive_tree_truncated")


def test_malformed_subtree_identity_fails_instead_of_claiming_complete_coverage() -> None:
    origin = "https://api.github.com"
    commit = "1" * 40
    routes = {
        f"{origin}/repos/o/r": [(200, {}, {"id": 7, "full_name": "o/r", "default_branch": "main"})],
        f"{origin}/repos/o/r/commits/main": [(200, {}, {"sha": commit})],
        f"{origin}/repos/o/r/git/trees/{commit}?recursive=1": [
            (200, {}, {"truncated": True, "tree": []})
        ],
        f"{origin}/repos/o/r/git/trees/{commit}": [
            (200, {}, {"truncated": False, "tree": [{"path": "src", "type": "tree"}]})
        ],
    }
    with pytest.raises(GitHubApiError, match="github_tree_response_invalid"):
        GitHubApi(spec(), RouteTransport(routes)).fetch_tree()


def test_recursive_tree_duplicate_or_invalid_paths_fail_closed() -> None:
    base = {"repository_id": 7, "full_name": "o/r", "commit": "1" * 40, "truncated": False}
    duplicate = base | {"tree": [
        {"path": "README.md", "type": "blob", "sha": "2" * 40},
        {"path": "README.md", "type": "blob", "sha": "3" * 40},
    ]}
    invalid = base | {"tree": [{"path": "../README.md", "type": "blob", "sha": "2" * 40}]}
    with pytest.raises(SourceIdentityError, match="github_tree_entry_invalid"):
        scan_github(duplicate, "source", None, ("github.standard", "1"))
    with pytest.raises(SourceIdentityError, match="github_tree_entry_invalid"):
        scan_github(invalid, "source", None, ("github.standard", "1"))


def test_file_renamed_into_secret_pattern_is_withdrawn_not_reingested() -> None:
    base = {"repository_id": 7, "full_name": "o/r", "commit": "1" * 40, "truncated": False}
    first = scan_github(
        base | {"tree": [{"path": "notes.md", "type": "blob", "sha": "2" * 40}]},
        "source",
        None,
        ("github.standard", "1"),
    )
    second = scan_github(
        base | {"commit": "3" * 40,
                "tree": [{"path": "credentials.json", "type": "blob", "sha": "2" * 40}]},
        "source",
        first,
        ("github.standard", "1"),
    )
    assert [operation.kind for operation in second.delta.operations] == ["remove"]
    assert "secret_skipped" in second.notes


def test_blob_is_bounded_and_base64_decoded(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APTUNI_GITHUB_TOKEN", "test-token")
    body = b"hello"
    sha = git_blob_sha(body)
    url = f"https://api.github.com/repos/o/r/git/blobs/{sha}"
    transport = RouteTransport({
        url: [(200, {}, {"sha": sha, "size": len(body), "encoding": "base64",
                         "content": base64.b64encode(body).decode()})]
    })
    assert GitHubApi(spec(token_env="APTUNI_GITHUB_TOKEN"), transport).fetch_blob(sha) == body
    assert transport.calls[0][1]["Authorization"] == "Bearer test-token"


def test_blob_body_must_match_requested_git_identity() -> None:
    requested = git_blob_sha(b"expected")
    body = b"different"
    url = f"https://api.github.com/repos/o/r/git/blobs/{requested}"
    transport = RouteTransport({
        url: [(200, {}, {"sha": requested, "size": len(body), "encoding": "base64",
                         "content": base64.b64encode(body).decode()})]
    })
    with pytest.raises(GitHubApiError, match="github_blob_identity_mismatch"):
        GitHubApi(spec(), transport).fetch_blob(requested)


def test_missing_credential_reference_fails_before_network(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("APTUNI_GITHUB_TOKEN", raising=False)
    transport = RouteTransport({})
    with pytest.raises(GitHubApiError, match="github_credential_unavailable"):
        GitHubApi(spec(token_env="APTUNI_GITHUB_TOKEN"), transport)._json("/repos/o/r")
    assert transport.calls == []


def test_credential_with_header_control_characters_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APTUNI_GITHUB_TOKEN", "token\nheader")
    transport = RouteTransport({})
    with pytest.raises(GitHubApiError, match="github_credential_invalid"):
        GitHubApi(spec(token_env="APTUNI_GITHUB_TOKEN"), transport)._json("/repos/o/r")
    assert transport.calls == []
