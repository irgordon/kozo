from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from harness.codes import FIXED_USER_MAPPING_FOUNDATION_EVIDENCE_INVALID, OK
from harness.runtime_evidence_taxonomy import get_smoke_marker_order
from harness.validators_impl import fixed_user_mapping_foundation_evidence as validator_module
from harness.validators_impl.fixed_user_mapping_foundation_evidence import (
    FixedUserMappingFoundationEvidenceValidator,
)

KOZO_NEGATIVE_COVERAGE = {
    "fixed_user_mapping_foundation_evidence": {
        "mapping_sequence_invalid": "test_fails_when_runtime_entry_precedes_survival",
        "page_tables_not_zeroed": "test_fails_when_page_tables_are_not_zeroed",
        "missing_upper_level_user": "test_fails_when_pml4_user_bit_is_missing",
        "nx_policy_missing": "test_fails_when_nx_policy_is_missing",
        "cr3_readback_missing": "test_fails_when_cr3_readback_is_missing",
        "software_walk_invalid": "test_fails_when_effective_user_check_is_missing",
        "survival_probe_invalid": "test_fails_when_user_data_restore_is_missing",
        "privilege_transition_present": "test_fails_when_ring3_transition_is_present",
        "linker_geometry_invalid": "test_fails_when_linker_page_assertion_is_missing",
        "missing_elf_symbol": "test_fails_when_user_stack_symbol_is_missing",
        "elf_geometry_invalid": "test_fails_when_user_code_geometry_is_wrong",
        "missing_elf_evidence": "test_fails_when_cr3_write_is_missing_from_elf",
        "metadata_log_mismatch": "test_fails_when_metadata_omits_mapping_marker",
        "runtime_marker_missing": "test_fails_when_serial_marker_is_missing",
        "diagnostic_names_field": "test_failure_diagnostic_names_field",
    }
}


class FixedUserMappingFoundationEvidenceTests(unittest.TestCase):
    def test_valid_evidence_passes(self):
        result = self.validate_fixture()
        self.assertEqual(result.status, "pass")
        self.assertEqual(result.code, OK)

    def test_fails_when_runtime_entry_precedes_survival(self):
        result = self.validate_fixture(
            mutate_boot=lambda text: text.replace(
                "    WRITE_COM1_MARKER user_mapping_survival_ok_marker, user_mapping_survival_ok_marker_end\n",
                "",
            )
        )
        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "mapping_sequence_invalid", "success_markers")

    def test_fails_when_page_tables_are_not_zeroed(self):
        result = self.validate_fixture(
            mutate_paging=lambda text: text.replace(
                "    mov ecx, GOVERNED_TABLE_BYTES / 8\n",
                "",
            )
        )
        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "page_tables_not_zeroed", "page_tables.zero_fill_required")

    def test_fails_when_pml4_user_bit_is_missing(self):
        result = self.validate_fixture(
            mutate_paging=lambda text: text.replace(
                "    or rax, PTE_PRESENT | PTE_WRITABLE | PTE_USER\n"
                "    mov [rel governed_pml4 + USER_PML4_INDEX * 8], rax\n",
                "    or rax, PTE_PRESENT | PTE_WRITABLE\n"
                "    mov [rel governed_pml4 + USER_PML4_INDEX * 8], rax\n",
            )
        )
        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "missing_upper_level_user", "permission_policy.user_levels")

    def test_fails_when_nx_policy_is_missing(self):
        result = self.validate_fixture(
            mutate_paging=lambda text: text.replace("    mov rdx, PTE_NX\n", "")
        )
        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "nx_policy_missing", "permission_policy")

    def test_fails_when_cr3_readback_is_missing(self):
        result = self.validate_fixture(
            mutate_paging=lambda text: text.replace("    mov rdx, cr3\n", "")
        )
        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "cr3_readback_missing", "activation")

    def test_fails_when_effective_user_check_is_missing(self):
        result = self.validate_fixture(
            mutate_paging=lambda text: text.replace("    test r8, PTE_USER\n", "")
        )
        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "software_walk_invalid", "software_walk")

    def test_fails_when_user_data_restore_is_missing(self):
        result = self.validate_fixture(
            mutate_paging=lambda text: text.replace("    mov qword [rdi], 0\n", "", 1)
        )
        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "survival_probe_invalid", "survival_probe")

    def test_fails_when_ring3_transition_is_present(self):
        result = self.validate_fixture(
            mutate_paging=lambda text: text.replace(
                "activate_fixed_user_mapping_root:\n",
                "activate_fixed_user_mapping_root:\n    iretq\n",
            )
        )
        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "privilege_transition_present", "non_goals.Ring 3 execution")

    def test_fails_when_linker_page_assertion_is_missing(self):
        result = self.validate_fixture(
            mutate_linker=lambda text: text.replace(
                "user probe code backing must be one page",
                "removed assertion",
            )
        )
        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "linker_geometry_invalid", "user_regions")

    def test_fails_when_user_stack_symbol_is_missing(self):
        result = self.validate_fixture(
            mutate_report=lambda report: mutate_report_symbol(report, "user_probe_stack")
        )
        self.assertEqual(result.status, "fail")
        self.assert_failure(
            result,
            "missing_elf_symbol",
            "kernel_elf_report.fixed_user_mapping_foundation.symbols.user_probe_stack",
        )

    def test_fails_when_user_code_geometry_is_wrong(self):
        def mutation(report):
            report["fixed_user_mapping_foundation"]["user_regions"]["code"]["size_bytes"] = 2048
            return report

        result = self.validate_fixture(mutate_report=mutation)
        self.assertEqual(result.status, "fail")
        self.assert_failure(
            result,
            "elf_geometry_invalid",
            "kernel_elf_report.fixed_user_mapping_foundation.user_regions.code",
        )

    def test_fails_when_cr3_write_is_missing_from_elf(self):
        def mutation(report):
            report["fixed_user_mapping_foundation"]["cr3_write_present"] = False
            return report

        result = self.validate_fixture(mutate_report=mutation)
        self.assertEqual(result.status, "fail")
        self.assert_failure(
            result,
            "missing_elf_evidence",
            "kernel_elf_report.fixed_user_mapping_foundation.cr3_write_present",
        )

    def test_fails_when_metadata_omits_mapping_marker(self):
        marker = "KOZO_USER_MAPPING_PERMISSIONS_OK"
        result = self.validate_fixture(
            mutate_metadata=lambda metadata: metadata
            | {"observed_markers": [value for value in metadata["observed_markers"] if value != marker]}
        )
        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "metadata_log_mismatch", "qemu_smoke.observed_markers")

    def test_fails_when_serial_marker_is_missing(self):
        result = self.validate_fixture(
            mutate_serial=lambda text: text.replace("KOZO_USER_MAPPING_ACTIVATE_OK\n", "")
        )
        self.assertEqual(result.status, "fail")
        self.assert_failure(
            result,
            "runtime_marker_missing",
            "qemu_smoke.KOZO_USER_MAPPING_ACTIVATE_OK",
        )

    def test_failure_diagnostic_names_field(self):
        result = self.validate_fixture(
            mutate_paging=lambda text: text.replace("    mov rdx, cr3\n", "")
        )
        self.assertEqual(result.code, FIXED_USER_MAPPING_FOUNDATION_EVIDENCE_INVALID)
        self.assertIn("reason", result.meta)
        self.assertIn("contract_field", result.meta)

    def validate_fixture(
        self,
        *,
        mutate_boot=None,
        mutate_paging=None,
        mutate_linker=None,
        mutate_report=None,
        mutate_metadata=None,
        mutate_serial=None,
    ):
        with tempfile.TemporaryDirectory() as directory:
            paths = write_fixture(
                Path(directory),
                mutate_boot,
                mutate_paging,
                mutate_linker,
                mutate_report,
                mutate_metadata,
                mutate_serial,
            )
            original = patch_paths(paths)
            try:
                return FixedUserMappingFoundationEvidenceValidator().validate({})
            finally:
                restore_paths(original)

    def assert_failure(self, result, reason, field):
        self.assertEqual(result.status, "fail")
        self.assertEqual(result.code, FIXED_USER_MAPPING_FOUNDATION_EVIDENCE_INVALID)
        self.assertEqual(result.meta["reason"], reason)
        self.assertEqual(result.meta["contract_field"], field)


