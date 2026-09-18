#!/usr/bin/env python3
"""Hard-crash helper for testing the durable approval/journal boundary."""

from __future__ import annotations

import os
import sqlite3
import sys
from pathlib import Path


def main() -> None:
    database, action_id, principal, crash_at = sys.argv[1:]
    connection = sqlite3.connect(str(Path(database)), isolation_level=None)
    connection.execute("BEGIN IMMEDIATE")
    row = connection.execute(
        "SELECT principal, consumed FROM actions WHERE action_id = ?", (action_id,)
    ).fetchone()
    if row is None or row[0] != principal or row[1]:
        os._exit(90)
    connection.execute("UPDATE actions SET consumed = 1 WHERE action_id = ?", (action_id,))
    connection.execute("INSERT INTO intents(action_id, state) VALUES (?, 'pending')", (action_id,))
    if crash_at == "before_commit":
        os._exit(91)
    connection.execute("COMMIT")
    if crash_at == "after_commit":
        os._exit(92)
    os._exit(0)


if __name__ == "__main__":
    main()
