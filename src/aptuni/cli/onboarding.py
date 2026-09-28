"""First-run questions for a brand-new user (Beta dogfooding, 2026-09-28).

The source question is about which part of the owner Aptuni may learn from, not about connectors.
Only sources that ship are offered. Folder, Obsidian and GitHub are located in the same flow, so a
chosen source always becomes an exact, confirmable plan step; Notion and MarginNote need a browser
authorization or a macOS permission prompt, so the plan lists the exact commands to run later.
Nothing is connected without an explicit choice, and pressing Enter skips every source.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from aptuni.i18n import t
from aptuni.sources.github import SourceIdentityError
from aptuni.sources.obsidian import is_vault

__all__ = [
    "HOST_MENU", "LATER_SOURCES", "SOURCE_MENU", "ask_folder", "ask_github", "ask_hosts", "ask_obsidian",
    "ask_sources", "intro", "later_lines",
]

SOURCE_MENU = ("folder", "obsidian", "github", "notion", "marginnote")
LATER_SOURCES = ("notion", "marginnote")
HOST_MENU = ("claude_code", "codex")
HOST_NAMES = {"claude_code": "Claude Code", "codex": "Codex"}  # product names are never translated
InputFn = Callable[[str], str]


def intro(locale: str) -> str:
    return t("onboarding.intro", locale)


def _menu(question: str, options: tuple[str, ...], label: Callable[[str], str], hint: str) -> str:
    lines = [question, *(f"  {number}. {label(option)}" for number, option in enumerate(options, start=1)), hint]
    return "\n".join(lines) + "\n> "


def _pick(raw: str, options: tuple[str, ...]) -> frozenset[str] | None:
    picked: set[str] = set()
    for item in (part.strip().lower() for part in raw.replace("，", ",").replace("、", ",").split(",")):
        if not item:
            continue
        if item.isdigit() and 1 <= int(item) <= len(options):
            picked.add(options[int(item) - 1])
        elif item in options:
            picked.add(item)
        else:
            return None
    return frozenset(picked)


def _ask_menu(ask: InputFn, locale: str, prompt: str, options: tuple[str, ...]) -> frozenset[str]:
    while True:
        picked = _pick(ask(prompt).strip(), options)
        if picked is not None:
            return picked
        print(t("advisor.question.invalid", locale))


def ask_sources(ask: InputFn, locale: str) -> frozenset[str]:
    prompt = _menu(t("onboarding.sources.question", locale), SOURCE_MENU,
                   lambda kind: t(f"onboarding.source.{kind}", locale), t("onboarding.sources.hint", locale))
    return _ask_menu(ask, locale, prompt, SOURCE_MENU)


def ask_hosts(ask: InputFn, locale: str) -> frozenset[str]:
    prompt = _menu(t("onboarding.hosts.question", locale), HOST_MENU,
                   HOST_NAMES.__getitem__, t("onboarding.hosts.hint", locale))
    return _ask_menu(ask, locale, prompt, HOST_MENU)


def _ask_path(ask: InputFn, locale: str, key: str, check: Callable[[Path], str | None]) -> str:
    while True:
        raw = ask(t(f"onboarding.ask.{key}", locale) + "\n> ").strip().strip("'\"")
        path = Path(raw).expanduser().resolve() if raw else None
        problem = "empty" if path is None else check(path)
        if problem is None and path is not None:
            return str(path)
        print(t(f"onboarding.invalid.{problem}", locale, path=raw))


def ask_folder(ask: InputFn, locale: str) -> str:
    return _ask_path(ask, locale, "folder", lambda path: None if path.is_dir() else "missing")


def ask_obsidian(ask: InputFn, locale: str) -> str:
    def check(path: Path) -> str | None:
        if not path.is_dir():
            return "missing"
        return None if is_vault(path) else "not_obsidian"
    return _ask_path(ask, locale, "obsidian", check)


def ask_github(ask: InputFn, locale: str, build: Callable[[str], str]) -> str:
    while True:
        raw = ask(t("onboarding.ask.github", locale) + "\n> ").strip()
        try:
            return build(raw)
        except (SourceIdentityError, ValueError):
            print(t("onboarding.invalid.github", locale, path=raw))


def later_lines(sources: frozenset[str], planned_kinds: frozenset[str], locale: str) -> list[str]:
    """What the owner connects later, with the exact command, and a hint when nothing is connected."""
    later = [kind for kind in SOURCE_MENU
             if kind in sources and f"source_{kind}" not in planned_kinds and kind in (*LATER_SOURCES, "obsidian")]
    lines: list[str] = []
    if later:
        lines.append(t("onboarding.later.title", locale))
        lines += [f"  - {t(f'onboarding.later.{kind}', locale)}" for kind in later]
    if not any(kind.startswith("source_") for kind in planned_kinds):
        lines.append(t("onboarding.later.none", locale))
    return lines
