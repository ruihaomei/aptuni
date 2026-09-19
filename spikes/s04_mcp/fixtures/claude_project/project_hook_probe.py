"""Outer-observable proof that Claude loaded the project hook layer."""

from __future__ import annotations

import os
import json
import sys
from pathlib import Path


marker = os.environ.get("PCC_S04_PROJECT_HOOK_MARKER")
if marker:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, OSError):
        payload = {}
    sanitized = {
        "event_is_session_start": payload.get("hook_event_name") == "SessionStart",
        "session_id_present": isinstance(payload.get("session_id"), str)
        and bool(payload["session_id"]),
    }
    Path(marker).write_text(json.dumps(sanitized, sort_keys=True), encoding="utf-8")