def write_fixture(root, mutate_boot, mutate_paging, mutate_linker, mutate_report, mutate_metadata, mutate_serial):
    paths = {
        "contract": root / "contract.json",
        "boot": root / "boot.asm",
        "paging": root / "paging.asm",
        "linker": root / "kernel.ld",
        "report": root / "kernel_elf_report.json",
        "metadata": root / "qemu_smoke.metadata.json",
        "serial": root / "qemu_smoke.log",
    }
    paths["contract"].write_text(validator_module._CONTRACT_PATH.read_text())
    write_mutated(paths["boot"], validator_module._BOOT_PATH.read_text(), mutate_boot)
    write_mutated(paths["paging"], validator_module._PAGING_PATH.read_text(), mutate_paging)
    write_mutated(paths["linker"], validator_module._LINKER_PATH.read_text(), mutate_linker)
    report = valid_report()
    paths["report"].write_text(json.dumps(mutate_report(report) if mutate_report else report))
    markers = list(get_smoke_marker_order())
    metadata = {"outcome": "pass", "observed_markers": markers}
    paths["metadata"].write_text(json.dumps(mutate_metadata(metadata) if mutate_metadata else metadata))
    serial = "\n".join(markers) + "\n"
    paths["serial"].write_text(mutate_serial(serial) if mutate_serial else serial)
    return paths


def write_mutated(path, text, mutation):
    path.write_text(mutation(text) if mutation else text)


def valid_report():
    names = (
        *validator_module._TABLE_SYMBOLS,
        *validator_module._BACKING_SYMBOLS,
    )
    symbols = {
        name: {"present": True, "address": f"0xffffffff802{index:05x}"}
        for index, name in enumerate(names, start=1)
    }
    page_range = {"size_bytes": 7 * 4096, "start_aligned": True}
    user_range = {"size_bytes": 4096, "start_aligned": True}
    return {
        "fixed_user_mapping_foundation": {
            "symbols": symbols,
            "page_table_storage": page_range,
            "user_regions": {
                "code": dict(user_range),
                "data": dict(user_range),
                "stack": dict(user_range),
            },
            "pre_odin_call_order_valid": True,
            "cr3_read_present": True,
            "cr3_write_present": True,
            "software_walk_present": True,
            "paging_module_transition_instructions": [],
        }
    }


def mutate_report_symbol(report, symbol):
    report["fixed_user_mapping_foundation"]["symbols"][symbol]["present"] = False
    return report


def patch_paths(paths):
    names = {
        "_CONTRACT_PATH": "contract",
        "_BOOT_PATH": "boot",
        "_PAGING_PATH": "paging",
        "_LINKER_PATH": "linker",
        "_ELF_REPORT_PATH": "report",
        "_METADATA_PATH": "metadata",
        "_SERIAL_PATH": "serial",
    }
    original = {}
    for attribute, key in names.items():
        original[attribute] = getattr(validator_module, attribute)
        setattr(validator_module, attribute, paths[key])
    return original


def restore_paths(original):
    for attribute, value in original.items():
        setattr(validator_module, attribute, value)


if __name__ == "__main__":
    unittest.main()
