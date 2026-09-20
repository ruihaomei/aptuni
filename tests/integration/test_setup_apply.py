"""Guided setup: plan, one terminal confirmation, apply, resume, cancel (plan 02 steps 1, 4, 5).

The cases mirror the plan's scripted acceptance journey (A-G) and keep its classes apart: success,
refusal, cancellation and recovery each have their own assertions.
"""

from __future__ import annotations

import itertools
import json
import re
from pathlib import Path

import pytest

from aptuni.adapters.manager import BUNDLE_FILES, AdapterManager
from aptuni.application import setup as setup_api
from aptuni.application.errors import AptuniError
from aptuni.application.service import AptuniService
from aptuni.application.setup import SetupError, cancel_setup_plan, load_setup_plan, pending_setup_actions
from aptuni.application.workspace import Workspace
from aptuni.cli import setup_apply as setup_apply_api
from aptuni.cli.main import run as cli_run
from aptuni.cli.setup_apply import apply_setup_plan
from marginnote_fixture import base_cards, build_store


def _service(tmp_path: Path) -> AptuniService:
    return AptuniService(Workspace(tmp_path / "state"))


def _notes(tmp_path: Path, name: str = "notes", body: str = "Competing risks and the Fine-Gray model.") -> Path:
    root = tmp_path / name
    root.mkdir()
    (root / "stats.md").write_text(body, encoding="utf-8")
    return root


def _plan_argv(tmp_path: Path, *extra: str, locale: str = "en", privacy: str = "quality") -> list[str]:
    source = "folder" if "--folder" in extra else "other"
    return ["setup", "plan", "--lang", locale, "--source", source, "--memory", "basic",
            "--privacy", privacy, "--vault", str(tmp_path / "Aptuni"), "--json", *extra]


def _plan(service: AptuniService, tmp_path: Path, *extra: str, locale: str = "en",
          privacy: str = "quality", capsys: pytest.CaptureFixture[str]) -> dict:
    assert cli_run(_plan_argv(tmp_path, *extra, locale=locale, privacy=privacy), service) == 0
    return json.loads(capsys.readouterr().out)


def test_case_a_plan_creates_nothing_and_apply_installs_exactly_the_listed_steps(
    tmp_path: Path, capsys: pytest.CaptureFixture[str],
) -> None:
    service = _service(tmp_path)
    root = _notes(tmp_path)
    plan = _plan(service, tmp_path, "--folder", str(root), capsys=capsys)

    assert not (tmp_path / "Aptuni").exists(), "planning must create nothing"
    assert service.workspace.vault_path() is None
    assert [step["kind"] for step in plan["steps"]] == ["vault", "source_folder", "sync", "doctor", "smoke"]

    report = apply_setup_plan(service, plan["action_id"], plan["digest"])
    assert report.terminal_state == "complete"
    assert report.doctor_ok and report.smoke_ok
    assert (tmp_path / "Aptuni" / "HEAD.json").exists()
    assert [source.roots[0] for source in service.sources()] == [str(root)]
    assert service.evidence(service.sources()[0].id), "the approved folder must be ingested"
    assert pending_setup_actions(service.workspace.state_dir) == [], "a complete apply leaves nothing pending"


