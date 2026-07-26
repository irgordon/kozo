from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from harness.codes import FIXED_USER_REQUEST_BOUNDARY_EVIDENCE_INVALID, OK
from harness.runtime_evidence_taxonomy import get_smoke_marker_order
from harness.validators_impl import fixed_user_request_boundary_evidence as validator_module
from harness.validators_impl.fixed_user_request_boundary_evidence import (
    FixedUserRequestBoundaryEvidenceValidator,
)

KOZO_NEGATIVE_COVERAGE = {
    "fixed_user_request_boundary_evidence": {
        "layout_geometry_invalid": "test_fails_when_request_address_changes",
        "ring3_request_invalid": "test_fails_when_ring3_request_field_is_missing",
        "handler_order_invalid": "test_fails_when_frame_validation_is_missing",
        "span_validation_invalid": "test_fails_when_overflow_check_is_missing",
        "copy_in_invalid": "test_fails_when_copy_in_is_partial",
        "copy_out_invalid": "test_fails_when_copy_out_is_partial",
        "response_readback_invalid": "test_fails_when_response_readback_validation_is_missing",
        "request_validation_invalid": "test_fails_when_request_field_validation_is_missing",
        "service_invalid": "test_fails_when_service_token_operation_changes",
        "buffer_clear_invalid": "test_fails_when_clear_readback_is_missing",
        "failure_emits_success": "test_fails_when_failure_path_contains_success_marker",
        "failure_halt_missing": "test_fails_when_boot_failure_does_not_halt",
        "linker_geometry_invalid": "test_fails_when_shadow_assertion_is_missing",
        "missing_elf_symbol": "test_fails_when_request_shadow_symbol_is_missing",
        "elf_geometry_invalid": "test_fails_when_response_shadow_size_is_wrong",
        "missing_elf_evidence": "test_fails_when_handler_order_is_missing_from_elf",
        "missing_elf_copy_evidence": "test_fails_when_elf_copy_count_is_short",
        "missing_elf_clear_evidence": "test_fails_when_elf_clear_count_is_short",
        "prohibited_instruction_present": "test_fails_when_syscall_is_present",
        "runtime_outcome_invalid": "test_fails_when_qemu_is_blocked",
        "metadata_log_mismatch": "test_fails_when_metadata_omits_boundary_marker",
        "runtime_marker_missing": "test_fails_when_serial_omits_boundary_marker",
        "runtime_marker_duplicate": "test_fails_when_boundary_marker_is_duplicated",
        "diagnostic_names_field": "test_failure_diagnostic_names_field",
    }
}


