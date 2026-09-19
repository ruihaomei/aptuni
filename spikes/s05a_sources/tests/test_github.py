"""GitHub Standard identity: repository ID, commit, path, blob, truncation and bounded selection."""

from __future__ import annotations

import random
import unittest
from typing import Any

from s05a.contract import default_registry, delta_to_json
from s05a.github import GitHubScan, SourceIdentityError, scan_github

PARSER = ("github.standard", "1")


def tree(commit: str, files: dict[str, str], truncated: bool = False, repo_id: int = 42,
         name: str = "octo/demo") -> dict[str, Any]:
    entries = [{"path": p, "type": "blob", "sha": sha, "size": 10} for p, sha in files.items()]
    entries.append({"path": "src", "type": "tree", "sha": "t" * 40})
    return {"repository_id": repo_id, "full_name": name, "commit": commit * 40, "truncated": truncated,
            "tree": entries}


FILES = {
    "README.md": "a" * 40,
    "pyproject.toml": "b" * 40,
    "src/core.py": "c" * 40,
    "src/util.py": "d" * 40,
    "tests/test_core.py": "e" * 40,
}


def scan(data: dict[str, Any], previous: GitHubScan | None = None, budget: int = 10) -> GitHubScan:
    return scan_github(data, "src-gh", previous, PARSER, budget=budget)


def kinds(result: GitHubScan) -> list[str]:
    return sorted(op.kind for op in result.delta.operations)


class GitHubIdentityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.first = scan(tree("1", FILES))

    def test_first_import_records_repository_commit_path_and_blob(self) -> None:
        self.assertEqual(["add"] * 5, kinds(self.first))
        fields = self.first.snapshot.items[0].locator.extension.fields
        self.assertEqual({"repository_id", "commit", "path", "blob", "owner_name", "mode", "selection_reason"},
                         set(fields))
        self.assertEqual("standard", fields["mode"])

    def test_new_commit_with_same_blobs_is_a_noop(self) -> None:
        self.assertEqual([], kinds(scan(tree("2", FILES), self.first)))

    def test_identical_replay_is_idempotent(self) -> None:
        changed = dict(FILES, **{"src/core.py": "f" * 40})
        one, two = scan(tree("2", changed), self.first), scan(tree("2", changed), self.first)
        self.assertEqual(delta_to_json(one.delta), delta_to_json(two.delta))

    def test_edit_is_modify(self) -> None:
        [op] = scan(tree("2", dict(FILES, **{"src/core.py": "f" * 40})), self.first).delta.operations
        self.assertEqual("modify", op.kind)

    def test_same_blob_new_path_is_move(self) -> None:
        files = dict(FILES)
        files["src/engine.py"] = files.pop("src/core.py")
        [op] = scan(tree("2", files), self.first).delta.operations
        self.assertEqual("move", op.kind)
        self.assertEqual("src/engine.py", op.after.extension.fields["path"])  # type: ignore[union-attr]

    def test_deleted_path_is_tombstone_proposal(self) -> None:
        files = {k: v for k, v in FILES.items() if k != "src/util.py"}
        [op] = scan(tree("2", files), self.first).delta.operations
        self.assertEqual(("remove", "tombstone_proposal"), (op.kind, op.effect))

    def test_truncated_tree_is_partial_and_never_removes(self) -> None:
        files = {k: v for k, v in FILES.items() if k != "src/util.py"}
        second = scan(tree("2", files, truncated=True), self.first)
        self.assertEqual("partial", second.snapshot.coverage)
        self.assertEqual([], kinds(second))
        self.assertIn("tree_truncated", second.notes)

    def test_repository_rename_keeps_identity(self) -> None:
        second = scan(tree("2", FILES, name="octo/renamed"), self.first)
        self.assertEqual([], kinds(second))
        self.assertEqual("octo/renamed", second.snapshot.items[0].locator.extension.fields["owner_name"])

    def test_different_repository_under_same_source_is_refused(self) -> None:
        with self.assertRaises(SourceIdentityError):
            scan(tree("2", FILES, repo_id=99), self.first)


class GitHubSelectionTests(unittest.TestCase):
    def big_tree(self, seed: int) -> dict[str, Any]:
        files = {f"src/mod_{i:04d}.py": f"{i:040d}" for i in range(1500)}
        files.update({"README.md": "a" * 40, "package.json": "b" * 40})
        data = tree("1", files)
        random.Random(seed).shuffle(data["tree"])
        return data

    def test_selection_is_bounded_deterministic_and_prioritized(self) -> None:
        one, two = scan(self.big_tree(1), budget=20), scan(self.big_tree(2), budget=20)
        self.assertEqual(one.snapshot, two.snapshot)
        self.assertEqual(20, len(one.snapshot.items))
        reasons = {i.locator.extension.fields["path"]: i.locator.extension.fields["selection_reason"]
                   for i in one.snapshot.items}
        self.assertEqual("readme", reasons["README.md"])
        self.assertEqual("manifest", reasons["package.json"])

    def test_selection_is_sticky_and_unselected_files_are_not_removed(self) -> None:
        first = scan(self.big_tree(1), budget=20)
        data = self.big_tree(3)
        data["tree"].append({"path": "src/aaa_new.py", "type": "blob", "sha": "9" * 40, "size": 1})
        second = scan(data, first, budget=20)
        self.assertEqual([], kinds(second))
        self.assertEqual(first.snapshot.items, second.snapshot.items)

    def test_every_locator_passes_the_registry(self) -> None:
        registry = default_registry()
        for op in scan(tree("1", FILES)).delta.operations:
            self.assertIs(op, registry.gate(op))


if __name__ == "__main__":
    unittest.main()
