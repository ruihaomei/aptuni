"""Execute a confirmed guided-setup plan through application services (plan 02 step 5).

Every step goes through ``AptuniService`` or ``AdapterManager``; nothing here reimplements Vault,
source or grant logic. Each step is idempotent and journaled before the next one runs, so a crash
resumes rather than repeating work, and the adapter grant id is derived from the plan digest so a
resumed apply can never create a second grant.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from aptuni.adapters.manager import AdapterManager
from aptuni.advisor import load_catalog
from aptuni.application.errors import AptuniError
from aptuni.application.marginnote_ingest import MarginNoteSourceSpec
from aptuni.application.service import AptuniService
from aptuni.application.setup import (
    SetupError,
    SetupPlan,
    SetupStep,
    commit_setup_intent,
    completed_setup,
    finish_setup_intent,
    load_setup_plan,
    plan_from_dict,
    record_step,
)
from aptuni.sources.github import GitHubSourceSpec

HOST_ADAPTER = {"claude_code": "claude", "codex": "codex"}
# What a folder of notes ingests *into*. This is not the adapter read scope: `plan.modules`
# says what an agent may later read, which is a separate, per-module consent.
FOLDER_INGEST_MODULES = ("knowledge",)
SOURCE_ROLE = {"source_folder": "notes", "source_github": "repository",
               "source_marginnote": "study-notes"}
SMOKE_QUERY = "what should my agent know about me"
# A step outcome is a success only if it says so here. Anything else stops the run, so a later
# step -- notably a host grant -- can never run after an earlier failure (Review 33 B5).
SUCCESS = ("created", "already_present", "ok", "synced", "skipped")


def _succeeded(outcome: str) -> bool:
    return outcome.split(":", 1)[0] in SUCCESS


@dataclass
class SetupReport:
    action_id: str
    vault_path: str
    terminal_state: str
    results: dict[str, str] = field(default_factory=dict)
    grants: list[str] = field(default_factory=list)
    host_files: list[str] = field(default_factory=list)
    doctor_ok: bool = False
    smoke_ok: bool = False
    failure: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "action_id": self.action_id, "vault_path": self.vault_path,
            "terminal_state": self.terminal_state, "results": dict(self.results),
            "grants": list(self.grants), "host_files": list(self.host_files),
            "doctor_ok": self.doctor_ok, "smoke_ok": self.smoke_ok, "failure": self.failure,
        }


@dataclass(frozen=True)
class _PreparedAdapter:
    manager: AdapterManager
    action_id: str
    grant_id: str
    existed_before_step: bool


def _run_vault(service: AptuniService, step: SetupStep) -> str:
    """Create the Vault, or adopt the one this plan already names. Never adopt a different Vault."""
    existing = service.workspace.vault_path()
    if existing is not None:
        if Path(existing).resolve() != Path(step.target).resolve():
            raise SetupError(
                "setup_vault_conflict",
                "A different Vault is already configured; plan again with that path or move it first.",
            )
        return "already_present"
    service.init(Path(step.target))
    return "created"


def _run_source_folder(service: AptuniService, step: SetupStep) -> tuple[str, str | None]:
    root = Path(step.target)
    for source in service.sources():
        if source.roots and Path(source.roots[0]).resolve() == root.resolve():
            if _source_matches(source, "folder", (str(root),), "notes"):
                return f"already_present:{source.id}", None
            raise SetupError("setup_source_conflict", "That folder is already configured differently.")
    source = service.add_folder_source(root, FOLDER_INGEST_MODULES, "notes")
    return "created", source.id


def _github_spec(target: str) -> GitHubSourceSpec:
    try:
        value = json.loads(target)
        if not isinstance(value, dict) or set(value) != {"repository_url", "api_origin", "ref", "token_env"}:
            raise TypeError
        if not isinstance(value["repository_url"], str) or not isinstance(value["api_origin"], str):
            raise TypeError
        if value["ref"] is not None and not isinstance(value["ref"], str):
            raise TypeError
        if value["token_env"] is not None and not isinstance(value["token_env"], str):
            raise TypeError
        return GitHubSourceSpec.build(value["repository_url"], api_origin=value["api_origin"],
                                      ref=value["ref"], token_env=value["token_env"])
    except (json.JSONDecodeError, KeyError, TypeError, ValueError) as error:
        raise SetupError("setup_action_invalid", "The setup plan contains an invalid GitHub source.") from error


def _marginnote_spec(target: str) -> MarginNoteSourceSpec:
    try:
        value = json.loads(target)
        if not isinstance(value, dict) or set(value) != {"store", "notebooks"}:
            raise TypeError
        if not isinstance(value["store"], str):
            raise TypeError
        raw = value["notebooks"]
        if raw is not None and (not isinstance(raw, list) or not raw
                                or any(not isinstance(item, str) or not item for item in raw)):
            raise TypeError
        return MarginNoteSourceSpec(Path(value["store"]), None if raw is None else frozenset(raw))
    except (json.JSONDecodeError, KeyError, TypeError, ValueError) as error:
        raise SetupError("setup_action_invalid", "The setup plan contains an invalid MarginNote source.") from error


def _source_matches(source: Any, source_type: str, roots: tuple[str, ...], role: str) -> bool:
    return (source.source_type == source_type and tuple(source.roots) == roots
            and tuple(source.module_mapping) == FOLDER_INGEST_MODULES and source.semantic_role == role)


def _existing_source(service: AptuniService, source_type: str, roots: tuple[str, ...], role: str) -> Any | None:
    same_identity = [source for source in service.sources()
                     if source.source_type == source_type and tuple(source.roots) == roots]
    exact = next((source for source in same_identity if _source_matches(source, source_type, roots, role)), None)
    if exact is not None:
        return exact
    if same_identity:
        raise SetupError("setup_source_conflict", "That source is already configured differently.")
    return None


def _run_source_github(service: AptuniService, step: SetupStep) -> tuple[str, str | None]:
    spec = _github_spec(step.target)
    existing = _existing_source(service, "github", spec.roots(), SOURCE_ROLE[step.kind])
    if existing is not None:
        return f"already_present:{existing.id}", None
    source = service.add_github_source(
        spec.repository_url, FOLDER_INGEST_MODULES, SOURCE_ROLE[step.kind], ref=spec.ref,
        token_env=spec.token_env, api_origin=spec.api_origin,
    )
    return "created", source.id


def _run_source_marginnote(service: AptuniService, step: SetupStep) -> tuple[str, str | None]:
    spec = _marginnote_spec(step.target)
    existing = _existing_source(service, "marginnote4", spec.roots(), SOURCE_ROLE[step.kind])
    if existing is not None:
        return f"already_present:{existing.id}", None
    notebooks = None if spec.notebooks is None else tuple(sorted(spec.notebooks))
    source = service.add_marginnote_source(
        spec.store, notebooks, FOLDER_INGEST_MODULES, SOURCE_ROLE[step.kind],
    )
    return "created", source.id


def _source_expectation(step: SetupStep) -> tuple[str, tuple[str, ...], str] | None:
    if step.kind == "source_folder":
        return "folder", (str(Path(step.target)),), SOURCE_ROLE[step.kind]
    if step.kind == "source_github":
        return "github", _github_spec(step.target).roots(), SOURCE_ROLE[step.kind]
    if step.kind == "source_marginnote":
        return "marginnote4", _marginnote_spec(step.target).roots(), SOURCE_ROLE[step.kind]
    return None


def planned_sources(service: AptuniService, plan: SetupPlan) -> list[Any]:
    """Return only existing sources whose full policy matches a frozen setup source step."""
    try:
        sources = service.sources()
    except AptuniError:
        return []
    planned: list[Any] = []
    for step in plan.steps:
        expectation = _source_expectation(step)
        if expectation is None:
            continue
        source_type, roots, role = expectation
        source = next((item for item in sources if _source_matches(item, source_type, roots, role)), None)
        if source is not None:
            planned.append(source)
    return planned


def _prepare_adapter(service: AptuniService, step: SetupStep, plan: SetupPlan) -> _PreparedAdapter:
    """Resolve the deterministic grant id before its side effect, so ownership can be journaled."""
    manager = AdapterManager(service.workspace)
    host = HOST_ADAPTER[step.target]
    adapter_plan = manager.plan(host, plan.modules, allow_host_model_egress=True)
    grant_id = f"grant-{adapter_plan.digest[:16]}"
    existed = (manager.root / "grants" / f"{grant_id}.json").exists()
    return _PreparedAdapter(manager, adapter_plan.action_id, grant_id, existed)


def _run_adapter(prepared: _PreparedAdapter) -> tuple[str, str | None]:
    """Idempotently publish or repair both the grant and every deterministic bundle file."""
    grant, _ = prepared.manager.apply(prepared.action_id)
    prepared.manager.discard_pending(prepared.action_id)
    if prepared.existed_before_step:
        return f"already_present:{grant.grant_id}", None
    return "created", grant.grant_id


def _sync_sources(service: AptuniService, plan: SetupPlan, report: SetupReport) -> str:
    """Sync only sources named by this digest-bound plan; never sweep pre-existing sources."""
    synced = 0
    planned = planned_sources(service, plan)
    expected_count = sum(step.kind.startswith("source_") for step in plan.steps)
    if len(planned) != expected_count:
        return "failed:source_not_found"
    for source in planned:
        try:
            service.sync(source.id)
            synced += 1
        except AptuniError as error:
            report.results[f"sync:{source.id}"] = f"failed:{error.code}"
            return f"failed:{error.code}"
    return f"synced:{synced}"


def apply_setup_plan(
    service: AptuniService, action_id: str, confirmed_digest: str,
) -> SetupReport:
    """Run one confirmed plan to a terminal state, resuming a previously committed intent."""
    state_dir = service.workspace.state_dir
    current_plan = load_setup_plan(state_dir, action_id)
    if current_plan.catalog_digest != load_catalog().version_digest():
        raise SetupError("setup_catalog_changed", "The bundled catalog changed; cancel and plan setup again.")
    finished = completed_setup(state_dir, action_id)
    if finished is not None:
        if finished.get("digest") != confirmed_digest:
            raise SetupError("confirmation_stale", "The confirmation does not match this finished setup.")
        return SetupReport(
            action_id, str(finished.get("vault_path", "")), "complete",
            results=dict(finished.get("results", {})),
            grants=[item for item in finished.get("created", []) if str(item).startswith("grant-")],
            host_files=[str(item) for item in finished.get("host_files", [])],
            doctor_ok=bool(finished.get("doctor_ok")), smoke_ok=bool(finished.get("smoke_ok")),
        )
    intent_path, intent = commit_setup_intent(state_dir, action_id, confirmed_digest)
    plan = _plan_of(intent)
    report = SetupReport(action_id, plan.vault_path, "incomplete_resumable",
                         results=dict(intent["results"]), host_files=list(plan.host_files))
    for step in plan.steps:
        key = step.key()
        if _succeeded(report.results.get(key, "")):
            _carry_completed(step, report, intent, report.results[key])
            continue
        prepared_adapter: _PreparedAdapter | None = None
        if step.kind == "adapter":
            prepared_adapter = _prepare_adapter(service, step, plan)
            if not prepared_adapter.existed_before_step and prepared_adapter.grant_id not in intent["created"]:
                # This durable pre-effect claim resolves the crash window between grant publication
                # and the normal step-result journal write. A pre-existing grant is never claimed.
                record_step(intent_path, intent, key, "prepared", prepared_adapter.grant_id)
                report.results[key] = "prepared"
        try:
            outcome, created = (_run_adapter(prepared_adapter) if prepared_adapter is not None
                                else _run_step(service, step, plan, report))
        except (AptuniError, OSError) as error:
            code = error.code if isinstance(error, AptuniError) else "io_error"
            report.results[key] = f"failed:{code}"
            report.failure = code
            record_step(intent_path, intent, key, report.results[key])
            return report
        report.results[key] = outcome
        record_step(intent_path, intent, key, outcome, created)
        if step.kind == "adapter":
            grant_id = created if created else outcome.partition(":")[2]
            if grant_id.startswith("grant-") and grant_id not in report.grants:
                report.grants.append(grant_id)
        if not _succeeded(outcome):
            report.failure = outcome.split(":", 1)[-1]
            return report
    report.terminal_state = "complete"
    finish_setup_intent(state_dir, action_id, intent, plan, report)
    return report


def _plan_of(intent: dict[str, Any]) -> SetupPlan:
    return plan_from_dict(intent["plan"])


def _carry_completed(
    step: SetupStep, report: SetupReport, intent: dict[str, Any], outcome: str,
) -> None:
    """Reconstruct report fields from durable step outcomes after a crash."""
    if step.kind == "doctor":
        report.doctor_ok = outcome == "ok"
    elif step.kind == "smoke":
        report.smoke_ok = outcome == "ok"
    elif step.kind == "adapter":
        reused = outcome.partition(":")[2]
        grants = [reused] if reused.startswith("grant-") else [
            item for item in intent.get("created", []) if str(item).startswith("grant-")
        ]
        report.grants.extend(item for item in grants if item not in report.grants)


def _run_step(  # noqa: PLR0911 - one explicit branch per frozen step kind
    service: AptuniService, step: SetupStep, plan: SetupPlan, report: SetupReport,
) -> tuple[str, str | None]:
    if step.kind == "vault":
        return _run_vault(service, step), None
    if step.kind == "source_folder":
        return _run_source_folder(service, step)
    if step.kind == "source_github":
        return _run_source_github(service, step)
    if step.kind == "source_marginnote":
        return _run_source_marginnote(service, step)
    if step.kind == "sync":
        return _sync_sources(service, plan, report), None
    if step.kind == "doctor":
        report.doctor_ok = service.doctor().ok
        return ("ok" if report.doctor_ok else "failed:doctor"), None
    if step.kind == "smoke":
        _smoke(service)
        report.smoke_ok = True
        return "ok", None
    raise SetupError("invalid_setup_step", "The setup plan contains an unknown step.")


def _smoke(service: AptuniService) -> None:
    """Prove the installed system answers a real request; an empty Vault legitimately returns none."""
    service.identity_card()
    service.context(SMOKE_QUERY, budget=400)
