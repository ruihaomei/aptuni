"""Obsidian vault identity, topology, frontmatter minimization and admission bounds."""

from __future__ import annotations

import os
import tempfile
import unicodedata
import unittest
from pathlib import Path

from aptuni.sources.contract import default_registry
from aptuni.sources.obsidian import ObsidianScan, is_vault, scan_obsidian
from aptuni.sources.obsidian_parse import (
    MAX_ALIASES,
    MAX_LINKS,
    MAX_PROPERTY_KEYS,
    MAX_TAGS,
    MAX_TOKEN,
    body_without_frontmatter,
    parse_note,
    sanitize_token,
)

PARSER = ("obsidian.vault", "1")


class VaultFixture:
    def __init__(self) -> None:
        self._temp = tempfile.TemporaryDirectory()
        self.root = Path(self._temp.name)
        (self.root / ".obsidian").mkdir()
        (self.root / ".obsidian" / "workspace.json").write_text("{}\n", encoding="utf-8")

    def write(self, relative: str, text: str) -> None:
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def move(self, old: str, new: str) -> None:
        (self.root / new).parent.mkdir(parents=True, exist_ok=True)
        os.replace(self.root / old, self.root / new)

    def scan(self, previous: ObsidianScan | None = None, **kw: object) -> ObsidianScan:
        return scan_obsidian(self.root, "src-obsidian", previous, PARSER, **kw)  # type: ignore[arg-type]

    def close(self) -> None:
        self._temp.cleanup()


def fields_by_path(scan: ObsidianScan) -> dict[str, dict[str, object]]:
    return {
        str(item.locator.extension.fields["relative_path"]): dict(item.locator.extension.fields)
        for item in scan.snapshot.items
    }


def kinds(scan: ObsidianScan) -> list[str]:
    return sorted(op.kind for op in scan.delta.operations)


class ObsidianAdmissionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.vault = VaultFixture()
        self.addCleanup(self.vault.close)

    def test_a_directory_without_an_obsidian_marker_is_not_a_vault(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            plain = Path(raw)
            (plain / "note.md").write_text("plain markdown\n", encoding="utf-8")
            self.assertFalse(is_vault(plain))
        self.assertTrue(is_vault(self.vault.root))

    def test_vault_config_trash_and_attachments_are_never_read(self) -> None:
        self.vault.write("Note.md", "body\n")
        self.vault.write(".obsidian/plugins/secret-plugin/data.json", '{"token":"abc"}\n')
        self.vault.write(".trash/Deleted.md", "deleted body\n")
        self.vault.write("attachments/diagram.png", "not really a png\n")
        self.vault.write("Attached.pdf", "pdf bytes\n")
        self.vault.write("notes/.env", "SECRET=1\n")
        self.vault.write("notes/id_rsa", "private key\n")

        scan = self.vault.scan()

        self.assertEqual(["Note.md"], sorted(fields_by_path(scan)))
        self.assertIn("obsidian_config_skipped", scan.notes)
        self.assertIn("trash_skipped", scan.notes)
        self.assertIn("attachment_skipped", scan.notes)

    def test_symlinked_notes_and_directories_are_skipped(self) -> None:
        self.vault.write("Real.md", "real\n")
        outside = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: __import__("shutil").rmtree(outside, ignore_errors=True))
        (outside / "Outside.md").write_text("outside\n", encoding="utf-8")
        os.symlink(outside / "Outside.md", self.vault.root / "Link.md")
        os.symlink(outside, self.vault.root / "linked-folder")

        scan = self.vault.scan()

        self.assertEqual(["Real.md"], sorted(fields_by_path(scan)))
        self.assertIn("symlink_skipped", scan.notes)

    def test_an_oversized_note_is_skipped_and_reported(self) -> None:
        self.vault.write("Small.md", "small\n")
        self.vault.write("Huge.md", "x" * 4096)

        scan = self.vault.scan(max_bytes=1024)

        self.assertEqual(["Small.md"], sorted(fields_by_path(scan)))
        self.assertIn("oversized_skipped", scan.notes)

    def test_a_vault_over_the_file_bound_reports_partial_and_proposes_no_removal(self) -> None:
        for index in range(4):
            self.vault.write(f"Note{index}.md", f"body {index}\n")
        first = self.vault.scan()
        self.assertEqual("complete", first.snapshot.coverage)

        second = self.vault.scan(previous=first, max_files=2)

        self.assertEqual("partial", second.snapshot.coverage)
        self.assertIn("coverage_partial", second.notes)
        self.assertNotIn("remove", kinds(second))


class ObsidianTopologyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.vault = VaultFixture()
        self.addCleanup(self.vault.close)

    def test_locator_carries_identity_and_topology_but_no_property_values(self) -> None:
        self.vault.write(
            "areas/Research/Method.md",
            "---\n"
            "tags: [method, reproducibility]\n"
            "aliases:\n"
            "  - Experimental Method\n"
            "employer: A Very Private Employer Name\n"
            "salary: 123456\n"
            "---\n"
            "# Method\n"
            "See [[Protocol]] and [[areas/Research/Baseline|the baseline]].\n"
            "## Details\n"
            "Also #open-question here.\n",
        )

        scan = self.vault.scan()
        fields = fields_by_path(scan)["areas/Research/Method.md"]

        self.assertEqual("Method", fields["note_name"])
        self.assertEqual("areas/Research", fields["folder_path"])
        self.assertEqual(["Baseline", "Protocol"], sorted(fields["outbound_links"]))  # type: ignore[arg-type]
        self.assertEqual(["method", "open-question", "reproducibility"], sorted(fields["tags"]))  # type: ignore[arg-type]
        self.assertEqual(["Experimental Method"], fields["aliases"])
        self.assertEqual(["aliases", "employer", "salary", "tags"], sorted(fields["property_keys"]))  # type: ignore[arg-type]
        self.assertEqual(2, fields["heading_count"])

        rendered = repr(fields)
        self.assertNotIn("A Very Private Employer Name", rendered)
        self.assertNotIn("123456", rendered)

    def test_a_note_at_the_vault_root_reports_an_empty_folder_path(self) -> None:
        self.vault.write("Inbox.md", "body\n")

        fields = fields_by_path(self.vault.scan())["Inbox.md"]

        self.assertEqual("Inbox", fields["note_name"])
        self.assertEqual("", fields["folder_path"])

    def test_registered_locator_schema_validates_every_emitted_locator(self) -> None:
        self.vault.write("Note.md", "---\ntags: [a]\n---\n[[Other]]\n")
        self.vault.write("Other.md", "plain\n")
        registry = default_registry()

        scan = self.vault.scan()

        for item in scan.snapshot.items:
            self.assertTrue(registry.understands(item.locator.extension))
            registry.validate(item.locator.extension)
        for operation in scan.delta.operations:
            self.assertEqual("none", registry.gate(operation).review_state)


