from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from harness.codes import KERNEL_LOADABILITY_INVALID, OK
from harness.validators_impl import kernel_loadability as validator_module
from harness.validators_impl.kernel_loadability import KernelLoadabilityValidator

KOZO_NEGATIVE_COVERAGE = {
    "kernel_loadability": {
        "missing_report": "test_fails_when_kernel_elf_report_is_missing",
        "invalid_report": "test_fails_when_kernel_elf_report_is_invalid_json",
        "missing_entry": "test_fails_when_entry_address_is_missing",
        "missing_load_segments": "test_fails_when_load_segments_are_missing",
        "wrong_architecture": "test_fails_when_architecture_is_wrong",
        "limine_lower_half_phdr": "test_fails_when_lower_half_phdr_boot_blocker_mismatches",
        "load_layout_mismatch": "test_fails_when_lower_half_layout_blocker_is_missing",
        "blocker_mismatch": "test_fails_when_boot_blocker_does_not_match_elf_issue",
        "diagnostic_names_field": "test_failure_diagnostic_names_field",
    }
}


class KernelLoadabilityValidatorTests(unittest.TestCase):
    def test_passes_when_kernel_elf_report_is_loadable(self):
        result = self.validate_fixture()

        self.assertEqual(result.status, "pass")
        self.assertEqual(result.code, OK)

    def test_fails_when_kernel_elf_report_is_missing(self):
        self.assertEqual("kernel_loadability", KernelLoadabilityValidator.name)
        result = self.validate_fixture(remove_report=True)

        self.assertEqual(result.status, "fail")
        self.assert_kernel_failure(result, "missing_report", "kernel_loadability.report")

    def test_fails_when_kernel_elf_report_is_invalid_json(self):
        self.assertEqual("kernel_loadability", KernelLoadabilityValidator.name)
        result = self.validate_fixture(mutate_report_text=lambda _: "{not json")

        self.assertEqual(result.status, "fail")
        self.assert_kernel_failure(result, "invalid_report", "kernel_loadability.report")

    def test_fails_when_entry_address_is_missing(self):
        self.assertEqual("kernel_loadability", KernelLoadabilityValidator.name)
        result = self.validate_fixture(mutate_report=lambda report: report | {"entry_address": ""})

        self.assertEqual(result.status, "fail")
        self.assert_kernel_failure(result, "missing_entry", "kernel_loadability.entry_address")

    def test_fails_when_load_segments_are_missing(self):
        self.assertEqual("kernel_loadability", KernelLoadabilityValidator.name)
        result = self.validate_fixture(
            mutate_report=lambda report: report | {
                "load_segments": [],
                "detected_issues": ["missing_load_segments"],
                "blocker_category": "missing_load_segments",
            },
            mutate_blocker=lambda blocker: blocker | {"blocker_category": "missing_load_segments"},
        )

        self.assertEqual(result.status, "fail")
        self.assert_kernel_failure(result, "missing_load_segments", "kernel_loadability.load_segments")

    def test_fails_when_architecture_is_wrong(self):
        self.assertEqual("kernel_loadability", KernelLoadabilityValidator.name)
        result = self.validate_fixture(mutate_report=lambda report: report | {"architecture": "aarch64"})

        self.assertEqual(result.status, "fail")
        self.assert_kernel_failure(result, "field_mismatch", "kernel_loadability.architecture")

    def test_accepts_lower_half_phdr_blocker_when_report_and_blocker_match(self):
        self.assertEqual("kernel_loadability", KernelLoadabilityValidator.name)
        result = self.validate_fixture(
            mutate_report=lambda _: lower_half_phdr_report(),
            mutate_blocker=lambda blocker: blocker | {"blocker_category": "limine_lower_half_phdr"},
        )

        self.assertEqual(result.status, "pass")
        self.assertEqual(result.code, OK)

    def test_fails_when_lower_half_layout_blocker_is_missing(self):
        self.assertEqual("kernel_loadability", KernelLoadabilityValidator.name)
        result = self.validate_fixture(
            mutate_report=lambda _: lower_half_phdr_report() | {"load_layout_blocker": "none"},
            mutate_blocker=lambda blocker: blocker | {"blocker_category": "limine_lower_half_phdr"},
        )

        self.assertEqual(result.status, "fail")
        self.assert_kernel_failure(result, "load_layout_mismatch", "kernel_loadability.load_layout_blocker")

    def test_fails_when_lower_half_phdr_boot_blocker_mismatches(self):
        self.assertEqual("kernel_loadability", KernelLoadabilityValidator.name)
        result = self.validate_fixture(mutate_report=lambda _: lower_half_phdr_report())

        self.assertEqual(result.status, "fail")
        self.assert_kernel_failure(result, "blocker_mismatch", "boot_blocker.blocker_category")

    def test_fails_when_mixed_load_layout_has_no_blocker(self):
        self.assertEqual("kernel_loadability", KernelLoadabilityValidator.name)
        result = self.validate_fixture(
            mutate_report=lambda report: mixed_load_layout_report(report) | {
                "all_load_segments_higher_half": True,
                "load_layout_blocker": "none",
            },
            mutate_blocker=lambda blocker: blocker | {"blocker_category": "limine_lower_half_phdr"},
        )

        self.assertEqual(result.status, "fail")
        self.assert_kernel_failure(
            result,
            "load_layout_mismatch",
            "kernel_loadability.all_load_segments_higher_half",
        )

    def test_fails_when_vma_lma_summary_is_missing(self):
        self.assertEqual("kernel_loadability", KernelLoadabilityValidator.name)
        result = self.validate_fixture(mutate_report=lambda report: report | {"virtual_base": ""})

        self.assertEqual(result.status, "fail")
        self.assert_kernel_failure(result, "missing_load_layout", "kernel_loadability.virtual_base")

    def test_fails_when_higher_half_summary_mismatches(self):
        self.assertEqual("kernel_loadability", KernelLoadabilityValidator.name)
        result = self.validate_fixture(mutate_report=lambda report: report | {"all_load_segments_higher_half": False})

        self.assertEqual(result.status, "fail")
        self.assert_kernel_failure(
            result,
            "load_layout_mismatch",
            "kernel_loadability.all_load_segments_higher_half",
        )

    def test_fails_when_boot_blocker_does_not_match_elf_issue(self):
        self.assertEqual("kernel_loadability", KernelLoadabilityValidator.name)
        result = self.validate_fixture(
            mutate_report=lambda report: report | {
                "detected_issues": ["linker_output_invalid"],
                "blocker_category": "linker_output_invalid",
            }
        )

        self.assertEqual(result.status, "fail")
        self.assert_kernel_failure(result, "blocker_mismatch", "boot_blocker.blocker_category")

    def test_accepts_clean_elf_with_next_qemu_blocker(self):
        self.assertEqual("kernel_loadability", KernelLoadabilityValidator.name)
        result = self.validate_fixture(mutate_blocker=lambda blocker: blocker | {"blocker_category": "serial_not_initialized"})

        self.assertEqual(result.status, "pass")
        self.assertEqual(result.code, OK)

    def test_fails_when_clean_elf_has_stale_lower_half_blocker(self):
        self.assertEqual("kernel_loadability", KernelLoadabilityValidator.name)
        result = self.validate_fixture(mutate_blocker=lambda blocker: blocker | {"blocker_category": "limine_lower_half_phdr"})

        self.assertEqual(result.status, "fail")
        self.assert_kernel_failure(result, "blocker_mismatch", "boot_blocker.blocker_category")

    def test_failure_diagnostic_names_field(self):
        self.assertEqual("kernel_loadability", KernelLoadabilityValidator.name)
        result = self.validate_fixture(mutate_report=lambda report: report | {"generated_by": "manual"})

        self.assertEqual(result.status, "fail")
        self.assertEqual(result.code, KERNEL_LOADABILITY_INVALID)
        self.assertEqual(result.meta["reason"], "field_mismatch")
        self.assertEqual(result.meta["contract_field"], "kernel_loadability.generated_by")

    def validate_fixture(
        self,
        *,
        remove_report: bool = False,
        mutate_report=None,
        mutate_report_text=None,
        mutate_blocker=None,
    ):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = write_fixture_files(root)

            if remove_report:
                paths["report"].unlink()
            elif mutate_report is not None:
                report = json.loads(paths["report"].read_text())
                paths["report"].write_text(json.dumps(mutate_report(report), indent=2) + "\n")
            elif mutate_report_text is not None:
                paths["report"].write_text(mutate_report_text(paths["report"].read_text()))

            if mutate_blocker is not None:
                blocker = json.loads(paths["blocker"].read_text())
                paths["blocker"].write_text(json.dumps(mutate_blocker(blocker), indent=2) + "\n")

            old_paths = patch_validator_paths(paths)
            try:
                return KernelLoadabilityValidator().validate({})
            finally:
                restore_validator_paths(old_paths)

    def assert_kernel_failure(self, result, reason: str, contract_field: str):
        self.assertEqual(result.status, "fail")
        self.assertEqual(result.code, KERNEL_LOADABILITY_INVALID)
        self.assertEqual(result.meta["reason"], reason)
        self.assertEqual(result.meta["contract_field"], contract_field)