class FixedUserRequestBoundaryEvidenceTests(unittest.TestCase):
    def test_valid_evidence_passes(self):
        result = self.validate_fixture()
        self.assertEqual((result.status, result.code), ("pass", OK))

    def test_fails_when_request_address_changes(self):
        mutation = lambda text: text.replace(
            "%define FIXED_USER_REQUEST_VA (USER_PROBE_DATA_VA + 0x000)",
            "%define FIXED_USER_REQUEST_VA (USER_PROBE_DATA_VA + 0x008)",
        )
        result = self.validate_fixture(mutate_layout=mutation)
        self.assertEqual(result.status, "fail")
        self.assert_reason(result, "layout_geometry_invalid")

    def test_fails_when_ring3_request_field_is_missing(self):
        mutation = lambda text: text.replace("    mov dword [rdi + 36], 0\n", "")
        result = self.validate_fixture(mutate_privilege=mutation)
        self.assertEqual(result.status, "fail")
        self.assert_reason(result, "ring3_request_invalid")

    def test_fails_when_frame_validation_is_missing(self):
        mutation = lambda text: text.replace("    call validate_ring3_return_frame\n", "")
        result = self.validate_fixture(mutate_privilege=mutation)
        self.assertEqual(result.status, "fail")
        self.assert_reason(result, "handler_order_invalid")

    def test_fails_when_overflow_check_is_missing(self):
        mutation = lambda text: text.replace("    jc .invalid\n", "", 1)
        result = self.validate_fixture(mutate_privilege=mutation)
        self.assertEqual(result.status, "fail")
        self.assert_reason(result, "span_validation_invalid")

    def test_fails_when_copy_in_is_partial(self):
        mutation = lambda text: text.replace("    mov [rdi + 32], rax\n", "", 1)
        result = self.validate_fixture(mutate_privilege=mutation)
        self.assertEqual(result.status, "fail")
        self.assert_reason(result, "copy_in_invalid")

    def test_fails_when_copy_out_is_partial(self):
        mutation = lambda text: text.replace("    mov [rdi + 40], rax\n", "", 1)
        result = self.validate_fixture(mutate_privilege=mutation)
        self.assertEqual(result.status, "fail")
        self.assert_reason(result, "copy_out_invalid")

    def test_fails_when_response_readback_validation_is_missing(self):
        mutation = lambda text: text.replace("    call fixed_user_response_fields_are_valid\n", "", 2)
        result = self.validate_fixture(mutate_privilege=mutation)
        self.assertEqual(result.status, "fail")
        self.assert_reason(result, "response_readback_invalid")

    def test_fails_when_request_field_validation_is_missing(self):
        mutation = lambda text: text.replace(
            "    cmp dword [rel fixed_user_request_shadow + 36], 0\n",
            "",
        )
        result = self.validate_fixture(mutate_privilege=mutation)
        self.assertEqual(result.status, "fail")
        self.assert_reason(result, "request_validation_invalid")

    def test_fails_when_service_token_operation_changes(self):
        mutation = lambda text: text.replace("    xor rax, rdx\n", "    or rax, rdx\n", 1)
        result = self.validate_fixture(mutate_privilege=mutation)
        self.assertEqual(result.status, "fail")
        self.assert_reason(result, "service_invalid")

    def test_fails_when_clear_readback_is_missing(self):
        mutation = lambda text: text.replace("    call fixed_user_buffers_are_zero\n", "", 1)
        result = self.validate_fixture(mutate_privilege=mutation)
        self.assertEqual(result.status, "fail")
        self.assert_reason(result, "buffer_clear_invalid")

    def test_fails_when_failure_path_contains_success_marker(self):
        mutation = lambda text: text.replace(
            "privilege_return_failure:\n",
            "privilege_return_failure:\n    ; KOZO_FIXED_USER_REQUEST_OK\n",
        )
        result = self.validate_fixture(mutate_privilege=mutation)
        self.assertEqual(result.status, "fail")
        self.assert_reason(result, "failure_emits_success")

    def test_fails_when_boot_failure_does_not_halt(self):
        mutation = lambda text: text.replace("    jnz .halt\n", "")
        result = self.validate_fixture(mutate_boot=mutation)
        self.assertEqual(result.status, "fail")
        self.assert_reason(result, "failure_halt_missing")

    def test_fails_when_shadow_assertion_is_missing(self):
        mutation = lambda text: text.replace(
            "fixed user request shadow must be exactly 40 bytes",
            "removed",
        )
        result = self.validate_fixture(mutate_linker=mutation)
        self.assertEqual(result.status, "fail")
        self.assert_reason(result, "linker_geometry_invalid")

    def test_fails_when_request_shadow_symbol_is_missing(self):
        mutation = lambda report: remove_symbol(report, "fixed_user_request_shadow")
        result = self.validate_fixture(mutate_report=mutation)
        self.assertEqual(result.status, "fail")
        self.assert_reason(result, "missing_elf_symbol")

    def test_fails_when_response_shadow_size_is_wrong(self):
        def mutation(report):
            report["fixed_user_request_boundary"]["response_shadow"]["size_bytes"] = 40
            return report
        result = self.validate_fixture(mutate_report=mutation)
        self.assertEqual(result.status, "fail")
        self.assert_reason(result, "elf_geometry_invalid")

    def test_fails_when_handler_order_is_missing_from_elf(self):
        def mutation(report):
            report["fixed_user_request_boundary"]["handler_call_order_valid"] = False
            return report
        result = self.validate_fixture(mutate_report=mutation)
        self.assertEqual(result.status, "fail")
        self.assert_reason(result, "missing_elf_evidence")

    def test_fails_when_elf_copy_count_is_short(self):
        def mutation(report):
            report["fixed_user_request_boundary"]["copy_in_memory_move_count"] = 8
            return report
        result = self.validate_fixture(mutate_report=mutation)
        self.assertEqual(result.status, "fail")
        self.assert_reason(result, "missing_elf_copy_evidence")

    def test_fails_when_elf_clear_count_is_short(self):
        def mutation(report):
            report["fixed_user_request_boundary"]["clear_stosq_count"] = 4
            return report
        result = self.validate_fixture(mutate_report=mutation)
        self.assertEqual(result.status, "fail")
        self.assert_reason(result, "missing_elf_clear_evidence")

    def test_fails_when_syscall_is_present(self):
        def mutation(report):
            report["fixed_user_request_boundary"]["prohibited_boundary_instructions"] = ["syscall"]
            return report
        result = self.validate_fixture(mutate_report=mutation)
        self.assertEqual(result.status, "fail")
        self.assert_reason(result, "prohibited_instruction_present")

    def test_fails_when_qemu_is_blocked(self):
        mutation = lambda data: data | {"outcome": "blocked"}
        result = self.validate_fixture(mutate_metadata=mutation)
        self.assertEqual(result.status, "fail")
        self.assert_reason(result, "runtime_outcome_invalid")

    def test_fails_when_metadata_omits_boundary_marker(self):
        marker = "KOZO_FIXED_USER_REQUEST_OK"
        mutation = lambda data: data | {
            "observed_markers": [value for value in data["observed_markers"] if value != marker]
        }
        result = self.validate_fixture(mutate_metadata=mutation)
        self.assertEqual(result.status, "fail")
        self.assert_reason(result, "metadata_log_mismatch")

    def test_fails_when_serial_omits_boundary_marker(self):
        mutation = lambda text: text.replace("KOZO_FIXED_USER_REQUEST_OK\n", "")
        result = self.validate_fixture(mutate_serial=mutation)
        self.assertEqual(result.status, "fail")
        self.assert_reason(result, "runtime_marker_missing")

    def test_fails_when_boundary_marker_is_duplicated(self):
        mutation = lambda text: text.replace(
            "KOZO_FIXED_USER_REQUEST_OK\n",
            "KOZO_FIXED_USER_REQUEST_OK\nKOZO_FIXED_USER_REQUEST_OK\n",
        )
        result = self.validate_fixture(mutate_serial=mutation)
        self.assertEqual(result.status, "fail")
        self.assert_reason(result, "runtime_marker_duplicate")

    def test_failure_diagnostic_names_field(self):
        result = self.validate_fixture(mutate_boot=lambda text: text.replace("    jnz .halt\n", ""))
        self.assertEqual(result.code, FIXED_USER_REQUEST_BOUNDARY_EVIDENCE_INVALID)
        self.assertIn("reason", result.meta)
        self.assertIn("contract_field", result.meta)

    def assert_reason(self, result, reason):
        self.assertEqual(result.status, "fail")
        self.assertEqual(result.code, FIXED_USER_REQUEST_BOUNDARY_EVIDENCE_INVALID)
        self.assertEqual(result.meta["reason"], reason)

    def validate_fixture(
        self,
        mutate_boot=None,
        mutate_privilege=None,
        mutate_layout=None,
        mutate_linker=None,
        mutate_report=None,
        mutate_metadata=None,
        mutate_serial=None,
    ):
        with tempfile.TemporaryDirectory() as directory:
            paths = write_fixture(
                Path(directory),
                mutate_boot,
                mutate_privilege,
                mutate_layout,
                mutate_linker,
                mutate_report,
                mutate_metadata,
                mutate_serial,
            )
            original = patch_paths(paths)
            try:
                return FixedUserRequestBoundaryEvidenceValidator().validate({})
            finally:
                restore_paths(original)


