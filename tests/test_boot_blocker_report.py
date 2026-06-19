from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from harness.codes import BOOT_BLOCKER_REPORT_INVALID, OK
from harness.validators_impl import boot_blocker_report as validator_module
from harness.validators_impl.boot_blocker_report import BootBlockerReportValidator

KOZO_NEGATIVE_COVERAGE = {
    "boot_blocker_report": {
        "missing_report": "test_fails_when_boot_blocker_report_is_missing",
        "invalid_report_json": "test_fails_when_boot_blocker_report_json_is_invalid",
        "field_mismatch": "test_fails_when_boot_blocker_outcome_is_wrong",
        "missing_component": "test_fails_when_missing_component_is_absent",
        "missing_current_surface": "test_fails_when_current_surface_is_absent",
        "missing_non_claim": "test_fails_when_non_claim_is_absent",
        "missing_documentation_reference": "test_fails_when_documentation_reference_is_absent",
        "diagnostic_names_boot_blocker_field": "test_failure_diagnostic_names_boot_blocker_field",
    }
}


class BootBlockerReportValidatorTests(unittest.TestCase):
    def test_passes_when_boot_blocker_report_is_complete(self):
        result = self.validate_fixture()

        self.assertEqual(result.status, "pass")
        self.assertEqual(result.code, OK)

    def test_passes_when_iso_exists_and_qemu_serial_evidence_is_missing(self):
        result = self.validate_fixture(mutate_report_json=lambda _: qemu_serial_blocker_report())

        self.assertEqual(result.status, "pass")
        self.assertEqual(result.code, OK)

    def test_fails_when_boot_blocker_report_is_missing(self):
        self.assertEqual("boot_blocker_report", BootBlockerReportValidator.name)
        result = self.validate_fixture(remove_report=True)

        self.assertEqual(result.status, "fail")
        self.assert_boot_failure(result, "missing_report", "boot_blocker.report")

    def test_fails_when_boot_blocker_report_json_is_invalid(self):
        self.assertEqual("boot_blocker_report", BootBlockerReportValidator.name)
        result = self.validate_fixture(mutate_report=lambda _: "{not json")

        self.assertEqual(result.status, "fail")
        self.assert_boot_failure(result, "invalid_report_json", "boot_blocker.report_json")

    def test_fails_when_boot_blocker_outcome_is_wrong(self):
        self.assertEqual("boot_blocker_report", BootBlockerReportValidator.name)
        result = self.validate_fixture(mutate_report_json=lambda report: report | {"outcome": "pass"})

        self.assertEqual(result.status, "fail")
        self.assert_boot_failure(result, "field_mismatch", "boot_blocker.outcome")

    def test_fails_when_boot_blocker_category_is_unknown(self):
        self.assertEqual("boot_blocker_report", BootBlockerReportValidator.name)
        result = self.validate_fixture(mutate_report_json=lambda report: report | {"blocker_category": "unknown"})

        self.assertEqual(result.status, "fail")
        self.assert_boot_failure(result, "field_mismatch", "boot_blocker.blocker_category")

    def test_fails_when_missing_component_is_absent(self):
        self.assertEqual("boot_blocker_report", BootBlockerReportValidator.name)
        result = self.validate_fixture(
            mutate_report_json=lambda report: remove_list_value(report, "missing_components", "Limine executable")
        )

        self.assertEqual(result.status, "fail")
        self.assert_boot_failure(result, "missing_component", "boot_blocker.missing_components.Limine executable")

    def test_fails_when_current_surface_is_absent(self):
        self.assertEqual("boot_blocker_report", BootBlockerReportValidator.name)
        result = self.validate_fixture(
            mutate_report_json=lambda report: remove_list_value(
                report,
                "current_surfaces",
                "kernel/arch/x86_64/boot.asm defines a 64-bit _start symbol",
            )
        )

        self.assertEqual(result.status, "fail")
        self.assert_boot_failure(
            result,
            "missing_current_surface",
            "boot_blocker.current_surfaces.kernel/arch/x86_64/boot.asm defines a 64-bit _start symbol",
        )

    def test_fails_when_non_claim_is_absent(self):
        self.assertEqual("boot_blocker_report", BootBlockerReportValidator.name)
        result = self.validate_fixture(
            mutate_report_json=lambda report: remove_list_value(report, "cannot_claim", "QEMU boot")
        )

        self.assertEqual(result.status, "fail")
        self.assert_boot_failure(result, "missing_non_claim", "boot_blocker.cannot_claim.QEMU boot")

    def test_fails_when_documentation_reference_is_absent(self):
        self.assertEqual("boot_blocker_report", BootBlockerReportValidator.name)
        result = self.validate_fixture(
            mutate_boot_doc=lambda text: text.replace("missing_iso_generation_tooling", "missing")
        )

        self.assertEqual(result.status, "fail")
        self.assert_boot_failure(
            result,
            "missing_documentation_reference",
            "docs/BOOT.md.missing_iso_generation_tooling",
        )

    def test_failure_diagnostic_names_boot_blocker_field(self):
        self.assertEqual("boot_blocker_report", BootBlockerReportValidator.name)
        result = self.validate_fixture(mutate_report_json=lambda report: report | {"validator": "other"})

        self.assertEqual(result.status, "fail")
        self.assertEqual(result.code, BOOT_BLOCKER_REPORT_INVALID)
        self.assertEqual(result.meta["reason"], "field_mismatch")
        self.assertEqual(result.meta["contract_field"], "boot_blocker.validator")

    def validate_fixture(
        self,
        *,
        remove_report: bool = False,
        mutate_report=None,
        mutate_report_json=None,
        mutate_boot_doc=None,
    ):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            report_path = root / "artifacts" / "runtime" / "boot_blocker_report.json"
            boot_doc_path = root / "docs" / "BOOT.md"
            blockers_doc_path = root / "docs" / "BOOT_BLOCKERS.md"
            runtime_doc_path = root / "docs" / "RUNTIME_EVIDENCE.md"
            release_doc_path = root / "docs" / "RELEASE_EVIDENCE.md"
            write_fixture_files(root)

            if remove_report:
                report_path.unlink()
            elif mutate_report is not None:
                report_path.write_text(mutate_report(report_path.read_text()))
            elif mutate_report_json is not None:
                report = json.loads(report_path.read_text())
                report_path.write_text(json.dumps(mutate_report_json(report), indent=2) + "\n")

            if mutate_boot_doc is not None:
                boot_doc_path.write_text(mutate_boot_doc(boot_doc_path.read_text()))

            old_paths = patch_validator_paths(
                report_path,
                boot_doc_path,
                blockers_doc_path,
                runtime_doc_path,
                release_doc_path,
            )
            try:
                return BootBlockerReportValidator().validate({})
            finally:
                restore_validator_paths(old_paths)

    def assert_boot_failure(self, result, reason: str, contract_field: str):
        self.assertEqual(result.code, BOOT_BLOCKER_REPORT_INVALID)
        self.assertEqual(result.meta["reason"], reason)
        self.assertEqual(result.meta["contract_field"], contract_field)


