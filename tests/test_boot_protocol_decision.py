from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from harness.codes import BOOT_PROTOCOL_DECISION_INVALID, OK
from harness.validators_impl import boot_protocol_decision as validator_module
from harness.validators_impl.boot_protocol_decision import BootProtocolDecisionValidator

KOZO_NEGATIVE_COVERAGE = {
    "boot_protocol_decision": {
        "missing_adr": "test_fails_when_adr_is_missing",
        "wrong_protocol": "test_fails_when_selected_protocol_is_not_limine",
        "missing_alternative": "test_fails_when_required_alternative_is_missing",
        "missing_non_goal": "test_fails_when_required_non_goal_is_missing",
        "missing_boot_blocker_reduced_statement": "test_fails_when_boot_blocker_reduced_statement_is_missing",
        "missing_v032_next_phase": "test_fails_when_v032_next_phase_is_missing",
        "diagnostic_names_decision_field": "test_failure_diagnostic_names_decision_field",
    }
}


class BootProtocolDecisionValidatorTests(unittest.TestCase):
    def test_passes_when_boot_protocol_decision_is_complete(self):
        result = self.validate_fixture()

        self.assertEqual(result.status, "pass")
        self.assertEqual(result.code, OK)

    def test_fails_when_adr_is_missing(self):
        self.assertEqual("boot_protocol_decision", BootProtocolDecisionValidator.name)
        result = self.validate_fixture(remove_adr=True)

        self.assertEqual(result.status, "fail")
        self.assert_decision_failure(result, "missing_document", "docs/decisions/0001-boot-protocol.md")

    def test_fails_when_selected_protocol_is_not_limine(self):
        self.assertEqual("boot_protocol_decision", BootProtocolDecisionValidator.name)
        result = self.validate_fixture(mutate_adr=lambda text: text.replace("Selected protocol: Limine", "Selected protocol: Multiboot2"))

        self.assertEqual(result.status, "fail")
        self.assert_decision_failure(result, "missing_selected_protocol", "docs/decisions/0001-boot-protocol.md.selected_protocol")

    def test_fails_when_required_alternative_is_missing(self):
        self.assertEqual("boot_protocol_decision", BootProtocolDecisionValidator.name)
        result = self.validate_fixture(mutate_adr=lambda text: text.replace("## UEFI-first", "## Firmware-first"))

        self.assertEqual(result.status, "fail")
        self.assert_decision_failure(result, "missing_uefi_first_alternative", "docs/decisions/0001-boot-protocol.md.uefi_first_alternative")

    def test_fails_when_required_non_goal_is_missing(self):
        self.assertEqual("boot_protocol_decision", BootProtocolDecisionValidator.name)
        result = self.validate_fixture(mutate_adr=lambda text: text.replace("This decision does not claim Linux compatibility.", ""))

        self.assertEqual(result.status, "fail")
        self.assert_decision_failure(result, "missing_linux_non_goal", "docs/decisions/0001-boot-protocol.md.linux_non_goal")

    def test_fails_when_boot_blocker_reduced_statement_is_missing(self):
        self.assertEqual("boot_protocol_decision", BootProtocolDecisionValidator.name)
        result = self.validate_fixture(mutate_boot_blockers=lambda text: text.replace("The previous `missing_boot_protocol_and_image_packaging` blocker is reduced.", ""))

        self.assertEqual(result.status, "fail")
        self.assert_decision_failure(result, "missing_boot_blockers_reduced", "docs/BOOT_BLOCKERS.md.boot_blockers_reduced")

    def test_fails_when_v032_next_phase_is_missing(self):
        self.assertEqual("boot_protocol_decision", BootProtocolDecisionValidator.name)
        result = self.validate_fixture(mutate_phasemap=lambda text: text.replace("v0.3.2", "v0.3.x"))

        self.assertEqual(result.status, "fail")
        self.assert_decision_failure(result, "missing_phasemap_next_phase", "PHASEMAP.md.phasemap_next_phase")

    def test_failure_diagnostic_names_decision_field(self):
        self.assertEqual("boot_protocol_decision", BootProtocolDecisionValidator.name)
        result = self.validate_fixture(mutate_boot_doc=lambda text: text.replace("Selected boot protocol: Limine", "Selected boot protocol: unknown"))

        self.assertEqual(result.status, "fail")
        self.assertEqual(result.code, BOOT_PROTOCOL_DECISION_INVALID)
        self.assertEqual(result.meta["reason"], "missing_boot_doc_references_protocol")
        self.assertEqual(result.meta["contract_field"], "docs/BOOT.md.boot_doc_references_protocol")

    def validate_fixture(
        self,
        *,
        remove_adr: bool = False,
        mutate_adr=None,
        mutate_boot_doc=None,
        mutate_boot_blockers=None,
        mutate_phasemap=None,
    ):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = write_fixture_files(root)

            if remove_adr:
                paths["adr"].unlink()
            if mutate_adr is not None:
                paths["adr"].write_text(mutate_adr(paths["adr"].read_text()))
            if mutate_boot_doc is not None:
                paths["boot"].write_text(mutate_boot_doc(paths["boot"].read_text()))
            if mutate_boot_blockers is not None:
                paths["blockers"].write_text(mutate_boot_blockers(paths["blockers"].read_text()))
            if mutate_phasemap is not None:
                paths["phasemap"].write_text(mutate_phasemap(paths["phasemap"].read_text()))

            old_paths = patch_validator_paths(paths)
            try:
                return BootProtocolDecisionValidator().validate({})
            finally:
                restore_validator_paths(old_paths)

    def assert_decision_failure(self, result, reason: str, contract_field: str):
        self.assertEqual(result.code, BOOT_PROTOCOL_DECISION_INVALID)
        self.assertEqual(result.meta["reason"], reason)
        self.assertEqual(result.meta["contract_field"], contract_field)


