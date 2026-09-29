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
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from aptuni.adapters.manager import BUNDLE_FILES, SCOPES, AdapterManager, host_disclosure
from aptuni.advisor import AdvisorError, CatalogError, SetupAnswers, load_catalog, recommend
from aptuni.advisor.preview import plugin_name, render_preview
from aptuni.advisor.recommend import HOSTS, MEMORY_EXPERIENCES, PRIVACY_MODES, SOURCE_KINDS
from aptuni.api.v1 import CAPABILITIES, AptuniAPIError, load_manifest
from aptuni.api.v1.grants import PluginGrantManager
from aptuni.application.setup import (
    SetupError,
    SetupPlan,
    SetupStep,
    cancel_setup_plan,
    create_setup_plan,
    finish_setup_cancellation,
    load_setup_plan,
    pending_setup_actions,
    setup_action_state,
)
from aptuni.application.workspace import DEFAULT_VAULT
from aptuni.cli import onboarding
from aptuni.cli.grant_consent import render_consent
from aptuni.cli.host_connect import connect_lines
from aptuni.cli.render import delimited_untrusted
from aptuni.cli.setup_apply import HOST_ADAPTER, PLUGIN_CLAIM, apply_setup_plan, planned_sources
from aptuni.cli.setup_progress import failure_lines
from aptuni.cli.setup_progress import printer as progress_printer
from aptuni.domain.records import MODULES
from aptuni.i18n import I18nError, has_message, normalize_locale, t
from aptuni.sources.github import DEFAULT_API_ORIGIN, GitHubSourceSpec, SourceIdentityError

HOST_EXECUTABLES = {"claude_code": "claude", "codex": "codex"}
DEFAULT_SETUP_MODULES = ("identity", "knowledge", "skills", "projects", "goals", "preferences")
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


@dataclass(frozen=True)
class SourceTargets:
    """Exact source locations collected in the first-run flow; empty when given as options."""

    folders: tuple[str, ...] = ()
    obsidian: str | None = None
    github: tuple[str, ...] = ()


def _ask_language(args: argparse.Namespace, interactive: bool, ask: InputFn) -> str:
    if args.lang is None and interactive:
        locale: str = _ask(t("advisor.question.language", "en"), lambda raw: normalize_locale(raw, strict=True),
                           ask, "en")
        print(onboarding.intro(locale))
        return locale
    return _locale(args)


def _ask_sources(args: argparse.Namespace, interactive: bool, ask: InputFn, locale: str) -> frozenset[str]:
    if args.sources is None and interactive:
        return onboarding.ask_sources(ask, locale)
    return frozenset(args.sources or ())


def _ask_rest(args: argparse.Namespace, interactive: bool, ask: InputFn, locale: str,
              sources: frozenset[str]) -> SetupAnswers:
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
                names = ", ".join(onboarding.HOST_NAMES.get(host, host) for host in sorted(detected))
                print(t("advisor.question.detected", locale, hosts=names))
            hosts = onboarding.ask_hosts(ask, locale)
        else:
            hosts = detected
    return SetupAnswers(locale=locale, sources=sources, memory=memory, privacy=privacy, hosts=hosts)


def collect_answers(args: argparse.Namespace, interactive: bool, ask: InputFn | None = None) -> SetupAnswers:
    """Merge options with interactive answers, asking the PRD §50 questions in order."""
    ask = ask or input
    locale = _ask_language(args, interactive, ask)
    return _ask_rest(args, interactive, ask, locale, _ask_sources(args, interactive, ask, locale))


def collect_setup(args: argparse.Namespace, interactive: bool,
                  ask: InputFn | None = None) -> tuple[SetupAnswers, SourceTargets]:
    """Like ``collect_answers``, and ask where each chosen source is right after it is chosen."""
    ask = ask or input
    locale = _ask_language(args, interactive, ask)
    sources = _ask_sources(args, interactive, ask, locale)
    targets = SourceTargets()
    if interactive:
        targets = SourceTargets(
            folders=(onboarding.ask_folder(ask, locale),) if "folder" in sources and not args.folders else (),
            obsidian=onboarding.ask_obsidian(ask, locale) if "obsidian" in sources and not args.obsidian else None,
            github=(onboarding.ask_github(ask, locale, _github_url),)
            if "github" in sources and not args.github_repositories else (),
        )
    return _ask_rest(args, interactive, ask, locale, sources), targets


