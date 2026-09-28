"""How to make Claude Code or Codex use a generated bundle (Beta dogfooding, 2026-09-28).

Aptuni never edits host configuration, so after a bundle exists the owner needs the exact commands.
They are derived from the bundle itself: the Claude plugin directory, and the Codex skills folder plus
the MCP command recorded in the bundle's ``config.toml``. Aptuni stays OFF until a skill is invoked.
"""

from __future__ import annotations

import os
import shlex
import tomllib
from pathlib import Path

from aptuni.i18n import t

__all__ = ["connect_lines"]


def connect_lines(bundle: Path, locale: str) -> list[str]:
    """Return the connect instructions for one bundle, or nothing if it is not a known host bundle."""
    if (bundle / ".claude-plugin" / "plugin.json").is_file():
        quoted = shlex.quote(str(bundle))
        return [t("connect.claude.title", locale), f"    claude plugin marketplace add {quoted}",
                "    claude plugin install aptuni@aptuni-local",
                t("connect.claude.once", locale), f"    claude --plugin-dir {quoted}",
                t("connect.claude.use", locale), t("connect.off", locale)]
    config = bundle / "config.toml"
    if config.is_file():
        server = tomllib.loads(config.read_text(encoding="utf-8"))["mcp_servers"]["aptuni"]
        state = os.environ.get("APTUNI_STATE_DIR")
        env = f"--env APTUNI_STATE_DIR={shlex.quote(state)} " if state else ""
        command = shlex.join([str(server["command"]), *(str(arg) for arg in server["args"])])
        skills = shlex.quote(str(bundle / ".agents" / "skills"))
        return [t("connect.codex.title", locale),
                f"    mkdir -p .agents/skills && cp -R {skills}/. .agents/skills/",
                f"    codex mcp add aptuni {env}-- {command}",
                t("connect.codex.use", locale), t("connect.off", locale)]
    return []