class ObsidianParseTests(unittest.TestCase):
    def test_every_wikilink_form_normalizes_to_one_bounded_target(self) -> None:
        structure = parse_note(
            "[[Note]] [[Note|alias]] [[Note#Heading]] [[folder/Note]] ![[Note]] [[Note.md]]\n",
        )

        self.assertEqual(["Note"], structure.outbound_links)

    def test_links_and_tags_inside_code_are_not_structure(self) -> None:
        structure = parse_note(
            "Real [[Kept]] and #kept-tag.\n"
            "```\n[[Fenced]] #fenced-tag\n```\n"
            "Inline `[[Inline]] #inline-tag` here.\n"
            "~~~\n[[Tilde]]\n~~~\n",
        )

        self.assertEqual(["Kept"], structure.outbound_links)
        self.assertEqual(["kept-tag"], structure.tags)

    def test_a_heading_is_not_an_inline_tag(self) -> None:
        structure = parse_note("# Title\n## Subtitle\ntext #real-tag text\n")

        self.assertEqual(["real-tag"], structure.tags)
        self.assertEqual(2, structure.heading_count)

    def test_frontmatter_subset_yields_keys_tags_and_aliases(self) -> None:
        structure = parse_note(
            "---\n"
            "# a comment\n"
            "tags: [alpha, beta]\n"
            "aliases:\n"
            "  - First\n"
            "  - Second\n"
            "status: active\n"
            "---\n"
            "body\n",
        )

        self.assertEqual(["alpha", "beta"], structure.tags)
        self.assertEqual(["First", "Second"], structure.aliases)
        self.assertEqual(["aliases", "status", "tags"], structure.property_keys)
        self.assertEqual((), structure.notes)

    def test_out_of_subset_frontmatter_admits_the_note_without_properties(self) -> None:
        for block in (
            "---\nnested:\n  deep:\n    key: value\n---\nbody\n",
            "---\nanchor: &a value\nother: *a\n---\nbody\n",
            "---\nblock: |\n  multi\n  line\n---\nbody\n",
            "---\nunterminated: yes\nbody without a closing fence\n",
        ):
            structure = parse_note(block)
            self.assertEqual([], structure.property_keys, block)
            self.assertEqual([], structure.tags, block)
            self.assertIn("frontmatter_unsupported", structure.notes, block)

    def test_a_fence_that_is_not_at_byte_zero_is_body_text(self) -> None:
        structure = parse_note("Intro paragraph.\n---\ntags: [not-frontmatter]\n---\n")

        self.assertEqual([], structure.tags)
        self.assertEqual([], structure.property_keys)
        self.assertEqual((), structure.notes)

    def test_oversized_structure_is_capped_deterministically_and_flagged(self) -> None:
        tags = ", ".join(f"tag{index:04d}" for index in range(MAX_TAGS + 20))
        links = " ".join(f"[[Note{index:04d}]]" for index in range(MAX_LINKS + 20))

        structure = parse_note(f"---\ntags: [{tags}]\n---\n{links}\n")

        self.assertEqual(MAX_TAGS, len(structure.tags))
        self.assertEqual(MAX_LINKS, len(structure.outbound_links))
        self.assertTrue(structure.truncated)
        # The cap keeps the FIRST tokens in input order, so it is stable rather than set-ordered.
        self.assertEqual([f"tag{index:04d}" for index in range(MAX_TAGS)], structure.tags)
        self.assertEqual([f"Note{index:04d}" for index in range(MAX_LINKS)], structure.outbound_links)

    def test_control_characters_and_long_tokens_cannot_forge_a_field(self) -> None:
        structure = parse_note(
            "---\n"
            'tags: ["norm\x1b[31mal", "two\u202eline"]\n'
            "---\n"
            f"[[{'n' * (MAX_TOKEN + 50)}]] [[good\x1b[0mlink]]\n",
        )

        for token in (*structure.tags, *structure.outbound_links):
            self.assertLessEqual(len(token), MAX_TOKEN)
            self.assertFalse(any(ord(character) < 32 or ord(character) == 127 for character in token), token)

    def test_a_byte_order_mark_does_not_defeat_frontmatter_detection(self) -> None:
        """A BOM must not turn the property block into body text (Review 55 B1)."""
        text = "\ufeff---\nemployer: A Very Private Employer Name\nclient: #AcmeCorp\n---\nVisible body.\n"

        structure = parse_note(text)
        body = body_without_frontmatter(text)

        self.assertEqual(["client", "employer"], structure.property_keys)
        self.assertEqual([], structure.tags)
        self.assertEqual("Visible body.", body.strip())
        self.assertNotIn("A Very Private Employer Name", body)

    def test_a_yaml_document_end_marker_is_not_a_frontmatter_terminator(self) -> None:
        """Obsidian terminates only on `---`; `...` must fail closed, never split the block."""
        text = "---\ntitle: Note\n...\nemployer: SecretCorp Ltd\n---\n# Body\n"

        structure = parse_note(text)

        self.assertEqual([], structure.property_keys)
        self.assertIn("frontmatter_unsupported", structure.notes)
        self.assertNotIn("SecretCorp Ltd", body_without_frontmatter(text))

    def test_a_fence_with_trailing_whitespace_still_fails_closed_when_unterminated(self) -> None:
        text = "---\t\nemployer: Private Value\nmore body\n"

        structure = parse_note(text)

        self.assertIn("frontmatter_unsupported", structure.notes)
        self.assertNotIn("Private Value", body_without_frontmatter(text))

    def test_singular_alias_and_tag_keys_are_both_accepted(self) -> None:
        structure = parse_note("---\ntag: [one]\nalias: [Other Name]\n---\nbody\n")

        self.assertEqual(["one"], structure.tags)
        self.assertEqual(["Other Name"], structure.aliases)

    def test_alias_and_property_key_caps_are_enforced(self) -> None:
        aliases = "".join(f"  - Alias{index:04d}\n" for index in range(MAX_ALIASES + 5))
        keys = "".join(f"key{index:04d}: value\n" for index in range(MAX_PROPERTY_KEYS + 5))

        structure = parse_note(f"---\naliases:\n{aliases}{keys}---\nbody\n")

        self.assertEqual(MAX_ALIASES, len(structure.aliases))
        self.assertEqual(MAX_PROPERTY_KEYS, len(structure.property_keys))
        self.assertTrue(structure.truncated)

    def test_sanitize_token_scrubs_every_control_and_format_character(self) -> None:
        for raw in ("a\x1b[31mb", "a\x00b", "a\nb", "a\u202eb", "a\u200bb", "a\u2028b", "a\rb"):
            token = sanitize_token(raw)
            self.assertNotIn("\x1b", token)
            self.assertFalse(
                any(unicodedata.category(character) in {"Cc", "Cf", "Zl", "Zp"} for character in token),
                repr(raw),
            )

    def test_the_excerpt_body_never_contains_the_frontmatter_block(self) -> None:
        text = "---\nemployer: A Very Private Employer Name\n---\nThe visible body.\n"

        body = body_without_frontmatter(text)

        self.assertNotIn("A Very Private Employer Name", body)
        self.assertNotIn("employer", body)
        self.assertIn("The visible body.", body)


