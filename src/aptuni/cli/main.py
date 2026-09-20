"""``aptuni`` command line: the owner's terminal interface to their Vault."""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

from aptuni import __version__
from aptuni.adapters.manager import AdapterManager
from aptuni.application.errors import AptuniError
from aptuni.application.service import AptuniService, Status
from aptuni.application.workspace import DEFAULT_VAULT, Workspace
from aptuni.cli.marginnote_commands import MARGINNOTE_COMMANDS, add_marginnote_parsers, cmd_marginnote
from aptuni.cli.memory_cli import add_memory_commands, cmd_memory, cmd_observe
from aptuni.cli.render import delimited_untrusted
from aptuni.cli.setup_commands import (
    add_guided_setup_command,
    add_setup_commands,
    cmd_advise,
    cmd_plugin,
    cmd_recipe,
    cmd_setup,
)
from aptuni.domain.invariants import InvariantError
from aptuni.domain.records import MODULES, SchemaVersionError
from aptuni.vault.store import VaultIntegrityError

UNSAFE_STATE_ERRORS = (VaultIntegrityError, InvariantError, SchemaVersionError, OSError, ValueError, TypeError,
                       KeyError, AttributeError)


def _on_off(value: str) -> bool:
    if value not in ("on", "off"):
        raise argparse.ArgumentTypeError("use 'on' or 'off'")
    return value == "on"


def _add_source_commands(sub: Any) -> None:
    source = sub.add_parser("source", help="approve and inspect personal data sources")
    source_sub = source.add_subparsers(dest="source_command", required=True, metavar="ACTION")
    source_add = source_sub.add_parser("add-folder", help="approve a local folder as a source")
    source_add.add_argument("path", type=Path)
    source_add.add_argument("--module", action="append", required=True, choices=MODULES, dest="modules")
    source_add.add_argument("--role", required=True, help="what this folder means (for example: portfolio)")
    source_add.add_argument("--primary-for", action="append", default=[], metavar="DIMENSION")
    source_add.add_argument("--json", action="store_true")
    github_add = source_sub.add_parser("add-github", help="approve one GitHub repository as a source")
    github_add.add_argument("repository_url", help="exact https repository URL")
    github_add.add_argument("--module", action="append", required=True, choices=MODULES, dest="modules")
    github_add.add_argument("--role", required=True, help="what this repository means")
    github_add.add_argument("--ref", help="branch, tag, or commit to follow (default: repository default branch)")
    github_add.add_argument("--token-env", metavar="NAME", help="environment variable holding a least-scope token")
    github_add.add_argument("--api-origin", default="https://api.github.com",
                            help="GitHub API origin (GitHub Enterprise must use same-host /api/v3)")
    github_add.add_argument("--primary-for", action="append", default=[], metavar="DIMENSION")
    github_add.add_argument("--json", action="store_true")
    add_marginnote_parsers(source_sub)
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


def _add_retrieval_commands(sub: Any) -> None:
    search = sub.add_parser("search", help="search current permitted personal context")
    search.add_argument("query")
    search.add_argument("--module", choices=MODULES)
    search.add_argument("--limit", type=int, default=5)
    search.add_argument("--json", action="store_true")

    index = sub.add_parser("index", help="inspect or rebuild the disposable search index")
    index_sub = index.add_subparsers(dest="index_command", required=True, metavar="ACTION")
    index_status = index_sub.add_parser("status", help="show projection freshness, rows and size")
    index_status.add_argument("--json", action="store_true")
    index_rebuild = index_sub.add_parser("rebuild", help="rebuild from current permitted Vault records")
    index_rebuild.add_argument("--json", action="store_true")
    index_sub.add_parser("delete", help="delete the derived index (the Vault is unchanged)")


def _add_context_commands(sub: Any) -> None:
    identity = sub.add_parser("identity", help="return a bounded L0 identity card")
    identity.add_argument("--budget", type=int, default=512, metavar="UNITS")
    identity.add_argument("--json", action="store_true")

    context = sub.add_parser("context", help="return bounded, layered personal context for a task")
    context.add_argument("query")
    context.add_argument("--module", action="append", choices=MODULES, dest="modules")
    context.add_argument("--budget", type=int, default=1500, metavar="UNITS")
    context.add_argument("--limit", type=int, default=20)
    context.add_argument("--evidence", action="store_true", help="allow minimized L4 Evidence")
    context.add_argument("--json", action="store_true")