def _github_url(raw: str) -> str:
    """Validate a repository address offline and return it unchanged."""
    GitHubSourceSpec.build(raw)
    return raw


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


def add_guided_setup_command(sub: Any) -> None:
    """``aptuni setup``: plan, one terminal confirmation, apply, cancel (plan 02 steps 1, 4, 5)."""
    setup = sub.add_parser("setup", help="plan and apply a complete guided setup")
    setup_sub = setup.add_subparsers(dest="setup_command", required=True, metavar="ACTION")

    plan = setup_sub.add_parser("plan", help="build a setup plan; creates nothing")
    plan.add_argument("--lang", default=None, help="en or zh-CN (asked first when interactive)")
    plan.add_argument("--source", action="append", choices=SOURCE_KINDS, default=None, dest="sources")
    plan.add_argument("--memory", choices=MEMORY_EXPERIENCES)
    plan.add_argument("--privacy", choices=PRIVACY_MODES)
    plan.add_argument("--host", action="append", choices=HOSTS, default=None, dest="hosts")
    plan.add_argument("--no-host", action="store_true", help="plan without any agent host")
    plan.add_argument("--detect-hosts", action="store_true", help="look for claude/codex executables on PATH")
    plan.add_argument("--vault", default=None, help="where the Profile Vault goes")
    plan.add_argument("--folder", action="append", default=None, dest="folders",
                      help="an exact folder to approve as a source (repeatable); never discovered for you")
    plan.add_argument("--obsidian", default=None, help="an exact Obsidian vault folder to approve as a source")
    plan.add_argument("--github", action="append", default=None, dest="github_repositories",
                      help="an exact GitHub https repository URL to approve (repeatable)")
    plan.add_argument("--github-ref", help="branch, tag, or commit to follow for each --github repository")
    plan.add_argument("--github-token-env", help="environment variable holding a least-scope GitHub token")
    plan.add_argument("--github-api-origin", default=DEFAULT_API_ORIGIN,
                      help="GitHub API origin (Enterprise must use the same host's /api/v3)")
    plan.add_argument("--marginnote-store", type=Path,
                      help="exact local MarginNote 4 SQLite library path from explicit discovery")
    margin_scope = plan.add_mutually_exclusive_group()
    margin_scope.add_argument("--marginnote-notebook", action="append", dest="marginnote_notebooks")
    margin_scope.add_argument("--marginnote-all-notebooks", action="store_true")
    plan.add_argument("--module", action="append", choices=MODULES, default=None, dest="modules")
    plan.add_argument("--plugin-manifest", type=Path, default=None,
                      help="also approve this installed plugin's Aptuni grant in the same confirmation")
    plan.add_argument("--plugin-capability", action="append", choices=CAPABILITIES, default=None,
                      dest="plugin_capabilities", help="grant only these plugin capabilities (repeatable)")
    plan.add_argument("--json", action="store_true")

    apply_parser = setup_sub.add_parser("apply", help="apply one exact plan after a terminal confirmation")
    apply_parser.add_argument("action_id")
    apply_parser.add_argument("--lang", default=None)
    apply_parser.add_argument("--json", action="store_true")

    cancel = setup_sub.add_parser("cancel", help="cancel a plan and roll back what it created")
    cancel.add_argument("action_id")
    cancel.add_argument("--lang", default=None)

    status = setup_sub.add_parser("status", help="show setup actions you can still apply or resume")
    status.add_argument("--lang", default=None)
    status.add_argument("--json", action="store_true")


