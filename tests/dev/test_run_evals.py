from __future__ import annotations

import importlib.util
import json
import shutil
import tempfile
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).parents[2] / "tools" / "run_evals.py"
SPEC = importlib.util.spec_from_file_location("run_evals", MODULE_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"cannot load {MODULE_PATH}")
evals = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(evals)


class EvaluationHarnessTests(unittest.TestCase):
    def test_frozen_production_retrieval_evaluation_passes(self) -> None:
        result = evals.evaluate()
        self.assertTrue(result["passed"], result["failures"])
        self.assertGreaterEqual(result["metrics"]["retrieval"]["dev"]["recall_at_5"], 0.85)
        self.assertEqual(0.0, result["metrics"]["retrieval"]["dev"]["false_positive_rate"])
        self.assertIsNone(result["inputs"]["sbom_sha256"])

    def test_context_noise_checksum_detects_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            fixture = root / "example.json"
            fixture.write_text('{"changed":true}\n', encoding="utf-8")
            fixture.with_suffix(".sha256").write_text(f"{'0' * 64}  example.json\n", encoding="utf-8")
            with self.assertRaises(evals.EvaluationInputError):
                evals.verify_companion_checksum(fixture)

    def test_every_frozen_retrieval_input_mutation_blocks_before_scoring(self) -> None:
        manifest = json.loads((evals.CORPUS_ROOT / "FREEZE.json").read_text(encoding="utf-8"))
        for relative in manifest["sha256"]:
            with self.subTest(relative=relative), tempfile.TemporaryDirectory() as raw:
                root = Path(raw)
                shutil.copy2(evals.CORPUS_ROOT / "FREEZE.json", root / "FREEZE.json")
                for item in manifest["sha256"]:
                    target = root / item
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(evals.CORPUS_ROOT / item, target)
                with (root / relative).open("ab") as handle:
                    handle.write(b"\n")
                with self.assertRaises(evals.EvaluationInputError):
                    evals.evaluate(corpus_root=root)

    def test_threshold_failure_names_split_and_metric(self) -> None:
        failures = evals.threshold_failures("holdout", {"mrr": 0.5}, {"mrr_min": 0.7})
        self.assertEqual(["holdout.mrr=0.500000 misses mrr_min=0.7"], failures)

    def test_missing_sbom_blocks_instead_of_producing_an_incomplete_manifest(self) -> None:
        with self.assertRaises(evals.EvaluationInputError):
            evals.evaluate(sbom=Path("does-not-exist.cdx.json"))


if __name__ == "__main__":
    unittest.main()