def write_fixture(root, mutate_boot, mutate_privilege, mutate_layout, mutate_linker, mutate_report, mutate_metadata, mutate_serial):
    paths = {
        "contract": root / "contract.json",
        "boot": root / "boot.asm",
        "privilege": root / "privilege.asm",
        "layout": root / "layout.inc",
        "linker": root / "kernel.ld",
        "report": root / "kernel_elf_report.json",
        "metadata": root / "qemu_smoke.metadata.json",
        "serial": root / "qemu_smoke.log",
    }
    paths["contract"].write_text(validator_module._CONTRACT_PATH.read_text())
    write_mutated(paths["boot"], validator_module._BOOT_PATH.read_text(), mutate_boot)
    write_mutated(paths["privilege"], validator_module._PRIVILEGE_PATH.read_text(), mutate_privilege)
    write_mutated(paths["layout"], validator_module._LAYOUT_PATH.read_text(), mutate_layout)
    write_mutated(paths["linker"], validator_module._LINKER_PATH.read_text(), mutate_linker)
    report = valid_report()
    paths["report"].write_text(json.dumps(mutate_report(report) if mutate_report else report))
    markers = list(get_smoke_marker_order())
    metadata = {"outcome": "pass", "observed_markers": markers}
    paths["metadata"].write_text(json.dumps(mutate_metadata(metadata) if mutate_metadata else metadata))
    serial = "\n".join(markers) + "\n"
    paths["serial"].write_text(mutate_serial(serial) if mutate_serial else serial)
    return paths


