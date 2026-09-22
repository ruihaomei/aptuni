from __future__ import annotations

import base64
import hashlib
import json
from collections.abc import Mapping
from typing import Any

import pytest

from aptuni.sources.github import (
    GitHubActivityBatch,
    GitHubApi,
    GitHubApiError,
    GitHubSourceSpec,
    HttpResult,
    SourceIdentityError,
    scan_github,
    scan_github_activity,
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


def assert_partial_activity_preserves_prior(batch: GitHubActivityBatch) -> None:
    assert batch.complete is False
    prior = scan_github_activity(
        GitHubActivityBatch(7, "o/r", ({
            "activity_id": "9" * 40,
            "activity_key": "commit:" + "9" * 40,
            "activity_kind": "commit",
            "actor": "octocat",
            "commit": "9" * 40,
            "mode": "deep",
            "occurred_at": "2026-09-19T01:02:03+00:00",
            "title": "Prior",
        },), True, ()),
        "source", None, ("github.deep", "1"),
    )
    reconciled = scan_github_activity(batch, "source", prior, ("github.deep", "1"))
    assert all(operation.kind != "remove" for operation in reconciled.delta.operations)
    assert any(
        item.locator.extension.fields["activity_key"] == "commit:" + "9" * 40
        for item in reconciled.snapshot.items
    )


def test_source_spec_keeps_only_a_credential_reference() -> None:
    value = spec(ref="main", token_env="APTUNI_GITHUB_TOKEN")
    assert value.roots() == (
        "https://github.com/o/r",
        "api:https://api.github.com",
        "ref:main",
        "env:APTUNI_GITHUB_TOKEN",
    )
    assert GitHubSourceSpec.from_roots(value.roots()) == value


def test_deep_source_requires_and_round_trips_one_exact_actor() -> None:
    value = spec(ref="main", token_env="APTUNI_GITHUB_TOKEN", actor="Octo-Cat")
    assert value.roots() == (
        "https://github.com/o/r",
        "api:https://api.github.com",
        "ref:main",
        "env:APTUNI_GITHUB_TOKEN",
        "actor:Octo-Cat",
    )
    assert GitHubSourceSpec.from_roots(value.roots()) == value
    assert spec().roots() == ("https://github.com/o/r", "api:https://api.github.com")
    for actor in ("", "-octocat", "octo cat", "octocat\nforged", "x" * 65):
        with pytest.raises(SourceIdentityError, match="github_actor_invalid"):
            spec(actor=actor)


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


def test_authored_commits_are_exact_actor_minimized_and_paginated() -> None:
    origin = "https://api.github.com"
    commit = "1" * 40
    routes = {
        f"{origin}/repos/o/r": [(200, {}, {"id": 7, "full_name": "o/r", "default_branch": "main"})],
        f"{origin}/repos/o/r/commits?author=Octo-Cat&per_page=100&page=1&sha=main": [
            (200, {}, [{
                "sha": commit,
                "author": {"login": "octo-cat"},
                "commit": {"author": {"date": "2026-09-20T01:02:03Z"},
                           "message": "Fix parser\n\nbody that must not be stored"},
            }]),
        ],
    }
    transport = RouteTransport(routes)

    batch = GitHubApi(spec(ref="main", actor="Octo-Cat"), transport).fetch_authored_commits()

    assert batch.repository_id == 7
    assert batch.complete is True
    assert batch.items == ({
        "activity_id": commit,
        "activity_key": f"commit:{commit}",
        "activity_kind": "commit",
        "actor": "Octo-Cat",
        "commit": commit,
        "mode": "deep",
        "occurred_at": "2026-09-20T01:02:03+00:00",
        "title": "Fix parser",
    },)
    serialized = json.dumps(batch.items)
    assert "body that must not be stored" not in serialized


@pytest.mark.parametrize("repository_id", [True, 0, -1])
def test_deep_repository_identity_must_be_an_exact_positive_integer(repository_id: object) -> None:
    origin = "https://api.github.com"
    routes = {
        f"{origin}/repos/o/r": [
            (200, {}, {"id": repository_id, "full_name": "o/r", "default_branch": "main"})
        ],
    }
    with pytest.raises(GitHubApiError, match="github_repository_response_invalid"):
        GitHubApi(spec(actor="octocat"), RouteTransport(routes)).fetch_deep_activity()

    with pytest.raises(SourceIdentityError, match="github_repository_identity_invalid"):
        scan_github_activity(
            GitHubActivityBatch(repository_id, "o/r", (), True, ()),  # type: ignore[arg-type]
            "source", None, ("github.deep", "1"),
        )


def test_authored_commits_skip_unlinked_or_mismatched_authors_as_partial() -> None:
    origin = "https://api.github.com"
    routes = {
        f"{origin}/repos/o/r": [(200, {}, {"id": 7, "full_name": "o/r", "default_branch": "main"})],
        f"{origin}/repos/o/r/commits?author=octocat&per_page=100&page=1&sha=main": [
            (200, {}, [
                {"sha": "1" * 40, "author": None,
                 "commit": {"author": {"date": "2026-09-20T01:02:03Z"}, "message": "unlinked"}},
                {"sha": "2" * 40, "author": {"login": "someone-else"},
                 "commit": {"author": {"date": "2026-09-20T01:02:03Z"}, "message": "other"}},
            ]),
        ],
    }

    batch = GitHubApi(spec(ref="main", actor="octocat"), RouteTransport(routes)).fetch_authored_commits()

    assert batch.items == ()
    assert batch.complete is False
    assert batch.notes == ("commit_author_unverified_skipped",)


def test_authored_commit_control_bytes_are_sanitized_before_storage() -> None:
    origin = "https://api.github.com"
    commit = "a" * 40
    routes = {
        f"{origin}/repos/o/r": [(200, {}, {"id": 7, "full_name": "o/r", "default_branch": "main"})],
        f"{origin}/repos/o/r/commits?author=octocat&per_page=100&page=1&sha=main": [
            (200, {}, [{
                "sha": commit,
                "author": {"login": "octocat"},
                "commit": {"author": {"date": "2026-09-20T01:02:03Z"},
                           "message": "Fix\x1b[31m parser\x00\nforged row"},
            }]),
        ],
    }

    batch = GitHubApi(spec(actor="octocat"), RouteTransport(routes)).fetch_authored_commits()

    assert batch.items[0]["title"] == "Fix [31m parser"
    assert not any(ord(character) < 32 for character in batch.items[0]["title"])
    assert "forged row" not in batch.items[0]["title"]


def test_authored_commit_page_cap_is_partial_and_response_bytes_are_bounded() -> None:
    origin = "https://api.github.com"
    routes: dict[str, list[tuple[int, dict[str, str], Any]]] = {
        f"{origin}/repos/o/r": [(200, {}, {"id": 7, "full_name": "o/r", "default_branch": "main"})],
    }
    for page in range(1, 6):
        items = [
            {
                "sha": f"{(page - 1) * 100 + index:040x}",
                "author": {"login": "octocat"},
                "commit": {"author": {"date": "2026-09-20T01:02:03Z"}, "message": "bounded"},
            }
            for index in range(100)
        ]
        routes[f"{origin}/repos/o/r/commits?author=octocat&per_page=100&page={page}&sha=main"] = [
            (200, {}, items)
        ]
    transport = RouteTransport(routes)

    batch = GitHubApi(spec(actor="octocat"), transport).fetch_authored_commits()

    assert len(batch.items) == 500
    assert batch.complete is False
    assert batch.notes == ("deep_commits_truncated",)
    assert {call[2] for call in transport.calls[1:]} == {2_000_000}


def test_authored_commit_duplicate_or_naive_timestamp_fails_closed() -> None:
    origin = "https://api.github.com"
    commit = {
        "sha": "1" * 40,
        "author": {"login": "octocat"},
        "commit": {"author": {"date": "2026-09-20T01:02:03Z"}, "message": "one"},
    }
    duplicate_routes = {
        f"{origin}/repos/o/r": [(200, {}, {"id": 7, "full_name": "o/r", "default_branch": "main"})],
        f"{origin}/repos/o/r/commits?author=octocat&per_page=100&page=1&sha=main": [
            (200, {}, [commit, commit]),
        ],
    }
    with pytest.raises(GitHubApiError, match="github_deep_activity_duplicate"):
        GitHubApi(spec(actor="octocat"), RouteTransport(duplicate_routes)).fetch_authored_commits()

    naive = json.loads(json.dumps(commit))
    naive["commit"]["author"]["date"] = "2026-09-20T01:02:03"
    naive_routes = {
        f"{origin}/repos/o/r": [(200, {}, {"id": 7, "full_name": "o/r", "default_branch": "main"})],
        f"{origin}/repos/o/r/commits?author=octocat&per_page=100&page=1&sha=main": [(200, {}, [naive])],
    }
    with pytest.raises(GitHubApiError, match="github_deep_timestamp_invalid"):
        GitHubApi(spec(actor="octocat"), RouteTransport(naive_routes)).fetch_authored_commits()


def test_deep_activity_includes_exact_actor_opened_pull_requests() -> None:
    origin = "https://api.github.com"
    commit_url = f"{origin}/repos/o/r/commits?author=octocat&per_page=100&page=1&sha=main"
    pr_url = (
        f"{origin}/search/issues?q=repo%3Ao%2Fr+is%3Apr+author%3Aoctocat"
        "&per_page=100&page=1"
    )
    reviewed_url = (
        f"{origin}/search/issues?q=repo%3Ao%2Fr+is%3Apr+reviewed-by%3Aoctocat"
        "&per_page=100&page=1"
    )
    routes = {
        f"{origin}/repos/o/r": [
            (200, {}, {"id": 7, "full_name": "o/r", "default_branch": "main"})
        ],
        commit_url: [(200, {}, [])],
        pr_url: [(200, {}, {
            "total_count": 2,
            "incomplete_results": False,
            "items": [
                {
                    "id": 41,
                    "number": 8,
                    "title": "Ship\x1b[31m bounded sync\nforged",
                    "state": "open",
                    "created_at": "2026-09-20T01:02:03Z",
                    "user": {"login": "OctoCat"},
                    "repository_url": f"{origin}/repos/o/r",
                    "pull_request": {},
                    "body": "must not persist",
                },
                {
                    "id": 42,
                    "number": 9,
                    "title": "someone else's",
                    "state": "closed",
                    "created_at": "2026-09-21T01:02:03Z",
                    "user": {"login": "other"},
                    "repository_url": f"{origin}/repos/o/r",
                    "pull_request": {},
                },
            ],
        })],
        reviewed_url: [(200, {}, {"total_count": 0, "incomplete_results": False, "items": []})],
    }

    batch = GitHubApi(spec(actor="octocat"), RouteTransport(routes)).fetch_deep_activity()

    assert batch.complete is False
    assert batch.notes == ("pull_request_author_unverified_skipped",)
    assert batch.items == ({
        "activity_id": "41",
        "activity_key": "pull_request:41",
        "activity_kind": "pull_request",
        "actor": "octocat",
        "mode": "deep",
        "occurred_at": "2026-09-20T01:02:03+00:00",
        "pull_number": 8,
        "state": "open",
        "title": "Ship [31m bounded sync forged",
    },)
    assert "must not persist" not in json.dumps(batch.items)


def test_deep_activity_includes_only_submitted_exact_actor_reviews() -> None:
    origin = "https://api.github.com"
    routes = {
        f"{origin}/repos/o/r": [
            (200, {}, {"id": 7, "full_name": "o/r", "default_branch": "main"})
        ],
        f"{origin}/repos/o/r/commits?author=octocat&per_page=100&page=1&sha=main": [
            (200, {}, [])
        ],
        (
            f"{origin}/search/issues?q=repo%3Ao%2Fr+is%3Apr+author%3Aoctocat"
            "&per_page=100&page=1"
        ): [(200, {}, {"total_count": 0, "incomplete_results": False, "items": []})],
        (
            f"{origin}/search/issues?q=repo%3Ao%2Fr+is%3Apr+reviewed-by%3Aoctocat"
            "&per_page=100&page=1"
        ): [(200, {}, {
            "total_count": 1,
            "incomplete_results": False,
            "items": [{
                "id": 80,
                "number": 12,
                "title": "Reviewed PR",
                "state": "closed",
                "created_at": "2026-09-18T01:02:03Z",
                "user": {"login": "author"},
                "repository_url": f"{origin}/repos/o/r",
                "pull_request": {},
            }],
        })],
        f"{origin}/repos/o/r/pulls/12/reviews?per_page=100&page=1": [(200, {}, [
            {
                "id": 91,
                "user": {"login": "OctoCat"},
                "submitted_at": "2026-09-20T04:05:06Z",
                "state": "APPROVED\x00",
                "body": "must not persist",
            },
            {
                "id": 92,
                "user": {"login": "other"},
                "submitted_at": "2026-09-20T04:05:06Z",
                "state": "COMMENTED",
            },
            {
                "id": 93,
                "user": {"login": "octocat"},
                "submitted_at": None,
                "state": "PENDING",
            },
        ])],
    }

    batch = GitHubApi(spec(actor="octocat"), RouteTransport(routes)).fetch_deep_activity()

    assert batch.complete is True
    assert batch.items == ({
        "activity_id": "91",
        "activity_key": "review:91",
        "activity_kind": "review",
        "actor": "octocat",
        "mode": "deep",
        "occurred_at": "2026-09-20T04:05:06+00:00",
        "pull_number": 12,
        "state": "approved",
    },)
    assert "must not persist" not in json.dumps(batch.items)


def test_deep_pull_request_search_incomplete_is_partial_and_cross_repo_fails_closed() -> None:
    origin = "https://api.github.com"
    repository = f"{origin}/repos/o/r"
    commits = f"{repository}/commits?author=octocat&per_page=100&page=1&sha=main"
    authored = (
        f"{origin}/search/issues?q=repo%3Ao%2Fr+is%3Apr+author%3Aoctocat"
        "&per_page=100&page=1"
    )
    reviewed = (
        f"{origin}/search/issues?q=repo%3Ao%2Fr+is%3Apr+reviewed-by%3Aoctocat"
        "&per_page=100&page=1"
    )
    routes = {
        repository: [(200, {}, {"id": 7, "full_name": "o/r", "default_branch": "main"})],
        commits: [(200, {}, [])],
        authored: [(200, {}, {"total_count": 0, "incomplete_results": True, "items": []})],
        reviewed: [(200, {}, {"total_count": 0, "incomplete_results": False, "items": []})],
    }
    partial = GitHubApi(spec(actor="octocat"), RouteTransport(routes)).fetch_deep_activity()
    assert partial.complete is False
    assert partial.notes == ("deep_search_incomplete",)

    wrong_repo_routes = {
        repository: [(200, {}, {"id": 7, "full_name": "o/r", "default_branch": "main"})],
        commits: [(200, {}, [])],
        authored: [(200, {}, {
            "total_count": 1,
            "incomplete_results": False,
            "items": [{
                "id": 41,
                "number": 8,
                "title": "wrong repository",
                "state": "open",
                "created_at": "2026-09-20T01:02:03Z",
                "user": {"login": "octocat"},
                "repository_url": f"{origin}/repos/other/repo",
                "pull_request": {},
            }],
        })],
    }
    with pytest.raises(GitHubApiError, match="github_deep_pull_request_invalid"):
        GitHubApi(spec(actor="octocat"), RouteTransport(wrong_repo_routes)).fetch_deep_activity()


def test_deep_review_page_cap_is_partial_and_duplicate_review_fails_closed() -> None:
    origin = "https://api.github.com"
    repository = f"{origin}/repos/o/r"
    commits = f"{repository}/commits?author=octocat&per_page=100&page=1&sha=main"
    authored = (
        f"{origin}/search/issues?q=repo%3Ao%2Fr+is%3Apr+author%3Aoctocat"
        "&per_page=100&page=1"
    )
    reviewed = (
        f"{origin}/search/issues?q=repo%3Ao%2Fr+is%3Apr+reviewed-by%3Aoctocat"
        "&per_page=100&page=1"
    )
    candidate = {
        "id": 80,
        "number": 12,
        "title": "Reviewed PR",
        "state": "closed",
        "created_at": "2026-09-18T01:02:03Z",
        "user": {"login": "author"},
        "repository_url": repository,
        "pull_request": {},
    }
    routes: dict[str, list[tuple[int, dict[str, str], Any]]] = {
        repository: [(200, {}, {"id": 7, "full_name": "o/r", "default_branch": "main"})],
        commits: [(200, {}, [])],
        authored: [(200, {}, {"total_count": 0, "incomplete_results": False, "items": []})],
        reviewed: [(200, {}, {"total_count": 1, "incomplete_results": False, "items": [candidate]})],
    }
    other_reviews = [
        {
            "id": page * 100 + index + 1,
            "user": {"login": "other"},
            "submitted_at": "2026-09-20T04:05:06Z",
            "state": "COMMENTED",
        }
        for page in range(2)
        for index in range(100)
    ]
    routes[f"{repository}/pulls/12/reviews?per_page=100&page=1"] = [
        (200, {}, other_reviews[:100])
    ]
    routes[f"{repository}/pulls/12/reviews?per_page=100&page=2"] = [
        (200, {}, other_reviews[100:])
    ]
    partial = GitHubApi(spec(actor="octocat"), RouteTransport(routes)).fetch_deep_activity()
    assert partial.items == ()
    assert partial.complete is False
    assert partial.notes == ("deep_review_pages_truncated",)

    review = {
        "id": 91,
        "user": {"login": "octocat"},
        "submitted_at": "2026-09-20T04:05:06Z",
        "state": "APPROVED",
    }
    duplicate_routes = {
        repository: [(200, {}, {"id": 7, "full_name": "o/r", "default_branch": "main"})],
        commits: [(200, {}, [])],
        authored: [(200, {}, {"total_count": 0, "incomplete_results": False, "items": []})],
        reviewed: [(200, {}, {"total_count": 1, "incomplete_results": False, "items": [candidate]})],
        f"{repository}/pulls/12/reviews?per_page=100&page=1": [(200, {}, [review, review])],
    }
    with pytest.raises(GitHubApiError, match="github_deep_activity_duplicate"):
        GitHubApi(spec(actor="octocat"), RouteTransport(duplicate_routes)).fetch_deep_activity()


def test_deep_pull_request_fifth_page_boundary_is_executable() -> None:
    origin = "https://api.github.com"
    repository = f"{origin}/repos/o/r"

    def pull(number: int) -> dict[str, Any]:
        return {
            "id": 10_000 + number,
            "number": number,
            "title": f"PR {number}",
            "state": "open",
            "created_at": "2026-09-20T01:02:03Z",
            "user": {"login": "octocat"},
            "repository_url": repository,
            "pull_request": {},
        }

    def fetch(count: int) -> GitHubActivityBatch:
        routes: dict[str, list[tuple[int, dict[str, str], Any]]] = {
            repository: [(200, {}, {"id": 7, "full_name": "o/r", "default_branch": "main"})],
            f"{repository}/commits?author=octocat&per_page=100&page=1&sha=main": [(200, {}, [])],
            (
                f"{origin}/search/issues?q=repo%3Ao%2Fr+is%3Apr+reviewed-by%3Aoctocat"
                "&per_page=100&page=1"
            ): [(200, {}, {"total_count": 0, "incomplete_results": False, "items": []})],
        }
        for page in range(1, 6):
            start = (page - 1) * 100
            page_items = [pull(number) for number in range(start + 1, min(count, start + 100) + 1)]
            query = (
                f"{origin}/search/issues?q=repo%3Ao%2Fr+is%3Apr+author%3Aoctocat"
                f"&per_page=100&page={page}"
            )
            routes[query] = [(200, {}, {
                "total_count": count, "incomplete_results": False, "items": page_items,
            })]
        return GitHubApi(spec(actor="octocat"), RouteTransport(routes)).fetch_deep_activity()

    below = fetch(499)
    assert len(below.items) == 499
    assert below.complete is True

    at_cap = fetch(500)
    assert len(at_cap.items) == 500
    assert "deep_search_truncated" in at_cap.notes
    assert_partial_activity_preserves_prior(at_cap)


def test_deep_search_count_change_is_partial() -> None:
    origin = "https://api.github.com"
    first = (
        f"{origin}/search/issues?q=repo%3Ao%2Fr+is%3Apr+author%3Aoctocat"
        "&per_page=100&page=1"
    )
    second = first[:-1] + "2"
    transport = RouteTransport({
        first: [(200, {}, {
            "total_count": 101, "incomplete_results": False,
            "items": [{"id": number} for number in range(100)],
        })],
        second: [(200, {}, {
            "total_count": 100, "incomplete_results": False, "items": [{"id": 100}],
        })],
    })
    _items, complete, notes = GitHubApi(spec(actor="octocat"), transport)._search_pull_requests(
        "author:octocat", max_pages=5,
    )
    assert complete is False
    assert "deep_search_count_changed" in notes


def test_deep_review_candidate_and_request_boundaries_are_executable() -> None:
    origin = "https://api.github.com"
    repository = f"{origin}/repos/o/r"

    def candidate(number: int) -> dict[str, Any]:
        return {
            "id": 20_000 + number,
            "number": number,
            "title": f"Candidate {number}",
            "state": "closed",
            "created_at": "2026-09-18T01:02:03Z",
            "user": {"login": "author"},
            "repository_url": repository,
            "pull_request": {},
        }

    def routes_for(count: int, *, two_full_pages: bool = False) -> dict[str, list[tuple[int, dict[str, str], Any]]]:
        candidates = [candidate(number) for number in range(1, count + 1)]
        routes: dict[str, list[tuple[int, dict[str, str], Any]]] = {
            repository: [(200, {}, {"id": 7, "full_name": "o/r", "default_branch": "main"})],
            f"{repository}/commits?author=octocat&per_page=100&page=1&sha=main": [(200, {}, [])],
            (
                f"{origin}/search/issues?q=repo%3Ao%2Fr+is%3Apr+author%3Aoctocat"
                "&per_page=100&page=1"
            ): [(200, {}, {"total_count": 0, "incomplete_results": False, "items": []})],
            (
                f"{origin}/search/issues?q=repo%3Ao%2Fr+is%3Apr+reviewed-by%3Aoctocat"
                "&per_page=100&page=1"
            ): [(200, {}, {
                "total_count": count, "incomplete_results": False, "items": candidates,
            })],
        }
        for number in range(1, count + 1):
            first = [] if not two_full_pages else [
                {
                    "id": number * 1000 + index,
                    "user": {"login": "other"},
                    "submitted_at": "2026-09-20T04:05:06Z",
                    "state": "COMMENTED",
                }
                for index in range(100)
            ]
            routes[f"{repository}/pulls/{number}/reviews?per_page=100&page=1"] = [(200, {}, first)]
            if two_full_pages and number <= 50:
                routes[f"{repository}/pulls/{number}/reviews?per_page=100&page=2"] = [(200, {}, first)]
        return routes

    below_transport = RouteTransport(routes_for(99))
    below = GitHubApi(spec(actor="octocat"), below_transport).fetch_deep_activity()
    assert below.complete is True
    assert len([call for call in below_transport.calls if "/reviews?" in call[0]]) == 99

    candidate_transport = RouteTransport(routes_for(100))
    at_candidate_cap = GitHubApi(spec(actor="octocat"), candidate_transport).fetch_deep_activity()
    assert len([call for call in candidate_transport.calls if "/reviews?" in call[0]]) == 100
    assert_partial_activity_preserves_prior(at_candidate_cap)

    request_transport = RouteTransport(routes_for(51, two_full_pages=True))
    at_request_cap = GitHubApi(spec(actor="octocat"), request_transport).fetch_deep_activity()
    review_calls = [call for call in request_transport.calls if "/reviews?" in call[0]]
    assert len(review_calls) == 100
    assert not any("/pulls/51/reviews" in call[0] for call in review_calls)
    assert_partial_activity_preserves_prior(at_request_cap)


def test_deep_review_item_500_boundary_is_executable() -> None:
    origin = "https://api.github.com"
    repository = f"{origin}/repos/o/r"

    def fetch(count: int) -> GitHubActivityBatch:
        sizes = [99, 99, 99, 99, 99, count - 495]
        candidates = [{
            "id": 30_000 + number,
            "number": number,
            "title": f"Candidate {number}",
            "state": "closed",
            "created_at": "2026-09-18T01:02:03Z",
            "user": {"login": "author"},
            "repository_url": repository,
            "pull_request": {},
        } for number in range(1, 7)]
        routes: dict[str, list[tuple[int, dict[str, str], Any]]] = {
            repository: [(200, {}, {"id": 7, "full_name": "o/r", "default_branch": "main"})],
            f"{repository}/commits?author=octocat&per_page=100&page=1&sha=main": [(200, {}, [])],
            (
                f"{origin}/search/issues?q=repo%3Ao%2Fr+is%3Apr+author%3Aoctocat"
                "&per_page=100&page=1"
            ): [(200, {}, {"total_count": 0, "incomplete_results": False, "items": []})],
            (
                f"{origin}/search/issues?q=repo%3Ao%2Fr+is%3Apr+reviewed-by%3Aoctocat"
                "&per_page=100&page=1"
            ): [(200, {}, {
                "total_count": 6, "incomplete_results": False, "items": candidates,
            })],
        }
        review_id = 1
        for number, size in enumerate(sizes, 1):
            values = []
            for _ in range(size):
                values.append({
                    "id": review_id,
                    "user": {"login": "octocat"},
                    "submitted_at": "2026-09-20T04:05:06Z",
                    "state": "APPROVED",
                })
                review_id += 1
            routes[f"{repository}/pulls/{number}/reviews?per_page=100&page=1"] = [(200, {}, values)]
        return GitHubApi(spec(actor="octocat"), RouteTransport(routes)).fetch_deep_activity()

    below = fetch(499)
    assert len(below.items) == 499
    assert below.complete is True
    at_cap = fetch(500)
    assert len(at_cap.items) == 500
    assert "deep_review_item_budget_exhausted" in at_cap.notes
    assert_partial_activity_preserves_prior(at_cap)


def test_activity_scan_never_withdraws_from_partial_commit_history() -> None:
    item = {
        "activity_id": "1" * 40,
        "activity_key": "commit:" + "1" * 40,
        "activity_kind": "commit",
        "actor": "octocat",
        "commit": "1" * 40,
        "mode": "deep",
        "occurred_at": "2026-09-20T01:02:03+00:00",
        "title": "Initial commit",
    }
    first = scan_github_activity(
        GitHubActivityBatch(7, "o/r", (item,), True, ()),
        "source", None, ("github.deep", "1"),
    )
    partial = scan_github_activity(
        GitHubActivityBatch(7, "o/r", (), False, ("deep_commits_truncated",)),
        "source", first, ("github.deep", "1"),
    )

    assert partial.delta.operations == ()
    assert partial.snapshot.items == first.snapshot.items
    assert partial.snapshot.coverage == "partial"


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