def write_fixture_files(root: Path) -> dict[str, Path]:
    paths = {
        "report": root / "artifacts" / "runtime" / "kernel_elf_report.json",
        "blocker": root / "artifacts" / "runtime" / "boot_blocker_report.json",
    }
    for path in paths.values():
        path.parent.mkdir(parents=True, exist_ok=True)
    paths["report"].write_text(json.dumps(valid_report(), indent=2) + "\n")
    paths["blocker"].write_text(json.dumps(valid_blocker(), indent=2) + "\n")
    return paths


def valid_report() -> dict[str, object]:
    return {
        "version": 0,
        "phase": "v0.4.2",
        "evidence_type": "kernel-elf-loadability",
        "generated_by": "scripts/kernel_elf_report.py",
        "kernel_elf": "artifacts/runtime/boot_image/image-root/boot/kozo/kozo-kernel.elf",
        "linker_script": "linker/kernel.ld",
        "architecture": "x86_64",
        "elf_class": "ELF64",
        "endianness": "little",
        "elf_type": "EXEC",
        "entry_symbol": "_start",
        "entry_address": "0xffffffff80200000",
        "entry_symbol_address": "0xffffffff80200000",
        "entry_symbol_matches_entry": True,
        "entry_is_lower_half": False,
        "entry_address_class": "higher-half",
        "program_header_count": 6,
        "section_count": 13,
        "load_segments": [
            {
                "type": "PT_LOAD",
                "flags": "r-x",
                "offset": "0x1000",
                "virtual_address": "0xffffffff80200000",
                "physical_address": "0x200000",
                "file_size": "0x2f82",
                "memory_size": "0x2f82",
                "alignment": "0x1000",
            },
        ],
        "virtual_base": "0xffffffff80200000",
        "physical_load_base": "0x200000",
        "minimum_load_virtual_address": "0xffffffff80200000",
        "minimum_load_physical_address": "0x200000",
        "has_lower_half_load_segment": False,
        "all_load_segments_higher_half": True,
        "load_layout_blocker": "none",
        "detected_issues": [],
        "blocker_category": "none",
        "proves": [
            "kernel ELF is an x86_64 executable",
            "kernel ELF has an entry point matching _start",
            "kernel ELF has PT_LOAD segments",
            "kernel ELF load layout was inspected for Limine lower-half PHDR rejection",
        ],
        "does_not_prove": [
            "QEMU boot",
            "kernel entry execution",
            "serial initialization",
            "hardware trap execution",
            "Linux compatibility",
            "POSIX compatibility",
            "general userspace execution",
            "process model behavior",
            "VFS behavior",
            "scheduler maturity",
            "ELF loading by Limine",
            "file descriptor behavior",
            "production readiness",
        ],
    }


