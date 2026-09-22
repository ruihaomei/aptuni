"""Owner CLI for conservative Profile promotion and retrospective review (ADR-0020)."""

from __future__ import annotations

import json
from typing import Any


def add_profile_commands(sub: Any) -> None:
    profile = sub.add_parser("profile", help="promote and review stable Profile facts")
    actions = profile.add_subparsers(dest="profile_command", required=True, metavar="ACTION")
    refresh = actions.add_parser("refresh", help="promote eligible pinned memories")
    refresh.add_argument("--json", action="store_true")
    review = actions.add_parser("review", help="review automatically promoted Profile facts")
    review_actions = review.add_subparsers(dest="profile_review_command", required=True, metavar="ACTION")
    listing = review_actions.add_parser("list", help="list promoted facts awaiting review")
    listing.add_argument("--json", action="store_true")
    for name in ("accept", "reject"):
        parser = review_actions.add_parser(name, help=f"{name} one promoted Profile fact")
        parser.add_argument("fact_id")
        parser.add_argument("--json", action="store_true")


def _dump(value: object) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True))


def _item(fact: Any, state: str) -> dict[str, object]:
    return {
        "id": fact.id,
        "module": fact.module,
        "statement": fact.statement,
        "memory_ids": list(fact.memory_ids),
        "review_state": state,
    }


def cmd_profile(args: Any, service: Any) -> int:
    if args.profile_command == "refresh":
        promoted = service.refresh_profile()
        if args.json:
            _dump({"promoted": [fact.id for fact in promoted]})
        else:
            print(f"Promoted {len(promoted)} stable Profile fact(s).")
        return 0
    action = args.profile_review_command
    if action == "list":
        pending = service.profile_review_pending()
        if args.json:
            _dump([_item(fact, "auto_promoted_pending_review") for fact in pending])
        elif not pending:
            print("No automatically promoted Profile facts are waiting for review.")
        else:
            for fact in pending:
                print(f"{fact.id}  [{fact.module}]  {fact.statement}")
        return 0
    state = service.review_profile_fact(args.fact_id, action)
    if args.json:
        _dump({"fact_id": args.fact_id, "review_state": state})
    else:
        print(f"Profile fact {args.fact_id}: {state}.")
    return 0
