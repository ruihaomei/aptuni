"""Rendering helpers shared by every owner-facing surface.

Any value that came from outside the core -- a folder name, a host destination, a source root -- is
data, never terminal structure. It is rendered bounded, escaped and delimited, with control and
confusable characters flagged, so a crafted name cannot forge the lines an owner reads before
confirming an irreversible action (ADR-0013 item 2).
"""

from __future__ import annotations

import json

MAX_RENDERED = 500


def delimited_untrusted(value: str) -> str:
    """Render an outside-controlled name as bounded escaped data, never terminal structure."""
    bounded = value[:MAX_RENDERED]
    rendered = json.dumps(bounded, ensure_ascii=True)
    flags = []
    if any(ord(character) < 32 or ord(character) == 127 for character in bounded):
        flags.append("control-escaped")
    if any(ord(character) > 127 for character in bounded):
        flags.append("non-ascii/confusable-escaped")
    if len(value) > len(bounded):
        flags.append("truncated")
    return rendered + (" [" + ", ".join(flags) + "]" if flags else "")
