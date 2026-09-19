#!/usr/bin/env python3
"""Validate the repository-carried Claude Code/Codex relay without dependencies."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path


REQUIRED_FILES = (
    "AGENTS.md",
    "CLAUDE.md",
    "docs/dev/STATE.md",
    "docs/dev/HANDOFF.md",
    "docs/dev/KNOWN_ISSUES.md",
    "docs/dev/RESEARCH_NOTES.md",
    "docs/dev/ROADMAP.md",
    "docs/dev/SPIKES.md",
    "docs/dev/THREAT_MODEL.md",
    "docs/dev/DECISIONS/README.md",
)
STATE_MARKERS = (
    "**Updated:**",
    "**Current gate:**",
    "**Production code:**",
    "## Next highest-priority task",
    "## Latest validation state",
)
VALIDATION_MARKERS = ("workspace-text", "Markdown link", "ADR-index")
LINK_RE = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
ALLOWED_VERDICTS = {
    "review": {"APPROVE", "APPROVE_WITH_NON_BLOCKING_NOTES", "BLOCK"},
    "drill": {"PASS", "FAIL", "PENDING"},
}
OPEN_VERDICTS = {"BLOCK", "FAIL", "PENDING"}
RESPONDS_TO_RE = re.compile(r"^- \*\*Responds to:\*\* `([^`]+)`", re.MULTILINE)
VERDICT_LINE_RE = re.compile(
    r"^(?:- )?\*\*(?:Verdict|Cold-relay verdict):\*\* "
    r"\*\*(APPROVE WITH NON-BLOCKING NOTES|APPROVE|BLOCK|PASS|FAIL)\*\*",
    re.MULTILINE,
)
TEXT_SUFFIXES = {".md", ".py", ".json", ".toml", ".yaml", ".yml"}


def check_required_files(root: Path) -> list[str]:
    return [f"missing required relay file: {name}" for name in REQUIRED_FILES if not (root / name).is_file()]


def check_adr_index(root: Path) -> list[str]:
    decisions = root / "docs" / "dev" / "DECISIONS"
    index = decisions / "README.md"
    if not index.is_file():
        return ["missing ADR index: docs/dev/DECISIONS/README.md"]
    text = index.read_text(encoding="utf-8")
    errors: list[str] = []
    for adr in sorted(decisions.glob("ADR-[0-9][0-9][0-9][0-9]-*.md")):
        count = text.count(adr.name)
        if count != 1:
            errors.append(f"ADR index must reference {adr.name} exactly once; found {count}")
    indexed = set(re.findall(r"\((ADR-[0-9]{4}-[^)]+\.md)\)", text))
    actual = {path.name for path in decisions.glob("ADR-[0-9][0-9][0-9][0-9]-*.md")}
    for stale in sorted(indexed - actual):
        errors.append(f"ADR index references missing file: {stale}")
    return errors


def check_markdown_links(root: Path) -> list[str]:
    errors: list[str] = []
    for path in sorted(root.glob("**/*.md")):
        if any(part.startswith(".") for part in path.relative_to(root).parts):
            continue
        text = path.read_text(encoding="utf-8")
        for raw_target in LINK_RE.findall(text):
            target = raw_target.split("#", 1)[0].strip().strip("<>")
            if not target or "://" in target or target.startswith("/") or target.startswith("mailto:"):
                continue
            if not (path.parent / target).resolve().exists():
                errors.append(f"broken relative Markdown link in {path.relative_to(root)}: {raw_target}")
    return errors


def check_state(root: Path) -> list[str]:
    path = root / "docs" / "dev" / "STATE.md"
    if not path.is_file():
        return ["missing docs/dev/STATE.md"]
    text = path.read_text(encoding="utf-8")
    errors = [f"STATE.md missing marker: {marker}" for marker in STATE_MARKERS if marker not in text]
    errors.extend(
        f"STATE.md latest validation must mention: {marker}"
        for marker in VALIDATION_MARKERS
        if marker not in text
    )
    return errors


def parse_report_verdict(text: str) -> tuple[str | None, str | None]:
    """Return ``(verdict, error)`` from anchored final-verdict lines in a report.

    A report must contain at least one anchored verdict line and all such lines must agree.
    Prose mentioning verdict words (for example "NON-BLOCKING") is ignored.
    """
    found = {match.group(1) for match in VERDICT_LINE_RE.finditer(text)}
    if not found:
        return None, "no final verdict line"
    if len(found) > 1:
        return None, f"conflicting verdicts {sorted(found)}"
    display = found.pop()
    return display.replace(" WITH NON-BLOCKING NOTES", "_WITH_NON_BLOCKING_NOTES"), None


def _report_number(name: str) -> int:
    match = re.match(r"(\d+)-", name)
    return int(match.group(1)) if match else -1


def _load_streams(reviews: Path) -> tuple[dict[str, dict[str, object]] | None, list[str]]:
    status_path = reviews / "STATUS.json"
    if not status_path.is_file():
        return None, ["missing review lineage manifest: docs/dev/reviews/STATUS.json"]
    try:
        status = json.loads(status_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        return None, [f"invalid review lineage manifest: {exc}"]
    streams = status.get("streams")
    if status.get("version") != 2 or not isinstance(streams, dict) or not streams:
        return None, ["review lineage manifest must have version=2 and non-empty streams"]
    return streams, []


def _check_stream(reviews: Path, name: str, item: object) -> tuple[list[str], set[str], str | None]:
    """Validate one lineage stream; return errors, referenced report names, resolved verdict."""
    if not isinstance(item, dict):
        return [f"review stream {name} must be an object"], set(), None
    kind = item.get("kind")
    verdict = item.get("verdict")
    current = item.get("current")
    supersedes = item.get("supersedes", [])
    if kind not in ALLOWED_VERDICTS:
        return [f"review stream {name} has invalid kind: {kind}"], set(), None
    if verdict not in ALLOWED_VERDICTS[kind]:
        return [f"review stream {name}: verdict {verdict} not allowed for kind {kind}"], set(), None
    if not isinstance(supersedes, list) or not all(isinstance(v, str) for v in supersedes):
        return [f"review stream {name} supersedes must be a string list"], set(), None
    if verdict == "PENDING":
        if current is not None or supersedes:
            return [f"review stream {name} is PENDING but names reports"], set(), verdict
        return [], set(), verdict
    if not isinstance(current, str) or not (reviews / current).is_file():
        return [f"review stream {name} current report missing: {current}"], set(), None
    errors: list[str] = []
    if current in supersedes:
        errors.append(f"review stream {name} cannot supersede its current report")
    for previous in supersedes:
        if not (reviews / previous).is_file():
            errors.append(f"review stream {name} superseded report missing: {previous}")
        elif _report_number(previous) >= _report_number(current):
            errors.append(f"review stream {name}: current {current} is not the newest report")
    parsed, parse_error = parse_report_verdict((reviews / current).read_text(encoding="utf-8"))
    if parse_error:
        errors.append(f"review stream {name} report {current}: {parse_error}")
    elif parsed != verdict:
        errors.append(f"review stream {name}: manifest verdict {verdict} does not match report {parsed}")
    return errors, {current, *supersedes}, verdict


def _check_remediations(reviews: Path, referenced: set[str]) -> list[str]:
    errors: list[str] = []
    for path in sorted(reviews.glob("*remediation*.md")):
        text = path.read_text(encoding="utf-8")
        targets = set(RESPONDS_TO_RE.findall(text))
        if not targets or not targets <= referenced:
            errors.append(f"remediation {path.name} must declare Responds to: a manifest report")
        if VERDICT_LINE_RE.search(text):
            errors.append(f"remediation {path.name} must not contain a verdict line")
    return errors


def _check_summaries(root: Path, summary: str) -> list[str]:
    errors: list[str] = []
    expected = f"Review status manifest: {summary}"
    for name in ("STATE.md", "HANDOFF.md"):
        path = root / "docs" / "dev" / name
        text = path.read_text(encoding="utf-8") if path.is_file() else ""
        lines = [line.strip() for line in text.splitlines() if "Review status manifest:" in line]
        if len(lines) != 1:
            errors.append(f"{name} must contain exactly one review summary line; found {len(lines)}")
        elif lines[0] != expected:
            errors.append(f"{name} review summary is stale; expected: {expected}")
    return errors


def check_review_state(root: Path) -> list[str]:
    reviews = root / "docs" / "dev" / "reviews"
    if not reviews.is_dir():
        return ["missing docs/dev/reviews directory"]
    streams, errors = _load_streams(reviews)
    if streams is None:
        return errors
    referenced: set[str] = set()
    summary: list[str] = []
    for name, item in sorted(streams.items()):
        stream_errors, names, verdict = _check_stream(reviews, name, item)
        errors.extend(stream_errors)
        referenced.update(names)
        if verdict is not None:
            summary.append(f"{name}={verdict}")
    for path in sorted(reviews.glob("*.md")):
        if "remediation" not in path.name and path.name not in referenced:
            errors.append(f"review report is absent from lineage manifest: {path.name}")
    errors.extend(_check_remediations(reviews, referenced))
    errors.extend(_check_summaries(root, "; ".join(summary)))
    return errors


def review_gate_open(root: Path) -> bool:
    """True while any stream is BLOCK, FAIL or PENDING (production code must not start)."""
    streams, errors = _load_streams(root / "docs" / "dev" / "reviews")
    if streams is None or errors:
        return True
    return any(
        not isinstance(item, dict) or item.get("verdict") in OPEN_VERDICTS for item in streams.values()
    )


def check_instruction_size(root: Path, maximum_bytes: int = 12_000) -> list[str]:
    errors: list[str] = []
    for name in ("AGENTS.md", "CLAUDE.md"):
        path = root / name
        if path.is_file() and path.stat().st_size > maximum_bytes:
            errors.append(f"{name} exceeds concise instruction limit: {path.stat().st_size} bytes")
    return errors


def _is_host_local_log(relative: Path) -> bool:
    """Match the gitignored ``**/.claude/logs/`` host runtime directory."""
    parts = relative.parts
    return any(parts[i] == ".claude" and parts[i + 1] == "logs" for i in range(len(parts) - 1))


def check_workspace_text(root: Path) -> list[str]:
    """Cover new/untracked text files that ordinary ``git diff --check`` cannot see."""
    errors: list[str] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(root)
        if any(part in {".git", "temp", "__pycache__"} for part in relative.parts):
            continue
        if _is_host_local_log(relative):
            continue
        if path.suffix not in TEXT_SUFFIXES and path.name != ".gitignore":
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            errors.append(f"expected UTF-8 text file: {relative}")
            continue
        for number, line in enumerate(text.splitlines(), start=1):
            if line.endswith((" ", "\t")):
                errors.append(f"trailing whitespace in {relative}:{number}")
        if text and not text.endswith("\n"):
            errors.append(f"missing final newline in {relative}")
        if text.endswith("\n\n"):
            errors.append(f"extra blank line at EOF in {relative}")
    return errors


def run_checks(root: Path) -> list[str]:
    checks = (
        check_required_files,
        check_adr_index,
        check_markdown_links,
        check_state,
        check_review_state,
        check_instruction_size,
        check_workspace_text,
    )
    errors: list[str] = []
    for check in checks:
        errors.extend(check(root))
    return errors


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    root = Path(args[0]).resolve() if args else Path(__file__).resolve().parents[1]
    errors = run_checks(root)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        print(f"relay check failed: {len(errors)} error(s)", file=sys.stderr)
        return 1
    print("relay check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
