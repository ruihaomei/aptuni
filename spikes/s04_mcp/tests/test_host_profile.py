"""ADR-0013 evidence-only host-status and path-identity tests."""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from s04.host_profile import (
    ConfinementEvidence,
    EffectiveSettingsSnapshot,
    HostEvidenceStore,
    HostProfileSpec,
    PathIdentity,
    ProfileState,
    derive_status,
    evaluate_profile,
)


class HostStatusTests(unittest.TestCase):
    def test_status_domain_never_contains_confined(self) -> None:
        statuses = {
            derive_status(ProfileState.INSTALLED, evidence).confinement
            for evidence in (
                (),
                (ConfinementEvidence.PROBE_SKIPPED,),
                (ConfinementEvidence.CANARY_WRITE_SUCCEEDED,),
            )
        }
        self.assertEqual({"unverified", "not_in_effect"}, statuses)
        self.assertNotIn("confined", statuses)

    def test_positive_core_evidence_reports_not_in_effect(self) -> None:
        positive = (
            ConfinementEvidence.CANARY_WRITE_SUCCEEDED,
            ConfinementEvidence.SOCKET_CONNECT_SUCCEEDED,
            ConfinementEvidence.APPLE_EVENT_SUCCEEDED,
            ConfinementEvidence.ESCAPE_SETTING_VISIBLE,
            ConfinementEvidence.PROTECTED_PATH_WRITABLE,
            ConfinementEvidence.UNBUNDLED_ENTRY_VISIBLE,
            ConfinementEvidence.HOST_ESCALATION_AVAILABLE,
        )
        for item in positive:
            with self.subTest(item=item):
                status = derive_status(ProfileState.INSTALLED, (item,))
                self.assertEqual("not_in_effect", status.confinement)
                self.assertEqual((item.value,), status.reason_codes)

    def test_missing_or_drifted_profile_is_positive_unsafe_evidence(self) -> None:
        missing = derive_status(ProfileState.MISSING, ())
        drifted = derive_status(ProfileState.DRIFTED, ())
        self.assertEqual(("profile_missing",), missing.reason_codes)
        self.assertEqual("not_in_effect", missing.confinement)
        self.assertEqual(("profile_drifted",), drifted.reason_codes)
        self.assertEqual("not_in_effect", drifted.confinement)

    def test_unobservable_profile_stays_unverified(self) -> None:
        status = derive_status(ProfileState.UNVERIFIED, ())
        self.assertEqual("unverified", status.confinement)
        self.assertEqual(("effective_settings_unobservable",), status.reason_codes)

    def test_positive_unsafe_evidence_overrides_unobservable_profile_confinement(self) -> None:
        status = derive_status(
            ProfileState.UNVERIFIED,
            (ConfinementEvidence.CANARY_WRITE_SUCCEEDED,),
        )
        self.assertEqual(ProfileState.UNVERIFIED, status.profile)
        self.assertEqual("not_in_effect", status.confinement)
        self.assertEqual(
            ("canary_write_succeeded", "effective_settings_unobservable"),
            status.reason_codes,
        )

    def test_incomplete_misdirected_and_agent_only_evidence_stay_unverified(self) -> None:
        for item in (
            ConfinementEvidence.PROBE_SKIPPED,
            ConfinementEvidence.PROBE_MISDIRECTED,
            ConfinementEvidence.AGENT_REPORTED_ONLY,
            ConfinementEvidence.CLONE_PROVENANCE_UNOBSERVABLE,
        ):
            with self.subTest(item=item):
                status = derive_status(ProfileState.INSTALLED, (item,))
                self.assertEqual("unverified", status.confinement)
                self.assertEqual((item.value,), status.reason_codes)

    def test_untrusted_labels_environment_and_adapter_fields_cannot_elevate(self) -> None:
        forged = {
            "confinement": "confined",
            "PCC_CONFINEMENT": "confined",
            "adapter_status": "safe",
        }
        status = derive_status(
            ProfileState.INSTALLED,
            (),
            untrusted_metadata=forged,
        )
        self.assertEqual("unverified", status.confinement)
        self.assertEqual(("positive_evidence_absent",), status.reason_codes)

    def test_host_payload_contains_only_enum_and_fixed_reason_codes(self) -> None:
        marker = "/Users/synthetic/private/MARKER-9f8d"
        status = derive_status(
            ProfileState.INSTALLED,
            (ConfinementEvidence.CANARY_WRITE_SUCCEEDED,),
            untrusted_metadata={"path": marker},
        )
        payload = status.to_host_payload()
        self.assertEqual(
            {
                "profile": "installed",
                "confinement": "not_in_effect",
                "reason_codes": ["canary_write_succeeded"],
            },
            payload,
        )
        self.assertNotIn(marker, repr(payload))

    def test_evidence_is_bound_to_one_session_and_not_carried_forward(self) -> None:
        store = HostEvidenceStore()
        store.start("session-N", ProfileState.INSTALLED)
        store.record("session-N", ConfinementEvidence.CANARY_WRITE_SUCCEEDED)
        self.assertEqual("not_in_effect", store.status("session-N").confinement)

        store.start("session-N-plus-1", ProfileState.INSTALLED)
        next_status = store.status("session-N-plus-1")
        self.assertEqual("unverified", next_status.confinement)
        self.assertEqual(("positive_evidence_absent",), next_status.reason_codes)

    def test_unknown_session_fails_closed(self) -> None:
        store = HostEvidenceStore()
        with self.assertRaisesRegex(KeyError, "unknown_session"):
            store.status("forged")


class PathIdentityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.protected = self.root / "protected" / "vault.db"
        self.protected.parent.mkdir()
        self.protected.write_text("synthetic", encoding="utf-8")

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_symlink_and_hardlink_resolve_to_protected_identity(self) -> None:
        symlink = self.root / "writable" / "via-symlink"
        symlink.parent.mkdir()
        symlink.symlink_to(self.protected)
        hardlink = self.root / "writable" / "via-hardlink"
        os.link(self.protected, hardlink)

        identity = PathIdentity.capture(self.protected)
        self.assertTrue(identity.matches(symlink))
        self.assertTrue(identity.matches(hardlink))

    def test_independent_copy_is_not_misrepresented_as_same_identity(self) -> None:
        independent = self.root / "copy.db"
        independent.write_bytes(self.protected.read_bytes())
        identity = PathIdentity.capture(self.protected)
        self.assertFalse(identity.matches(independent))
        self.assertEqual(
            ConfinementEvidence.CLONE_PROVENANCE_UNOBSERVABLE,
            identity.unverifiable_copy_evidence(independent),
        )


class ProfileDiffTests(unittest.TestCase):
    def setUp(self) -> None:
        self.spec = HostProfileSpec(
            required={
                "sandbox.enabled": True,
                "sandbox.allowUnsandboxedCommands": False,
                "sandbox.filesystem.disabled": False,
                "sandbox.filesystem.allowWrite": (),
            },
            exact_sequences=frozenset({"sandbox.filesystem.allowWrite"}),
        )
        self.exact = {
            "sandbox": {
                "enabled": True,
                "allowUnsandboxedCommands": False,
                "filesystem": {"disabled": False, "allowWrite": []},
            }
        }

    def test_exact_effective_profile_is_installed(self) -> None:
        observation = evaluate_profile(
            self.spec, EffectiveSettingsSnapshot(self.exact, complete=True)
        )
        self.assertEqual(ProfileState.INSTALLED, observation.profile)
        self.assertEqual((), observation.reason_codes)

    def test_absent_settings_are_missing(self) -> None:
        observation = evaluate_profile(
            self.spec, EffectiveSettingsSnapshot(None, complete=True)
        )
        self.assertEqual(ProfileState.MISSING, observation.profile)
        self.assertEqual(("profile_missing",), observation.reason_codes)

    def test_unreadable_or_incomplete_settings_are_unverified(self) -> None:
        for snapshot in (
            EffectiveSettingsSnapshot(None, complete=False),
            EffectiveSettingsSnapshot(self.exact, complete=False),
        ):
            with self.subTest(snapshot=snapshot):
                observation = evaluate_profile(self.spec, snapshot)
                self.assertEqual(ProfileState.UNVERIFIED, observation.profile)
                self.assertEqual(
                    ("effective_settings_unobservable",), observation.reason_codes
                )

    def test_missing_overridden_and_appended_required_values_are_drift(self) -> None:
        cases = (
            {"sandbox": {"enabled": True}},
            {
                "sandbox": {
                    "enabled": True,
                    "allowUnsandboxedCommands": True,
                    "filesystem": {"disabled": False, "allowWrite": []},
                }
            },
            {
                "sandbox": {
                    "enabled": True,
                    "allowUnsandboxedCommands": False,
                    "filesystem": {"disabled": False, "allowWrite": ["/tmp/escape"]},
                }
            },
        )
        for effective in cases:
            with self.subTest(effective=effective):
                observation = evaluate_profile(
                    self.spec, EffectiveSettingsSnapshot(effective, complete=True)
                )
                self.assertEqual(ProfileState.DRIFTED, observation.profile)
                self.assertTrue(observation.reason_codes)

    def test_unknown_non_security_key_does_not_turn_profile_into_drift(self) -> None:
        effective = dict(self.exact)
        effective["ui"] = {"theme": "dark"}
        observation = evaluate_profile(
            self.spec, EffectiveSettingsSnapshot(effective, complete=True)
        )
        self.assertEqual(ProfileState.INSTALLED, observation.profile)

    def test_profile_reason_codes_are_content_free(self) -> None:
        effective = {
            "sandbox": {
                "enabled": True,
                "allowUnsandboxedCommands": False,
                "filesystem": {
                    "disabled": False,
                    "allowWrite": ["/Users/synthetic/private/MARKER"],
                },
            }
        }
        observation = evaluate_profile(
            self.spec, EffectiveSettingsSnapshot(effective, complete=True)
        )
        self.assertEqual(("required_value_mismatch",), observation.reason_codes)
        self.assertNotIn("MARKER", repr(observation))


if __name__ == "__main__":
    unittest.main()