def _add_adapter_commands(sub: Any) -> None:
    adapter = sub.add_parser("adapter", help="prepare bounded Claude Code or Codex integration")
    adapter_sub = adapter.add_subparsers(dest="adapter_command", required=True, metavar="ACTION")
    plan = adapter_sub.add_parser("plan", help="preview a host adapter and informed egress grant")
    plan.add_argument("host", choices=("claude", "codex"))
    plan.add_argument("--module", action="append", required=True, choices=MODULES, dest="modules")
    plan.add_argument("--allow-host-model-egress", action="store_true")
    plan.add_argument("--allow-memory-proposals", action="store_true",
                      help="let the agent propose memories that you review with 'aptuni memory'")
    plan.add_argument("--json", action="store_true")
    apply = adapter_sub.add_parser("apply", help="terminal-confirm one exact pending adapter plan")
    apply.add_argument("action_id")
    apply.add_argument("--json", action="store_true")
    l0 = adapter_sub.add_parser("l0", help=argparse.SUPPRESS)
    l0.add_argument("--grant", required=True, dest="grant_id")
    l0.add_argument("--budget", type=int, default=512)


def _add_privacy_commands(sub: Any) -> None:
    privacy = sub.add_parser("privacy", help="inspect where personal data copies may exist")
    privacy_sub = privacy.add_subparsers(dest="privacy_command", required=True, metavar="ACTION")
    privacy_status = privacy_sub.add_parser("status", help="list managed and external copy locations")
    privacy_status.add_argument("--json", action="store_true")
    privacy_purge = privacy_sub.add_parser("purge", help="preview or confirm irreversible privacy deletion")
    purge_sub = privacy_purge.add_subparsers(dest="purge_command", required=True, metavar="ACTION")
    purge_preview = purge_sub.add_parser("preview", help="create an exact purge preview")
    purge_preview.add_argument("record_ids", nargs="+")
    purge_preview.add_argument("--json", action="store_true")
    purge_confirm = purge_sub.add_parser("confirm", help="confirm one exact core-generated purge action")
    purge_confirm.add_argument("action_id")
    purge_confirm.add_argument("--confirm-digest", help="exact digest from the preview, for scripted use")
    purge_confirm.add_argument("--json", action="store_true")
    purge_cancel = purge_sub.add_parser("cancel", help="abandon a confirmed purge that deleted nothing canonical")
    purge_cancel.add_argument("action_id")


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

    _add_source_commands(sub)
    _add_retrieval_commands(sub)
    _add_context_commands(sub)
    _add_adapter_commands(sub)
    add_setup_commands(sub)
    add_guided_setup_command(sub)
    add_memory_commands(sub)

    export = sub.add_parser("export", help="write a private, readable copy of your current Profile")
    export.add_argument("path", type=Path)
    export.add_argument("--json", action="store_true")

    _add_privacy_commands(sub)

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
    if args.source_command == "add-github":
        source = service.add_github_source(
            args.repository_url,
            modules=tuple(args.modules),
            role=args.role,
            ref=args.ref,
            token_env=args.token_env,
            api_origin=args.api_origin,
            primary_for=tuple(args.primary_for),
        )
        if args.json:
            _print_json(_source_json(source))
        else:
            print(f"Approved GitHub source {source.id}: {source.roots[0]}")
        return 0
    if args.source_command in MARGINNOTE_COMMANDS:
        return cmd_marginnote(args, service, _source_json)
    sources = service.sources()
    if args.json:
        _print_json([_source_json(source) for source in sources])
    elif not sources:
        print("No sources yet. Add one with aptuni source add-folder or aptuni source add-github.")
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


def _open_url(locator: Any) -> str | None:
    """Deep link back to the source card, derived (never stored) from the native note ID."""
    if locator.provider == "marginnote" and locator.extension.version == 2:
        return f"marginnote4app://note/{locator.extension.fields['note_id']}"
    return None


