"""``aptuni attach``: reconnect this installation to an existing Vault (Beta finding P2)."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Any

from aptuni.application.errors import AptuniError
from aptuni.application.service import AptuniService
from aptuni.cli.render import delimited_untrusted
from aptuni.i18n import normalize_locale, t

_LOCALIZED_ERRORS = frozenset({"vault_invalid", "vault_unverified", "vault_already_configured", "state_inside_vault"})


def add_attach_command(sub: Any) -> None:
    attach = sub.add_parser("attach", help="use an existing Profile Vault with this installation (read-only check)")
    attach.add_argument("path", type=Path, help="the folder that holds your existing Vault (it contains HEAD.json)")
    attach.add_argument("--lang", default=None, help="en or zh-CN")


def cmd_attach(args: argparse.Namespace, service: AptuniService) -> int:
    locale = normalize_locale(args.lang or os.environ.get("APTUNI_LANG"))
    path = args.path.expanduser().resolve()
    try:
        result = service.attach(path)
    except AptuniError as error:
        if error.code not in _LOCALIZED_ERRORS:
            raise
        try:
            configured = str(service.workspace.vault_path())
        except (OSError, ValueError, KeyError, TypeError):
            configured = "?"
        print("aptuni: " + t(f"attach.error.{error.code}", locale, path=delimited_untrusted(str(path)),
                             configured=delimited_untrusted(configured),
                             config=delimited_untrusted(str(service.workspace.config_path))), file=sys.stderr)
        return 1
    shown = delimited_untrusted(str(result.vault_path))
    if result.already_attached:
        print(t("attach.already", locale, path=shown))
    else:
        print(t("attach.done", locale, path=shown, seq=result.seq, records=result.records))
    print(t("attach.next", locale))
    return 0
