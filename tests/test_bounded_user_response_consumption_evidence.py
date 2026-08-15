from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

from harness.codes import BOUNDED_USER_RESPONSE_CONSUMPTION_EVIDENCE_INVALID, OK
from harness.runtime_evidence_taxonomy import get_smoke_marker_order
from harness.validators_impl import bounded_user_response_consumption_evidence as validator_module
from harness.validators_impl.bounded_user_response_consumption_evidence import (
    BoundedUserResponseConsumptionEvidenceValidator,
)

KOZO_NEGATIVE_COVERAGE = {
    "bounded_user_response_consumption_evidence": {
        "layout_geometry_invalid": "test_fails_when_layout_constant_is_missing",
        "phase_dispatch_invalid": "test_fails_when_response_phase_dispatch_is_missing",
        "first_handler_order_invalid": "test_fails_when_first_handler_does_not_prepare_resume",
        "resume_frame_invalid": "test_fails_when_second_iretq_is_missing",
        "ring3_consumer_invalid": "test_fails_when_second_int_is_missing",
        "partial_ring3_response_validation": "test_fails_when_response_comparison_is_missing",
        "second_handler_order_invalid": "test_fails_when_response_revalidation_is_missing",
        "record_copy_invalid": "test_fails_when_record_copy_is_partial",
        "record_validation_invalid": "test_fails_when_record_validation_is_partial",
        "final_clearing_invalid": "test_fails_when_consumption_shadow_is_not_cleared",
        "phase_reset_invalid": "test_fails_when_phase_reset_is_missing",
        "failure_emits_success": "test_fails_when_failure_emits_success",
        "linker_geometry_invalid": "test_fails_when_linker_phase_assertion_is_missing",
        "missing_elf_symbol": "test_fails_when_elf_symbol_is_missing",
        "elf_geometry_invalid": "test_fails_when_elf_shadow_geometry_is_wrong",
        "missing_elf_evidence": "test_fails_when_elf_evidence_is_missing",
        "missing_elf_operation": "test_fails_when_elf_record_copy_is_partial",
        "prohibited_instruction_present": "test_fails_when_elf_contains_syscall",
        "runtime_outcome_invalid": "test_fails_when_qemu_is_blocked",
        "metadata_log_mismatch": "test_fails_when_metadata_markers_are_stale",
        "runtime_marker_missing": "test_fails_when_serial_marker_is_missing",
        "runtime_marker_duplicate": "test_fails_when_serial_marker_is_duplicated",
        "diagnostic_names_field": "test_failure_diagnostic_names_field",
    }
}


