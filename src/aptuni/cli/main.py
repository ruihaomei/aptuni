"""``aptuni`` command line: the owner's terminal interface to their Vault."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

from aptuni import __version__
from aptuni.application.errors import AptuniError
from aptuni.application.service import AptuniService, Status
from aptuni.application.workspace import DEFAULT_VAULT, Workspace
from aptuni.domain.records import MODULES


def _on_off(value: str) -> bool:
    if value not in ("on", "off"):
        raise argparse.ArgumentTypeError("use 'on' or 'off'")
    return value == "on"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="aptuni", description="Aptuni — context, attuned to you.")
    parser.add_argument("--version", action="version", version=f"aptuni {__version__}")
    sub = parser.add_subparsers(dest="command", required=True, metavar="COMMAND")

    init = sub.add_parser("init", help="create your Profile Vault")
    init.add_argument("path", nargs="?", type=Path, default=DEFAULT_VAULT,
                      help=f"Vault location (default: {DEFAULT_VAULT})")

    status = sub.add_parser("status", help="show Vault location, size and module switches")
    status.add_argument("--json", action="store_true")

    remember = sub.add_parser("remember", help="record something true about you")
    remember.add_argument("statement")
    remember.add_argument("--module", required=True, choices=MODULES)
    remember.add_argument("--from", dest="valid_from", help="valid from (YYYY, YYYY-MM or YYYY-MM-DD)")
    remember.add_argument("--until", dest="valid_until", help="valid until (partial date)")

    facts = sub.add_parser("facts", help="list current facts")
    facts.add_argument("--module", choices=MODULES)
    facts.add_argument("--json", action="store_true")

    correct = sub.add_parser("correct", help="replace a fact (history is kept)")
    correct.add_argument("fact_id")
    correct.add_argument("statement")

    retract = sub.add_parser("retract", help="withdraw a fact (history is kept; not a deletion)")
    retract.add_argument("fact_id")

    module = sub.add_parser("module", help="control what enters (ingest) and what agents see (expose)")
    module_sub = module.add_subparsers(dest="module_command", required=True, metavar="ACTION")
    module_list = module_sub.add_parser("list", help="show module switches")
    module_list.add_argument("--json", action="store_true")
    module_set = module_sub.add_parser("set", help="change one module")
    module_set.add_argument("name", choices=MODULES)
    module_set.add_argument("--ingest", type=_on_off, metavar="on|off")
    module_set.add_argument("--expose", type=_on_off, metavar="on|off")

    source = sub.add_parser("source", help="approve and inspect personal data sources")
    source_sub = source.add_subparsers(dest="source_command", required=True, metavar="ACTION")
    source_add = source_sub.add_parser("add-folder", help="approve a local folder as a source")
    source_add.add_argument("path", type=Path)
    source_add.add_argument("--module", action="append", required=True, choices=MODULES, dest="modules")
    source_add.add_argument("--role", required=True, help="what this folder means (for example: portfolio)")
    source_add.add_argument("--primary-for", action="append", default=[], metavar="DIMENSION")
    source_add.add_argument("--json", action="store_true")
    source_list = source_sub.add_parser("list", help="list approved sources")
    source_list.add_argument("--json", action="store_true")

    sync = sub.add_parser("sync", help="sync one approved source into minimized evidence")
    sync.add_argument("source_id")
    sync.add_argument("--json", action="store_true")

    evidence = sub.add_parser("evidence", help="inspect current source evidence")
    evidence.add_argument("--source", dest="source_id")
    evidence.add_argument("--json", action="store_true")

    review = sub.add_parser("review", help="inspect or resolve held source changes")
    review_sub = review.add_subparsers(dest="review_command", required=True, metavar="ACTION")
    review_list = review_sub.add_parser("list", help="list source changes waiting for review")
    review_list.add_argument("source_id")
    review_list.add_argument("--json", action="store_true")

    sub.add_parser("doctor", help="recover and fully verify the Vault")
    return parser


def _print_json(value: Any) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True))


def _modules_json(status: Status) -> dict[str, dict[str, bool]]:
    return {m: {"ingest": i, "expose": e} for m, (i, e) in status.modules.items()}


def _print_modules(status: Status) -> None:
    print(f"{'module':<14} {'ingest':<7} expose")
    for name, (ingest, expose) in status.modules.items():
        print(f"{name:<14} {'on' if ingest else 'off':<7} {'on' if expose else 'off'}")


def _cmd_init(args: argparse.Namespace, service: AptuniService) -> int:
    status = service.init(args.path)
    print(f"Created your Aptuni Vault at {status.vault_path}")
    print(f"Local state (lock, ledger, config): {status.state_dir}")
    return 0


def _cmd_status(args: argparse.Namespace, service: AptuniService) -> int:
    status = service.status()
    if args.json:
        _print_json({"vault": str(status.vault_path), "state_dir": str(status.state_dir), "seq": status.seq,
                     "policy_epoch": status.policy_epoch, "counts": status.counts, "modules": _modules_json(status)})
        return 0
    print(f"Vault: {status.vault_path}  (commit {status.seq}, policy epoch {status.policy_epoch})")
    print("Records: " + (", ".join(f"{k}={v}" for k, v in sorted(status.counts.items())) or "none"))
    hidden = [m for m, (_, expose) in status.modules.items() if not expose]
    print("Hidden from agents: " + (", ".join(hidden) or "nothing"))
    return 0


def _cmd_remember(args: argparse.Namespace, service: AptuniService) -> int:
    fact = service.remember(args.statement, args.module, args.valid_from, args.valid_until)
    print(f"Remembered in {fact.module}: {fact.id}")
    return 0


def _cmd_facts(args: argparse.Namespace, service: AptuniService) -> int:
    facts = service.facts(args.module)
    if args.json:
        _print_json([{"id": f.id, "module": f.module, "statement": f.statement, "valid_from": f.valid_from,
                      "valid_until": f.valid_until, "trust": f.trust} for f in facts])
    elif not facts:
        print('No facts yet. Add one with: aptuni remember "..." --module preferences')
    else:
        for fact in facts:
            print(f"{fact.id}  [{fact.module}]  {fact.statement}")
    return 0


def _cmd_correct(args: argparse.Namespace, service: AptuniService) -> int:
    fact = service.correct(args.fact_id, args.statement)
    print(f"Corrected; new fact {fact.id} supersedes {args.fact_id}")
    return 0


def _cmd_retract(args: argparse.Namespace, service: AptuniService) -> int:
    service.retract(args.fact_id)
    print(f"Retracted {args.fact_id} (kept in history)")
    return 0


def _cmd_module(args: argparse.Namespace, service: AptuniService) -> int:
    if args.module_command == "set":
        service.set_module(args.name, ingest=args.ingest, expose=args.expose)
    status = service.status()
    if getattr(args, "json", False):
        _print_json(_modules_json(status))
    else:
        _print_modules(status)
    return 0


def _source_json(source: Any) -> dict[str, Any]:
    return {
        "id": source.id,
        "type": source.source_type,
        "roots": list(source.roots),
        "role": source.semantic_role,
        "modules": list(source.module_mapping),
        "primary_for": list(source.authority.primary_for),
    }


def _cmd_source(args: argparse.Namespace, service: AptuniService) -> int:
    if args.source_command == "add-folder":
        source = service.add_folder_source(
            args.path,
            modules=tuple(args.modules),
            role=args.role,
            primary_for=tuple(args.primary_for),
        )
        if args.json:
            _print_json(_source_json(source))
        else:
            print(f"Approved folder source {source.id}: {source.roots[0]}")
        return 0
    sources = service.sources()
    if args.json:
        _print_json([_source_json(source) for source in sources])
    elif not sources:
        print("No sources yet. Add one with: aptuni source add-folder PATH --module knowledge --role notes")
    else:
        for source in sources:
            print(f"{source.id}  [{source.source_type}]  {source.semantic_role}  {source.roots[0]}")
    return 0


def _cmd_sync(args: argparse.Namespace, service: AptuniService) -> int:
    report = service.sync(args.source_id)
    value = {
        "source_id": report.source_id,
        "counts": report.counts,
        "review_items": report.review_items,
        "notes": list(report.notes),
        "evidence_written": report.evidence_written,
    }
    if args.json:
        _print_json(value)
    else:
        changes = ", ".join(f"{kind}={count}" for kind, count in sorted(report.counts.items())) or "no changes"
        print(f"Synced {report.source_id}: {changes}; evidence={report.evidence_written}; review={report.review_items}")
    return 0


def _cmd_evidence(args: argparse.Namespace, service: AptuniService) -> int:
    evidence = service.evidence(args.source_id)
    values = [
        {
            "id": item.id,
            "source_id": item.provenance.source_id,
            "module": item.module,
            "relative_path": item.provenance.locator.extension.fields.get("relative_path"),
            "signals": list(item.signals),
            "excerpt": item.excerpt,
            "content_hash": item.content_hash,
            "review_status": item.review_status,
        }
        for item in evidence
    ]
    if args.json:
        _print_json(values)
    elif not values:
        print("No current evidence.")
    else:
        for item in values:
            print(f"{item['id']}  [{item['module']}]  {item['relative_path']}  {', '.join(item['signals'])}")
    return 0


def _review_json(operation: Any) -> dict[str, Any]:
    locator = operation.after or operation.before
    return {
        "kind": operation.kind,
        "subject_id": operation.subject_id,
        "relative_path": locator.extension.fields.get("relative_path") if locator else None,
        "reasons": list(operation.reasons),
        "candidates": list(operation.candidates),
    }


def _cmd_review(args: argparse.Namespace, service: AptuniService) -> int:
    operations = service.review_queue(args.source_id)
    values = [_review_json(operation) for operation in operations]
    if args.json:
        _print_json(values)
    elif not values:
        print("No source changes waiting for review.")
    else:
        for item in values:
            print(f"{item['kind']}  {item['relative_path']}  {', '.join(item['reasons'])}")
    return 0


def _cmd_doctor(args: argparse.Namespace, service: AptuniService) -> int:
    report = service.doctor()
    if report.ok:
        print(f"Vault healthy: commit {report.seq}, {report.records} records, all invariants hold.")
        return 0
    print("Vault problems found:")
    for problem in report.problems:
        print(f"  - {problem}")
    return 2


COMMANDS: dict[str, Callable[[argparse.Namespace, AptuniService], int]] = {
    "init": _cmd_init,
    "status": _cmd_status,
    "remember": _cmd_remember,
    "facts": _cmd_facts,
    "correct": _cmd_correct,
    "retract": _cmd_retract,
    "module": _cmd_module,
    "source": _cmd_source,
    "sync": _cmd_sync,
    "evidence": _cmd_evidence,
    "review": _cmd_review,
    "doctor": _cmd_doctor,
}


def run(argv: Sequence[str], service: AptuniService) -> int:
    args = build_parser().parse_args(argv)
    return COMMANDS[args.command](args, service)


def main(argv: Sequence[str] | None = None) -> int:
    service = AptuniService(Workspace.default())
    try:
        return run(sys.argv[1:] if argv is None else argv, service)
    except AptuniError as error:
        print(f"aptuni: {error.message}", file=sys.stderr)
        return 1
