"""``aptuni observe``, ``aptuni memory …`` and ``aptuni review …`` (ADR-0011, ADR-0013, ADR-0018).

Two paths live here and they are deliberately different. A candidate the policy will not promote
still needs the full preview and a typed confirmation before it becomes a memory. A candidate the
policy *does* promote is already active, so its review happens afterwards: `aptuni review` lists
what was promoted and settles it with accept / edit / reject / pin, none of which is a
confirmation ceremony because none of them is the irreversible direction.
"""

from __future__ import annotations

import argparse
import json
from typing import Any

from aptuni.application.errors import AptuniError
from aptuni.domain.records import MODULES
from aptuni.policy.promotion import review_state_of


def add_memory_commands(sub: Any) -> None:
    observe = sub.add_parser(
        "observe", help="note something about yourself (used right away; review it later)")
    observe.add_argument("statement")
    observe.add_argument("--module", required=True, choices=MODULES)
    observe.add_argument("--json", action="store_true")
    memory = sub.add_parser("memory", help="review, list or forget interaction memories")
    memory_sub = memory.add_subparsers(dest="memory_command", required=True, metavar="ACTION")
    for name, text in (("pending", "list proposals waiting for your review"), ("list", "list accepted memories")):
        parser = memory_sub.add_parser(name, help=text)
        parser.add_argument("--json", action="store_true")
    for name in ("accept", "reject"):
        parser = memory_sub.add_parser(name, help=f"{name} one proposal after reviewing its preview")
        parser.add_argument("candidate_id")
        parser.add_argument("--confirm-digest", help="exact digest from the preview, for scripted review")
    forget = memory_sub.add_parser("forget", help="stop using a memory (history is kept; not a deletion)")
    forget.add_argument("memory_id")
    forget.add_argument("--confirm-digest", help="exact digest from the preview, for scripted review")
    _add_review_commands(memory_sub)
    provider = memory_sub.add_parser("provider", help="inspect or manage the optional Mem0 projection")
    provider_sub = provider.add_subparsers(dest="provider_command", required=True, metavar="ACTION")
    for name, text in (
        ("status", "show content-free Mem0 projection health and capabilities"),
        ("rebuild", "rebuild Mem0 from current accepted canonical memories"),
        ("delete", "delete the entire derived Mem0 projection"),
    ):
        parser = provider_sub.add_parser(name, help=text)
        parser.add_argument("--json", action="store_true")


def _add_review_commands(memory_sub: Any) -> None:
    review = memory_sub.add_parser("review", help="review what Aptuni learned on its own")
    review_sub = review.add_subparsers(dest="review_command", required=True, metavar="ACTION")
    listing = review_sub.add_parser("list", help="list memories promoted by policy, awaiting your review")
    listing.add_argument("--json", action="store_true")
    for name, text in (
        ("accept", "keep this memory as it is"),
        ("reject", "stop using this memory (its history is kept)"),
        ("pin", "keep this memory and leave it out of future reminders"),
    ):
        parser = review_sub.add_parser(name, help=text)
        parser.add_argument("memory_id")
        parser.add_argument("--json", action="store_true")
    edit = review_sub.add_parser("edit", help="correct this memory; the original stays in history")
    edit.add_argument("memory_id")
    edit.add_argument("statement")
    edit.add_argument("--json", action="store_true")
    reminders = review_sub.add_parser("reminders", help="show whether the review queue is worth a look")
    reminders.add_argument("--json", action="store_true")
    snooze = review_sub.add_parser("snooze", help="defer the review reminder")
    snooze.add_argument("--clear", action="store_true", help="undo a snooze and remind me again")
    snooze.add_argument("--json", action="store_true")
    policy = review_sub.add_parser("policy", help="show or change how eagerly Aptuni promotes")
    policy.add_argument("--auto-promotion", choices=("on", "off"))
    policy.add_argument("--host-proposals", choices=("on", "off"),
                        help="on: save Agent proposals without asking (still reviewable; sensitive modules ask)")
    policy.add_argument("--pending-threshold", type=int)
    policy.add_argument("--interval-days", type=int)
    policy.add_argument("--snooze-days", type=int)
    policy.add_argument("--json", action="store_true")


def _cmd_snooze(args: argparse.Namespace, service: Any) -> int:
    if args.clear:
        cleared = service.clear_review_snooze()
        if args.json:
            _dump({"snoozed_until": None, "cleared": cleared})
        else:
            print("Snooze cleared." if cleared else "There was no snooze to clear.")
        return 0
    until = service.snooze_review()
    if args.json:
        _dump({"snoozed_until": until.isoformat()})
    else:
        print(f"Snoozed. Aptuni will not mention the review queue again before {until.date()}.")
    return 0