def _plan_steps(
    answers: SetupAnswers,
    folders: tuple[str, ...],
    obsidian: str | None,
    github_targets: tuple[str, ...],
    marginnote_target: str | None,
    vault: Path,
) -> tuple[SetupStep, ...]:
    """Exactly what will happen, in order. Every target is explicit; nothing is inferred at apply."""
    steps = [SetupStep("vault", str(vault))]
    steps += [SetupStep("source_folder", folder) for folder in folders]
    if obsidian is not None:
        steps.append(SetupStep("source_obsidian", obsidian))
    steps += [SetupStep("source_github", target) for target in github_targets]
    if marginnote_target is not None:
        steps.append(SetupStep("source_marginnote", marginnote_target))
    if folders or obsidian or github_targets or marginnote_target is not None:
        steps.append(SetupStep("sync", "approved"))
    if answers.privacy != "local_only":
        steps += [SetupStep("adapter", host) for host in sorted(answers.hosts) if host in HOST_ADAPTER]
    steps += [SetupStep("doctor", "vault"), SetupStep("smoke", "context")]
    return tuple(steps)


def _host_files(steps: tuple[SetupStep, ...]) -> tuple[str, ...]:
    """Every file the apply step will write, read from the adapter that writes them (Review 33 B6)."""
    return tuple(f"{step.target}: {name}" for step in steps if step.kind == "adapter"
                 for name in BUNDLE_FILES[HOST_ADAPTER[step.target]])


def _egress(steps: tuple[SetupStep, ...]) -> tuple[dict[str, str], ...]:
    """Who receives personal context, where, and under whose retention (Review 33 B2)."""
    return tuple({"host": step.target, **host_disclosure(HOST_ADAPTER[step.target]),
                  "scope_count": str(len(SCOPES)), "scopes": ", ".join(SCOPES)}
                 for step in steps if step.kind == "adapter")


def _render_plan(plan: SetupPlan, locale: str, action_state: str = "pending") -> list[str]:
    """Render the one surface the owner confirms.

    Every value that came from outside the core is escaped and delimited, so a crafted folder name
    cannot forge a line here -- notably a false confinement claim (Review 33 B1, ADR-0013 item 2).
    """
    lines = [t("setup.plan.title", locale), "",
             t("setup.plan.action", locale, action_id=plan.action_id),
             t("setup.plan.vault", locale, path=delimited_untrusted(plan.vault_path)), "",
             t("setup.plan.steps", locale)]
    for number, step in enumerate(plan.steps, start=1):
        kind = "vault_existing" if step.kind == "vault" and (Path(step.target) / "HEAD.json").is_file() else step.kind
        text = t(f"setup.plan.step.{kind}", locale, target=delimited_untrusted(_shown_target(step.kind, step.target)))
        lines.append(f"  {number}. {text}")
    lines.append("")
    for step in plan.steps:
        if step.kind == "plugin_grant":
            lines += [*_plugin_consent(step.target, locale), ""]
    later = onboarding.later_lines(frozenset(plan.answers.get("sources", ())),
                                   frozenset(step.kind for step in plan.steps), locale)
    if later:
        lines += [*later, ""]
    lines += _render_release(plan, locale)
    if plan.host_files:
        lines += [t("setup.plan.host_files", locale),
                  *(f"  - {delimited_untrusted(name)}" for name in plan.host_files),
                  t("setup.plan.bundle_root", locale, path=delimited_untrusted(plan.bundle_root)),
                  t("setup.plan.host_not_modified", locale)]
    else:
        lines.append(t("setup.plan.host_files_none", locale))
    state_key = {"pending": "setup.plan.nothing_yet", "resumable": "setup.plan.resumable",
                 "complete": "setup.plan.already_complete"}[action_state]
    lines += [t("setup.plan.confinement", locale),
              t("setup.plan.rollback", locale), "",
              t(state_key, locale),
              t("setup.plan.expires", locale, expires=_when(plan.expires_at), digest=plan.digest),
              t("setup.plan.confirm_hint", locale, action_id=plan.action_id)]
    return lines


