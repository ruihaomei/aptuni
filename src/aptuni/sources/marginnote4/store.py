"""Read-only discovery and snapshot reads of the local MarginNote 4 store (ADR-0015).

The store is MarginNote's private Core Data SQLite database. Access is strictly read-only, gated by
a schema fingerprint, and wrapped in a child-process probe because macOS privacy protection (TCC)
blocks a process that touches another app's container until the user answers a system prompt.
Only minimized columns are selected; excerpt bodies and comment blobs are never read as text.
"""

from __future__ import annotations

import base64
import hashlib
import plistlib
import sqlite3
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

CONTAINER = Path.home() / "Library" / "Containers" / "QReader.MarginStudy.easy" / "Data"
STORE_GLOB = "Library/Private Documents/MN4NotebookDatabase/*/MarginNotes.sqlite"
APP_INFO = Path("/Applications/MarginNote 4.app/Contents/Info.plist")
PROBE_TIMEOUT_SECONDS = 20.0
TITLE_CHARS = 80
LABEL_FALLBACK_CHARS = 48

# Core Data model digests of layouts verified against a real store (ADR-0015 schema gate).
KNOWN_MODEL_DIGESTS = {
    "uH9kLsJKhfZYr77NiBWedzWEr2KAKBQqjepixUA10fn15YLBquTscxrldL6KLmwCoc4N+54seztwgZFLGgv9Qw==": "mn4-4.4",
}
REQUIRED_COLUMNS = {
    "ZBOOKNOTE": {"ZNOTEID", "ZTOPICID", "Z_OPT", "ZNOTETITLE", "ZHIGHLIGHT_TEXT", "ZGROUPNOTEID", "ZMINDLINKS",
                  "ZNOTES", "ZNOTE_DATE", "ZHIGHLIGHT_DATE", "ZBOOKMD5", "ZSTARTPAGE", "ZENDPAGE"},
    "ZTOPIC": {"ZTOPICID", "ZTITLE", "Z_OPT"},
    "ZBOOK": {"ZMD5", "ZMD5LONG", "ZFILE", "ZPATH"},
    "Z_METADATA": {"Z_UUID", "Z_PLIST"},
}

ProbeStatus = Literal["found", "permission_pending", "permission_denied", "not_found"]


class MarginNoteStoreError(RuntimeError):
    """A fixed, content-free reason the store cannot be read safely."""


@dataclass(frozen=True)
class Probe:
    status: ProbeStatus
    stores: tuple[Path, ...] = ()


@dataclass(frozen=True)
class NoteRow:
    note_id: str
    notebook_id: str
    revision: int
    title: str
    excerpt_head: str
    has_excerpt: bool
    group_id: str | None
    mindlinks: str
    annotated: bool
    note_date: float | None
    book_md5: str | None
    start_page: int | None
    end_page: int | None


@dataclass(frozen=True)
class StoreSnapshot:
    database_id: str
    layout: str
    notebooks: dict[str, str]  # notebook id -> title (display only)
    books: dict[str, str]  # book md5 (long or short) -> document file stem, ≤40 chars
    notes: tuple[NoteRow, ...]


_PROBE = (
    "import glob, os, sys\n"
    "root = sys.argv[1]\n"
    "try:\n"
    "    os.listdir(root)\n"
    "except FileNotFoundError:\n"
    "    sys.exit(4)\n"
    "except PermissionError:\n"
    "    sys.exit(3)\n"
    "for path in sorted(glob.glob(os.path.join(root, sys.argv[2]))):\n"
    "    print(path)\n"
)


def probe(container: Path = CONTAINER, timeout: float = PROBE_TIMEOUT_SECONDS) -> Probe:
    """Look for stores in a child process so a pending macOS privacy prompt cannot hang Aptuni."""
    try:
        done = subprocess.run([sys.executable, "-c", _PROBE, str(container), STORE_GLOB], capture_output=True,
                              text=True, timeout=timeout, check=False)
    except subprocess.TimeoutExpired:
        return Probe("permission_pending")
    if done.returncode == 4:
        return Probe("not_found")
    if done.returncode == 3:
        return Probe("permission_denied")
    stores = tuple(Path(line) for line in done.stdout.splitlines() if line.strip())
    return Probe("found", stores) if stores else Probe("not_found")


def app_version(info: Path = APP_INFO) -> str | None:
    try:
        with open(info, "rb") as handle:
            value = plistlib.load(handle).get("CFBundleShortVersionString")
    except (OSError, plistlib.InvalidFileException):
        return None
    return str(value) if value else None


def _connect(path: Path) -> sqlite3.Connection:
    if not path.is_file():
        raise MarginNoteStoreError("marginnote_store_missing")
    try:
        connection = sqlite3.connect(f"{path.resolve().as_uri()}?mode=ro", uri=True, timeout=10)
        connection.execute("PRAGMA query_only = ON")
    except sqlite3.Error as error:
        raise MarginNoteStoreError("marginnote_store_unreadable") from error
    return connection


