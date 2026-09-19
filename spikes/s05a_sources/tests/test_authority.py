"""User-policy authority: sole primary supersedes; everything else goes to parallel review."""

from __future__ import annotations

import unittest

from s05a.authority import (
    Claim,
    SourceConfig,
    config_from_json,
    config_to_json,
    recheck,
    resolution_from_json,
    resolution_to_json,
    resolve,
)


def config(source: str, primary: tuple[str, ...] = (), version: int = 1) -> SourceConfig:
    return SourceConfig(source, "folder", ("~/materials",), "application_materials", ("experience",), primary, version)


def claim(cid: str, source: str, value: str, confidence: float = 0.5, version: int = 1) -> Claim:
    return Claim(cid, source, "experience.role", "experience:acme", value, confidence, version)


class ResolveTests(unittest.TestCase):
    def test_sole_primary_supersedes_within_its_dimension(self) -> None:
        configs = {"cv": config("cv", ("experience.role",)), "gh": config("gh")}
        result = resolve([claim("c1", "cv", "Analyst"), claim("c2", "gh", "Engineer", 0.99)], configs)
        self.assertEqual(("c1", False, "sole_primary"), (result.winner, result.needs_review, result.reason))

    def test_confidence_never_overrides_missing_authority(self) -> None:
        configs = {"a": config("a"), "b": config("b")}
        result = resolve([claim("c1", "a", "X", 0.99), claim("c2", "b", "Y", 0.10)], configs)
        self.assertIsNone(result.winner)
        self.assertTrue(result.needs_review)
        self.assertEqual({"c1", "c2"}, set(result.parallel))
        self.assertEqual("no_primary", result.reason)

    def test_two_primaries_are_parallel_review(self) -> None:
        configs = {"a": config("a", ("experience.role",)), "b": config("b", ("experience.role",))}
        result = resolve([claim("c1", "a", "X"), claim("c2", "b", "Y")], configs)
        self.assertEqual(("multiple_primaries", True), (result.reason, result.needs_review))

    def test_primary_for_other_dimension_has_no_authority_here(self) -> None:
        configs = {"a": config("a", ("knowledge.studied",)), "b": config("b")}
        result = resolve([claim("c1", "a", "X"), claim("c2", "b", "Y")], configs)
        self.assertEqual("no_primary", result.reason)

    def test_agreeing_claims_need_no_review(self) -> None:
        configs = {"a": config("a"), "b": config("b")}
        result = resolve([claim("c1", "a", "X"), claim("c2", "b", "X")], configs)
        self.assertEqual(("agreement", False), (result.reason, result.needs_review))

    def test_policy_change_before_commit_forces_review(self) -> None:
        configs = {"cv": config("cv", ("experience.role",)), "gh": config("gh")}
        claims = [claim("c1", "cv", "Analyst"), claim("c2", "gh", "Engineer")]
        result = resolve(claims, configs)
        changed = {"cv": config("cv", (), version=2), "gh": config("gh")}
        rechecked = recheck(result, claims, changed)
        self.assertIsNone(rechecked.winner)
        self.assertEqual(("policy_changed", True), (rechecked.reason, rechecked.needs_review))
        self.assertIs(result, recheck(result, claims, configs))

    def test_claims_from_unconfigured_source_are_rejected(self) -> None:
        with self.assertRaises(KeyError):
            resolve([claim("c1", "ghost", "X")], {})


class RoundTripTests(unittest.TestCase):
    def test_config_round_trips(self) -> None:
        original = config("cv", ("experience.role", "projects.role"), version=3)
        self.assertEqual(original, config_from_json(config_to_json(original)))

    def test_conflict_resolution_round_trips(self) -> None:
        configs = {"a": config("a"), "b": config("b")}
        result = resolve([claim("c1", "a", "X"), claim("c2", "b", "Y")], configs)
        self.assertEqual(result, resolution_from_json(resolution_to_json(result)))


if __name__ == "__main__":
    unittest.main()
