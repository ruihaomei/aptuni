"""Durable, digest-bound guided-setup plans and their apply journal (plan 02 steps 1, 4, 5).

A plan is a frozen promise: it names every artifact the apply step will create, binds that list to
the catalog version and the owner's own answers (Review 20 N11), and expires. Producing a plan
changes nothing. Applying one needs a single terminal confirmation of the plan digest, after which
each step is journaled so a crash resumes instead of repeating work or creating a duplicate grant.

This module deliberately knows nothing about the services that execute the steps; the orchestrator
injects them. That keeps the schema, the digest and the crash protocol independently testable.
"""

from __future__ import annotations

import json
import os
import re
import secrets
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from aptuni.application.errors import AptuniError
from aptuni.domain.ids import sha256_text
from aptuni.domain.records import MODULES
from aptuni.domain.temporal import utc_now

SETUP_TTL = timedelta(minutes=30)
ACTION_RE = re.compile(r"^setup-[0-9a-f]{16}$")
SCHEMA_VERSION = 1
STEP_KINDS = (
    "vault", "source_folder", "source_github", "source_marginnote", "sync", "adapter", "doctor", "smoke",
)
TERMINAL_STATES = ("complete", "incomplete_resumable")


class SetupError(AptuniError):
    """A setup plan is missing, expired, stale or otherwise unusable (fixed codes, no user text)."""


@dataclass(frozen=True)
class SetupStep:
    """One idempotent unit of work. ``target`` is exact; the apply step never infers it."""

    kind: str
    target: str

    def key(self) -> str:
        return f"{self.kind}:{self.target}"


@dataclass(frozen=True)
class SetupPlan:
    schema_version: int
    action_id: str
    catalog_digest: str
    locale: str
    answers: dict[str, Any]
    recommendation_digest: str
    recipe_id: str
    vault_path: str
    modules: tuple[str, ...]
    host_files: tuple[str, ...]
    egress: tuple[dict[str, str], ...]
    bundle_root: str
    steps: tuple[SetupStep, ...]
    nonce_id: str
    expires_at: str
    digest: str

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["steps"] = [asdict(step) for step in self.steps]
        return value

    def expired(self) -> bool:
        return datetime.fromisoformat(self.expires_at) <= utc_now()


def _digest_fields(value: dict[str, Any]) -> str:
    body = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return sha256_text(body)


def _plan_fields(plan: SetupPlan) -> dict[str, Any]:
    """Every field the owner is shown, so the confirmation cannot cover a different plan."""
    return {
        "schema_version": plan.schema_version,
        "catalog_digest": plan.catalog_digest,
        "locale": plan.locale,
        "answers": plan.answers,
        "recommendation_digest": plan.recommendation_digest,
        "recipe_id": plan.recipe_id,
        "vault_path": plan.vault_path,
        "action_id": plan.action_id,
        "modules": list(plan.modules),
        "host_files": list(plan.host_files),
        "egress": [dict(sorted(item.items())) for item in plan.egress],
        "bundle_root": plan.bundle_root,
        "steps": [[step.kind, step.target] for step in plan.steps],
        "nonce_id": plan.nonce_id,
        "expires_at": plan.expires_at,
    }


def _validate_action_id(action_id: str) -> None:
    if not ACTION_RE.fullmatch(action_id):
        raise SetupError("invalid_setup_action_id", "An exact core-generated setup action ID is required.")


def _write_private_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(path.parent, 0o700)
    body = (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=1) + "\n").encode("utf-8")
    tmp = path.with_name(f".{path.name}.{os.getpid()}.{secrets.token_hex(4)}.tmp")
    descriptor = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        remaining = memoryview(body)
        while remaining:
            remaining = remaining[os.write(descriptor, remaining):]
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    os.replace(tmp, path)
    directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)


def _unlink_durable(path: Path) -> None:
    try:
        path.unlink()
    except FileNotFoundError:
        return
    descriptor = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def setup_root(state_dir: Path) -> Path:
    return state_dir / "setup"


def create_setup_plan(
    state_dir: Path, *, catalog_digest: str, locale: str, answers: dict[str, Any],
    recommendation_digest: str, recipe_id: str, vault_path: Path, modules: tuple[str, ...],
    host_files: tuple[str, ...], egress: tuple[dict[str, str], ...], bundle_root: Path,
    steps: tuple[SetupStep, ...],
) -> SetupPlan:
    """Write one pending plan. Nothing outside ``state/setup/pending`` is touched."""
    if not modules or len(set(modules)) != len(modules) or any(module not in MODULES for module in modules):
        raise SetupError("invalid_setup_modules", "The setup plan contains an invalid module scope.")
    for step in steps:
        if step.kind not in STEP_KINDS:
            raise SetupError("invalid_setup_step", "The setup plan contains an unknown step.")
    partial = SetupPlan(
        SCHEMA_VERSION, "setup-" + secrets.token_hex(8), catalog_digest, locale, dict(answers),
        recommendation_digest, recipe_id, str(vault_path), modules, host_files, egress,
        str(bundle_root), steps, secrets.token_hex(16), (utc_now() + SETUP_TTL).isoformat(), "",
    )
    plan = SetupPlan(**{**partial.__dict__, "digest": _digest_fields(_plan_fields(partial))})
    _write_private_json(setup_root(state_dir) / "pending" / f"{plan.action_id}.json", plan.to_dict())
    return plan


