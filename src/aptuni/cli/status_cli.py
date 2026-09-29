"""``aptuni status`` in the owner's language (Beta Day 0, 2026-09-29).

The Agent guide starts with ``aptuni status``, so it accepts ``--lang`` and ``APTUNI_LANG`` like the
other owner commands. ``--json`` is a contract and stays unchanged in every language.
"""

from __future__ import annotations

import argparse
import json
import os
from typing import Any

from aptuni.application.service import AptuniService
from aptuni.i18n import normalize_locale, t

__all__ = ["add_status_command", "cmd_status"]


def add_status_command(sub: Any) -> None:
    status = sub.add_parser("status", help="show Vault location, size and module switches")
    status.add_argument("--json", action="store_true")
    status.add_argument("--lang", default=None, help="en or zh-CN")


def cmd_status(args: argparse.Namespace, service: AptuniService) -> int:
    status = service.status()
    reminder = service.review_reminder()
    if args.json:
        print(json.dumps({
            "vault": str(status.vault_path), "state_dir": str(status.state_dir), "seq": status.seq,
            "policy_epoch": status.policy_epoch, "counts": status.counts,
            "modules": {m: {"ingest": i, "expose": e} for m, (i, e) in status.modules.items()},
            "review": {"pending": reminder.pending, "due": reminder.due, "reason": reminder.reason},
        }, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    locale = normalize_locale(args.lang or os.environ.get("APTUNI_LANG"))
    counts = ", ".join(f"{k}={v}" for k, v in sorted(status.counts.items()))
    hidden = ", ".join(m for m, (_, expose) in status.modules.items() if not expose)
    print(t("status.vault", locale, path=status.vault_path, seq=status.seq, epoch=status.policy_epoch))
    print(t("status.records", locale, counts=counts or t("status.none", locale)))
    print(t("status.hidden", locale, modules=hidden or t("status.nothing", locale)))
    if reminder.due:
        print(t("status.review_due", locale, pending=reminder.pending))
    return 0