def _render_release(plan: SetupPlan, locale: str) -> list[str]:
    """State plainly what typing APPLY releases, to whom (Review 33 B2, B3)."""
    if not plan.egress:
        hosts = plan.answers.get("hosts", [])
        key = "setup.plan.release_local_host" if hosts else "setup.plan.release_none"
        return [t(key, locale, modules=_module_names(plan.modules, locale), hosts=", ".join(hosts)), ""]
    lines = [t("setup.plan.release", locale, modules=_module_names(plan.modules, locale))]
    for item in plan.egress:
        lines.append(t("setup.plan.release_to", locale, host=delimited_untrusted(item["host"]),
                       operator=delimited_untrusted(item["operator"]),
                       destination=delimited_untrusted(item["destination"]),
                       retention=_retention(item["retention"], locale),
                       scope_count=item["scope_count"], scopes=item["scopes"]))
    operators = ", ".join(dict.fromkeys(delimited_untrusted(item["operator"]) for item in plan.egress))
    for step in plan.steps:
        if step.kind == "plugin_grant":
            value = json.loads(step.target)
            lines.append(t("setup.plan.release_plugin", locale, name=delimited_untrusted(value["name"]),
                           modules=_module_names(value["modules"], locale), operators=operators))
    lines += [t("setup.plan.release_change", locale), ""]
    return lines


def _shown_target(kind: str, target: str) -> str:
    """Show GitHub and plugin steps by name rather than by their frozen JSON targets."""
    if kind not in ("source_github", "plugin_grant"):
        return target
    try:
        value = json.loads(target)
        if kind == "plugin_grant":
            return f"{value['plugin_id']} {value['version']}"
        return str(value["repository_url"]) + (f" @ {value['ref']}" if value.get("ref") else "")
    except (json.JSONDecodeError, KeyError, TypeError):
        return target


def _plugin_consent(target: str, locale: str) -> list[str]:
    value = json.loads(target)
    return render_consent(plugin_id=value["plugin_id"], version=value["version"],
                          capabilities=tuple(value["capabilities"]), required=tuple(value["required"]),
                          modules=tuple(value["modules"]), locale=locale, name=value["name"],
                          narrow_flag="--plugin-capability")


def _retention(value: str, locale: str) -> str:
    key = f"setup.retention.{value}"
    return t(key, locale) if has_message(key, locale) else delimited_untrusted(value)


def _when(value: str) -> str:
    """Show an ISO timestamp as minutes in UTC; leave anything unexpected untouched."""
    try:
        return datetime.fromisoformat(value).astimezone(UTC).strftime("%Y-%m-%d %H:%M UTC")
    except (TypeError, ValueError):
        return value


def _module_names(modules: tuple[str, ...] | list[str], locale: str) -> str:
    """Keep the exact module ids that ``aptuni module set`` takes; add the local name in Chinese."""
    if locale != "zh-CN":
        return ", ".join(modules)
    return "、".join(f"{t(f'consent.module.{module}', locale)}（{module}）" for module in modules)


def cmd_setup(args: argparse.Namespace, service: Any) -> int:
    handlers = {"plan": _setup_plan, "apply": _setup_apply, "cancel": _setup_cancel, "status": _setup_status}
    return handlers[args.setup_command](args, service)


