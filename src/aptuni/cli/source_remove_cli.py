"""``aptuni source remove SOURCE_ID``: stop using an approved source (ADR-0027).

The preview names the source and how much it contributed; only a typed APPLY by the owner applies
it. History is kept, and the purge command that deletes it for good is named on the same screen.
"""

from __future__ import annotations

import argparse
import os
from typing import Any

from aptuni.cli.render import delimited_untrusted
from aptuni.i18n import normalize_locale, t

__all__ = ["add_source_remove_parser", "cmd_source_remove"]


def add_source_remove_parser(source_sub: Any) -> None:
    remove = source_sub.add_parser("remove", help="stop using an approved source and withdraw its evidence")
    remove.add_argument("source_id")
    remove.add_argument("--lang", default=None, help="en or zh-CN")


def cmd_source_remove(args: argparse.Namespace, service: Any) -> int:
    locale = normalize_locale(args.lang or os.environ.get("APTUNI_LANG"))
    preview = service.source_removal_preview(args.source_id)
    source = preview.source
    label = delimited_untrusted(source.roots[0] if source.roots else source.id)
    count = len(preview.evidence_ids)
    print(t("source.remove.title", locale, source=label, source_id=source.id))
    effect = "source.remove.repair" if preview.repair else "source.remove.effect"
    print(t(effect, locale, count=count, source_id=source.id))
    print(t("source.remove.again", locale))
    try:
        typed = input(t("source.remove.prompt", locale)).strip()
    except (EOFError, KeyboardInterrupt):
        typed = ""
    if typed != "APPLY":
        print(t("source.remove.cancelled", locale))
        return 1
    removed = service.remove_source(source.id, preview.digest)
    print(t("source.remove.done", locale, source_id=source.id, count=removed))
    return 0
