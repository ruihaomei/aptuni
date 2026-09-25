"""CLI journey for longitudinal maintainer dogfooding."""

from __future__ import annotations

import json
from typing import Any

from aptuni.cli.render import delimited_untrusted


def add_evaluation_commands(sub: Any) -> None:
    evaluate = sub.add_parser("evaluate", help="measure Aptuni on your real setup over time")
    actions = evaluate.add_subparsers(dest="evaluation_command", required=True, metavar="ACTION")
    for name, help_text in (
        ("setup", "inspect content-free setup readiness"),
        ("capture", "capture one content-free longitudinal snapshot"),
        ("report", "report longitudinal quality metrics"),
        ("reset", "delete all derived longitudinal evaluation state"),
    ):
        parser = actions.add_parser(name, help=help_text)
        parser.add_argument("--json", action="store_true")
    trial = actions.add_parser("trial", help="run one retrieval trial without storing its query text")
    trial.add_argument("query")
    trial.add_argument("--limit", type=int, default=5)
    trial.add_argument("--evidence", action="store_true", help="also measure L4 source Evidence")
    trial.add_argument("--json", action="store_true")
    score = actions.add_parser("score", help="label every returned record as useful or noise")
    score.add_argument("trial_id")
    score.add_argument("--useful", nargs="*", default=[])
    score.add_argument("--noise", nargs="*", default=[])
    score.add_argument("--json", action="store_true")


def _dump(value: object) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True))


def cmd_evaluate(args: Any, service: Any) -> int:
    action = args.evaluation_command
    if action == "setup":
        value = service.evaluation_setup()
    elif action == "trial":
        trial = service.evaluation_trial(args.query, limit=args.limit, include_evidence=args.evidence)
        value = {
            "trial_id": trial.id,
            "include_evidence": trial.include_evidence,
            "query_digest": trial.query_digest,
            "vault_seq": trial.vault_seq,
            "requested_units": trial.requested_units,
            "used_units": trial.used_units,
            "truncated": trial.truncated,
            "exposure_violations": trial.exposure_violations,
            "items": [
                {"id": item.id, "kind": item.kind, "module": item.module, "text": item.text}
                for item in trial.items
            ],
        }
    elif action == "score":
        trial = service.score_evaluation_trial(
            args.trial_id, useful_ids=tuple(args.useful), noise_ids=tuple(args.noise),
        )
        value = {"trial_id": trial.id, "scored": trial.scored,
                 "useful": list(trial.useful_ids), "noise": list(trial.noise_ids)}
    elif action == "capture":
        value = service.capture_evaluation_snapshot()
    elif action == "reset":
        value = {"removed": service.reset_evaluation()}
    else:
        value = service.evaluation_report()
    if args.json:
        _dump(value)
    else:
        _print_human(action, value)
    return 0


def _print_human(action: str, value: dict[str, Any]) -> None:
    if action == "trial":
        mode = "Profile/Memory + Evidence" if value["include_evidence"] else "Profile/Memory only"
        print(f"Trial {value['trial_id']} at Vault commit {value['vault_seq']} ({mode})")
        for item in value["items"]:
            print(f"  {item['id']}  [{item['module']}]  {delimited_untrusted(item['text'])}")
        print("Classify every id with: aptuni evaluate score TRIAL --useful ... --noise ...")
    elif action == "setup":
        print(f"Vault commit {value['vault_seq']}; sources={', '.join(value['source_types']) or 'none'}; "
              f"retrieval={value['retrieval_projection']}")
    elif action == "score":
        print(f"Scored {value['trial_id']}: useful={len(value['useful'])}, noise={len(value['noise'])}.")
    elif action == "capture":
        print(f"Captured longitudinal snapshot at Vault commit {value['vault_seq']}.")
    elif action == "reset":
        print("Deleted longitudinal evaluation state." if value["removed"] else "No evaluation state existed.")
    else:
        retrieval = value["retrieval"]
        print(f"Scored trials={retrieval['scored_trials']}; useful={retrieval['useful_context_rate']:.3f}; "
              f"noise={retrieval['noise_rate']:.3f}; traceable={retrieval['traceable_useful_rate']:.3f}.")