def _cmd_evidence(args: argparse.Namespace, service: AptuniService) -> int:
    evidence = service.evidence(args.source_id)
    values = [
        {
            "id": item.id,
            "source_id": item.provenance.source_id,
            "module": item.module,
            "relative_path": item.provenance.locator.extension.fields.get(
                "relative_path", item.provenance.locator.extension.fields.get("path")
            ),
            "subject": item.subject,
            "open_url": _open_url(item.provenance.locator),
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
            where = item["relative_path"] or item["subject"]
            print(f"{item['id']}  [{item['module']}]  {where}  {', '.join(item['signals'])}")
    return 0


def _review_json(operation: Any) -> dict[str, Any]:
    locator = operation.after or operation.before
    return {
        "kind": operation.kind,
        "subject_id": operation.subject_id,
        "relative_path": locator.extension.fields.get(
            "relative_path", locator.extension.fields.get("path")
        ) if locator else None,
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


def _cmd_search(args: argparse.Namespace, service: AptuniService) -> int:
    hits = service.search(args.query, module=args.module, limit=args.limit)
    values = [
        {
            "id": hit.id,
            "record_type": hit.record_type,
            "module": hit.module,
            "text": hit.text,
            "score": hit.score,
            "source_id": hit.source_id,
        }
        for hit in hits
    ]
    if args.json:
        _print_json(values)
    elif not hits:
        print("No permitted current context matched.")
    else:
        for hit in hits:
            print(f"{hit.id}  [{hit.module}/{hit.record_type}]  {hit.text}")
    return 0


def _index_json(status: Any) -> dict[str, Any]:
    return {
        "path": str(status.path),
        "state": status.state,
        "vault_seq": status.vault_seq,
        "records": status.records,
        "bytes": status.bytes,
        "schema_version": status.schema_version,
        "lexeme_version": status.lexeme_version,
    }


def _cmd_index(args: argparse.Namespace, service: AptuniService) -> int:
    if args.index_command == "delete":
        service.delete_index()
        print("Deleted the derived search index; canonical Vault records were not changed.")
        return 0
    status = service.rebuild_index() if args.index_command == "rebuild" else service.index_status()
    if args.json:
        _print_json(_index_json(status))
    else:
        print(f"Index: {status.state}  records={status.records}  bytes={status.bytes}  path={status.path}")
    return 0


def _context_json(response: Any) -> dict[str, Any]:
    return {
        "audience": response.audience,
        "requested_units": response.requested_units,
        "used_units": response.used_units,
        "remaining_units": response.remaining_units,
        "truncated": response.truncated,
        "layers": list(response.layers),
        "vault_seq": response.vault_seq,
        "policy_epoch": response.policy_epoch,
        "items": [item.payload() | {"units": item.units} for item in response.items],
    }


def _print_context(response: Any) -> None:
    if not response.items:
        print("No permitted context fit the requested budget.")
    else:
        for item in response.items:
            label = item.canonical_id or item.kind
            print(f"{item.layer}  {label}  {item.text}")
    marker = " truncated" if response.truncated else ""
    print(f"Budget: {response.used_units}/{response.requested_units} units; "
          f"remaining={response.remaining_units}{marker}")


def _cmd_identity(args: argparse.Namespace, service: AptuniService) -> int:
    response = service.identity_card(budget=args.budget)
    if args.json:
        _print_json(_context_json(response))
    else:
        _print_context(response)
    return 0


def _cmd_context(args: argparse.Namespace, service: AptuniService) -> int:
    response = service.context(
        args.query,
        modules=tuple(args.modules or ()),
        budget=args.budget,
        include_evidence=args.evidence,
        limit=args.limit,
    )
    if args.json:
        _print_json(_context_json(response))
    else:
        _print_context(response)
    return 0


def _cmd_adapter(args: argparse.Namespace, service: AptuniService) -> int:
    manager = AdapterManager(service.workspace)
    if args.adapter_command == "plan":
        plan = manager.plan(
            args.host,
            tuple(args.modules),
            allow_host_model_egress=args.allow_host_model_egress,
            allow_memory_proposals=args.allow_memory_proposals,
        )
        if args.json:
            _print_json({
                "action_id": plan.action_id,
                "digest": plan.digest,
                "host": plan.host,
                "modules": list(plan.modules),
                "scopes": list(plan.scopes),
                "preview": manager.preview(plan),
            })
        else:
            print(manager.preview(plan))
            print(f"Pending action: {plan.action_id}")
            print(f"Apply from your terminal with: aptuni adapter apply {plan.action_id}")
        return 0
    if args.adapter_command == "apply":
        plan = manager.pending(args.action_id)
        print(manager.preview(plan))
        if input("Type APPLY to create this grant and bundle: ") != "APPLY":
            print("Cancelled; no grant or bundle was created.")
            return 1
        grant, bundle = manager.apply(args.action_id)
        if args.json:
            _print_json({"grant_id": grant.grant_id, "host": grant.host, "bundle": str(bundle)})
        else:
            print(f"Prepared {grant.host} adapter bundle at {bundle}")
            print("Review and install the generated host configuration, then start a new host session.")
        return 0
    grant = manager.load_grant(args.grant_id)
    response = service.identity_card(
        budget=args.budget,
        audience="host_mcp",
        access=grant.access(),
    )
    for item in response.items:
        print(item.text)
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


def _cmd_export(args: argparse.Namespace, service: AptuniService) -> int:
    report = service.export(args.path)
    value = {
        "path": str(report.path),
        "files": report.files,
        "facts": report.facts,
        "memories": report.memories,
        "evidence": report.evidence,
        "omitted_full_content": report.omitted_full_content,
    }
    if args.json:
        _print_json(value)
    else:
        print(f"Exported current Profile to {report.path}: facts={report.facts}, memories={report.memories}, "
              f"evidence={report.evidence}.")
        if report.omitted_full_content:
            print(f"Omitted {report.omitted_full_content} full-content source record(s) for privacy.")
        print("This copy is not tracked by Aptuni and is not a restorable Vault backup.")
    return 0


def _cmd_privacy(args: argparse.Namespace, service: AptuniService) -> int:
    if args.privacy_command == "purge":
        return _cmd_privacy_purge(args, service)
    inventory = service.privacy_inventory()
    if args.json:
        _print_json(inventory.to_dict())
        return 0
    print(f"Privacy inventory at Vault commit {inventory.vault_seq}")
    print(f"{'copy':<34} {'control':<31} location")
    for inventory_item in inventory.copies:
        present = "unknown" if inventory_item.present is None else (
            str(inventory_item.bytes) + " B" if inventory_item.present else "absent"
        )
        # Source roots and host destinations are user/provider controlled; never print them raw.
        location = inventory_item.location if inventory_item.managed else delimited_untrusted(
            inventory_item.location)
        print(f"{inventory_item.id:<34} {inventory_item.deletion_control:<31} {location} ({present})")
    print("Exports and host/provider transcripts are not tracked copies; Aptuni cannot delete them for you.")
    return 0


def _cmd_privacy_purge(args: argparse.Namespace, service: AptuniService) -> int:
    if args.purge_command == "cancel":
        service.cancel_privacy_purge(args.action_id)
        print(f"Cancelled purge {args.action_id}. No canonical record was deleted by it; derived copies "
              "it had already removed stay removed. Preview again to delete anything.")
        return 0
    if args.purge_command == "preview":
        preview = service.privacy_purge_preview(tuple(args.record_ids))
        if args.json:
            _print_json(preview.to_dict())
        else:
            _print_purge_preview(preview)
            print(f"Confirm only after review: aptuni privacy purge confirm {preview.action_id}")
        return 0
    if args.confirm_digest is None:
        preview = service.pending_privacy_purge(args.action_id)
        _print_purge_preview(preview)
        if input("Type PURGE to irreversibly delete these managed copies: ").strip() != "PURGE":
            print("Cancelled. Nothing was changed.")
            return 1
        digest = preview.digest
    else:
        digest = args.confirm_digest
    receipt = service.confirm_privacy_purge(args.action_id, digest)
    if args.json:
        _print_json(receipt.model_dump(mode="json"))
    else:
        print(f"Purge {receipt.purge_id}: {receipt.terminal_state}")
        for receipt_item in receipt.per_copy:
            print(f"  {receipt_item.copy_class}: {receipt_item.result}")
            if receipt_item.provider is not None:
                print(f"    provider={receipt_item.provider} data_class={receipt_item.data_class} "
                      f"destination={delimited_untrusted(receipt_item.destination or 'unknown')}")
    return 2 if receipt.terminal_state == "incomplete_retryable" else 0


def _print_purge_preview(preview: Any) -> None:
    print(f"Purge action: {preview.action_id}\nVault commit: {preview.vault_seq}\n"
          f"Policy epoch: {preview.policy_epoch}\nRequested records: {len(preview.requested_record_ids)}\n"
          f"Records after non-resurrection expansion: {len(preview.record_ids)}")
    for record_id in preview.record_ids:
        print(f"  {record_id}")
    print("Effects:")
    for effect in preview.copy_effects:
        print(f"  - {effect}")
    print(f"Managed copies in this exact action: {len(preview.managed_copy_ids)}")
    for copy_id in preview.managed_copy_ids:
        print(f"  {copy_id}")
    print(f"External copies requiring user action: {len(preview.external_copies)}")
    for external in preview.external_copies:
        print(f"  {external['copy_id']}  provider={external['provider']}  data_class={external['data_class']}  "
              f"destination={delimited_untrusted(external['destination'])}")
    print(f"Nonce: {preview.nonce_id}\nExpires: {preview.expires_at}\nDigest: {preview.digest}")


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
    "search": _cmd_search,
    "index": _cmd_index,
    "identity": _cmd_identity,
    "context": _cmd_context,
    "adapter": _cmd_adapter,
    "doctor": _cmd_doctor,
    "plugin": cmd_plugin,
    "recipe": cmd_recipe,
    "advise": cmd_advise,
    "setup": cmd_setup,
    "observe": cmd_observe,
    "memory": cmd_memory,
    "export": _cmd_export,
    "privacy": _cmd_privacy,
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
    except BrokenPipeError:
        # The reader (for example ``| head``) closed the pipe; this is not a Vault problem.
        os.dup2(os.open(os.devnull, os.O_WRONLY), sys.stdout.fileno())
        return 1
    except UNSAFE_STATE_ERRORS as error:
        # Last-line boundary (review 19 N2): never print a traceback or the exception text, which can
        # echo Vault content. APTUNI_DEBUG=1 re-raises for development.
        if os.environ.get("APTUNI_DEBUG") == "1":
            raise
        print(f"aptuni: the Vault, its state or its configuration could not be read safely "
              f"({type(error).__name__}). Nothing was changed; run 'aptuni doctor' for details.", file=sys.stderr)
        return 1
