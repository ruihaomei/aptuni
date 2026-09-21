#!/usr/bin/env python3
"""Dependency, license, secret and built-artifact checks used locally and in CI."""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
import tarfile
import tomllib
import zipfile
from pathlib import Path

NOTICE_HEADING = "## Distributed runtime dependencies"
TABLE_ROW = re.compile(r"^\| ([^|]+) \| ([^|]+) \| ([^|]+) \|")
SECRET_PATTERNS = {
    "private key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----"),
    "AWS access key": re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b"),
    "GitHub token": re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})\b"),
    "OpenAI-style key": re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{20,}\b"),
}
KNOWN_PUBLIC_EXAMPLES = {"AKIAIOSFODNN7EXAMPLE"}
REQUIRED_LEGAL_FILES = {"LICENSE", "NOTICE", "THIRD_PARTY_NOTICES.md"}
ACTION_USE = re.compile(r"^\s*-\s+uses:\s+([^\s#]+)", re.MULTILINE)
COMMIT_SHA = re.compile(r"^[0-9a-f]{40}$")


def runtime_packages(lock_path: Path) -> dict[str, str]:
    """Return the complete cross-platform runtime closure recorded by uv.lock."""
    value = tomllib.loads(lock_path.read_text(encoding="utf-8"))
    packages = {item["name"]: item for item in value["package"]}
    if "aptuni" not in packages:
        raise ValueError("uv.lock has no aptuni project package")
    found = {"aptuni"}
    pending: list[tuple[str, frozenset[str]]] = [("aptuni", frozenset())]
    processed: set[tuple[str, frozenset[str]]] = set()
    while pending:
        name, extras = pending.pop()
        state = (name, extras)
        if state in processed:
            continue
        processed.add(state)
        package = packages[name]
        dependencies = list(package.get("dependencies", ()))
        optional = package.get("optional-dependencies", {})
        for extra in extras:
            dependencies.extend(optional.get(extra, ()))
        for dependency in dependencies:
            name = dependency["name"]
            if name not in packages:
                raise ValueError(f"uv.lock dependency has no package entry: {name}")
            found.add(name)
            pending.append((name, frozenset(dependency.get("extra", ()))))
    return {name: str(packages[name]["version"]) for name in sorted(found - {"aptuni"})}


def notice_packages(notice_path: Path) -> dict[str, str]:
    text = notice_path.read_text(encoding="utf-8")
    try:
        section = text.split(NOTICE_HEADING, 1)[1].split("\n## ", 1)[0]
    except IndexError as error:
        raise ValueError("THIRD_PARTY_NOTICES.md has no runtime dependency section") from error
    result: dict[str, str] = {}
    for line in section.splitlines():
        match = TABLE_ROW.match(line)
        if match and match.group(1) != "Package" and not set(match.group(1)) <= {"-"}:
            result[match.group(1).strip().lower()] = match.group(2).strip()
    return result


def check_notices(root: Path) -> list[str]:
    locked = runtime_packages(root / "uv.lock")
    noticed = notice_packages(root / "THIRD_PARTY_NOTICES.md")
    errors = [f"runtime dependency missing from notices: {name}=={locked[name]}"
              for name in sorted(locked.keys() - noticed.keys())]
    errors += [f"notice lists non-runtime dependency: {name}=={noticed[name]}"
               for name in sorted(noticed.keys() - locked.keys())]
    errors += [f"notice version for {name} is {noticed[name]}, lock has {locked[name]}"
               for name in sorted(locked.keys() & noticed.keys()) if noticed[name] != locked[name]]
    return errors


def tracked_files(root: Path) -> tuple[Path, ...]:
    output = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
        cwd=root,
        check=True,
        capture_output=True,
    ).stdout.decode("utf-8")
    return tuple(root / name for name in output.split("\0") if name)


def check_secrets(paths: tuple[Path, ...], root: Path) -> list[str]:
    errors: list[str] = []
    for path in paths:
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for label, pattern in SECRET_PATTERNS.items():
            for match in pattern.finditer(text):
                if match.group(0) in KNOWN_PUBLIC_EXAMPLES:
                    continue
                line = text.count("\n", 0, match.start()) + 1
                errors.append(f"possible {label} in {path.relative_to(root)}:{line}")
    return errors


def _artifact_members(path: Path) -> set[str]:
    if path.suffix == ".whl":
        with zipfile.ZipFile(path) as archive:
            return set(archive.namelist())
    if path.name.endswith(".tar.gz"):
        with tarfile.open(path, "r:gz") as archive:
            return {member.name for member in archive.getmembers()}
    raise ValueError(f"unsupported distribution artifact: {path}")