def write_fixture_files(root: Path) -> dict[str, Path]:
    decisions = root / "docs" / "decisions"
    decisions.mkdir(parents=True)
    docs = root / "docs"
    adr = decisions / "0001-boot-protocol.md"
    boot_protocol = docs / "BOOT_PROTOCOL.md"
    boot = docs / "BOOT.md"
    blockers = docs / "BOOT_BLOCKERS.md"
    phasemap = root / "PHASEMAP.md"
    roadmap = root / "ROADMAP.md"

    adr.write_text(valid_adr_text())
    boot_protocol.write_text(valid_boot_protocol_text())
    boot.write_text("Selected boot protocol: Limine\nRemaining blocker: `missing_iso_generation_tooling`.\n")
    blockers.write_text("Boot protocol decision: complete.\nThe previous `missing_boot_protocol_and_image_packaging` blocker is reduced.\n")
    phasemap.write_text("v0.3.2 Boot Image Skeleton\n")
    roadmap.write_text("v0.3.2 Boot Image Skeleton QEMU serial smoke\n")
    return {
        "adr": adr,
        "boot_protocol": boot_protocol,
        "boot": boot,
        "blockers": blockers,
        "phasemap": phasemap,
        "roadmap": roadmap,
    }


def valid_adr_text() -> str:
    return "\n".join(
        (
            "Status: Accepted",
            "Selected protocol: Limine",
            "Target architecture: x86_64",
            "Initial boot target: QEMU serial smoke",
            "## Limine",
            "## Multiboot2",
            "## UEFI-first",
            "## Raw custom loader",
            "This decision does not claim QEMU boot.",
            "This decision does not claim Linux compatibility.",
            "This decision does not claim production readiness.",
        )
    )


def valid_boot_protocol_text() -> str:
    return "Selected protocol: Limine\nv0.3.2 Boot Image Skeleton\n"


def patch_validator_paths(paths: dict[str, Path]):
    old_paths = (
        validator_module._ADR_PATH,
        validator_module._BOOT_PROTOCOL_PATH,
        validator_module._BOOT_DOC_PATH,
        validator_module._BOOT_BLOCKERS_PATH,
        validator_module._PHASEMAP_PATH,
        validator_module._ROADMAP_PATH,
    )
    validator_module._ADR_PATH = paths["adr"]
    validator_module._BOOT_PROTOCOL_PATH = paths["boot_protocol"]
    validator_module._BOOT_DOC_PATH = paths["boot"]
    validator_module._BOOT_BLOCKERS_PATH = paths["blockers"]
    validator_module._PHASEMAP_PATH = paths["phasemap"]
    validator_module._ROADMAP_PATH = paths["roadmap"]
    return old_paths


def restore_validator_paths(old_paths) -> None:
    (
        validator_module._ADR_PATH,
        validator_module._BOOT_PROTOCOL_PATH,
        validator_module._BOOT_DOC_PATH,
        validator_module._BOOT_BLOCKERS_PATH,
        validator_module._PHASEMAP_PATH,
        validator_module._ROADMAP_PATH,
    ) = old_paths


if __name__ == "__main__":
    unittest.main()