def test_case_b_local_only_plans_no_host_egress(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Strict local-only must not plan any adapter grant, even with a host selected."""
    service = _service(tmp_path)
    argv = _plan_argv(tmp_path, "--host", "claude_code", locale="en", privacy="local_only")
    assert cli_run(argv, service) == 0
    plan = json.loads(capsys.readouterr().out)

    assert not [step for step in plan["steps"] if step["kind"] == "adapter"]
    assert plan["host_files"] == []
    report = apply_setup_plan(service, plan["action_id"], plan["digest"])
    assert report.terminal_state == "complete"
    assert report.grants == []
    assert not (service.workspace.state_dir / "adapters" / "grants").exists()

    argv = [arg for arg in _plan_argv(tmp_path, "--host", "claude_code", locale="en",
                                      privacy="local_only") if arg != "--json"]
    assert cli_run(argv, _service(tmp_path / "preview")) == 0
    preview = capsys.readouterr().out
    assert "creates no Aptuni host grant" in preview
    assert "can still read files" in preview
    assert "Nothing leaves this device" not in preview


def test_case_c_host_plan_names_every_file_before_confirmation(
    tmp_path: Path, capsys: pytest.CaptureFixture[str],
) -> None:
    service = _service(tmp_path)
    argv = _plan_argv(tmp_path, "--host", "claude_code", "--host", "codex")
    assert cli_run(argv, service) == 0
    plan = json.loads(capsys.readouterr().out)

    assert [step["target"] for step in plan["steps"] if step["kind"] == "adapter"] == ["claude_code", "codex"]
    assert "claude_code: .mcp.json" in plan["host_files"]
    assert "claude_code: hooks.json" in plan["host_files"]
    assert "codex: config.toml" in plan["host_files"]

    report = apply_setup_plan(service, plan["action_id"], plan["digest"])
    assert report.terminal_state == "complete"
    assert len(report.grants) == 2
    assert not list((service.workspace.state_dir / "adapters" / "pending").glob("*.json"))
    for grant_id in report.grants:
        assert (service.workspace.state_dir / "adapters" / "grants" / f"{grant_id}.json").exists()


def test_case_d_no_host_plan_is_complete_on_its_own(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    service = _service(tmp_path)
    plan = _plan(service, tmp_path, capsys=capsys)
    assert plan["host_files"] == []
    assert apply_setup_plan(service, plan["action_id"], plan["digest"]).terminal_state == "complete"


def test_case_e_a_missing_folder_stops_before_any_partial_activation(
    tmp_path: Path, capsys: pytest.CaptureFixture[str],
) -> None:
    service = _service(tmp_path)
    plan = _plan(service, tmp_path, "--folder", str(tmp_path / "absent"),
                 "--host", "codex", capsys=capsys)
    report = apply_setup_plan(service, plan["action_id"], plan["digest"])

    assert report.terminal_state == "incomplete_resumable"
    assert report.failure == "source_not_found"
    assert report.grants == [], "no host grant may exist after a failed earlier step"
    assert not (service.workspace.state_dir / "adapters" / "grants").exists()
    assert pending_setup_actions(service.workspace.state_dir) == [plan["action_id"]], "must stay resumable"


def test_case_f_cancelling_a_plan_leaves_no_trace(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    service = _service(tmp_path)
    plan = _plan(service, tmp_path, "--folder", str(_notes(tmp_path)), capsys=capsys)

    assert cancel_setup_plan(service.workspace.state_dir, plan["action_id"]) == (False, [])
    assert not (tmp_path / "Aptuni").exists()
    assert service.workspace.vault_path() is None
    assert pending_setup_actions(service.workspace.state_dir) == []
    with pytest.raises(SetupError) as gone:
        load_setup_plan(service.workspace.state_dir, plan["action_id"])
    assert gone.value.code == "setup_action_not_found"


def test_case_f_terminal_confirmation_refuses_anything_but_apply(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = _service(tmp_path)
    plan = _plan(service, tmp_path, capsys=capsys)
    monkeypatch.setattr("builtins.input", lambda _prompt: "yes")

    assert cli_run(["setup", "apply", plan["action_id"]], service) == 1
    assert "Cancelled" in capsys.readouterr().out
    assert not (tmp_path / "Aptuni").exists()
    assert pending_setup_actions(service.workspace.state_dir) == [plan["action_id"]]


def test_case_g_a_resumed_apply_finishes_without_duplicating_a_grant(
    tmp_path: Path, capsys: pytest.CaptureFixture[str],
) -> None:
    """Review 20 N11 / plan 02 step 5: restart must resume, never create a second grant."""
    service = _service(tmp_path)
    missing = tmp_path / "later"
    plan = _plan(service, tmp_path, "--folder", str(missing), "--host", "codex", capsys=capsys)
    first = apply_setup_plan(service, plan["action_id"], plan["digest"])
    assert first.terminal_state == "incomplete_resumable"

    head = (tmp_path / "Aptuni" / "HEAD.json").read_bytes()
    missing.mkdir()
    (missing / "n.md").write_text("now present", encoding="utf-8")
    second = apply_setup_plan(service, plan["action_id"], plan["digest"])
    assert second.terminal_state == "complete"
    assert second.results[f"vault:{tmp_path / 'Aptuni'}"] == "created", "the journal keeps the first outcome"
    assert (tmp_path / "Aptuni" / "HEAD.json").read_bytes() != head, "the resumed run still ingests the folder"
    assert service.workspace.vault_path() == tmp_path / "Aptuni"

    grants = sorted((service.workspace.state_dir / "adapters" / "grants").glob("grant-*.json"))
    assert len(grants) == 1, "a resumed apply must not create a duplicate grant"

    third = apply_setup_plan(service, plan["action_id"], plan["digest"])
    assert third.terminal_state == "complete", "re-applying a finished plan is idempotent"
    assert len(sorted((service.workspace.state_dir / "adapters" / "grants").glob("grant-*.json"))) == 1


def test_confirmation_is_bound_to_the_plan_digest(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    service = _service(tmp_path)
    plan = _plan(service, tmp_path, capsys=capsys)
    with pytest.raises(SetupError) as stale:
        apply_setup_plan(service, plan["action_id"], "sha256:" + "0" * 64)
    assert stale.value.code == "confirmation_stale"
    assert not (tmp_path / "Aptuni").exists()


def test_a_tampered_plan_fails_closed(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """The digest covers the steps, so an edited plan file can never be confirmed."""
    service = _service(tmp_path)
    plan = _plan(service, tmp_path, capsys=capsys)
    path = service.workspace.state_dir / "setup" / "pending" / f"{plan['action_id']}.json"
    value = json.loads(path.read_text(encoding="utf-8"))
    value["vault_path"] = str(tmp_path / "elsewhere")
    path.write_text(json.dumps(value), encoding="utf-8")

    with pytest.raises(SetupError) as invalid:
        load_setup_plan(service.workspace.state_dir, plan["action_id"])
    assert invalid.value.code == "setup_action_invalid"
    assert not (tmp_path / "elsewhere").exists()


def test_an_expired_plan_cannot_be_applied(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = _service(tmp_path)
    plan = _plan(service, tmp_path, capsys=capsys)
    later = setup_api.utc_now() + setup_api.SETUP_TTL + setup_api.timedelta(minutes=1)
    monkeypatch.setattr(setup_api, "utc_now", lambda: later)

    with pytest.raises(SetupError) as expired:
        apply_setup_plan(service, plan["action_id"], plan["digest"])
    assert expired.value.code == "confirmation_expired"
    assert not (tmp_path / "Aptuni").exists()


def test_apply_refuses_to_adopt_a_different_vault(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    service = _service(tmp_path)
    service.init(tmp_path / "Existing")
    plan = _plan(service, tmp_path, capsys=capsys)
    report = apply_setup_plan(service, plan["action_id"], plan["digest"])

    assert report.terminal_state == "incomplete_resumable"
    assert report.failure == "setup_vault_conflict"
    assert service.workspace.vault_path() == tmp_path / "Existing"
    assert not (tmp_path / "Aptuni").exists()


def test_cancel_after_a_complete_apply_rolls_back_the_grant_it_created(
    tmp_path: Path, capsys: pytest.CaptureFixture[str],
) -> None:
    """The success message promises this rollback, so the promise must hold."""
    service = _service(tmp_path)
    argv = _plan_argv(tmp_path, "--host", "codex")
    assert cli_run(argv, service) == 0
    plan = json.loads(capsys.readouterr().out)
    report = apply_setup_plan(service, plan["action_id"], plan["digest"])
    assert report.grants and report.terminal_state == "complete"

    assert cli_run(["setup", "cancel", plan["action_id"]], service) == 0
    assert "removed" in capsys.readouterr().out.lower()
    assert not sorted((service.workspace.state_dir / "adapters" / "grants").glob("grant-*.json"))
    assert (tmp_path / "Aptuni" / "HEAD.json").exists(), "cancel never deletes the owner's Vault"


def test_cancel_is_refused_for_an_unknown_action(tmp_path: Path) -> None:
    service = _service(tmp_path)
    with pytest.raises(SetupError) as missing:
        cancel_setup_plan(service.workspace.state_dir, "setup-" + "0" * 16)
    assert missing.value.code == "setup_action_not_found"
    with pytest.raises(SetupError) as bad_id:
        cancel_setup_plan(service.workspace.state_dir, "not-an-action")
    assert bad_id.value.code == "invalid_setup_action_id"


@pytest.mark.parametrize("locale", ["en", "zh-CN"])
def test_the_plan_renders_in_both_locales_without_untranslated_keys(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], locale: str,
) -> None:
    service = _service(tmp_path)
    argv = [arg for arg in _plan_argv(tmp_path, locale=locale) if arg != "--json"]
    assert cli_run(argv, service) == 0
    out = capsys.readouterr().out
    assert "setup.plan." not in out, "an untranslated key leaked into the rendered plan"
    assert str(tmp_path / "Aptuni") in out
    assert ("No Vault, source, grant" in out) if locale == "en" else ("尚未创建 Vault、来源、授权" in out)


@pytest.mark.parametrize("locale", ["en", "zh-CN"])
def test_every_confirmed_step_is_numbered_in_order(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], locale: str,
) -> None:
    """The owner confirms this list, so each step must carry its own position (no mixed bullets)."""
    service = _service(tmp_path)
    argv = [arg for arg in _plan_argv(tmp_path, "--host", "codex", locale=locale) if arg != "--json"]
    assert cli_run(argv, service) == 0
    out = capsys.readouterr().out

    heading = "This will do exactly these steps" if locale == "en" else "将严格按顺序执行以下步骤"
    body = out.split(heading, 1)[1]
    steps = list(itertools.takewhile(lambda line: line.strip(), body.splitlines()[1:]))

    assert len(steps) >= 4, "the rendered plan lost its steps"
    numbers = [match.group(1) if (match := re.match(r"  (\d+)\. \S", line)) else line for line in steps]
    assert numbers == [str(number) for number in range(1, len(steps) + 1)], (
        f"every step must carry its own position 1..n; got {numbers!r}"
    )


def test_the_grant_created_by_setup_carries_only_the_planned_modules(
    tmp_path: Path, capsys: pytest.CaptureFixture[str],
) -> None:
    service = _service(tmp_path)
    argv = _plan_argv(tmp_path, "--host", "codex", "--module", "goals", "--module", "skills")
    assert cli_run(argv, service) == 0
    plan = json.loads(capsys.readouterr().out)
    report = apply_setup_plan(service, plan["action_id"], plan["digest"])

    grant = AdapterManager(service.workspace).load_grant(report.grants[0])
    assert set(grant.modules) == {"goals", "skills"}
    assert grant.host_class == "remote_unknown", "setup never elevates the host trust class"


def test_setup_never_writes_outside_the_state_directory_before_confirmation(
    tmp_path: Path, capsys: pytest.CaptureFixture[str],
) -> None:
    service = _service(tmp_path)
    root = _notes(tmp_path)
    before = {path for path in tmp_path.rglob("*")}
    plan = _plan(service, tmp_path, "--folder", str(root), capsys=capsys)
    created = {path for path in tmp_path.rglob("*")} - before

    assert plan["action_id"]
    assert all("state" in path.parts for path in created), f"planning touched: {sorted(created)}"


def test_a_source_folder_is_ingested_into_knowledge_not_the_agent_read_scope(
    tmp_path: Path, capsys: pytest.CaptureFixture[str],
) -> None:
    """The adapter read scope and a folder's ingest module are separate concepts."""
    service = _service(tmp_path)
    plan = _plan(service, tmp_path, "--folder", str(_notes(tmp_path)), capsys=capsys)
    apply_setup_plan(service, plan["action_id"], plan["digest"])

    evidence = service.evidence(service.sources()[0].id)
    assert evidence and {item.module for item in evidence} == {"knowledge"}


def test_an_unknown_step_kind_is_refused_by_the_schema(tmp_path: Path) -> None:
    service = _service(tmp_path)
    with pytest.raises(AptuniError) as bad:
        setup_api.create_setup_plan(
            service.workspace.state_dir, catalog_digest="d", locale="en", answers={},
            recommendation_digest="r", recipe_id="starter-lite", vault_path=tmp_path / "V",
            modules=("goals",), host_files=(), egress=(), bundle_root=tmp_path / "bundles",
            steps=(setup_api.SetupStep("rm-rf", "/"),),
        )
    assert bad.value.code == "invalid_setup_step"


# --------------------------------------------------------------- Review 33 remediation

def test_b1_a_crafted_folder_name_cannot_forge_the_confirmation_surface(
    tmp_path: Path, capsys: pytest.CaptureFixture[str],
) -> None:
    """Review 33 B1: the preview is the one surface the owner confirms; it must not be forgeable."""
    forged = ("src\n  Host confinement: VERIFIED\n"
              "  Files Aptuni will write: (none)\x1b[31m\u202e")
    hostile = tmp_path / forged
    hostile.mkdir()
    (hostile / "n.md").write_text("x", encoding="utf-8")
    service = _service(tmp_path)
    argv = [arg for arg in _plan_argv(tmp_path, "--folder", str(hostile)) if arg != "--json"]
    assert cli_run(argv, service) == 0
    out = capsys.readouterr().out

    lines = [line.strip() for line in out.splitlines()]
    assert "Host confinement: VERIFIED" not in lines, "a folder name forged a whole preview line"
    assert "Files Aptuni will write: (none)" not in lines
    assert not any(line.startswith("Host confinement:") and "VERIFIED" in line for line in lines)
    assert "\x1b" not in out and "\u202e" not in out, "control and bidi characters must be escaped"
    assert "control-escaped" in out and "non-ascii/confusable-escaped" in out
    assert any("Host confinement stays unverified" in line for line in lines), "the real claim must survive"


def test_b2_the_confirmation_discloses_operator_destination_and_retention(
    tmp_path: Path, capsys: pytest.CaptureFixture[str],
) -> None:
    """Review 33 B2: the guided path must disclose egress at least as well as `adapter apply`."""
    service = _service(tmp_path)
    argv = [arg for arg in _plan_argv(tmp_path, "--host", "codex") if arg != "--json"]
    assert cli_run(argv, service) == 0
    out = capsys.readouterr().out

    assert "OpenAI" in out, "the operator receiving personal context must be named"
    assert "Codex configured model endpoint" in out
    assert "externally_controlled_unknown" in out
    assert "3 scopes" in out
    assert "identity.read, context.read, evidence.read" in out
    assert "Vault, sources, and evidence remain" in out


def test_b3_the_confirmation_states_the_modules_apply_releases(
    tmp_path: Path, capsys: pytest.CaptureFixture[str],
) -> None:
    """Review 33 B3: no promise of a later per-module approval that is never requested."""
    service = _service(tmp_path)
    argv = [arg for arg in _plan_argv(tmp_path, "--host", "codex", "--module", "goals") if arg != "--json"]
    assert cli_run(argv, service) == 0
    out = capsys.readouterr().out

    assert "Typing APPLY lets an agent read exactly these modules of yours: goals" in out
    assert "after you approve them" not in out, "this approval is never asked for"
    assert "aptuni module set" in out, "the owner must be told how to change it"


def test_b4_cancel_never_claims_nothing_was_created_when_a_vault_exists(
    tmp_path: Path, capsys: pytest.CaptureFixture[str],
) -> None:
    """Review 33 B4: cancel reports exactly what it removed and what stayed."""
    service = _service(tmp_path)
    root = _notes(tmp_path)
    plan = _plan(service, tmp_path, "--folder", str(root), capsys=capsys)
    assert apply_setup_plan(service, plan["action_id"], plan["digest"]).terminal_state == "complete"

    assert cli_run(["setup", "cancel", plan["action_id"]], service) == 0
    out = capsys.readouterr().out
    assert "Nothing had been created" not in out, "a Vault, a source and evidence all exist"
    assert "Still present" in out
    assert str(tmp_path / "Aptuni") in out.replace("\\/", "/") or "Aptuni" in out
    assert (tmp_path / "Aptuni" / "HEAD.json").exists()


def test_b5_a_failing_sync_stops_the_run_before_any_host_grant(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Review 33 B5: a swallowed step failure let a grant be created after it."""
    service = _service(tmp_path)
    plan = _plan(service, tmp_path, "--folder", str(_notes(tmp_path)), "--host", "codex", capsys=capsys)

    def refuse(_source_id: str) -> None:
        raise AptuniError("source_unavailable", "injected sync failure")

    monkeypatch.setattr(AptuniService, "sync", lambda _self, source_id: refuse(source_id))
    report = apply_setup_plan(service, plan["action_id"], plan["digest"])

    assert report.terminal_state == "incomplete_resumable"
    assert report.failure == "source_unavailable"
    assert report.grants == [], "no grant may be created after a failed step"
    assert not (service.workspace.state_dir / "adapters" / "grants").exists()


def test_b5_a_failing_doctor_stops_the_run(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = _service(tmp_path)
    plan = _plan(service, tmp_path, capsys=capsys)

    class Unhealthy:
        ok = False

    monkeypatch.setattr(AptuniService, "doctor", lambda _self: Unhealthy())
    report = apply_setup_plan(service, plan["action_id"], plan["digest"])

    assert report.terminal_state == "incomplete_resumable"
    assert report.failure == "doctor"
    assert "smoke:context" not in report.results, "nothing after a failed check may run"


def test_b5_a_failing_smoke_stops_the_run(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = _service(tmp_path)
    plan = _plan(service, tmp_path, capsys=capsys)

    def fail_context(*_args: object, **_kwargs: object) -> None:
        raise AptuniError("context_failed", "injected smoke failure")

    monkeypatch.setattr(AptuniService, "context", fail_context)
    report = apply_setup_plan(service, plan["action_id"], plan["digest"])

    assert report.terminal_state == "incomplete_resumable"
    assert report.failure == "context_failed"
    assert report.results["smoke:context"] == "failed:context_failed"


def test_b6_the_preview_names_every_file_the_adapter_actually_writes(
    tmp_path: Path, capsys: pytest.CaptureFixture[str],
) -> None:
    """Review 33 B6: the promised file set is read from the code that writes the files."""
    service = _service(tmp_path)
    argv = _plan_argv(tmp_path, "--host", "claude_code", "--host", "codex")
    assert cli_run(argv, service) == 0
    plan = json.loads(capsys.readouterr().out)
    report = apply_setup_plan(service, plan["action_id"], plan["digest"])
    assert report.terminal_state == "complete"

    promised = {name.split(": ", 1)[1] for name in plan["host_files"]}
    written = {path.name for grant in report.grants
               for path in (service.workspace.state_dir / "adapters" / "bundles" / grant).iterdir()}
    assert written <= promised, f"apply wrote files the preview never named: {written - promised}"
    assert "AGENTS.md" in promised, "the Codex AGENTS.md was previously written but never previewed"


def test_b6_the_report_does_not_claim_the_host_config_was_modified(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = _service(tmp_path)
    argv = _plan_argv(tmp_path, "--host", "codex")
    assert cli_run(argv, service) == 0
    plan = json.loads(capsys.readouterr().out)
    monkeypatch.setattr("builtins.input", lambda _prompt: "APPLY")
    assert cli_run(["setup", "apply", plan["action_id"]], service) == 0
    out = capsys.readouterr().out

    assert "is NOT modified" in out, "the owner must be told the host config was not touched"
    assert str(service.workspace.state_dir / "adapters" / "bundles") in out.replace('\\/', '/') or \
        "bundles" in out, "the bundle location must be shown"
    assert "Estimated setup:" in out and "Difficulty:" in out
    assert "Privacy:" in out and "Benefits:" in out and "Trade-offs:" in out


def test_n5_end_of_input_at_the_confirmation_is_a_clean_cancellation(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = _service(tmp_path)
    plan = _plan(service, tmp_path, capsys=capsys)

    def interrupted(_prompt: str) -> str:
        raise EOFError

    monkeypatch.setattr("builtins.input", interrupted)
    assert cli_run(["setup", "apply", plan["action_id"]], service) == 130
    assert not (tmp_path / "Aptuni").exists()


def test_n8_a_second_grant_for_different_modules_is_still_refused_after_a_resume(
    tmp_path: Path, capsys: pytest.CaptureFixture[str],
) -> None:
    """Review 33 N8: content-addressed ids made the old assertion vacuous; count grants for real."""
    service = _service(tmp_path)
    missing = tmp_path / "later"
    plan = _plan(service, tmp_path, "--folder", str(missing), "--host", "codex", capsys=capsys)
    assert apply_setup_plan(service, plan["action_id"], plan["digest"]).failure == "source_not_found"

    missing.mkdir()
    (missing / "n.md").write_text("present", encoding="utf-8")
    assert apply_setup_plan(service, plan["action_id"], plan["digest"]).terminal_state == "complete"
    grants = {path.stem for path in (service.workspace.state_dir / "adapters" / "grants").glob("grant-*.json")}
    assert len(grants) == 1

    # A different module set is a different plan, and must not be silently folded into this one.
    other_argv = _plan_argv(tmp_path, "--host", "codex", "--module", "goals")
    assert cli_run(other_argv, service) == 0
    other = json.loads(capsys.readouterr().out)
    assert other["digest"] != plan["digest"]
    with pytest.raises(SetupError):
        apply_setup_plan(service, plan["action_id"], other["digest"])


def test_n9_the_journey_runs_in_chinese_with_a_chinese_path_and_mixed_language_name(
    tmp_path: Path, capsys: pytest.CaptureFixture[str],
) -> None:
    """Plan 02 requires the acceptance journey in Simplified Chinese with Chinese paths."""
    root = tmp_path / "我的笔记" / "research-资料"
    root.mkdir(parents=True)
    (root / "统计-notes.md").write_text("竞争风险与 Fine-Gray 模型", encoding="utf-8")
    service = _service(tmp_path)
    vault = tmp_path / "我的 Aptuni 档案"

    argv = ["setup", "plan", "--lang", "zh-CN", "--source", "folder", "--memory", "basic",
            "--privacy", "quality", "--vault", str(vault), "--folder", str(root), "--json"]
    assert cli_run(argv, service) == 0
    plan = json.loads(capsys.readouterr().out)
    assert plan["locale"] == "zh-CN"

    report = apply_setup_plan(service, plan["action_id"], plan["digest"])
    assert report.terminal_state == "complete", report.results
    assert (vault / "HEAD.json").exists()
    evidence = service.evidence(service.sources()[0].id)
    assert evidence, "a Chinese-named file under a Chinese path must be ingested"

    assert cli_run(["setup", "status", "--lang", "zh-CN"], service) == 0
    assert "待处理" in capsys.readouterr().out or "没有" in capsys.readouterr().out


def test_n9_the_chinese_preview_escapes_a_chinese_path_without_losing_it(
    tmp_path: Path, capsys: pytest.CaptureFixture[str],
) -> None:
    root = tmp_path / "笔记"
    root.mkdir()
    service = _service(tmp_path)
    argv = ["setup", "plan", "--lang", "zh-CN", "--source", "folder", "--memory", "basic",
            "--privacy", "local_only", "--vault", str(tmp_path / "V"), "--folder", str(root)]
    assert cli_run(argv, service) == 0
    out = capsys.readouterr().out

    assert "setup.plan." not in out
    assert "\\u7b14\\u8bb0" in out, "the Chinese path is escaped, not dropped"
    assert "没有任何数据离开本机" in out


def test_renaming_a_pending_plan_cannot_change_the_action_id(
    tmp_path: Path, capsys: pytest.CaptureFixture[str],
) -> None:
    """The path, embedded action id and digest must all name the same action."""
    service = _service(tmp_path)
    plan = _plan(service, tmp_path, capsys=capsys)
    pending = service.workspace.state_dir / "setup" / "pending"
    renamed_id = "setup-" + "b" * 16
    (pending / f"{plan['action_id']}.json").rename(pending / f"{renamed_id}.json")

    with pytest.raises(SetupError) as invalid:
        load_setup_plan(service.workspace.state_dir, renamed_id)
    assert invalid.value.code == "setup_action_invalid"


def test_cli_reapply_of_a_finished_action_is_a_no_op(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = _service(tmp_path)
    plan = _plan(service, tmp_path, capsys=capsys)
    assert apply_setup_plan(service, plan["action_id"], plan["digest"]).terminal_state == "complete"
    before = (tmp_path / "Aptuni" / "HEAD.json").read_bytes()
    monkeypatch.setattr("builtins.input", lambda _prompt: "APPLY")

    assert cli_run(["setup", "apply", plan["action_id"]], service) == 0
    out = capsys.readouterr().out
    assert "already complete" in out
    assert "No Vault, source, grant" not in out
    assert (tmp_path / "Aptuni" / "HEAD.json").read_bytes() == before


def test_resume_after_receipt_crash_preserves_doctor_and_smoke_verdicts(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = _service(tmp_path)
    plan = _plan(service, tmp_path, capsys=capsys)
    real_finish = setup_apply_api.finish_setup_intent
    monkeypatch.setattr(setup_apply_api, "finish_setup_intent",
                        lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("crash")))
    with pytest.raises(OSError, match="crash"):
        apply_setup_plan(service, plan["action_id"], plan["digest"])
    monkeypatch.setattr(setup_apply_api, "finish_setup_intent", real_finish)

    resumed = apply_setup_plan(service, plan["action_id"], plan["digest"])
    assert resumed.terminal_state == "complete"
    assert resumed.doctor_ok and resumed.smoke_ok


def test_cancel_does_not_revoke_a_grant_that_setup_only_reused(
    tmp_path: Path, capsys: pytest.CaptureFixture[str],
) -> None:
    service = _service(tmp_path)
    service.init(tmp_path / "Aptuni")
    manager = AdapterManager(service.workspace)
    prior_plan = manager.plan("codex",
                              ("identity", "knowledge", "skills", "projects", "goals", "preferences"),
                              allow_host_model_egress=True)
    prior_grant, _ = manager.apply(prior_plan.action_id)

    plan = _plan(service, tmp_path, "--host", "codex", capsys=capsys)
    report = apply_setup_plan(service, plan["action_id"], plan["digest"])
    assert report.grants == [prior_grant.grant_id]
    assert cli_run(["setup", "cancel", plan["action_id"]], service) == 0

    assert manager.load_grant(prior_grant.grant_id) == prior_grant


def test_success_report_includes_explicit_profile_and_confinement_status(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = _service(tmp_path)
    plan = _plan(service, tmp_path, "--host", "codex", capsys=capsys)
    monkeypatch.setattr("builtins.input", lambda _prompt: "APPLY")
    assert cli_run(["setup", "apply", plan["action_id"]], service) == 0
    output = capsys.readouterr().out
    assert "Profile status: unverified" in output
    assert "confinement: unverified" in output


def test_setup_has_no_scripted_confirmation_bypass(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    service = _service(tmp_path)
    plan = _plan(service, tmp_path, capsys=capsys)
    with pytest.raises(SystemExit):
        cli_run(["setup", "apply", plan["action_id"], "--confirm-digest", plan["digest"]], service)
    assert not (tmp_path / "Aptuni").exists()


def test_sync_step_reads_only_sources_named_by_the_setup_plan(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = _service(tmp_path)
    service.init(tmp_path / "Aptuni")
    old = _notes(tmp_path, "old")
    old_source = service.add_folder_source(old, ("knowledge",), "old-notes")
    new = _notes(tmp_path, "new")
    plan = _plan(service, tmp_path, "--folder", str(new), capsys=capsys)
    real_sync = AptuniService.sync
    called: list[str] = []

    def traced_sync(self: AptuniService, source_id: str) -> object:
        called.append(source_id)
        return real_sync(self, source_id)

    monkeypatch.setattr(AptuniService, "sync", traced_sync)
    report = apply_setup_plan(service, plan["action_id"], plan["digest"])

    assert report.terminal_state == "complete"
    new_source = next(source for source in service.sources() if source.roots[0] == str(new))
    assert called == [new_source.id]
    assert old_source.id not in called


def test_cancel_remains_retryable_when_grant_revocation_fails(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = _service(tmp_path)
    plan = _plan(service, tmp_path, "--host", "codex", capsys=capsys)
    assert apply_setup_plan(service, plan["action_id"], plan["digest"]).terminal_state == "complete"
    receipt = service.workspace.state_dir / "setup" / "receipts" / f"{plan['action_id']}.json"

    def fail_revoke(_self: AdapterManager, _grant_id: str) -> bool:
        raise AptuniError("revoke_failed", "injected revoke failure")

    monkeypatch.setattr(AdapterManager, "revoke", fail_revoke)
    with pytest.raises(AptuniError, match="injected revoke failure"):
        cli_run(["setup", "cancel", plan["action_id"]], service)
    assert receipt.exists(), "the action record must survive so cancellation can be retried"


def test_crash_after_grant_creation_preserves_setup_ownership_for_cancel(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = _service(tmp_path)
    plan = _plan(service, tmp_path, "--host", "codex", capsys=capsys)
    real_record = setup_apply_api.record_step
    crashed = False

    def crash_after_adapter(
        intent_path: Path, intent: dict[str, object], key: str, result: str,
        created: str | None = None,
    ) -> None:
        nonlocal crashed
        if key == "adapter:codex" and result == "created" and not crashed:
            crashed = True
            raise OSError("crash after adapter effect")
        real_record(intent_path, intent, key, result, created)

    monkeypatch.setattr(setup_apply_api, "record_step", crash_after_adapter)
    with pytest.raises(OSError, match="crash after adapter effect"):
        apply_setup_plan(service, plan["action_id"], plan["digest"])
    grants = sorted((service.workspace.state_dir / "adapters" / "grants").glob("grant-*.json"))
    assert len(grants) == 1

    monkeypatch.setattr(setup_apply_api, "record_step", real_record)
    assert apply_setup_plan(service, plan["action_id"], plan["digest"]).terminal_state == "complete"
    assert cli_run(["setup", "cancel", plan["action_id"]], service) == 0
    assert not grants[0].exists(), "cancel must revoke the grant this action created before the crash"


def test_case_c_exact_github_and_marginnote_sources_are_created_from_the_plan(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = _service(tmp_path)
    folder = _notes(tmp_path)
    store = build_store(tmp_path / "mn" / "MarginNotes.sqlite", base_cards())
    argv = [
        "setup", "plan", "--lang", "en", "--source", "folder", "--source", "github",
        "--source", "marginnote", "--memory", "basic", "--privacy", "minimize_cloud",
        "--host", "claude_code", "--host", "codex", "--vault", str(tmp_path / "Aptuni"),
        "--folder", str(folder), "--github", "https://github.com/example/research",
        "--github-token-env", "GITHUB_TOKEN", "--marginnote-store", str(store),
        "--marginnote-all-notebooks", "--json",
    ]
    assert cli_run(argv, service) == 0
    plan = json.loads(capsys.readouterr().out)
    kinds = [step["kind"] for step in plan["steps"]]
    assert kinds[1:4] == ["source_folder", "source_github", "source_marginnote"]
    assert "GITHUB_TOKEN" in plan["steps"][2]["target"]
    assert str(store) in plan["steps"][3]["target"]

    monkeypatch.setattr(AptuniService, "sync", lambda _self, _source_id: None)
    report = apply_setup_plan(service, plan["action_id"], plan["digest"])
    assert report.terminal_state == "complete"
    assert {source.source_type for source in service.sources()} == {"folder", "github", "marginnote4"}


def test_named_shipped_source_without_exact_configuration_creates_no_plan(
    tmp_path: Path, capsys: pytest.CaptureFixture[str],
) -> None:
    service = _service(tmp_path)
    argv = ["setup", "plan", "--lang", "en", "--source", "github", "--memory", "basic",
            "--privacy", "quality", "--no-host", "--vault", str(tmp_path / "Aptuni"), "--json"]
    assert cli_run(argv, service) == 2
    assert "--github" in capsys.readouterr().err
    assert not (service.workspace.state_dir / "setup" / "pending").exists()


def test_existing_folder_with_different_policy_is_a_conflict(
    tmp_path: Path, capsys: pytest.CaptureFixture[str],
) -> None:
    service = _service(tmp_path)
    service.init(tmp_path / "Aptuni")
    root = _notes(tmp_path)
    service.add_folder_source(root, ("identity",), "identity-material")
    plan = _plan(service, tmp_path, "--folder", str(root), capsys=capsys)

    report = apply_setup_plan(service, plan["action_id"], plan["digest"])
    assert report.failure == "setup_source_conflict"
    assert len(service.sources()) == 1


def test_catalog_change_invalidates_a_pending_confirmation(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = _service(tmp_path)
    plan = _plan(service, tmp_path, capsys=capsys)

    class ChangedCatalog:
        @staticmethod
        def version_digest() -> str:
            return "changed-catalog"

    monkeypatch.setattr(setup_apply_api, "load_catalog", ChangedCatalog)
    with pytest.raises(SetupError) as stale:
        apply_setup_plan(service, plan["action_id"], plan["digest"])
    assert stale.value.code == "setup_catalog_changed"
    assert not (tmp_path / "Aptuni").exists()


def test_cancel_consumes_both_intent_and_receipt_after_receipt_publication_crash(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = _service(tmp_path)
    plan = _plan(service, tmp_path, "--host", "codex", capsys=capsys)
    real_unlink = setup_api._unlink_durable
    receipt = service.workspace.state_dir / "setup" / "receipts" / f"{plan['action_id']}.json"

    def crash_before_intent_unlink(path: Path) -> None:
        if path.parent.name == "intents" and receipt.exists():
            raise OSError("crash after receipt publication")
        real_unlink(path)

    monkeypatch.setattr(setup_api, "_unlink_durable", crash_before_intent_unlink)
    with pytest.raises(OSError, match="crash after receipt publication"):
        apply_setup_plan(service, plan["action_id"], plan["digest"])
    intent = service.workspace.state_dir / "setup" / "intents" / f"{plan['action_id']}.json"
    assert intent.exists() and receipt.exists()

    monkeypatch.setattr(setup_api, "_unlink_durable", real_unlink)
    assert cli_run(["setup", "cancel", plan["action_id"]], service) == 0
    assert not intent.exists() and not receipt.exists()
    with pytest.raises(SetupError) as gone:
        apply_setup_plan(service, plan["action_id"], plan["digest"])
    assert gone.value.code == "setup_action_not_found"


@pytest.mark.parametrize(("setup_host", "adapter_host", "missing_file"), [
    ("claude_code", "claude", name) for name in BUNDLE_FILES["claude"]
] + [
    ("codex", "codex", name) for name in BUNDLE_FILES["codex"]
])
def test_resume_repairs_each_missing_adapter_bundle_file(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch,
    setup_host: str, adapter_host: str, missing_file: str,
) -> None:
    service = _service(tmp_path)
    plan = _plan(service, tmp_path, "--host", setup_host, capsys=capsys)
    real_apply = AdapterManager.apply
    injected = False

    def partial_apply(self: AdapterManager, action_id: str) -> tuple[object, Path]:
        nonlocal injected
        grant, bundle = real_apply(self, action_id)
        if not injected:
            injected = True
            (bundle / missing_file).unlink()
            raise OSError("injected adapter bundle crash")
        return grant, bundle

    monkeypatch.setattr(AdapterManager, "apply", partial_apply)
    first = apply_setup_plan(service, plan["action_id"], plan["digest"])
    assert first.terminal_state == "incomplete_resumable" and first.failure == "io_error"

    monkeypatch.setattr(AdapterManager, "apply", real_apply)
    resumed = apply_setup_plan(service, plan["action_id"], plan["digest"])
    assert resumed.terminal_state == "complete"
    grant_id = resumed.grants[0]
    bundle = service.workspace.state_dir / "adapters" / "bundles" / grant_id
    assert {path.name for path in bundle.iterdir()} == set(BUNDLE_FILES[adapter_host])
