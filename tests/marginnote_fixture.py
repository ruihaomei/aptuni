"""Synthetic MarginNote 4 store with the real layout's tables, columns and model digest (no real data)."""

from __future__ import annotations

import base64
import plistlib
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path

from aptuni.sources.marginnote4.store import KNOWN_MODEL_DIGESTS

DIGEST = next(iter(KNOWN_MODEL_DIGESTS))
SECRET_EXCERPT = "SECRET-BODY the full textbook paragraph that must never reach the Vault"
BOOK_LONG = "b" * 64


def nid(n: int) -> str:
    return f"00000000-0000-4000-8000-{n:012d}"


@dataclass
class Card:
    title: str = ""
    excerpt: str = ""
    children: list[int] = field(default_factory=list)
    group: int | None = None
    notebook: str = "NB-A"
    comments: bool = False
    page: int | None = None
    revision: int = 1


def build_store(path: Path, cards: dict[int, Card], notebooks: dict[str, str] | None = None,
                digest: str = DIGEST, drop_column: str | None = None) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.unlink(missing_ok=True)
    notebooks = notebooks or {"NB-A": "Statistics", "NB-B": "Engineering"}
    note_columns = ["Z_PK", "Z_OPT", "ZNOTEID", "ZTOPICID", "ZNOTETITLE", "ZHIGHLIGHT_TEXT", "ZGROUPNOTEID",
                    "ZMINDLINKS", "ZNOTES", "ZNOTE_DATE", "ZHIGHLIGHT_DATE", "ZBOOKMD5", "ZSTARTPAGE", "ZENDPAGE"]
    if drop_column:
        note_columns.remove(drop_column)
    with sqlite3.connect(path) as db:
        db.execute("PRAGMA journal_mode=WAL")
        db.execute(f"CREATE TABLE ZBOOKNOTE ({', '.join(note_columns)})")
        db.execute("CREATE TABLE ZTOPIC (Z_PK, Z_OPT, ZTOPICID, ZTITLE)")
        db.execute("CREATE TABLE ZBOOK (Z_PK, ZMD5, ZMD5LONG, ZFILE, ZPATH)")
        db.execute("CREATE TABLE Z_METADATA (Z_VERSION, Z_UUID, Z_PLIST)")
        meta = plistlib.dumps({"NSStoreModelVersionHashesDigest": digest, "NSStoreType": "SQLite"},
                              fmt=plistlib.FMT_BINARY)
        db.execute("INSERT INTO Z_METADATA VALUES (1, 'STORE-UUID-1', ?)", (meta,))
        db.executemany("INSERT INTO ZTOPIC VALUES (?, 1, ?, ?)", [(i, t, title) for i, (t, title)
                                                                   in enumerate(notebooks.items())])
        db.execute("INSERT INTO ZBOOK VALUES (1, 'short', ?, 'Elements of Statistical Learning.pdf', 'x/y')",
                   (BOOK_LONG,))
        for key, card in cards.items():
            row = {"Z_PK": key, "Z_OPT": card.revision, "ZNOTEID": nid(key), "ZTOPICID": card.notebook,
                   "ZNOTETITLE": card.title or None, "ZHIGHLIGHT_TEXT": card.excerpt or None,
                   "ZGROUPNOTEID": nid(card.group) if card.group else None,
                   "ZMINDLINKS": "|".join(nid(c) for c in card.children) or None,
                   "ZNOTES": b"blob" if card.comments else None, "ZNOTE_DATE": 757382400.0 + key * 86400,
                   "ZHIGHLIGHT_DATE": None, "ZBOOKMD5": BOOK_LONG if card.page else None,
                   "ZSTARTPAGE": card.page, "ZENDPAGE": card.page}
            values = [row[c] for c in note_columns]
            db.execute(f"INSERT INTO ZBOOKNOTE VALUES ({', '.join('?' for _ in values)})", values)
    return path


def base_cards() -> dict[int, Card]:
    """Statistics › Ensemble methods › Random forest (+ bagging, OOB), with excerpts and a merged card."""
    return {
        1: Card(title="Ensemble methods", children=[2, 3]),
        2: Card(title="Random forest", children=[4, 5, 6], comments=True, page=587),
        3: Card(title="Boosting"),
        4: Card(title="Bagging", page=588),
        5: Card(title="Out-of-bag error", page=592),
        6: Card(excerpt=SECRET_EXCERPT, page=589),  # untitled excerpt leaf: counted, never copied
        7: Card(excerpt=SECRET_EXCERPT, group=2),  # merged into the Random forest card
        8: Card(title="Feature engineering", notebook="NB-B"),
    }


def unknown_digest() -> str:
    return base64.b64encode(b"not-a-verified-layout").decode("ascii")