def _setup_plan(args: argparse.Namespace, service: Any) -> int:  # noqa: PLR0911 - CLI error exits are explicit
    locale = _locale(args)
    interactive = sys.stdin.isatty() and not args.json
    try:
        answers, targets = collect_setup(args, interactive)
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
    locale = answers.locale
    folders = tuple(str(Path(folder).expanduser().resolve()) for folder in (*(args.folders or ()), *targets.folders))
    obsidian = targets.obsidian or (str(Path(args.obsidian).expanduser().resolve()) if args.obsidian else None)
    try:
        github_targets = tuple(_github_target(repository, args.github_api_origin, args.github_ref,
                                               args.github_token_env)
                               for repository in (*(args.github_repositories or ()), *targets.github))
        marginnote_target = _marginnote_target(args)
    except (SourceIdentityError, ValueError) as error:
        print("aptuni: " + str(error), file=sys.stderr)
        return 2
    if not _sources_located(answers, locale, folders, github_targets):
        return 2
    try:
        plugin_target = _plugin_target(args.plugin_manifest, args.plugin_capabilities)
    except (AptuniAPIError, OSError, ValueError) as error:
        print("aptuni: " + t("setup.error.plugin_manifest", locale, reason=str(error)), file=sys.stderr)
        return 2
    if plugin_target is not None and (answers.privacy == "local_only" or not set(answers.hosts) & set(HOST_ADAPTER)):
        # A plugin's reads reach the model of the agent that runs it; no such release exists here.
        print("aptuni: " + t("setup.error.plugin_needs_host", locale), file=sys.stderr)
        return 2
    modules = tuple(dict.fromkeys(args.modules or DEFAULT_SETUP_MODULES))
    vault = _planned_vault(args, service, locale)
    if vault is None:
        return 2
    steps = _plan_steps(answers, folders, obsidian, github_targets, marginnote_target, vault)
    if plugin_target is not None:
        steps = (*steps[:-2], SetupStep("plugin_grant", plugin_target), *steps[-2:])
    plan = create_setup_plan(
        service.workspace.state_dir, catalog_digest=catalog.version_digest(), locale=answers.locale,
        answers={"sources": sorted(answers.sources), "memory": answers.memory, "privacy": answers.privacy,
                 "hosts": sorted(answers.hosts)},
        recommendation_digest=rec.digest, recipe_id=rec.recipe_id, vault_path=vault, modules=modules,
        host_files=_host_files(steps), egress=_egress(steps),
        bundle_root=service.workspace.state_dir / "adapters" / "bundles", steps=steps,
    )
    if args.json:
        print(json.dumps(plan.to_dict(), ensure_ascii=False, indent=1))
        return 0
    print("\n".join(render_preview(rec, catalog, answers.locale, footer=False, brief=True)))
    print()
    print("\n".join(_render_plan(plan, answers.locale)))
    return 0


