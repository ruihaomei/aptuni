"""Readable, portable export of the current Profile (PRD §4, §21).

``aptuni export`` writes one Markdown file per module with YAML frontmatter, readable in any editor
or in Obsidian without a plugin. It is a *copy* for reading and portability; the Vault stays the
source of truth. Pending proposals, rejected or forgotten memories, retractions and withdrawn
evidence are left out. The export is an owner action, so modules hidden from agents are included
and marked, never silently dropped.
"""

from __future__ import annotations

import os
import shutil
import tempfile
from dataclasses import dataclass
from html import escape
from pathlib import Path
from typing import Any, cast

from aptuni.domain.invariants import RecordSet
from aptuni.domain.records import MODULES, Module


@dataclass(frozen=True)
class ExportReport:
    path: Path
    files: int
    facts: int
    memories: int
    evidence: int
    omitted_full_content: int


def _yaml_scalar(value: object) -> str:
    text = str(value)
    return '"' + text.replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ") + '"'


def _markdown_text(text: str | None) -> str:
    """Render tainted record text as inert Markdown text, not links, HTML, headings or images."""
    collapsed = escape(" ".join((text or "").split()), quote=False)
    special = frozenset(r"\`*_[\]{}()#+-!|>")
    return "".join("\\" + character if character in special else character for character in collapsed)


def _module_markdown(module: str, facts: list[Any], memories: list[Any], evidence: list[Any],
                     exposed: bool, ingesting: bool, seq: int) -> str:
    lines = ["---", f"module: {module}", f"exposed_to_agents: {str(exposed).lower()}",
             f"accepting_new_information: {str(ingesting).lower()}", f"vault_commit: {seq}",
             f"facts: {len(facts)}", f"memories: {len(memories)}", f"evidence: {len(evidence)}",
             "generated_by: aptuni export", "---", "", f"# {module.capitalize()}", ""]
    if not exposed:
        lines += ["> Hidden from agents. This file is your own copy.", ""]
    if facts:
        lines += ["## Facts", ""]
        lines += [f"- {_markdown_text(f.statement)} `{f.id}`" +
                  (f" (valid {f.valid_from}–{f.valid_until or 'now'})" if f.valid_from else "") for f in facts]
        lines.append("")
    if memories:
        lines += ["## Memories", ""]
        lines += [f"- {_markdown_text(m.statement)} `{m.id}` · from "
                  f"{_markdown_text(m.provenance.episode)}" for m in memories]
        lines.append("")
    if evidence:
        lines += ["## Evidence", ""]
        for item in evidence:
            signals = ", ".join(item.signals) or "withdrawn"
            lines.append(f"- **{_markdown_text(item.subject)}** [{signals}] "
                         f"{_markdown_text(item.excerpt)} `{item.id}`")
        lines.append("")
    return "\n".join(lines)


def _write_private(path: Path, body: str) -> None:
    path.write_text(body, encoding="utf-8")
    path.chmod(0o600)


def export_profile(records: RecordSet, seq: int, target: Path) -> ExportReport:
    """Write the export atomically into ``target`` (created, must be empty or absent)."""
    target = target.expanduser().absolute()
    if target.is_symlink() or (target.exists() and not target.is_dir()):
        raise FileExistsError("export_target_not_empty")
    if target.exists() and any(target.iterdir()):
        raise FileExistsError("export_target_not_empty")
    policy = records.policy()
    reviews = records.records()
    accepted = {r.target_id for r in reviews if r.record_type == "review_event" and r.decision == "accept"}
    withdrawn = {r.target_id for r in reviews if r.record_type == "review_event"
                 and r.decision in ("reject", "revoke")}
    current_memories = [r for r in records.records() if r.record_type == "memory" and r.id not in withdrawn
                        and r.candidate_id in accepted and r.candidate_id not in withdrawn]
    current_facts = records.current_facts()
    current_evidence = [e for e in records.current_evidence() if e.change_kind != "retraction"]
    facts = [f for f in current_facts if not f.retention.full_content]
    memories = [m for m in current_memories if not m.retention.full_content]
    evidence = [e for e in current_evidence if not e.retention.full_content]
    omitted_full_content = (len(current_facts) - len(facts) + len(current_memories) - len(memories)
                            + len(current_evidence) - len(evidence))
    target.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{target.name}.partial-", dir=target.parent))
    staging.chmod(0o700)
    files = 0
    try:
        for raw_module in MODULES:
            module = cast(Module, raw_module)
            module_facts = [f for f in facts if f.module == module]
            module_memories = [m for m in memories if m.module == module]
            module_evidence = sorted((e for e in evidence if e.module == module), key=lambda e: e.subject)
            if not (module_facts or module_memories or module_evidence):
                continue
            switch = policy.modules[module] if policy else None
            body = _module_markdown(module, module_facts, module_memories, module_evidence,
                                    bool(switch and switch.expose_enabled),
                                    bool(switch and switch.ingest_enabled), seq)
            _write_private(staging / f"{module}.md", body + "\n")
            files += 1
        readme = ["---", f"vault_commit: {seq}", f"title: {_yaml_scalar('Aptuni profile export')}", "---", "",
                  "# Aptuni profile export", "",
                  "A readable copy of your current Profile. The Vault remains the source of truth; delete this",
                  "folder when you no longer need it (Aptuni does not track or purge copies you export).", "",
                  "Full-content retained source material is deliberately omitted. This readable projection is",
                  "not a restorable Vault backup.", ""]
        _write_private(staging / "README.md", "\n".join(readme) + "\n")
        # POSIX rename atomically replaces an existing empty directory with the completed staging tree.
        # If the target became non-empty after the preflight check, replacement fails and preserves it.
        os.replace(staging, target)
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    return ExportReport(target, files + 1, len(facts), len(memories), len(evidence), omitted_full_content)
