from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from typing import Any

ROOT = Path(__file__).parents[2]
SKILLS = ("add-source-provider", "run-evals", "audit-licenses", "release")
LOCAL_PATH = re.compile(
    r"`((?:(?:docs|src|tests|tools|skills|\.github)/[^`\n\s]+|"
    r"(?:AGENTS|CHANGELOG|CONTRIBUTING|SECURITY|THIRD_PARTY_NOTICES)\.md))"
)


def _fixture(name: str) -> dict[str, Any]:
    path = ROOT / "tests" / "fixtures" / "skills" / f"{name}.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _frontmatter(text: str) -> dict[str, str]:
    lines = text.splitlines()
    if not lines or lines[0] != "---":
        raise ValueError("missing frontmatter opening delimiter")
    try:
        end = lines.index("---", 1)
    except ValueError as error:
        raise ValueError("missing frontmatter closing delimiter") from error
    values: dict[str, str] = {}
    for line in lines[1:end]:
        key, separator, value = line.partition(":")
        if not separator or not key or not value.strip():
            raise ValueError(f"invalid frontmatter line: {line}")
        values[key] = value.strip().strip('"')
    return values


def _expand(value: str, temporary: Path) -> str:
    if value == ".tools/bin/uv":
        return shutil.which("uv") or str(ROOT / value)
    return value.replace("{tmp}", str(temporary))


def _digests(directory: Path) -> dict[str, str]:
    return {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(directory.iterdir())
        if path.is_file()
    }


class SkillSmokeTests(unittest.TestCase):
    def test_skill_contracts_and_local_references_are_complete(self) -> None:
        for name in SKILLS:
            with self.subTest(skill=name):
                skill = ROOT / "skills" / name / "SKILL.md"
                text = skill.read_text(encoding="utf-8")
                frontmatter = _frontmatter(text)
                self.assertEqual({"name", "description"}, set(frontmatter))
                self.assertEqual(name, frontmatter["name"])
                self.assertTrue(frontmatter["description"].startswith("This skill should be used when "))
                for heading in ("## Goal", "## Boundaries", "## Workflow", "## Completion evidence"):
                    self.assertIn(heading, text)
                for relative in LOCAL_PATH.findall(text):
                    self.assertTrue((ROOT / relative.rstrip(".,")).exists(), relative)
                fixture = _fixture(name)
                self.assertEqual(name, fixture["skill"])
                self.assertTrue(fixture["prompt"].strip())
                self.assertIn(fixture["trigger"].lower(), frontmatter["description"].lower())

    def test_fixture_commands_execute_the_skill_smokes(self) -> None:
        for name in SKILLS:
            with self.subTest(skill=name), tempfile.TemporaryDirectory() as raw:
                temporary = Path(raw)
                fixture = _fixture(name)
                environment = os.environ.copy()
                environment.update(fixture.get("environment", {}))
                for command in fixture["commands"]:
                    subprocess.run(
                        [_expand(part, temporary) for part in command],
                        cwd=ROOT,
                        env=environment,
                        check=True,
                        capture_output=True,
                        text=True,
                    )
                for output in fixture.get("required_outputs", []):
                    self.assertTrue(Path(_expand(output, temporary)).is_file())
                if "reproducible_dirs" in fixture:
                    first, second = (
                        Path(_expand(value, temporary)) for value in fixture["reproducible_dirs"]
                    )
                    self.assertEqual(_digests(first), _digests(second))
                if "artifact_dir" in fixture:
                    artifacts = sorted(
                        path
                        for path in Path(_expand(fixture["artifact_dir"], temporary)).iterdir()
                        if path.suffix == ".whl" or path.name.endswith(".tar.gz")
                    )
                    subprocess.run(
                        [
                            _expand(".tools/bin/uv", temporary),
                            "run",
                            "python",
                            "tools/check_supply_chain.py",
                            "artifacts",
                            *map(str, artifacts),
                        ],
                        cwd=ROOT,
                        check=True,
                        capture_output=True,
                        text=True,
                    )


if __name__ == "__main__":
    unittest.main()
