"""Reconnect this installation to an existing Profile Vault (Beta finding P2).

A reinstall, a new machine or a wiped state directory leaves a healthy Vault with no config pointing
at it. Attaching reads and verifies that Vault and then writes only the local config pointer. It
never calls ``Vault.open``, because opening runs ``recover()``, which may rewrite files inside the
Vault; the first ordinary command after attaching performs that normal recovery instead.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from aptuni.application.errors import AptuniError
from aptuni.application.workspace import Workspace
from aptuni.vault.fsgate import UnsupportedFilesystemError
from aptuni.vault.store import Vault, VaultIntegrityError

__all__ = ["AttachResult", "attach_vault"]


@dataclass(frozen=True)
class AttachResult:
    vault_path: Path
    already_attached: bool
    seq: int
    records: int


def attach_vault(workspace: Workspace, vault_path: Path) -> AttachResult:
    """Verify ``vault_path`` read-only, then point this installation's config at it."""
    vault_path = vault_path.expanduser().resolve()
    state = workspace.state_dir.expanduser().resolve()
    if state == vault_path or vault_path in state.parents:
        raise AptuniError("state_inside_vault", "The state directory must be outside the Vault.")
    if not (vault_path / "HEAD.json").is_file():
        raise AptuniError(
            "vault_invalid",
            f"{vault_path} is not an Aptuni Vault (it has no HEAD.json). Check the path, "
            "or create a new Vault with `aptuni init`.",
        )
    configured = workspace.vault_path()
    if configured is not None and configured.resolve() != vault_path:
        raise AptuniError(
            "vault_already_configured",
            f"This installation already uses the Vault at {configured}. Nothing was changed. "
            "To use a different Vault, move or remove the local config first "
            f"({workspace.config_path}); no Vault is ever deleted.",
        )
    state.mkdir(parents=True, exist_ok=True)
    os.chmod(state, 0o700)
    try:
        report = Vault(vault_path, state).verify()
    except (VaultIntegrityError, UnsupportedFilesystemError, OSError, ValueError, KeyError, TypeError) as error:
        raise _unverified(vault_path, type(error).__name__) from error
    if not report.ok:
        raise _unverified(vault_path, "; ".join(report.problems))
    if configured is None:
        workspace.save(vault_path)
    return AttachResult(vault_path, configured is not None, report.seq, report.records)


def _unverified(vault_path: Path, reason: str) -> AptuniError:
    return AptuniError(
        "vault_unverified",
        f"The Vault at {vault_path} did not pass verification ({reason}). Nothing was changed. "
        "Keep this folder as it is; if you have a backup, check it with `aptuni backup verify`.",
    )
