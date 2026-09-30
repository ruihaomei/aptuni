"""``aptuni knowledge [QUERY]``: the owner's view of the derived Knowledge State (ADR-0029 item 8)."""

from __future__ import annotations

import argparse
import json
import os
from typing import Any

from aptuni.cli.render import delimited_untrusted
from aptuni.domain.records import MODULES
from aptuni.i18n import normalize_locale, t

__all__ = ["add_knowledge_command", "cmd_knowledge"]


def add_knowledge_command(sub: Any) -> None:
    knowledge = sub.add_parser(
        "knowledge", help="show what your Evidence says per concept (derived; not a proficiency score)",
    )
    knowledge.add_argument("query", nargs="?", default=None, help="a topic; omit to list the strongest concepts")
    knowledge.add_argument("--module", action="append", default=[], choices=MODULES, dest="modules")
    knowledge.add_argument("--limit", type=int, default=20)
    knowledge.add_argument("--json", action="store_true")
    knowledge.add_argument("--lang", default=None, help="en or zh-CN")


def cmd_knowledge(args: argparse.Namespace, service: Any) -> int:
    states = service.knowledge_states(args.query, modules=tuple(args.modules), limit=max(1, min(args.limit, 100)))
    if args.json:
        print(json.dumps({"states": [state.payload() for state in states]}, ensure_ascii=False, indent=2,
                         sort_keys=True))
        return 0
    locale = normalize_locale(args.lang or os.environ.get("APTUNI_LANG"))
    if not states:
        print(t("knowledge.empty", locale))
        return 0
    print(t("knowledge.header", locale))
    for state in states:
        print(t("knowledge.row", locale, level=t(f"knowledge.level.{state.level}", locale),
                label=delimited_untrusted(state.label), studied=state.counts["studied"],
                applied=state.counts["applied"], applied_sources=state.contexts["applied"],
                demonstrated=state.counts["demonstrated"], exposure=state.counts["exposure"],
                declared=state.declared, concept_id=delimited_untrusted(state.concept_id)))
    return 0
