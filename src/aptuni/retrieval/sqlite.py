"""Atomic, disposable SQLite FTS5 projection over permitted canonical records."""

from __future__ import annotations

import fcntl
import os
import sqlite3
import tempfile
from collections.abc import Iterable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from aptuni.retrieval.lexical import LEXEME_VERSION, cjk_lexemes, query_expression

PROJECTION_SCHEMA = 1


FALLBACK_RELATIVE_SCORE = 0.25


class ProjectionError(RuntimeError):
    """Projection creation or access failed; canonical records remain untouched."""


@dataclass(frozen=True)
class ProjectionDocument:
    record_id: str
    record_type: str
    module: str
    source_id: str | None
    text: str


@dataclass(frozen=True)
class SearchRow:
    record_id: str
    score: float


@dataclass(frozen=True)
class ProjectionStatus:
    path: Path
    state: str
    vault_seq: int | None
    records: int
    bytes: int
    schema_version: int | None
    lexeme_version: int | None


class SqliteProjection:
    def __init__(self, state_dir: Path) -> None:
        self.directory = state_dir.expanduser().resolve() / "projections"
        self.path = self.directory / "retrieval.sqlite"
        self.lock_path = self.directory / "retrieval.lock"

    def _read_uri(self) -> str:
        return self.path.as_uri() + "?mode=ro"

    @contextmanager
    def _writer_lock(self) -> Iterator[None]:
        self.directory.mkdir(parents=True, exist_ok=True)
        os.chmod(self.directory, 0o700)
        with open(self.lock_path, "a+b") as handle:
            os.chmod(self.lock_path, 0o600)
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)

    def status(self, current_seq: int | None = None) -> ProjectionStatus:
        if not self.path.exists():
            return ProjectionStatus(self.path, "missing", None, 0, 0, None, None)
        try:
            with sqlite3.connect(self._read_uri(), uri=True) as connection:
                metadata = dict(connection.execute("SELECT key, value FROM metadata"))
                records = int(connection.execute("SELECT count(*) FROM records_fts").fetchone()[0])
            schema = int(metadata["schema_version"])
            lexeme = int(metadata["lexeme_version"])
            vault_seq = int(metadata["vault_seq"])
            compatible = schema == PROJECTION_SCHEMA and lexeme == LEXEME_VERSION
            state = "ready" if compatible and (current_seq is None or current_seq == vault_seq) else "stale"
            return ProjectionStatus(self.path, state, vault_seq, records, self.path.stat().st_size, schema, lexeme)
        except (KeyError, OSError, sqlite3.Error, TypeError, ValueError):
            size = self.path.stat().st_size if self.path.exists() else 0
            return ProjectionStatus(self.path, "corrupt", None, 0, size, None, None)

    def ensure(self, documents: Iterable[ProjectionDocument], vault_seq: int) -> ProjectionStatus:
        status = self.status(vault_seq)
        if status.state == "ready":
            return status
        return self.rebuild(documents, vault_seq)

    def rebuild(self, documents: Iterable[ProjectionDocument], vault_seq: int) -> ProjectionStatus:
        rows = list(documents)
        with self._writer_lock():
            existing = self.status()
            if existing.state == "ready" and existing.vault_seq is not None and existing.vault_seq > vault_seq:
                return existing
            descriptor, raw_tmp = tempfile.mkstemp(prefix=".retrieval-", suffix=".tmp", dir=self.directory)
            os.close(descriptor)
            tmp = Path(raw_tmp)
            try:
                self._build(tmp, rows, vault_seq)
                os.chmod(tmp, 0o600)
                file_descriptor = os.open(tmp, os.O_RDONLY)
                try:
                    os.fsync(file_descriptor)
                finally:
                    os.close(file_descriptor)
                os.replace(tmp, self.path)
                directory_descriptor = os.open(self.directory, os.O_RDONLY | os.O_DIRECTORY)
                try:
                    os.fsync(directory_descriptor)
                finally:
                    os.close(directory_descriptor)
            except (OSError, sqlite3.Error) as error:
                raise ProjectionError("sqlite_projection_rebuild_failed") from error
            finally:
                tmp.unlink(missing_ok=True)
            status = self.status(vault_seq)
            if status.state != "ready":
                raise ProjectionError("sqlite_projection_rebuild_incomplete")
            return status

    @staticmethod
    def _build(path: Path, rows: list[ProjectionDocument], vault_seq: int) -> None:
        with sqlite3.connect(path) as connection:
            connection.execute("PRAGMA journal_mode=DELETE")
            connection.execute("PRAGMA synchronous=FULL")
            connection.execute("CREATE TABLE metadata(key TEXT PRIMARY KEY, value TEXT NOT NULL)")
            try:
                connection.execute(
                    "CREATE VIRTUAL TABLE records_fts USING fts5("
                    "record_id UNINDEXED, record_type UNINDEXED, module UNINDEXED, "
                    "source_id UNINDEXED, body, tokenize='unicode61')"
                )
            except sqlite3.OperationalError as error:
                raise ProjectionError("sqlite_fts5_unavailable") from error
            metadata = {
                "schema_version": str(PROJECTION_SCHEMA),
                "lexeme_version": str(LEXEME_VERSION),
                "vault_seq": str(vault_seq),
            }
            connection.executemany("INSERT INTO metadata(key, value) VALUES (?, ?)", metadata.items())
            connection.executemany(
                "INSERT INTO records_fts(record_id, record_type, module, source_id, body) "
                "VALUES (?, ?, ?, ?, ?)",
                (
                    (row.record_id, row.record_type, row.module, row.source_id or "", " ".join(cjk_lexemes(row.text)))
                    for row in rows
                ),
            )
            connection.commit()

    def search(
        self,
        query: str,
        *,
        module: str | None = None,
        modules: tuple[str, ...] | None = None,
        record_types: tuple[str, ...] | None = None,
        limit: int = 5,
    ) -> list[SearchRow]:
        if type(limit) is not int or not 1 <= limit <= 101:
            raise ValueError("limit must be between 1 and 101")
        if module is not None and modules is not None:
            raise ValueError("pass module or modules, not both")
        filters, filter_parameters = "", list[Any]()
        if module is not None:
            filters += " AND module = ?"
            filter_parameters.append(module)
        elif modules:
            filters += " AND module IN (" + ",".join("?" for _ in modules) + ")"
            filter_parameters.extend(modules)
        if record_types:
            filters += " AND record_type IN (" + ",".join("?" for _ in record_types) + ")"
            filter_parameters.extend(record_types)
        rows = self._match(query_expression(query, "all"), filters, filter_parameters, limit)
        if len(rows) < limit:
            # Task-shaped requests rarely contain every term of a record: fill the remaining slots with
            # ranked any-term matches, keeping only those within FALLBACK_RELATIVE_SCORE of the best.
            seen = {row.record_id for row in rows}
            extra = [row for row in self._match(query_expression(query, "any"), filters, filter_parameters, limit)
                     if row.record_id not in seen]
            if extra:
                floor = extra[0].score * FALLBACK_RELATIVE_SCORE
                rows += [row for row in extra if row.score >= floor][: limit - len(rows)]
        return rows

    def _match(self, expression: str | None, filters: str, filter_parameters: list[Any], limit: int) -> list[SearchRow]:
        if expression is None:
            return []
        statement = (
            "SELECT record_id, bm25(records_fts) FROM records_fts WHERE records_fts MATCH ?"
            + filters + " ORDER BY bm25(records_fts), record_id LIMIT ?"
        )
        parameters: list[Any] = [expression, *filter_parameters, limit]
        try:
            with sqlite3.connect(self._read_uri(), uri=True) as connection:
                return [SearchRow(str(row[0]), -float(row[1])) for row in connection.execute(statement, parameters)]
        except sqlite3.Error as error:
            raise ProjectionError("sqlite_projection_search_failed") from error

    def delete(self) -> None:
        with self._writer_lock():
            sidecars = (self.path.with_name(self.path.name + "-wal"), self.path.with_name(self.path.name + "-shm"))
            for path in (self.path, *sidecars):
                path.unlink(missing_ok=True)


def documents_for(records: Iterable[Any]) -> list[ProjectionDocument]:
    documents = []
    for record in records:
        text = getattr(record, "statement", None) or getattr(record, "excerpt", None) or getattr(record, "subject", "")
        source_id = getattr(getattr(record, "provenance", None), "source_id", None)
        documents.append(ProjectionDocument(record.id, record.record_type, record.module, source_id, str(text)))
    return documents