def write_fixture_files(root: Path) -> None:
    (root / "artifacts" / "runtime").mkdir(parents=True)
    (root / "docs").mkdir(parents=True)
    (root / "artifacts" / "runtime" / "boot_blocker_report.json").write_text(json.dumps(valid_report(), indent=2) + "\n")
    for path in (
        root / "docs" / "BOOT.md",
        root / "docs" / "BOOT_BLOCKERS.md",
        root / "docs" / "RUNTIME_EVIDENCE.md",
        root / "docs" / "RELEASE_EVIDENCE.md",
    ):
        path.write_text(valid_doc_text())


def valid_report() -> dict[str, object]:
    return {
        "version": 0,
            "phase": "v0.3.6",
        "outcome": "blocked",
        "evidence_type": "boot-blocker-report",
        "generated_by": "scripts/boot_blocker_report.sh",
        "validator": "boot_blocker_report",
        "blocker_category": "missing_iso_generation_tooling",
        "missing_components": [
            "Limine executable",
            "xorriso executable",
            "Limine bootloader artifacts",
            "bootable ISO artifact",
            "validated QEMU serial smoke execution",
        ],
        "current_surfaces": [
            "kernel/arch/x86_64/boot.asm defines a 64-bit _start symbol",
            "kernel/main.odin exports kernel_entry",
            "kernel/arch/x86_64/serial.odin initializes COM1 serial output",
            "linker/kernel.ld defines the kernel ELF layout",
            "boot/limine.conf defines the Limine boot entry",
            "scripts/build_boot_image.sh stages the boot image skeleton",
            "docs/BOOT_TOOLING.md documents Limine and xorriso acquisition paths",
            "scripts/build_boot_image.sh implements the Limine and xorriso ISO generation path",
            "scripts/build_boot_image.sh writes package metadata for the blocked ISO tooling attempt",
            "scripts/qemu_smoke.sh fails closed until kozo.iso exists",
            "scripts/runtime_smoke.sh proves runtime-adjacent object and symbol evidence",
        ],
        "cannot_claim": [
            "QEMU boot",
            "hardware trap execution",
            "Linux compatibility",
            "POSIX compatibility",
            "general userspace execution",
            "process model behavior",
            "VFS behavior",
            "scheduler maturity",
            "ELF loading",
            "file descriptor behavior",
            "production readiness",
        ],
        "next_required_fix": "Install or provide the documented Limine executable, Limine bootloader artifacts, and xorriso executable so scripts/build_boot_image.sh can create artifacts/runtime/boot_image/kozo.iso, then run scripts/qemu_smoke.sh to capture serial output before claiming QEMU boot evidence.",
        "inspected_paths": [
            "kernel/arch/x86_64/boot.asm",
            "kernel/main.odin",
            "kernel/arch/x86_64/serial.odin",
            "linker/kernel.ld",
            "boot/limine.conf",
            "docs/BOOT_TOOLING.md",
            "scripts/build_boot_image.sh",
            "artifacts/runtime/boot_image/package_metadata.json",
            "scripts/qemu_smoke.sh",
            "scripts/runtime_smoke.sh",
            "docs/RUNTIME_EVIDENCE.md",
        ],
    }


