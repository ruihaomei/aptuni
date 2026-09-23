"""CLI bridge and installer for the separate Obsidian owner interface."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from aptuni.cli.render import delimited_untrusted


def add_interface_commands(sub: Any) -> None:
    interface = sub.add_parser("interface", help="install and serve local human interfaces")
    interfaces = interface.add_subparsers(dest="interface_kind", required=True, metavar="INTERFACE")
    obsidian = interfaces.add_parser("obsidian", help="Obsidian owner review interface")
    actions = obsidian.add_subparsers(dest="obsidian_command", required=True, metavar="ACTION")

    snapshot = actions.add_parser("snapshot", help="read the bounded owner dashboard")
    snapshot.add_argument("--json", action="store_true")
    evidence = actions.add_parser("evidence", help="show canonical support for a record")
    evidence.add_argument("record_id")
    evidence.add_argument("--json", action="store_true")
    action = actions.add_parser("action", help="apply an existing owner review action")
    action.add_argument("record_id")
    action.add_argument("action", choices=("accept", "edit", "reject", "pin", "forget"))
    action.add_argument("--statement")
    action.add_argument("--confirm-digest")
    action.add_argument("--json", action="store_true")
    install = actions.add_parser("install", help="copy the bundled plugin into an Obsidian vault")
    install.add_argument("vault", type=Path)
    install.add_argument("--json", action="store_true")


def cmd_interface(args: Any, service: Any) -> int:
    if args.interface_kind != "obsidian":
        raise AssertionError("unknown interface")
    action = args.obsidian_command
    if action == "snapshot":
        value = service.obsidian_snapshot()
    elif action == "evidence":
        value = service.obsidian_evidence(args.record_id)
    elif action == "action":
        value = service.obsidian_action(
            args.record_id, args.action, statement=args.statement, confirmed_digest=args.confirm_digest,
        )
    else:
        target = service.install_obsidian_interface(args.vault)
        value = {"contract": "aptuni.obsidian@1", "plugin_dir": str(target), "enabled": False}
    if args.json:
        print(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        _print_human(action, value)
    return 0


def _print_human(action: str, value: dict[str, Any]) -> None:
    if action == "snapshot":
        print(f"Aptuni Obsidian view at Vault commit {value['vault_seq']}")
        for key in ("profile", "memories", "evidence", "recent_changes", "pending_reviews"):
            print(f"  {key}: {len(value[key])}")
    elif action == "evidence":
        print(f"Evidence for {value['record_id']}")
        for item in value["supports"]:
            print(f"  {item['id']} [{item['kind']}] {delimited_untrusted(item['text'])}")
    elif action == "install":
        print(f"Installed disabled Aptuni plugin at {delimited_untrusted(value['plugin_dir'])}")
    elif value.get("confirmation_required"):
        print(f"Forget preview for {value['record_id']}: {delimited_untrusted(value['statement'])}")
        print(f"Confirm with digest {value['digest']}")
    else:
        print(f"{value['action']} {value['record_id']}: {value['review_state']}")
