"""`aptuni backup create | verify | list | restore` — the owner's restore path.

`restore` is the only destructive verb here, so it follows the project's confirmation discipline: the
full preview, then one terminal word bound to the preview digest. Every path the owner supplied is
rendered as bounded escaped data, so a crafted folder name cannot forge a line in that preview
(ADR-0013 item 2).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

from aptuni.application.restore import RestorePreview
from aptuni.cli.render import delimited_untrusted
from aptuni.i18n import normalize_locale, t

CONFIRM_WORD = "RESTORE"


def add_backup_commands(sub: Any) -> None:
    backup = sub.add_parser("backup", help="make and restore a verified copy of your Profile Vault")
    actions = backup.add_subparsers(dest="backup_command", required=True, metavar="ACTION")

    create = actions.add_parser("create", help="write a verified restorable backup")
    create.add_argument("path", help="an empty or new folder outside your Vault")

    verify = actions.add_parser("verify", help="check a backup without touching your Vault")
    verify.add_argument("path")

    listing = actions.add_parser("list", help="list the backups in a folder")
    listing.add_argument("path", nargs="?", default=".")

    # Restore replaces the canonical generation, so it uses the same preview/confirm/cancel shape as
    # `privacy purge`: the confirmation names one exact pending action rather than a path.
    restore = actions.add_parser("restore", help="preview, confirm or cancel a restore")
    restore_actions = restore.add_subparsers(dest="restore_command", required=True, metavar="ACTION")
    preview = restore_actions.add_parser("preview", help="show exactly what a restore would change")
    preview.add_argument("path")
    confirm = restore_actions.add_parser("confirm", help="apply one exact previewed restore")
    confirm.add_argument("action_id")
    confirm.add_argument("--confirm-digest", default=None,
                         help="exact digest from the preview, for scripted use")
    cancel = restore_actions.add_parser("cancel", help="drop a pending restore preview")
    cancel.add_argument("action_id")

    for parser in (create, verify, listing, preview, confirm, cancel):
        parser.add_argument("--lang", default=None, help="en or zh-CN")
        parser.add_argument("--json", action="store_true")


def _locale(args: argparse.Namespace) -> str:
    return normalize_locale(args.lang or os.environ.get("APTUNI_LANG"))


def _print_json(value: object) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=1, sort_keys=True))


def render_restore_preview(preview: RestorePreview, locale: str) -> list[str]:
    """The one surface the owner confirms. Outside-controlled values are escaped data, never lines."""
    return [
        t("backup.restore.title", locale), "",
        t("backup.restore.action", locale, action_id=preview.action_id),
        t("backup.restore.from", locale, path=delimited_untrusted(preview.backup_path),
          created=delimited_untrusted(preview.backup_created_at)),
        t("backup.restore.replace", locale, live_seq=preview.live_seq, backup_seq=preview.backup_seq),
        t("backup.restore.counts", locale, live=preview.live_record_count, backup=preview.backup_record_count),
        t("backup.restore.discarded", locale, count=preview.discarded_record_count),
        t("backup.restore.dropped", locale, count=preview.ledger_drop_count),
        t("backup.restore.new_ledger", locale, count=preview.new_ledger_digest_count),
        t("backup.restore.derived", locale), "",
        t("backup.restore.kept", locale),
        t("backup.restore.expires", locale, expires=preview.expires_at, digest=preview.digest),
        t("backup.restore.confirm_hint", locale, action_id=preview.action_id),
    ]


def _render_summary(summary: Any, locale: str) -> list[str]:
    lines = [t("backup.summary.path", locale, path=delimited_untrusted(summary.path))]
    if summary.ok:
        lines += [
            t("backup.summary.ok", locale, seq=summary.vault_seq, records=summary.record_count,
              segments=summary.segment_count, created=delimited_untrusted(summary.created_at)),
            t("backup.summary.deletions", locale, count=summary.deletion_digest_count),
        ]
    else:
        lines.append(t("backup.summary.bad", locale))
        lines += [f"  - {delimited_untrusted(problem)}" for problem in summary.problems]
    return lines


def _create(args: argparse.Namespace, service: Any, locale: str) -> int:
    summary = service.create_backup(Path(args.path))
    if args.json:
        _print_json(summary.to_dict())
        return 0
    print("\n".join(_render_summary(summary, locale)))
    print(t("backup.create.done", locale))
    print(t("backup.create.unencrypted", locale))
    print(t("backup.create.not_export", locale))
    return 0


def _verify(args: argparse.Namespace, service: Any, locale: str) -> int:
    summary = service.verify_backup(Path(args.path))
    if args.json:
        _print_json(summary.to_dict())
    else:
        print("\n".join(_render_summary(summary, locale)))
    return 0 if summary.ok else 1


def _list(args: argparse.Namespace, service: Any, locale: str) -> int:
    summaries = service.list_backups(Path(args.path))
    if args.json:
        _print_json([item.to_dict() for item in summaries])
        return 0
    if not summaries:
        print(t("backup.list.none", locale, path=delimited_untrusted(str(Path(args.path)))))
        return 0
    for summary in summaries:
        print("\n".join(_render_summary(summary, locale)))
    return 0 if all(summary.ok for summary in summaries) else 1


def _restore_preview(args: argparse.Namespace, service: Any, locale: str) -> int:
    preview = service.restore_preview(Path(args.path))
    if args.json:
        _print_json(preview.to_dict())
        return 0
    print("\n".join(render_restore_preview(preview, locale)))
    return 0


def _restore_confirm(args: argparse.Namespace, service: Any, locale: str) -> int:
    if args.confirm_digest is None:
        # Interactive: replay the exact preview, then ask in the terminal. Never confirm a plan the
        # owner has not seen in this invocation.
        preview = service.pending_restore(args.action_id)
        print("\n".join(render_restore_preview(preview, locale)))
        if not sys.stdin.isatty():
            print(t("backup.restore.needs_terminal", locale, action_id=preview.action_id))
            return 1
        if input(t("backup.restore.prompt", locale, word=CONFIRM_WORD)).strip() != CONFIRM_WORD:
            print(t("backup.restore.cancelled", locale))
            return 1
        digest = preview.digest
    else:
        digest = args.confirm_digest

    receipt = service.confirm_restore(args.action_id, digest)
    if args.json:
        _print_json(receipt.to_dict())
        return 0
    print(t("backup.restore.done", locale, seq=receipt.published_seq,
            records=receipt.restored_record_count))
    if receipt.discarded_record_count:
        print(t("backup.restore.done_discarded", locale, count=receipt.discarded_record_count))
    if receipt.ledger_dropped_count:
        print(t("backup.restore.done_dropped", locale, count=receipt.ledger_dropped_count))
    print(t("backup.restore.done_derived", locale))
    return 0


def _restore_cancel(args: argparse.Namespace, service: Any, locale: str) -> int:
    service.cancel_restore(args.action_id)
    print(t("backup.restore.cancelled_action", locale, action_id=args.action_id))
    return 0


def _restore(args: argparse.Namespace, service: Any, locale: str) -> int:
    handlers = {"preview": _restore_preview, "confirm": _restore_confirm, "cancel": _restore_cancel}
    return handlers[args.restore_command](args, service, locale)


def cmd_backup(args: argparse.Namespace, service: Any) -> int:
    locale = _locale(args)
    handlers = {"create": _create, "verify": _verify, "list": _list, "restore": _restore}
    return handlers[args.backup_command](args, service, locale)
