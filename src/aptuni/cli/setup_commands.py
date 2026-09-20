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
from pathlib import Path
from typing import Any

from aptuni.adapters.manager import BUNDLE_FILES, SCOPES, AdapterManager, host_disclosure
from aptuni.advisor import AdvisorError, CatalogError, SetupAnswers, load_catalog, recommend
from aptuni.advisor.preview import plugin_name, render_preview
from aptuni.advisor.recommend import HOSTS, MEMORY_EXPERIENCES, PRIVACY_MODES, SOURCE_KINDS
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
from aptuni.cli.render import delimited_untrusted
from aptuni.cli.setup_apply import HOST_ADAPTER, apply_setup_plan, planned_sources
from aptuni.domain.records import MODULES
from aptuni.i18n import I18nError, normalize_locale, t
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
    github_targets: tuple[str, ...],
    marginnote_target: str | None,
    vault: Path,
) -> tuple[SetupStep, ...]:
    """Exactly what will happen, in order. Every target is explicit; nothing is inferred at apply."""
    steps = [SetupStep("vault", str(vault))]
    steps += [SetupStep("source_folder", folder) for folder in folders]
    steps += [SetupStep("source_github", target) for target in github_targets]
    if marginnote_target is not None:
        steps.append(SetupStep("source_marginnote", marginnote_target))
    if folders or github_targets or marginnote_target is not None:
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
        text = t(f"setup.plan.step.{step.kind}", locale, target=delimited_untrusted(step.target))
        lines.append(f"  {number}. {text}")
    lines.append("")
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
              t("setup.plan.expires", locale, expires=plan.expires_at, digest=plan.digest),
              t("setup.plan.confirm_hint", locale, action_id=plan.action_id)]
    return lines


def _render_release(plan: SetupPlan, locale: str) -> list[str]:
    """State plainly what typing APPLY releases, to whom (Review 33 B2, B3)."""
    if not plan.egress:
        hosts = plan.answers.get("hosts", [])
        key = "setup.plan.release_local_host" if hosts else "setup.plan.release_none"
        return [t(key, locale, modules=", ".join(plan.modules), hosts=", ".join(hosts)), ""]
    lines = [t("setup.plan.release", locale, modules=", ".join(plan.modules))]
    for item in plan.egress:
        lines.append(t("setup.plan.release_to", locale, host=delimited_untrusted(item["host"]),
                       operator=delimited_untrusted(item["operator"]),
                       destination=delimited_untrusted(item["destination"]),
                       retention=delimited_untrusted(item["retention"]),
                       scope_count=item["scope_count"], scopes=item["scopes"]))
    lines += [t("setup.plan.release_change", locale), ""]
    return lines


def cmd_setup(args: argparse.Namespace, service: Any) -> int:
    handlers = {"plan": _setup_plan, "apply": _setup_apply, "cancel": _setup_cancel, "status": _setup_status}
    return handlers[args.setup_command](args, service)


def _setup_plan(args: argparse.Namespace, service: Any) -> int:  # noqa: PLR0911 - CLI error exits are explicit
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
    folders = tuple(str(Path(folder).expanduser().resolve()) for folder in (args.folders or ()))
    try:
        github_targets = tuple(_github_target(repository, args.github_api_origin, args.github_ref,
                                               args.github_token_env)
                               for repository in (args.github_repositories or ()))
        marginnote_target = _marginnote_target(args)
    except (SourceIdentityError, ValueError) as error:
        print("aptuni: " + str(error), file=sys.stderr)
        return 2
    missing = []
    if answers.sources & {"folder", "application_materials"} and not folders:
        missing.append("--folder")
    if "github" in answers.sources and not github_targets:
        missing.append("--github")
    if "marginnote" in answers.sources and marginnote_target is None:
        missing.append("--marginnote-store plus a notebook scope")
    if missing:
        print("aptuni: exact configuration required for shipped source(s): " + ", ".join(missing), file=sys.stderr)
        return 2
    modules = tuple(dict.fromkeys(args.modules or DEFAULT_SETUP_MODULES))
    vault = Path(args.vault).expanduser().resolve() if args.vault else DEFAULT_VAULT
    steps = _plan_steps(answers, folders, github_targets, marginnote_target, vault)
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
    print("\n".join(render_preview(rec, catalog, answers.locale)))
    print()
    print("\n".join(_render_plan(plan, answers.locale)))
    return 0


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
    print("\n".join((*render_preview(rec, catalog, locale, footer=False), "",
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
    report = apply_setup_plan(service, args.action_id, plan.digest)
    if args.json:
        print(json.dumps(report.to_dict(), ensure_ascii=False, indent=1))
        return 0 if report.terminal_state == "complete" else 2
    return _print_report(report, plan, locale)


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


def _print_report(report: Any, plan: SetupPlan, locale: str) -> int:
    print(t("setup.apply.result", locale, action_id=report.action_id, state=report.terminal_state))
    for key, result in report.results.items():
        print(t("setup.apply.step_result", locale, step=delimited_untrusted(key), result=result))
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
        print(t("setup.apply.relaunch", locale))
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
    rolled = [item for item in rollback if item.startswith("grant-") and manager.revoke(item)]
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
