"""First-run onboarding for a brand-new user (Beta dogfooding, 2026-09-28).

The interactive ``aptuni setup plan`` asks which part of the owner Aptuni may learn from, in product
language, collects the exact location of each chosen source in the same flow, and states which
sources the owner connects later. Nothing is connected without an explicit choice.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest

from aptuni.application.service import AptuniService
from aptuni.application.setup import load_setup_plan, pending_setup_actions
from aptuni.application.workspace import Workspace
from aptuni.cli import setup_commands
from aptuni.cli.main import main, run
from aptuni.cli.setup_apply import apply_setup_plan


def _service(tmp_path: Path) -> AptuniService:
    return AptuniService(Workspace(tmp_path / "state"))


def _interactive(monkeypatch: pytest.MonkeyPatch, answers: list[str]) -> list[str]:
    prompts: list[str] = []
    queue = list(answers)

    def fake_input(prompt: str = "") -> str:
        prompts.append(prompt)
        if not queue:
            raise AssertionError(f"unexpected extra prompt: {prompt}")
        return queue.pop(0)

    monkeypatch.setattr(setup_commands.sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr("builtins.input", fake_input)
    return prompts


def _plan_interactively(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, answers: list[str],
                        *extra: str) -> tuple[AptuniService, list[str], Callable[[], object]]:
    service = _service(tmp_path)
    prompts = _interactive(monkeypatch, answers)
    assert run(["setup", "plan", "--vault", str(tmp_path / "Aptuni"), *extra], service) == 0

    def plan() -> object:
        (action,) = pending_setup_actions(service.workspace.state_dir)
        return load_setup_plan(service.workspace.state_dir, action)
    return service, prompts, plan


def _obsidian_vault(tmp_path: Path) -> Path:
    root = tmp_path / "ObsidianVault"
    (root / ".obsidian").mkdir(parents=True)
    (root / "Transformers.md").write_text("Attention weights come from query-key similarity.", encoding="utf-8")
    return root


def _notes(tmp_path: Path) -> Path:
    root = tmp_path / "notes"
    root.mkdir()
    (root / "cv.md").write_text("Survival analysis with competing risks.", encoding="utf-8")
    return root


# language, sources, …targets, memory, privacy, hosts
def test_english_source_question_is_about_what_aptuni_learns_not_connectors(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    _, prompts, _ = _plan_interactively(tmp_path, monkeypatch, ["1", "", "1", "3", ""])
    printed = capsys.readouterr().out
    question = prompts[1]

    assert "Profile" in printed and "Memory" in printed and "evidence" in printed.lower()
    assert "OFF" in printed
    assert "Obsidian — let Aptuni understand the notes and knowledge you have built up over time" in question
    assert "GitHub — let Aptuni understand the projects you have actually worked on" in question
    assert "Notion — let Aptuni read only the pages you explicitly approve" in question
    assert "Enter to skip" in question and "add sources later" in question
    for unsupported in ("zotero", "application_materials", "other"):
        assert unsupported not in question.lower()


def test_chinese_source_question_uses_natural_product_language(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    _, prompts, _ = _plan_interactively(tmp_path, monkeypatch, ["2", "", "1", "3", ""])
    printed = capsys.readouterr().out
    question = prompts[1]

    assert "默认关闭" in printed
    assert "Obsidian：让 Aptuni 了解你长期整理的笔记与知识" in question
    assert "GitHub：让 Aptuni 了解你真实参与的项目和开发经历" in question
    assert "Notion：让 Aptuni 只读取你明确授权的页面" in question
    assert "MarginNote：让 Aptuni 参考你的学习笔记" in question
    assert "本地文件夹：让 Aptuni 读取你指定的本地资料目录" in question
    assert "直接回车跳过" in question


def test_skipping_every_source_connects_nothing_and_says_how_to_add_later(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    _, _, plan = _plan_interactively(tmp_path, monkeypatch, ["1", "", "1", "3", ""])
    out = capsys.readouterr().out

    assert not [step for step in plan().steps if step.kind.startswith("source_")]
    assert "aptuni source add-folder" in out


def test_choosing_a_folder_asks_for_its_path_and_asks_again_when_it_is_wrong(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    notes = _notes(tmp_path)
    _, prompts, plan = _plan_interactively(
        tmp_path, monkeypatch, ["1", "1", str(tmp_path / "missing"), str(notes), "1", "3", ""])
    out = capsys.readouterr().out

    assert "folder" in prompts[2].lower() and prompts[3] == prompts[2]
    assert "does not exist" in out
    assert [(s.kind, s.target) for s in plan().steps if s.kind.startswith("source_")] == [
        ("source_folder", str(notes.resolve()))]


def test_choosing_obsidian_connects_that_vault_after_confirmation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    vault = _obsidian_vault(tmp_path)
    plain = _notes(tmp_path)
    service, _, plan = _plan_interactively(
        tmp_path, monkeypatch, ["1", "2", str(plain), str(vault), "1", "3", ""])
    out = capsys.readouterr().out
    frozen = plan()

    assert ".obsidian" in out, "a plain folder is refused with the reason"
    assert [s.kind for s in frozen.steps if s.kind.startswith("source_")] == ["source_obsidian"]
    report = apply_setup_plan(service, frozen.action_id, frozen.digest)
    assert report.terminal_state == "complete"
    assert [source.source_type for source in service.sources()] == ["obsidian"]
    assert service.search("query-key similarity")


def test_choosing_several_sources_plans_each_one(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    notes = _notes(tmp_path)
    _, _, plan = _plan_interactively(
        tmp_path, monkeypatch, ["1", "1,3", str(notes), "https://github.com/octocat/Hello-World", "1", "3", ""])

    assert [s.kind for s in plan().steps if s.kind.startswith("source_")] == ["source_folder", "source_github"]


def test_notion_and_marginnote_are_listed_as_later_steps_with_exact_commands(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    _, _, plan = _plan_interactively(tmp_path, monkeypatch, ["1", "4,5", "1", "3", ""])
    out = capsys.readouterr().out

    assert not [s for s in plan().steps if s.kind.startswith("source_")]
    assert "aptuni source connect-notion" in out
    assert "aptuni source discover-marginnote" in out


def test_agent_question_lists_supported_agents_by_name(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, prompts, plan = _plan_interactively(tmp_path, monkeypatch, ["1", "", "1", "1", "1,2"])

    assert "1. Claude Code" in prompts[-1] and "2. Codex" in prompts[-1]
    assert "cursor" not in prompts[-1].lower()
    assert [s.target for s in plan().steps if s.kind == "adapter"] == ["claude_code", "codex"]


def test_scripted_setup_can_name_an_obsidian_vault(tmp_path: Path) -> None:
    vault = _obsidian_vault(tmp_path)
    service = _service(tmp_path)
    assert run(["setup", "plan", "--lang", "en", "--source", "obsidian", "--obsidian", str(vault),
                "--memory", "basic", "--privacy", "local_only", "--no-host",
                "--vault", str(tmp_path / "Aptuni")], service) == 0
    (action,) = pending_setup_actions(service.workspace.state_dir)
    steps = load_setup_plan(service.workspace.state_dir, action).steps
    assert [s.kind for s in steps if s.kind.startswith("source_")] == ["source_obsidian"]


def test_scripted_setup_missing_folder_explains_the_fix_in_chinese(
    tmp_path: Path, capsys: pytest.CaptureFixture[str],
) -> None:
    service = _service(tmp_path)
    assert run(["setup", "plan", "--lang", "zh-CN", "--source", "folder", "--memory", "basic",
                "--privacy", "local_only", "--no-host"], service) == 2
    err = capsys.readouterr().err
    assert "--folder" in err and "aptuni setup plan" in err and "文件夹" in err


def test_bare_aptuni_welcomes_a_new_user_with_the_first_command(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    monkeypatch.setenv("APTUNI_STATE_DIR", str(tmp_path / "state"))
    assert main([]) == 0
    out = capsys.readouterr().out
    assert "aptuni setup plan" in out and "aptuni attach" in out and "第一次使用" in out
    assert "aptuni guide agent" in out


def test_commands_before_setup_point_to_setup_or_attach(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    monkeypatch.setenv("APTUNI_STATE_DIR", str(tmp_path / "state"))
    assert main(["status"]) == 1
    err = capsys.readouterr().err
    assert "aptuni setup plan" in err and "aptuni attach" in err


def test_github_steps_show_the_repository_address_not_internal_json(
    tmp_path: Path, capsys: pytest.CaptureFixture[str],
) -> None:
    service = _service(tmp_path)
    assert run(["setup", "plan", "--lang", "zh-CN", "--source", "github", "--github",
                "https://github.com/octocat/Hello-World", "--memory", "basic", "--privacy", "local_only",
                "--no-host", "--vault", str(tmp_path / "Aptuni")], service) == 0
    out = capsys.readouterr().out
    assert "https://github.com/octocat/Hello-World" in out
    assert "api_origin" not in out and "token_env" not in out


def test_setup_plan_shows_a_short_recommendation_and_keeps_details_in_advise(
    tmp_path: Path, capsys: pytest.CaptureFixture[str],
) -> None:
    service = _service(tmp_path)
    argv = ["--lang", "en", "--source", "other", "--memory", "basic", "--privacy", "quality", "--host", "codex"]
    assert run(["setup", "plan", *argv, "--vault", str(tmp_path / "Aptuni")], service) == 0
    plan_out = capsys.readouterr().out
    assert "[agent.mcp]" not in plan_out and "Benefits:" not in plan_out and "Trade-offs:" not in plan_out
    assert "Starter Lite" in plan_out and "aptuni advise" in plan_out
    assert run(["advise", *argv], service) == 0
    assert "Benefits:" in capsys.readouterr().out


def test_chinese_plan_localizes_retention_and_expiry(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    service = _service(tmp_path)
    assert run(["setup", "plan", "--lang", "zh-CN", "--source", "other", "--memory", "basic", "--privacy", "quality",
                "--host", "codex", "--vault", str(tmp_path / "Aptuni")], service) == 0
    out = capsys.readouterr().out
    assert "externally_controlled_unknown" not in out and "由提供方控制" in out
    assert "+00:00" not in out and " UTC" in out


def test_memory_question_is_honest_about_beta_availability(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, prompts, _ = _plan_interactively(tmp_path, monkeypatch, ["1", "", "1", "3", ""])
    assert "not available in this Beta" in prompts[2]
    _, zh_prompts, _ = _plan_interactively(tmp_path / "zh", monkeypatch, ["2", "", "1", "3", ""])
    assert "本 Beta 暂不可用" in zh_prompts[2]