def plan_from_dict(value: dict[str, Any]) -> SetupPlan:
    try:
        steps = tuple(SetupStep(str(item["kind"]), str(item["target"])) for item in value["steps"])
        plan = SetupPlan(
            int(value["schema_version"]), str(value["action_id"]), str(value["catalog_digest"]),
            str(value["locale"]), dict(value["answers"]), str(value["recommendation_digest"]),
            str(value["recipe_id"]), str(value["vault_path"]),
            tuple(str(item) for item in value["modules"]),
            tuple(str(item) for item in value["host_files"]),
            tuple({str(key): str(item[key]) for key in item} for item in value["egress"]),
            str(value["bundle_root"]), steps,
            str(value["nonce_id"]), str(value["expires_at"]), str(value["digest"]),
        )
    except (KeyError, TypeError, ValueError) as error:
        raise SetupError("setup_action_invalid", "The pending setup action is invalid; plan it again.") from error
    if plan.schema_version != SCHEMA_VERSION or not ACTION_RE.fullmatch(plan.action_id):
        raise SetupError("setup_action_invalid", "The pending setup action is invalid; plan it again.")
    if any(step.kind not in STEP_KINDS for step in plan.steps):
        raise SetupError("setup_action_invalid", "The pending setup action is invalid; plan it again.")
    if plan.digest != _digest_fields(_plan_fields(plan)):
        raise SetupError("setup_action_invalid", "The pending setup action is invalid; plan it again.")
    return plan


def load_setup_plan(state_dir: Path, action_id: str) -> SetupPlan:
    """Load the exact plan frozen in a pending action, intent, or completion receipt."""
    _validate_action_id(action_id)
    pending = setup_root(state_dir) / "pending" / f"{action_id}.json"
    intent = setup_root(state_dir) / "intents" / f"{action_id}.json"
    receipt = setup_root(state_dir) / "receipts" / f"{action_id}.json"
    try:
        if pending.exists():
            value = json.loads(pending.read_text(encoding="utf-8"))
        elif intent.exists():
            value = json.loads(intent.read_text(encoding="utf-8"))["plan"]
        elif receipt.exists():
            value = json.loads(receipt.read_text(encoding="utf-8"))["plan"]
        else:
            raise FileNotFoundError
        if not isinstance(value, dict):
            raise TypeError
        plan = plan_from_dict(value)
        if plan.action_id != action_id:
            raise SetupError("setup_action_invalid", "The pending setup action is invalid; plan it again.")
        return plan
    except FileNotFoundError as error:
        raise SetupError("setup_action_not_found", "No exact pending setup action was found.") from error
    except (json.JSONDecodeError, OSError, KeyError, TypeError) as error:
        raise SetupError("setup_action_invalid", "The pending setup action is invalid; plan it again.") from error


def commit_setup_intent(state_dir: Path, action_id: str, confirmed_digest: str) -> tuple[Path, dict[str, Any]]:
    """Turn one confirmed plan into a durable intent, or resume the intent already committed."""
    _validate_action_id(action_id)
    intent_path = setup_root(state_dir) / "intents" / f"{action_id}.json"
    if intent_path.exists():
        try:
            intent = json.loads(intent_path.read_text(encoding="utf-8"))
            plan = plan_from_dict(intent["plan"])
        except (OSError, json.JSONDecodeError, KeyError, TypeError) as error:
            raise SetupError("setup_action_invalid", "The committed setup action is invalid.") from error
        _validate_progress(intent, plan, action_id)
        if confirmed_digest != plan.digest:
            raise SetupError("confirmation_stale", "The confirmation does not match this setup action.")
        return intent_path, intent
    plan = load_setup_plan(state_dir, action_id)
    if confirmed_digest != plan.digest:
        raise SetupError("confirmation_stale", "The digest does not match this plan; nothing changed.")
    if plan.expired():
        raise SetupError("confirmation_expired", "The setup confirmation expired; plan it again.")
    fresh: dict[str, Any] = {"schema_version": SCHEMA_VERSION, "plan": plan.to_dict(), "results": {},
                             "created": []}
    _write_private_json(intent_path, fresh)
    _unlink_durable(setup_root(state_dir) / "pending" / f"{action_id}.json")
    return intent_path, fresh


def record_step(intent_path: Path, intent: dict[str, Any], key: str, result: str,
                created: str | None = None) -> None:
    """Make one step's outcome durable before the next one starts."""
    intent["results"][key] = result
    if created is not None and created not in intent["created"]:
        intent["created"].append(created)
    _write_private_json(intent_path, intent)