def check_artifacts(paths: tuple[Path, ...]) -> list[str]:
    errors: list[str] = []
    for path in paths:
        members = _artifact_members(path)
        basenames = {Path(member).name for member in members}
        for required in sorted(REQUIRED_LEGAL_FILES - basenames):
            errors.append(f"{path.name} is missing {required}")
    return errors


def check_workflow(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    errors: list[str] = []
    if not re.search(r"(?m)^permissions:\n  contents: read$", text):
        errors.append("CI workflow must declare top-level read-only contents permission")
    if "persist-credentials: false" not in text:
        errors.append("CI checkout must disable persisted credentials")
    if "uvx " in text:
        errors.append("CI must run supply-chain tools from the locked environment, not uvx")
    if text.count("uv build --offline --no-build-isolation") < 2:
        errors.append("CI reproducibility builds must use the locked backend without network access")
    if "--require-hashes" not in text or "--no-deps build-a/*.whl" not in text:
        errors.append("CI clean-wheel smoke must install the audited hashes before the wheel")
    if "--no-install-project" not in text or "--all-groups --no-build-isolation" not in text:
        errors.append("CI sync must seed locked build tools before building the project")
    if "tools/run_evals.py --sbom artifacts/aptuni.cdx.json" not in text:
        errors.append("CI must retain a frozen evaluation manifest tied to the generated SBOM")
    steps = re.split(r"(?m)(?=^      - )", text)
    evaluation_upload = next((
        step for step in steps
        if "uses: actions/upload-artifact@" in step and "path: artifacts/eval-run.json" in step
    ), None)
    required_condition = "if: always() && hashFiles('artifacts/eval-run.json') != ''"
    if (evaluation_upload is None or required_condition not in evaluation_upload
            or "retention-days: 14" not in evaluation_upload):
        errors.append("CI must upload a written evaluation manifest even when its threshold step fails")
    for reference in ACTION_USE.findall(text):
        if reference.startswith("./"):
            continue
        if "@" not in reference or not COMMIT_SHA.fullmatch(reference.rsplit("@", 1)[1]):
            errors.append(f"CI action is not pinned to an immutable commit: {reference}")
    return errors


def check_release_workflow(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    errors: list[str] = []
    if not re.search(r"(?m)^permissions:\n  contents: read$", text):
        errors.append("release workflow must default to read-only contents permission")
    if '      - "v[0-9]+.[0-9]+.[0-9]+"' not in text or "workflow_dispatch" in text:
        errors.append("release workflow must publish only from semantic-version tag pushes")
    if "persist-credentials: false" not in text:
        errors.append("release checkout must disable persisted credentials")
    if text.count("id-token: write") != 1 or "environment:\n      name: pypi" not in text:
        errors.append("release publish job must have the sole OIDC permission in the pypi environment")
    if text.count("uv build --offline --no-build-isolation") < 2:
        errors.append("release artifacts must be built twice with the locked offline backend")
    if "python tools/check_supply_chain.py artifacts build-a/*" not in text:
        errors.append("release workflow must check artifact legal files")
    if "uv publish dist/*.whl dist/*.tar.gz" not in text:
        errors.append("release workflow must publish only wheel and sdist artifacts")
    for reference in ACTION_USE.findall(text):
        if reference.startswith("./"):
            continue
        if "@" not in reference or not COMMIT_SHA.fullmatch(reference.rsplit("@", 1)[1]):
            errors.append(f"release action is not pinned to an immutable commit: {reference}")
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("notices", "secrets", "workflow", "artifacts", "all"))
    parser.add_argument("paths", nargs="*", type=Path)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args(argv)
    root = args.root.resolve()
    errors: list[str] = []
    if args.command in ("notices", "all"):
        errors.extend(check_notices(root))
    if args.command in ("secrets", "all"):
        errors.extend(check_secrets(tracked_files(root), root))
    if args.command in ("workflow", "all"):
        errors.extend(check_workflow(root / ".github" / "workflows" / "ci.yml"))
        errors.extend(check_release_workflow(root / ".github" / "workflows" / "release.yml"))
    if args.command in ("artifacts", "all"):
        if not args.paths:
            errors.append("artifact paths are required")
        else:
            errors.extend(check_artifacts(tuple(path.resolve() for path in args.paths)))
    for error in errors:
        print(f"ERROR: {error}", file=sys.stderr)
    if errors:
        return 1
    print(f"supply-chain {args.command} check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