def _cmd_edit(args: argparse.Namespace, service: Any) -> int:
    corrected = service.edit_memory(args.memory_id, args.statement)
    if args.json:
        _dump({"memory_id": corrected, "supersedes": args.memory_id, "review_state": "accepted"})
    else:
        print(f"Corrected as {corrected}. The original {args.memory_id} stays in your history.")
    return 0


def cmd_review(args: argparse.Namespace, service: Any) -> int:
    action = args.review_command
    routed = {"list": _cmd_review_list, "policy": _cmd_review_policy,
              "reminders": _cmd_reminders, "snooze": _cmd_snooze, "edit": _cmd_edit}.get(action)
    if routed is not None:
        return int(routed(args, service))
    state = service.review_memory(args.memory_id, action)
    if args.json:
        _dump({"memory_id": args.memory_id, "review_state": state})
    else:
        print({
            "accepted": f"Kept {args.memory_id}.",
            "revoked": f"Stopped using {args.memory_id}. Its history is kept.",
            "pinned": f"Pinned {args.memory_id}. It will not appear in review reminders.",
        }[state])
    return 0


def _cmd_review_list(args: argparse.Namespace, service: Any) -> int:
    items = service.review_pending()
    if args.json:
        _dump([{"id": m.id, "module": m.module, "statement": m.statement,
                "review_state": "auto_promoted_pending_review"} for m in items])
        return 0
    if not items:
        print("Nothing Aptuni learned on its own is waiting for you.")
        return 0
    print(f"{len(items)} memory(ies) Aptuni added on its own. They are already in use:")
    for memory in items:
        print(f"  {memory.id}  [{memory.module}]  {memory.statement}")
    print("Keep one with: aptuni memory review accept ID   |   stop using it with: aptuni memory review reject ID")
    return 0


def _cmd_reminders(args: argparse.Namespace, service: Any) -> int:
    reminder = service.review_reminder()
    if args.json:
        _dump({"pending": reminder.pending, "due": reminder.due, "reason": reminder.reason,
               "threshold": reminder.threshold,
               "next_due_at": reminder.next_due_at.isoformat() if reminder.next_due_at else None})
        return 0
    if not reminder.due:
        print(f"{reminder.pending} memory(ies) awaiting review; no reminder is due.")
        return 0
    print(f"{reminder.pending} memory(ies) Aptuni added on its own are waiting for you. "
          "See them with: aptuni memory review list")
    return 0


def _cmd_review_policy(args: argparse.Namespace, service: Any) -> int:
    changes: dict[str, Any] = {}
    if args.auto_promotion is not None:
        changes["auto_promotion_enabled"] = args.auto_promotion == "on"
    if args.host_proposals is not None:
        changes["auto_promote_host_proposals"] = args.host_proposals == "on"
    for flag, field in (("pending_threshold", "pending_threshold"), ("interval_days", "interval_days"),
                        ("snooze_days", "snooze_days")):
        value = getattr(args, flag)
        if value is not None:
            changes[field] = value
    policy = service.set_review_policy(**changes) if changes else service.review_policy()
    if args.json:
        _dump({"auto_promotion_enabled": policy.auto_promotion_enabled,
               "auto_promote_host_proposals": policy.auto_promote_host_proposals,
               "sensitive_modules": list(policy.sensitive_modules),
               "pending_threshold": policy.pending_threshold,
               "interval_days": policy.interval_days, "snooze_days": policy.snooze_days})
        return 0
    state = "on" if policy.auto_promotion_enabled else "off"
    print(
        f"Automatic promotion: {state}" + "\n" +
        "Agent proposals: " + ("saved automatically, reviewable later" if policy.auto_promote_host_proposals
                               else "wait for your confirmation") + "\n" +
        f"Always asks first for: {', '.join(policy.sensitive_modules) or '(nothing)'}" + "\n" +
        f"Reminds at: {policy.pending_threshold} pending, or after {policy.interval_days} days" + "\n" +
        f"Snooze length: {policy.snooze_days} days"
    )
    return 0


def _dump(value: Any) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True))


def cmd_observe(args: argparse.Namespace, service: Any) -> int:
    proposal = service.observe(args.statement, args.module)
    if args.json:
        _dump({"candidate_id": proposal.candidate_id, "created": proposal.created,
               "memory_id": proposal.memory_id, "review_state": proposal.review_state})
        return 0
    if proposal.memory_id is None:
        state = "recorded" if proposal.created else "already recorded"
        print(f"Observation {state} as {proposal.candidate_id}; review it with: aptuni memory accept "
              f"{proposal.candidate_id}")
        return 0
    # Say plainly that this is already in use, and how to undo it, rather than burying it.
    print(f"Noted and in use as {proposal.memory_id}. Aptuni added this on its own because you "
          f"said it yourself.\nChange your mind with: aptuni memory review reject {proposal.memory_id}")
    return 0


