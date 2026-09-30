"""``aptuni source authorize|reclassify SOURCE_ID``: owner decisions on classification (ADR-0028, 0029).

``authorize`` raises a source's ceiling; ``reclassify`` applies the current item classifier to
Evidence recorded by an older one. Each preview says how many current items change and how; only a
typed APPLY by the owner applies it. Anything else changes nothing.
"""

from __future__ import annotations

import argparse
import os
from typing import Any

from aptuni.cli.render import delimited_untrusted
from aptuni.domain.records import AUTHORITY_GRANTS
from aptuni.i18n import normalize_locale, t

__all__ = ["add_source_authority_parser", "cmd_source_authority", "cmd_source_reclassify"]


def add_source_authority_parser(source_sub: Any) -> None:
    authorize = source_sub.add_parser(
        "authorize", help="let an approved source count as evidence for one Profile dimension",
    )
    authorize.add_argument("source_id")
    authorize.add_argument("--grant", required=True, choices=sorted(set(AUTHORITY_GRANTS.values())),
                           metavar="DIMENSION")
    authorize.add_argument("--lang", default=None, help="en or zh-CN")
    reclassify = source_sub.add_parser(
        "reclassify", help="re-check each item of an approved source with the current classifier",
    )
    reclassify.add_argument("source_id")
    reclassify.add_argument("--lang", default=None, help="en or zh-CN")


def _confirmed(prompt: str) -> bool:
    try:
        return input(prompt).strip() == "APPLY"
    except (EOFError, KeyboardInterrupt):
        return False


def cmd_source_authority(args: argparse.Namespace, service: Any) -> int:
    locale = normalize_locale(args.lang or os.environ.get("APTUNI_LANG"))
    preview = service.source_authority_preview(args.source_id, args.grant)
    source = preview.source
    label = delimited_untrusted(source.roots[0] if source.roots else source.id)
    signal = args.grant.split(".", 1)[1]
    print(t("source.authorize.title", locale, source=label, source_id=source.id,
            what=t(f"source.authorize.what.{signal}", locale)))
    print(t("source.authorize.effect", locale, count=len(preview.evidence_ids),
            rule=t(f"source.authorize.rule.{signal}", locale)))
    print(t("source.authorize.review", locale))
    if not _confirmed(t("source.authorize.prompt", locale)):
        print(t("source.authorize.cancelled", locale))
        return 1
    result = service.grant_source_authority(source.id, args.grant, preview.digest)
    print(t("source.authorize.done", locale, source_id=source.id, evidence=result.evidence_written,
            profile=result.profile_written))
    return 0


def cmd_source_reclassify(args: argparse.Namespace, service: Any) -> int:
    locale = normalize_locale(args.lang or os.environ.get("APTUNI_LANG"))
    preview = service.source_reclassify_preview(args.source_id)
    source = preview.source
    label = delimited_untrusted(source.roots[0] if source.roots else source.id)
    print(t("source.reclassify.title", locale, source=label, source_id=source.id))
    if not preview.changes:
        print(t("source.reclassify.none", locale, source_id=source.id))
        return 0
    print(t("source.reclassify.effect", locale, count=len(preview.changes), down=preview.downgrades,
            up=preview.upgrades))
    print(t("source.authorize.review", locale))
    if not _confirmed(t("source.reclassify.prompt", locale)):
        print(t("source.reclassify.cancelled", locale))
        return 1
    result = service.reclassify_source(source.id, preview.digest)
    print(t("source.reclassify.done", locale, source_id=source.id, evidence=result.evidence_written,
            profile=result.profile_written))
    return 0
