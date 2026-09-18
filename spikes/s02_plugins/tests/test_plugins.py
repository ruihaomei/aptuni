"""S02 acceptance tests: discovery without execution, isolation, approval bound to the closure."""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from s02.fixtures import build_wheel, fixture_dists

SPIKE_ROOT = Path(__file__).resolve().parents[1]
PINNED_PYTHON = os.environ.get("S02_PYTHON", "/opt/homebrew/bin/python3.13")


class PluginEnv:
    """A disposable venv with selected fixture wheels installed offline."""

    def __init__(self, base: Path, name: str, dists: list[str], wheelhouse: Path) -> None:
        self.root = base / name
        self.markers = base / f"{name}-markers"
        self.markers.mkdir()
        subprocess.run([PINNED_PYTHON, "-m", "venv", str(self.root)], check=True)
        self.python = self.root / "bin" / "python"
        self.pip(["install", "--no-index", "--find-links", str(wheelhouse), *dists])

    def pip(self, args: list[str]) -> None:
        subprocess.run([str(self.python), "-m", "pip", "-q", "--disable-pip-version-check", *args],
                       check=True, capture_output=True)

    def run(self, *args: str) -> dict:
        env = dict(os.environ, PYTHONPATH=str(SPIKE_ROOT), S02_MARKER_DIR=str(self.markers))
        result = subprocess.run([str(self.python), "-m", "s02.cli", *args], env=env, cwd=SPIKE_ROOT,
                                capture_output=True, text=True, check=False)
        if result.returncode != 0:
            raise AssertionError(f"cli exited {result.returncode}: {result.stderr}")
        return json.loads(result.stdout)

    def imported(self) -> set[str]:
        return {p.name for p in self.markers.iterdir()}

    def clear_markers(self) -> None:
        for path in self.markers.iterdir():
            path.unlink()

    def site_packages(self) -> Path:
        return next((self.root / "lib").glob("python3.*/site-packages"))


