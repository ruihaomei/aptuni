"""Multiprocess writers/readers on the Gate 0 baseline: one valid serial outcome, no lost update."""

from __future__ import annotations

import multiprocessing as mp
import os
import signal
import tempfile
import time
import unittest
from pathlib import Path

from s01.records import parse_record
from s01.vault import ConflictError, Vault
from tests.helpers import golden_raw

WRITERS = 8
ATTEMPTS_PER_WRITER = 6


def _observation(writer: int, attempt: int) -> dict:
    base = next(r for r in golden_raw() if r["id"] == "obs_00000000000000000000000001")
    suffix = f"{writer:02d}{attempt:02d}"
    return base | {
        "id": f"obs_{'0' * 21}9{suffix}",  # prefix '9' keeps generated ids disjoint from golden ids
        "idempotency_key": f"w{writer}:a{attempt}",
        "recorded_at": f"2026-09-18T15:{writer % 60:02d}:{attempt % 60:02d}+08:00",
    }


def _writer(vault_dir: str, state_dir: str, writer: int, results: "mp.Queue[tuple]") -> None:
    vault = Vault(Path(vault_dir), Path(state_dir))
    for attempt in range(ATTEMPTS_PER_WRITER):
        record = parse_record(_observation(writer, attempt))
        while True:
            seq = vault.head().seq
            try:
                vault.commit([record], expected_seq=seq)
                results.put(("ok", record.id))
                break
            except ConflictError:
                results.put(("conflict", record.id))


def _reader(vault_dir: str, state_dir: str, stop_at: float, results: "mp.Queue[tuple]") -> None:
    vault = Vault(Path(vault_dir), Path(state_dir))
    reads = 0
    while time.time() < stop_at:
        records = vault.read_all()  # raises on any torn/partial snapshot
        ids = [r.id for r in records]
        if len(ids) != len(set(ids)):
            results.put(("torn", reads))
            return
        reads += 1
    results.put(("reads", reads))


def _hold_lock_forever(vault_dir: str, state_dir: str) -> None:
    vault = Vault(Path(vault_dir), Path(state_dir))
    with vault.writer_lock():
        time.sleep(3600)


class ConcurrencyTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(dir=os.environ.get("S01_TMP_ROOT"))
        base = Path(self._tmp.name)
        self.vault_dir, self.state_dir = base / "vault", base / "state"
        seed = [parse_record(r) for r in golden_raw()]
        Vault.init(self.vault_dir, self.state_dir).commit(seed, expected_seq=0)
        self.ctx = mp.get_context("spawn")

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_simultaneous_writers_serialize_without_lost_updates(self) -> None:
        results = self.ctx.Queue()
        reader = self.ctx.Process(target=_reader, args=(str(self.vault_dir), str(self.state_dir),
                                                        time.time() + 8, results))
        writers = [self.ctx.Process(target=_writer, args=(str(self.vault_dir), str(self.state_dir),
                                                          w, results)) for w in range(WRITERS)]
        reader.start()
        for proc in writers:
            proc.start()
        for proc in writers:
            proc.join(60)
            self.assertEqual(0, proc.exitcode)
        reader.join(30)
        self.assertEqual(0, reader.exitcode)
        events = []
        while not results.empty():
            events.append(results.get())
        committed = {rid for kind, rid in events if kind == "ok"}
        self.assertEqual(WRITERS * ATTEMPTS_PER_WRITER, len(committed))
        self.assertFalse([e for e in events if e[0] == "torn"])
        vault = Vault(self.vault_dir, self.state_dir)
        final_ids = {r.id for r in vault.read_all()}
        self.assertTrue(committed <= final_ids, "lost update")
        self.assertEqual(1 + WRITERS * ATTEMPTS_PER_WRITER, vault.head().seq)
        self.last_conflicts = sum(1 for e in events if e[0] == "conflict")

    def test_lock_holder_crash_releases_lock(self) -> None:
        holder = self.ctx.Process(target=_hold_lock_forever, args=(str(self.vault_dir), str(self.state_dir)))
        holder.start()
        time.sleep(1.0)
        vault = Vault(self.vault_dir, self.state_dir)
        self.assertFalse(vault.try_writer_lock(), "lock should be held by the live holder")
        os.kill(holder.pid, signal.SIGKILL)
        holder.join(10)
        deadline = time.time() + 5
        while not vault.try_writer_lock() and time.time() < deadline:
            time.sleep(0.05)
        record = parse_record(_observation(99, 0))
        vault.commit([record], expected_seq=vault.head().seq)
        self.assertIn(record.id, {r.id for r in vault.read_all()})


if __name__ == "__main__":
    unittest.main()
