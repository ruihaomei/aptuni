"""Find the owner's grant for this plugin without an environment variable.

``APTUNI_TOP_DOWN_GRANT_ID`` still wins when set. Otherwise the plugin asks Aptuni's public owner CLI
(``aptuni developer grant list --json``, contract ``aptuni.developer@1``) for current grants and
uses the newest one bound to this exact manifest digest, which is the owner's latest decision. It
never creates or widens a grant; ``connect`` still revalidates it live.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from collections.abc import Callable, Mapping
from datetime import datetime
from typing import Any

from aptuni.api.v1 import PluginManifest

__all__ = ["GrantLookupError", "list_owner_grants", "resolve_grant_id"]

ENV_VAR = "APTUNI_TOP_DOWN_GRANT_ID"


class GrantLookupError(RuntimeError):
    """No usable grant; the message tells the owner exactly what to run."""


def list_owner_grants() -> list[dict[str, Any]]:
    try:
        done = subprocess.run(
            [sys.executable, "-m", "aptuni", "developer", "grant", "list", "--json"],
            capture_output=True, text=True, timeout=30, check=False, env=dict(os.environ),
        )
        value = json.loads(done.stdout) if done.returncode == 0 else {}
    except (OSError, subprocess.SubprocessError, json.JSONDecodeError):
        value = {}
    grants = value.get("grants", []) if isinstance(value, dict) else []
    return [grant for grant in grants if isinstance(grant, dict)]


def resolve_grant_id(manifest: PluginManifest, environ: Mapping[str, str],
                     lister: Callable[[], list[dict[str, Any]]] = list_owner_grants) -> str:
    pinned = environ.get(ENV_VAR, "").strip()
    if pinned:
        return pinned
    digest = manifest.digest()
    matching = [grant for grant in lister()
                if grant.get("plugin_id") == manifest.id and grant.get("manifest_digest") == digest
                and isinstance(grant.get("grant_id"), str)]
    if not matching:
        raise GrantLookupError(
            "top_down_grant_required: no Aptuni grant for this Top-Down Learning version. Approve one with "
            "'aptuni developer grant plan \"$(top-down-study-mcp --manifest-path)\"' and "
            "'aptuni developer grant apply ACTION_ID' (type APPLY)."
        )
    newest = max(matching, key=lambda grant: _created(grant.get("created_at")))
    return str(newest["grant_id"])


def _created(value: object) -> datetime:
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return datetime.min.replace(tzinfo=datetime.now().astimezone().tzinfo)