def qemu_serial_blocker_report() -> dict[str, object]:
    report = valid_report()
    report.update(
        {
            "blocker_category": "missing_qemu_serial_evidence",
            "missing_components": [
                "validated QEMU serial smoke execution",
            ],
            "current_surfaces": [
                value for value in report["current_surfaces"]
                if value != "scripts/build_boot_image.sh writes package metadata for the blocked ISO tooling attempt"
            ] + [
                "scripts/build_boot_image.sh produced artifacts/runtime/boot_image/kozo.iso",
                "artifacts/runtime/boot_image/package_metadata.json records packaged ISO metadata",
            ],
            "next_required_fix": "Run scripts/qemu_smoke.sh with QEMU available, capture serial output, and validate the expected KOZO marker before claiming QEMU boot evidence.",
        }
    )
    return report


def valid_doc_text() -> str:
    return "\n".join(
        (
            "artifacts/runtime/boot_blocker_report.json",
            "artifacts/runtime/boot_image/package_metadata.json",
            "artifacts/runtime/boot_image/kozo.iso",
            "scripts/boot_blocker_report.sh",
            "scripts/qemu_smoke.sh",
            "boot_blocker_report",
            "docs/BOOT_TOOLING.md",
            "missing_iso_generation_tooling",
            "missing_qemu_serial_evidence",
        )
    )


def remove_list_value(report: dict[str, object], key: str, value: str) -> dict[str, object]:
    report[key] = [item for item in report[key] if item != value]
    return report


def patch_validator_paths(report_path: Path, boot_doc_path: Path, blockers_doc_path: Path, runtime_doc_path: Path, release_doc_path: Path):
    old_paths = (
        validator_module._REPORT_PATH,
        validator_module._BOOT_DOC_PATH,
        validator_module._BOOT_BLOCKERS_PATH,
        validator_module._RUNTIME_EVIDENCE_PATH,
        validator_module._RELEASE_EVIDENCE_PATH,
    )
    validator_module._REPORT_PATH = report_path
    validator_module._BOOT_DOC_PATH = boot_doc_path
    validator_module._BOOT_BLOCKERS_PATH = blockers_doc_path
    validator_module._RUNTIME_EVIDENCE_PATH = runtime_doc_path
    validator_module._RELEASE_EVIDENCE_PATH = release_doc_path
    return old_paths


def restore_validator_paths(old_paths) -> None:
    (
        validator_module._REPORT_PATH,
        validator_module._BOOT_DOC_PATH,
        validator_module._BOOT_BLOCKERS_PATH,
        validator_module._RUNTIME_EVIDENCE_PATH,
        validator_module._RELEASE_EVIDENCE_PATH,
    ) = old_paths


if __name__ == "__main__":
    unittest.main()
