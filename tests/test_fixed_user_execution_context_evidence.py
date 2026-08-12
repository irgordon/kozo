from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

from harness.codes import FIXED_USER_EXECUTION_CONTEXT_CONTRACT_INVALID, OK
from harness.runtime_evidence_taxonomy import get_smoke_marker_order
from harness.validators_impl import fixed_user_execution_context_evidence as validator_module
from harness.validators_impl.fixed_user_execution_context_evidence import (
    FixedUserExecutionContextEvidenceValidator,
)

KOZO_NEGATIVE_COVERAGE = {
    "fixed_user_execution_context_evidence": {
        "context_geometry_invalid": "test_fails_when_context_size_changes",
        "result_geometry_invalid": "test_fails_when_result_size_changes",
        "linker_geometry_invalid": "test_fails_when_linker_assertion_is_missing",
        "lifecycle_invalid": "test_fails_when_activation_is_skipped",
        "context_format_invalid": "test_fails_when_format_validation_is_missing",
        "identity_invalid": "test_fails_when_identity_changes",
        "identity_pointer_derived": "test_fails_when_identity_is_pointer_derived",
        "binding_invalid": "test_fails_when_fixed_binding_validation_is_missing",
        "reserved_state_invalid": "test_fails_when_reserved_validation_is_missing",
        "transition_accounting_invalid": "test_fails_when_transition_accounting_is_missing",
        "third_transition_allowed": "test_fails_when_third_transition_guard_is_missing",
        "phase_count_mismatch_allowed": "test_fails_when_phase_count_rejection_is_missing",
        "result_commit_invalid": "test_fails_when_result_commit_is_repeated",
        "result_survival_invalid": "test_fails_when_result_is_not_validated_after_clear",
        "result_retains_authority": "test_fails_when_result_reads_identity",
        "cleanup_invalid": "test_fails_when_cleanup_readback_is_missing",
        "failure_cleanup_invalid": "test_fails_when_failure_cleanup_skips_clear",
        "continuation_before_clear": "test_fails_when_continuation_skips_completion",
        "failure_emits_success": "test_fails_when_failure_emits_success",
        "missing_elf_evidence": "test_fails_when_elf_record_is_missing",
        "missing_elf_symbol": "test_fails_when_context_symbol_is_missing",
        "elf_geometry_invalid": "test_fails_when_elf_result_alignment_is_wrong",
        "elf_storage_policy_invalid": "test_fails_when_elf_context_is_executable",
        "elf_overlap_invalid": "test_fails_when_elf_storage_overlaps",
        "runtime_outcome_invalid": "test_fails_when_qemu_is_blocked",
        "marker_sequence_changed": "test_fails_when_marker_sequence_changes",
        "runtime_marker_invalid": "test_fails_when_marker_is_duplicated",
        "diagnostic_names_field": "test_failure_diagnostic_names_field",
    }
}


