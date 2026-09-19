"""``aptuni source discover-marginnote | add-marginnote``.

Discovery runs only when the user asks, reads notebook IDs, titles and counts for the user's own
terminal, and persists nothing. Adding a source is the separate ingestion permission.
"""

from __future__ import annotations

import argparse
import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

from aptuni.application.errors import AptuniError
from aptuni.application.source_commands import MARGINNOTE_MESSAGES
from aptuni.domain.records import MODULES
from aptuni.sources.marginnote4 import MarginNoteStoreError, probe
from aptuni.sources.marginnote4.store import CONTAINER, app_version, inventory


def add_marginnote_parsers(source_sub: Any) -> None:
    discover = source_sub.add_parser(
        "discover-marginnote", help="look for a local MarginNote 4 library (asks macOS for access; reads no notes)")
    discover.add_argument("--container", type=Path, default=CONTAINER, help=argparse.SUPPRESS)
    discover.add_argument("--json", action="store_true")
    add = source_sub.add_parser("add-marginnote", help="approve MarginNote 4 notebooks as a read-only source")
    add.add_argument("--store", type=Path, help="library path from discover-marginnote (default: the only one found)")
    scope = add.add_mutually_exclusive_group(required=True)
    scope.add_argument("--notebook", action="append", dest="notebooks", metavar="NOTEBOOK_ID")
    scope.add_argument("--all-notebooks", action="store_true", help="include every notebook, also future ones")
    add.add_argument("--module", action="append", required=True, choices=MODULES, dest="modules")
    add.add_argument("--role", required=True, help="what these notes mean (for example: study-notes)")
    add.add_argument("--primary-for", action="append", default=[], metavar="DIMENSION",
                     help="for example knowledge.studied: MarginNote is your authority for what you studied")
    add.add_argument("--json", action="store_true")


def discover(container: Path = CONTAINER) -> dict[str, Any]:
    found = probe(container)
    result: dict[str, Any] = {"status": found.status, "app_version": app_version(), "stores": []}
    if found.status != "found":
        result["message"] = MARGINNOTE_MESSAGES.get(f"marginnote_{found.status}", "")
    for store in found.stores:
        entry: dict[str, Any] = {"path": str(store)}
        try:
            layout, notebooks = inventory(store)
        except MarginNoteStoreError as error:
            entry.update(status=str(error), message=MARGINNOTE_MESSAGES.get(str(error), ""))
        else:
            entry.update(status="supported", layout=layout, notebooks=[
                {"id": n.notebook_id, "title": n.title, "notes": n.notes} for n in notebooks])
        result["stores"].append(entry)
    return result


def cmd_discover(args: argparse.Namespace) -> int:
    result = discover(args.container)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=1))
        return 0 if result["status"] == "found" else 2
    if result["status"] != "found":
        print(f"MarginNote: {result['status']}. {result.get('message', '')}")
        return 2
    print(f"MarginNote {result['app_version'] or '(version unknown)'}: {len(result['stores'])} library found. "
          "Nothing was stored.")
    for store in result["stores"]:
        print(f"\nLibrary: {store['path']}\nStatus: {store['status']} {store.get('message', '')}".rstrip())
        for notebook in store.get("notebooks", []):
            if notebook["notes"]:
                print(f"  {notebook['id']}  {notebook['notes']:>6} notes  {notebook['title']}")
    print("\nNext: aptuni source add-marginnote --notebook NOTEBOOK_ID --module knowledge --role study-notes")
    return 0


MARGINNOTE_COMMANDS = ("discover-marginnote", "add-marginnote")


def cmd_marginnote(args: argparse.Namespace, service: Any, as_json: Callable[[Any], dict[str, Any]]) -> int:
    if args.source_command == "discover-marginnote":
        return cmd_discover(args)
    source = service.add_marginnote_source(
        resolve_store(args.store), None if args.all_notebooks else tuple(args.notebooks),
        modules=tuple(args.modules), role=args.role, primary_for=tuple(args.primary_for))
    if args.json:
        print(json.dumps(as_json(source), ensure_ascii=False, indent=1, sort_keys=True))
    else:
        scope = "all notebooks" if args.all_notebooks else f"{len(args.notebooks)} notebook(s)"
        print(f"Approved MarginNote source {source.id} ({scope}, read-only). Run: aptuni sync {source.id}")
    return 0


def resolve_store(store: Path | None) -> Path:
    if store is not None:
        return store
    found = probe()
    if found.status != "found":
        code = f"marginnote_{found.status}"
        raise AptuniError(code, MARGINNOTE_MESSAGES.get(code, "MarginNote is not reachable."))
    if len(found.stores) != 1:
        raise AptuniError("marginnote_store_ambiguous", "Several MarginNote libraries were found; pass --store.")
    return found.stores[0]
