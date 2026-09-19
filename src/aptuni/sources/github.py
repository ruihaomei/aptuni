"""Bounded GitHub Standard source and deterministic snapshot reconciliation.

Identity: ``repository_id`` anchors the source (owner/name may change); the
resolved commit makes a snapshot reproducible; ``path`` is the item key and the
blob SHA is content identity only. Standard mode selects a bounded, sticky,
deterministic subset. A truncated tree or an unselected-but-present item means
coverage is partial, which never proves disappearance.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter, deque
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Any, Protocol

from aptuni.sources.folder import EXCLUDED_DIRS, is_secret
from aptuni.sources.reconcile import KeyedSpec, Observed, reconcile_keyed
from aptuni.sources.records import CandidateDelta, Snapshot

MANIFESTS = frozenset({"pyproject.toml", "package.json", "requirements.txt", "cargo.toml", "go.mod",
                       "setup.cfg", "pom.xml", "build.gradle"})
SOURCE_SUFFIXES = frozenset({".py", ".ts", ".js", ".rs", ".go", ".java", ".ipynb", ".r", ".jl"})
TEXT_SUFFIXES = SOURCE_SUFFIXES | frozenset({".md", ".txt", ".toml", ".json", ".yaml", ".yml", ".ini", ".cfg"})
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
DEFAULT_BUDGET = 40
DEFAULT_API_ORIGIN = "https://api.github.com"
API_VERSION = "2022-11-28"
MAX_JSON_BYTES = 8_500_000
MAX_BLOB_BYTES = 1_000_000
MAX_TREE_REQUESTS = 200
MAX_TREE_ENTRIES = 100_000
MAX_REDIRECTS = 3
GITHUB_EXCLUDED_DIRS = EXCLUDED_DIRS | frozenset({".cache", ".pytest_cache", ".mypy_cache", ".ruff_cache"})


class SourceIdentityError(ValueError):
    """The observed repository is not the configured source (fixed code only)."""


class GitHubApiError(RuntimeError):
    """A bounded, sanitized provider error safe to map at the application boundary."""


@dataclass(frozen=True)
class GitHubSourceSpec:
    owner: str
    repository: str
    repository_url: str
    api_origin: str = DEFAULT_API_ORIGIN
    ref: str | None = None
    token_env: str | None = None

    @classmethod
    def build(
        cls,
        repository_url: str,
        *,
        api_origin: str = DEFAULT_API_ORIGIN,
        ref: str | None = None,
        token_env: str | None = None,
    ) -> GitHubSourceSpec:
        repo = urllib.parse.urlsplit(repository_url.rstrip("/"))
        api = urllib.parse.urlsplit(api_origin.rstrip("/"))
        try:
            repo_port, api_port = repo.port, api.port
        except ValueError as error:
            raise SourceIdentityError("github_origin_port_invalid") from error
        parts = tuple(part for part in repo.path.split("/") if part)
        if (repo.scheme.lower() != "https" or repo.query or repo.fragment or len(parts) != 2
                or repo.username is not None or repo.password is not None or repo_port is not None):
            raise SourceIdentityError("github_repository_url_invalid")
        if (api.scheme.lower() != "https" or not api.netloc or api.query or api.fragment
                or api.username is not None or api.password is not None or api_port is not None):
            raise SourceIdentityError("github_api_origin_invalid")
        repo_host = (repo.hostname or "").lower()
        api_host = (api.hostname or "").lower()
        if (not re.fullmatch(r"[a-z0-9.-]+", repo_host) or not re.fullmatch(r"[a-z0-9.-]+", api_host)
                or repo_host.startswith(".") or api_host.startswith(".")):
            raise SourceIdentityError("github_origin_host_invalid")
        canonical_repository_url = f"https://{repo_host}/{'/'.join(parts)}"
        canonical_api_origin = f"https://{api_host}{api.path.rstrip('/')}"
        if repo_host == "github.com":
            if canonical_api_origin != DEFAULT_API_ORIGIN:
                raise SourceIdentityError("github_api_origin_mismatch")
        elif api_host != repo_host or api.path.rstrip("/") != "/api/v3":
            raise SourceIdentityError("github_api_origin_mismatch")
        if any(not re.fullmatch(r"[A-Za-z0-9_.-]+", part) for part in parts):
            raise SourceIdentityError("github_repository_url_invalid")
        if ref is not None and (not ref or len(ref.encode("utf-8")) > 255 or any(c in ref for c in "?#")):
            raise SourceIdentityError("github_ref_invalid")
        if token_env is not None and not re.fullmatch(r"[A-Z][A-Z0-9_]{0,127}", token_env):
            raise SourceIdentityError("github_token_reference_invalid")
        return cls(parts[0], parts[1], canonical_repository_url, canonical_api_origin, ref, token_env)

    def roots(self) -> tuple[str, ...]:
        values = [self.repository_url, f"api:{self.api_origin}"]
        if self.ref is not None:
            values.append(f"ref:{self.ref}")
        if self.token_env is not None:
            values.append(f"env:{self.token_env}")
        return tuple(values)

    @classmethod
    def from_roots(cls, roots: tuple[str, ...]) -> GitHubSourceSpec:
        if not roots:
            raise SourceIdentityError("github_source_config_invalid")
        options: dict[str, str] = {}
        for value in roots[1:]:
            prefix, separator, payload = value.partition(":")
            if not separator or prefix not in {"api", "ref", "env"} or prefix in options:
                raise SourceIdentityError("github_source_config_invalid")
            options[prefix] = payload
        return cls.build(roots[0], api_origin=options.get("api", DEFAULT_API_ORIGIN),
                         ref=options.get("ref"), token_env=options.get("env"))


@dataclass(frozen=True)
class HttpResult:
    status: int
    url: str
    headers: Mapping[str, str]
    body: bytes


class GitHubTransport(Protocol):
    def get(self, url: str, headers: Mapping[str, str], max_bytes: int) -> HttpResult: ...


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(
        self,
        req: urllib.request.Request,
        fp: Any,
        code: int,
        msg: str,
        headers: Any,
        newurl: str,
    ) -> None:
        return None


class UrllibGitHubTransport:
    """HTTPS transport that returns redirects to the caller for explicit origin checks."""

    def get(self, url: str, headers: Mapping[str, str], max_bytes: int) -> HttpResult:
        request = urllib.request.Request(url, headers=dict(headers), method="GET")
        opener = urllib.request.build_opener(_NoRedirect())
        try:
            response = opener.open(request, timeout=20)
        except urllib.error.HTTPError as error:
            response = error
        except (OSError, urllib.error.URLError) as error:
            raise GitHubApiError("github_network_failed") from error
        with response:
            body = response.read(max_bytes + 1)
            if len(body) > max_bytes:
                raise GitHubApiError("github_response_too_large")
            normalized = {key.lower(): value for key, value in response.headers.items()}
            return HttpResult(int(response.status), response.geturl(), normalized, body)


@dataclass(frozen=True)
class GitHubTree:
    data: dict[str, Any]
    default_branch: str
    notes: tuple[str, ...]


class GitHubApi:
    """Small REST client with exact-origin redirects and explicit traversal budgets."""

    def __init__(self, spec: GitHubSourceSpec, transport: GitHubTransport | None = None) -> None:
        self.spec = spec
        self.transport = transport or UrllibGitHubTransport()

    def _headers(self) -> dict[str, str]:
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": API_VERSION,
            "User-Agent": "aptuni/0.1 github-standard",
        }
        if self.spec.token_env is not None:
            token = os.environ.get(self.spec.token_env)
            if not token:
                raise GitHubApiError("github_credential_unavailable")
            if token != token.strip() or any(character in token for character in "\r\n"):
                raise GitHubApiError("github_credential_invalid")
            headers["Authorization"] = f"Bearer {token}"
        return headers

    @staticmethod
    def _require_api_url(url: str, expected: urllib.parse.SplitResult, error_prefix: str) -> None:
        actual = urllib.parse.urlsplit(url)
        if (actual.scheme, actual.netloc) != (expected.scheme, expected.netloc):
            raise GitHubApiError(f"github_{error_prefix}_origin_denied")
        if not actual.path.startswith(expected.path.rstrip("/") + "/"):
            raise GitHubApiError(f"github_{error_prefix}_path_denied")

    def _json(self, path: str, *, max_bytes: int = MAX_JSON_BYTES) -> tuple[Any, Mapping[str, str]]:
        if not path.startswith("/"):
            raise GitHubApiError("github_request_path_invalid")
        url = self.spec.api_origin + path
        expected = urllib.parse.urlsplit(self.spec.api_origin)
        for _ in range(MAX_REDIRECTS + 1):
            result = self.transport.get(url, self._headers(), max_bytes)
            self._require_api_url(result.url, expected, "response")
            if result.status in {301, 302, 307, 308}:
                location = result.headers.get("location")
                if not location:
                    raise GitHubApiError("github_redirect_invalid")
                target = urllib.parse.urlsplit(urllib.parse.urljoin(url, location))
                self._require_api_url(urllib.parse.urlunsplit(target), expected, "redirect")
                url = urllib.parse.urlunsplit(target)
                continue
            if result.status in {403, 429}:
                if "retry-after" in result.headers:
                    raise GitHubApiError("github_rate_limited_retry_after")
                if result.headers.get("x-ratelimit-remaining") == "0":
                    raise GitHubApiError("github_rate_limited_reset")
                raise GitHubApiError("github_access_denied")
            if result.status != 200:
                raise GitHubApiError("github_request_failed")
            content_type = result.headers.get("content-type", "").split(";", 1)[0].strip().lower()
            if content_type not in {"application/json", "application/vnd.github+json"}:
                raise GitHubApiError("github_content_type_invalid")
            try:
                return json.loads(result.body), result.headers
            except (UnicodeDecodeError, json.JSONDecodeError) as error:
                raise GitHubApiError("github_json_invalid") from error
        raise GitHubApiError("github_redirect_limit")

    def fetch_tree(self) -> GitHubTree:
        slug = f"{urllib.parse.quote(self.spec.owner)}/{urllib.parse.quote(self.spec.repository)}"
        repo, _ = self._json(f"/repos/{slug}")
        if not isinstance(repo, dict):
            raise GitHubApiError("github_repository_response_invalid")
        repository_id = repo.get("id")
        full_name = repo.get("full_name")
        default_branch = repo.get("default_branch")
        if not isinstance(repository_id, int) or not isinstance(full_name, str) or not isinstance(default_branch, str):
            raise GitHubApiError("github_repository_response_invalid")
        requested_ref = self.spec.ref or default_branch
        commit, _ = self._json(f"/repos/{slug}/commits/{urllib.parse.quote(requested_ref, safe='')}")
        commit_sha = commit.get("sha") if isinstance(commit, dict) else None
        if not isinstance(commit_sha, str) or not SHA_RE.fullmatch(commit_sha):
            raise GitHubApiError("github_commit_response_invalid")
        recursive, _ = self._json(f"/repos/{slug}/git/trees/{commit_sha}?recursive=1")
        if not isinstance(recursive, dict) or not isinstance(recursive.get("tree"), list):
            raise GitHubApiError("github_tree_response_invalid")
        notes: set[str] = set()
        entries = recursive["tree"]
        truncated = bool(recursive.get("truncated"))
        if truncated:
            notes.add("recursive_tree_truncated")
            entries, complete = self._walk_tree(slug, commit_sha)
            truncated = not complete
            if complete:
                notes.add("recursive_tree_recovered")
            else:
                notes.add("tree_traversal_budget_exhausted")
        return GitHubTree({"repository_id": repository_id, "full_name": full_name, "commit": commit_sha,
                           "truncated": truncated, "tree": entries}, default_branch, tuple(sorted(notes)))

    def _walk_tree(self, slug: str, root_sha: str) -> tuple[list[dict[str, Any]], bool]:
        pending: deque[tuple[str, str]] = deque([("", root_sha)])
        blobs: list[dict[str, Any]] = []
        requests = 0
        while pending and requests < MAX_TREE_REQUESTS and len(blobs) < MAX_TREE_ENTRIES:
            prefix, sha = pending.popleft()
            value, _ = self._json(f"/repos/{slug}/git/trees/{sha}")
            requests += 1
            if not isinstance(value, dict) or not isinstance(value.get("tree"), list) or value.get("truncated"):
                return blobs, False
            seen: set[str] = set()
            for raw in value["tree"]:
                if not isinstance(raw, dict) or not isinstance(raw.get("path"), str):
                    raise GitHubApiError("github_tree_response_invalid")
                relative = raw["path"]
                kind, child_sha = raw.get("type"), raw.get("sha")
                if (not _valid_path(relative) or relative in seen or kind not in {"blob", "tree", "commit"}
                        or not isinstance(child_sha, str) or not SHA_RE.fullmatch(child_sha)):
                    raise GitHubApiError("github_tree_response_invalid")
                assert isinstance(child_sha, str)
                seen.add(relative)
                path = f"{prefix}/{relative}" if prefix else relative
                if kind == "tree":
                    pending.append((path, child_sha))
                elif kind == "blob":
                    blobs.append(dict(raw) | {"path": path})
                    if len(blobs) >= MAX_TREE_ENTRIES:
                        break
        return blobs, not pending and len(blobs) < MAX_TREE_ENTRIES

    def fetch_blob(self, sha: str) -> bytes:
        if not SHA_RE.fullmatch(sha):
            raise GitHubApiError("github_blob_sha_invalid")
        slug = f"{urllib.parse.quote(self.spec.owner)}/{urllib.parse.quote(self.spec.repository)}"
        value, _ = self._json(f"/repos/{slug}/git/blobs/{sha}", max_bytes=MAX_BLOB_BYTES * 2)
        if (not isinstance(value, dict) or value.get("sha") != sha or value.get("encoding") != "base64"
                or not isinstance(value.get("content"), str)):
            raise GitHubApiError("github_blob_response_invalid")
        try:
            encoded = "".join(value["content"].split())
            body = base64.b64decode(encoded, validate=True)
        except (ValueError, TypeError) as error:
            raise GitHubApiError("github_blob_response_invalid") from error
        if len(body) > MAX_BLOB_BYTES:
            raise GitHubApiError("github_blob_too_large")
        if type(value.get("size")) is not int or value["size"] != len(body):
            raise GitHubApiError("github_blob_response_invalid")
        git_sha = hashlib.sha1(f"blob {len(body)}\0".encode() + body, usedforsecurity=False).hexdigest()
        if git_sha != sha:
            raise GitHubApiError("github_blob_identity_mismatch")
        return body


@dataclass(frozen=True)
class GitHubScan:
    snapshot: Snapshot
    delta: CandidateDelta
    parser: tuple[str, str]
    repository_id: int
    notes: tuple[str, ...]


def _selection_reason(path: str) -> tuple[int, str]:
    if _excluded_path(path) is not None:
        return 5, "excluded"
    name = PurePosixPath(path).name.lower()
    if name.startswith("readme"):
        return 0, "readme"
    if name in MANIFESTS:
        return 1, "manifest"
    if PurePosixPath(name).suffix in SOURCE_SUFFIXES:
        return 2, "representative_source"
    if PurePosixPath(name).suffix in TEXT_SUFFIXES:
        return 3, "documentation"
    return 4, "other"


def _valid_path(path: str) -> bool:
    parts = path.split("/")
    return bool(path) and not path.startswith("/") and "\x00" not in path and all(
        part not in {"", ".", ".."} for part in parts
    )


def _excluded_path(path: str) -> str | None:
    if not _valid_path(path):
        return "invalid_path"
    parts = PurePosixPath(path).parts
    if any(part.startswith(".") or part in GITHUB_EXCLUDED_DIRS for part in parts[:-1]):
        return "excluded_dir_skipped"
    if parts[-1].startswith(".") or is_secret(parts[-1]):
        return "secret_skipped" if is_secret(parts[-1]) else "hidden_skipped"
    return None


def _validated(data: dict[str, Any]) -> tuple[int, str, str, bool, dict[str, str]]:
    repository_id = data.get("repository_id")
    commit = str(data.get("commit", ""))
    if not isinstance(repository_id, int) or not SHA_RE.match(commit):
        raise SourceIdentityError("github_response_invalid")
    blobs: dict[str, str] = {}
    tree = data.get("tree")
    if not isinstance(tree, list):
        raise SourceIdentityError("github_tree_invalid")
    seen: set[str] = set()
    for entry in tree:
        if not isinstance(entry, Mapping) or not isinstance(entry.get("path"), str):
            raise SourceIdentityError("github_tree_entry_invalid")
        path, kind, sha = entry["path"], entry.get("type"), entry.get("sha")
        if not _valid_path(path) or path in seen or kind not in {"blob", "tree", "commit"}:
            raise SourceIdentityError("github_tree_entry_invalid")
        seen.add(path)
        if not isinstance(sha, str) or not SHA_RE.fullmatch(sha):
            raise SourceIdentityError("github_blob_sha_invalid")
        if entry.get("type") != "blob":
            continue
        blobs[path] = sha
    return repository_id, commit, str(data.get("full_name", "")), bool(data.get("truncated")), blobs


def scan_github(
    data: dict[str, Any],
    source_id: str,
    previous: GitHubScan | None,
    parser: tuple[str, str],
    budget: int = DEFAULT_BUDGET,
) -> GitHubScan:
    repository_id, commit, full_name, truncated, blobs = _validated(data)
    if previous is not None and previous.repository_id != repository_id:
        raise SourceIdentityError("repository_identity_changed")
    notes = {"tree_truncated"} if truncated else set()
    excluded = {_excluded_path(path) for path in blobs}
    notes.update(reason for reason in excluded if reason is not None)
    eligible = {path for path in blobs if _selection_reason(path)[1] not in {"other", "excluded"}}

    previous_reasons = {
        item.locator.extension.fields["path"]: item.locator.extension.fields["selection_reason"]
        for item in (previous.snapshot.items if previous else ())
    }
    sticky = sorted(path for path in previous_reasons if path in eligible)
    # A known item renamed out of its path keeps first claim on a budget slot (review F3).
    vanished_blobs = {
        item.locator.extension.fields["blob"]
        for item in (previous.snapshot.items if previous else ())
        if not item.held and item.locator.extension.fields["path"] not in blobs
    }
    fresh_paths = [path for path in eligible if path not in previous_reasons]
    fresh_per_blob = Counter(blobs[path] for path in fresh_paths)
    # Only an unambiguous rename target is prioritized; a common blob (e.g. empty file) cannot flood.
    priority = {blob for blob in vanished_blobs if fresh_per_blob[blob] == 1}
    fresh = sorted(fresh_paths, key=lambda path: (blobs[path] not in priority, _selection_reason(path)[0],
                                                  path.count("/"), path))
    selected = (sticky + fresh)[:budget]
    dropped = set(sticky) - set(selected)
    if dropped:
        notes.add("selection_budget_dropped_known_items")
    coverage = "partial" if truncated or dropped else "complete"

    observed = [
        Observed(path, "gitblob:" + blobs[path], {
            "repository_id": repository_id,
            "commit": commit,
            "blob": blobs[path],
            "owner_name": full_name,
            "mode": "standard",
            "selection_reason": previous_reasons.get(path, _selection_reason(path)[1]),
        })
        for path in selected
    ]
    spec = KeyedSpec(source_id, "github", "github.locator", 1, "path")
    parser_changed = previous is not None and previous.parser != parser
    result = reconcile_keyed(spec, previous.snapshot if previous else None, observed, coverage, parser_changed)
    delta = CandidateDelta.build(
        source_id,
        previous.snapshot.snapshot_id if previous else None,
        result.snapshot.snapshot_id,
        parser,
        result.operations,
        sequence=previous.delta.sequence + 1 if previous else 1,
    )
    return GitHubScan(result.snapshot, delta, parser, repository_id, tuple(sorted(notes)))