def _cmd_forget(args: argparse.Namespace, service: Any) -> int:
    if args.confirm_digest is not None:
        service.forget_memory_confirmed(args.memory_id, args.confirm_digest)
        print(f"Forgotten: {args.memory_id} no longer reaches any agent. Its history is kept.")
        return 0
    preview = service.memory_forget_preview(args.memory_id)
    digest = preview.digest()
    print(f"Memory: {preview.memory_id}\nModule: {preview.module}\nFrom: {preview.episode} "
          f"({preview.trust})\nStatement: {preview.statement}\nPolicy epoch: {preview.policy_epoch}\n"
          f"Effect: stop exposing this memory; keep its audit history\nNonce: {preview.nonce_id}\n"
          f"Expires: {preview.expires_at.isoformat()}\nDigest: {digest}")
    if input("Type FORGET to revoke this memory: ").strip() != "FORGET":
        service.cancel_memory_confirmation("memory", args.memory_id)
        print("Cancelled. Nothing was changed.")
        return 1
    service.forget_memory_confirmed(args.memory_id, digest)
    print(f"Forgotten: {args.memory_id} no longer reaches any agent. Its history is kept.")
    return 0


def _cmd_listing(args: argparse.Namespace, service: Any) -> int:
    """`memory pending` and `memory list`: the two read-only views of the lifecycle."""
    if args.memory_command == "pending":
        items = service.pending_memories()
        if args.json:
            _dump([{"candidate_id": p.candidate_id, "module": p.module, "trust": p.trust, "episode": p.episode,
                    "statement": p.statement} for p in items])
        elif not items:
            print("Nothing is waiting for review.")
        for p in [] if args.json else items:
            print(f"{p.candidate_id}  [{p.module}]  from {p.episode}: {p.statement}")
        return 0
    memories = service.memories()
    records = service.records()
    if args.json:
        _dump([{"id": m.id, "module": m.module, "statement": m.statement,
                "review_state": review_state_of(m, records)} for m in memories])
    for m in [] if args.json else memories:
        print(f"{m.id}  [{m.module}]  {m.statement}")
    return 0


def cmd_memory(args: argparse.Namespace, service: Any) -> int:
    action = args.memory_command
    routed = {"review": cmd_review, "provider": _cmd_provider, "forget": _cmd_forget,
              "pending": _cmd_listing, "list": _cmd_listing}.get(action)
    if routed is not None:
        return int(routed(args, service))
    preview = service.memory_preview(args.candidate_id)
    digest = preview.digest(action)
    print(f"Proposal: {preview.candidate_id}\nModule: {preview.module}\nFrom: {preview.episode} "
          f"({preview.trust})\nStatement: {preview.statement}\nPolicy epoch: {preview.policy_epoch}\n"
          f"Decision: {action}\nNonce: {preview.nonce_id}\nExpires: {preview.expires_at.isoformat()}\n"
          f"Digest: {digest}")
    if args.confirm_digest is None:
        word = action.upper()
        if input(f"Type {word} to {action} this memory: ").strip() != word:
            service.cancel_memory_confirmation("candidate", args.candidate_id)
            print("Cancelled. Nothing was changed.")
            return 1
    elif args.confirm_digest != digest:
        raise AptuniError("confirmation_stale", "The digest does not match this preview; nothing was changed.")
    memory_id = service.decide_memory(args.candidate_id, action, digest)
    print(f"Accepted as {memory_id}." if memory_id else "Rejected. It will never be used.")
    return 0


def _cmd_provider(args: argparse.Namespace, service: Any) -> int:
    action = args.provider_command
    if action == "delete":
        removed = service.delete_memory_provider()
        value = {"provider": "mem0", "removed": removed, "canonical_changed": False}
        if args.json:
            _dump(value)
        else:
            print("Deleted the derived Mem0 projection; the canonical Vault was not changed."
                  if removed else "No Mem0 projection was present; the canonical Vault was not changed.")
        return 0
    if action == "rebuild":
        report = service.rebuild_memory_provider()
        value = {
            "provider": report.provider,
            "records": report.records,
            "vault_seq": report.vault_seq,
            "generation": report.generation,
            "cleanup_pending": report.cleanup_pending,
        }
        if args.json:
            _dump(value)
        else:
            cleanup = " cleanup_required" if report.cleanup_pending else ""
            print(f"Rebuilt Mem0 projection: records={report.records} vault_seq={report.vault_seq}{cleanup}")
        return 0
    status = service.memory_provider_status()
    if args.json:
        _dump(status.to_dict())
    else:
        print(f"Mem0 projection: {status.state}  records={status.records}  "
              f"dependency={'available' if status.dependency_available else 'missing'}")
        print("Inference: disabled; deletion: whole-store rebuild; portable export: no")
    return 0
