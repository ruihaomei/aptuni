"""``aptuni plugin | recipe | advise``: read-only catalog views and the basic Plugin Advisor.

Nothing here touches the Vault, grants or host configuration. ``advise`` asks the PRD §50 questions
(language first), or takes them as options for scripted use, and prints a preview bound to a plan
digest. Applying a plan is a separate, terminal-confirmed step.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from collections.abc import Callable
from typing import Any

from aptuni.advisor import AdvisorError, CatalogError, SetupAnswers, load_catalog, recommend
from aptuni.advisor.preview import plugin_name, render_preview
from aptuni.advisor.recommend import HOSTS, MEMORY_EXPERIENCES, PRIVACY_MODES, SOURCE_KINDS
from aptuni.i18n import I18nError, normalize_locale, t

HOST_EXECUTABLES = {"claude_code": "claude", "codex": "codex"}
InputFn = Callable[[str], str]


def add_setup_commands(sub: Any) -> None:
    plugin = sub.add_parser("plugin", help="list known plugins and their maturity")
    plugin_sub = plugin.add_subparsers(dest="plugin_command", required=True, metavar="ACTION")
    plugin_list = plugin_sub.add_parser("list", help="list plugins")
    plugin_list.add_argument("--lang", default=None)
    plugin_list.add_argument("--json", action="store_true")

    recipe = sub.add_parser("recipe", help="list or show setup Recipes")
    recipe_sub = recipe.add_subparsers(dest="recipe_command", required=True, metavar="ACTION")
    recipe_list = recipe_sub.add_parser("list", help="list recipes")
    recipe_show = recipe_sub.add_parser("show", help="show one recipe")
    recipe_show.add_argument("recipe_id")
    for parser in (recipe_list, recipe_show):
        parser.add_argument("--lang", default=None)
        parser.add_argument("--json", action="store_true")

    advise = sub.add_parser("advise", help="recommend a setup from a few plain-language questions (read-only)")
    advise.add_argument("--lang", default=None, help="en or zh-CN (asked first when interactive)")
    advise.add_argument("--source", action="append", choices=SOURCE_KINDS, default=None, dest="sources")
    advise.add_argument("--memory", choices=MEMORY_EXPERIENCES)
    advise.add_argument("--privacy", choices=PRIVACY_MODES)
    advise.add_argument("--host", action="append", choices=HOSTS, default=None, dest="hosts")
    advise.add_argument("--no-host", action="store_true", help="plan without any agent host")
    advise.add_argument("--detect-hosts", action="store_true", help="look for claude/codex executables on PATH")
    advise.add_argument("--json", action="store_true")


def _locale(args: argparse.Namespace) -> str:
    return normalize_locale(args.lang or os.environ.get("APTUNI_LANG"))


def detect_hosts() -> frozenset[str]:
    """Only checks PATH for known host executables; never scans personal files."""
    return frozenset(host for host, exe in HOST_EXECUTABLES.items() if shutil.which(exe))


def cmd_plugin(args: argparse.Namespace, _service: object) -> int:
    catalog, locale = load_catalog(), _locale(args)
    plugins = sorted(catalog.plugins.values(), key=lambda p: p.id)
    if args.json:
        print(json.dumps([p.model_dump(mode="json") for p in plugins], ensure_ascii=False, indent=1))
        return 0
    for p in plugins:
        maturity = t(f"catalog.maturity.{p.maturity}", locale)
        print(f"{p.id:24} {maturity:10} {t(p.name, locale)} — {t(p.summary, locale)}")
    return 0


def cmd_recipe(args: argparse.Namespace, _service: object) -> int:
    catalog, locale = load_catalog(), _locale(args)
    if args.recipe_command == "show" and args.recipe_id not in catalog.recipes:
        print(f"aptuni: unknown recipe '{args.recipe_id}'", file=sys.stderr)
        return 2
    recipes = [catalog.recipes[args.recipe_id]] if args.recipe_command == "show" else \
        sorted(catalog.recipes.values(), key=lambda r: r.id)
    if args.json:
        print(json.dumps([{**r.model_dump(mode="json"), "available": catalog.recipe_available(r.id)} for r in recipes],
                         ensure_ascii=False, indent=1))
        return 0
    for r in recipes:
        available = catalog.recipe_available(r.id)
        state = t("catalog.recipe.available" if available else "catalog.recipe.unavailable", locale)
        print(f"{r.id:16} {state:12} {t(r.name, locale)} — {t(r.goal, locale)}")
        if args.recipe_command == "show":
            names = ", ".join(plugin_name(catalog, pid, locale) for pid in r.plugins)
            print("  " + t("catalog.recipe.plugins", locale, plugins=names))
            if r.later:
                later = ", ".join(plugin_name(catalog, pid, locale) for pid in r.later)
                print("  " + t("catalog.recipe.later", locale, plugins=later))
    return 0


def _ask(prompt: str, parse: Callable[[str], Any], ask: InputFn, locale: str) -> Any:
    while True:
        try:
            return parse(ask(prompt + "\n> ").strip())
        except ValueError:
            print(t("advisor.question.invalid", locale))


def _choice(options: tuple[str, ...]) -> Callable[[str], str]:
    def parse(raw: str) -> str:
        if raw.isdigit() and 1 <= int(raw) <= len(options):
            return options[int(raw) - 1]
        if raw in options:
            return raw
        raise ValueError(raw)
    return parse


def _many(options: tuple[str, ...]) -> Callable[[str], frozenset[str]]:
    def parse(raw: str) -> frozenset[str]:
        values = frozenset(v.strip() for v in raw.replace("，", ",").split(",") if v.strip())
        if not values <= set(options):
            raise ValueError(raw)
        return values
    return parse


def collect_answers(args: argparse.Namespace, interactive: bool, ask: InputFn | None = None) -> SetupAnswers:
    """Merge options with interactive answers, asking the PRD §50 questions in order."""
    ask = ask or input
    if args.lang is None and interactive:
        locale = _ask(t("advisor.question.language", "en"), lambda raw: normalize_locale(raw, strict=True), ask, "en")
    else:
        locale = _locale(args)
    sources = frozenset(args.sources or ())
    if args.sources is None and interactive:
        sources = _ask(t("advisor.question.sources", locale), _many(SOURCE_KINDS), ask, locale)
    memory = args.memory or (_ask(t("advisor.question.memory", locale), _choice(MEMORY_EXPERIENCES), ask, locale)
                             if interactive else None)
    privacy = args.privacy or (_ask(t("advisor.question.privacy", locale), _choice(PRIVACY_MODES), ask, locale)
                               if interactive else None)
    if memory is None:
        raise AdvisorError("missing_answer:memory")
    if privacy is None:
        raise AdvisorError("missing_answer:privacy")
    hosts = frozenset(args.hosts or ())
    if args.no_host:
        hosts = frozenset()
    elif args.hosts is None:
        detected = detect_hosts() if (interactive or args.detect_hosts) else frozenset()
        if interactive:
            if detected:
                print(t("advisor.question.detected", locale, hosts=", ".join(sorted(detected))))
            hosts = _ask(t("advisor.question.hosts", locale), _many(HOSTS), ask, locale)
        else:
            hosts = detected
    return SetupAnswers(locale=locale, sources=sources, memory=memory, privacy=privacy, hosts=hosts)


def cmd_advise(args: argparse.Namespace, _service: object) -> int:
    locale = _locale(args)
    interactive = sys.stdin.isatty() and not args.json
    try:
        answers = collect_answers(args, interactive)
        catalog = load_catalog()
        rec = recommend(answers, catalog)
    except (EOFError, KeyboardInterrupt):
        print("\n" + t("advisor.error.cancelled", locale), file=sys.stderr)
        return 130
    except (CatalogError, I18nError):
        print("aptuni: " + t("advisor.error.catalog", "en"), file=sys.stderr)
        return 1
    except AdvisorError as error:
        code, _, name = str(error).partition(":")
        key = "advisor.error.missing_answer" if code == "missing_answer" else "advisor.error.invalid_answer"
        print("aptuni: " + t(key, locale, name=name), file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps({**rec.to_dict(), "digest": rec.digest, "locale": answers.locale},
                         ensure_ascii=False, indent=1))
        return 0
    print("\n".join(render_preview(rec, catalog, answers.locale)))
    return 0
