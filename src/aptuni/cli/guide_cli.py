"""``aptuni guide agent`` and ``aptuni connect``: set Aptuni up from inside an Agent chat.

The guide is the playbook the user's Agent follows so the owner only answers questions in chat and
types one APPLY in their own terminal. ``connect`` reprints the host commands for the current grant,
because the Agent does not see the output of the apply the owner ran in their terminal.
"""

from __future__ import annotations

import argparse
import os
import sys
from importlib import resources
from typing import Any

from aptuni import __version__
from aptuni.adapters.manager import AdapterManager
from aptuni.application.errors import AptuniError
from aptuni.application.service import AptuniService
from aptuni.cli import onboarding
from aptuni.cli.host_connect import connect_lines
from aptuni.i18n import normalize_locale, t

__all__ = ["add_guide_commands", "agent_guide", "cmd_connect", "cmd_guide"]

HOST_NAMES = {"claude": "Claude Code", "codex": "Codex"}


def add_guide_commands(sub: Any) -> None:
    guide = sub.add_parser("guide", help="print a setup playbook for your Agent to follow in chat")
    guide.add_argument("topic", choices=("agent",))
    guide.add_argument("--lang", default=None, help="en or zh-CN: the language your Agent should speak")
    connect = sub.add_parser("connect", help="show the exact commands that connect Claude Code or Codex")
    connect.add_argument("host", choices=tuple(HOST_NAMES))
    connect.add_argument("--lang", default=None, help="en or zh-CN")


def _locale(args: argparse.Namespace) -> str:
    return normalize_locale(args.lang or os.environ.get("APTUNI_LANG"))


def agent_guide(locale: str) -> str:
    template = resources.files("aptuni.guides").joinpath("agent-setup.md").read_text(encoding="utf-8")
    sources = "\n".join(f"{number}. {t(f'onboarding.source.{kind}', locale)}"
                        for number, kind in enumerate(onboarding.SOURCE_MENU, start=1))
    values = {"version": __version__, "lang": locale, "language": "简体中文" if locale == "zh-CN" else "English",
              "intro": onboarding.intro(locale).strip(), "sources": sources}
    for key, value in values.items():
        template = template.replace("{{" + key + "}}", value)
    return template


def cmd_guide(args: argparse.Namespace, _service: object) -> int:
    print(agent_guide(_locale(args)))
    return 0


def cmd_connect(args: argparse.Namespace, service: AptuniService) -> int:
    locale = _locale(args)
    manager = AdapterManager(service.workspace)
    candidates = []
    for path in (manager.root / "grants").glob("grant-*.json") if (manager.root / "grants").is_dir() else ():
        try:
            grant = manager.load_grant(path.stem)
        except (AptuniError, OSError, ValueError, KeyError, TypeError):
            continue
        bundle = manager.root / "bundles" / grant.grant_id
        if grant.host == args.host and bundle.is_dir():
            candidates.append((path.stat().st_mtime, bundle))
    if not candidates:
        print("aptuni: " + t("connect.none", locale, host=HOST_NAMES[args.host]), file=sys.stderr)
        return 1
    print("\n".join(connect_lines(max(candidates)[1], locale)))
    return 0
