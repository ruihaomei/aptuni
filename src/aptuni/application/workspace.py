"""Where the Vault and the local state live.

The state directory holds only what is disposable or host-local: the writer lock, the config, the
retrieval projection, pending confirmations and adapter grants. It can be deleted and rebuilt. The
deletion ledger is *not* here — it is canonical and lives in the Vault, so a deletion survives a
wiped state directory and travels with a backup (ADR-0016, which amends ADR-0010 after KI-021).
``APTUNI_STATE_DIR`` overrides the default.
"""

from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path

CONFIG_VERSION = 1
DEFAULT_VAULT = Path.home() / "Aptuni"


def default_state_dir() -> Path:
    override = os.environ.get("APTUNI_STATE_DIR")
    if override:
        return Path(override).expanduser()
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "Aptuni"
    base = os.environ.get("XDG_STATE_HOME") or str(Path.home() / ".local" / "state")
    return Path(base) / "aptuni"


@dataclass(frozen=True)
class Workspace:
    state_dir: Path

    @classmethod
    def default(cls) -> Workspace:
        return cls(default_state_dir())

    @property
    def config_path(self) -> Path:
        return self.state_dir / "config.json"

    def vault_path(self) -> Path | None:
        if not self.config_path.exists():
            return None
        data = json.loads(self.config_path.read_text(encoding="utf-8"))
        return Path(data["vault"])

    def save(self, vault: Path) -> None:
        self.state_dir.mkdir(parents=True, exist_ok=True)
        body = json.dumps({"version": CONFIG_VERSION, "vault": str(vault)}, indent=1, sort_keys=True)
        tmp = self.config_path.with_suffix(".tmp")
        tmp.write_text(body + "\n", encoding="utf-8")
        os.replace(tmp, self.config_path)