def valid_report():
    symbols = {name: {"present": True, "address": "0xffffffff80200000"} for name in validator_module._ELF_SYMBOLS}
    return {
        "fixed_user_request_boundary": {
            "symbols": symbols,
            "request_shadow": valid_range(40),
            "response_shadow": valid_range(48),
            "response_verify": valid_range(48),
            "ring3_request_store_count": 8,
            "ring3_return_interrupt_present": True,
            "handler_call_order_valid": True,
            "copy_in_memory_move_count": 10,
            "copy_out_memory_move_count": 12,
            "readback_memory_move_count": 12,
            "clear_memory_move_count": 1,
            "clear_stosq_count": 5,
            "post_clear_zero_validation_present": True,
            "fixed_continuation_jump_present": True,
            "prohibited_boundary_instructions": [],
        }
    }


def valid_range(size):
    return {
        "size_bytes": size,
        "required_size_bytes": size,
        "required_alignment_bytes": 8,
        "start_aligned": True,
    }


def remove_symbol(report, name):
    report["fixed_user_request_boundary"]["symbols"][name]["present"] = False
    return report


def write_mutated(path, text, mutation):
    path.write_text(mutation(text) if mutation else text)


def patch_paths(paths):
    names = ("contract", "boot", "privilege", "layout", "linker", "report", "metadata", "serial")
    attributes = (
        "_CONTRACT_PATH",
        "_BOOT_PATH",
        "_PRIVILEGE_PATH",
        "_LAYOUT_PATH",
        "_LINKER_PATH",
        "_ELF_REPORT_PATH",
        "_METADATA_PATH",
        "_SERIAL_PATH",
    )
    original = {attribute: getattr(validator_module, attribute) for attribute in attributes}
    for attribute, name in zip(attributes, names):
        setattr(validator_module, attribute, paths[name])
    return original


def restore_paths(original):
    for attribute, value in original.items():
        setattr(validator_module, attribute, value)


if __name__ == "__main__":
    unittest.main()