class BoundedUserResponseConsumptionEvidenceTests(unittest.TestCase):
    def test_valid_evidence_passes(self):
        result = self.validate_fixture()
        self.assertEqual(result.status, "pass")
        self.assertEqual(result.code, OK)

    def test_fails_when_layout_constant_is_missing(self):
        result = self.validate_fixture(layout=lambda text: text.replace("%define FIXED_USER_PHASE_CONSUMED 2", ""))
        self.assertEqual(result.status, "fail")
        self.assert_reason(result, "layout_geometry_invalid")

    def test_fails_when_response_phase_dispatch_is_missing(self):
        result = self.validate_fixture(
            privilege=lambda text: text.replace("    je handle_fixed_user_response_consumption\n", "", 1)
        )
        self.assertEqual(result.status, "fail")
        self.assert_reason(result, "phase_dispatch_invalid")

    def test_fails_when_first_handler_does_not_prepare_resume(self):
        result = self.validate_fixture(
            privilege=lambda text: text.replace("    call prepare_user_response_resume\n", "", 1)
        )
        self.assertEqual(result.status, "fail")
        self.assert_reason(result, "first_handler_order_invalid")

    def test_fails_when_second_iretq_is_missing(self):
        result = self.validate_fixture(
            privilege=lambda text: replace_in_range(
                text,
                "resume_fixed_user_response_consumer:",
                "validate_user_visible_response:",
                "    iretq\n",
                "    ud2\n",
            )
        )
        self.assertEqual(result.status, "fail")
        self.assert_reason(result, "resume_frame_invalid")

    def test_fails_when_second_int_is_missing(self):
        result = self.validate_fixture(
            privilege=lambda text: replace_in_range(
                text,
                "user_response_consumer_start:",
                "user_response_consumer_end:",
                "    int KOZO_PRIVILEGE_RETURN_VECTOR\n",
                "",
            )
        )
        self.assertEqual(result.status, "fail")
        self.assert_reason(result, "ring3_consumer_invalid")

    def test_fails_when_response_comparison_is_missing(self):
        result = self.validate_fixture(
            privilege=lambda text: text.replace("    cmp qword [rdi + 80], 0\n", "", 1)
        )
        self.assertEqual(result.status, "fail")
        self.assert_reason(result, "partial_ring3_response_validation")

    def test_fails_when_response_revalidation_is_missing(self):
        result = self.validate_fixture(
            privilege=lambda text: text.replace("    call validate_user_visible_response\n", "", 1)
        )
        self.assertEqual(result.status, "fail")
        self.assert_reason(result, "second_handler_order_invalid")

    def test_fails_when_record_copy_is_partial(self):
        result = self.validate_fixture(
            privilege=lambda text: replace_in_range(
                text,
                "copy_fixed_user_consumption_record:",
                "validate_fixed_user_consumption_record:",
                "    mov rax, [rsi + 40]\n    mov [rdi + 40], rax\n",
                "",
            )
        )
        self.assertEqual(result.status, "fail")
        self.assert_reason(result, "record_copy_invalid")

    def test_fails_when_record_validation_is_partial(self):
        result = self.validate_fixture(
            privilege=lambda text: text.replace(
                "    cmp qword [rel fixed_user_consumption_shadow + 40], 0\n",
                "",
                1,
            )
        )
        self.assertEqual(result.status, "fail")
        self.assert_reason(result, "record_validation_invalid")

    def test_fails_when_consumption_shadow_is_not_cleared(self):
        result = self.validate_fixture(
            privilege=lambda text: replace_in_range(
                text,
                "clear_fixed_user_response_transaction:",
                "clear_fixed_user_request_buffers:",
                "    lea rdi, [rel fixed_user_consumption_shadow]\n",
                "    lea rdi, [rel fixed_user_request_shadow]\n",
            )
        )
        self.assertEqual(result.status, "fail")
        self.assert_reason(result, "final_clearing_invalid")

    def test_fails_when_phase_reset_is_missing(self):
        result = self.validate_fixture(
            privilege=lambda text: replace_in_range(
                text,
                "privilege_ring0_continuation:",
                "privilege_fault_sink:",
                "    cmp qword [rel fixed_user_transaction_phase], FIXED_USER_PHASE_REQUEST_PENDING\n",
                "",
            )
        )
        self.assertEqual(result.status, "fail")
        self.assert_reason(result, "phase_reset_invalid")

    def test_fails_when_failure_emits_success(self):
        result = self.validate_fixture(
            privilege=lambda text: text.replace(
                "privilege_return_failure:\n",
                "privilege_return_failure:\n    call runtime_serial_write_fixed_user_response_marker\n",
            )
        )
        self.assertEqual(result.status, "fail")
        self.assert_reason(result, "failure_emits_success")

    def test_fails_when_linker_phase_assertion_is_missing(self):
        result = self.validate_fixture(
            linker=lambda text: text.replace(
                '"fixed user transaction phase must be exactly 8 bytes"',
                '"phase assertion removed"',
            )
        )
        self.assertEqual(result.status, "fail")
        self.assert_reason(result, "linker_geometry_invalid")

    def test_fails_when_elf_symbol_is_missing(self):
        def mutation(report):
            report["bounded_user_response_consumption"]["symbols"]["user_response_consumer_start"]["present"] = False
            return report
        result = self.validate_fixture(report=mutation)
        self.assertEqual(result.status, "fail")
        self.assert_reason(result, "missing_elf_symbol")

    def test_fails_when_elf_shadow_geometry_is_wrong(self):
        def mutation(report):
            report["bounded_user_response_consumption"]["consumption_shadow"]["size_bytes"] = 40
            return report
        result = self.validate_fixture(report=mutation)
        self.assertEqual(result.status, "fail")
        self.assert_reason(result, "elf_geometry_invalid")

    def test_fails_when_elf_evidence_is_missing(self):
        def mutation(report):
            del report["bounded_user_response_consumption"]
            return report
        result = self.validate_fixture(report=mutation)
        self.assertEqual(result.status, "fail")
        self.assert_reason(result, "missing_elf_evidence")

    def test_fails_when_elf_record_copy_is_partial(self):
        def mutation(report):
            report["bounded_user_response_consumption"]["record_copy_memory_move_count"] = 4
            return report
        result = self.validate_fixture(report=mutation)
        self.assertEqual(result.status, "fail")
        self.assert_reason(result, "missing_elf_operation")

    def test_fails_when_elf_contains_syscall(self):
        def mutation(report):
            report["bounded_user_response_consumption"]["prohibited_instructions"] = ["syscall"]
            return report
        result = self.validate_fixture(report=mutation)
        self.assertEqual(result.status, "fail")
        self.assert_reason(result, "prohibited_instruction_present")

    def test_fails_when_qemu_is_blocked(self):
        result = self.validate_fixture(metadata=lambda data: data | {"outcome": "blocked"})
        self.assertEqual(result.status, "fail")
        self.assert_reason(result, "runtime_outcome_invalid")

    def test_fails_when_metadata_markers_are_stale(self):
        def mutation(data):
            data["observed_markers"] = data["observed_markers"][:-1]
            return data
        result = self.validate_fixture(metadata=mutation)
        self.assertEqual(result.status, "fail")
        self.assert_reason(result, "metadata_log_mismatch")

    def test_fails_when_serial_marker_is_missing(self):
        result = self.validate_fixture(
            serial=lambda text: text.replace("KOZO_USER_RESPONSE_CONSUMED_OK", "")
        )
        self.assertEqual(result.status, "fail")
        self.assert_reason(result, "runtime_marker_missing")

    def test_fails_when_serial_marker_is_duplicated(self):
        result = self.validate_fixture(serial=lambda text: text + "\nKOZO_FIXED_USER_RESPONSE_OK\n")
        self.assertEqual(result.status, "fail")
        self.assert_reason(result, "runtime_marker_duplicate")

    def test_failure_diagnostic_names_field(self):
        result = self.validate_fixture(layout=lambda text: text.replace("%define FIXED_USER_PHASE_CONSUMED 2", ""))
        self.assertEqual(result.code, BOUNDED_USER_RESPONSE_CONSUMPTION_EVIDENCE_INVALID)
        self.assertIn("reason", result.meta)
        self.assertIn("contract_field", result.meta)

    def assert_reason(self, result, reason):
        self.assertEqual(result.status, "fail")
        self.assertEqual(result.code, BOUNDED_USER_RESPONSE_CONSUMPTION_EVIDENCE_INVALID)
        self.assertEqual(result.meta["reason"], reason)
        self.assertIn("contract_field", result.meta)

    def validate_fixture(
        self,
        *,
        boot=None,
        privilege=None,
        layout=None,
        linker=None,
        report=None,
        metadata=None,
        serial=None,
    ):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            serial_source = root / "serial-source"
            serial_source.write_text(valid_serial_log())
            fixtures = {
                "_BOOT_PATH": (validator_module._BOOT_PATH, boot, False),
                "_PRIVILEGE_PATH": (validator_module._PRIVILEGE_PATH, privilege, False),
                "_LAYOUT_PATH": (validator_module._LAYOUT_PATH, layout, False),
                "_LINKER_PATH": (validator_module._LINKER_PATH, linker, False),
                "_ELF_REPORT_PATH": (validator_module._ELF_REPORT_PATH, report, True),
                "_METADATA_PATH": (validator_module._METADATA_PATH, metadata, True),
                "_SERIAL_PATH": (serial_source, serial, False),
            }
            originals = {}
            try:
                for index, (attribute, (source_path, mutation, is_json)) in enumerate(fixtures.items()):
                    target = root / f"fixture-{index}"
                    if is_json:
                        value = json.loads(source_path.read_text())
                        if attribute == "_METADATA_PATH":
                            value["observed_markers"] = list(get_smoke_marker_order())
                            value["outcome"] = "pass"
                            value["blocker_category"] = "none"
                        target.write_text(json.dumps(mutation(copy.deepcopy(value)) if mutation else value))
                    else:
                        value = source_path.read_text()
                        target.write_text(mutation(value) if mutation else value)
                    originals[attribute] = getattr(validator_module, attribute)
                    setattr(validator_module, attribute, target)
                return BoundedUserResponseConsumptionEvidenceValidator().validate({})
            finally:
                for attribute, value in originals.items():
                    setattr(validator_module, attribute, value)


def replace_in_range(text, start, end, old, new):
    start_index = text.index(start)
    end_index = text.index(end, start_index)
    section = text[start_index:end_index].replace(old, new, 1)
    return text[:start_index] + section + text[end_index:]


def valid_serial_log():
    return "\n".join(get_smoke_marker_order()) + "\n"


if __name__ == "__main__":
    unittest.main()