def _plugin_target(manifest_path: Path | None, capabilities: list[str] | None) -> str | None:
    """Freeze exactly what the plugin grant will be: manifest digest, capabilities and modules."""
    if manifest_path is None:
        return None
    path = manifest_path.expanduser().resolve()
    manifest = load_manifest(path)
    if manifest.egress != ("none",):
        raise ValueError("this plugin declares network egress; setup only grants local no-egress plugins")
    selected = tuple(capabilities or manifest.requested_capabilities)
    if not set(selected) <= set(manifest.requested_capabilities):
        raise ValueError("the grant cannot exceed the capabilities the plugin requests")
    if not set(manifest.required_capabilities) <= set(selected):
        raise ValueError("the grant must include every capability the plugin requires")
    return json.dumps({"manifest": str(path), "digest": manifest.digest(), "plugin_id": manifest.id,
                       "name": manifest.name, "version": manifest.version, "capabilities": list(selected),
                       "required": list(manifest.required_capabilities), "modules": list(manifest.modules)},
                      ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _planned_vault(args: argparse.Namespace, service: Any, locale: str) -> Path | None:
    """The configured Vault by default; refuse another one before the owner types APPLY."""
    configured = service.workspace.vault_path()
    vault = Path(args.vault).expanduser().resolve() if args.vault else Path(configured or DEFAULT_VAULT)
    if configured is not None and Path(configured).resolve() != vault.resolve():
        print("aptuni: " + t("setup.error.other_vault", locale, configured=delimited_untrusted(str(configured))),
              file=sys.stderr)
        return None
    return vault


def _sources_located(answers: SetupAnswers, locale: str, folders: tuple[str, ...],
                     github_targets: tuple[str, ...]) -> bool:
    """Every chosen folder or GitHub source must name its exact location.

    Notion, MarginNote without a store, and Obsidian without a path are listed as later steps with
    exact commands instead, in interactive and scripted setup alike.
    """
    missing: list[tuple[str, str]] = []
    if answers.sources & {"folder", "application_materials"} and not folders:
        missing.append(("folder", "--folder PATH"))
    if "github" in answers.sources and not github_targets:
        missing.append(("github", "--github URL"))
    if missing:
        names = "、".join(t(f"onboarding.name.{kind}", locale) for kind, _ in missing) if locale == "zh-CN" \
            else ", ".join(t(f"onboarding.name.{kind}", locale) for kind, _ in missing)
        print("aptuni: " + t("setup.error.missing_source", locale, sources=names,
                             flags=" ".join(flag for _, flag in missing)), file=sys.stderr)
        return False
    return True


def _github_target(repository: str, api_origin: str, ref: str | None, token_env: str | None) -> str:
    spec = GitHubSourceSpec.build(repository, api_origin=api_origin, ref=ref, token_env=token_env)
    return json.dumps({"repository_url": spec.repository_url, "api_origin": spec.api_origin,
                       "ref": spec.ref, "token_env": spec.token_env},
                      ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _marginnote_target(args: argparse.Namespace) -> str | None:
    store = args.marginnote_store
    notebooks = args.marginnote_notebooks
    all_notebooks = args.marginnote_all_notebooks
    if store is None:
        if notebooks or all_notebooks:
            raise ValueError("--marginnote-store is required with a notebook scope")
        return None
    if not notebooks and not all_notebooks:
        raise ValueError("choose --marginnote-notebook or --marginnote-all-notebooks")
    resolved = store.expanduser().resolve()
    if not resolved.is_file():
        raise ValueError("the exact MarginNote store does not exist")
    return json.dumps({"store": str(resolved), "notebooks": None if all_notebooks else sorted(set(notebooks))},
                      ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _setup_apply(args: argparse.Namespace, service: Any) -> int:
    plan = load_setup_plan(service.workspace.state_dir, args.action_id)
    action_state = setup_action_state(service.workspace.state_dir, args.action_id)
    locale = _locale(args) if args.lang else plan.locale
    catalog = load_catalog()
    if plan.catalog_digest != catalog.version_digest():
        raise SetupError("setup_catalog_changed", "The bundled catalog changed; cancel and plan setup again.")
    answers = _answers_from_plan(plan)
    rec = recommend(answers, catalog)
    if rec.digest != plan.recommendation_digest or rec.recipe_id != plan.recipe_id:
        raise SetupError("setup_action_invalid", "The frozen setup recommendation no longer matches its plan.")
    print("\n".join((*render_preview(rec, catalog, locale, footer=False, brief=True), "",
                     *_render_plan(plan, locale, action_state))))
    try:
        typed = input(t("setup.apply.prompt", locale)).strip()
    except (EOFError, KeyboardInterrupt):
        print("\n" + t("setup.apply.cancelled" if action_state == "pending"
                         else "setup.apply.declined_resume", locale))
        return 130
    if typed != "APPLY":
        print(t("setup.apply.cancelled" if action_state == "pending"
                else "setup.apply.declined_resume", locale))
        return 1
    report = apply_setup_plan(service, args.action_id, plan.digest, progress=progress_printer(locale))
    if args.json:
        print(json.dumps(report.to_dict(), ensure_ascii=False, indent=1))
        return 0 if report.terminal_state == "complete" else 2
    return _print_report(report, plan, locale, service)


def _answers_from_plan(plan: SetupPlan) -> SetupAnswers:
    try:
        value = plan.answers
        if set(value) != {"sources", "memory", "privacy", "hosts"}:
            raise TypeError
        sources, memory = value["sources"], value["memory"]
        privacy, hosts = value["privacy"], value["hosts"]
        if (not isinstance(sources, list) or not isinstance(hosts, list)
                or not isinstance(memory, str) or not isinstance(privacy, str)
                or any(not isinstance(item, str) for item in (*sources, *hosts))):
            raise TypeError
        answers = SetupAnswers(plan.locale, frozenset(sources), memory, privacy, frozenset(hosts))
        answers.validate()
        return answers
    except (AdvisorError, KeyError, TypeError, ValueError) as error:
        raise SetupError("setup_action_invalid", "The setup plan contains invalid advisor answers.") from error


def _print_report(report: Any, plan: SetupPlan, locale: str, service: Any) -> int:
    print(t("setup.apply.result", locale, action_id=report.action_id, state=report.terminal_state))
    for key, result in report.results.items():
        kind, _, target = key.partition(":")
        print(t("setup.apply.step_result", locale, step=delimited_untrusted(f"{kind}:{_shown_target(kind, target)}"),
                result=result))
    if report.terminal_state != "complete":
        print(t("setup.apply.resumable", locale, failure=report.failure or "an earlier step"))
        print(t("setup.apply.rollback", locale, action_id=report.action_id))
        return 2
    print(t("setup.apply.vault", locale, path=delimited_untrusted(report.vault_path)))
    print(t("setup.apply.doctor_ok" if report.doctor_ok else "setup.apply.doctor_failed", locale))
    print(t("setup.apply.smoke_ok" if report.smoke_ok else "setup.apply.smoke_empty", locale))
    if report.grants:
        print(t("setup.apply.grants", locale, grants=", ".join(report.grants)))
        print(t("setup.apply.bundle_written", locale, path=delimited_untrusted(plan.bundle_root)))
        for name in report.host_files:
            print(f"  - {delimited_untrusted(name)}")
        print(t("setup.plan.host_not_modified", locale))
        for grant in report.grants:
            lines = connect_lines(Path(plan.bundle_root) / grant, locale)
            if lines:
                print("\n".join(("", *lines)))
        print(t("setup.apply.relaunch", locale))
    for grant_id in report.plugin_grants:
        print(t("setup.apply.plugin_grant", locale, grant_id=grant_id))
    for line in failure_lines(report.source_failures, service.sources(), locale):
        print(line)
    print(t("setup.apply.host_status", locale))
    print(t("setup.apply.privacy", locale))
    print(t("setup.apply.rollback", locale, action_id=report.action_id))
    print(t("setup.apply.next", locale))
    return 0


def _setup_cancel(args: argparse.Namespace, service: Any) -> int:
    """Roll back what this action created, and say exactly what stayed (Review 33 B4)."""
    locale = _locale(args)
    plan = load_setup_plan(service.workspace.state_dir, args.action_id)
    was_confirmed, rollback = cancel_setup_plan(service.workspace.state_dir, args.action_id)
    manager = AdapterManager(service.workspace)
    plugins = PluginGrantManager(service.workspace)
    rolled = [item for item in rollback if item.startswith("grant-") and manager.revoke(item)]
    for item in rollback:
        if item.startswith(PLUGIN_CLAIM):
            grant_id = item.removeprefix(PLUGIN_CLAIM)
            discarded = plugins.cancel("act-" + grant_id.removeprefix("grant-"))  # a preview left by a crash
            if plugins.revoke(grant_id) or discarded:
                rolled.append(grant_id)
    if not was_confirmed:
        print(t("setup.cancel.nothing", locale, action_id=args.action_id))
        return 0
    finish_setup_cancellation(service.workspace.state_dir, args.action_id)
    print(t("setup.cancel.removed", locale, action_id=args.action_id,
            items=", ".join(rolled) if rolled else t("setup.cancel.no_grants", locale)))
    kept = [delimited_untrusted(plan.vault_path)] if Path(plan.vault_path).exists() else []
    kept += [delimited_untrusted(source.roots[0]) for source in planned_sources(service, plan)]
    if kept:
        print(t("setup.cancel.kept", locale, items="; ".join(kept)))
    print(t("setup.cancel.vault_kept", locale))
    return 0


def _setup_status(args: argparse.Namespace, service: Any) -> int:
    locale = _locale(args)
    actions = pending_setup_actions(service.workspace.state_dir)
    if args.json:
        print(json.dumps({"pending": actions}, ensure_ascii=False, indent=1))
        return 0
    print(t("setup.status.pending", locale, actions=", ".join(actions)) if actions
          else t("setup.status.none", locale))
    return 0