class S02Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._tmp = tempfile.TemporaryDirectory()
        base = Path(cls._tmp.name)
        cls.wheelhouse = base / "wheelhouse"
        for dist in fixture_dists():
            build_wheel(dist, cls.wheelhouse)
        build_wheel(fixture_dists(dep_version="2.0.0")[0], base / "wheelhouse-v2")
        cls.base = base
        cls.env_a = PluginEnv(base, "env-a", ["pcx-fixture-good", "pcx-fixture-broken",
                                              "pcx-fixture-future", "pcx-fixture-sneaky"], cls.wheelhouse)
        cls.env_b = PluginEnv(base, "env-b", ["pcx-fixture-good", "pcx-fixture-dup"], cls.wheelhouse)

    @classmethod
    def tearDownClass(cls) -> None:
        cls._tmp.cleanup()

    def setUp(self) -> None:
        for env in (self.env_a, self.env_b):
            env.clear_markers()
        self.approvals = self.base / f"approvals-{self._testMethodName}.json"

    def approve(self, env: PluginEnv, *plugin_ids: str) -> None:
        for plugin_id in plugin_ids:
            env.run("approve", "--id", plugin_id, "--approvals", str(self.approvals))

    # ---------------------------------------------------------------- discovery
    def test_discovery_reads_manifests_without_importing_plugin_code(self) -> None:
        found = self.env_a.run("discover")
        self.assertEqual(set(), self.env_a.imported())
        ids = {p["plugin_id"]: p["status"] for p in found["plugins"]}
        self.assertEqual("ok", ids["source.fixture_good"])
        self.assertEqual("ok", ids["source.fixture_broken"])
        self.assertEqual("incompatible_contract", ids["source.fixture_future"])

    def test_duplicate_ids_fail_closed_without_import(self) -> None:
        found = self.env_b.run("discover")
        statuses = [p["status"] for p in found["plugins"] if p["plugin_id"] == "source.fixture_good"]
        self.assertEqual(["duplicate_id", "duplicate_id"], statuses)
        result = self.env_b.run("activate", "--enable", "source.fixture_good",
                                "--approvals", str(self.approvals))
        self.assertEqual([], result["active"])
        self.assertIn("duplicate", result["failed"]["source.fixture_good"])
        self.assertEqual(set(), self.env_b.imported())

    def test_incompatible_contract_is_rejected_before_import(self) -> None:
        with self.assertRaises(AssertionError) as ctx:
            self.approve(self.env_a, "source.fixture_future")
        self.assertIn("contract source/2", str(ctx.exception))
        result = self.env_a.run("activate", "--enable", "source.fixture_future",
                                "--approvals", str(self.approvals))
        self.assertIn("contract", result["failed"]["source.fixture_future"])
        self.assertNotIn("pcx_fixture_future.provider", self.env_a.imported())

    # ---------------------------------------------------------------- activation
    def test_unapproved_plugin_is_denied_without_import(self) -> None:
        result = self.env_a.run("activate", "--enable", "source.fixture_good",
                                "--approvals", str(self.approvals))
        self.assertIn("not approved", result["failed"]["source.fixture_good"])
        self.assertEqual(set(), self.env_a.imported())

    def test_broken_import_is_isolated_and_core_continues(self) -> None:
        self.approve(self.env_a, "source.fixture_good", "source.fixture_broken")
        result = self.env_a.run("activate", "--enable", "source.fixture_good,source.fixture_broken",
                                "--approvals", str(self.approvals))
        self.assertEqual(["source.fixture_good"], result["active"])
        self.assertIn("import", result["failed"]["source.fixture_broken"])

    def test_unconfigured_plugin_is_never_imported(self) -> None:
        self.approve(self.env_a, "source.fixture_good")
        self.env_a.run("activate", "--enable", "source.fixture_good", "--approvals", str(self.approvals))
        imported = self.env_a.imported()
        self.assertIn("pcx_fixture_good.provider", imported)
        self.assertNotIn("pcx_fixture_sneaky.provider", imported)
        self.assertNotIn("pcx_fixture_broken.provider", imported)

    def test_undeclared_network_is_detected_not_contained(self) -> None:
        self.approve(self.env_a, "source.fixture_sneaky")
        result = self.env_a.run("activate", "--enable", "source.fixture_sneaky",
                                "--approvals", str(self.approvals))
        self.assertEqual([], result["active"])
        self.assertIn("undeclared network", result["failed"]["source.fixture_sneaky"])
        self.assertTrue(any("detection only" in w for w in result["warnings"]))

    def test_activation_warns_plugins_are_trusted_code(self) -> None:
        self.approve(self.env_a, "source.fixture_good")
        result = self.env_a.run("activate", "--enable", "source.fixture_good",
                                "--approvals", str(self.approvals))
        self.assertTrue(any("trusted code" in w for w in result["warnings"]))

    # ---------------------------------------------------------------- closure approval
    def test_approval_records_complete_resolved_closure(self) -> None:
        self.approve(self.env_a, "source.fixture_good")
        record = json.loads(self.approvals.read_text(encoding="utf-8"))["source.fixture_good"]
        closure = {d["name"]: d for d in record["closure"]}
        self.assertEqual({"pcx-fixture-good", "pcx-fixture-dep"}, set(closure))
        self.assertEqual("1.0.0", closure["pcx-fixture-dep"]["version"])
        self.assertEqual(["pcx-fixture-dep>=1"], closure["pcx-fixture-good"]["requires"])
        self.assertRegex(closure["pcx-fixture-dep"]["record_digest"], r"^sha256:[0-9a-f]{64}$")
        self.assertRegex(record["manifest_sha256"], r"^sha256:[0-9a-f]{64}$")

    def test_tampered_transitive_file_requires_renewed_approval(self) -> None:
        env = PluginEnv(self.base, f"env-tamper-{os.getpid()}", ["pcx-fixture-good"], self.wheelhouse)
        self.approve(env, "source.fixture_good")
        target = env.site_packages() / "pcx_fixture_dep" / "__init__.py"
        target.write_text(target.read_text(encoding="utf-8") + "EVIL = True\n", encoding="utf-8")
        result = env.run("activate", "--enable", "source.fixture_good", "--approvals", str(self.approvals))
        self.assertIn("renewed approval", result["failed"]["source.fixture_good"])
        self.assertEqual(set(), env.imported())

    def test_tampered_bytecode_evades_record_but_not_isolated_pycache(self) -> None:
        env = PluginEnv(self.base, f"env-pyc-{os.getpid()}", ["pcx-fixture-good"], self.wheelhouse)
        self.approve(env, "source.fixture_good")
        pkg = env.site_packages() / "pcx_fixture_good"
        forge = (
            "import importlib.util, marshal, pathlib, sys\n"
            "pkg = pathlib.Path(sys.argv[1]); pyc = pkg / '__pycache__' / 'provider.cpython-313.pyc'\n"
            "header = pyc.read_bytes()[:16]\n"
            "evil = compile(\"import os, pathlib\\n"
            "pathlib.Path(os.environ['S02_MARKER_DIR'], 'PWNED').write_text('x')\\n"
            "class Provider:\\n    def probe(self): return {}\\n\", str(pkg / 'provider.py'), 'exec')\n"
            "pyc.write_bytes(header + marshal.dumps(evil))\n"
        )
        subprocess.run([str(env.python), "-c", forge, str(pkg)], check=True)
        # RECORD lists .pyc files without hashes, so closure verification still passes:
        result = env.run("activate", "--enable", "source.fixture_good", "--approvals", str(self.approvals))
        self.assertEqual(["source.fixture_good"], result["active"])
        self.assertIn("PWNED", env.imported(), "expected the documented bytecode gap to reproduce")
        env.clear_markers()
        isolated = env.run("activate", "--enable", "source.fixture_good", "--approvals", str(self.approvals),
                           "--isolated-bytecode")
        self.assertEqual(["source.fixture_good"], isolated["active"])
        self.assertNotIn("PWNED", env.imported())

    def test_transitive_version_drift_requires_renewed_approval(self) -> None:
        env = PluginEnv(self.base, f"env-drift-{os.getpid()}", ["pcx-fixture-good"], self.wheelhouse)
        self.approve(env, "source.fixture_good")
        env.pip(["install", "--no-index", "--find-links", str(self.base / "wheelhouse-v2"),
                 "pcx-fixture-dep==2.0.0"])
        result = env.run("activate", "--enable", "source.fixture_good", "--approvals", str(self.approvals))
        self.assertIn("renewed approval", result["failed"]["source.fixture_good"])
        self.assertEqual(set(), env.imported())


if __name__ == "__main__":
    unittest.main()
