"""``aptuni observe`` and ``aptuni memory pending|list|accept|reject|forget`` (ADR-0011, ADR-0013).

Accepting or rejecting renders the full preview and needs a typed confirmation in the owner's
terminal (or ``--confirm-digest`` with the exact digest printed by that preview).
"""

from __future__ import annotations

import argparse
import json
from typing import Any

from aptuni.application.errors import AptuniError
from aptuni.domain.records import MODULES


def add_memory_commands(sub: Any) -> None:
    observe = sub.add_parser("observe", help="note something about yourself for review (stays hidden until accepted)")
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
    provider = memory_sub.add_parser("provider", help="inspect or manage the optional Mem0 projection")
    provider_sub = provider.add_subparsers(dest="provider_command", required=True, metavar="ACTION")
    for name, text in (
        ("status", "show content-free Mem0 projection health and capabilities"),
        ("rebuild", "rebuild Mem0 from current accepted canonical memories"),
        ("delete", "delete the entire derived Mem0 projection"),
    ):
        parser = provider_sub.add_parser(name, help=text)
        parser.add_argument("--json", action="store_true")


def _dump(value: Any) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True))


def cmd_observe(args: argparse.Namespace, service: Any) -> int:
    proposal = service.observe(args.statement, args.module)
    if args.json:
        _dump({"candidate_id": proposal.candidate_id, "created": proposal.created})
    else:
        state = "recorded" if proposal.created else "already recorded"
        print(f"Observation {state} as {proposal.candidate_id}; review it with: aptuni memory accept "
              f"{proposal.candidate_id}")
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


def cmd_memory(args: argparse.Namespace, service: Any) -> int:
    action = args.memory_command
    if action == "provider":
        return _cmd_provider(args, service)
    if action == "pending":
        items = service.pending_memories()
        if args.json:
            _dump([{"candidate_id": p.candidate_id, "module": p.module, "trust": p.trust, "episode": p.episode,
                    "statement": p.statement} for p in items])
        elif not items:
            print("Nothing is waiting for review.")
        for p in [] if args.json else items:
            print(f"{p.candidate_id}  [{p.module}]  from {p.episode}: {p.statement}")
        return 0
    if action == "list":
        memories = service.memories()
        if args.json:
            _dump([{"id": m.id, "module": m.module, "statement": m.statement} for m in memories])
        for m in [] if args.json else memories:
            print(f"{m.id}  [{m.module}]  {m.statement}")
        return 0
    if action == "forget":
        return _cmd_forget(args, service)
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
