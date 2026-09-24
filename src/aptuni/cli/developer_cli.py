"""Owner commands for public plugin inspection, scaffolding and least-privilege grants."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from aptuni.api.v1 import CAPABILITIES, load_manifest, scaffold_plugin
from aptuni.api.v1.grants import PluginGrantManager
from aptuni.application.service import AptuniService
from aptuni.domain.records import MODULES


def add_developer_commands(sub: Any) -> None:
    developer = sub.add_parser("developer", help="build and authorize local Aptuni API clients")
    actions = developer.add_subparsers(dest="developer_command", required=True, metavar="ACTION")
    inspect = actions.add_parser("inspect", help="validate one aptuni.plugin@1 manifest")
    inspect.add_argument("manifest", type=Path)
    inspect.add_argument("--json", action="store_true")
    scaffold = actions.add_parser("scaffold", help="create a public-API-only plugin starter")
    scaffold.add_argument("path", type=Path)
    scaffold.add_argument("--id", required=True, dest="plugin_id")
    scaffold.add_argument("--name", required=True)
    scaffold.add_argument("--json", action="store_true")
    grant = actions.add_parser("grant", help="plan or apply a local plugin grant")
    grants = grant.add_subparsers(dest="grant_command", required=True, metavar="ACTION")
    plan = grants.add_parser("plan", help="freeze a narrowed manifest-bound grant preview")
    plan.add_argument("manifest", type=Path)
    plan.add_argument("--capability", action="append", choices=CAPABILITIES, dest="capabilities")
    plan.add_argument("--module", action="append", choices=MODULES, dest="modules")
    plan.add_argument("--json", action="store_true")
    apply = grants.add_parser("apply", help="owner-confirm one exact plugin grant")
    apply.add_argument("action_id")
    apply.add_argument("--json", action="store_true")
    listing = grants.add_parser("list", help="list current local API grants")
    listing.add_argument("--json", action="store_true")
    cancel = grants.add_parser("cancel", help="discard one pending plugin grant preview")
    cancel.add_argument("action_id")
    cancel.add_argument("--json", action="store_true")
    revoke = grants.add_parser("revoke", help="revoke one current local API grant")
    revoke.add_argument("grant_id")
    revoke.add_argument("--json", action="store_true")


def cmd_developer(args: Any, service: AptuniService) -> int:
    value: object
    if args.developer_command == "scaffold":
        files = scaffold_plugin(args.path, plugin_id=args.plugin_id, name=args.name)
        value = {"contract": "aptuni.developer@1", "files": [str(path) for path in files]}
    elif args.developer_command == "inspect":
        value = load_manifest(args.manifest).model_dump(mode="json")
    else:
        manager = PluginGrantManager(service.workspace)
        if args.grant_command == "plan":
            manifest = load_manifest(args.manifest)
            plan = manager.plan(
                manifest,
                capabilities=tuple(args.capabilities) if args.capabilities else None,
                modules=tuple(args.modules) if args.modules else None,
            )
            value = plan.model_dump(mode="json") | {
                "preview": _preview(plan.plugin_id, plan.plugin_version, plan.capabilities, plan.modules),
            }
        elif args.grant_command == "apply":
            plan = manager.pending(args.action_id)
            preview = _preview(plan.plugin_id, plan.plugin_version, plan.capabilities, plan.modules)
            print(preview, file=sys.stderr if args.json else sys.stdout)
            if not _owner_confirms_apply(json_mode=args.json):
                print("Cancelled; no plugin grant was created.")
                return 1
            value = manager.apply(args.action_id).model_dump(mode="json")
        elif args.grant_command == "list":
            value = {
                "contract": "aptuni.developer@1",
                "grants": [grant.model_dump(mode="json") for grant in manager.list_grants()],
            }
        elif args.grant_command == "cancel":
            value = {"contract": "aptuni.developer@1", "cancelled": manager.cancel(args.action_id)}
        else:
            value = {"contract": "aptuni.developer@1", "revoked": manager.revoke(args.grant_id)}
    if getattr(args, "json", False):
        print(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


def _preview(plugin_id: str, version: str, capabilities: tuple[str, ...], modules: tuple[str, ...]) -> str:
    return (
        f"Plugin: {plugin_id} {version}\nCapabilities: {', '.join(capabilities)}\n"
        f"Modules: {', '.join(modules)}\nEgress: none\n"
        "Effect: create a private manifest-bound local grant; no plugin code is imported or run."
    )


def _owner_confirms_apply(*, json_mode: bool) -> bool:
    prompt = "Type APPLY to create this local plugin grant: "
    if json_mode:
        print(prompt, end="", file=sys.stderr, flush=True)
        return input() == "APPLY"
    return input(prompt) == "APPLY"