class FixedUserExecutionContextEvidenceTests(unittest.TestCase):
    def test_valid_evidence_passes(self):
        result = self.validate_fixture()
        self.assertEqual((result.status, result.code), ("pass", OK))

    def test_fails_when_context_size_changes(self):
        result = self.validate_fixture(
            layout=lambda text: text.replace("%define FIXED_USER_CONTEXT_SIZE 128", "%define FIXED_USER_CONTEXT_SIZE 136")
        )
        self.assert_failure(result, "context_geometry_invalid")

    def test_fails_when_result_size_changes(self):
        result = self.validate_fixture(
            layout=lambda text: text.replace("%define FIXED_USER_CONTEXT_RESULT_SIZE 32", "%define FIXED_USER_CONTEXT_RESULT_SIZE 40")
        )
        self.assert_failure(result, "result_geometry_invalid")

    def test_fails_when_linker_assertion_is_missing(self):
        result = self.validate_fixture(
            linker=lambda text: text.replace("(fixed_user_context % 16) == 0", "context_alignment_removed")
        )
        self.assert_failure(result, "linker_geometry_invalid")

    def test_fails_when_activation_is_skipped(self):
        result = self.validate_fixture(
            privilege=lambda text: text.replace("    call activate_fixed_user_execution_context\n", "", 1)
        )
        self.assert_failure(result, "lifecycle_invalid")

    def test_fails_when_format_validation_is_missing(self):
        result = self.validate_fixture(
            privilege=lambda text: text.replace("FIXED_USER_CONTEXT_STRUCTURE_SIZE_OFFSET", "REMOVED_STRUCTURE_SIZE_OFFSET")
        )
        self.assert_failure(result, "context_format_invalid")

    def test_fails_when_identity_changes(self):
        result = self.validate_fixture(
            layout=lambda text: text.replace("0x4b4f5a4f43545831", "0x4b4f5a4f43545832")
        )
        self.assert_failure(result, "identity_invalid")

    def test_fails_when_identity_is_pointer_derived(self):
        result = self.validate_fixture(
            privilege=lambda text: text.replace(
                "populate_fixed_user_execution_context:\n",
                "populate_fixed_user_execution_context:\n    lea rax, [rel fixed_user_context]\n",
                1,
            )
        )
        self.assert_failure(result, "identity_pointer_derived")

    def test_fails_when_fixed_binding_validation_is_missing(self):
        result = self.validate_fixture(
            privilege=lambda text: replace_in_range(
                text,
                "validate_fixed_user_context_bindings:",
                "validate_fixed_user_context_reserved_state:",
                "FIXED_USER_CONTEXT_USER_STACK_TOP_OFFSET",
                "REMOVED_STACK_TOP_OFFSET",
            )
        )
        self.assert_failure(result, "binding_invalid")

    def test_fails_when_reserved_validation_is_missing(self):
        result = self.validate_fixture(
            privilege=lambda text: replace_in_range(
                text,
                "validate_fixed_user_context_reserved_state:",
                "validate_fixed_user_context_phase_and_count:",
                "FIXED_USER_CONTEXT_RESERVED_1_OFFSET",
                "REMOVED_RESERVED_OFFSET",
            )
        )
        self.assert_failure(result, "reserved_state_invalid")

    def test_fails_when_transition_accounting_is_missing(self):
        result = self.validate_fixture(
            privilege=lambda text: text.replace("    call record_fixed_user_context_transition\n", "", 1)
        )
        self.assert_failure(result, "transition_accounting_invalid")

    def test_fails_when_third_transition_guard_is_missing(self):
        result = self.validate_fixture(
            privilege=lambda text: replace_in_range(
                text,
                "record_fixed_user_context_transition:",
                "validate_fixed_user_context_return:",
                "    jae .budget_exceeded\n",
                "",
            )
        )
        self.assert_failure(result, "third_transition_allowed")

    def test_fails_when_phase_count_rejection_is_missing(self):
        result = self.validate_fixture(
            privilege=lambda text: replace_in_range(
                text,
                "validate_fixed_user_context_phase_and_count:",
                "populate_fixed_user_execution_context:",
                "fixed_user_context_count_invalid:",
                "fixed_user_context_count_accepted:",
            )
        )
        self.assert_failure(result, "phase_count_mismatch_allowed")

    def test_fails_when_result_commit_is_repeated(self):
        result = self.validate_fixture(
            privilege=lambda text: text.replace(
                "    call commit_fixed_user_context_result\n",
                "    call commit_fixed_user_context_result\n    call commit_fixed_user_context_result\n",
                1,
            )
        )
        self.assert_failure(result, "result_commit_invalid")

    def test_fails_when_result_is_not_validated_after_clear(self):
        result = self.validate_fixture(
            privilege=lambda text: replace_in_range(
                text,
                "complete_fixed_user_execution_context:",
                "fail_and_clear_fixed_user_execution_context:",
                "    call validate_fixed_user_context_success_result\n",
                "",
            )
        )
        self.assert_failure(result, "result_survival_invalid")

    def test_fails_when_result_reads_identity(self):
        result = self.validate_fixture(
            privilege=lambda text: text.replace(
                "commit_fixed_user_context_result:\n",
                "commit_fixed_user_context_result:\n    mov rax, [rel fixed_user_context + FIXED_USER_CONTEXT_OPAQUE_IDENTITY_OFFSET]\n",
                1,
            )
        )
        self.assert_failure(result, "result_retains_authority")

    def test_fails_when_cleanup_readback_is_missing(self):
        result = self.validate_fixture(
            privilege=lambda text: replace_in_range(
                text,
                "clear_fixed_user_execution_context:",
                "complete_fixed_user_execution_context:",
                "    call fixed_qword_span_is_zero\n",
                "",
            )
        )
        self.assert_failure(result, "cleanup_invalid")

    def test_fails_when_failure_cleanup_skips_clear(self):
        result = self.validate_fixture(
            privilege=lambda text: replace_in_range(
                text,
                "fail_and_clear_fixed_user_execution_context:",
                "commit_fixed_user_context_failure_result:",
                "    call clear_fixed_user_execution_context\n",
                "",
            )
        )
        self.assert_failure(result, "failure_cleanup_invalid")

    def test_fails_when_failure_result_is_not_validated_after_clear(self):
        result = self.validate_fixture(
            privilege=lambda text: replace_in_range(
                text,
                "fail_and_clear_fixed_user_execution_context:",
                "commit_fixed_user_context_failure_result:",
                "    call validate_fixed_user_context_failure_result_survives\n",
                "",
            )
        )
        self.assert_failure(result, "failure_cleanup_invalid")

    def test_fails_when_continuation_skips_completion(self):
        result = self.validate_fixture(
            privilege=lambda text: replace_in_range(
                text,
                "privilege_ring0_continuation:",
                "privilege_fault_sink:",
                "    call complete_fixed_user_execution_context\n",
                "",
            )
        )
        self.assert_failure(result, "continuation_before_clear")

    def test_fails_when_failure_emits_success(self):
        result = self.validate_fixture(
            privilege=lambda text: text.replace(
                "fail_and_clear_fixed_user_execution_context:\n",
                "fail_and_clear_fixed_user_execution_context:\n    call runtime_serial_write_ring0_return_marker\n",
                1,
            )
        )
        self.assert_failure(result, "failure_emits_success")

    def test_fails_when_elf_record_is_missing(self):
        result = self.validate_fixture(report=lambda value: value.pop("fixed_user_execution_context") and value)
        self.assert_failure(result, "missing_elf_evidence")

    def test_fails_when_context_symbol_is_missing(self):
        def mutation(report):
            report["fixed_user_execution_context"]["symbols"]["fixed_user_context"]["present"] = False
            return report

        self.assert_failure(self.validate_fixture(report=mutation), "missing_elf_symbol")

    def test_fails_when_elf_result_alignment_is_wrong(self):
        def mutation(report):
            report["fixed_user_execution_context"]["result"]["start_aligned"] = False
            return report

        self.assert_failure(self.validate_fixture(report=mutation), "elf_geometry_invalid")

    def test_fails_when_elf_context_is_executable(self):
        def mutation(report):
            report["fixed_user_execution_context"]["context"]["non_executable"] = False
            return report

        self.assert_failure(self.validate_fixture(report=mutation), "elf_storage_policy_invalid")

    def test_fails_when_elf_storage_overlaps(self):
        def mutation(report):
            record = report["fixed_user_execution_context"]
            record["overlaps"] = ["context:result"]
            record["no_overlap"] = False
            return report

        self.assert_failure(self.validate_fixture(report=mutation), "elf_overlap_invalid")

    def test_fails_when_elf_protected_range_evidence_is_incomplete(self):
        def mutation(report):
            record = report["fixed_user_execution_context"]
            record["protected_ranges"].pop("boot_stack")
            return report

        self.assert_failure(self.validate_fixture(report=mutation), "elf_overlap_invalid")

    def test_fails_when_qemu_is_blocked(self):
        self.assert_failure(
            self.validate_fixture(metadata=lambda value: value | {"outcome": "blocked"}),
            "runtime_outcome_invalid",
        )

    def test_fails_when_marker_sequence_changes(self):
        def mutation(metadata):
            metadata["observed_markers"] = metadata["observed_markers"][:-1]
            return metadata

        self.assert_failure(self.validate_fixture(metadata=mutation), "marker_sequence_changed")

    def test_fails_when_marker_is_duplicated(self):
        marker = get_smoke_marker_order()[0]
        self.assert_failure(
            self.validate_fixture(serial=lambda text: text + marker + "\n"),
            "runtime_marker_invalid",
        )

    def test_failure_diagnostic_names_field(self):
        result = self.validate_fixture(
            layout=lambda text: text.replace("%define FIXED_USER_CONTEXT_SIZE 128", "%define FIXED_USER_CONTEXT_SIZE 136")
        )
        self.assertEqual(result.code, FIXED_USER_EXECUTION_CONTEXT_CONTRACT_INVALID)
        self.assertIn("reason", result.meta)
        self.assertIn("contract_field", result.meta)

    def validate_fixture(
        self,
        *,
        privilege=None,
        layout=None,
        linker=None,
        runtime=None,
        report=None,
        metadata=None,
        serial=None,
    ):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            paths = self.write_fixtures(
                root, privilege, layout, linker, runtime, report, metadata, serial
            )
            originals = self.patch_paths(paths)
            try:
                return FixedUserExecutionContextEvidenceValidator().validate({})
            finally:
                self.restore_paths(originals)

    def write_fixtures(self, root, privilege, layout, linker, runtime, report, metadata, serial):
        text_fixtures = {
            "contract": (validator_module._CONTRACT_PATH, None),
            "privilege": (validator_module._PRIVILEGE_PATH, privilege),
            "layout": (validator_module._LAYOUT_PATH, layout),
            "linker": (validator_module._LINKER_PATH, linker),
            "runtime": (validator_module._RUNTIME_PATH, runtime),
        }
        paths = {}
        for name, (source, mutation) in text_fixtures.items():
            paths[name] = root / name
            value = source.read_text()
            paths[name].write_text(mutation(value) if mutation else value)
        paths["report"] = self.write_json(root / "report", validator_module._ELF_REPORT_PATH, report)
        paths["metadata"] = self.write_json(root / "metadata", validator_module._METADATA_PATH, metadata)
        paths["serial"] = root / "serial"
        markers = "\n".join(get_smoke_marker_order()) + "\n"
        paths["serial"].write_text(serial(markers) if serial else markers)
        return paths

    def write_json(self, target, source, mutation):
        value = json.loads(source.read_text())
        target.write_text(json.dumps(mutation(copy.deepcopy(value)) if mutation else value))
        return target

    def patch_paths(self, paths):
        mapping = {
            "_CONTRACT_PATH": paths["contract"],
            "_PRIVILEGE_PATH": paths["privilege"],
            "_LAYOUT_PATH": paths["layout"],
            "_LINKER_PATH": paths["linker"],
            "_RUNTIME_PATH": paths["runtime"],
            "_ELF_REPORT_PATH": paths["report"],
            "_METADATA_PATH": paths["metadata"],
            "_SERIAL_PATH": paths["serial"],
        }
        originals = {name: getattr(validator_module, name) for name in mapping}
        for name, path in mapping.items():
            setattr(validator_module, name, path)
        return originals

    def restore_paths(self, originals):
        for name, path in originals.items():
            setattr(validator_module, name, path)

    def assert_failure(self, result, reason):
        self.assertEqual(result.status, "fail")
        self.assertEqual(result.code, FIXED_USER_EXECUTION_CONTEXT_CONTRACT_INVALID)
        self.assertEqual(result.meta["reason"], reason)
        self.assertIn("contract_field", result.meta)


def replace_in_range(text, start, end, old, new):
    start_index = text.index(start)
    end_index = text.index(end, start_index)
    segment = text[start_index:end_index]
    return text[:start_index] + segment.replace(old, new, 1) + text[end_index:]


if __name__ == "__main__":
    unittest.main()
