from __future__ import annotations

import importlib.util
import tarfile
import tempfile
import unittest
import zipfile
from pathlib import Path

MODULE_PATH = Path(__file__).parents[2] / "tools" / "check_supply_chain.py"
SPEC = importlib.util.spec_from_file_location("check_supply_chain", MODULE_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"cannot load {MODULE_PATH}")
gate = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(gate)


class SupplyChainTests(unittest.TestCase):
    def test_notice_check_reports_missing_extra_and_wrong_versions(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "uv.lock").write_text(
                'version = 1\n[[package]]\nname = "aptuni"\nversion = "1"\n'
                'dependencies = [{name = "dep"}]\n[[package]]\nname = "dep"\nversion = "2"\n',
                encoding="utf-8",
            )
            (root / "THIRD_PARTY_NOTICES.md").write_text(
                "## Distributed runtime dependencies\n\n| Package | Version | License | Notes |\n"
                "|---|---|---|---|\n| extra | 1 | MIT | x |\n",
                encoding="utf-8",
            )
            errors = gate.check_notices(root)
            self.assertTrue(any("missing" in error and "dep==2" in error for error in errors))
            self.assertTrue(any("non-runtime" in error and "extra==1" in error for error in errors))

    def test_runtime_packages_follows_requested_extras(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            lock = Path(raw) / "uv.lock"
            lock.write_text(
                'version = 1\n[[package]]\nname = "aptuni"\nversion = "1"\n'
                'dependencies = [{name = "dep", extra = ["crypto"]}]\n'
                '[[package]]\nname = "dep"\nversion = "2"\n'
                '[package.optional-dependencies]\ncrypto = [{name = "crypto"}]\n'
                '[[package]]\nname = "crypto"\nversion = "3"\n',
                encoding="utf-8",
            )
            self.assertEqual({"crypto": "3", "dep": "2"}, gate.runtime_packages(lock))

    def test_secret_scan_allows_named_public_example_but_rejects_a_key(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            safe = root / "safe.txt"
            safe.write_text("AKIAIOSFODNN7EXAMPLE", encoding="utf-8")
            unsafe = root / "unsafe.txt"
            unsafe.write_text("-----BEGIN " + "PRIVATE KEY-----", encoding="utf-8")
            errors = gate.check_secrets((safe, unsafe), root)
            self.assertEqual(["possible private key in unsafe.txt:1"], errors)

    def test_secret_scan_rejects_temporary_and_fine_grained_credentials(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            fixtures = {
                "aws.txt": "ASIA" + "A" * 16,
                "github.txt": "github_" + "pat_" + "A" * 24,
                "openai.txt": "sk-" + "proj-" + "A" * 24,
            }
            paths = []
            for name, value in fixtures.items():
                path = root / name
                path.write_text(value, encoding="utf-8")
                paths.append(path)
            errors = gate.check_secrets(tuple(paths), root)
            self.assertEqual(3, len(errors))
            self.assertTrue(any("AWS access key" in error for error in errors))
            self.assertTrue(any("GitHub token" in error for error in errors))
            self.assertTrue(any("OpenAI-style key" in error for error in errors))

    def test_artifacts_require_all_legal_files(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            wheel = root / "a.whl"
            with zipfile.ZipFile(wheel, "w") as archive:
                for name in gate.REQUIRED_LEGAL_FILES:
                    archive.writestr(f"pkg.dist-info/licenses/{name}", "ok")
            sdist = root / "a.tar.gz"
            payload = root / "LICENSE"
            payload.write_text("ok", encoding="utf-8")
            with tarfile.open(sdist, "w:gz") as archive:
                archive.add(payload, arcname="a/LICENSE")
            self.assertEqual([], gate.check_artifacts((wheel,)))
            errors = gate.check_artifacts((sdist,))
            self.assertTrue(any("NOTICE" in error for error in errors))
            self.assertTrue(any("THIRD_PARTY_NOTICES.md" in error for error in errors))

    def test_workflow_rejects_mutable_action_and_persisted_credentials(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            workflow = Path(raw) / "ci.yml"
            workflow.write_text(
                "permissions:\n  contents: read\nsteps:\n"
                "  - uses: actions/checkout@v4\n    with:\n      persist-credentials: true\n",
                encoding="utf-8",
            )
            errors = gate.check_workflow(workflow)
            self.assertTrue(any("immutable commit" in error for error in errors))
            self.assertTrue(any("persisted credentials" in error for error in errors))
            self.assertTrue(any("locked backend" in error for error in errors))
            self.assertTrue(any("audited hashes" in error for error in errors))
            self.assertTrue(any("evaluation manifest" in error for error in errors))
            self.assertTrue(any("threshold step fails" in error for error in errors))

    def test_workflow_binds_failed_eval_retention_to_the_upload_step(self) -> None:
        workflow = MODULE_PATH.parents[1] / ".github" / "workflows" / "ci.yml"
        text = workflow.read_text(encoding="utf-8")
        with tempfile.TemporaryDirectory() as raw:
            mutated = Path(raw) / "ci.yml"
            mutated.write_text(text.replace(
                "path: artifacts/eval-run.json", "path: artifacts/not-the-eval.json",
            ), encoding="utf-8")
            self.assertTrue(any("threshold step fails" in error
                                for error in gate.check_workflow(mutated)))

            condition = "if: always() && hashFiles('artifacts/eval-run.json') != ''"
            detached = text.replace(condition, "if: success()")
            detached = detached.replace(
                "      - name: Export runtime inventory and audit vulnerabilities",
                f"      - name: No-op detached condition\n        {condition}\n        run: true\n"
                "      - name: Export runtime inventory and audit vulnerabilities",
            )
            mutated.write_text(detached, encoding="utf-8")
            self.assertTrue(any("threshold step fails" in error
                                for error in gate.check_workflow(mutated)))

    def test_release_workflow_limits_publish_authority_and_reproducibly_builds(self) -> None:
        workflow = MODULE_PATH.parents[1] / ".github" / "workflows" / "release.yml"
        self.assertEqual([], gate.check_release_workflow(workflow))

        text = workflow.read_text(encoding="utf-8")
        with tempfile.TemporaryDirectory() as raw:
            mutated = Path(raw) / "release.yml"
            mutated.write_text(text.replace("id-token: write", "contents: write"), encoding="utf-8")
            self.assertTrue(any("sole OIDC permission" in error
                                for error in gate.check_release_workflow(mutated)))

            mutated.write_text(text.replace(
                '      - "v[0-9]+.[0-9]+.[0-9]+"', "      - main",
            ), encoding="utf-8")
            self.assertTrue(any("semantic-version tag" in error
                                for error in gate.check_release_workflow(mutated)))


if __name__ == "__main__":
    unittest.main()