def lower_half_phdr_report() -> dict[str, object]:
    report = valid_report()
    report.update(
        {
            "entry_address": "0x200000",
            "entry_symbol_address": "0x200000",
            "entry_is_lower_half": True,
            "entry_address_class": "lower-half",
            "load_segments": [
                {
                    "type": "PT_LOAD",
                    "flags": "r-x",
                    "offset": "0x1000",
                    "virtual_address": "0x200000",
                    "physical_address": "0x200000",
                    "file_size": "0x2f82",
                    "memory_size": "0x2f82",
                    "alignment": "0x1000",
                },
            ],
            "virtual_base": "0x200000",
            "physical_load_base": "0x200000",
            "minimum_load_virtual_address": "0x200000",
            "minimum_load_physical_address": "0x200000",
            "has_lower_half_load_segment": True,
            "all_load_segments_higher_half": False,
            "load_layout_blocker": "limine_lower_half_phdr",
            "detected_issues": ["limine_lower_half_phdr"],
            "blocker_category": "limine_lower_half_phdr",
            "proves": ["kernel ELF loadability was inspected"],
        }
    )
    return report


def mixed_load_layout_report(report: dict[str, object]) -> dict[str, object]:
    segments = [
        {
            "type": "PT_LOAD",
            "flags": "r-x",
            "offset": "0x1000",
            "virtual_address": "0xffffffff80200000",
            "physical_address": "0x200000",
            "file_size": "0x2f82",
            "memory_size": "0x2f82",
            "alignment": "0x1000",
        },
        {
            "type": "PT_LOAD",
            "flags": "rw-",
            "offset": "0x4000",
            "virtual_address": "0x204000",
            "physical_address": "0x204000",
            "file_size": "0x1000",
            "memory_size": "0x1000",
            "alignment": "0x1000",
        },
    ]
    return report | {
        "load_segments": segments,
        "virtual_base": "0x204000",
        "physical_load_base": "0x200000",
        "minimum_load_virtual_address": "0x204000",
        "minimum_load_physical_address": "0x200000",
        "has_lower_half_load_segment": True,
        "all_load_segments_higher_half": False,
        "load_layout_blocker": "limine_lower_half_phdr",
        "detected_issues": ["limine_lower_half_phdr"],
        "blocker_category": "limine_lower_half_phdr",
    }


def valid_blocker() -> dict[str, object]:
    return {
        "phase": "v0.4.2",
        "blocker_category": "kernel_not_loaded",
    }


def patch_validator_paths(paths: dict[str, Path]):
    old_paths = (
        validator_module._REPORT_PATH,
        validator_module._BOOT_BLOCKER_REPORT_PATH,
    )
    validator_module._REPORT_PATH = paths["report"]
    validator_module._BOOT_BLOCKER_REPORT_PATH = paths["blocker"]
    return old_paths


def restore_validator_paths(old_paths) -> None:
    (
        validator_module._REPORT_PATH,
        validator_module._BOOT_BLOCKER_REPORT_PATH,
    ) = old_paths


if __name__ == "__main__":
    unittest.main()