def _layout(connection: sqlite3.Connection) -> tuple[str, str]:
    """Return (layout name, database id) or fail closed on an unknown or incomplete layout."""
    try:
        for table, columns in REQUIRED_COLUMNS.items():
            present = {row[1] for row in connection.execute(f'PRAGMA table_info("{table}")')}
            if not columns <= present:
                raise MarginNoteStoreError("marginnote_schema_unsupported")
        uuid, raw = connection.execute("SELECT Z_UUID, Z_PLIST FROM Z_METADATA").fetchone()
        metadata = plistlib.loads(raw)
    except (sqlite3.Error, TypeError, ValueError, plistlib.InvalidFileException) as error:
        raise MarginNoteStoreError("marginnote_schema_unsupported") from error
    digest = metadata.get("NSStoreModelVersionHashesDigest")
    if isinstance(digest, bytes):
        digest = base64.b64encode(digest).decode("ascii")
    layout = KNOWN_MODEL_DIGESTS.get(str(digest))
    if layout is None:
        raise MarginNoteStoreError("marginnote_schema_unsupported")
    return layout, "mn4db-" + hashlib.sha256(str(uuid).encode("utf-8")).hexdigest()[:16]


@dataclass(frozen=True)
class NotebookEntry:
    notebook_id: str
    title: str
    notes: int


def inventory(path: Path) -> tuple[str, tuple[NotebookEntry, ...]]:
    """Layout plus notebook IDs, titles and note counts for discovery; no card content is read."""
    connection = _connect(path)
    try:
        layout, _ = _layout(connection)
        counts = dict(connection.execute("SELECT ZTOPICID, count(*) FROM ZBOOKNOTE GROUP BY ZTOPICID").fetchall())
        entries = tuple(NotebookEntry(str(t), str(title or "")[:80], int(counts.get(t, 0)))
                        for t, title in connection.execute("SELECT ZTOPICID, ZTITLE FROM ZTOPIC ORDER BY ZTITLE")
                        if t)
    except sqlite3.Error as error:
        raise MarginNoteStoreError("marginnote_store_unreadable") from error
    finally:
        connection.close()
    return layout, entries


def _int(value: object) -> int | None:
    return int(value) if isinstance(value, int | float) else None


def read_snapshot(path: Path, notebooks: frozenset[str] | None) -> StoreSnapshot:
    """One consistent read-only snapshot of the selected notebooks (``None`` = all notebooks)."""
    connection = _connect(path)
    try:
        connection.execute("BEGIN")  # one WAL read transaction: the schema check and every query agree
        layout, database_id = _layout(connection)
        topics = {str(t): str(title or "") for t, title in connection.execute("SELECT ZTOPICID, ZTITLE FROM ZTOPIC")
                  if t and (notebooks is None or t in notebooks)}
        books: dict[str, str] = {}
        for short, long, file, path_value in connection.execute("SELECT ZMD5, ZMD5LONG, ZFILE, ZPATH FROM ZBOOK"):
            name = Path(str(file or path_value or "")).stem[:40]  # notes reference books by ZMD5LONG
            books.update({str(key): name for key in (long, short) if key})
        rows = connection.execute(
            "SELECT ZNOTEID, ZTOPICID, Z_OPT, substr(coalesce(ZNOTETITLE, ''), 1, ?),"
            " substr(coalesce(ZHIGHLIGHT_TEXT, ''), 1, ?), length(coalesce(ZHIGHLIGHT_TEXT, '')) > 0,"
            " ZGROUPNOTEID, coalesce(ZMINDLINKS, ''), ZNOTES IS NOT NULL, coalesce(ZNOTE_DATE, ZHIGHLIGHT_DATE),"
            " ZBOOKMD5, ZSTARTPAGE, ZENDPAGE FROM ZBOOKNOTE", (TITLE_CHARS, LABEL_FALLBACK_CHARS)).fetchall()
        connection.execute("ROLLBACK")
    except sqlite3.Error as error:
        raise MarginNoteStoreError("marginnote_store_unreadable") from error
    finally:
        connection.close()  # closing ends the read transaction on every path
    notes = tuple(
        NoteRow(str(r[0]), str(r[1]), int(r[2] or 0), str(r[3]), str(r[4]), bool(r[5]), r[6] or None, str(r[7]),
                bool(r[8]), float(r[9]) if isinstance(r[9], int | float) else None, r[10] or None,
                _int(r[11]), _int(r[12]))
        for r in rows if r[0] and r[1] in topics)
    return StoreSnapshot(database_id, layout, topics, books, notes)