def _validate_progress(value: dict[str, Any], plan: SetupPlan, action_id: str) -> None:
    """Reject malformed journals before their values can skip or fabricate setup steps."""
    results = value.get("results")
    created = value.get("created")
    valid_keys = {step.key() for step in plan.steps}
    if (
        value.get("schema_version") != SCHEMA_VERSION
        or plan.action_id != action_id
        or not isinstance(results, dict)
        or any(not isinstance(key, str) or not isinstance(result, str)
               or key not in valid_keys for key, result in results.items())
        or not isinstance(created, list)
        or any(not isinstance(item, str) for item in created)
    ):
        raise SetupError("setup_action_invalid", "The committed setup action is invalid.")


def finish_setup_intent(state_dir: Path, action_id: str, intent: dict[str, Any],
                        plan: SetupPlan, report: Any) -> None:
    """Record a completed apply, so the promised rollback works and a repeat apply is a no-op.

    The receipt stores what actually happened. It never asserts a check passed that never ran.
    """
    _write_private_json(setup_root(state_dir) / "receipts" / f"{action_id}.json", {
        "schema_version": SCHEMA_VERSION, "action_id": action_id, "vault_path": plan.vault_path,
        "digest": plan.digest, "host_files": list(plan.host_files),
        "doctor_ok": bool(report.doctor_ok), "smoke_ok": bool(report.smoke_ok),
        "created": list(intent.get("created", [])), "results": dict(intent.get("results", {})),
        "plan": plan.to_dict(),
    })
    _unlink_durable(setup_root(state_dir) / "intents" / f"{action_id}.json")


def completed_setup(state_dir: Path, action_id: str) -> dict[str, Any] | None:
    """Return the receipt of an already-finished apply, so repeating it changes nothing."""
    _validate_action_id(action_id)
    path = setup_root(state_dir) / "receipts" / f"{action_id}.json"
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    except (OSError, json.JSONDecodeError) as error:
        raise SetupError("setup_action_invalid", "The finished setup action is invalid.") from error
    try:
        if not isinstance(value, dict):
            raise TypeError
        plan = plan_from_dict(value["plan"])
        _validate_progress(value, plan, action_id)
        if (
            value.get("action_id") != action_id
            or value.get("digest") != plan.digest
            or value.get("vault_path") != plan.vault_path
            or value.get("host_files") != list(plan.host_files)
            or not isinstance(value.get("doctor_ok"), bool)
            or not isinstance(value.get("smoke_ok"), bool)
        ):
            raise TypeError
    except (KeyError, TypeError, ValueError, SetupError) as error:
        raise SetupError("setup_action_invalid", "The finished setup action is invalid.") from error
    return value


def cancel_setup_plan(state_dir: Path, action_id: str) -> tuple[bool, list[str]]:
    """Cancel a plan and report what an apply had already created, newest first.

    Returns ``(was_confirmed, rollback_ids)``. A plan that was never confirmed leaves nothing
    behind. A confirmed one may have created grants and bundles; those ids are returned so the
    caller can roll them back, and ``was_confirmed`` tells the caller it must NOT claim that nothing
    was created -- a Vault, sources and evidence may well exist (Review 33 B4). The Vault is never
    removed here: it may already hold the owner's records, and deleting personal data is explicit.
    """
    _validate_action_id(action_id)
    root = setup_root(state_dir)
    pending = root / "pending" / f"{action_id}.json"
    if pending.exists():
        _unlink_durable(pending)
        return False, []
    record = next((path for path in (root / "intents" / f"{action_id}.json",
                                     root / "receipts" / f"{action_id}.json") if path.exists()), None)
    if record is None:
        raise SetupError("setup_action_not_found", "No setup action with that id.")
    try:
        created = json.loads(record.read_text(encoding="utf-8")).get("created", [])
    except (OSError, json.JSONDecodeError) as error:
        raise SetupError("setup_action_invalid", "The committed setup action is invalid.") from error
    return True, ([str(item) for item in reversed(created)] if isinstance(created, list) else [])


def finish_setup_cancellation(state_dir: Path, action_id: str) -> None:
    """Consume a confirmed action only after all external rollback work has succeeded."""
    _validate_action_id(action_id)
    root = setup_root(state_dir)
    records = [path for path in (root / "intents" / f"{action_id}.json",
                                 root / "receipts" / f"{action_id}.json") if path.exists()]
    if not records:
        raise SetupError("setup_action_not_found", "No setup action with that id.")
    for record in records:
        _unlink_durable(record)


def pending_setup_actions(state_dir: Path) -> list[str]:
    """Every plan the owner could still confirm or resume, so none is ever invisible."""
    root = setup_root(state_dir)
    found: set[str] = set()
    for folder in ("pending", "intents"):
        directory = root / folder
        if directory.is_dir():
            found.update(path.stem for path in directory.glob("setup-*.json"))
    return sorted(found)


def setup_action_state(state_dir: Path, action_id: str) -> str:
    """Return the owner-facing durable phase for one exact action."""
    _validate_action_id(action_id)
    root = setup_root(state_dir)
    if (root / "receipts" / f"{action_id}.json").exists():
        return "complete"
    if (root / "intents" / f"{action_id}.json").exists():
        return "resumable"
    if (root / "pending" / f"{action_id}.json").exists():
        return "pending"
    raise SetupError("setup_action_not_found", "No setup action with that id.")
