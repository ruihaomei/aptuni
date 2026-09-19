"""``aptuni advise | recipe | plugin``: read-only, bilingual, and never touching the Vault."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

from aptuni.cli.setup_commands import collect_answers

REPO = Path(__file__).resolve().parents[2]


def run(state: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ, APTUNI_STATE_DIR=str(state), PYTHONPATH=str(REPO / "src"))
    env.pop("APTUNI_LANG", None)
    return subprocess.run([sys.executable, "-m", "aptuni", *args], env=env, capture_output=True, text=True,
                          check=False, stdin=subprocess.DEVNULL)


def test_advise_json_is_scriptable_and_read_only(tmp_path: Path) -> None:
    state = tmp_path / "state"
    done = run(state, "advise", "--json", "--source", "folder", "--memory", "basic", "--privacy", "local_only",
               "--host", "claude_code")
    assert done.returncode == 0, done.stderr
    plan = json.loads(done.stdout)
    assert plan["recipe_id"] == "starter-lite"
    assert plan["host_release"] == "refused_local_only"
    assert plan["host_file_access"] is True
    assert plan["digest"].startswith("sha256:")
    assert not state.exists(), "advise must not create state, config, grants or a Vault"


def test_advise_preview_in_both_languages(tmp_path: Path) -> None:
    common = ("advise", "--source", "github", "--memory", "automatic", "--privacy", "quality", "--no-host")
    english = run(tmp_path / "s", *common, "--lang", "en")
    chinese = run(tmp_path / "s", *common, "--lang", "zh-CN")
    assert english.returncode == chinese.returncode == 0, english.stderr + chinese.stderr
    assert "Researcher" in english.stdout and "Nothing was installed" in english.stdout
    assert "研究者" in chinese.stdout and "没有安装或修改任何内容" in chinese.stdout
    digest = next(line for line in english.stdout.splitlines() if "sha256:" in line).split("sha256:")[1]
    assert digest in chinese.stdout, "the plan digest is language independent"


def test_advise_without_answers_fails_with_localized_message(tmp_path: Path) -> None:
    done = run(tmp_path / "s", "advise", "--lang", "zh-CN", "--privacy", "quality")
    assert done.returncode == 2
    assert "缺少回答：memory" in done.stderr
    assert "Traceback" not in done.stderr


def test_recipe_and_plugin_listings(tmp_path: Path) -> None:
    recipes = run(tmp_path / "s", "recipe", "list", "--json")
    assert recipes.returncode == 0, recipes.stderr
    available = {r["id"]: r["available"] for r in json.loads(recipes.stdout)}
    assert available == {"starter-lite": True, "researcher": True, "personal-memory": False,
                         "temporal-memory": False}
    unknown = run(tmp_path / "s", "recipe", "show", "nope")
    assert unknown.returncode == 2
    plugins = run(tmp_path / "s", "plugin", "list", "--lang", "zh-CN")
    assert plugins.returncode == 0 and "计划中" in plugins.stdout


def _namespace(**values: object) -> argparse.Namespace:
    base: dict[str, object] = {"lang": None, "sources": None, "memory": None, "privacy": None, "hosts": None,
                               "no_host": False, "detect_hosts": False}
    base.update(values)
    return argparse.Namespace(**base)


def test_interactive_questions_ask_language_first_and_retry_invalid_answers(monkeypatch: object) -> None:
    import aptuni.cli.setup_commands as module

    monkeypatch.setattr(module, "detect_hosts", lambda: frozenset({"codex"}))  # type: ignore[attr-defined]
    replies = iter(["2", "github，folder", "maybe", "1", "3", "codex"])
    prompts: list[str] = []

    def ask(prompt: str) -> str:
        prompts.append(prompt)
        return next(replies)

    answers = collect_answers(_namespace(), interactive=True, ask=ask)
    assert "Which language" in prompts[0]
    assert "智能体" in prompts[1]
    assert answers.locale == "zh-CN"
    assert answers.sources == frozenset({"github", "folder"})
    assert answers.memory == "basic" and answers.privacy == "local_only"
    assert answers.hosts == frozenset({"codex"})


def test_local_only_preview_never_claims_nothing_leaves_when_a_host_is_named(tmp_path: Path) -> None:
    for lang, forbidden, required in (("en", "nothing leaves this device", "own file tools"),
                                      ("zh-CN", "没有任何数据离开本机", "自身的文件工具")):
        done = run(tmp_path / "s", "advise", "--lang", lang, "--source", "folder", "--memory", "basic",
                   "--privacy", "local_only", "--host", "claude_code")
        assert done.returncode == 0, done.stderr
        assert forbidden not in done.stdout and required in done.stdout
        assert "content-free" not in done.stdout


def test_interactive_cancel_is_quiet(monkeypatch: object) -> None:
    import aptuni.cli.setup_commands as module

    def cancel(_prompt: str) -> str:
        raise EOFError

    monkeypatch.setattr(module, "input", cancel, raising=False)  # type: ignore[attr-defined]
    monkeypatch.setattr(module.sys.stdin, "isatty", lambda: True)  # type: ignore[attr-defined]
    args = _namespace(json=False)
    assert module.cmd_advise(args, None) == 130
