"""``aptuni source authorize SOURCE_ID --grant DIMENSION``: upgrade an approved source (ADR-0028).

The preview says how many current items change and that each forms an active Profile fact; only a
typed APPLY by the owner applies it. Anything else leaves the source reference-only.
"""

from __future__ import annotations

import argparse
import os
from typing import Any

from aptuni.cli.render import delimited_untrusted
from aptuni.domain.records import AUTHORITY_GRANTS
from aptuni.i18n import normalize_locale, t

__all__ = ["add_source_authority_parser", "cmd_source_authority"]


def add_source_authority_parser(source_sub: Any) -> None:
    authorize = source_sub.add_parser(
        "authorize", help="let an approved source count as evidence for one Profile dimension",
    )
    authorize.add_argument("source_id")
    authorize.add_argument("--grant", required=True, choices=sorted(set(AUTHORITY_GRANTS.values())),
                           metavar="DIMENSION")
    authorize.add_argument("--lang", default=None, help="en or zh-CN")


def cmd_source_authority(args: argparse.Namespace, service: Any) -> int:
    locale = normalize_locale(args.lang or os.environ.get("APTUNI_LANG"))
    preview = service.source_authority_preview(args.source_id, args.grant)
    source = preview.source
    label = delimited_untrusted(source.roots[0] if source.roots else source.id)
    print(t("source.authorize.title", locale, source=label, source_id=source.id))
    print(t("source.authorize.effect", locale, count=len(preview.evidence_ids)))
    print(t("source.authorize.review", locale))
    try:
        typed = input(t("source.authorize.prompt", locale)).strip()
    except (EOFError, KeyboardInterrupt):
        typed = ""
    if typed != "APPLY":
        print(t("source.authorize.cancelled", locale))
        return 1
    result = service.grant_source_authority(source.id, args.grant, preview.digest)
    print(t("source.authorize.done", locale, source_id=source.id, evidence=result.evidence_written,
            profile=result.profile_written))
    return 0