class ObsidianReplayTests(unittest.TestCase):
    def setUp(self) -> None:
        self.vault = VaultFixture()
        self.addCleanup(self.vault.close)

    def test_repeat_scan_is_a_no_op(self) -> None:
        self.vault.write("Note.md", "stable body\n")
        first = self.vault.scan()

        second = self.vault.scan(previous=first)

        self.assertEqual(["add"], kinds(first))
        self.assertEqual([], kinds(second))
        self.assertEqual(first.snapshot.snapshot_id, second.snapshot.snapshot_id)

    def test_an_edit_is_a_modify_and_a_rename_is_a_move(self) -> None:
        self.vault.write("Note.md", "first body\n")
        first = self.vault.scan()
        subject = first.snapshot.items[0].locator.subject_id

        self.vault.write("Note.md", "second body\n")
        edited = self.vault.scan(previous=first)
        self.assertEqual(["modify"], kinds(edited))

        self.vault.move("Note.md", "archive/Renamed.md")
        renamed = self.vault.scan(previous=edited)

        self.assertEqual(["move"], kinds(renamed))
        self.assertEqual(subject, renamed.delta.operations[0].subject_id)
        fields = fields_by_path(renamed)["archive/Renamed.md"]
        self.assertEqual("Renamed", fields["note_name"])
        self.assertEqual("archive", fields["folder_path"])

    def test_a_deleted_note_becomes_a_tombstone_proposal(self) -> None:
        self.vault.write("Note.md", "body\n")
        first = self.vault.scan()
        (self.vault.root / "Note.md").unlink()

        removed = self.vault.scan(previous=first)

        self.assertEqual(["remove"], kinds(removed))
        self.assertEqual("tombstone_proposal", removed.delta.operations[0].effect)

    def test_a_structure_only_edit_still_updates_the_locator(self) -> None:
        self.vault.write("Note.md", "body\n")
        first = self.vault.scan()
        self.vault.write("Note.md", "body [[Added]]\n")

        second = self.vault.scan(previous=first)

        self.assertEqual(["modify"], kinds(second))
        self.assertEqual(["Added"], fields_by_path(second)["Note.md"]["outbound_links"])


if __name__ == "__main__":
    unittest.main()
